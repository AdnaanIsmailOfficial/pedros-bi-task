import os
import sys
import duckdb
from openpyxl import Workbook

# Lets the table borders print on any Windows terminal.
sys.stdout.reconfigure(encoding="utf-8")

con = duckdb.connect("warehouse.duckdb", read_only=True)

# The FY26 branch P&L as one long list: one row per branch, month and P&L line.
# Sales are positive and every cost is negative, so adding up any group of rows gives its profit:
# Sales + Cost of sales = Gross Profit, and everything together = EBITDA.
# This comes straight from the warehouse with SQL and does not use Power BI or any DAX measure,
# which is what makes it an independent check on the report.
rows = con.sql("""
    with sales as (
        select f.branch_code, d.month_start, d.month_label,
               sum(f.net_sales_excl) as sales, sum(f.cost_of_sales_excl) as cost_of_sales
        from fact_sales f join dim_date d on d.date = f.txn_date
        where d.fiscal_year = 'FY26'
        group by all
    ),
    lines as (
        select branch_code, month_start, month_label,
               '1 Gross Profit' as pl_group, '1 Sales' as pl_line, sales as amount
        from sales
        union all
        select branch_code, month_start, month_label,
               '1 Gross Profit', '2 Cost of sales', -cost_of_sales
        from sales
        union all
        select f.branch_code, d.date, d.month_label,
               '2 Operating expenses', a.account_code || ' ' || a.account_name, -f.amount_excl
        from fact_opex f
        join dim_date d on d.date = f.month_start
        join dim_account a using (account_code)
        where d.fiscal_year = 'FY26' and a.is_in_ebitda
    )
    select b.branch_code, b.branch_name, l.month_start, l.month_label,
           l.pl_group, l.pl_line, round(cast(l.amount as double), 2) as amount
    from lines l join dim_branch b using (branch_code)
    order by b.branch_code, l.month_start, l.pl_group, l.pl_line
""")

os.makedirs("excel", exist_ok=True)
path = "excel/fy26_branch_pl_data.xlsx"

wb = Workbook()
ws = wb.active
ws.title = "data"
ws.append(rows.columns)
for row in rows.fetchall():
    ws.append(row)
wb.save(path)

print(f"Wrote {ws.max_row - 1:,} rows to {path}")

# The totals the pivot table should show, so there is something to compare it with.
print("\n=== What the pivot table should add up to (FY26, all branches)")
con.sql("""
    select round(sum(net_sales_excl), 2) as sales,
           round(sum(gross_profit), 2) as gross_profit,
           (select sum(f.amount_excl) from fact_opex f
            join dim_date d on d.date = f.month_start join dim_account a using (account_code)
            where d.fiscal_year = 'FY26' and a.is_in_ebitda) as opex
    from fact_sales f join dim_date d on d.date = f.txn_date
    where d.fiscal_year = 'FY26'
""").show(max_width=220)
con.close()
