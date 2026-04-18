"""Kalshi fee model (post-July 2025 schedule).

Taker fee per contract:  ceil(0.07   * C * P * (1-P))  cents
Maker fee per contract:  ceil(0.0175 * C * P * (1-P))  cents

Where C = number of contracts, P = price in dollars (0..1).
ceil() is applied once to the *total* fee per order (not per contract).

References
----------
- https://kalshi.com/fee-schedule
- https://kalshi.com/docs/kalshi-fee-schedule.pdf
"""
from __future__ import annotations

import math
from dataclasses import dataclass


TAKER_COEF = 0.07
MAKER_COEF = 0.0175


def fee_cents(contracts: int, price: float, role: str = "taker") -> int:
    """Return the Kalshi fee in whole cents for a single-order fill.

    Parameters
    ----------
    contracts : number of contracts filled in the order (C)
    price     : fill price in dollars (0..1)
    role      : 'taker' or 'maker'
    """
    if contracts <= 0:
        return 0
    if not (0.0 <= price <= 1.0):
        raise ValueError(f"price out of range: {price}")
    coef = TAKER_COEF if role == "taker" else MAKER_COEF
    raw = coef * contracts * price * (1.0 - price) * 100.0  # in cents
    return math.ceil(raw)


def round_trip_fee_cents(contracts: int, entry_px: float, exit_px: float,
                         entry_role: str = "taker", exit_role: str = "taker") -> int:
    """Total fees in cents for open + close of a position."""
    return fee_cents(contracts, entry_px, entry_role) + fee_cents(contracts, exit_px, exit_role)


def min_edge_cents(price: float, role: str = "taker", contracts: int = 100) -> float:
    """Breakeven edge in cents per contract needed to cover round-trip at `price`.

    Assumes settlement against the same side (enter at P, resolve in favor at 100¢
    — approximation). Useful as a quick hurdle filter.
    """
    # Approx: if we enter at P and resolve at $1 (win), we pay entry fee + 0 settlement fee
    # Expected edge must cover the entry fee in expectation.
    # Use price as also exit price for a neutral closeout scenario.
    rt = round_trip_fee_cents(contracts, price, price, role, role)
    return rt / contracts  # cents per contract


@dataclass
class FeeAwareQuote:
    """A price adjusted for fees so EV is comparable across price points."""
    raw_price: float     # dollars
    role: str            # 'taker' or 'maker'
    contracts: int
    effective_cost: float  # dollars per contract including fee

    @classmethod
    def from_buy(cls, price: float, contracts: int, role: str = "taker") -> "FeeAwareQuote":
        fee_d = fee_cents(contracts, price, role) / 100.0 / contracts
        return cls(price, role, contracts, price + fee_d)


if __name__ == "__main__":
    print(f"{'Price':>8} {'Taker/100':>10} {'Maker/100':>10} {'MinEdge¢':>10}")
    for p in [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]:
        t = fee_cents(100, p, "taker")
        m = fee_cents(100, p, "maker")
        mx = min_edge_cents(p)
        print(f"{p:>8.2f} {t:>10d} {m:>10d} {mx:>10.2f}")
