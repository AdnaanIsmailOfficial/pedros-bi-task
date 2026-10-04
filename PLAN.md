# Plan

Written before any pipeline code. Updated only when a decision changes, with the reason.

## What each business question needs

| # | Question | Needs from the data |
| --- | --- | --- |
| 1 | Sales, GP and EBITDA by group and branch, against budget and last year | Clean sales lines with cost attached, ledger costs per branch and month, the budget at the same grain, and a fiscal calendar starting in March |
| 2 | Like-for-like growth against total growth | Branch open and close dates, so a branch only counts if it traded through both periods |
| 3 | Which branches underperform, and why | Sales, GP % and each cost line as a share of sales per branch, so the cause can be separated into sales, margin or costs |
| 4 | The 2025 dip in GP % | Unit price and unit cost over time per item, plus discount per line |
| 5 | Whether closing Northdale was right | Monthly branch P&L for PMB04 up to closure: sales trend, EBITDA and performance against budget |
| 6 | Weekly store KPIs | Transaction counts, average ticket, discount %, attach rate, labour %, and void and refund activity per branch per week |

## Tables I expect to end up with

- **Raw:** one table per extract, loaded as text, never edited.
- **Staging:** `stg_sales`, `stg_items`, `stg_costs`, `stg_branches`, `stg_gl`, `stg_budget`. Types fixed, codes standardised, bad rows removed, each rule commented.
- **Facts:** `fact_sales` (one row per POS line, excl VAT, with cost), `fact_opex` (branch, month, account), `fact_budget` (branch, month, measure).
- **Dimensions:** `dim_date` (with fiscal year and period), `dim_branch`, `dim_item`, `dim_account`.

All cleaning happens in SQL in the warehouse. Power BI only models and measures.

## How I will know the numbers are right

1. **Control totals.** Sales, GP and EBITDA per financial year must match `finance_control_totals.csv` to the rand. If they do not, the data is not clean yet and I do not move on.
2. **Automated checks.** At least 6, run at the end of every pipeline run, and the run fails if any check fails. Unique keys, no orphan codes, no rows lost or doubled in joins, no nulls in money columns.
3. **Idempotence.** Run the pipeline twice and compare row counts and totals. They must be identical.
4. **Measure tests.** Each DAX measure checked against a SQL query for one branch and one month.
5. **Independent check.** An Excel pivot of the FY26 branch P&L built from the marts, compared to the Power BI figures.

## Assumptions and open decisions

- Financial year runs March to February, as stated in the brief.
- Definitions I must decide during profiling and write down here: how refunds and voids are treated, which ledger accounts sit above the EBITDA line, and the exact rule for like-for-like.
- Tools: Python and DuckDB for the pipeline, Power BI Desktop for the report, Excel for the check.

## Order of work

Day 1: profile, land, clean, model, check, reconcile. Day 2: Power BI model, measures, first two pages. Day 3: remaining pages, Excel check, findings, README.
