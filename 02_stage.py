import sys
import duckdb

# Lets the table borders print on any Windows terminal.
sys.stdout.reconfigure(encoding="utf-8")

con = duckdb.connect("warehouse.duckdb")

VAT = 1.15  # South African VAT is 15%, so an amount incl VAT divided by 1.15 is the amount excl VAT.


def show(title, sql):
    print("\n=== " + title)
    con.sql(sql).show(max_width=220, max_rows=40)


def stop_unless(ok, message):
    if not ok:
        raise SystemExit("STOP: " + message)


def count(sql):
    return con.sql(sql).fetchone()[0]


# ---------- Sales ----------
# Step A: give every column a real type and standardise the codes. No rows are removed here.
con.execute("""
    create or replace temp table pos_typed as
    select
        txn_id,
        cast(line_no as integer) as line_no,
        -- Problem 7: two date formats. Each one is tried explicitly, never guessed.
        -- try_strptime gives an empty value when the format does not fit, so the other one is tried.
        coalesce(try_strptime(txn_datetime, '%d/%m/%Y %H:%M'),
                 try_strptime(txn_datetime, '%Y-%m-%d %H:%M:%S')) as txn_ts,
        -- Problem 1: branch codes written four ways. Trim, upper case, remove the dash.
        upper(replace(trim(branch_code), '-', '')) as branch_code,
        trim(cashier) as cashier,
        upper(trim(item_code)) as item_code,
        cast(qty as integer) as qty,
        cast(unit_price_incl as decimal(18, 2)) as unit_price_incl,
        cast(discount_incl as decimal(18, 2)) as discount_incl,
        trim(payment_type) as payment_type,
        upper(trim(txn_type)) as txn_type,
        source_file
    from raw_pos_sales
""")

stop_unless(count("select count(*) from pos_typed where txn_ts is null") == 0,
            "a sales line has a date that fits neither known format")

# Step B: Problem 6, the same three days are in two files. Keep one row per txn_id + line_no.
# Ordering by source_file keeps the FY25 copy, which is the year those days belong to.
con.execute("""
    create or replace temp table pos_deduped as
    select * from pos_typed
    qualify row_number() over (partition by txn_id, line_no order by source_file) = 1
""")

# Step C: Problem 4, remove the TEST cashier. Then add the money columns.
# Problem 5: prices and discounts include VAT, so divide by 1.15.
# Problem 3: refunds have negative qty and negative discount, so they come out negative and reduce sales.
con.execute(f"""
    create or replace temp table pos_clean as
    select
        txn_id, line_no, txn_ts, cast(txn_ts as date) as txn_date,
        branch_code, cashier, item_code, payment_type, txn_type,
        qty, unit_price_incl, discount_incl,
        qty * unit_price_incl / {VAT} as gross_sales_excl,
        discount_incl / {VAT} as discount_excl,
        (qty * unit_price_incl - discount_incl) / {VAT} as net_sales_excl,
        source_file
    from pos_deduped
    where cashier <> 'TEST'
""")

# Step D: Problem 2, voids are not sales. They go to their own table for the void-rate KPI.
con.execute("create or replace table stg_sales as select * from pos_clean where txn_type in ('SALE', 'REFUND')")
con.execute("create or replace table stg_voids as select * from pos_clean where txn_type = 'VOID'")

# Row accounting: every raw line must be explained, either kept or removed for a named reason.
raw_lines = count("select count(*) from raw_pos_sales")
duplicates = raw_lines - count("select count(*) from pos_deduped")
test_lines = count("select count(*) from pos_deduped where cashier = 'TEST'")
void_lines = count("select count(*) from stg_voids")
sales_lines = count("select count(*) from stg_sales")

print("Where every raw sales line went")
print(f"  raw lines                     {raw_lines:>10,}")
print(f"  less duplicates (problem 6)   {-duplicates:>10,}")
print(f"  less TEST cashier (problem 4) {-test_lines:>10,}")
print(f"  less voids, to stg_voids (2)  {-void_lines:>10,}")
print(f"  lines in stg_sales            {sales_lines:>10,}")
stop_unless(raw_lines - duplicates - test_lines - void_lines == sales_lines,
            "sales lines do not add up, a row was lost or has an unknown txn_type")

# ---------- Branches ----------
con.execute("""
    create or replace table stg_branches as
    select
        upper(replace(trim(branch_code), '-', '')) as branch_code,
        trim(branch_name) as branch_name,
        trim(region) as region,
        trim(ownership) as ownership,
        cast(open_date as date) as open_date,
        cast(close_date as date) as close_date,   -- empty for stores that are still open
        cast(tills as integer) as tills
    from raw_branches
""")

# ---------- Items ----------
# Problem 9: trim the text and standardise the case of the category.
# Problem 8: CH02 is listed twice. Keep the row whose list price matches the latest price the tills charge.
con.execute("""
    create or replace table stg_items as
    with till_price as (
        select item_code, arg_max(unit_price_incl, txn_ts) as latest_till_price
        from stg_sales where txn_type = 'SALE' group by item_code
    )
    select
        upper(trim(i.item_code)) as item_code,
        trim(i.description) as description,
        upper(left(trim(i.category), 1)) || lower(substr(trim(i.category), 2)) as category,
        cast(i.list_price_incl as decimal(18, 2)) as list_price_incl,
        upper(trim(i.active)) = 'Y' as is_active
    from raw_item_master i
    left join till_price t on t.item_code = upper(trim(i.item_code))
    qualify row_number() over (
        partition by upper(trim(i.item_code))
        order by (cast(i.list_price_incl as decimal(18, 2)) = t.latest_till_price) desc nulls last
    ) = 1
""")

# ---------- Costs ----------
# Problem 10: cost changes over time. Each row gets the date range it was in force,
# so a sale can later be matched to the cost on its own date.
con.execute("""
    create or replace table stg_costs as
    select
        upper(trim(item_code)) as item_code,
        cast(effective_from as date) as effective_from,
        lead(cast(effective_from as date), 1, date '9999-12-31')
            over (partition by upper(trim(item_code)) order by cast(effective_from as date)) as effective_to,
        cast(unit_cost_excl as decimal(18, 2)) as unit_cost_excl
    from raw_item_cost_history
""")

# ---------- Ledger ----------
# Problem 11: only operating expenses count towards EBITDA. Depreciation and interest sit below it.
con.execute("""
    create or replace table stg_accounts as
    select
        trim(account_code) as account_code,
        trim(account_name) as account_name,
        trim(pl_group) as pl_group,
        trim(pl_group) = 'Operating expenses' as is_in_ebitda
    from raw_gl_accounts
""")

# Problem 12: period is text like 2024/03. Turn it into the first day of the month.
# The one negative line (a credit) is kept. Lines are not deduplicated, because that credit
# shares its branch, month and account with a normal expense line and both are real.
con.execute("""
    create or replace table stg_gl as
    select
        cast(strptime(period, '%Y/%m') as date) as month_start,
        upper(replace(trim(branch_code), '-', '')) as branch_code,
        trim(account_code) as account_code,
        cast(amount_excl as decimal(18, 2)) as amount_excl
    from raw_gl_opex_monthly
""")

# ---------- Budget ----------
# Problem 13: the budget is sideways, one column per month. Unpivot to one row per branch, measure and month.
# Empty cells (months when a store was not open) are left out, so there is no budget row for them.
con.execute("""
    create or replace table stg_budget as
    select
        upper(replace(trim(Branch), '-', '')) as branch_code,
        trim(Measure) as measure,
        cast(strptime(month_label, '%b-%y') as date) as month_start,
        cast(amount as decimal(18, 2)) as budget_amount
    from (
        unpivot raw_budget_wide
        on columns(* exclude (Branch, Measure, source_file, loaded_at))
        into name month_label value amount
    )
""")

# ---------- Quick checks before moving on ----------
show("Rows per staging table",
     """select 'stg_sales' as table_name, count(*) as row_count from stg_sales
        union all select 'stg_voids', count(*) from stg_voids
        union all select 'stg_branches', count(*) from stg_branches
        union all select 'stg_items', count(*) from stg_items
        union all select 'stg_costs', count(*) from stg_costs
        union all select 'stg_accounts', count(*) from stg_accounts
        union all select 'stg_gl', count(*) from stg_gl
        union all select 'stg_budget', count(*) from stg_budget""")

stop_unless(count("select count(*) from stg_sales") == count("select count(distinct (txn_id, line_no)) from stg_sales"),
            "txn_id + line_no is not unique in stg_sales")
stop_unless(count("select count(*) from stg_items") == count("select count(distinct item_code) from stg_items"),
            "item_code is not unique in stg_items")
stop_unless(count("select count(*) from stg_sales s anti join stg_branches b using (branch_code)") == 0,
            "stg_sales has a branch code that is not in stg_branches")
stop_unless(count("select count(*) from stg_sales s anti join stg_items i using (item_code)") == 0,
            "stg_sales has an item code that is not in stg_items")
stop_unless(count("select count(*) from stg_gl g anti join stg_accounts a using (account_code)") == 0,
            "stg_gl has an account code that is not in stg_accounts")
# The budget cells are empty for months when a store was not open, and unpivot leaves empty cells out.
# So the right test is: a store has a budget for a month exactly when it was open in that month.
stop_unless(count("""
    with months as (select distinct month_start from stg_budget),
    expected as (
        select b.branch_code, m.month_start
        from stg_branches b join months m
          on m.month_start >= date_trunc('month', b.open_date)
         and m.month_start <= coalesce(b.close_date, date '9999-12-31')),
    actual as (select branch_code, month_start from stg_budget group by all having count(*) = 2)
    select count(*) from (
        (select * from expected except select * from actual)
        union all
        (select * from actual except select * from expected))
""") == 0, "stg_budget months do not match the months each store was open")
stop_unless(count("select count(*) from stg_budget where month_start is null or budget_amount is null") == 0,
            "stg_budget has an empty month or amount")

# The financial year starts in March, so January and February belong to the year before.
show("Sales excl VAT per financial period, against finance's control totals",
     """with pos as (
            select case when txn_date < date '2025-03-01' then 'FY25'
                        when txn_date < date '2026-03-01' then 'FY26'
                        else 'FY27_H1' end as period,
                   sum(net_sales_excl) as pos_sales
            from stg_sales group by 1)
        select c.period, round(p.pos_sales, 2) as pos_sales,
               cast(c.net_sales_excl_vat as double) as finance_sales,
               round(p.pos_sales - cast(c.net_sales_excl_vat as double), 2) as difference
        from raw_finance_control_totals c
        left join pos p on replace(upper(c.period), ' ', '_') = p.period
        order by c.period""")

print("Staging tables built.")
con.close()
