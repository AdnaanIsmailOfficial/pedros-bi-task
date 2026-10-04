"""
Generates the dummy source extracts for the BI work sample.

Everything here is synthetic. Washr is modelled as a 12-branch group so that
store-level reporting (Sales, GP, EBITDA, like-for-like) has something to chew on.
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

# code, name, region, ownership, open, close, bays, base txns/day, profile, attach, disc_prob, disc_pct
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
    ("SV01", "Express Wash",            "Wash",    120,  16, 30),
    ("SV02", "Wash and Vac",            "Wash",    180,  24, 28),
    ("SV03", "Full Valet",              "Wash",    450,  62, 16),
    ("SV04", "Interior Detail",         "Detail",  650,  95, 6),
    ("SV05", "Exterior Detail",         "Detail",  750, 120, 5),
    ("SV06", "Full Detail",             "Detail", 1200, 190, 4),
    ("SV07", "Ceramic Coating",         "Detail", 4500, 1150, 0.6),
    ("SV08", "Paint Correction",        "Detail", 2800, 520, 0.8),
    ("SV09", "Headlight Restoration",   "Detail",  350,  55, 2),
    ("SV10", "Engine Bay Clean",        "Wash",    300,  38, 3),
    ("AD01", "Tyre Shine",              "Add-on",   40,   6, 30),
    ("AD02", "Air Freshener",           "Add-on",   25,   7, 25),
    ("AD03", "Wax Upgrade",             "Add-on",  150,  28, 20),
    ("AD04", "Leather Treatment",       "Add-on",  250,  45, 10),
    ("AD05", "Pet Hair Removal",        "Add-on",  180,  20, 8),
    ("AD06", "Odour Treatment",         "Add-on",  300,  48, 7),
    ("RT01", "Microfibre Cloth 3 Pack", "Retail",   99,  52, 25),
    ("RT02", "Car Shampoo 1L",          "Retail",  129,  71, 20),
    ("RT03", "Foam Cannon",             "Retail",  499, 310, 5),
    ("RT04", "Tyre Gel 500ml",          "Retail",   89,  47, 15),
    ("RT05", "Glass Cleaner 500ml",     "Retail",   79,  41, 15),
    ("RT06", "Wash Mitt",               "Retail",   69,  33, 10),
    ("RT07", "Dash Wipes",              "Retail",   59,  29, 8),
    ("RT08", "Pressure Washer Lance",   "Retail",  349, 228, 2),
]
PROFILE = {  # multiplier on the weight of each service category
    "standard": {"Wash": 1.0, "Detail": 1.0},
    "premium":  {"Wash": 0.7, "Detail": 2.3},
    "express":  {"Wash": 1.35, "Detail": 0.3},
}
DOW = [0.72, 0.78, 0.85, 0.95, 1.20, 1.65, 1.05]          # Mon..Sun
SEASON = {1: 0.86, 2: 0.92, 3: 1.0, 4: 1.02, 5: 0.97, 6: 0.90, 7: 0.92, 8: 0.98, 9: 1.04, 10: 1.06, 11: 1.10, 12: 1.32}
HOURS = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
HOUR_W = [3, 7, 11, 13, 14, 15, 15, 11, 7, 4]
PAY = ["Card", "Card", "Card", "Cash", "EFT", "Account"]


def price_on(item, day):
    code, _, cat, price, _, _ = item
    if cat == "Retail":
        return round(price * 1.05) if day >= dt.date(2026, 3, 1) else price
    if day >= dt.date(2025, 7, 1):
        return int(round(price * 1.06 / 5.0)) * 5
    return price


def cost_rows():
    rows = []
    for code, _, cat, _, cost, _ in ITEMS:
        if cat != "Retail":
            cost = cost * 2.0      # chemicals and consumables plus the detailer's per-job commission
        rows.append((code, dt.date(2024, 3, 1), round(cost, 2)))
        c2 = round(cost * 1.08, 2)
        rows.append((code, dt.date(2025, 4, 1), c2))
        if cat == "Retail":
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
    services = [i for i in ITEMS if i[0].startswith("SV")]
    addons = [i for i in ITEMS if i[0].startswith("AD")]
    retail = [i for i in ITEMS if i[0].startswith("RT")]

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
            sv_w = [i[5] * PROFILE[profile][i[2]] for i in services]
            for _ in range(n):
                txn_seq += 1
                txn_id = f"T{txn_seq:07d}"
                ts = dt.datetime.combine(day, dt.time(random.choices(HOURS, HOUR_W)[0], random.randrange(60), random.randrange(60)))
                cashier = f"C{code[-2:]}{random.randint(1, 4)}"
                pay = random.choice(PAY)
                lines = []
                if random.random() < 0.05:
                    lines.append((random.choices(retail, [i[5] for i in retail])[0], random.choice([1, 1, 1, 2])))
                else:
                    lines.append((random.choices(services, sv_w)[0], 1))
                    if random.random() < attach:
                        for it in random.sample(addons, random.choice([1, 1, 1, 2])):
                            lines.append((it, 1))
                    if random.random() < 0.09:
                        lines.append((random.choices(retail, [i[5] for i in retail])[0], 1))
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
            it = random.choice(services)
            if random.random() < 0.3:
                emit(day, [f"T{txn_seq:07d}", 1, code, "TEST", "ZZTEST", 1, "1.00", "0.00", "Cash", "SALE"], ts)
            else:
                emit(day, [f"T{txn_seq:07d}", 1, code, "TEST", it[0], 1, f"{price_on(it, day):.2f}", "0.00", "Cash", "SALE"], ts)
        day += dt.timedelta(days=1)
    for f in files.values():
        f.close()

    with open(os.path.join(OUT, "branches.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["branch_code", "branch_name", "region", "ownership", "open_date", "close_date", "wash_bays"])
        for b in BRANCHES:
            w.writerow([b[0], b[1], b[2], b[3], b[4] or "2021-03-01", b[5] or "", b[6]])

    with open(os.path.join(OUT, "item_master.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item_code", "description", "category", "list_price_incl", "active"])
        for i, it in enumerate(ITEMS):
            cat = it[2]
            if it[0] in ("AD03", "AD05"):
                cat = "ADD-ON"
            if it[0] == "RT04":
                cat = "retail "
            desc = it[1] + ("  " if i % 7 == 0 else "")
            w.writerow([it[0], desc, cat, f"{price_on(it, END):.2f}", "Y"])
        w.writerow(["SV02", "Wash and Vac", "Wash", "190.00", "Y"])       # catalogue duplicate
        w.writerow(["SV11", "Fleet Wash (discontinued)", "Wash", "95.00", "N"])

    with open(os.path.join(OUT, "item_cost_history.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item_code", "effective_from", "unit_cost_excl"])
        for code, eff, cost in cost_rows():
            w.writerow([code, eff.isoformat(), f"{cost:.2f}"])


if __name__ == "__main__":
    main()
    print("POS, branch and item extracts written to", OUT)
