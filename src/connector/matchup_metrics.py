import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def _today_est():
    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def _norm(name):
    return str(name or "").strip().lower()


def _key(home, away):
    return "|".join(sorted([_norm(home), _norm(away)]))


def load_cached_metrics(date_str=None):
    date_str = date_str or _today_est()
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "data" / "matchup-metrics" / f"{date_str}.json"
    if not path.exists():
        return {"by_game_pk": {}, "by_matchup": {}, "meta": {"date": date_str, "found": False, "path": str(path)}}

    try:
        payload = json.loads(path.read_text())
    except Exception:
        return {"by_game_pk": {}, "by_matchup": {}, "meta": {"date": date_str, "found": False, "path": str(path), "error": "parse_failed"}}

    by_game_pk = {}
    by_matchup = {}
    for m in payload.get("matchups", []) or []:
        game_pk = m.get("game_pk")
        if game_pk is not None:
            by_game_pk[int(game_pk)] = m
        home = (((m.get("home") or {}).get("name")) or "")
        away = (((m.get("away") or {}).get("name")) or "")
        by_matchup[_key(home, away)] = m

    return {
        "by_game_pk": by_game_pk,
        "by_matchup": by_matchup,
        "meta": {
            "date": date_str,
            "found": True,
            "path": str(path),
            "odds_source": payload.get("odds_source") or {},
            "count": payload.get("count", 0),
        },
    }


def _safe_float(v):
    try:
        return float(v)
    except Exception:
        return None


def _weight(name: str, default: float = 1.0):
    try:
        return float(os.environ.get(name, str(default)))
    except Exception:
        return default


def get_metric_for_game(metrics_index, game_data):
    if not metrics_index:
        return None

    game_pk = game_data.get("gamePk")
    if game_pk is not None and int(game_pk) in metrics_index.get("by_game_pk", {}):
        return metrics_index["by_game_pk"][int(game_pk)]

    home = (((game_data.get("gameData") or {}).get("teams") or {}).get("home") or {}).get("name")
    away = (((game_data.get("gameData") or {}).get("teams") or {}).get("away") or {}).get("name")
    return metrics_index.get("by_matchup", {}).get(_key(home, away))


def apply_cached_metrics_to_advantage(adv_score, game_data, metrics_index, weight=1.0):
    metric = get_metric_for_game(metrics_index, game_data)
    if not metric:
        return adv_score, None

    home_bonus = 0.0
    away_bonus = 0.0
    reasons = []

    w_market = _weight("METRIC_WEIGHT_MARKET", 1.0)
    w_pitch = _weight("METRIC_WEIGHT_PITCHING", 1.0)
    w_off = _weight("METRIC_WEIGHT_OFFENSE", 1.0)
    w_bp = _weight("METRIC_WEIGHT_BULLPEN", 1.0)
    w_ctx = _weight("METRIC_WEIGHT_CONTEXT", 1.0)

    # Dynamic scaling: when both lineups are announced, offense/context are more reliable.
    lineups = metric.get("lineups") or {}
    both_announced = bool(lineups.get("both_announced"))
    if both_announced:
        w_off *= 1.15
        w_ctx *= 1.15
        reasons.append("lineups_both_announced")
    else:
        w_off *= 0.80
        w_ctx *= 0.80
        reasons.append("lineups_incomplete")

    market = metric.get("market") or {}
    implied_home = _safe_float(market.get("implied_home_prob"))
    if implied_home is not None:
        if implied_home >= 0.60:
            home_bonus += (0.75 * w_market)
            reasons.append(f"market_implied_home={implied_home:.3f}")
        elif implied_home <= 0.40:
            away_bonus += (0.75 * w_market)
            reasons.append(f"market_implied_home={implied_home:.3f}")
        elif implied_home >= 0.55:
            home_bonus += (0.35 * w_market)
            reasons.append(f"market_lean_home={implied_home:.3f}")
        elif implied_home <= 0.45:
            away_bonus += (0.35 * w_market)
            reasons.append(f"market_lean_away={implied_home:.3f}")

    ml_move = _safe_float(market.get("moneyline_move"))
    if ml_move is not None:
        # For home odds in American format: more negative (delta < 0) tends toward home.
        if ml_move <= -15:
            home_bonus += (0.35 * w_market)
            reasons.append(f"moneyline_move_home={ml_move}")
        elif ml_move >= 15:
            away_bonus += (0.35 * w_market)
            reasons.append(f"moneyline_move_away={ml_move}")

    consensus = market.get("consensus") or {}
    ml_range = _safe_float(consensus.get("moneyline_range"))
    ml_outliers = _safe_float(consensus.get("moneyline_outlier_books"))
    books = _safe_float(consensus.get("books"))
    if books is not None and books >= 4 and ml_range is not None and ml_range >= 35:
        # Market disagreement -> reduce confidence / avoid overcommit.
        home_bonus -= (0.10 * w_ctx)
        away_bonus -= (0.10 * w_ctx)
        reasons.append(f"market_dispersion_range={ml_range:.1f}")
    if ml_outliers is not None and ml_outliers >= 2:
        home_bonus -= (0.06 * w_ctx)
        away_bonus -= (0.06 * w_ctx)
        reasons.append(f"market_outliers={int(ml_outliers)}")

    home_pitch = ((((metric.get("home") or {}).get("probable_pitcher") or {}).get("stats") or {}))
    away_pitch = ((((metric.get("away") or {}).get("probable_pitcher") or {}).get("stats") or {}))
    hk = _safe_float(home_pitch.get("k_bb"))
    ak = _safe_float(away_pitch.get("k_bb"))
    if hk is not None and ak is not None:
        diff = hk - ak
        if diff >= 0.6:
            home_bonus += (0.30 * w_pitch)
            reasons.append(f"pitcher_kbb_home_edge={diff:.2f}")
        elif diff <= -0.6:
            away_bonus += (0.30 * w_pitch)
            reasons.append(f"pitcher_kbb_away_edge={abs(diff):.2f}")

    park = metric.get("park_factors") or {}
    run_factor = _safe_float(park.get("run_factor"))
    hr_factor = _safe_float(park.get("hr_factor"))
    if run_factor is not None and hr_factor is not None:
        # In run-suppressing parks, give small bonus to stronger starting pitching profile.
        if run_factor <= 0.96 and hr_factor <= 0.93:
            h_k9 = _safe_float(((((metric.get("home") or {}).get("probable_pitcher") or {}).get("advanced") or {}).get("k9")))
            a_k9 = _safe_float(((((metric.get("away") or {}).get("probable_pitcher") or {}).get("advanced") or {}).get("k9")))
            if h_k9 is not None and a_k9 is not None:
                k9_diff = h_k9 - a_k9
                if k9_diff >= 0.8:
                    home_bonus += (0.10 * w_ctx)
                    reasons.append(f"park_pitch_home_edge={k9_diff:.2f}")
                elif k9_diff <= -0.8:
                    away_bonus += (0.10 * w_ctx)
                    reasons.append(f"park_pitch_away_edge={abs(k9_diff):.2f}")

    lineups = metric.get("lineups") or {}
    hp = _safe_float(lineups.get("home_platoon_score"))
    ap = _safe_float(lineups.get("away_platoon_score"))
    if hp is not None and ap is not None:
        p_diff = hp - ap
        if p_diff >= 0.10:
            home_bonus += (0.18 * w_ctx)
            reasons.append(f"platoon_home_edge={p_diff:.3f}")
        elif p_diff <= -0.10:
            away_bonus += (0.18 * w_ctx)
            reasons.append(f"platoon_away_edge={abs(p_diff):.3f}")

    home_off = (((metric.get("home") or {}).get("offense") or {}))
    away_off = (((metric.get("away") or {}).get("offense") or {}))
    hops = _safe_float(home_off.get("ops"))
    aops = _safe_float(away_off.get("ops"))
    if hops is not None and aops is not None:
        odiff = hops - aops
        if odiff >= 0.040:
            home_bonus += (0.25 * w_off)
            reasons.append(f"ops_home_edge={odiff:.3f}")
        elif odiff <= -0.040:
            away_bonus += (0.25 * w_off)
            reasons.append(f"ops_away_edge={abs(odiff):.3f}")

    home_off_adv = (((metric.get("home") or {}).get("offense_advanced") or {}))
    away_off_adv = (((metric.get("away") or {}).get("offense_advanced") or {}))
    h_iso = _safe_float(home_off_adv.get("iso"))
    a_iso = _safe_float(away_off_adv.get("iso"))
    if h_iso is not None and a_iso is not None:
        iso_diff = h_iso - a_iso
        if iso_diff >= 0.020:
            home_bonus += (0.18 * w_off)
            reasons.append(f"iso_home_edge={iso_diff:.3f}")
        elif iso_diff <= -0.020:
            away_bonus += (0.18 * w_off)
            reasons.append(f"iso_away_edge={abs(iso_diff):.3f}")

    h_bbpa = _safe_float(home_off_adv.get("bb_per_pa"))
    a_bbpa = _safe_float(away_off_adv.get("bb_per_pa"))
    h_kpa = _safe_float(home_off_adv.get("k_per_pa"))
    a_kpa = _safe_float(away_off_adv.get("k_per_pa"))
    if None not in (h_bbpa, a_bbpa, h_kpa, a_kpa):
        h_disc = h_bbpa - h_kpa
        a_disc = a_bbpa - a_kpa
        d_disc = h_disc - a_disc
        if d_disc >= 0.020:
            home_bonus += (0.16 * w_off)
            reasons.append(f"discipline_home_edge={d_disc:.3f}")
        elif d_disc <= -0.020:
            away_bonus += (0.16 * w_off)
            reasons.append(f"discipline_away_edge={abs(d_disc):.3f}")

    home_pitch_adv = ((((metric.get("home") or {}).get("probable_pitcher") or {}).get("advanced") or {}))
    away_pitch_adv = ((((metric.get("away") or {}).get("probable_pitcher") or {}).get("advanced") or {}))

    h_opsa = _safe_float(home_pitch_adv.get("ops_allowed"))
    a_opsa = _safe_float(away_pitch_adv.get("ops_allowed"))
    if h_opsa is not None and a_opsa is not None:
        # Lower OPS allowed is better for the pitcher's team.
        p_diff = a_opsa - h_opsa
        if p_diff >= 0.030:
            home_bonus += (0.20 * w_pitch)
            reasons.append(f"pitch_ops_allowed_home_edge={p_diff:.3f}")
        elif p_diff <= -0.030:
            away_bonus += (0.20 * w_pitch)
            reasons.append(f"pitch_ops_allowed_away_edge={abs(p_diff):.3f}")

    h_hr9 = _safe_float(home_pitch_adv.get("hr9"))
    a_hr9 = _safe_float(away_pitch_adv.get("hr9"))
    if h_hr9 is not None and a_hr9 is not None:
        hr_diff = a_hr9 - h_hr9
        if hr_diff >= 0.20:
            home_bonus += (0.12 * w_pitch)
            reasons.append(f"pitch_hr9_home_edge={hr_diff:.2f}")
        elif hr_diff <= -0.20:
            away_bonus += (0.12 * w_pitch)
            reasons.append(f"pitch_hr9_away_edge={abs(hr_diff):.2f}")

    bullpen = metric.get("bullpen") or {}
    home_f = _safe_float(bullpen.get("home_fatigue_score"))
    away_f = _safe_float(bullpen.get("away_fatigue_score"))
    if home_f is not None and away_f is not None:
        # Lower fatigue score = fresher bullpen.
        diff = away_f - home_f
        if diff >= 12:
            home_bonus += (0.22 * w_bp)
            reasons.append(f"bullpen_home_fresher={diff:.1f}")
        elif diff <= -12:
            away_bonus += (0.22 * w_bp)
            reasons.append(f"bullpen_away_fresher={abs(diff):.1f}")

    if home_bonus == 0 and away_bonus == 0:
        return adv_score, {"applied": False, "metric": metric, "reasons": []}

    scale = max(0.0, float(weight or 1.0))
    adv_score.home = adv_score.home + round(home_bonus * scale, 3)
    adv_score.away = adv_score.away + round(away_bonus * scale, 3)

    return adv_score, {
        "applied": True,
        "home_bonus": round(home_bonus * scale, 3),
        "away_bonus": round(away_bonus * scale, 3),
        "reasons": reasons,
        "metric": metric,
    }
