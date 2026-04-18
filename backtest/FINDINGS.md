# Backtest findings — v1 synthetic run

**Run:** `python -m backtest.run_all` against synthetic, literature-calibrated
snapshots. This is NOT a historical replay (Kalshi public orderbook tape is
thin pre-2024H2). It measures whether each strategy's entry rule extracts
edge **after fees and one tick of slippage** given snapshots engineered to
respect the strategy's thesis.

## Headline results

| Strategy | Trades | Hit rate | Avg return / trade | Sharpe | PF | Verdict |
|---|---|---|---|---|---|---|
| S01 — FLB fade | 2000 | ~89% | +0.1% | 0.09 | 1.03 | Marginal — thesis clears fees thinly |
| S02 — MLB starter news | 300 | 55% | +13.1% | 1.18 | 1.26 | **Strong** — 0.30× Kelly + maker fee works |
| S03 — NBA series HCA | 120 | 49% | −9.7% | −0.93 | 0.82 | **Fails** — 4¢ threshold too thin for taker fees |
| S04 — NFL weather | 80 | 55% | +3.5% | 0.34 | 1.08 | Marginal — small-sample, weak Sharpe |
| S05 — Popular futures | 40 | 83% | −4.1% | −0.89 | 0.78 | **Fails** — bid-ask + slippage on 5-25¢ contracts eats edge |
| S06 — Stale reprice | 1500 | 50% | −6.2% | −0.57 | 0.90 | **Fails** — 2.5¢ threshold insufficient after taker fee |

## Interpretation

Three findings are robust regardless of synthetic-vs-real data:

1. **Taker-fee math at mid prices is brutal.** At P=0.5 the taker fee is
   ~1.75¢ per contract. Our S03/S06 entry thresholds of 2.5-4¢ gross edge
   leave, on average, **less than 1¢ of net edge after fee + 1-tick slippage**.
   The synthetic data confirms the math: break-even at best, negative after
   bid-ask round-tripping.

2. **Sub-20¢ longshot fade (S01) barely clears.** Even with a literature-
   documented 2-3% overpricing, taker fees compress realized return to
   roughly zero on average. Reaffirms the strategy-spec note that S01 needs
   a **maker-only variant** to be truly profitable.

3. **Popular-team futures short (S05) fails on bid-ask.** Synthetic spreads
   of 2¢ on 5-25¢ contracts effectively erase the 2.5-5% premium. Real
   Kalshi championship markets have tighter spreads in peak liquidity
   (~1¢), so the effect is less severe live, but it's a warning sign.

## Action taken

Rather than retune synthetic generators to make strategies look profitable,
I'm documenting the findings honestly and making two concrete changes:

### Change 1: raise minimum-edge thresholds

| Strategy | v1 threshold | v1.1 threshold | Reason |
|---|---|---|---|
| S01 | 2 pp | **3 pp** | Fee math at 10¢ needs ~2.5¢ edge to break even after taker+slip |
| S03 | 4 pp | **6 pp** | Mid-price fees are ~1.75¢ each side |
| S05 | 2 pp | **3 pp** | Bid-ask on futures contracts eats a full cent |
| S06 | 2.5 pp | **3.5 pp** | Must clear fee + 1 tick slip with margin |

### Change 2: S01 and S06 become maker-preferred

S01 maker-only variant submits resting bids below current best-ask; we fill
only if a sharp buyer exists who wants to pay up. This is slower but the
maker fee (0.0175 coefficient) is 4× cheaper than taker and S01's thesis is
patient by design.

S06 remains taker-preferred in code but the risk register now flags its
Sharpe expectation down from 1.5 to 0.8, and its allocation ceiling is
tightened from 5% to 3% of bankroll.

### Change 3: require post-fee positive EV in a hard assertion

The engine's `simulate_entry` now returns a `net_edge_cents` alongside
`fee`. Strategies that don't show `net_edge_cents > 0` after entry fee and
exit assumption are auto-skipped with a logged warning. This will be wired
into Phase 6's live scanner as well.

## What a real backtest would add

Items to revisit when we pull real historical data in Phase 7:

- **Intraday liquidity variation.** Synthetic depths are uniform; real
  Kalshi books thin out overnight and at game start.
- **Settlement delays.** Kalshi settles quickly but non-zero latency can
  matter for compounded sizing.
- **Correlated outcome days.** My synthetic outcomes are i.i.d.; real sports
  days have slate-level correlations that increase drawdown.
- **Adversarial selection.** Synthetic doesn't model whether our maker
  orders get filled only by smart money.

## Directional confidence

Given these caveats, the v1 strategy book as specified is **credibly
profitable on paper only for S02 (MLB starter news)**. The others require
the v1.1 threshold tightening before live capital. Phase 6 will ship with
S01-S06 all *active* but S03/S05/S06 in **shadow-mode** (scanner logs
would-be trades but does not submit) until calibrated data confirms edge.
