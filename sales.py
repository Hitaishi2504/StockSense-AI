from datetime import date

from flask import Blueprint, jsonify, request

from .. import db
from ..db import to_date
from ..utils import err, parse_date, parse_int, parse_money

bp = Blueprint("sales", __name__, url_prefix="/api/sales")


@bp.get("")
def list_sales():
    limit = min(int(request.args.get("limit", 200)), 2000)
    sql = ("SELECT s.sale_id, s.product_id, p.product_name, p.category, s.quantity_sold, s.sale_date, "
           "s.selling_price, s.is_sample FROM sales s JOIN products p ON p.product_id = s.product_id")
    params = []
    start, end = request.args.get("start"), request.args.get("end")
    where = []
    if start:
        where.append("s.sale_date >= %s"); params.append(start)
    if end:
        where.append("s.sale_date <= %s"); params.append(end)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY s.sale_date DESC, s.sale_id DESC LIMIT " + str(limit)
    rows = db.query(sql, params)
    for r in rows:
        r["total"] = round(r["quantity_sold"] * r["selling_price"], 2)
    return jsonify({"items": rows})


@bp.post("")
def add_sale():
    d = request.get_json(force=True, silent=True) or {}
    try:
        ref = str(d.get("product") or d.get("product_id") or "").strip()
        if not ref:
            raise ValueError("Enter a product name or product ID.")
        qty = parse_int(d.get("quantity_sold"), "Quantity sold", 1)
        sdate = parse_date(d.get("sale_date"), "Sales date") or date.today()
        if sdate > date.today():
            raise ValueError("Sales date cannot be in the future.")
    except ValueError as e:
        return err(str(e))

    # find product by ID, else by exact name, else by unique partial name
    prod = None
    if ref.isdigit():
        prod = db.query("SELECT * FROM products WHERE product_id = %s", (int(ref),), one=True)
    if not prod:
        rows = db.query("SELECT * FROM products WHERE LOWER(product_name) = %s", (ref.lower(),))
        if not rows:
            rows = db.query("SELECT * FROM products WHERE LOWER(product_name) LIKE %s", (f"%{ref.lower()}%",))
        if len(rows) > 1:
            names = ", ".join(f"{r['product_name']} (ID {r['product_id']})" for r in rows[:5])
            return err(f"More than one product matches '{ref}': {names}. Please use the product ID.")
        prod = rows[0] if rows else None
    if not prod:
        return err(f"No product found for '{ref}'.", 404)

    try:
        price = parse_money(d.get("selling_price"), "Selling price") if d.get("selling_price") not in (None, "") \
            else float(prod["selling_price"])
    except ValueError as e:
        return err(str(e))
    exp = to_date(prod["expiry_date"])
    if exp and sdate > exp:
        return err(f"'{prod['product_name']}' had expired on {exp} - it cannot be sold on {sdate}.")

    with db.transaction():
        _, n = db.execute(  # atomic stock check + decrement: cannot go negative even with two users
            "UPDATE products SET stock_quantity = stock_quantity - %s WHERE product_id = %s AND stock_quantity >= %s",
            (qty, prod["product_id"], qty))
        if n == 0:
            cur = db.query("SELECT stock_quantity FROM products WHERE product_id = %s", (prod["product_id"],), one=True)
            return err(f"Not enough stock. Only {cur['stock_quantity']} unit(s) of '{prod['product_name']}' available.")
        sid, _ = db.execute(
            "INSERT INTO sales (product_id, quantity_sold, sale_date, selling_price) VALUES (%s,%s,%s,%s)",
            (prod["product_id"], qty, sdate, price))
    left = db.query("SELECT stock_quantity FROM products WHERE product_id = %s", (prod["product_id"],), one=True)
    return jsonify({"sale_id": sid, "product_name": prod["product_name"], "stock_left": left["stock_quantity"],
                    "message": f"Sale recorded. {left['stock_quantity']} unit(s) of {prod['product_name']} left."}), 201


@bp.delete("/<int:sid>")
def undo_sale(sid):
    s = db.query("SELECT * FROM sales WHERE sale_id = %s", (sid,), one=True)
    if not s:
        return err("Sale not found.", 404)
    with db.transaction():
        db.execute("DELETE FROM sales WHERE sale_id = %s", (sid,))
        if not s["is_sample"]:
            db.execute("UPDATE products SET stock_quantity = stock_quantity + %s WHERE product_id = %s",
                       (s["quantity_sold"], s["product_id"]))
    return jsonify({"message": "Sale removed" + ("." if s["is_sample"] else " and the stock was restored.")})
