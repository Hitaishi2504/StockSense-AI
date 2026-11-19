"""Sample INVENTORY data (clearly flagged is_sample=1). Completely separate from the
store/department sales CSV used for forecasting.

Product names, categories, suppliers and prices come from the grocery CSV if present.
Dates are generated relative to TODAY, because the CSV's own dates are inconsistent
(about half its rows expire before they were received)."""
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from backend import db
from backend.config import Config

SHELF_LIFE_DAYS = {"Dairy": 28, "Fruits & Vegetables": 14, "Seafood": 8, "Bakery": 9,
                   "Beverages": 180, "Grains & Pulses": 365, "Oils & Fats": 270}

FALLBACK = [  # used only if the grocery CSV is not in the data folder
    ("Full Cream Milk 1L", "Dairy", 60, 25, "Amul Dairy", 2.1), ("Paneer 200g", "Dairy", 25, 10, "Amul Dairy", 3.5),
    ("Curd 500g", "Dairy", 40, 15, "Mother Dairy", 1.2), ("Tomato", "Fruits & Vegetables", 80, 30, "Local Farms", 0.9),
    ("Banana", "Fruits & Vegetables", 70, 25, "Local Farms", 0.6), ("Spinach", "Fruits & Vegetables", 30, 12, "Local Farms", 0.7),
    ("Brown Bread", "Bakery", 35, 15, "Daily Bakers", 1.4), ("Basmati Rice 5kg", "Grains & Pulses", 50, 15, "Agro Foods", 9.0),
    ("Toor Dal 1kg", "Grains & Pulses", 45, 15, "Agro Foods", 3.2), ("Sunflower Oil 1L", "Oils & Fats", 40, 15, "Oil Mills Ltd", 3.0),
    ("Orange Juice 1L", "Beverages", 30, 10, "Fresh Drinks", 2.5), ("Rohu Fish 1kg", "Seafood", 18, 8, "Coastal Fisheries", 6.0),
]


def _price(v):
    return float(str(v).replace("$", "").replace(",", "").strip())


def _source_rows(limit):
    path = Path(Config.DATA_DIR) / "Grocery_Inventory_and_Sales_Dataset.csv"
    if not path.exists():
        return [dict(name=n, category=c, stock=s, minimum=m, supplier=sup, price=p) for n, c, s, m, sup, p in FALLBACK]
    g = pd.read_csv(path)
    g = g.rename(columns={"Catagory": "Category"})      # the CSV header is misspelled
    g = g.dropna(subset=["Category", "Product_Name"]).drop_duplicates("Product_Name")
    g = g[g["Category"].isin(SHELF_LIFE_DAYS)].sample(frac=1, random_state=11)
    # round-robin across categories so the sample has a good mix
    picked, per = [], {c: [] for c in SHELF_LIFE_DAYS}
    for _, r in g.iterrows():
        per[r["Category"]].append(r)
    slots = [c for c, k in (("Grains & Pulses", 2), ("Beverages", 2), ("Oils & Fats", 2), ("Dairy", 2),
                            ("Fruits & Vegetables", 1), ("Bakery", 1), ("Seafood", 1)) for _ in range(k)]
    while len(picked) < limit and any(per.values()):
        for c in slots:
            if per[c] and len(picked) < limit:
                picked.append(per[c].pop())
    return [dict(name=r["Product_Name"], category=r["Category"], stock=int(r["Stock_Quantity"]),
                 minimum=int(r["Reorder_Level"] * 0.6) + 5, supplier=r["Supplier_Name"],
                 price=_price(r["Unit_Price"])) for r in picked]


def seed(limit=60, force=False):
    if not force and db.query("SELECT COUNT(*) AS n FROM products", one=True)["n"] > 0:
        return "Products already exist - sample data not added (use --force to add anyway)."
    rnd = random.Random(7)
    today = date.today()
    n_prod = n_sales = 0
    for row in _source_rows(limit):
        life = SHELF_LIFE_DAYS[row["category"]]
        age = rnd.uniform(0.0, 1.18)                     # fraction of shelf life already used
        expiry = today + timedelta(days=round(life * (1 - age)))
        mfg = expiry - timedelta(days=life)
        sell = round(max(0.2, row["price"]), 2)
        buy = round(sell * rnd.uniform(0.55, 0.80), 2)
        sup = db.query("SELECT supplier_id FROM suppliers WHERE name = %s", (row["supplier"],), one=True)
        sid = sup["supplier_id"] if sup else db.execute("INSERT INTO suppliers (name) VALUES (%s)", (row["supplier"],))[0]
        added = today - timedelta(days=45)
        pid, _ = db.execute(
            "INSERT INTO products (product_name, category, stock_quantity, purchase_price, selling_price, supplier_id, "
            "manufacturing_date, expiry_date, min_stock_level, date_added, is_sample) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)",
            (row["name"], row["category"], row["stock"], buy, sell, sid, mfg, expiry, row["minimum"], added))
        n_prod += 1
        lam = max(0.5, row["minimum"] / 14 * rnd.uniform(0.6, 1.6))
        day = max(mfg, added)
        last = min(expiry, today - timedelta(days=1))
        while day <= last:
            if rnd.random() < 0.85:
                qty = max(1, int(round(rnd.gauss(lam, lam ** 0.5))))
                db.execute("INSERT INTO sales (product_id, quantity_sold, sale_date, selling_price, is_sample) "
                           "VALUES (%s,%s,%s,%s,1)", (pid, qty, day, sell))
                n_sales += 1
            day += timedelta(days=1)
    return f"Added {n_prod} sample products and {n_sales} sample sales rows (all flagged as sample)."
