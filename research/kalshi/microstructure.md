# Kalshi Sports Contracts — Market Microstructure

_Last updated: April 2026. Author: research agent. Status: living document._

## 0. Executive snapshot

Kalshi's sports ecosystem is a CFTC-regulated binary-outcome book with a mostly-retail taker population, a thin-but-growing professional market-maker population, and a structural edge for liquidity providers against biased retail flow. The empirically-documented inefficiencies — longshot overpricing at the low tail, favorite under/overpricing at the high tail, and emotional-market mispricing — translate into exploitable edges **if and only if** the strategy can pay fees, cross the spread tactically, and size around liquidity constraints. This document is the quantitative scaffolding for Phases 2–6.

## 1. Regulatory and platform context

Kalshi is registered with the CFTC as a Designated Contract Market (DCM), approved in 2020, with full sports event contracts live since January 24, 2025. The legal landscape as of April 2026 is:

- **Federal:** On April 6, 2026, the Third Circuit affirmed preliminary injunctions in Kalshi's favor, holding that the Commodity Exchange Act likely preempts state gambling laws as applied to sports event contracts listed on CFTC-registered DCMs. Similar federal district court outcomes occurred in Nevada and New Jersey. [Skadden memo](https://www.skadden.com/insights/publications/2026/04/third-circuit-affirms-kalshis-preliminary-injunction) | [Holland & Knight analysis](https://www.hklaw.com/en/insights/publications/2026/04/federal-appeals-court-cftc-jurisdiction-over-sports-event-contracts)
- **CFTC rulemaking:** Public comment period on sports event contracts open through April 30, 2026; the CFTC must decide by Q3 2026 whether to formally approve, restrict, or prohibit.
- **State counter-actions:** Massachusetts Suffolk Superior Court issued a preliminary injunction in January 2026 restricting Kalshi's in-state sports contract activity. Active cease-and-desist postures (or litigation) in MA, MD, NV (partially), NJ (partially), OH, MI, MT, AZ, IL.

**Investment implication:** state-specific enforcement risk is real and episodic. Any live deployment should monitor state-level developments weekly. A Massachusetts-style injunction can evaporate access overnight; this is a non-trivial tail risk that must sit on top of model edge.

## 2. Contract taxonomy

Kalshi lists sports contracts in three main topological families:

| Family | Structure | Typical resolution | Liquidity profile |
|---|---|---|---|
| Single-game binary | `TEAM_A_WINS` vs. `TEAM_A_LOSES` (or ML-style Yes/No) | 2-4 hours post-start | Highest liquidity; tightest spreads near 50¢, wide at tails |
| Series (MLB postseason, NBA/NHL playoffs) | Binary on series winner, 4-game to 7-game | 5-20 days | Medium liquidity; large ticks early, convergence late |
| Futures / season-long | Division winner, conference winner, championship | 1-9 months | Lowest liquidity; heavy retail; largest structural mispricing |
| Player props | "Player X scores > N" | Game-day | New, sparse liquidity as of 2026; inefficient |
| Live / in-game | Repricing same contract during play | Real-time | Episodic liquidity, wide spreads during volatility bursts |

Contracts trade 0-100¢ (1¢ ticks) and settle at $0 or $1 per contract. Kalshi uses a CLOB (central limit order book) with make/take interaction; no AMM, no LMSR. This matters for strategy design — order placement is the alpha, not market-making curvature.

## 3. Fees and edge threshold

Post-July-2025 fee schedule (both maker and taker scale with probability):
- **Taker fee per contract:** `ceil(0.07 × C × P × (1 − P))` cents, where P is price in dollars, C is contracts
- **Maker fee per contract:** `ceil(0.0175 × C × P × (1 − P))` cents (was flat $0.0025 before July 2025)

Key implications at single contract (C=1):

| Price | Taker fee | Maker fee | Round-trip cost as % of capital |
|---|---|---|---|
| 5¢ | 0.33¢ → ceil 1¢ | 0.08¢ → ceil 1¢ | ~40% round-trip at $0.05/contract cost basis |
| 10¢ | 0.63¢ → ceil 1¢ | 0.16¢ → ceil 1¢ | ~20% |
| 25¢ | 1.31¢ → ceil 2¢ | 0.33¢ → ceil 1¢ | ~12% |
| 50¢ | 1.75¢ → ceil 2¢ | 0.44¢ → ceil 1¢ | ~8% |
| 75¢ | 1.31¢ → ceil 2¢ | 0.33¢ → ceil 1¢ | ~4% |
| 90¢ | 0.63¢ → ceil 1¢ | 0.16¢ → ceil 1¢ | ~2% |

**Critical: the ceil() operator makes low-volume trades at extreme prices extremely expensive in percentage terms.** A 5¢ taker buying 1 contract pays ~20% to enter. Trading at scale (≥ ~70 contracts) smooths this because the ceil() operation only rounds a sub-penny fraction once.

**Edge threshold:** for an edge to be tradable round-trip as a taker against a neutral counterparty (no fee offset), model EV in cents must exceed roughly:
- At 50¢: 3.5¢ (2×1.75¢)
- At 25¢ or 75¢: 2.6¢
- At 10¢ or 90¢: 1.3¢
- At 5¢ or 95¢: 0.7¢

Plus slippage. Treat **4¢ expected edge at mid-range** and **1.5¢ at tails** as minimum filters. Sources: [Kalshi fee schedule](https://kalshi.com/fee-schedule) | [Karl Whelan working paper (UCD)](https://www.ucd.ie/economics/t4media/WP2025_19.pdf) | [Deadspin fee analysis](https://deadspin.com/prediction-markets/kalshi/fees/).

## 4. Retail flow signatures and behavioral inefficiencies

Two independent large-scale empirical analyses converge on the same picture:

### 4.1 Becker (2025) — 72.1M trade microstructure analysis

Jonathan Becker's analysis of 72.1 million Kalshi trades ([source](https://www.jbecker.dev/research/prediction-market-microstructure)) documents a **systematic wealth transfer from takers to makers**, distinct from information asymmetry — i.e., makers profit structurally, not via superior forecasting. Specific findings relevant for strategy construction:

1. **Longshot overpricing at the low tail.** Contracts priced at 5¢ win only 4.18% of the time, implying −16.4% mispricing (P implied by market is too high by ~0.8¢). This pattern is consistent for all contracts priced < 20¢.
2. **Favorite underpricing at the high tail.** Contracts above 80¢ outperform their implied probability (the mirror of the 5¢ case). 95¢ contracts resolve 95.83% Yes.
3. **Makers buying YES earn +0.77% excess return; makers buying NO earn +1.25% excess return.** This is structural premium, not pick-skill.
4. **Emotional-engagement markets show largest biases.** Election, high-profile sports, and polarizing cultural markets exhibit the strongest taker-pays-premium effect. Routine markets (weather, GDP, etc.) are closer to efficient.
5. **Volume surge post-Oct-2024 legal victory attracted professional LPs** who partially arb'd the retail bias. Implication: the edges have been compressing since late 2024 but remain exploitable in sports-specific contract subcategories with thin pro participation.

### 4.2 Whelan (2025) — Makers and Takers economics paper

Karl Whelan's working paper ([UCD Working Paper 2025/19](https://www.ucd.ie/economics/t4media/WP2025_19.pdf)) models Kalshi's microstructure as a two-sided market where the maker fee schedule (low) combined with retail taker behavior (aggressive, emotional) yields a stable equilibrium of positive expected maker return. Key results:

- Average maker earns ~1.0-1.5% per round-trip after fees in mature markets.
- Taker loss is concentrated in high-emotion, low-information markets.
- Average contract spread on sports single-game binary is 2-4¢ near 50¢ probability, widening to 5-10¢ at tails.

### 4.3 Sports-specific taker biases (literature)

The academic favorite-longshot bias literature applied to Kalshi sports:

- **Baseball:** Garrett & Nowotny (see Snowberg & Wolfers ([NBER 15923](https://www.nber.org/system/files/working_papers/w15923/w15923.pdf))) find *no* favorite-longshot bias in baseball moneyline markets — bettors appear to price baseball more rationally. Kalshi MLB data confirms this qualitatively; longshot edges in MLB are smaller than in NBA/NFL.
- **College football / basketball:** Shank (2017) finds persistent favorite-longshot bias in college sports moneyline markets ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1062976916000041)). This *should* transfer to Kalshi CBB contracts.
- **NFL:** moderate longshot bias in NFL moneyline; stronger in weekly Super Bowl futures where home-bias and popular-team-bias dominate.
- **Prospect-theory explanation.** Snowberg & Wolfers find misperception of probabilities (prospect theory) explains bias better than risk-love. Implication: bias concentrates in markets where retail can't compute probabilities well (longshots, multi-leg futures, unfamiliar sports).

### 4.4 Structural strategy implications

| Observed inefficiency | Strategy hook | Expected edge |
|---|---|---|
| Sub-20¢ longshot overpricing | Short (sell YES / buy NO) tail contracts where model agrees | 50-200 bps / trade |
| Above-80¢ favorite underpricing | Long (buy YES) favorites where model agrees | 50-150 bps / trade |
| High-emotion markets mispriced | Overweight position size in polarizing matchups (rivalry games, home-favorite contests) when model disagrees with crowd | additive 50-100 bps |
| Retail futures bias | Fade popular futures (AL East winner Yankees, NBA championship Lakers) when model implied ≠ market | 100-300 bps on season-long contracts |
| Time-decay on settled info | Enter post-injury-report / post-weather-report when market lags by >10 min | 30-100 bps |

These are *maximum achievable* edges at thin size; real net-of-fee edges after the fee table above will be ~30-50% smaller.

## 5. Liquidity profile

From Kalshi public data and [kalshidata.com](https://www.kalshidata.com/), plus Kalshi's own research portal ([research.kalshi.com](https://research.kalshi.com/)):

- **Typical NBA/NFL single-game binary pre-tip liquidity:** $50k-$500k depth within 3¢ of mid on top-tier games; $5k-$50k on mid-tier; $500-$5k on low-profile matchups.
- **MLB regular-season single-game:** $5k-$50k depth for contenders, $500-$5k for weaker markets. Baseball liquidity is materially lower than NBA/NFL.
- **Series markets (playoffs):** $20k-$200k on popular series (Lakers-Celtics, Yankees-Dodgers); $2k-$20k on less popular.
- **Futures:** $5k-$50k aggregate open interest on high-profile (Super Bowl winner, NBA champ); under $5k on division/conference. Spreads often 3-8¢ wide.
- **Player props:** nascent as of April 2026. Liquidity <$1k per contract is common. High edge but severe capacity constraint.

**Capacity model for strategy sizing:**
- Daily dollar volume on sports contracts: ~$80-200M per day during peak season (Oct-Nov football overlap).
- Depth within 2¢ of mid for target contracts typically 0.5-2% of daily volume.
- A strategy consistently trading 200 bps edge can likely deploy $500k-$2M of AUM across sports before its own order flow begins to reprice markets.
- Above $5M AUM, edge compression from self-impact dominates; this is retail-adjacent capital, not institutional scale.

Sources: [kalshidata.com](https://www.kalshidata.com/) | [Kalshi research](https://research.kalshi.com/) | [Ainvest volume analysis](https://www.ainvest.com/news/kalshi-20b-volume-surge-liquidity-catalyst-fee-trap-2604/).

## 6. Time decay and intra-day dynamics

Observed patterns (from Kalshi CLOB snapshots and community analytics):

1. **Pre-game efficient zone.** Single-game markets converge toward sportsbook-implied probability in the 2-hour window before start. Edges erode ~30-60% in this window as sharps arb the book against DraftKings/FanDuel/Pinnacle.
2. **Lineup-news step function.** Announcements (starting pitcher, NBA scratches, QB injury) produce 2-10¢ discontinuous repricings. Markets frequently over-react in first 5-10 min, under-react for 1-3 hours after weird news (backup-QB starts, unusual lineup changes).
3. **Live in-game vol.** Repricing during play exhibits wider spreads (5-15¢ during volatility) and frequent lags relative to actual win-probability models (DraftKings live WP, nflfastR EPA-based live WP). Fastest arb is reading opposing-platform live WP vs. Kalshi mid.
4. **Favorites decay differently.** 85¢+ favorites show positive time-decay (they drift up toward fair) for the final 24 hours before game; longshots decay down.
5. **Series settlement mechanics.** Game-by-game updates cause series-contract repricings that frequently over-react to single-game outcomes (e.g., 1-0 lead in a 7-game series moves series price more than Bayesian update warrants).

## 7. Settlement mechanics

- Contracts resolve at $0 or $1 upon CFTC-approved settlement source (typically official league stats or a designated data provider).
- No settlement fee.
- Resolution delay: typically 2-12 hours post-event end; occasionally longer for series/futures resolution on non-standard outcomes.
- **Edge case: settlement disputes.** Rare but have occurred (delayed MLB game resolution, NBA preseason rule ambiguities). Settlement source documented per contract; worth reading each contract's fine print.
- **Early-exit liquidity.** Because binaries are tradable until settlement, one can harvest gains before resolution — useful for risk management and to avoid capital-lock during late-resolution contracts.

## 8. Market-maker presence

Evidence of professional LPs (from Becker 2025 and community observation):

- Pre-Oct-2024: mostly retail, wide spreads, thin depth.
- Oct-2024 through present: several specialist LPs now consistent in single-game sports markets. Identifiable by order-flow patterns (1-2¢ wide quotes, $5k-$50k depth, rapid repricing on fundamental news).
- **Implication:** make-take strategies for us are hard — professional LPs already capture the easy spread. Our edge must come from **model disagreement with market** (Phase 2), not from liquidity provision.
- Futures, player props, and regional/niche contracts remain LP-thin. Those are where naive taker edges still pay.

## 9. Structural-inefficiency taxonomy (Phase 1 deliverable)

Distilled from the above, ranked by robustness of empirical support:

| Rank | Inefficiency | Empirical support | Sports where strongest |
|---|---|---|---|
| 1 | Sub-20¢ longshot overpricing | Strong (Becker 72M trades + academic FL-bias lit) | CBB, NFL moneyline upsets, MMA dogs, golf outrights |
| 2 | Above-80¢ favorite mispricing (mixed direction) | Strong (Becker) | Most sports; direction varies — Kalshi favorites typically *underpriced* vs. prob, opposite of traditional FL-bias |
| 3 | High-emotion market overpricing | Strong (Becker) | Rivalry games, playoff games, postseason futures |
| 4 | Retail futures bias (popular team premium) | Moderate | NBA champ odds, NFL Super Bowl, World Series futures |
| 5 | Lineup-news reaction lag | Moderate (community observation) | MLB starter changes, NBA load-management scratches |
| 6 | Live-WP lag vs. other platforms | Moderate | NFL and NBA live markets |
| 7 | Series overreaction to single-game result | Weak (community observation; limited formal study) | NBA playoff series, MLB postseason |
| 8 | Weather-report reaction lag | Weak | MLB, NFL outdoor stadiums |

## 10. Folklore vs. evidence

Flagging claims I've seen in community discussion that are **not** well-supported:

- ❌ "Kalshi is always more efficient than DraftKings because of pros." → False at tails and on non-marquee markets; Becker data shows persistent pricing gaps vs. sportsbook no-vig.
- ❌ "Market makers on Kalshi have superior information." → False per Becker: maker YES and NO returns are nearly symmetric positive → structural, not informational edge.
- ❌ "Liquidity at tails is fake / spoofed." → Not demonstrated in any serious work; community paranoia.
- ✅ "Settlement is reliable modulo rare edge cases." → Supported; document those edge cases per contract.
- ⚠️ "Fees are cheap." → Mixed; cheap at mid-range in-scale, expensive at tails at small size due to ceil() rounding.

## 11. Strategy-design takeaways (feeds Phase 3)

1. **Our edge must come from probability estimation, not market making.** Professional LPs dominate make-take in single-game binary.
2. **Size matters for fees.** Round 70+ contracts per trade where possible to avoid ceil() drag.
3. **Prefer taker at 10¢ and 90¢ tails when model disagrees.** Fee drag is small in cents, edge is large in cents.
4. **Avoid mid-range taker without >5¢ edge.** Net-of-fee EV doesn't clear hurdle.
5. **Futures and props are the thickest retail targets.** Structural bias strongest, LP competition weakest. Primary strategy focus.
6. **Live markets are secondary but valuable.** Need low-latency data pipe and live-WP model from open-source sports analytics.
7. **Monitor state-legal risk monthly.** A single adverse state ruling can vaporize regional access.

## 12. Bibliography (primary sources)

1. [Kalshi official fee schedule PDF (Feb 2026)](https://kalshi.com/docs/kalshi-fee-schedule.pdf)
2. [Kalshi fee schedule web page](https://kalshi.com/fee-schedule)
3. [Kalshi Help Center – fees](https://help.kalshi.com/trading/fees)
4. [Kalshi research portal](https://research.kalshi.com/)
5. [kalshidata.com dashboard](https://www.kalshidata.com/)
6. Becker, J. (2025). "The Microstructure of Wealth Transfer in Prediction Markets." [jbecker.dev/research/prediction-market-microstructure](https://www.jbecker.dev/research/prediction-market-microstructure)
7. Whelan, K. (2025). "Makers and Takers: The Economics of the Kalshi Prediction Market." UCD Centre for Economic Research Working Paper 2025/19. [PDF](https://www.ucd.ie/economics/t4media/WP2025_19.pdf) and [Karl Whelan personal](https://www.karlwhelan.com/Papers/Kalshi.pdf)
8. Courtney, A. "Maker/Taker Math on Kalshi." Whirligigbear Substack. [link](https://whirligigbear.substack.com/p/makertaker-math-on-kalshi)
9. Snowberg, E. & Wolfers, J. (2010). "Explaining the Favorite-Longshot Bias: Is It Risk-Love or Misperceptions?" *Journal of Political Economy* 118(4). [NBER working paper](https://www.nber.org/system/files/working_papers/w15923/w15923.pdf)
10. Shank, C. (2017). "A Favorite-Longshot Bias in Fixed-Odds Betting Markets." *Quarterly Review of Economics and Finance*. [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1062976916000041)
11. Green, E., Lee, H., Rothschild, D. "The Favorite-Longshot Midas." [Berkeley PDF](https://www.stat.berkeley.edu/~aldous/157/Papers/Green.pdf)
12. Whelan, K. (2024). "Risk aversion and favourite–longshot bias in a competitive fixed-odds betting market." *Economica*. [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/ecca.12500)
13. DataGolf. "The Favourite-Longshot Bias is not a bias" (contrarian view). [link](https://datagolf.com/fav-longshot-not-a-bias)
14. Third Circuit ruling (Apr 6, 2026) – [Skadden analysis](https://www.skadden.com/insights/publications/2026/04/third-circuit-affirms-kalshis-preliminary-injunction)
15. [Holland & Knight, Feb 2026 – "Prediction Markets at a Crossroads"](https://www.hklaw.com/en/insights/publications/2026/02/prediction-markets-at-a-crossroads-the-continued-jurisdictional-battle)
16. [Foley & Lardner analysis June 2025](https://www.foley.com/insights/publications/2025/06/the-cftc-is-shaking-up-sports-bettings-legal-future/)
17. [Stinson LLP – sportsbooks vs. commodity exchanges](https://www.stinson.com/newsroom-publications-sportsbooks-or-commodity-exchanges-the-rising-legal-tensions-between-sports-betting-and-prediction-markets)
18. [BCLP – Sports Event Contract Litigation](https://www.bclplaw.com/en-US/events-insights-news/sports-event-contract-litigation-generates-bizarre-results.html)
19. Croxson, K. & Reade, J. "The Favourite-Longshot Bias, Bookmaker Margins and Insider Trading" [Academia.edu](https://www.academia.edu/16834446/The_Favourite_Longshot_Bias_Bookmaker_Margins_and_Insider_Trading_in_a_Variety_of_Betting_Markets)
20. Kalshi API documentation v3 (technical reference, pulled via API).
