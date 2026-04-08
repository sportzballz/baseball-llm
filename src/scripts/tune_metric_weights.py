#!/usr/bin/env python3
import itertools
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.objects import AdvantageScore
from connector.matchup_metrics import apply_cached_metrics_to_advantage


@dataclass
class Sample:
    game_pk: int
    home: str
    away: str
    winner: str
    metric: dict


def load_metric_files(days=7):
    root = Path(__file__).resolve().parents[2] / "data" / "matchup-metrics"
    files = sorted(root.glob("*.json"), reverse=True)[:days]
    out = []
    for p in files:
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        out.append(data)
    return out


def fetch_winner(game_pk: int):
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    d = json.loads(urlopen(url, timeout=25).read().decode("utf-8"))
    gd = d.get("gameData") or {}
    ls = ((d.get("liveData") or {}).get("linescore") or {})
    home_name = (((gd.get("teams") or {}).get("home") or {}).get("name"))
    away_name = (((gd.get("teams") or {}).get("away") or {}).get("name"))
    hr = (((ls.get("teams") or {}).get("home") or {}).get("runs"))
    ar = (((ls.get("teams") or {}).get("away") or {}).get("runs"))
    status = ((gd.get("status") or {}).get("detailedState") or "")

    if hr is None or ar is None:
        return None, status
    if hr == ar:
        return None, status
    return (home_name if hr > ar else away_name), status


def build_samples(metric_payloads):
    samples = []
    winner_cache = {}

    for payload in metric_payloads:
        for m in payload.get("matchups", []) or []:
            pk = m.get("game_pk")
            if not pk:
                continue
            if pk not in winner_cache:
                try:
                    winner_cache[pk] = fetch_winner(pk)
                except Exception:
                    winner_cache[pk] = (None, "error")
            winner, status = winner_cache[pk]
            if winner is None:
                continue
            samples.append(
                Sample(
                    game_pk=int(pk),
                    home=((m.get("home") or {}).get("name") or ""),
                    away=((m.get("away") or {}).get("name") or ""),
                    winner=winner,
                    metric=m,
                )
            )

    return samples


def predict_side(metric, weights):
    # Inject weights via env to reuse production logic.
    for k, v in weights.items():
        os.environ[k] = str(v)

    idx = {
        "by_game_pk": {int(metric.get("game_pk")): metric},
        "by_matchup": {},
        "meta": {"found": True},
    }
    fake_game_data = {
        "gamePk": int(metric.get("game_pk")),
        "gameData": {
            "teams": {
                "home": {"name": ((metric.get("home") or {}).get("name"))},
                "away": {"name": ((metric.get("away") or {}).get("name"))},
            }
        },
    }

    adv = AdvantageScore(home=0, away=0, home_stats=[], away_stats=[])
    adv, _ = apply_cached_metrics_to_advantage(adv, fake_game_data, idx, weight=1.0)
    if adv.home >= adv.away:
        return ((metric.get("home") or {}).get("name"))
    return ((metric.get("away") or {}).get("name"))


def score_weights(samples, weights):
    if not samples:
        return 0.0, 0, 0
    correct = 0
    for s in samples:
        pred = predict_side(s.metric, weights)
        if pred == s.winner:
            correct += 1
    total = len(samples)
    return correct / total, correct, total


def main():
    payloads = load_metric_files(days=10)
    samples = build_samples(payloads)
    if not samples:
        print("No finalized samples available for tuning.")
        return

    grid = [0.5, 0.75, 1.0, 1.25, 1.5]
    best = None

    for wm, wp, wo, wb, wc in itertools.product(grid, grid, grid, grid, grid):
        w = {
            "METRIC_WEIGHT_MARKET": wm,
            "METRIC_WEIGHT_PITCHING": wp,
            "METRIC_WEIGHT_OFFENSE": wo,
            "METRIC_WEIGHT_BULLPEN": wb,
            "METRIC_WEIGHT_CONTEXT": wc,
        }
        acc, correct, total = score_weights(samples, w)
        rec = (acc, correct, total, w)
        if (best is None) or (rec[0] > best[0]):
            best = rec

    acc, correct, total, w = best
    print(f"samples={total} correct={correct} acc={acc:.4f}")
    print("recommended weights:")
    print(json.dumps(w, indent=2))


if __name__ == "__main__":
    main()
