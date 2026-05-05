# ============================================================
#  risk.py — position tracking and kill switch
# ============================================================

import logging
from config import MAX_CONTRACTS_PER_MARKET, MAX_TOTAL_CONTRACTS, MAX_LOSS_DOLLARS

log = logging.getLogger("risk")


class RiskManager:
    def __init__(self, starting_balance_cents: int):
        self.starting_balance = starting_balance_cents
        self.kill_switch_triggered = False

    def check_kill_switch(self, current_balance_cents: int) -> bool:
        """Returns True if the bot should stop trading."""
        if self.kill_switch_triggered:
            return True

        loss_cents = self.starting_balance - current_balance_cents
        loss_dollars = loss_cents / 100.0

        if loss_dollars >= MAX_LOSS_DOLLARS:
            log.critical(
                f"KILL SWITCH TRIGGERED — Loss: ${loss_dollars:.2f} "
                f"(limit: ${MAX_LOSS_DOLLARS}). Shutting down."
            )
            self.kill_switch_triggered = True
            return True

        return False

    def position_size_for(self, ticker: str, positions: list, desired: int) -> int:
        """
        Returns how many contracts we're allowed to add for a given market,
        respecting per-market and total limits.
        """
        # Current position in this specific market
        market_pos = next(
            (p for p in positions if p.get("ticker") == ticker), None
        )
        current_in_market = 0
        if market_pos:
            current_in_market = abs(
                market_pos.get("position", 0)
            )

        # Total contracts across all markets
        total_held = sum(abs(p.get("position", 0)) for p in positions)

        # Per-market headroom
        headroom_market = MAX_CONTRACTS_PER_MARKET - current_in_market
        # Total headroom
        headroom_total = MAX_TOTAL_CONTRACTS - total_held

        allowed = min(desired, headroom_market, headroom_total)

        if allowed <= 0:
            log.debug(f"No room to add {ticker}: market={current_in_market}, total={total_held}")

        return max(0, allowed)

    def log_status(self, current_balance_cents: int, positions: list):
        loss = (self.starting_balance - current_balance_cents) / 100.0
        total_contracts = sum(abs(p.get("position", 0)) for p in positions)
        sign = "+" if loss <= 0 else "-"
        log.info(
            f"Balance: ${current_balance_cents/100:.2f} | "
            f"P&L: {sign}${abs(loss):.2f} | "
            f"Open contracts: {total_contracts}"
        )
