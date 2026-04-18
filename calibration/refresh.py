"""Nightly calibration refresh.

Reads the rolling 30-day window of scan files, joins each scan candidate
with its settled outcome, and reports per-strategy:
  - n_scans: total candidates surfaced
  - n_settled: count with known outcome
  - avg_model_p: mean model-predicted Yes probability
  - realized_rate: empirical Yes rate of the underlying events
  - log_loss, brier: calibration quality scalars
  - reliability curve (10 buckets)

Also produces a per-sport model-level reliability report by bucketing
pregame-model predictions against settlement outcomes.

Emits:
  dashboard/data/calibration.json
  dashboard/data/calibration_reliability.svg   (tiny inline SVG per sport)

If <30 days of settled data exist, returns a `warming_up: True` flag
and leaves the dashboard banner in a "waiting for data" state.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

log = logging.getLogger("calibration.refresh")
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "dashboard" / "data"
ARCHIVE_DIR = DATA_DIR  # scan_*.json lives here too
WINDOW_DAYS = 30


# ---------------------------------------------------------------------------
# Load scans + settled outcomes
# ---------------------------------------------------------------------------
def load_window(window_days: int = WINDOW_DAYS) -> list[dict]:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=window_days)
    files = sorted(ARCHIVE_DIR.glob("scan_*.json"))
    rows = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            ts = dt.datetime.fromisoformat(data["scanned_at"])
            if ts < cutoff:
                continue
            for c in data.get("top_live", []) + data.get("top_shadow", []):
                rows.append(c)
        except Exception as e:  # noqa: BLE001
            log.warning("skip %s: %s", f, e)
    return rows


def load_settlements() -> dict[str, bool]:
    """Load settled outcomes. In production, pulled from Kalshi /settlements.
    For v1 we look for an optional `settlements.json` produced out-of-band."""
    p = DATA_DIR / "settlements.json"
    if not p.exists():
        return {}
    try:
        return {k: bool(v) for k, v in json.loads(p.read_text()).items()}
    except Exception as e:  # noqa: BLE001
        log.warning("settlements parse: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def _clip(p: float, eps: float = 1e-6) -> float:
    return min(1 - eps, max(eps, p))


def log_loss(labels: list[bool], probs: list[float]) -> float:
    if not labels:
        return 0.0
    s = 0.0
    for y, p in zip(labels, probs):
        p = _clip(p)
        s += -(math.log(p) if y else math.log(1 - p))
    return s / len(labels)


def brier(labels: list[bool], probs: list[float]) -> float:
    if not labels:
        return 0.0
    return sum((int(y) - p) ** 2 for y, p in zip(labels, probs)) / len(labels)


def reliability_curve(labels: list[bool], probs: list[float], n_buckets: int = 10) -> list[dict]:
    buckets = [[] for _ in range(n_buckets)]
    for y, p in zip(labels, probs):
        idx = min(n_buckets - 1, int(p * n_buckets))
        buckets[idx].append((p, y))
    out = []
    for i, b in enumerate(buckets):
        if not b:
            out.append({"bucket_lo": i / n_buckets, "bucket_hi": (i + 1) / n_buckets,
                        "n": 0, "avg_p": None, "realized": None})
            continue
        ps = [x[0] for x in b]
        ys = [int(x[1]) for x in b]
        out.append({
            "bucket_lo": round(i / n_buckets, 3),
            "bucket_hi": round((i + 1) / n_buckets, 3),
            "n": len(b),
            "avg_p": round(sum(ps) / len(ps), 4),
            "realized": round(sum(ys) / len(ys), 4),
        })
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def compute() -> dict:
    rows = load_window(WINDOW_DAYS)
    settlements = load_settlements()

    by_strategy: dict[str, list[dict]] = defaultdict(list)
    by_sport: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        sid = r.get("strategy_id")
        sport = r.get("sport")
        if sid:
            by_strategy[sid].append(r)
        if sport:
            by_sport[sport].append(r)

    per_strategy = {}
    for sid, items in by_strategy.items():
        settled = [(r, settlements[r["market_ticker"]]) for r in items
                   if r["market_ticker"] in settlements]
        labels = [y for _, y in settled]
        probs = [r["model_p_yes"] for r, _ in settled]
        per_strategy[sid] = {
            "n_scans": len(items),
            "n_settled": len(settled),
            "avg_model_p": round(sum(probs) / len(probs), 4) if probs else 0.0,
            "realized_rate": round(sum(labels) / len(labels), 4) if labels else 0.0,
            "log_loss": round(log_loss(labels, probs), 4) if labels else 0.0,
            "brier": round(brier(labels, probs), 4) if labels else 0.0,
            "reliability": reliability_curve(labels, probs) if labels else [],
        }

    per_sport = {}
    for sport, items in by_sport.items():
        settled = [(r, settlements[r["market_ticker"]]) for r in items
                   if r["market_ticker"] in settlements]
        labels = [y for _, y in settled]
        probs = [r["model_p_yes"] for r, _ in settled]
        per_sport[sport] = {
            "n_scans": len(items),
            "n_settled": len(settled),
            "log_loss": round(log_loss(labels, probs), 4) if labels else 0.0,
            "brier": round(brier(labels, probs), 4) if labels else 0.0,
            "reliability": reliability_curve(labels, probs) if labels else [],
        }

    warming_up = sum(v["n_settled"] for v in per_strategy.values()) < 30

    out = {
        "refreshed_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "window_days": WINDOW_DAYS,
        "warming_up": warming_up,
        "n_scans_total": len(rows),
        "n_scans_settled": sum(v["n_settled"] for v in per_strategy.values()),
        "per_strategy": per_strategy,
        "per_sport": per_sport,
    }
    (DATA_DIR / "calibration.json").write_text(json.dumps(out, indent=2))
    return out


def main():
    logging.basicConfig(level=logging.INFO)
    sys.path.insert(0, str(REPO_ROOT))
    out = compute()
    print(json.dumps({
        "warming_up": out["warming_up"],
        "n_settled": out["n_scans_settled"],
        "strategies": list(out["per_strategy"].keys()),
    }, indent=2))


if __name__ == "__main__":
    main()
