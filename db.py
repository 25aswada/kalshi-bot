# ============================================================
#  db.py — SQLite logger for trades and cycle events
# ============================================================

import sqlite3
import logging
from datetime import datetime, timezone

log = logging.getLogger("db")
DB_PATH = "bot_log.db"


def init_db():
    """Create tables if they don't exist."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT,
            ticker      TEXT,
            side        TEXT,
            price_cents INTEGER,
            count       INTEGER,
            fair_value  INTEGER,
            edge        INTEGER,
            order_id    TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cycles (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ts              TEXT,
            balance_cents   INTEGER,
            total_contracts INTEGER,
            pnl_cents       INTEGER
        )
    """)
    con.commit()
    con.close()
    log.info(f"Database initialized at {DB_PATH}")


def log_order(ticker, side, price_cents, count, fair_value, edge, order_id):
    ts = datetime.now(timezone.utc).isoformat()
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO orders (ts,ticker,side,price_cents,count,fair_value,edge,order_id) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (ts, ticker, side, price_cents, count, fair_value, edge, order_id)
    )
    con.commit()
    con.close()


def log_cycle(balance_cents, total_contracts, starting_balance):
    ts = datetime.now(timezone.utc).isoformat()
    pnl = balance_cents - starting_balance
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO cycles (ts,balance_cents,total_contracts,pnl_cents) VALUES (?,?,?,?)",
        (ts, balance_cents, total_contracts, pnl)
    )
    con.commit()
    con.close()
