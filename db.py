"""Thin database layer. One connection per request (stored on flask.g).

All SQL in the project is written with %s placeholders (MySQL style).
Date arithmetic is done in Python, so the SQL stays simple and portable.
"""
import contextlib
import sqlite3
from datetime import date, datetime
from decimal import Decimal

from flask import g

from .config import Config

IS_SQLITE = Config.DB_BACKEND == "sqlite"


def _connect():
    if IS_SQLITE:
        conn = sqlite3.connect(Config.SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    import pymysql
    return pymysql.connect(
        host=Config.MYSQL_HOST, port=Config.MYSQL_PORT, user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD, database=Config.MYSQL_DATABASE,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, autocommit=False,
    )


def get_conn():
    if "db" not in g:
        g.db = _connect()
        g.in_tx = False
    return g.db


def close_conn(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def _sql(sql):
    return sql.replace("%s", "?") if IS_SQLITE else sql


def _clean(row):
    out = {}
    for k, v in dict(row).items():
        if isinstance(v, Decimal):
            v = float(v)
        out[k] = v
    return out


def query(sql, params=(), one=False):
    cur = get_conn().cursor()
    cur.execute(_sql(sql), tuple(params))
    rows = [_clean(r) for r in cur.fetchall()]
    cur.close()
    get_conn().commit() if not g.get("in_tx") else None  # end read snapshot
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, params=()):
    """Run INSERT/UPDATE/DELETE. Returns (last_insert_id, rows_affected)."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(_sql(sql), tuple(params))
        result = (cur.lastrowid, cur.rowcount)
        if not g.get("in_tx"):
            conn.commit()
        return result
    except Exception:
        if not g.get("in_tx"):
            conn.rollback()
        raise
    finally:
        cur.close()


@contextlib.contextmanager
def transaction():
    conn = get_conn()
    g.in_tx = True
    try:
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        g.in_tx = False


def run_script(sql_text):
    """Execute a multi-statement SQL script (used by database/init_db.py)."""
    conn = get_conn()
    cur = conn.cursor()
    for stmt in [s.strip() for s in sql_text.split(";") if s.strip()]:
        cur.execute(stmt)
    conn.commit()
    cur.close()


def to_date(v):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])
