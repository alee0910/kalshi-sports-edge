# Disclaimer

## Not investment advice

This repository is a personal research project. Nothing in it is investment
advice, a solicitation to transact, or a recommendation to trade any
financial instrument. The author and maintainers of this repository are not
registered investment advisers, broker-dealers, or futures commission
merchants.

Past performance — including both synthetic backtest performance and any
live-scanner PnL shown on the dashboard — does not predict future results.
Kalshi event contracts carry a real risk of total loss of principal on any
given contract.

## Kalshi regulatory status (as of April 2026)

Kalshi event contracts are, as of this writing, listed on a CFTC-designated
contract market under the Commodity Exchange Act. Litigation and rulemaking
are active:

- The Third Circuit has affirmed the preliminary injunctions entered in the
  Kalshi vs. New Jersey and Kalshi vs. Nevada matters, allowing Kalshi to
  continue offering sports event contracts in those states pending
  resolution.
- Massachusetts has a state-level injunction in place as of early 2026. No
  orders should be submitted from MA IP addresses while that injunction
  remains in effect.
- The CFTC has an open rulemaking on sports event contracts; the comment
  period closes April 30, 2026. The final rule may materially alter product
  availability or fee structure.

Before trading, **verify** the current status via Kalshi's regulatory
disclosures, the CFTC site, and your own counsel. This document may be out
of date; the April 2026 framing reflects the state of the law at the time
of writing.

## Jurisdiction blocklist

`strategies/registry.py::GLOBAL.jurisdiction_blocklist` currently contains
`("MA",)`. Do not add jurisdictions without legal review.

Puerto Rico, Guam, American Samoa, and US Virgin Islands are excluded by
Kalshi's own eligibility rules and do not need to be re-listed here.

## Self-exclusion and responsible gambling

If you or someone you know has a problem with gambling, call or text
**1-800-GAMBLER** or visit **ncpgambling.org**. Kalshi is a derivatives
exchange, not a sportsbook — but the behavioral risks of frequent sports
contract trading overlap materially with the behavioral risks of sports
betting.

This repo's code is designed to be **model-driven** — no strategy in it
relies on gut feel, hot takes, or parasocial fandom. If you find yourself
manually overriding the scanner, that is a personal-risk signal worth
taking seriously.

## Data sources & licenses

- `nfl_data_py` and `nflfastR`: MIT-licensed public data.
- `mlb_data_py` and MLB Gameday feeds: public but subject to MLB Advanced
  Media's terms of use; commercial redistribution is prohibited.
- `nba_api` stats.nba.com scraper: operates at NBA.com's discretion; respect
  rate limits (`nba_api` default is 30s between calls).
- **No PFF, DataGolf, KenPom, or other paid feeds are included.** Models
  use public data only.
- Kalshi API: personal use under the API terms of service. The API key
  stored as `KALSHI_API_KEY` should never be committed to the repo.

## License

This is a private research repository; see `LICENSE` for the full terms
("All rights reserved", no commercial redistribution). Literature references
in `research/domain/*.md` are cited but not redistributed; follow the links
for the original work.
