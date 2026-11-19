from collections import Counter, defaultdict

from flask import Blueprint, jsonify

from .. import db
from ..config import Config
from ..services import expiry as ex
from ..services import inventory as inv

bp = Blueprint("dashboard", __name__, url_prefix="/api")


@bp.get("/dashboard")
def dashboard():
    products = inv.load_products()
    live = [p for p in products if p["stock_quantity"] > 0]
    es = ex.summary(products)
    low = [p for p in products if p["stock_status"] in ("Low", "Critical", "Out of Stock")]

    cat_units, cat_count = defaultdict(int), Counter()
    for p in products:
        cat_units[p["category"]] += p["stock_quantity"]
        cat_count[p["category"]] += 1
    risk = Counter(p["expiry_status"] for p in live)

    recent = db.query("SELECT s.sale_id, p.product_name, s.quantity_sold, s.sale_date, s.selling_price, s.is_sample "
                      "FROM sales s JOIN products p ON p.product_id = s.product_id "
                      "ORDER BY s.sale_date DESC, s.sale_id DESC LIMIT 8")

    predicted = {"available": False, "reason": "Model not trained yet."}
    try:
        from ml import forecast as fc
        total = fc.next_weeks_total(Config.DATA_DIR, Config.MODEL_DIR, 4)
        if total is not None:
            predicted = {"available": True, "next4_total": total}
    except Exception as e:  # dataset missing etc. - dashboard must still load
        predicted = {"available": False, "reason": str(e)}

    return jsonify({
        "cards": {"total_products": len(products), "total_stock": sum(p["stock_quantity"] for p in products),
                  "expiring_soon": es["soon"], "urgent": es["urgent"], "expired": es["expired"],
                  "low_stock": len(low), "predicted_sales": predicted, "value_at_risk": es["value_at_risk"]},
        "category_chart": [{"category": c, "units": cat_units[c], "products": cat_count[c]} for c in sorted(cat_units)],
        "expiry_chart": [{"status": s, "count": risk.get(s, 0)} for s in ("Expired", "Urgent", "Expiring Soon", "Safe")],
        "low_stock": sorted(low, key=lambda p: p["stock_quantity"] - p["min_stock_level"])[:8],
        "expiring": ex.alerts(products, "all", "all")[:8],
        "recent_sales": recent,
    })
