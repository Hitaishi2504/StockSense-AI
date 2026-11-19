"""Expiry alerts + rule-based selling recommendations. Every action carries a reason."""
import math
from collections import defaultdict


def discount_tier(days):
    if days <= 2:
        return 50
    if days <= 7:
        return 30
    if days <= 14:
        return 20
    return 10


def alerts(products, category=None, period="all"):
    """Products still in stock that are expired / urgent / expiring soon."""
    out = [p for p in products if p["stock_quantity"] > 0 and p["days_to_expiry"] is not None
           and p["days_to_expiry"] <= 30]
    if category and category != "all":
        out = [p for p in out if p["category"] == category]
    if period == "expired":
        out = [p for p in out if p["days_to_expiry"] < 0]
    elif period == "7":
        out = [p for p in out if 0 <= p["days_to_expiry"] <= 7]
    elif period == "30":
        out = [p for p in out if 0 <= p["days_to_expiry"] <= 30]
    elif period == "high":
        out = [p for p in out if p["risk_level"] in ("High", "Expired")]
    return sorted(out, key=lambda p: p["days_to_expiry"])


def summary(products):
    live = [p for p in products if p["stock_quantity"] > 0 and p["days_to_expiry"] is not None]
    return {
        "expired": sum(1 for p in live if p["days_to_expiry"] < 0),
        "urgent": sum(1 for p in live if 0 <= p["days_to_expiry"] <= 7),
        "soon": sum(1 for p in live if 0 <= p["days_to_expiry"] <= 30),
        "high_risk": sum(1 for p in live if p["risk_level"] == "High"),
        "value_at_risk": round(sum(p["value_at_risk"] for p in live), 2),
    }


def _best_partner(p, products):  # partner must outlast the at-risk product by a safe margin
    """A healthy, fast-moving product in the same category to bundle with (from real sales history)."""
    cands = [q for q in products if q["category"] == p["category"] and q["product_id"] != p["product_id"]
             and q["stock_quantity"] > 0 and q["days_to_expiry"] is not None and q["days_to_expiry"] > max(14, p["days_to_expiry"] + 7)
             and q["has_history"]]
    return max(cands, key=lambda q: q["daily_rate"]) if cands else None


def recommend(products, category=None):
    """Recommendation cards for every in-stock product that is expired or expiring within 30 days."""
    batches = defaultdict(list)
    for q in products:
        if q["stock_quantity"] > 0 and q["expiry_date"]:
            batches[q["product_name"].strip().lower()].append(q)

    result = []
    for p in alerts(products, category, "all"):
        d, stock = p["days_to_expiry"], p["stock_quantity"]
        basis = ("based on its recent sales history" if p["has_history"]
                 else "using an ASSUMED sales rate (no sales history entered yet)")
        actions = []

        if d < 0:
            loss = round(stock * p["purchase_price"], 2)
            actions.append({"type": "Remove & write off",
                            "action": f"Remove all {stock} units from sale and record the write-off (cost {loss:,.2f}).",
                            "reason": f"Expired {-d} day(s) ago. Selling expired food is a safety and legal risk, so no discount applies."})
            result.append(_card(p, actions, priority=0, qty_before=0))
            continue

        rate = p["daily_rate"]
        expected = min(stock, math.floor(rate * d))
        at_risk = p["units_at_risk"]
        need_per_day = stock / max(d, 1)

        # FEFO
        same = sorted(batches[p["product_name"].strip().lower()], key=lambda q: q["expiry_date"])
        if len(same) > 1:
            pos = [q["product_id"] for q in same].index(p["product_id"]) + 1
            actions.append({"type": "FEFO",
                            "action": f"Batch {pos} of {len(same)} for this product - " + ("sell this one FIRST." if pos == 1 else "sell after the earlier-expiring batch."),
                            "reason": "First-Expired-First-Out: the batch that expires earliest must leave the shelf first."})
        else:
            actions.append({"type": "FEFO",
                            "action": "Move these units to the front of the shelf / top of the stock rotation.",
                            "reason": f"Expires in {d} day(s); FEFO rotation ensures it is picked before newer stock."})

        # Discount (never silently below cost unless nearly out of time)
        tier = discount_tier(d)
        breakeven = max(0.0, p["margin_pct"])
        if d > 3 and tier > breakeven:
            tier = int(math.floor(breakeven / 5.0) * 5)
            capped = True
        else:
            capped = False
        if tier >= 5:
            price = round(p["selling_price"] * (1 - tier / 100), 2)
            why = (f"{d} day(s) left; {basis}, about {expected} of {stock} units would sell, leaving ~{at_risk} at risk.")
            if tier > breakeven:
                why += (f" This is below the purchase price ({p['purchase_price']:.2f}), but recovering some cost beats "
                        f"a total write-off.")
            if capped:
                why += f" Discount capped at the break-even margin ({breakeven:.0f}%) so you do not sell below cost."
            actions.append({"type": "Discount", "action": f"Discount {tier}% (new price {price:.2f}).", "reason": why})
        else:
            actions.append({"type": "Promotion",
                            "action": "Margin is too thin for a discount - use shelf placement and signage instead.",
                            "reason": f"Margin is only {p['margin_pct']:.0f}%, so a discount would sell below cost while {d} days remain."})

        # BOGO
        if d <= 14 and at_risk >= 10 and p["margin_pct"] >= 50:
            actions.append({"type": "BOGO", "action": "Run a Buy 1 Get 1 offer.",
                            "reason": f"~{at_risk} units are at risk and the {p['margin_pct']:.0f}% margin can absorb the effective 50% price cut."})

        # Bundle
        if d <= 14 and at_risk > 0:
            partner = _best_partner(p, products)
            if partner:
                actions.append({"type": "Bundle",
                                "action": f"Bundle with '{partner['product_name']}' (same category, fast-moving, {partner['days_to_expiry']} days of shelf life left).",
                                "reason": f"'{partner['product_name']}' sells ~{partner['daily_rate']:.1f} units/day based on your sales history, so pairing it pulls this product along."})
            else:
                actions.append({"type": "Bundle", "action": "Bundle with a popular item from the same category (e.g. a 'meal deal').",
                                "reason": "No fast-moving partner could be identified from sales history yet - this is a general suggestion."})

        # Campaign
        if at_risk >= max(5, 0.3 * stock):
            actions.append({"type": "Campaign",
                            "action": "Feature in a 'Fresh deals' end-cap / WhatsApp or in-store announcement.",
                            "reason": f"{at_risk} of {stock} units ({at_risk / stock * 100:.0f}%) are projected to be unsold at expiry."})

        # Donation as last resort
        if d <= 3:
            actions.append({"type": "Donate",
                            "action": "If it will not sell, donate edible items to a food bank before the expiry date.",
                            "reason": "Only a few days remain; donation avoids waste and disposal cost."})

        # Pause restocking
        if stock > p["min_stock_level"]:
            actions.append({"type": "Hold reorder",
                            "action": "Do NOT restock this product for now.",
                            "reason": f"Stock ({stock}) is above the minimum ({p['min_stock_level']}) and part of it may expire unsold."})

        result.append(_card(p, actions, priority=d, qty_before=expected, need_per_day=need_per_day))
    return result


def _card(p, actions, priority, qty_before, need_per_day=None):
    return {
        "product_id": p["product_id"], "product_name": p["product_name"], "category": p["category"],
        "stock_quantity": p["stock_quantity"], "expiry_date": p["expiry_date"],
        "days_to_expiry": p["days_to_expiry"], "expiry_status": p["expiry_status"], "risk_level": p["risk_level"],
        "units_at_risk": p["units_at_risk"], "value_at_risk": p["value_at_risk"],
        "daily_rate": p["daily_rate"], "rate_basis": p["rate_basis"],
        "expected_sold_before_expiry": qty_before,
        "must_sell_per_day": round(need_per_day, 2) if need_per_day is not None else None,
        "actions": actions, "priority": priority,
    }
