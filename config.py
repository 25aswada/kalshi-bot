# ============================================================
#  config.py
# ============================================================
import os

# --- Kalshi credentials (set these as env vars in Railway) ---
KALSHI_KEY_ID          = "ecdbcc7e-77a9-472f-9e6d-53d19663a217"         # the UUID shown on kalshi.com
KALSHI_PRIVATE_KEY_PATH = "/Users/akshajsatyawada/Downloads/Kalshi/kalshi-private-key.pem"  # path to the downloaded .pem file
KALSHI_BASE_URL        = "https://api.elections.kalshi.com/trade-api/v2"

# --- Cities to trade ---
CITIES = {
    "KXHIGHNY":     {"lat": 40.7128, "lon": -74.0060,  "timezone": "America/New_York"},
    "KXHIGHCHI":    {"lat": 41.8781, "lon": -87.6298,  "timezone": "America/Chicago"},
    "KXHIGHLA":     {"lat": 34.0522, "lon": -118.2437, "timezone": "America/Los_Angeles"},
    "KXHIGHMIAMI":  {"lat": 25.7617, "lon": -80.1918,  "timezone": "America/New_York"},
    "KXHIGHAUSTIN": {"lat": 30.2672, "lon": -97.7431,  "timezone": "America/Chicago"},
}

# --- Paper trading ---
PAPER_TRADING = os.environ.get("PAPER_TRADING", "true").lower() == "true"
PAPER_STARTING_BALANCE = 5000  # cents = $50.00

# --- Strategy parameters ---
MIN_EDGE_CENTS    = 3
ORDER_SIZE        = 5
LOOP_INTERVAL_SEC = 20
FORECAST_STD_F    = 3.5

# --- Risk controls ---
MAX_CONTRACTS_PER_MARKET = 20
MAX_TOTAL_CONTRACTS      = 80
MAX_LOSS_DOLLARS         = 30.0