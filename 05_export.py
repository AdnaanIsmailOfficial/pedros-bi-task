import os
import sys
import duckdb

# Lets the table borders print on any Windows terminal.
sys.stdout.reconfigure(encoding="utf-8")

con = duckdb.connect("warehouse.duckdb", read_only=True)

# Only the star schema is exported. Raw and staging tables stay in the warehouse,
# so Power BI can only ever see cleaned and checked data.
tables = ["fact_sales", "fact_voids", "fact_opex", "fact_budget",
          "dim_date", "dim_branch", "dim_item", "dim_account"]

os.makedirs("marts", exist_ok=True)

print(f"{'table':<14}{'in warehouse':>14}{'in file':>12}{'size':>10}")
for table in tables:
    path = f"marts/{table}.parquet"
    # Parquet keeps the data types (dates stay dates, numbers stay numbers) and is much smaller than CSV.
    # Writing the file again replaces it, so a rerun never appends.
    con.execute(f"copy {table} to '{path}' (format parquet)")

    # Read the file back and compare it to the warehouse, so a bad export cannot go unnoticed.
    in_warehouse = con.sql(f"select count(*) from {table}").fetchone()[0]
    in_file = con.sql(f"select count(*) from read_parquet('{path}')").fetchone()[0]
    size_mb = os.path.getsize(path) / 1024 / 1024
    print(f"{table:<14}{in_warehouse:>14,}{in_file:>12,}{size_mb:>8.2f}MB")
    if in_warehouse != in_file:
        raise SystemExit(f"STOP: {path} has {in_file:,} rows but the warehouse has {in_warehouse:,}")

# The totals in the files must equal the totals that were reconciled to finance.
wh = con.sql("select round(sum(net_sales_excl), 2), round(sum(gross_profit), 2) from fact_sales").fetchone()
fl = con.sql("select round(sum(net_sales_excl), 2), round(sum(gross_profit), 2) from read_parquet('marts/fact_sales.parquet')").fetchone()
if wh != fl:
    raise SystemExit(f"STOP: sales or GP in the exported file {fl} differ from the warehouse {wh}")

print(f"\nExported sales {fl[0]:,.2f} and GP {fl[1]:,.2f}, the same as the warehouse.")
print("Marts are in the marts folder, ready for Power BI.")
con.close()
