import sys
import duckdb

# Lets the table borders print on any Windows terminal.
sys.stdout.reconfigure(encoding="utf-8")

# The warehouse file can be passed in, which is how the checks themselves get tested on a broken copy.
db = sys.argv[1] if len(sys.argv) > 1 else "warehouse.duckdb"
con = duckdb.connect(db, read_only=True)

# Sales, GP and EBITDA per financial period from the star schema, next to finance's figures.
# FY27 only has March to August in the data, which is what finance calls "FY27 H1".
RECON = """
    with s as (
        select d.fiscal_year, sum(f.net_sales_excl) as sales, sum(f.gross_profit) as gp
        from fact_sales f join dim_date d on d.date = f.txn_date group by 1),
    o as (
        select d.fiscal_year, sum(f.amount_excl) as opex
        from fact_opex f
        join dim_date d on d.date = f.month_start
        join dim_account a using (account_code)
        where a.is_in_ebitda group by 1),
    ours as (
        select s.fiscal_year, s.sales, s.gp, s.gp - o.opex as ebitda
        from s join o using (fiscal_year)),
    finance as (
        select left(period, 4) as fiscal_year, period,
               cast(net_sales_excl_vat as double) as sales,
               cast(gross_profit as double) as gp,
               cast(ebitda as double) as ebitda
        from raw_finance_control_totals)
    select f.period,
           round(o.sales, 2) as sales, f.sales as finance_sales, round(o.sales - f.sales, 2) as sales_diff,
           round(o.gp, 2) as gp, f.gp as finance_gp, round(o.gp - f.gp, 2) as gp_diff,
           round(o.ebitda, 2) as ebitda, f.ebitda as finance_ebitda, round(o.ebitda - f.ebitda, 2) as ebitda_diff
    from finance f left join ours o using (fiscal_year)
    order by f.period
"""

# Every check is a query that counts the rows that break a rule. Zero means the check passes.
checks = [
    # ----- Keys are unique: one row per thing, so nothing is counted twice -----
    ("Unique keys", "fact_sales has one row per txn_id + line_no",
     "select count(*) - count(distinct (txn_id, line_no)) from fact_sales"),
    ("Unique keys", "fact_opex has one row per branch, month and account",
     "select count(*) - count(distinct (branch_code, month_start, account_code)) from fact_opex"),
    ("Unique keys", "fact_budget has one row per branch, month and measure",
     "select count(*) - count(distinct (branch_code, month_start, measure)) from fact_budget"),
    ("Unique keys", "each dimension has one row per key",
     """select (select count(*) - count(distinct date) from dim_date)
             + (select count(*) - count(distinct branch_code) from dim_branch)
             + (select count(*) - count(distinct item_code) from dim_item)
             + (select count(*) - count(distinct account_code) from dim_account)"""),

    # ----- No orphans: every code in a fact exists in its dimension -----
    ("No orphan codes", "every sale and void has a known branch, item and date",
     """select (select count(*) from fact_sales f anti join dim_branch d using (branch_code))
             + (select count(*) from fact_sales f anti join dim_item d using (item_code))
             + (select count(*) from fact_sales f anti join dim_date d on d.date = f.txn_date)
             + (select count(*) from fact_voids f anti join dim_branch d using (branch_code))
             + (select count(*) from fact_voids f anti join dim_item d using (item_code))
             + (select count(*) from fact_voids f anti join dim_date d on d.date = f.txn_date)"""),
    ("No orphan codes", "every ledger and budget row has a known branch, account and month",
     """select (select count(*) from fact_opex f anti join dim_branch d using (branch_code))
             + (select count(*) from fact_opex f anti join dim_account d using (account_code))
             + (select count(*) from fact_opex f anti join dim_date d on d.date = f.month_start)
             + (select count(*) from fact_budget f anti join dim_branch d using (branch_code))
             + (select count(*) from fact_budget f anti join dim_date d on d.date = f.month_start)"""),

    # ----- No rows lost or doubled between the raw files and the facts -----
    ("Row counts", "every unique raw POS line is in fact_sales, in fact_voids, or is a TEST line",
     """select abs((select count(distinct (txn_id, line_no)) from raw_pos_sales)
                 - (select count(*) from fact_sales)
                 - (select count(*) from fact_voids)
                 - (select count(distinct (txn_id, line_no)) from raw_pos_sales where trim(cashier) = 'TEST'))"""),
    ("Row counts", "the ledger total is the same in raw and in fact_opex",
     """select case when abs((select sum(cast(amount_excl as decimal(18, 2))) from raw_gl_opex_monthly)
                            - (select sum(amount_excl) from fact_opex)) < 0.005 then 0 else 1 end"""),

    # ----- No empty values where a number is needed -----
    ("No empty values", "no empty money, quantity or cost in fact_sales",
     """select count(*) from fact_sales
        where qty is null or net_sales_excl is null or gross_sales_excl is null or discount_excl is null
           or unit_cost_excl is null or cost_of_sales_excl is null or gross_profit is null"""),
    ("No empty values", "no empty amounts in fact_opex or fact_budget",
     """select (select count(*) from fact_opex where amount_excl is null)
             + (select count(*) from fact_budget where budget_amount is null)"""),

    # ----- The business rules from problems.md actually held -----
    ("Business rules", "fact_sales holds only SALE and REFUND lines, and no TEST cashier",
     "select count(*) from fact_sales where txn_type not in ('SALE', 'REFUND') or cashier = 'TEST'"),
    ("Business rules", "sales are positive and refunds are negative",
     """select count(*) from fact_sales
        where (txn_type = 'SALE' and (qty <= 0 or net_sales_excl < 0))
           or (txn_type = 'REFUND' and (qty >= 0 or net_sales_excl > 0))"""),
    ("Business rules", "net sales = gross sales less discount, and GP = net sales less cost",
     """select count(*) from fact_sales
        where abs(net_sales_excl - (gross_sales_excl - discount_excl)) > 0.005
           or abs(gross_profit - (net_sales_excl - cost_of_sales_excl)) > 0.005"""),
    ("Business rules", "no store has sales before it opened or after it closed",
     """select count(*) from fact_sales f join dim_branch b using (branch_code)
        where f.txn_date < b.open_date or f.txn_date > coalesce(b.close_date, date '9999-12-31')"""),

    # ----- Nothing is missing in time -----
    ("Completeness", "every store has sales and ledger costs in every month it was open",
     """with months as (select distinct month_start from dim_date
                        where date between (select min(txn_date) from fact_sales) and (select max(txn_date) from fact_sales)),
        expected as (
            select b.branch_code, m.month_start from dim_branch b join months m
              on m.month_start >= date_trunc('month', b.open_date)
             and m.month_start <= coalesce(b.close_date, date '9999-12-31')),
        has_sales as (select distinct branch_code, cast(date_trunc('month', txn_date) as date) as month_start from fact_sales),
        has_opex as (select distinct branch_code, month_start from fact_opex)
        select (select count(*) from expected anti join has_sales using (branch_code, month_start))
             + (select count(*) from expected anti join has_opex using (branch_code, month_start))"""),

    # ----- The numbers agree with finance -----
    ("Reconciliation", "Sales, GP and EBITDA match finance's control totals in every period",
     f"""select count(*) from ({RECON})
         where sales is null
            or abs(sales_diff) >= 0.01 or abs(gp_diff) >= 0.01 or abs(ebitda_diff) >= 0.01"""),
]

print(f"Running {len(checks)} checks on {db}\n")
failed = 0
last_group = None
for group, name, sql in checks:
    if group != last_group:
        print(group)
        last_group = group
    bad = con.sql(sql).fetchone()[0]
    if bad:
        failed += 1
    print(f"  {'PASS' if not bad else 'FAIL'}  {name}" + (f"  ({bad:,} problems)" if bad else ""))

print("\n=== Reconciliation to finance's control totals")
con.sql(RECON).show(max_width=220)

# A fingerprint of the warehouse. Run the whole pipeline twice: this line must not change.
rows, sales, gp, opex = con.sql("""
    select (select count(*) from fact_sales), (select round(sum(net_sales_excl), 2) from fact_sales),
           (select round(sum(gross_profit), 2) from fact_sales), (select sum(amount_excl) from fact_opex)
""").fetchone()
print(f"Fingerprint: {rows:,} sales lines | sales {sales:,.2f} | GP {gp:,.2f} | ledger {opex:,.2f}")
con.close()

if failed:
    # A non-zero exit code is what tells the pipeline runner to stop.
    raise SystemExit(f"\nSTOP: {failed} of {len(checks)} checks failed. Do not export.")
print(f"\nAll {len(checks)} checks passed.")
