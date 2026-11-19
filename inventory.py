"""Core inventory calculations shared by every module: expiry status, stock status,
sales rate, units at risk. All rules are explicit so they can be explained to a user."""
import math
from datetime import date, timedelta

from .. import db
from ..db import to_date

DEFAULT_SETTINGS = {
    "store_name": "My Store",
    "lead_time_days": "7",            # days between ordering and delivery
    "cover_days": "14",               # how many days of sales a reorder should cover
    "assumed_cover_days": "14",       # ASSUMPTION used when a product has no sales history
    "basic_target_multiplier": "2",   # basic reorder: refill up to N x minimum stock
    "overstock_multiplier": "3",      # stock above N x minimum is 'Overstocked'
}
HISTORY_WINDOW_DAYS = 30
MIN_SALE_DAYS_FOR_HISTORY = 3   # need sales on >= 3 different days in the window to trust the rate


def get_settings():
    s = dict(DEFAULT_SETTINGS)
    for r in db.query("SELECT setting_key, setting_value FROM app_settings"):
        s[r["setting_key"]] = r["setting_value"]
    return s


def num(settings, key):
    return float(settings[key])


def sales_stats(today):
    """Per-product sales rate over the last 30 days, from the sales table (user-entered sales)."""
    start = today - timedelta(days=HISTORY_WINDOW_DAYS - 1)
    rows = db.query(
        "SELECT product_id, SUM(quantity_sold) AS units, COUNT(DISTINCT sale_date) AS sale_days, "
        "MIN(sale_date) AS first_sale FROM sales WHERE sale_date >= %s AND sale_date <= %s GROUP BY product_id",
        (start, today))
    return {r["product_id"]: r for r in rows}, start


def expiry_status(days):
    if days is None:
        return "Unknown"
    if days < 0:
        return "Expired"
    if days <= 7:
        return "Urgent"
    if days <= 30:
        return "Expiring Soon"
    return "Safe"


def stock_status(stock, minimum, overstock_mult):
    if stock <= 0:
        return "Out of Stock"
    if minimum > 0 and stock <= minimum * 0.5:
        return "Critical"
    if stock <= minimum:
        return "Low"
    if minimum > 0 and stock > minimum * overstock_mult:
        return "Overstocked"
    return "Adequate"


def load_products(today=None, settings=None):
    """All products with every derived field attached."""
    today = today or date.today()
    settings = settings or get_settings()
    stats, win_start = sales_stats(today)
    rows = db.query(
        "SELECT p.*, s.name AS supplier FROM products p LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id "
        "ORDER BY p.product_id")
    return [enrich(r, today, stats.get(r["product_id"]), win_start, settings) for r in rows]


def enrich(p, today, st, win_start, settings):
    for k in ("manufacturing_date", "expiry_date", "date_added"):
        p[k] = to_date(p.get(k))
    days = (p["expiry_date"] - today).days if p["expiry_date"] else None
    p["days_to_expiry"] = days
    p["expiry_status"] = expiry_status(days)
    p["stock_status"] = stock_status(p["stock_quantity"], p["min_stock_level"], num(settings, "overstock_multiplier"))
    p["margin_pct"] = round((p["selling_price"] - p["purchase_price"]) / p["selling_price"] * 100, 1) \
        if p["selling_price"] else 0.0

    # --- daily sales rate: real history if available, otherwise a LABELED assumption ---
    has_hist = bool(st and st["sale_days"] >= MIN_SALE_DAYS_FOR_HISTORY)
    if has_hist:
        first = to_date(st["first_sale"])
        start = max(win_start, min(p["date_added"] or today, first))
        obs_days = max(1, (today - start).days + 1)
        rate = st["units"] / obs_days
        p["units_30d"] = int(st["units"])
    else:
        rate = p["min_stock_level"] / max(1.0, num(settings, "assumed_cover_days"))
        p["units_30d"] = int(st["units"]) if st else 0
    p["daily_rate"] = round(rate, 2)
    p["rate_basis"] = "sales history" if has_hist else "assumption"
    p["has_history"] = has_hist

    # --- units at risk of expiring unsold ---
    stock = p["stock_quantity"]
    if days is None or stock <= 0:
        at_risk = 0
    elif days < 0:
        at_risk = stock
    elif days <= 30:
        at_risk = max(0, math.ceil(stock - rate * days))
    else:
        at_risk = 0
    p["units_at_risk"] = int(at_risk)
    p["value_at_risk"] = round(at_risk * p["purchase_price"], 2)
    ratio = at_risk / stock if stock else 0
    if stock <= 0 or days is None or days > 30:
        risk = "Low"
    elif days < 0:
        risk = "Expired"
    elif (days <= 7 and at_risk > 0) or ratio >= 0.5:
        risk = "High"
    elif at_risk > 0:
        risk = "Medium"
    else:
        risk = "Low"
    p["risk_level"] = risk
    return p
