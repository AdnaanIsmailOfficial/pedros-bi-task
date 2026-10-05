import glob
import sys
import duckdb

# Lets the table borders print on any Windows terminal.
sys.stdout.reconfigure(encoding="utf-8")

# The warehouse is one file on disk. It is created the first time this runs.
con = duckdb.connect("warehouse.duckdb")

# Raw table name -> the file (or files) that feed it.
files = {
    "raw_pos_sales": "data/pos_sales_*.csv",
    "raw_item_master": "data/item_master.csv",
    "raw_item_cost_history": "data/item_cost_history.csv",
    "raw_branches": "data/branches.csv",
    "raw_gl_opex_monthly": "data/gl_opex_monthly.csv",
    "raw_gl_accounts": "data/gl_accounts.csv",
    "raw_budget_wide": "data/budget_wide.csv",
    "raw_finance_control_totals": "data/finance_control_totals.csv",
}


def rows_in_files(path):
    """Count data rows straight from the files, without DuckDB, as an independent check."""
    total = 0
    for f in glob.glob(path):
        with open(f, encoding="utf-8") as fh:
            total += sum(1 for line in fh if line.strip()) - 1  # minus the header row
    return total


print(f"{'table':<30}{'in files':>10}{'in table':>10}")
for table, path in files.items():
    # "create or replace" rebuilds the table from scratch, so a rerun can never double the rows.
    # all_varchar keeps every column as plain text so nothing gets silently converted.
    con.execute(f"""
        create or replace table {table} as
        select *, filename as source_file, now() as loaded_at
        from read_csv('{path}', all_varchar=true, header=true, filename=true)
    """)
    con.execute(f"alter table {table} drop column filename")

    in_files = rows_in_files(path)
    in_table = con.sql(f"select count(*) from {table}").fetchone()[0]
    print(f"{table:<30}{in_files:>10,}{in_table:>10,}")

    # Stop the pipeline if a single row went missing or got added on the way in.
    if in_files != in_table:
        raise SystemExit(f"STOP: {table} has {in_table:,} rows but the files have {in_files:,}")

print("\nSales rows per source file")
con.sql("select source_file, count(*) as row_count from raw_pos_sales group by 1 order by 1").show(max_width=220)

print("All raw tables landed and row counts match the files.")
con.close()
