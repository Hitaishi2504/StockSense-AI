"""Report builders + CSV / PDF writers."""
import csv
import io
from datetime import date, timedelta

from .. import db
from ..config import Config
from . import expiry as ex
from . import inventory as inv
from . import reorder as ro


def _inventory(_a):
    cols = ["ID", "Product", "Category", "Supplier", "Stock", "Min stock", "Stock status", "Purchase price",
            "Selling price", "Mfg date", "Expiry date", "Days left", "Expiry status"]
    rows = [[p["product_id"], p["product_name"], p["category"], p["supplier"] or "", p["stock_quantity"],
             p["min_stock_level"], p["stock_status"], f"{p['purchase_price']:.2f}", f"{p['selling_price']:.2f}",
             p["manufacturing_date"] or "", p["expiry_date"], p["days_to_expiry"], p["expiry_status"]]
            for p in inv.load_products()]
    return {"title": "Inventory Report", "columns": cols, "rows": rows, "note": f"{len(rows)} products."}


def _expiry(_a):
    products = inv.load_products()
    recs = {r["product_id"]: r for r in ex.recommend(products)}
    cols = ["ID", "Product", "Category", "Stock", "Expiry date", "Days left", "Status", "Risk", "Units at risk",
            "Value at risk", "Sales-rate basis", "Recommended actions (with reasons)"]
    rows = []
    for p in ex.alerts(products):
        r = recs.get(p["product_id"])
        acts = " | ".join(f"{a['action']} Why: {a['reason']}" for a in r["actions"]) if r else ""
        rows.append([p["product_id"], p["product_name"], p["category"], p["stock_quantity"], p["expiry_date"],
                     p["days_to_expiry"], p["expiry_status"], p["risk_level"], p["units_at_risk"],
                     f"{p['value_at_risk']:.2f}", p["rate_basis"], acts])
    s = ex.summary(products)
    return {"title": "Expiry Report", "columns": cols, "rows": rows,
            "note": f"Expired: {s['expired']} | Urgent (<=7d): {s['urgent']} | Within 30d: {s['soon']} | "
                    f"High risk: {s['high_risk']} | Estimated value at risk: {s['value_at_risk']:,.2f}. "
                    "'assumption' = no sales history for that product, so a labeled assumed sales rate was used."}


def _reorder(_a):
    settings = inv.get_settings()
    cols = ["ID", "Product", "Category", "Supplier", "Stock", "Min stock", "Status", "Recommendation",
            "Qty to order", "Est. cost", "Method", "Reason"]
    rows = [[r["product_id"], r["product_name"], r["category"], r["supplier"] or "", r["stock_quantity"],
             r["min_stock_level"], r["stock_status"], r["recommendation"], r["recommended_qty"],
             f"{r['estimated_cost']:.2f}", r["method"], r["reason"]]
            for r in ro.build(inv.load_products(settings=settings), settings)]
    return {"title": "Reorder Report", "columns": cols, "rows": rows,
            "note": f"Lead time {settings['lead_time_days']} days, cover {settings['cover_days']} days. "
                    "Product-level rules only - the store/department CSV forecast is not used."}


def _sales(a):
    end = date.fromisoformat(a.get("end") or date.today().isoformat())
    start = date.fromisoformat(a.get("start") or (end - timedelta(days=29)).isoformat())
    data = db.query(
        "SELECT p.product_id, p.product_name, p.category, SUM(s.quantity_sold) AS units, "
        "SUM(s.quantity_sold * s.selling_price) AS revenue, SUM(s.quantity_sold * p.purchase_price) AS cost, "
        "MAX(s.is_sample) AS sample FROM sales s JOIN products p ON p.product_id = s.product_id "
        "WHERE s.sale_date >= %s AND s.sale_date <= %s GROUP BY p.product_id, p.product_name, p.category "
        "ORDER BY revenue DESC", (start, end))
    cols = ["ID", "Product", "Category", "Units sold", "Revenue", "Cost of goods", "Gross profit"]
    rows = [[r["product_id"], r["product_name"], r["category"], int(r["units"]), f"{r['revenue']:.2f}",
             f"{r['cost']:.2f}", f"{r['revenue'] - r['cost']:.2f}"] for r in data]
    tot = sum(r["revenue"] for r in data)
    out = {"title": "Sales Analysis Report", "columns": cols, "rows": rows,
           "note": f"Product-level sales entered in this app, {start} to {end}. Total revenue {tot:,.2f}. "
                   "Rows may include SAMPLE sales until you clear sample data in Settings.",
           "sections": []}
    try:  # separate, clearly labeled dataset section
        from ml import forecast as fc
        rep = fc.get_report(Config.MODEL_DIR)
        if rep:
            s = fc.series(Config.DATA_DIR, Config.MODEL_DIR, "all", "all", None, None, 8)
            m = rep["results"][rep["model_name"]]
            out["sections"].append({
                "title": "Store/department sales forecast (from sales.csv - NOT individual products)",
                "columns": ["Week", "Predicted sales (all stores)"],
                "rows": [[f["date"], f"{f['predicted']:,.0f}"] for f in s.get("future", [])],
                "note": f"Model: {rep['model_name']} | holdout weekly-total MAPE {m['weekly_total']['mape']:.1f}% | "
                        f"R2 {m['weekly_total']['r2']:.3f} | per store-dept-week R2 {m['row_level']['r2']:.3f}."})
    except Exception:
        pass
    return out


BUILDERS = {"inventory": _inventory, "expiry": _expiry, "reorder": _reorder, "sales": _sales}


def build(kind, args):
    if kind not in BUILDERS:
        raise KeyError(kind)
    return BUILDERS[kind](args)


def to_csv(rep):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([rep["title"], f"Generated {date.today()}"])
    w.writerow([rep["note"]])
    w.writerow([])
    w.writerow(rep["columns"])
    w.writerows(rep["rows"])
    for sec in rep.get("sections", []):
        w.writerow([])
        w.writerow([sec["title"]])
        w.writerow([sec["note"]])
        w.writerow(sec["columns"])
        w.writerows(sec["rows"])
    return "\ufeff" + buf.getvalue()   # BOM so Excel opens UTF-8 correctly


def to_pdf(rep, store_name):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    ss = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=ss["BodyText"], fontSize=7, leading=8.5)
    head = ParagraphStyle("head", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title=rep["title"])
    width = doc.width

    def table(cols, rows):
        wide = {c: 4.0 if c.lower().startswith(("reason", "recommended")) else 1.0 for c in cols}
        total = sum(wide.values())
        widths = [width * wide[c] / total for c in cols]
        data = [[Paragraph(str(c), head) for c in cols]] + [[Paragraph(str(v), cell) for v in r] for r in rows]
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                               ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return t

    el = [Paragraph(f"StockSense AI - {rep['title']}", ss["Title"]),
          Paragraph(f"{store_name} | Generated {date.today():%d %b %Y}", ss["Normal"]), Spacer(1, 4 * mm),
          Paragraph(rep["note"], ss["BodyText"]), Spacer(1, 4 * mm)]
    el.append(table(rep["columns"], rep["rows"]) if rep["rows"] else Paragraph("No rows for this report.", ss["BodyText"]))
    for sec in rep.get("sections", []):
        el += [Spacer(1, 8 * mm), Paragraph(sec["title"], ss["Heading3"]), Paragraph(sec["note"], ss["BodyText"]),
               Spacer(1, 2 * mm), table(sec["columns"], sec["rows"])]
    doc.build(el)
    return buf.getvalue()
