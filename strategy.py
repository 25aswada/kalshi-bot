# ============================================================
#  strategy.py — market-making logic for weather bracket markets
# ============================================================

import logging
from kalshi_client import KalshiClient
from fair_value import (
    get_forecast_high_f, fair_value_for_range,
    parse_range_from_market, get_series_ticker_for_market,
    clear_forecast_cache
)
from risk import RiskManager
from db import log_order
from config import MIN_EDGE_CENTS, ORDER_SIZE, CITIES, PAPER_TRADING

log = logging.getLogger("strategy")


def run_all_markets(client: KalshiClient, risk: RiskManager, positions: list, paper=None):
    """Fetch all weather markets and run strategy on each."""
    clear_forecast_cache()  # refresh forecasts once per cycle

    all_markets = []
    for series_ticker in CITIES.keys():
        try:
            markets = client.get_markets_for_series(series_ticker)
            log.info(f"{series_ticker}: {len(markets)} open market(s)")
            all_markets.extend(markets)
        except Exception as e:
            log.warning(f"Could not fetch markets for {series_ticker}: {e}")

    for market in all_markets:
        run_market(client, market, risk, positions, paper=paper)


def run_market(client: KalshiClient, market: dict, risk: RiskManager, positions: list, paper=None):
    ticker = market.get("ticker")
    if not ticker:
        return

    # --- Get fair value ---
    series_ticker = get_series_ticker_for_market(market)
    if not series_ticker:
        log.debug(f"Skipping {ticker}: can not identify series")
        return

    forecast = get_forecast_high_f(series_ticker)
    if forecast is None:
        return

    bracket = parse_range_from_market(market)
    if bracket is None:
        log.debug(f"Skipping {ticker}: can not parse range from title")
        return

    lo, hi = bracket
    fv = fair_value_for_range(forecast, lo, hi)

    # --- Get order book ---
    try:
        book = client.get_orderbook(ticker, depth=3)
    except Exception as e:
        log.warning(f"Orderbook error for {ticker}: {e}")
        return

    yes_bids = book.get("yes", [])
    no_bids  = book.get("no", [])

    best_bid = yes_bids[0]["price"] if yes_bids else None
    best_ask = (100 - no_bids[0]["price"]) if no_bids else None

    range_str = f"({lo if lo else "-inf"} to {hi if hi else "+inf"})"
    log.info(
        f"{ticker} {range_str} | forecast={forecast:.1f}F | "
        f"FV={fv}c | bid={best_bid}c | ask={best_ask}c"
    )

    # --- Trade decision ---
    # YES is cheap: best_ask < FV - MIN_EDGE
    if best_ask is not None and best_ask < fv - MIN_EDGE_CENTS:
        edge = fv - best_ask
        size = risk.position_size_for(ticker, positions, ORDER_SIZE)
        if size > 0:
            log.info(f"  -> BUY YES @ {best_ask}c (edge={edge}c)")
            try:
                if PAPER_TRADING and paper:
                    resp = paper.place_order(ticker, "yes", best_ask, size)
                else:
                    resp = client.place_order(ticker, "yes", best_ask, size)
                if resp:
                    oid = resp.get("order", {}).get("order_id", "")
                    log_order(ticker, "YES", best_ask, size, fv, edge, oid)
            except Exception as e:
                log.error(f"  Order failed: {e}")

    # YES is expensive: best_bid > FV + MIN_EDGE -> buy NO
    elif best_bid is not None and best_bid > fv + MIN_EDGE_CENTS:
        no_price = 100 - best_bid
        edge = best_bid - fv
        size = risk.position_size_for(ticker, positions, ORDER_SIZE)
        if size > 0:
            log.info(f"  -> BUY NO @ {no_price}c (edge={edge}c)")
            try:
                if PAPER_TRADING and paper:
                    resp = paper.place_order(ticker, "no", no_price, size)
                else:
                    resp = client.place_order(ticker, "no", no_price, size)
                if resp:
                    oid = resp.get("order", {}).get("order_id", "")
                    log_order(ticker, "NO", no_price, size, fv, edge, oid)
            except Exception as e:
                log.error(f"  Order failed: {e}")
    else:
        log.info(f"  -> No edge")


def cancel_all_open_orders(client: KalshiClient):
    try:
        orders = client.get_open_orders()
        for o in orders:
            try:
                client.cancel_order(o["order_id"])
            except Exception as e:
                log.warning(f"Failed to cancel {o['order_id']}: {e}")
        if orders:
            log.info(f"Cancelled {len(orders)} open orders")
    except Exception as e:
        log.error(f"Could not fetch open orders: {e}")