import duckdb
con = duckdb.connect()

# Load every extract as plain text so nothing gets silently converted.
files = {
    "pos": "data/pos_sales_*.csv",
    "items": "data/item_master.csv",
    "costs": "data/item_cost_history.csv",
    "branches": "data/branches.csv",
    "gl": "data/gl_opex_monthly.csv",
    "accounts": "data/gl_accounts.csv",
    "budget": "data/budget_wide.csv",
}
for name, path in files.items():
    con.execute(f"create view {name} as select * from read_csv('{path}', all_varchar=true, filename=true)")
    print(name, con.sql(f"select count(*) from {name}").fetchone())

# Both date formats found in the sales files, turned into a real timestamp.
TS = "coalesce(try_strptime(txn_datetime, '%d/%m/%Y %H:%M'), try_strptime(txn_datetime, '%Y-%m-%d %H:%M:%S'))"
# Branch code with spaces, dashes and lower case removed.
BR = "upper(replace(trim(branch_code), '-', ''))"


def ask(title, sql):
    print("\n=== " + title)
    con.sql(sql).show(max_width=220, max_rows=40)


# ---------- Branches ----------
ask("The branch list", "select * exclude (filename) from branches")

ask("How many different branch codes are in the sales? (should be 12)",
    "select count(distinct branch_code) as codes_in_sales from pos")

ask("The ways one branch is written",
    f"""select '[' || branch_code || ']' as branch_code, count(*) as how_many
        from pos where {BR} = 'DBN01' group by 1 order by 2 desc""")

# ---------- Transaction types and cashiers ----------
ask("Transaction types",
    """select txn_type, count(*) as lines, min(cast(qty as int)) as min_qty, max(cast(qty as int)) as max_qty,
              round(sum(cast(qty as int) * cast(unit_price_incl as double) - cast(discount_incl as double))) as value_incl
       from pos group by txn_type order by lines desc""")

ask("Cashiers with the fewest lines",
    "select cashier, count(*) as lines from pos group by cashier order by lines limit 5")

ask("What the TEST cashier rang up",
    f"""select item_code, count(*) as lines, min(unit_price_incl) as price, min(strftime({TS}, '%H:%M')) as earliest_time
        from pos where cashier = 'TEST' group by item_code order by lines desc limit 8""")

# ---------- Items ----------
ask("Item codes sold that are not in the item master",
    """select p.item_code, count(*) as lines from pos p
       left join items i on p.item_code = i.item_code
       where i.item_code is null group by 1""")

ask("Item codes that appear more than once in the item master",
    """select * exclude (filename) from items
       where item_code in (select item_code from items group by 1 having count(*) > 1)""")

ask("Categories in the item master, exactly as typed",
    "select '[' || category || ']' as category, count(*) as items from items group by 1 order by 1")

ask("Descriptions with spaces on the end",
    "select item_code, '[' || description || ']' as description from items where description <> trim(description)")

ask("Items that are inactive or never sold",
    """select i.item_code, i.description, i.active, count(p.item_code) as lines_sold
       from items i left join pos p on p.item_code = i.item_code
       group by all having count(p.item_code) = 0 or i.active <> 'Y'""")

# ---------- Dates ----------
ask("Date formats and date range per sales file",
    f"""select filename, min(txn_datetime) as example, min(length(txn_datetime)) as text_length,
               min({TS}) as first_sale, max({TS}) as last_sale
        from pos group by filename order by filename""")

# ---------- Duplicates ----------
ask("Is txn_id + line_no unique?",
    """select count(*) as raw_lines,
              count(distinct txn_id || '-' || line_no) as unique_lines,
              count(*) - count(distinct txn_id || '-' || line_no) as duplicate_lines
       from pos""")

ask("Where the duplicates come from",
    f"""with d as (select txn_id, line_no from pos group by all having count(*) > 1)
        select p.filename, count(*) as lines, min({TS})::date as first_day, max({TS})::date as last_day
        from pos p join d using (txn_id, line_no) group by 1 order by 1""")

ask("Does a plain DISTINCT remove them? (compare with unique_lines above)",
    "select count(*) as lines_after_distinct from (select distinct * exclude (filename) from pos)")

# ---------- Money ----------
ask("Is VAT in the prices? FY25 POS sales with and without VAT, against finance's FY25 total",
    f"""with s as (
            select sum(cast(qty as int) * cast(unit_price_incl as double) - cast(discount_incl as double)) as incl
            from (select * from pos qualify row_number() over (partition by txn_id, line_no order by filename) = 1)
            where {TS} < '2025-03-01' and txn_type <> 'VOID' and cashier <> 'TEST')
        select round(incl) as pos_as_is, round(incl / 1.15) as pos_less_vat,
               (select net_sales_excl_vat from read_csv('data/finance_control_totals.csv') where period = 'FY25') as finance_fy25
        from s""")

ask("Discount as a share of gross sales, per branch (top 4)",
    f"""select {BR} as branch,
               round(100 * sum(cast(discount_incl as double)) / sum(cast(qty as int) * cast(unit_price_incl as double)), 1) as discount_pct
        from pos where txn_type = 'SALE' group by 1 order by 2 desc limit 4""")

# ---------- Cost and price over time ----------
ask("Cost history for two items",
    "select * exclude (filename) from costs where item_code in ('CH02', 'DR01') order by item_code, effective_from")

ask("Selling price of one item over time",
    f"""select unit_price_incl, count(*) as lines, min({TS})::date as first_seen
        from pos where item_code = 'CH02' and cashier <> 'TEST' group by 1 order by 3""")

# ---------- Ledger ----------
ask("Ledger accounts and totals",
    """select g.account_code, a.account_name, a.pl_group, count(*) as lines,
              round(sum(cast(amount_excl as double))) as total
       from gl g left join accounts a using (account_code) group by all order by 1""")

ask("Ledger period format and negative lines",
    """select min(period) as first_period, max(period) as last_period,
              count(*) filter (where cast(amount_excl as double) < 0) as negative_lines
       from gl""")

ask("The negative ledger line", "select * exclude (filename) from gl where cast(amount_excl as double) < 0")

# ---------- Budget ----------
ask("Budget layout (first 6 columns)",
    'select Branch, Measure, "Mar-24", "Apr-24", "May-24", "Jun-24" from budget limit 4')

ask("Budget shape",
    "select count(*) as budget_rows, (select count(*) from (describe budget)) - 3 as month_columns from budget")

# ---------- Time coverage ----------
ask("Months traded per branch (30 months in the data)",
    f"""select {BR} as branch, count(distinct strftime({TS}, '%Y-%m')) as months_traded,
               min({TS})::date as first_sale, max({TS})::date as last_sale
        from pos group by 1 order by 1""")
