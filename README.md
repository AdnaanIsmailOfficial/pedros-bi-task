# Flame Yard Chicken: BI work sample

A small BI build for a fictional 12-store flame-grilled chicken franchise. It takes messy POS, ledger and budget extracts, cleans them in a DuckDB warehouse, and will end in a Power BI report covering Sales, Gross Profit, EBITDA and store KPIs.

All data is dummy data. The brief is in `TASK.md` and the plan is in `PLAN.md`.

This README is updated as each step is finished.

## Progress

| Step | What | Status |
| --- | --- | --- |
| Profile | Ask questions of the raw files and list the data problems | Done |
| 1. Land | Copy the raw extracts into the warehouse, untouched | Done |
| 2. Stage | Clean the data, one rule per problem | Done |
| 3. Model | Star schema: facts and dimensions | Done |
| 4. Check | Automated data checks that stop the pipeline | Done |
| 5. Reconcile | Sales, GP and EBITDA against finance's control totals | Done |
| 6. Export | Marts for Power BI | Done |
| 7. Power BI model | Load the marts and set the relationships | Done |
| 8. Measures | 31 DAX measures, each tested against SQL | Done |
| 9. Report | Four report pages | Done |
| 10. Excel check | Pivot of the FY26 branch P&L from the warehouse | Done |
| 11. Findings | One-page summary for the Financial Manager | Next |

## How to run it

You need Python with the `duckdb` package (`pip install duckdb`). From this folder, one command runs everything in order and stops at the first step that fails:

```
python run_pipeline.py
```

Or run the scripts one at a time:

```
python explore.py        # optional: the profiling questions
python 01_land_raw.py    # builds warehouse.duckdb with the raw tables
python 02_stage.py       # builds the clean staging tables
python 03_model.py       # builds the star schema
python 04_checks.py      # runs the data checks and the reconciliation
python 05_export.py      # writes the star schema to the marts folder
python 06_excel_data.py  # writes the data for the Excel check
```

Every script can be run again at any time. Each one rebuilds its tables from scratch, so a rerun gives the same result and never creates duplicates.

## What is in this folder

| File | What it is |
| --- | --- |
| `TASK.md` | The brief |
| `PLAN.md` | The plan, written before any pipeline code |
| `data/` | The raw extracts: three POS sales files, item master, cost history, branches, ledger, chart of accounts, budget and finance's control totals |
| `explore.py` | About 25 profiling questions asked of the raw files |
| `problems.md` | The 14 data problems found, with how each was spotted and the fix |
| `01_land_raw.py` | Step 1: lands the raw files in the warehouse |
| `02_stage.py` | Step 2: cleans the raw tables into staging tables |
| `03_model.py` | Step 3: builds the facts and dimensions |
| `04_checks.py` | Steps 4 and 5: the data checks and the reconciliation to finance |
| `05_export.py` | Step 6: exports the star schema as Parquet files |
| `06_excel_data.py` | Step 10: exports the FY26 branch P&L lines for the Excel check |
| `excel/fy26_branch_pl_data.xlsx` | The data for the Excel check, written by the script |
| `excel/fy26_branch_pl_check.xlsx` | The Excel check: the same data with a pivot table on the `pivot` sheet |
| `run_pipeline.py` | Runs all the steps in order and stops if one fails |
| `flame_yard.pbix` | The Power BI report |
| `warehouse.duckdb` | The warehouse. Not in git; the scripts rebuild it |
| `marts/` | The exported star schema, one Parquet file per table. Not in git; the scripts rebuild it |

## The layers

1. **Raw (`raw_*`).** One table per extract, every column kept as text, never edited. Each row records which file it came from and when it was loaded. This means any number can be traced back to its source file.
2. **Staging (`stg_*`).** The cleaned version of each raw table: real data types, standard codes, bad rows removed. Each rule is commented in the SQL with the problem number it fixes.
3. **Marts (`fact_*`, `dim_*`).** The star schema that Power BI reads.

All cleaning is done in SQL in the warehouse. Power BI will only model and measure.

## Step 1: landing the raw data

`01_land_raw.py` loads the ten CSV files into eight raw tables. The three POS files stack into one `raw_pos_sales` table.

The script counts the rows in the files with plain Python, separately from the database, and stops if the two counts differ.

| Raw table | Rows in files | Rows in table |
| --- | ---: | ---: |
| `raw_pos_sales` | 705,890 | 705,890 |
| `raw_gl_opex_monthly` | 2,588 | 2,588 |
| `raw_item_cost_history` | 58 | 58 |
| `raw_item_master` | 28 | 28 |
| `raw_budget_wide` | 24 | 24 |
| `raw_branches` | 12 | 12 |
| `raw_gl_accounts` | 9 | 9 |
| `raw_finance_control_totals` | 3 | 3 |

## Step 2: staging

`02_stage.py` applies the fixes from `problems.md`.

### Cleaning rules

| Problem | Rule applied | Staging table |
| --- | --- | --- |
| 1. Branch codes written four ways | Trim, upper case, remove the dash | `stg_sales`, `stg_voids` |
| 2. Voided transactions in the data | Moved out of sales into their own table, kept for a void-rate KPI | `stg_voids` |
| 3. Refunds are negative lines | Kept as negatives so they reduce sales | `stg_sales` |
| 4. Test transactions | Every line from the `TEST` cashier removed | `stg_sales`, `stg_voids` |
| 5. Prices include VAT | Price and discount divided by 1.15 | `stg_sales`, `stg_voids` |
| 6. Three days appear in two files | One row kept per `txn_id` + `line_no` | `stg_sales`, `stg_voids` |
| 7. Two date formats | Each format parsed explicitly, and the run stops if a date fits neither | `stg_sales`, `stg_voids` |
| 8. An item listed twice | One row per item code, keeping the price the tills charge | `stg_items` |
| 9. Inconsistent categories and descriptions | Trimmed, category case standardised, inactive item flagged | `stg_items` |
| 10. Cost changes over time | Each cost gets a from and to date, ready to match to the sale date | `stg_costs` |
| 11. Ledger includes lines below EBITDA | Each account flagged as in or out of EBITDA | `stg_accounts` |
| 12. Ledger period is text | Converted to the first day of the month. The one credit line is kept | `stg_gl` |
| 13. Budget laid out sideways | Unpivoted to one row per branch, measure and month | `stg_budget` |
| 14. Stores opened and closed mid-period | Nothing to clean. Open and close dates kept for the like-for-like measure | `stg_branches` |

### Where every raw sales line went

No line disappears without a reason. The script prints this and stops if it does not add up.

| | Lines |
| --- | ---: |
| Raw sales lines | 705,890 |
| Less duplicates (problem 6) | -2,208 |
| Less `TEST` cashier (problem 4) | -35 |
| Less voids, moved to `stg_voids` (problem 2) | -8,661 |
| **Lines in `stg_sales`** | **694,986** |

### Checks built into the script

The run stops with an error if any of these fail:

- every sales date fits one of the two known formats
- the row accounting above adds up
- `txn_id` + `line_no` is unique in `stg_sales`
- `item_code` is unique in `stg_items`
- every branch code and item code in sales exists in the branch and item tables
- every ledger account exists in the chart of accounts
- each store has a budget for exactly the months it was open

### Found while staging

The budget has empty cells for months when a store was not open: Ballito before June 2025, Hilton before November 2025 and Northdale after September 2025. These are left out, so `stg_budget` has 628 rows instead of 720 (12 branches x 2 measures x 30 months). The script checks that the missing months match the open and close dates exactly.

### Sales tie to finance

With the rules above, sales excl VAT match finance's control totals to the cent in all three periods.

| Period | Sales from POS | Finance control total | Difference |
| --- | ---: | ---: | ---: |
| FY25 | 12,926,995.45 | 12,926,995.45 | 0.00 |
| FY26 | 14,893,335.92 | 14,893,335.92 | 0.00 |
| FY27 H1 | 8,171,216.44 | 8,171,216.44 | 0.00 |

## Step 3: the star schema

`03_model.py` builds the tables Power BI will read. Facts hold the numbers. Dimensions hold the things you slice the numbers by.

| Table | One row per | Rows |
| --- | --- | ---: |
| `fact_sales` | POS line (sales and refunds), excl VAT, with cost and gross profit | 694,986 |
| `fact_voids` | Voided POS line, for the void-rate KPI | 8,661 |
| `fact_opex` | Branch, month and ledger account | 2,587 |
| `fact_budget` | Branch, month and measure (Sales or Gross profit) | 628 |
| `dim_date` | Day, 1 March 2024 to 28 February 2027 | 1,095 |
| `dim_branch` | Branch | 12 |
| `dim_item` | Item | 27 |
| `dim_account` | Ledger account | 9 |

### How the facts join to the dimensions

| Fact | Joins to |
| --- | --- |
| `fact_sales` | `dim_date` on `txn_date`, `dim_branch` on `branch_code`, `dim_item` on `item_code` |
| `fact_voids` | `dim_date` on `txn_date`, `dim_branch` on `branch_code`, `dim_item` on `item_code` |
| `fact_opex` | `dim_date` on `month_start`, `dim_branch` on `branch_code`, `dim_account` on `account_code` |
| `fact_budget` | `dim_date` on `month_start`, `dim_branch` on `branch_code` |

Sales are daily, while the ledger and the budget are monthly. The monthly facts join to the first day of their month in `dim_date`, so all of them can be filtered by the same month, quarter and financial year.

### Design choices

- **Cost on each sales line.** Costs changed over time, so each line gets the cost that was in force on the day of the sale. Using today's cost for old sales would understate past gross profit.
- **Gross profit is stored per line.** `gross_profit` = `net_sales_excl` less quantity x unit cost. A refund has a negative quantity, so it reverses both the sale and its cost.
- **Fiscal calendar in `dim_date`.** March is fiscal month 1. The table covers three whole financial years (FY25 to FY27) so that year on year comparisons in Power BI have complete years to work with.
- **`fact_opex` is summed to branch, month and account.** The ledger has two lines for DBN02 repairs in October 2025 (an expense and a credit), which net off into one row. That is why it has 2,587 rows and the ledger has 2,588.

### Checks built into the script

The run stops with an error if any of these fail:

- attaching cost did not change the number of sales lines
- every sales line has a cost
- every sale date exists in `dim_date`, and `dim_date` has no repeated day
- `fact_opex` adds up to the same total as the ledger

### Sales, Gross Profit and EBITDA tie to finance

All nine figures match finance's control totals to the cent.

| Period | Sales | Gross Profit | GP % | Operating expenses | EBITDA |
| --- | ---: | ---: | ---: | ---: | ---: |
| FY25 | 12,926,995.45 | 7,386,015.95 | 57.1% | 5,495,741.82 | 1,890,274.13 |
| FY26 | 14,893,335.92 | 8,278,456.34 | 55.6% | 6,199,802.50 | 2,078,653.84 |
| FY27 H1 | 8,171,216.44 | 4,564,110.83 | 55.9% | 3,380,369.00 | 1,183,741.83 |

This comparison is automated in the next step.

## Steps 4 and 5: data checks and reconciliation

`04_checks.py` runs 16 checks on the finished star schema. Each check is a query that counts the rows breaking a rule, so zero means pass. If any check fails, the script exits with an error, `run_pipeline.py` stops, and nothing after it runs.

| Group | Check |
| --- | --- |
| Unique keys | `fact_sales` has one row per `txn_id` + `line_no` |
| Unique keys | `fact_opex` has one row per branch, month and account |
| Unique keys | `fact_budget` has one row per branch, month and measure |
| Unique keys | Each dimension has one row per key |
| No orphan codes | Every sale and void has a known branch, item and date |
| No orphan codes | Every ledger and budget row has a known branch, account and month |
| Row counts | Every unique raw POS line is in `fact_sales`, in `fact_voids`, or is a TEST line |
| Row counts | The ledger total is the same in raw and in `fact_opex` |
| No empty values | No empty money, quantity or cost in `fact_sales` |
| No empty values | No empty amounts in `fact_opex` or `fact_budget` |
| Business rules | `fact_sales` holds only SALE and REFUND lines, and no TEST cashier |
| Business rules | Sales are positive and refunds are negative |
| Business rules | Net sales = gross sales less discount, and GP = net sales less cost |
| Business rules | No store has sales before it opened or after it closed |
| Completeness | Every store has sales and ledger costs in every month it was open |
| Reconciliation | Sales, GP and EBITDA match finance's control totals in every period |

All 16 pass.

### Why each group matters

- **Unique keys:** a repeated key means something is counted twice.
- **No orphan codes:** a sale with an unknown branch or item would show as blank in Power BI, or vanish from a filtered chart.
- **Row counts:** proves no line was lost or doubled between the raw files and the facts.
- **No empty values:** an empty cost would silently make gross profit too high.
- **Business rules:** proves the fixes in `problems.md` actually held.
- **Completeness:** a missing month would look like a real drop in sales or costs.
- **Reconciliation:** the final proof that the totals agree with finance.

### Proving the checks can fail

A check that can never fail proves nothing. To test them, a copy of the warehouse was broken on purpose in four ways: five sales lines doubled, one sale given an unknown branch, one cost emptied, and one month of ledger costs deleted for one store. The checks script was then pointed at the broken copy with `python 04_checks.py <file>`. Seven of the 16 checks failed and the script exited with an error. The real warehouse was not touched.

### Reconciliation

| Period | Sales | Finance | Diff | Gross Profit | Finance | Diff | EBITDA | Finance | Diff |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FY25 | 12,926,995.45 | 12,926,995.45 | 0.00 | 7,386,015.95 | 7,386,015.95 | 0.00 | 1,890,274.13 | 1,890,274.13 | 0.00 |
| FY26 | 14,893,335.92 | 14,893,335.92 | 0.00 | 8,278,456.34 | 8,278,456.34 | 0.00 | 2,078,653.84 | 2,078,653.84 | 0.00 |
| FY27 H1 | 8,171,216.44 | 8,171,216.44 | 0.00 | 4,564,110.83 | 4,564,110.83 | 0.00 | 1,183,741.83 | 1,183,741.83 | 0.00 |

### Running it twice gives the same result

The checks script prints a one-line fingerprint of the warehouse. The whole pipeline was run twice and the line was identical both times:

```
Fingerprint: 694,986 sales lines | sales 35,991,547.82 | GP 20,228,583.13 | ledger 16,213,808.04
```

## Step 6: export for Power BI

`05_export.py` writes each fact and dimension table to its own Parquet file in the `marts` folder. Power BI reads these files and nothing else.

| File | Rows | Size |
| --- | ---: | ---: |
| `fact_sales.parquet` | 694,986 | 10.7 MB |
| `fact_voids.parquet` | 8,661 | 0.1 MB |
| `fact_opex.parquet` | 2,587 | under 0.1 MB |
| `fact_budget.parquet` | 628 | under 0.1 MB |
| `dim_date.parquet` | 1,095 | under 0.1 MB |
| `dim_branch.parquet` | 12 | under 0.1 MB |
| `dim_item.parquet` | 27 | under 0.1 MB |
| `dim_account.parquet` | 9 | under 0.1 MB |

### Design choices

- **Parquet, not CSV.** Parquet keeps the data types, so a date arrives in Power BI as a date and a number as a number. A CSV would make Power BI guess the types again, which is the kind of guessing the pipeline was built to avoid. It is also much smaller.
- **Only the star schema is exported.** Raw and staging tables stay in the warehouse, so the report can only see cleaned and checked data.
- **Export runs last.** In `run_pipeline.py` it comes after the checks, so data that fails a check never reaches Power BI.
- **The export checks itself.** Each file is read back and its row count compared to the warehouse, and the Sales and Gross Profit totals in the file must equal the reconciled totals. The script stops if they differ.
- **SQL Server was the other option.** For a team, the marts would live in a database server such as SQL Server so that reports refresh on a schedule. For a single-machine work sample, files are simpler to hand over and give the same model.

## Step 7: the Power BI model

`flame_yard.pbix` loads the eight Parquet files from `marts` with no changes in Power Query. All cleaning stays in SQL.

There are 11 relationships. Every one is many to one from a fact to a dimension, active, with a single filter direction from the dimension to the fact.

| From (many) | To (one) |
| --- | --- |
| `fact_sales[txn_date]` | `dim_date[date]` |
| `fact_sales[branch_code]` | `dim_branch[branch_code]` |
| `fact_sales[item_code]` | `dim_item[item_code]` |
| `fact_voids[txn_date]` | `dim_date[date]` |
| `fact_voids[branch_code]` | `dim_branch[branch_code]` |
| `fact_voids[item_code]` | `dim_item[item_code]` |
| `fact_opex[month_start]` | `dim_date[date]` |
| `fact_opex[branch_code]` | `dim_branch[branch_code]` |
| `fact_opex[account_code]` | `dim_account[account_code]` |
| `fact_budget[month_start]` | `dim_date[date]` |
| `fact_budget[branch_code]` | `dim_branch[branch_code]` |

- **No fact joins to another fact.** Sales, costs and budget only meet through the shared dimensions, which is what lets one branch or month filter work on all of them.
- **Single direction only.** Filters flow from dimensions to facts. Two-way filters can give ambiguous results and are not needed here.
- **`dim_date` is marked as the date table**, so the year on year measures use the fiscal calendar built in SQL.

## Step 8: DAX measures

All measures live in one table called `_Measures`. Each batch is tested in DAX query view against figures worked out separately in SQL before it is saved into the model.

### Base measures

| Measure | DAX |
| --- | --- |
| Sales | `SUM ( fact_sales[net_sales_excl] )` |
| Cost of Sales | `SUM ( fact_sales[cost_of_sales_excl] )` |
| Gross Profit | `SUM ( fact_sales[gross_profit] )` |
| GP % | `DIVIDE ( [Gross Profit], [Sales] )` |
| Opex | `CALCULATE ( SUM ( fact_opex[amount_excl] ), dim_account[is_in_ebitda] = TRUE () )` |
| EBITDA | `[Gross Profit] - [Opex]` |

Test: Sales, Gross Profit, Opex and EBITDA by financial year in Power BI equal finance's control totals to the cent, the same as the warehouse.

### Budget and last year

| Measure | What it does |
| --- | --- |
| Budget Sales | Budget rows where the measure is "Sales excl VAT" |
| Budget GP | Budget rows where the measure is "Gross profit" |
| Sales vs Budget % | (Sales less Budget Sales) divided by Budget Sales |
| GP vs Budget % | (Gross Profit less Budget GP) divided by Budget GP |
| Sales LY | Sales for the same dates one year earlier |
| GP LY | Gross Profit for the same dates one year earlier |
| Sales Growth % | (Sales less Sales LY) divided by Sales LY |
| GP % LY | GP LY divided by Sales LY |

```
Sales LY =
VAR LastSaleDate = CALCULATE ( MAX ( fact_sales[txn_date] ), REMOVEFILTERS () )
RETURN
    CALCULATE (
        [Sales],
        DATEADD ( FILTER ( VALUES ( dim_date[date] ), dim_date[date] <= LastSaleDate ), -1, YEAR )
    )
```

**Why the last sale date matters.** The data stops at the end of August 2026 but the calendar runs to February 2027. Without the `LastSaleDate` filter, FY27 (six months of sales) would be compared with all twelve months of FY26 and show a large fake decline. With it, FY27 H1 is compared with FY26 H1.

Test, Power BI against SQL:

| Period | Sales | Budget Sales | vs Budget | Sales LY | Growth |
| --- | ---: | ---: | ---: | ---: | ---: |
| FY25 | 12,926,995.45 | 13,266,000 | -2.6% | none | none |
| FY26 | 14,893,335.92 | 15,138,500 | -1.6% | 12,926,995.45 | 15.2% |
| FY27 H1 | 8,171,216.44 | 8,226,500 | -0.7% | 6,833,006.03 | 19.6% |

FY25 has no last year figure because there is no FY24 data. It shows as blank, not zero.

### Store KPIs

| Measure | Definition |
| --- | --- |
| Transactions | Distinct `txn_id` where the type is SALE. Refunds are not counted as transactions |
| Average Ticket | Sales divided by Transactions |
| Discount % | Discount divided by gross sales (before discount) |
| Void Value | Value of voided lines, excl VAT |
| Void % | Void Value divided by Sales |
| Labour % | Salaries and wages (account 6000) divided by Sales |
| Drink Attach % | Share of transactions that include at least one drink |
| EBITDA % | EBITDA divided by Sales |

The ledger is monthly, so Labour % and EBITDA % are only meaningful by month or longer, not by week.

Test, Power BI against SQL:

| Period | Transactions | Average Ticket | Discount % | Void % | Labour % | Drink Attach % | EBITDA % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FY25 | 122,684 | 105.37 | 2.0% | 1.3% | 23.4% | 47.1% | 14.6% |
| FY26 | 134,462 | 110.76 | 1.9% | 1.3% | 23.1% | 46.9% | 14.0% |
| FY27 H1 | 71,381 | 114.47 | 1.8% | 1.3% | 22.9% | 47.1% | 14.5% |

### Like-for-like

**Rule:** a store counts as like-for-like for a period if it was already open at the start of the same period one year earlier, and was still open at the end of the period. Stores that opened or closed in between are left out of both years.

Measures: `LFL Stores`, `LFL Sales`, `LFL Sales LY`, `LFL Growth %`. The rule is worked out from `open_date` and `close_date` in `dim_branch` for whatever period is on screen, so it works for a year, a quarter or a month without any hard-coded store list.

Test, Power BI against SQL:

| Period | LFL stores | LFL Sales | LFL Sales LY | LFL growth | Total growth |
| --- | ---: | ---: | ---: | ---: | ---: |
| FY26 | 9 | 13,266,743.58 | 12,067,043.18 | 9.9% | 15.2% |
| FY27 H1 | 9 | 6,901,298.30 | 6,264,003.03 | 10.2% | 19.6% |

Total sales grew 15% and 20%, but the same nine stores grew about 10%. The rest came from opening Ballito and Hilton, net of closing Northdale.

### Margin and mix

| Measure | Definition |
| --- | --- |
| Opex % | Opex divided by Sales |
| Units | Sum of quantity sold. Refunds reduce it |
| Avg Selling Price | Gross sales excl VAT divided by Units |
| Avg Unit Cost | Cost of Sales divided by Units |
| Sales Mix % | Sales for the item or category divided by Sales for all items |

Test, Power BI against SQL:

| Month | Avg Selling Price | Avg Unit Cost | GP % |
| --- | ---: | ---: | ---: |
| Mar 2025 | 45.71 | 19.21 | 57.1% |
| Apr 2025 | 45.14 | 20.47 | 53.7% |
| Jul 2025 | 47.82 | 20.64 | 56.0% |

## Step 9: the report pages

All four pages required by the brief are in `flame_yard.pbix`. The year slicer is synced across the pages that use it, so two pages never quietly show different years.

| Page | What is on it | Business question |
| --- | --- | --- |
| Executive summary | Year slicer. Cards for Sales, Gross Profit, GP %, EBITDA, Sales vs Budget %, Sales Growth % and LFL Growth %. Sales by month against budget and last year. EBITDA by branch | 1 and 2 |
| Branch performance | Year slicer. One row per branch with Sales, vs Budget, Growth, GP %, Discount %, Opex %, Labour %, EBITDA and EBITDA %, with low GP % and high Opex % shaded red. Each cost type as a share of sales per branch | 3 |
| Margin and product mix | No year filter, so all 30 months show. GP % by month. Average selling price against average unit cost by month. Sales, mix and GP % by category | 4 |
| Branch P&L | Year and branch slicers. Monthly P&L from Sales down to EBITDA. Operating costs by account by month | 1 and 5 |

Figures on every page were checked against SQL on the warehouse while it was built.

## Step 10: the Excel check

An independent check that the report is right. The FY26 branch P&L is rebuilt in Excel from the warehouse, without Power BI and without any DAX measure, and compared with the Branch P&L page.

**How it works.** `06_excel_data.py` queries the warehouse with SQL and writes one row per branch, month and P&L line to `excel/fy26_branch_pl_data.xlsx` (1,152 rows). Sales are positive and every cost is negative, so adding up any group of rows gives its profit: Sales plus Cost of sales is Gross Profit, and all rows together are EBITDA.

**The pivot.** `excel/fy26_branch_pl_check.xlsx` has a pivot table on the `pivot` sheet: `pl_group` and `pl_line` in Rows, `branch_name` in Columns, Sum of `amount` in Values. It was built by hand in Excel for the web.

**Result.** The pivot and the Power BI report agree.

| FY26, all branches | Excel pivot | Power BI | Finance |
| --- | ---: | ---: | ---: |
| Gross Profit | 8,278,456.34 | 8,278,456.34 | 8,278,456.34 |
| Operating expenses | 6,199,802.50 | 6,199,802.50 | |
| EBITDA | 2,078,653.84 | 2,078,653.84 | 2,078,653.84 |

Per branch they agree as well, for example Musgrave EBITDA of 11,931.79 in both. Northdale shows minus 3,689.02 in Excel and minus 3,689.01 in Power BI. The one cent is because the export rounds each row to two decimals before Excel adds them up.

## What the report shows

These are the first readings from the pages. The findings summary will set them out properly.

- **Growth (question 2).** Sales grew 15.2% in FY26 and 19.6% in FY27 H1, but the same nine stores grew 9.9% and 10.2%. The rest came from new stores.
- **Underperformers (question 3).** Musgrave has healthy sales (R1.29m in FY26) but an EBITDA of only R12k, because costs take 55% of sales against about 39% elsewhere. The cause is salaries (32% of sales against about 21%) and rent (14% against about 9%). Pinetown has the third-highest sales but a GP % of 50.4% against about 56% elsewhere, because it gives away 12% of gross sales in discounts.
- **Margin dip (question 4).** GP % was 57.1% until March 2025, fell to 53.7% for April to June 2025, and has been 56.0% since July 2025. Unit costs rose about 8% on 1 April 2025 and selling prices only rose on 1 July 2025. It has recovered most of the way but is still about one point lower.
- **Northdale (question 5).** Sales fell from R70k to R80k a month in 2024 to R47k to R63k a month in 2025. It missed its sales budget by 15% to 23% in every month. In its last seven months it lost money in four and made a total of minus R3.7k. The data supports the closure.
- **Mix.** Chicken is 51% of sales. Sides earn the highest margin (69%) and drinks the lowest (41%).

## Definitions and decisions

- **Financial year:** 1 March to the end of February. FY26 is March 2025 to February 2026.
- **Net sales:** quantity x price, less discount, excl VAT. Refunds reduce sales. Voids and test transactions are excluded.
- **EBITDA:** Gross Profit less operating expenses (accounts 6000 to 6600). Depreciation and interest are excluded.
- **Duplicated days:** 26 to 28 February 2025 appear in both the FY25 and FY26 files. One copy is kept and they count in FY25, where the dates fall.
