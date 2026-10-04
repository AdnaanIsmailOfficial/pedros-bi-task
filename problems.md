# Data problems found

Found by profiling the raw extracts with `explore.py`, before any cleaning. Nothing has been fixed yet. Each entry says what is wrong, how it was spotted and what the fix will be.

The proof that this list is complete enough: with problems 1 to 5 handled, FY25 sales from the POS come to R12,926,995, which matches finance's control total of R12,926,995.45.

## Sales files (POS)

### 1. Branch codes are written four different ways
- **Spotted:** counted distinct `branch_code`. Expected 12, got 48.
- **Saw:** `DBN01` (70,316 lines), `dbn01` (899), `DBN01 ` with a space on the end (732), `DBN-01` (595). Same pattern for every branch.
- **Risk:** each store's sales split over four rows, and most variants do not match the branch list.
- **Fix:** trim, upper case, remove the dash.

### 2. Voided transactions are in the data
- **Spotted:** grouped by `txn_type`.
- **Saw:** 8,681 VOID lines worth R525,547 incl VAT. They have normal positive quantities, so they look like sales.
- **Risk:** sales overstated by transactions that were cancelled at the till.
- **Fix:** exclude VOID from sales. Keep them in a separate table for a void-rate KPI.

### 3. Refunds are negative lines
- **Spotted:** same query. REFUND lines have quantity -1 or -2.
- **Saw:** 5,702 lines worth -R344,576 incl VAT.
- **Risk:** dropping them, or taking the absolute value, overstates sales.
- **Fix:** keep them as negatives so they reduce sales. Decision recorded in PLAN.md.

### 4. Test transactions from a TEST cashier
- **Spotted:** listed cashiers by line count. Every real cashier has over 7,000 lines; `TEST` has 35.
- **Saw:** all rung up around 06:00, before stores open. 8 of them use item `ZZTEST` at R1.00, which is not in the item master. Some are dated before the store had opened (DBN07 shows a "sale" in July 2024 but opened in June 2025).
- **Risk:** small in rand terms, but it creates an orphan item and makes stores look like they traded before they existed.
- **Fix:** remove every line where cashier is TEST.

### 5. Prices and discounts include VAT
- **Spotted:** column names end in `_incl`, then confirmed against finance. POS FY25 as-is is R14,866,045. Divided by 1.15 it is R12,926,995, which is finance's number.
- **Risk:** every Sales and GP figure overstated by 15%. Cost is excl VAT, so GP % would also be wrong.
- **Fix:** divide price and discount by 1.15 in the warehouse.

### 6. The same three days are in two files
- **Spotted:** checked whether `txn_id` + `line_no` is unique. 705,890 lines, 703,682 unique, so 2,208 duplicates.
- **Saw:** all 2,208 are from 26 to 28 February 2025, and appear in both the FY25 and FY26 files. The FY26 extract was pulled starting three days early.
- **Risk:** three days of sales counted twice, split across two financial years.
- **Trap:** a plain `SELECT DISTINCT` does not remove them (still 705,890 rows), because the two files write the date differently.
- **Fix:** keep one row per `txn_id` + `line_no`.

### 7. Two different date formats
- **Spotted:** looked at an example date and the text length per file.
- **Saw:** FY25 uses `01/01/2025 09:01` (day first, no seconds). FY26 and FY27 use `2025-02-26 09:01:54`.
- **Risk:** a tool that guesses the format can read 03/04/2024 as 4 March instead of 3 April, with no error.
- **Fix:** parse each format explicitly, never let the tool guess.

## Item files

### 8. An item is in the catalogue twice
- **Spotted:** looked for item codes that appear more than once in `item_master.csv`.
- **Saw:** `CH02` Quarter Chicken and Chips, listed at R73.90 and again at R72.90.
- **Risk:** joining sales to items doubles every CH02 line (about 75,000 lines, the best seller). In Power BI the relationship would fail or become many-to-many.
- **Fix:** one row per item code in `dim_item`. Keep the row whose price matches what the tills charge (R73.90).

### 9. Categories and descriptions are typed inconsistently
- **Saw:** `Sides` and `SIDES`, `Drinks` and `drinks ` (lower case with a space). Four descriptions have spaces on the end. `CH09` is inactive and has never sold.
- **Risk:** a category chart would show Sides twice and Drinks twice.
- **Fix:** trim and standardise the case. Keep CH09 in the dimension, flagged inactive.

### 10. Cost changes over time
- **Spotted:** `item_cost_history.csv` has more than one row per item.
- **Saw:** every item's cost rose about 8% on 1 April 2025. Drinks and extras rose again on 1 March 2026. Selling prices only went up on 1 July 2025 (CH02 went from R69.90 to R73.90).
- **Risk:** using the latest cost for old sales understates past GP. It also hides the real story: for April to June 2025 costs were up and prices were not, so margin was squeezed.
- **Fix:** attach the cost that was in force on the sale date to each sales line.

## Ledger

### 11. The ledger extract includes lines that are below EBITDA
- **Spotted:** joined the ledger to the chart of accounts and looked at `pl_group`.
- **Saw:** account 7000 Depreciation (R1,027,207) and 7100 Interest (R110,688) sit alongside the operating expenses.
- **Risk:** summing the whole file as "costs" understates EBITDA by about R1.1m.
- **Fix:** flag each account as in or out of EBITDA in `dim_account`. Only 6000 to 6600 count.

### 12. Period is text, and one line is negative
- **Saw:** period is `2024/03`, not a date. One line is negative: DBN02, October 2025, Repairs and maintenance, -R18,500.
- **Decision:** convert the period to the first day of the month. The negative line looks like a credit (for example an insurance payout against a repair) and is kept. To confirm with finance.

## Budget

### 13. The budget is laid out sideways
- **Saw:** 24 rows (12 branches x 2 measures) and 30 month columns named `Mar-24` to `Aug-26`.
- **Risk:** cannot be joined to a date table or filtered by month in this shape.
- **Fix:** unpivot to one row per branch, measure and month, and turn the column name into a date.

## Branches

### 14. Not every store traded for the whole period
- **Spotted:** counted months traded per branch against the 30 months in the data.
- **Saw:** DBN07 Ballito opened 2 June 2025, PMB03 Hilton opened 3 November 2025, PMB04 Northdale closed 30 September 2025. The other nine traded all 30 months.
- **Risk:** total sales growth mixes real growth with new stores. This is the like-for-like question in the brief.
- **Fix:** nothing to clean. Handle it in the like-for-like measure using open and close dates.

## Not a data problem, but worth knowing

- DBN05 Pinetown gives 12.1% of gross sales away in discounts. Every other store is at 1% or less. This will show up in its GP %.
