# Kalshi Weather Trading Bot

Automatically trades Kalshi temperature markets overnight using
Open-Meteo weather forecasts as a fair value signal.

## Setup (5 minutes)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get your Kalshi API key
- Go to https://kalshi.com/account/api
- Create a new API key
- Paste it into `config.py` → `KALSHI_API_KEY`

### 3. Configure (optional)
Edit `config.py`:
- `MIN_EDGE_CENTS` — how much edge you need before trading (default: 3¢)
- `ORDER_SIZE` — contracts per trade (default: 5)
- `MAX_LOSS_DOLLARS` — kill switch (default: $30)
- `CITIES` — which cities to trade

### 4. Run
```bash
python main.py
```

Press `Ctrl+C` to stop. All open orders are cancelled automatically on exit.

## Output files
- `bot.log` — human-readable log of every cycle and trade
- `bot_log.db` — SQLite database with full order and P&L history

## View your P&L history
```bash
sqlite3 bot_log.db "SELECT ts, balance_cents/100.0, pnl_cents/100.0 FROM cycles ORDER BY ts DESC LIMIT 20;"
```

## How it works

1. Every 20 seconds, the bot searches Kalshi for active high-temperature markets
2. For each market, it fetches the forecast from Open-Meteo (free, no key needed)
3. It computes P(actual high > threshold) using a normal distribution
4. If the market price deviates from fair value by more than `MIN_EDGE_CENTS`:
   - Market overestimates YES → bot buys NO
   - Market underestimates YES → bot buys YES
5. Risk limits cap exposure; kill switch stops the bot on large losses

## Risk warning
This is real money. Start with a small balance ($50-100) and watch
the first few cycles manually before leaving it overnight.
