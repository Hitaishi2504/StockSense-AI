from flask import Blueprint, jsonify, request

from .. import db
from ..services import inventory as inv
from ..utils import err

bp = Blueprint("settings", __name__, url_prefix="/api/settings")
NUMERIC = {"lead_time_days": (0, 90), "cover_days": (1, 180), "assumed_cover_days": (1, 180),
           "basic_target_multiplier": (1, 10), "overstock_multiplier": (1.5, 20)}


@bp.get("")
def get():
    s = inv.get_settings()
    counts = db.query("SELECT (SELECT COUNT(*) FROM products WHERE is_sample=1) AS sp, "
                      "(SELECT COUNT(*) FROM sales WHERE is_sample=1) AS ss, "
                      "(SELECT COUNT(*) FROM products) AS tp", one=True)
    return jsonify({"settings": s, "sample_products": counts["sp"], "sample_sales": counts["ss"],
                    "total_products": counts["tp"]})


@bp.put("")
def put():
    d = request.get_json(force=True, silent=True) or {}
    for k, v in d.items():
        if k == "store_name":
            val = str(v).strip()[:80] or "My Store"
        elif k in NUMERIC:
            try:
                val = float(v)
            except (TypeError, ValueError):
                return err(f"{k} must be a number.")
            lo, hi = NUMERIC[k]
            if not lo <= val <= hi:
                return err(f"{k} must be between {lo} and {hi}.")
            val = str(int(val)) if val == int(val) else str(val)
        else:
            continue
        db.execute("DELETE FROM app_settings WHERE setting_key = %s", (k,))
        db.execute("INSERT INTO app_settings (setting_key, setting_value) VALUES (%s,%s)", (k, val))
    return jsonify({"message": "Settings saved."})


@bp.post("/clear-sample")
def clear_sample():
    db.execute("DELETE FROM sales WHERE is_sample = 1")
    db.execute("DELETE FROM products WHERE is_sample = 1")
    return jsonify({"message": "Sample products and sample sales removed. Your own data was kept."})
