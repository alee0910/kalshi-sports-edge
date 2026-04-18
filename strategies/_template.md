# Sxx — Strategy name

## Thesis

One paragraph: what is the mispricing, and why does it persist?

## Market selection

- Which Kalshi markets (by event type, ticker prefix, or rule) this applies to.
- Any state-level / jurisdiction exclusions.

## Entry signal

Pseudocode-level condition(s) triggered by the scanner. Must be deterministic
from public data + model outputs.

## Exit signal

When is the position closed? At settlement? At a reprice threshold? On a stop?

## Sizing

Kelly fraction and any overrides (per-contract cap, per-slate cap, per-sport
cap).

## Fee & slippage handling

Required edge after fees and 1-tick slippage.

## Expected performance (backtest placeholder)

Metrics we'll measure in Phase 4: sample size, hit rate, avg EV per trade, max
drawdown, Sharpe-equivalent, profit factor.

## Risks / failure modes

What kills this strategy? Honest list.

## References

Literature sources that support the thesis.
