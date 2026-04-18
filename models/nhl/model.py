"""NHL model — STUB.

This sport is NOT YET BUILT for v1. See research/domain/STUB_other_sports.md for
the literature review, intended architecture, and Kalshi edge candidates.

The scanner (core/scanner.py) checks the `not_yet_built` flag and skips any
nhl market it encounters at runtime, so this stub prevents accidental
trading on an unbuilt model.

Intended architecture (v2):
    Team xG differential adjusted for goalie GSAx + Markov regulation/OT/shootout sim
"""
from __future__ import annotations

from dataclasses import dataclass

not_yet_built: bool = True
sport: str = "nhl"
intended_architecture: str = (
    "Team xG differential adjusted for goalie GSAx + Markov regulation/OT/shootout sim"
)


@dataclass
class MatchupInputs:
    """Placeholder. Real spec will arrive when nhl literature review is completed
    to the same depth as MLB/NBA/NFL and this stub is replaced."""
    home: str = ""
    away: str = ""


@dataclass
class Prediction:
    home_win_prob: float = 0.0
    confidence: str = "not_yet_built"
    rationale: str = "nhl model not built in v1"


def predict(_: MatchupInputs) -> Prediction:  # noqa: D401
    """Refuse to predict — model not built."""
    raise NotImplementedError(
        "nhl model not yet built. See research/domain/STUB_other_sports.md "
        "for the research plan. Scanner is expected to skip this sport via "
        "the not_yet_built flag."
    )
