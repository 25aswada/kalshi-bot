# ============================================================
#  config.py — edit this before running
# ============================================================

# --- Kalshi credentials ---
# Go to kalshi.com → Account → API Keys → Create New Key
# You will get:
#   1. A Key ID (looks like: a952bcbe-ec3b-4b5b-b8f9-11dae589608c)
#   2. A private key file to download (save it as kalshi-private-key.pem
#      in the same folder as this bot)

KALSHI_KEY_ID          = "ecdbcc7e-77a9-472f-9e6d-53d19663a217"         # the UUID shown on kalshi.com
KALSHI_PRIVATE_KEY_PATH = "/Users/akshajsatyawada/Downloads/Kalshi/kalshi-private-key.pem"  # path to the downloaded .pem file
KALSHI_BASE_URL        = "https://api.elections.kalshi.com/trade-api/v2"

# --- Cities to trade ---
# series_ticker: Kalshi series identifier for that city's high temp market
CITIES = {
    "KXHIGHNY":     {"lat": 40.7128, "lon": -74.0060,  "timezone": "America/New_York"},
    "KXHIGHCHI":    {"lat": 41.8781, "lon": -87.6298,  "timezone": "America/Chicago"},
    "KXHIGHLA":     {"lat": 34.0522, "lon": -118.2437, "timezone": "America/Los_Angeles"},
    "KXHIGHMIAMI":  {"lat": 25.7617, "lon": -80.1918,  "timezone": "America/New_York"},
    "KXHIGHAUSTIN": {"lat": 30.2672, "lon": -97.7431,  "timezone": "America/Chicago"},
}

# --- Strategy parameters ---
MIN_EDGE_CENTS    = 3    # minimum edge before placing an order
ORDER_SIZE        = 5    # contracts per order
LOOP_INTERVAL_SEC = 20  # seconds between reprice cycles
FORECAST_STD_F    = 3.5  # assumed forecast uncertainty in degF

# --- Paper trading ---
PAPER_TRADING = True          # set False to go live with real money
PAPER_STARTING_BALANCE = 5000 # cents = $50.00

# --- Risk controls ---
MAX_CONTRACTS_PER_MARKET = 20
MAX_TOTAL_CONTRACTS      = 80
MAX_LOSS_DOLLARS         = 30.0