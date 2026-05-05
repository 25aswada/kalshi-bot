# ============================================================
#  kalshi_client.py — Kalshi REST API v2 with RSA-PSS auth
# ============================================================
#
#  Kalshi requires every request to be signed with your private key.
#  Headers needed on every request:
#    KALSHI-ACCESS-KEY       → your Key ID
#    KALSHI-ACCESS-TIMESTAMP → current time in milliseconds
#    KALSHI-ACCESS-SIGNATURE → RSA-PSS SHA256 signature of
#                              (timestamp_str + HTTP_METHOD + path)
#
#  The path signed must NOT include query parameters.
# ============================================================

import requests
import datetime
import base64
import logging
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from config import KALSHI_KEY_ID, KALSHI_PRIVATE_KEY_PATH, KALSHI_BASE_URL

log = logging.getLogger("kalshi")


def load_private_key(path: str):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())


def sign_request(private_key, timestamp_ms: str, method: str, path: str) -> str:
    """
    Signs: timestamp_ms + METHOD + path_without_query
    Using RSA-PSS with SHA256. Returns base64-encoded signature.
    """
    path_no_query = path.split("?")[0]
    msg = (timestamp_ms + method.upper() + path_no_query).encode("utf-8")
    signature = private_key.sign(
        msg,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


class KalshiClient:
    def __init__(self):
        self.private_key = load_private_key(KALSHI_PRIVATE_KEY_PATH)
        self.session = requests.Session()
        self.base = KALSHI_BASE_URL

    def _headers(self, method: str, path: str) -> dict:
        ts = str(int(datetime.datetime.now().timestamp() * 1000))
        sig = sign_request(self.private_key, ts, method, path)
        return {
            "KALSHI-ACCESS-KEY": KALSHI_KEY_ID,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": sig,
            "Content-Type": "application/json",
        }

    def _get(self, path, params=None):
        full_path = path
        r = self.session.get(
            f"{self.base}{path}",
            headers=self._headers("GET", "/trade-api/v2" + path),
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def _post(self, path, body):
        r = self.session.post(
            f"{self.base}{path}",
            headers=self._headers("POST", "/trade-api/v2" + path),
            json=body,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def _delete(self, path):
        r = self.session.delete(
            f"{self.base}{path}",
            headers=self._headers("DELETE", "/trade-api/v2" + path),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    # ----------------------------------------------------------
    #  Account
    # ----------------------------------------------------------
    def get_balance(self):
        data = self._get("/portfolio/balance")
        return data["balance"]

    def get_positions(self):
        data = self._get("/portfolio/positions")
        return data.get("market_positions", [])

    # ----------------------------------------------------------
    #  Markets
    # ----------------------------------------------------------
    def search_markets(self, keyword, status="open", limit=50):
        params = {"status": status, "limit": limit}
        data = self._get("/markets", params=params)
        markets = data.get("markets", [])
        keyword = keyword.upper()
        return [
            m for m in markets
            if keyword in m.get("ticker", "").upper()
            or keyword in m.get("title", "").upper()
        ]

    def get_markets_for_series(self, series_ticker, status="open", limit=20):
        """Fetch all open markets for a given series (e.g. KXHIGHNY)."""
        params = {"series_ticker": series_ticker, "status": status, "limit": limit}
        data = self._get("/markets", params=params)
        return data.get("markets", [])

    def get_orderbook(self, ticker, depth=5):
        data = self._get(f"/markets/{ticker}/orderbook", params={"depth": depth})
        return data.get("orderbook", data)

    # ----------------------------------------------------------
    #  Orders
    # ----------------------------------------------------------
    def place_order(self, ticker, side, price_cents, count, client_order_id=None):
        body = {
            "ticker": ticker,
            "action": "buy",
            "side": side,
            "type": "limit",
            "count": count,
            "yes_price": price_cents if side == "yes" else (100 - price_cents),
        }
        if client_order_id:
            body["client_order_id"] = client_order_id
        log.info(f"Placing {side.upper()} order on {ticker}: {count} @ {price_cents}c")
        return self._post("/orders", body)

    def cancel_order(self, order_id):
        return self._delete(f"/orders/{order_id}")

    def get_open_orders(self, ticker=None):
        params = {"status": "resting"}
        if ticker:
            params["ticker"] = ticker
        data = self._get("/orders", params=params)
        return data.get("orders", [])