#!/usr/bin/env python3
# ============================================================
#  main.py — entry point for the Kalshi weather trading bot
# ============================================================
#
#  USAGE:
#    pip install -r requirements.txt
#    python main.py
#
#  Press Ctrl+C to stop. All open orders are cancelled on exit.
# ============================================================

import time
import logging
import signal
import sys
from datetime import datetime, timezone

from kalshi_client import KalshiClient
from strategy import run_all_markets, cancel_all_open_orders
from paper_trading import PaperPortfolio
from config import PAPER_TRADING
from risk import RiskManager
from db import init_db, log_cycle
from config import LOOP_INTERVAL_SEC

# ---- Logging setup ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log"),
    ],
)
log = logging.getLogger("main")

# ---- Globals for graceful shutdown ----
client: KalshiClient | None = None
shutdown_requested = False


def handle_signal(sig, frame):
    global shutdown_requested
    log.info("Shutdown signal received — cancelling orders and exiting...")
    shutdown_requested = True


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def main():
    global client

    log.info("=" * 60)
    log.info("  Kalshi Weather Trading Bot  —  starting up")
    log.info("=" * 60)

    # --- Init ---
    init_db()
    client = KalshiClient()

    # Get starting balance (used for P&L tracking and kill switch)
    try:
        starting_balance = client.get_balance()
        log.info(f"Starting balance: ${starting_balance / 100:.2f}")
    except Exception as e:
        log.critical(f"Failed to connect to Kalshi: {e}")
        log.critical("Check your API key in config.py")
        sys.exit(1)

    # --- Paper trading setup ---
    paper = None
    if PAPER_TRADING:
        from config import PAPER_STARTING_BALANCE
        paper = PaperPortfolio()
        log.info(f"*** PAPER TRADING MODE — starting balance: ${PAPER_STARTING_BALANCE/100:.2f} ***")
        log.info("*** No real orders will be placed ***")

    risk = RiskManager(starting_balance)

    cycle = 0
    while not shutdown_requested:
        cycle += 1
        log.info(f"\n{'─'*50}")
        log.info(f"  Cycle #{cycle}  —  {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")
        log.info(f"{'─'*50}")

        try:
            # --- Fetch current state ---
            if PAPER_TRADING and paper:
                balance = paper.get_balance()
                positions = paper.get_positions()
            else:
                balance = client.get_balance()
                positions = client.get_positions()

            # --- Kill switch check ---
            if risk.check_kill_switch(balance):
                log.critical("Kill switch active — stopping bot.")
                break

            risk.log_status(balance, positions)

            total_contracts = sum(abs(p.get("position", 0)) for p in positions)
            log_cycle(balance, total_contracts, starting_balance)

            # --- Run strategy on all weather series ---
            run_all_markets(client, risk, positions, paper=paper)

        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error(f"Unexpected error in main loop: {e}", exc_info=True)

        # --- Wait before next cycle ---
        if not shutdown_requested:
            log.info(f"Sleeping {LOOP_INTERVAL_SEC}s until next cycle...")
            for _ in range(LOOP_INTERVAL_SEC):
                if shutdown_requested:
                    break
                time.sleep(1)

    # --- Graceful shutdown ---
    log.info("\nShutting down — cancelling all open orders...")
    if client:
        cancel_all_open_orders(client)

    if PAPER_TRADING and paper:
        log.info("\n=== PAPER TRADING FINAL SUMMARY ===")
        paper.print_summary()
    log.info("Bot stopped. Check bot.log and bot_log.db for full history.")


if __name__ == "__main__":
    main()