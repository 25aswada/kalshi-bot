# ============================================================
#  paper_trading.py — simulated portfolio for paper trading
# ============================================================

import logging
from config import PAPER_STARTING_BALANCE

log = logging.getLogger("paper")


class PaperPortfolio:
    def __init__(self):
        self.balance_cents = PAPER_STARTING_BALANCE
        self.positions = {}   # ticker -> {side, contracts, avg_price_cents}
        self.trade_log = []

    def get_balance(self):
        return self.balance_cents

    def get_positions(self):
        """Return positions in same format as Kalshi API."""
        result = []
        for ticker, pos in self.positions.items():
            result.append({
                "ticker": ticker,
                "position": pos["contracts"],
                "side": pos["side"],
            })
        return result

    def place_order(self, ticker, side, price_cents, count):
        cost = price_cents * count
        if cost > self.balance_cents:
            log.warning(f"  [PAPER] Insufficient balance (have {self.balance_cents}c, need {cost}c)")
            return None

        self.balance_cents -= cost

        if ticker not in self.positions:
            self.positions[ticker] = {"side": side, "contracts": 0, "avg_price_cents": price_cents}

        pos = self.positions[ticker]
        total_contracts = pos["contracts"] + count
        pos["avg_price_cents"] = (
            (pos["avg_price_cents"] * pos["contracts"] + price_cents * count) / total_contracts
        )
        pos["contracts"] = total_contracts
        pos["side"] = side

        trade = {
            "ticker": ticker,
            "side": side,
            "price_cents": price_cents,
            "count": count,
            "cost_cents": cost,
            "balance_after": self.balance_cents,
        }
        self.trade_log.append(trade)

        log.info(
            f"  [PAPER] {side.upper()} {count}x {ticker} @ {price_cents}c "
            f"| cost=${cost/100:.2f} | balance=${self.balance_cents/100:.2f}"
        )
        return {"order": {"order_id": f"paper-{len(self.trade_log)}"}}

    def settle_market(self, ticker, won: bool):
        """
        Call when a market resolves. If won=True, YES contracts pay $1 each.
        Updates balance accordingly.
        """
        if ticker not in self.positions:
            return
        pos = self.positions.pop(ticker)
        contracts = pos["contracts"]
        side = pos["side"]

        payout = 0
        if (side == "yes" and won) or (side == "no" and not won):
            payout = contracts * 100  # $1 per contract in cents
            self.balance_cents += payout

        log.info(
            f"  [PAPER] SETTLED {ticker} | won={won} | "
            f"payout=${payout/100:.2f} | balance=${self.balance_cents/100:.2f}"
        )

    def print_summary(self):
        log.info(f"[PAPER] Balance: ${self.balance_cents/100:.2f}")
        log.info(f"[PAPER] Open positions: {len(self.positions)}")
        for ticker, pos in self.positions.items():
            log.info(
                f"  {ticker}: {pos['contracts']}x {pos['side'].upper()} "
                f"@ avg {pos['avg_price_cents']}c"
            )
        log.info(f"[PAPER] Total trades: {len(self.trade_log)}")
        pnl = self.balance_cents - PAPER_STARTING_BALANCE
        sign = "+" if pnl >= 0 else ""
        log.info(f"[PAPER] P&L: {sign}${pnl/100:.2f}")