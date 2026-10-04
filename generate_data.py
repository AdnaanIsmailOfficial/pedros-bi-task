"""
Generates the dummy source extracts for the BI work sample.

Everything here is synthetic: a made-up 12-store flame-grilled chicken franchise
group ("Flame Yard Chicken"). No real company, customer or trading data is used.
The extracts are deliberately dirty: see TASK.md for the warning, not this file.

Run:  python generate_data.py      (standard library only, about a minute)
"""
import csv
import datetime as dt
import os
import random

random.seed(20261004)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)

START, END = dt.date(2024, 3, 1), dt.date(2026, 8, 31)
VAT = 1.15

# code, name, region, ownership, open, close, tills, base txns/day, profile, attach, disc_prob, disc_pct
BRANCHES = [
    ("DBN01", "Umhlanga",       "Durban North", "Company",   None,                None,               6, 30, "premium",  0.42, 0.06, 0.08),
    ("DBN02", "Durban North",   "Durban North", "Company",   None,                None,               5, 31, "standard", 0.33, 0.07, 0.08),
    ("DBN03", "Musgrave",       "Durban Central", "Company", None,                None,               5, 27, "standard", 0.30, 0.07, 0.08),
    ("DBN04", "Westville",      "Durban West",  "Franchise", None,                None,               4, 29, "standard", 0.36, 0.06, 0.08),
    ("DBN05", "Pinetown",       "Durban West",  "Franchise", None,                None,               5, 38, "standard", 0.25, 0.55, 0.22),
    ("DBN06", "Amanzimtoti",    "Durban South", "Franchise", None,                None,               4, 22, "standard", 0.28, 0.08, 0.08),
    ("DBN07", "Ballito",        "Durban North", "Company",   dt.date(2025, 6, 2), None,               5, 28, "premium",  0.40, 0.06, 0.08),
    ("DBN08", "Chatsworth",     "Durban South", "Franchise", None,                None,               6, 46, "express",  0.14, 0.08, 0.08),
    ("PMB01", "PMB Victoria Rd","Pietermaritzburg", "Company", None,              None,               5, 33, "standard", 0.31, 0.07, 0.08),
    ("PMB02", "Hayfields",      "Pietermaritzburg", "Company", None,              None,               4, 25, "standard", 0.34, 0.06, 0.08),
    ("PMB03", "Hilton",         "Pietermaritzburg", "Franchise", dt.date(2025, 11, 3), None,          3, 19, "premium",  0.38, 0.06, 0.08),
    ("PMB04", "Northdale",      "Pietermaritzburg", "Franchise", None,            dt.date(2025, 9, 30), 4, 24, "express", 0.18, 0.10, 0.10),
]

# code, description, category, list price incl VAT (Mar 2024), cost ex VAT (Mar 2024), base weight
ITEMS = [
    ("CH01", "Quarter Chicken",            "Chicken",  49.90,  17.50, 22),
    ("CH02", "Quarter Chicken and Chips",  "Chicken",  69.90,  24.50, 26),
    ("CH03", "Half Chicken",               "Chicken",  89.90,  33.00, 10),
    ("CH04", "Half Chicken and Chips",     "Chicken", 109.90,  40.00, 12),
    ("CH05", "Full Chicken",               "Chicken", 159.90,  62.00, 8),
    ("CH06", "6 Wings",                    "Chicken",  64.90,  24.00, 7),
    ("CH07", "12 Wings",                   "Chicken", 119.90,  46.00, 3),
    ("CH08", "Livers and Roll",            "Chicken",  44.90,  13.00, 5),
    ("BG01", "Chicken Burger",             "Burgers",  54.90,  19.00, 12),
    ("BG02", "Chicken Burger Meal",        "Burgers",  79.90,  28.00, 12),
    ("BG03", "Chicken Wrap",               "Burgers",  59.90,  21.00, 7),
    ("BG04", "Chicken Prego Roll",         "Burgers",  49.90,  17.00, 5),
    ("FM01", "Family Feast",               "Family",  249.90,  96.00, 4),
    ("FM02", "Mega Family Feast",          "Family",  399.90, 152.00, 1.5),
    ("SD01", "Regular Chips",              "Sides",    24.90,   6.50, 30),
    ("SD02", "Large Chips",                "Sides",    34.90,   9.00, 18),
    ("SD03", "Spicy Rice",                 "Sides",    22.90,   5.50, 14),
    ("SD04", "Coleslaw",                   "Sides",    19.90,   5.00, 12),
    ("SD05", "Portuguese Roll",            "Sides",     6.90,   2.20, 16),
    ("SD06", "Pap and Gravy",              "Sides",    19.90,   4.50, 10),
    ("DR01", "Soft Drink 330ml",           "Drinks",   17.90,   8.20, 35),
    ("DR02", "Soft Drink 500ml",           "Drinks",   21.90,  10.40, 30),
    ("DR03", "Soft Drink 2L",              "Drinks",   34.90,  19.50, 15),
    ("DR04", "Still Water 500ml",          "Drinks",   14.90,   5.80, 20),
    ("EX01", "Peri Sauce Bottle 250ml",    "Extras",   44.90,  21.00, 30),
    ("EX02", "Sauce Tub",                  "Extras",    5.90,   1.60, 70),
]
BOUGHT_IN = ("Drinks", "Extras")
PROFILE = {  # multiplier on the weight of each main-meal category
    "standard": {"Chicken": 1.0, "Burgers": 1.0, "Family": 1.0},
    "premium":  {"Chicken": 1.0, "Burgers": 0.8, "Family": 2.6},
    "express":  {"Chicken": 1.1, "Burgers": 1.4, "Family": 0.3},
}
DOW = [0.80, 0.80, 0.86, 0.95, 1.30, 1.40, 1.20]          # Mon..Sun
SEASON = {1: 0.88, 2: 0.93, 3: 1.0, 4: 1.02, 5: 0.97, 6: 0.94, 7: 0.96, 8: 0.98, 9: 1.03, 10: 1.05, 11: 1.08, 12: 1.30}
HOURS = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
HOUR_W = [2, 4, 9, 15, 15, 8, 5, 6, 11, 14, 11, 5]
PAY = ["Card", "Card", "Card", "Cash", "Cash", "Delivery app"]


def price_on(item, day):
    code, _, cat, price, _, _ = item
    if cat in BOUGHT_IN:
        return round(price * 1.05) - 0.10 if day >= dt.date(2026, 3, 1) else price
    if day >= dt.date(2025, 7, 1):
        return round(price * 1.06) - 0.10
    return price


def cost_rows():
    rows = []
    for code, _, cat, _, cost, _ in ITEMS:
        rows.append((code, dt.date(2024, 3, 1), round(cost, 2)))
        c2 = round(cost * 1.08, 2)
        rows.append((code, dt.date(2025, 4, 1), c2))
        if cat in BOUGHT_IN:
            rows.append((code, dt.date(2026, 3, 1), round(c2 * 1.06, 2)))
    return rows


def fy_of(day):
    return day.year + 1 if day.month >= 3 else day.year


def dirty_branch(code):
    r = random.random()
    if r < 0.012:
        return code.lower()
    if r < 0.022:
        return code + " "
    if r < 0.030:
        return code[:3] + "-" + code[3:]
    return code


def months_between(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month)


def main():
    mains = [i for i in ITEMS if i[2] in PROFILE["standard"]]
    sides = [i for i in ITEMS if i[2] == "Sides"]
    drinks = [i for i in ITEMS if i[2] == "Drinks"]
    extras = [i for i in ITEMS if i[2] == "Extras"]
    pick = lambda group: random.choices(group, [i[5] for i in group])[0]

    files, writers = {}, {}
    header = ["txn_id", "line_no", "txn_datetime", "branch_code", "cashier", "item_code",
              "qty", "unit_price_incl", "discount_incl", "payment_type", "txn_type"]
    for name in ("FY25", "FY26", "FY27_H1"):
        f = open(os.path.join(OUT, f"pos_sales_{name}.csv"), "w", newline="", encoding="utf-8")
        w = csv.writer(f)
        w.writerow(header)
        files[name], writers[name] = f, w

    def emit(day, row_tail, ts):
        fy = fy_of(day)
        name = {2025: "FY25", 2026: "FY26", 2027: "FY27_H1"}[fy]
        if name == "FY25":
            stamp = ts.strftime("%d/%m/%Y %H:%M")
        else:
            stamp = ts.strftime("%Y-%m-%d %H:%M:%S")
        writers[name].writerow(row_tail[:2] + [stamp] + row_tail[2:])
        # the FY26 extract was pulled with a start date three days too early
        if dt.date(2025, 2, 26) <= day <= dt.date(2025, 2, 28):
            writers["FY26"].writerow(row_tail[:2] + [ts.strftime("%Y-%m-%d %H:%M:%S")] + row_tail[2:])

    txn_seq = 0
    day = START
    while day <= END:
        for (code, _, _, _, opened, closed, _, base, profile, attach, dprob, dpct) in BRANCHES:
            if opened and day < opened:
                continue
            if closed and day > closed:
                continue
            m = months_between(START, day)
            trend = 1.005 ** m
            if code == "PMB04":
                trend = 0.972 ** max(0, months_between(dt.date(2024, 8, 1), day))
            if opened:
                age = (day - opened).days
                trend = (0.5 + 0.5 * min(1.0, age / 120.0)) * 1.006 ** max(0, months_between(opened, day))
            payday = 1.15 if (day.day >= 25 or day.day <= 2) else 1.0
            mean = base * DOW[day.weekday()] * SEASON[day.month] * trend * payday
            n = max(0, int(round(random.gauss(mean, mean ** 0.5))))
            mn_w = [i[5] * PROFILE[profile][i[2]] for i in mains]
            for _ in range(n):
                txn_seq += 1
                txn_id = f"T{txn_seq:07d}"
                ts = dt.datetime.combine(day, dt.time(random.choices(HOURS, HOUR_W)[0], random.randrange(60), random.randrange(60)))
                cashier = f"C{code[-2:]}{random.randint(1, 4)}"
                pay = random.choice(PAY)
                lines = []
                if random.random() < 0.04:
                    lines.append((pick(drinks), random.choice([1, 1, 2])))
                else:
                    lines.append((random.choices(mains, mn_w)[0], 1))
                    if random.random() < 0.22:
                        lines.append((random.choices(mains, mn_w)[0], 1))
                    if random.random() < attach + 0.12:
                        lines.append((pick(sides), random.choice([1, 1, 2])))
                    if random.random() < 0.45:
                        lines.append((pick(drinks), random.choice([1, 1, 2])))
                    if random.random() < 0.06:
                        lines.append((pick(extras), 1))
                disc = dpct * random.uniform(0.6, 1.4) if random.random() < dprob else 0.0
                r = random.random()
                ttype = "VOID" if r < 0.012 else ("REFUND" if r < 0.020 else "SALE")
                sign = -1 if ttype == "REFUND" else 1
                for ln, (it, q) in enumerate(lines, 1):
                    p = price_on(it, day)
                    d = round(p * q * disc, 2)
                    emit(day, [txn_id, ln, dirty_branch(code), cashier, it[0], sign * q,
                               f"{p:.2f}", f"{sign * d:.2f}", pay, ttype], ts)
        # till testing by the POS vendor, never real trade
        if random.random() < 0.035:
            txn_seq += 1
            code = random.choice(BRANCHES)[0]
            ts = dt.datetime.combine(day, dt.time(6, random.randrange(60), 0))
            it = random.choice(mains)
            if random.random() < 0.3:
                emit(day, [f"T{txn_seq:07d}", 1, code, "TEST", "ZZTEST", 1, "1.00", "0.00", "Cash", "SALE"], ts)
            else:
                emit(day, [f"T{txn_seq:07d}", 1, code, "TEST", it[0], 1, f"{price_on(it, day):.2f}", "0.00", "Cash", "SALE"], ts)
        day += dt.timedelta(days=1)
    for f in files.values():
        f.close()

    with open(os.path.join(OUT, "branches.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["branch_code", "branch_name", "region", "ownership", "open_date", "close_date", "tills"])
        for b in BRANCHES:
            w.writerow([b[0], b[1], b[2], b[3], b[4] or "2021-03-01", b[5] or "", b[6]])

    with open(os.path.join(OUT, "item_master.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item_code", "description", "category", "list_price_incl", "active"])
        for i, it in enumerate(ITEMS):
            cat = it[2]
            if it[0] in ("SD03", "SD05"):
                cat = "SIDES"
            if it[0] == "DR02":
                cat = "drinks "
            desc = it[1] + ("  " if i % 7 == 0 else "")
            w.writerow([it[0], desc, cat, f"{price_on(it, END):.2f}", "Y"])
        w.writerow(["CH02", "Quarter Chicken and Chips", "Chicken", "72.90", "Y"])   # catalogue duplicate
        w.writerow(["CH09", "Chicken Strips (discontinued)", "Chicken", "59.90", "N"])

    with open(os.path.join(OUT, "item_cost_history.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item_code", "effective_from", "unit_cost_excl"])
        for code, eff, cost in cost_rows():
            w.writerow([code, eff.isoformat(), f"{cost:.2f}"])


if __name__ == "__main__":
    main()
    print("POS, branch and item extracts written to", OUT)
