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
| 3. Model | Star schema: facts and dimensions | Next |
| 4. Check | Automated data checks that stop the pipeline | To do |
| 5. Reconcile | Sales, GP and EBITDA against finance's control totals | Sales done, GP and EBITDA to do |
| 6. Export | Marts for Power BI | To do |
| 7. Report | Power BI model, measures and four pages | To do |

## How to run it

You need Python with the `duckdb` package (`pip install duckdb`). From this folder, run the scripts in order:

```
python explore.py        # optional: the profiling questions
python 01_land_raw.py    # builds warehouse.duckdb with the raw tables
python 02_stage.py       # builds the clean staging tables
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
| `warehouse.duckdb` | The warehouse. Not in git; the scripts rebuild it |

## The layers

1. **Raw (`raw_*`).** One table per extract, every column kept as text, never edited. Each row records which file it came from and when it was loaded. This means any number can be traced back to its source file.
2. **Staging (`stg_*`).** The cleaned version of each raw table: real data types, standard codes, bad rows removed. Each rule is commented in the SQL with the problem number it fixes.
3. **Marts (`fact_*`, `dim_*`).** The star schema that Power BI reads. Not built yet.

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

Gross Profit and EBITDA are reconciled after the star schema is built, because GP needs the cost attached to each sales line.

## Definitions and decisions

- **Financial year:** 1 March to the end of February. FY26 is March 2025 to February 2026.
- **Net sales:** quantity x price, less discount, excl VAT. Refunds reduce sales. Voids and test transactions are excluded.
- **EBITDA:** Gross Profit less operating expenses (accounts 6000 to 6600). Depreciation and interest are excluded.
- **Duplicated days:** 26 to 28 February 2025 appear in both the FY25 and FY26 files. One copy is kept and they count in FY25, where the dates fall.
