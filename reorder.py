"""Explainable reorder recommendations.

Method A (product sales history available):
    reorder point  = avg daily sales x lead time + minimum stock
    order quantity = avg daily sales x (lead time + cover days) + minimum stock - usable stock
    (capped by shelf life so we do not order more than can sell before it expires)
Method B (no sales history): basic threshold rule, clearly labeled.
    reorder when stock <= minimum;  order up to N x minimum.
The store/department CSV forecast is never used here.
"""
import math

from .inventory import num


def build(products, settings):
    lead, cover = num(settings, "lead_time_days"), num(settings, "cover_days")
    mult = num(settings, "basic_target_multiplier")
    rows = []
    for p in products:
        stock, mn, d = p["stock_quantity"], p["min_stock_level"], p["days_to_expiry"]
        expired = d is not None and d < 0
        usable = 0 if expired else stock
        rate = p["daily_rate"] if p["has_history"] else 0.0
        method = "Sales-history based" if p["has_history"] else "Basic threshold (no sales history)"
        rec, qty, reason = "No action", 0, ""

        if p["has_history"]:
            rop = math.ceil(rate * lead + mn)
            target = rate * (lead + cover) + mn
            need = max(0, math.ceil(target - usable))
            if usable <= mn:
                rec, qty = "Reorder now", need
            elif usable <= rop:
                rec, qty = "Reorder soon", need
            reason = (f"Sells ~{rate:.1f}/day (last 30 days). Reorder point = {rate:.1f}x{lead:.0f} lead days + "
                      f"{mn} minimum = {rop}. Usable stock is {usable}.")
            life = (p["expiry_date"] - p["manufacturing_date"]).days if p["manufacturing_date"] and p["expiry_date"] else None
            if qty and life and life > 0:
                cap = max(1, math.floor(rate * life * 0.8))
                if qty > cap:
                    reason += f" Quantity capped from {qty} to {cap} (80% of what sells within its {life}-day shelf life) to avoid waste."
                    qty = cap
        else:
            if usable <= mn:
                rec = "Reorder now"
                qty = max(0, math.ceil(mn * mult - usable))
            reason = (f"Basic rule: reorder when stock <= minimum ({mn}); refill up to {mult:g}x minimum. "
                      f"Usable stock is {usable}. Enter more sales to switch to the sales-based method.")

        if expired and stock > 0:
            reason = f"All {stock} units are EXPIRED, so usable stock is 0. " + reason
        if rec == "No action" and d is not None and 0 <= d <= 30 and stock > mn:
            rec = "Hold - do not restock"
            reason = f"Stock ({stock}) is above minimum and expires in {d} day(s). Sell it first. " + reason
        elif rec == "No action" and p["stock_status"] == "Overstocked":
            rec = "Hold - do not restock"
            reason = f"Stock ({stock}) is more than {num(settings, 'overstock_multiplier'):g}x the minimum ({mn}). " + reason

        rows.append({
            "product_id": p["product_id"], "product_name": p["product_name"], "category": p["category"],
            "supplier": p["supplier"], "stock_quantity": stock, "min_stock_level": mn,
            "stock_status": p["stock_status"], "recommendation": rec, "recommended_qty": int(qty),
            "estimated_cost": round(qty * p["purchase_price"], 2), "method": method, "reason": reason.strip()})
    order = {"Reorder now": 0, "Reorder soon": 1, "Hold - do not restock": 2, "No action": 3}
    return sorted(rows, key=lambda r: (order[r["recommendation"]], r["stock_quantity"] - r["min_stock_level"]))
