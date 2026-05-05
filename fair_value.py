# ============================================================
#  fair_value.py — estimates probability from weather forecasts
# ============================================================
#
#  Kalshi weather markets are RANGE brackets, e.g.:
#    "Will NYC high be 62-63°F?" (2°F wide)
#    "Will NYC high be below 58°F?" (lower edge bracket)
#    "Will NYC high be 66°F or above?" (upper edge bracket)
#
#  Fair value for a range [lo, hi] = P(lo <= actual_high < hi)
#  We model actual_high ~ N(forecast_mean, FORECAST_STD_F)
#
#  Settlement uses NWS Daily Climate Report (not apps).
# ============================================================

import requests
import logging
import math
import re
from config import FORECAST_STD_F, CITIES

log = logging.getLogger("fair_value")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Cache forecasts so we don't hammer Open-Meteo every cycle
_forecast_cache = {}


def _normal_cdf(x, mean, std):
    """P(X <= x) where X ~ N(mean, std)"""
    z = (x - mean) / (std * math.sqrt(2))
    return 0.5 * (1 + math.erf(z))


def get_forecast_high_f(series_ticker: str) -> float | None:
    """
    Fetches today's forecast high temperature in °F.
    Caches result per series_ticker per run cycle.
    """
    if series_ticker in _forecast_cache:
        return _forecast_cache[series_ticker]

    city = CITIES.get(series_ticker)
    if not city:
        log.warning(f"Unknown series ticker: {series_ticker}")
        return None

    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "daily": "temperature_2m_max",
        "temperature_unit": "fahrenheit",
        "timezone": city["timezone"],
        "forecast_days": 1,
    }

    try:
        r = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        forecast = data["daily"]["temperature_2m_max"][0]
        log.info(f"{series_ticker} forecast high: {forecast:.1f}°F")
        _forecast_cache[series_ticker] = forecast
        return forecast
    except Exception as e:
        log.error(f"Open-Meteo error for {series_ticker}: {e}")
        return None


def clear_forecast_cache():
    """Call once per main loop cycle to refresh forecasts."""
    _forecast_cache.clear()


def fair_value_for_range(forecast_mean: float, lo: float | None, hi: float | None) -> int:
    """
    Returns fair value in Kalshi cents (1-99) for a temperature range bracket.
    lo=None means open lower edge (< hi)
    hi=None means open upper edge (>= lo)
    Both set means closed range [lo, hi)
    """
    if lo is None and hi is not None:
        # Lower edge: P(temp < hi)
        prob = _normal_cdf(hi, forecast_mean, FORECAST_STD_F)
    elif hi is None and lo is not None:
        # Upper edge: P(temp >= lo) = 1 - P(temp < lo)
        prob = 1.0 - _normal_cdf(lo, forecast_mean, FORECAST_STD_F)
    elif lo is not None and hi is not None:
        # Closed range: P(lo <= temp < hi)
        prob = _normal_cdf(hi, forecast_mean, FORECAST_STD_F) - _normal_cdf(lo, forecast_mean, FORECAST_STD_F)
    else:
        return 50  # fallback

    return max(1, min(99, round(prob * 100)))


def parse_range_from_market(market: dict) -> tuple[float | None, float | None] | None:
    """
    Parses the temperature range from a Kalshi market title.
    Returns (lo, hi) where None means open-ended.
    Examples:
      "Will the high be 62-63°F?" -> (62, 64)   [Kalshi ranges are inclusive on both ends, width=2]
      "Will the high be below 58°F?" -> (None, 58)
      "Will the high be 66°F or above?" -> (66, None)
    Returns None if we can't parse it.
    """
    title = market.get("title", "") + " " + market.get("subtitle", "")

    # "below X" or "under X" -> upper edge bracket
    m = re.search(r"below\s+(\d+)", title, re.IGNORECASE)
    if m:
        return (None, float(m.group(1)))

    m = re.search(r"under\s+(\d+)", title, re.IGNORECASE)
    if m:
        return (None, float(m.group(1)))

    # "X or above" / "X or higher" / "at least X" -> lower edge bracket
    m = re.search(r"(\d+)\s+or\s+(?:above|higher|more)", title, re.IGNORECASE)
    if m:
        return (float(m.group(1)), None)

    m = re.search(r"at least\s+(\d+)", title, re.IGNORECASE)
    if m:
        return (float(m.group(1)), None)

    # "X-Y" or "X to Y" range
    m = re.search(r"(\d+)\s*[-–to]+\s*(\d+)", title, re.IGNORECASE)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        return (lo, hi + 1)  # Kalshi ranges inclusive, convert to [lo, hi)

    log.debug(f"Could not parse range from: {title}")
    return None


def get_series_ticker_for_market(market: dict) -> str | None:
    """Extract the series ticker from a market dict."""
    # Market ticker format: KXHIGHNY-25MAY04-T62
    # Series ticker: KXHIGHNY
    ticker = market.get("ticker", "")
    for series in CITIES.keys():
        if ticker.startswith(series):
            return series
    # fallback: try event_ticker or series_ticker field
    return market.get("series_ticker") or market.get("event_ticker", "").split("-")[0] or None