from datetime import date
from flask import jsonify


def err(message, status=400, **extra):
    return jsonify({"error": message, **extra}), status


def parse_date(v, field):
    if v in (None, ""):
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        raise ValueError(f"{field} must be a valid date (YYYY-MM-DD).")


def parse_int(v, field, minimum=0):
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a whole number.")
    if n < minimum:
        raise ValueError(f"{field} must be at least {minimum}.")
    return n


def parse_money(v, field):
    try:
        n = round(float(v), 2)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number.")
    if n < 0:
        raise ValueError(f"{field} cannot be negative.")
    return n
