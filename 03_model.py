import sys
import duckdb

# Lets the table borders print on any Windows terminal.
sys.stdout.reconfigure(encoding="utf-8")

con = duckdb.connect("warehouse.duckdb")


def show(title, sql):
    print("\n=== " + title)
    con.sql(sql).show(max_width=220, max_rows=40)


def stop_unless(ok, message):
    if not ok:
        raise SystemExit("STOP: " + message)


def count(sql):
    return con.sql(sql).fetchone()[0]


# ---------- dim_date ----------
# One row per day for three whole financial years, 1 March 2024 to 28 February 2027.
# The financial year starts in March, so March is fiscal month 1 and January and February
# belong to the financial year that started the March before. FY26 is March 2025 to February 2026.
con.execute("""
    create or replace table dim_date as
    with days as (
        select cast(d as date) as date
        from generate_series(date '2024-03-01', date '2027-02-28', interval 1 day) as t(d)
    ),
    numbered as (
        select *,
               year(date) + case when month(date) >= 3 then 1 else 0 end as fiscal_year_no,
               (month(date) + 9) % 12 + 1 as fiscal_month_no
        from days
    )
    select
        date,
        year(date) as year,
        month(date) as month_no,
        strftime(date, '%b') as month_name,
        strftime(date, '%b %Y') as month_label,
        cast(date_trunc('month', date) as date) as month_start,
        fiscal_year_no,
        'FY' || right(cast(fiscal_year_no as varchar), 2) as fiscal_year,
        fiscal_month_no,
        'Q' || cast((fiscal_month_no + 2) // 3 as varchar) as fiscal_quarter,
        case when fiscal_month_no <= 6 then 'H1' else 'H2' end as fiscal_half,
        cast(date_trunc('week', date) as date) as week_start,   -- weeks start on Monday
        isodow(date) as day_of_week_no,                         -- 1 is Monday, 7 is Sunday
        strftime(date, '%a') as day_name,
        isodow(date) >= 6 as is_weekend
    from numbered
""")

# ---------- dim_branch ----------
con.execute("""
    create or replace table dim_branch as
    select branch_code, branch_name, region, ownership, open_date, close_date, tills,
           close_date is null as is_open
    from stg_branches
""")

# ---------- dim_item ----------
con.execute("""
    create or replace table dim_item as
    select item_code, description, category, list_price_incl, is_active
    from stg_items
""")

# ---------- dim_account ----------
con.execute("""
    create or replace table dim_account as
    select account_code, account_name, pl_group, is_in_ebitda
    from stg_accounts
""")

# ---------- fact_sales ----------
# One row per POS line, excl VAT, with the cost attached.
# Problem 10: the cost is the one in force on the day of the sale, found with a date range join.
# A left join is used so that a line with no matching cost is kept and shows up in the check below,
# instead of quietly disappearing.
con.execute("""
    create or replace table fact_sales as
    select
        s.txn_id, s.line_no, s.txn_date, s.txn_ts,
        s.branch_code, s.item_code, s.cashier, s.payment_type, s.txn_type,
        s.qty,
        s.gross_sales_excl,
        s.discount_excl,
        s.net_sales_excl,
        c.unit_cost_excl,
        s.qty * c.unit_cost_excl as cost_of_sales_excl,
        s.net_sales_excl - s.qty * c.unit_cost_excl as gross_profit
    from stg_sales s
    left join stg_costs c
      on c.item_code = s.item_code
     and s.txn_date >= c.effective_from
     and s.txn_date < c.effective_to
""")

# ---------- fact_voids ----------
# Voids are not sales, but the void-rate KPI needs them, so they get a small table of their own.
con.execute("""
    create or replace table fact_voids as
    select txn_id, line_no, txn_date, txn_ts, branch_code, item_code, cashier, payment_type,
           qty, net_sales_excl as void_value_excl
    from stg_voids
""")

# ---------- fact_opex ----------
# One row per branch, month and account. The credit line at DBN02 nets off against
# the expense line in the same month here.
con.execute("""
    create or replace table fact_opex as
    select branch_code, month_start, account_code, cast(sum(amount_excl) as decimal(18, 2)) as amount_excl
    from stg_gl
    group by all
""")

# ---------- fact_budget ----------
con.execute("""
    create or replace table fact_budget as
    select branch_code, month_start, measure, budget_amount
    from stg_budget
""")

# ---------- Did the joins lose or double anything? ----------
show("Rows per table in the star schema",
     """select 'fact_sales' as table_name, count(*) as row_count from fact_sales
        union all select 'fact_voids', count(*) from fact_voids
        union all select 'fact_opex', count(*) from fact_opex
        union all select 'fact_budget', count(*) from fact_budget
        union all select 'dim_date', count(*) from dim_date
        union all select 'dim_branch', count(*) from dim_branch
        union all select 'dim_item', count(*) from dim_item
        union all select 'dim_account', count(*) from dim_account""")

stop_unless(count("select count(*) from fact_sales") == count("select count(*) from stg_sales"),
            "the cost join changed the number of sales lines")
stop_unless(count("select count(*) from fact_sales where unit_cost_excl is null") == 0,
            "a sales line has no cost for its date")
stop_unless(count("select count(*) from fact_sales f anti join dim_date d on d.date = f.txn_date") == 0,
            "a sale falls outside the date table")
stop_unless(count("select count(*) from dim_date") == count("select count(distinct date) from dim_date"),
            "dim_date has a repeated day")
stop_unless(abs(count("select sum(amount_excl) from fact_opex") - count("select sum(amount_excl) from stg_gl")) < 0.005,
            "fact_opex total differs from the ledger")

show("How the financial calendar looks (first day of a few months)",
     """select date, month_label, fiscal_year, fiscal_month_no, fiscal_quarter, fiscal_half, week_start, day_name
        from dim_date
        where date in (date '2025-02-28', date '2025-03-01', date '2025-12-01', date '2026-01-01', date '2026-02-28', date '2026-03-01')
        order by date""")

# A first look at the full P&L per financial year. The formal reconciliation is step 5.
show("Sales, Gross Profit and EBITDA per financial year, from the star schema",
     """with s as (
            select d.fiscal_year, sum(f.net_sales_excl) as sales, sum(f.gross_profit) as gp
            from fact_sales f join dim_date d on d.date = f.txn_date group by 1),
        o as (
            select d.fiscal_year, sum(f.amount_excl) as opex
            from fact_opex f
            join dim_date d on d.date = f.month_start
            join dim_account a using (account_code)
            where a.is_in_ebitda group by 1)
        select s.fiscal_year, round(s.sales, 2) as sales, round(s.gp, 2) as gross_profit,
               round(100 * s.gp / s.sales, 1) as gp_pct,
               round(o.opex, 2) as opex, round(s.gp - o.opex, 2) as ebitda
        from s join o using (fiscal_year) order by 1""")

show("Finance's control totals", "select * exclude (source_file, loaded_at) from raw_finance_control_totals")

print("Star schema built.")
con.close()
