#!/usr/bin/env python3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ET = ZoneInfo("America/New_York")


def get_secret(name: str):
    val = os.environ.get(name)
    if val:
        return val

    repo_root = Path(__file__).resolve().parents[2]
    for env_name in (".env.local", ".env"):
        p = repo_root / env_name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            t = line.strip()
            if not t or t.startswith("#") or "=" not in t:
                continue
            k, v = t.split("=", 1)
            if k.strip() == name:
                return v.strip().strip('"').strip("'")
    return None

BALLPARK_COORDS = {
    "Angel Stadium": (33.8003, -117.8827),
    "Busch Stadium": (38.6226, -90.1928),
    "Chase Field": (33.4453, -112.0667),
    "Citi Field": (40.7571, -73.8458),
    "Citizens Bank Park": (39.9057, -75.1665),
    "Coors Field": (39.7559, -104.9942),
    "Comerica Park": (42.3390, -83.0485),
    "Daikin Park": (29.7572, -95.3555),
    "Dodger Stadium": (34.0739, -118.2400),
    "Fenway Park": (42.3467, -71.0972),
    "George M. Steinbrenner Field": (27.9801, -82.5078),
    "Globe Life Field": (32.7473, -97.0848),
    "Great American Ball Park": (39.0979, -84.5081),
    "Guaranteed Rate Field": (41.8300, -87.6338),
    "Kauffman Stadium": (39.0517, -94.4803),
    "loanDepot park": (25.7781, -80.2197),
    "Nationals Park": (38.8730, -77.0074),
    "Oracle Park": (37.7786, -122.3893),
    "Oriole Park at Camden Yards": (39.2838, -76.6217),
    "Petco Park": (32.7076, -117.1570),
    "PNC Park": (40.4469, -80.0057),
    "Progressive Field": (41.4962, -81.6852),
    "Rogers Centre": (43.6414, -79.3894),
    "Sutter Health Park": (38.5802, -121.5139),
    "Target Field": (44.9817, -93.2775),
    "T-Mobile Park": (47.5914, -122.3325),
    "Truist Park": (33.8907, -84.4677),
    "Wrigley Field": (41.9484, -87.6553),
    "Yankee Stadium": (40.8296, -73.9262),
}


def get_json(url: str, headers=None, timeout=25):
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=timeout) as res:
        body = res.read().decode("utf-8")
        return json.loads(body)


def est_today_str():
    return datetime.now(ET).date().isoformat()


def matchup_key(a: str, b: str):
    return "|".join(sorted([a or "", b or ""]))


def fetch_schedule(date_str: str):
    qs = urlencode({"sportId": 1, "date": date_str, "hydrate": "probablePitcher,team,linescore"})
    url = f"https://statsapi.mlb.com/api/v1/schedule?{qs}"
    return get_json(url)


def fetch_schedule_range(start_date: str, end_date: str):
    qs = urlencode({"sportId": 1, "startDate": start_date, "endDate": end_date})
    url = f"https://statsapi.mlb.com/api/v1/schedule?{qs}"
    return get_json(url)


def fetch_live_feed(game_pk: int):
    return get_json(f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live")


def fetch_boxscore(game_pk: int):
    return get_json(f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore")


def fetch_team_hitting(team_id: int, season: int):
    qs = urlencode({"stats": "season", "group": "hitting", "season": season})
    data = get_json(f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?{qs}")
    splits = (((data or {}).get("stats") or [{}])[0].get("splits") or [])
    return (splits[0].get("stat") if splits else {}) or {}


def fetch_team_hitting_advanced(team_id: int, season: int):
    qs = urlencode({"stats": "seasonAdvanced", "group": "hitting", "season": season})
    data = get_json(f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?{qs}")
    splits = (((data or {}).get("stats") or [{}])[0].get("splits") or [])
    return (splits[0].get("stat") if splits else {}) or {}


def fetch_pitcher_stats(player_id: int, season: int):
    qs = urlencode({"stats": "season", "group": "pitching", "season": season})
    data = get_json(f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?{qs}")
    splits = (((data or {}).get("stats") or [{}])[0].get("splits") or [])
    return (splits[0].get("stat") if splits else {}) or {}


def fetch_pitcher_advanced(player_id: int, season: int):
    qs = urlencode({"stats": "seasonAdvanced", "group": "pitching", "season": season})
    data = get_json(f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?{qs}")
    splits = (((data or {}).get("stats") or [{}])[0].get("splits") or [])
    return (splits[0].get("stat") if splits else {}) or {}


def safe_float(v):
    try:
        return float(v)
    except Exception:
        return None


def safe_int(v):
    try:
        return int(float(v))
    except Exception:
        return None


def avg(nums):
    vals = [float(x) for x in nums if x is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def fetch_odds_api_odds(date_str: str):
    key = get_secret("ODDS_API_KEY") or get_secret("THE_ODDS_API_KEY")
    if not key:
        return {}, {"source": "odds_api", "used": False, "reason": "missing_key"}

    qs = urlencode({
        "apiKey": key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
    })
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?{qs}"

    req = Request(url)
    with urlopen(req, timeout=25) as res:
        body = res.read().decode("utf-8")
        data = json.loads(body)
        remaining = res.headers.get("x-requests-remaining")
        used = res.headers.get("x-requests-used")

    out = {}
    for g in data or []:
        home = g.get("home_team")
        away = g.get("away_team")
        k = matchup_key(home, away)

        home_ml = []
        spread_home = []
        total_over = []

        for b in g.get("bookmakers") or []:
            for m in b.get("markets") or []:
                mk = m.get("key")
                outcomes = m.get("outcomes") or []
                if mk == "h2h":
                    o_home = next((o for o in outcomes if o.get("name") == home), None)
                    if o_home:
                        home_ml.append(safe_int(o_home.get("price")))
                elif mk == "spreads":
                    o_home = next((o for o in outcomes if o.get("name") == home), None)
                    if o_home:
                        spread_home.append(safe_float(o_home.get("point")))
                elif mk == "totals":
                    o_over = next((o for o in outcomes if str(o.get("name", "")).lower() == "over"), None)
                    if o_over:
                        total_over.append(safe_float(o_over.get("point")))

        cur_ml = avg(home_ml)
        cur_spread = avg(spread_home)
        cur_total = avg(total_over)

        out[k] = {
            "moneyline_open_home": safe_int(cur_ml),
            "moneyline_current_home": safe_int(cur_ml),
            "spread_open_home": round(cur_spread, 2) if cur_spread is not None else None,
            "spread_current_home": round(cur_spread, 2) if cur_spread is not None else None,
            "total_open": round(cur_total, 2) if cur_total is not None else None,
            "total_current": round(cur_total, 2) if cur_total is not None else None,
            "lastUpdated": g.get("commence_time"),
        }

    return out, {
        "source": "odds_api",
        "used": True,
        "requests_remaining": remaining,
        "requests_used": used,
        "date": date_str,
    }


def fetch_sportspage_odds(date_str: str):
    key = get_secret("SPORTSPAGE_API_KEY") or get_secret("SPORTSBOOK_API_KEY")
    if not key:
        return {}, {"source": "sportspage", "used": False, "reason": "missing_key"}

    url = f"https://sportspage-feeds.p.rapidapi.com/games?odds=moneyline&league=MLB&date={date_str}"
    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": "sportspage-feeds.p.rapidapi.com"}
    data = get_json(url, headers=headers)
    out = {}
    for r in (data or {}).get("results", []):
        away = (((r.get("teams") or {}).get("away") or {}).get("team"))
        home = (((r.get("teams") or {}).get("home") or {}).get("team"))
        k = matchup_key(home, away)
        odds = (r.get("odds") or [])
        o = odds[0] if odds else {}
        out[k] = {
            "moneyline_open_home": safe_int((((o.get("moneyline") or {}).get("open") or {}).get("homeOdds")),),
            "moneyline_current_home": safe_int((((o.get("moneyline") or {}).get("current") or {}).get("homeOdds")),),
            "spread_open_home": safe_float((((o.get("spread") or {}).get("open") or {}).get("home"))),
            "spread_current_home": safe_float((((o.get("spread") or {}).get("current") or {}).get("home"))),
            "total_open": safe_float((((o.get("total") or {}).get("open") or {}).get("total"))),
            "total_current": safe_float((((o.get("total") or {}).get("current") or {}).get("total"))),
            "lastUpdated": o.get("lastUpdated"),
        }
    return out, {"source": "sportspage", "used": True, "date": date_str}


def fetch_weather_for_game(game_dt_iso: str, venue_name: str):
    coords = BALLPARK_COORDS.get(venue_name)
    if not coords:
        return None
    lat, lon = coords

    dt = datetime.fromisoformat(game_dt_iso.replace("Z", "+00:00"))
    start_hour = dt.astimezone(ET).strftime("%Y-%m-%dT%H:00")
    qs = urlencode({
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation_probability",
        "timezone": "America/New_York",
        "start_hour": start_hour,
        "end_hour": start_hour,
    })
    data = get_json(f"https://api.open-meteo.com/v1/forecast?{qs}")
    h = (data or {}).get("hourly") or {}

    def first(name):
        vals = h.get(name) or []
        return vals[0] if vals else None

    return {
        "temperature_f": first("temperature_2m"),
        "humidity_pct": first("relative_humidity_2m"),
        "wind_mph": first("wind_speed_10m"),
        "wind_dir_deg": first("wind_direction_10m"),
        "precip_pct": first("precipitation_probability"),
    }


def _iso_to_est_date(iso_ts: str):
    dt = datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
    return dt.astimezone(ET).date().isoformat()


def compute_bullpen_freshness(as_of_date: str):
    as_of = datetime.fromisoformat(as_of_date).date()
    d1 = (as_of - timedelta(days=1)).isoformat()
    d2 = (as_of - timedelta(days=2)).isoformat()
    d3 = (as_of - timedelta(days=3)).isoformat()

    sched = fetch_schedule_range(d3, d1)
    box_cache = {}
    team_day_pitches = {}
    team_day_relievers = {}

    for block in (sched or {}).get("dates", []) or []:
        for g in block.get("games", []) or []:
            status = ((g.get("status") or {}).get("detailedState") or "").lower()
            if "final" not in status:
                continue

            game_pk = g.get("gamePk")
            if game_pk is None:
                continue

            if game_pk not in box_cache:
                try:
                    box_cache[game_pk] = fetch_boxscore(game_pk)
                except Exception:
                    box_cache[game_pk] = None

            box = box_cache.get(game_pk)
            if not box:
                continue

            try:
                g_day = _iso_to_est_date(g.get("gameDate"))
            except Exception:
                g_day = d1

            for side in ("home", "away"):
                team_blob = ((box.get("teams") or {}).get(side) or {})
                team = team_blob.get("team") or {}
                team_id = team.get("id")
                if team_id is None:
                    continue

                bullpen_ids = [pid for pid in (team_blob.get("bullpen") or []) if pid]
                players = team_blob.get("players") or {}
                pitches = 0
                relievers_used = 0
                for pid in bullpen_ids:
                    pdata = players.get(f"ID{pid}") or {}
                    pstats = ((pdata.get("stats") or {}).get("pitching") or {})
                    thrown = safe_int(pstats.get("pitchesThrown"))
                    if thrown is None:
                        thrown = safe_int(pstats.get("numberOfPitches"))
                    thrown = thrown or 0
                    # Some MLB endpoints omit per-pitcher pitch counts for historical boxscores.
                    # We still treat bullpen entries as appearances for freshness estimation.
                    if pdata:
                        relievers_used += 1
                    pitches += max(0, thrown)

                team_day_pitches.setdefault(team_id, {}).setdefault(g_day, 0)
                workload_units = pitches + (relievers_used * 12)
                team_day_pitches[team_id][g_day] += workload_units
                team_day_relievers.setdefault(team_id, {}).setdefault(g_day, 0)
                team_day_relievers[team_id][g_day] += relievers_used

    out = {}
    for team_id, by_day in team_day_pitches.items():
        p1 = by_day.get(d1, 0)
        p2 = by_day.get(d2, 0)
        p3 = by_day.get(d3, 0)
        weighted = (1.0 * p1) + (0.7 * p2) + (0.4 * p3)
        fatigue_score = min(100, max(0, int(round(weighted / 3.5))))
        out[team_id] = {
            "fatigue_score": fatigue_score,
            "pitches_last_3d": p1 + p2 + p3,
            "pitches_by_day": {d1: p1, d2: p2, d3: p3},
            "relievers_by_day": {
                d1: (team_day_relievers.get(team_id, {}) or {}).get(d1, 0),
                d2: (team_day_relievers.get(team_id, {}) or {}).get(d2, 0),
                d3: (team_day_relievers.get(team_id, {}) or {}).get(d3, 0),
            },
        }

    return out


def build(date_str: str):
    season = int(date_str[:4])
    sched = fetch_schedule(date_str)
    dates = (sched or {}).get("dates") or []
    games = dates[0].get("games") if dates else []

    odds_map = {}
    odds_meta = {}
    try:
        odds_map, odds_meta = fetch_odds_api_odds(date_str)
    except Exception as e:
        odds_meta = {"source": "odds_api", "used": False, "error": str(e)}

    if not odds_map:
        try:
            odds_map, odds_meta = fetch_sportspage_odds(date_str)
        except Exception as e:
            odds_map, odds_meta = {}, {"source": "sportspage", "used": False, "error": str(e)}

    team_cache = {}
    team_adv_cache = {}
    pitcher_cache = {}
    pitcher_adv_cache = {}
    bullpen_cache = {}
    try:
        bullpen_cache = compute_bullpen_freshness(date_str)
    except Exception:
        bullpen_cache = {}
    matchups = []

    for g in games or []:
        game_pk = g.get("gamePk")
        home = (((g.get("teams") or {}).get("home") or {}).get("team") or {})
        away = (((g.get("teams") or {}).get("away") or {}).get("team") or {})
        home_name = home.get("name")
        away_name = away.get("name")
        home_id = home.get("id")
        away_id = away.get("id")

        home_prob = (((g.get("teams") or {}).get("home") or {}).get("probablePitcher") or {})
        away_prob = (((g.get("teams") or {}).get("away") or {}).get("probablePitcher") or {})

        live = {}
        both_lineups_announced = False
        try:
            live = fetch_live_feed(game_pk)
            box = (((live.get("liveData") or {}).get("boxscore") or {}).get("teams") or {})
            home_batting = ((box.get("home") or {}).get("battingOrder") or [])
            away_batting = ((box.get("away") or {}).get("battingOrder") or [])
            both_lineups_announced = len(home_batting) >= 9 and len(away_batting) >= 9
        except Exception:
            pass

        if home_id not in team_cache:
            try:
                team_cache[home_id] = fetch_team_hitting(home_id, season)
            except Exception:
                team_cache[home_id] = {}
        if away_id not in team_cache:
            try:
                team_cache[away_id] = fetch_team_hitting(away_id, season)
            except Exception:
                team_cache[away_id] = {}

        if home_id not in team_adv_cache:
            try:
                team_adv_cache[home_id] = fetch_team_hitting_advanced(home_id, season)
            except Exception:
                team_adv_cache[home_id] = {}
        if away_id not in team_adv_cache:
            try:
                team_adv_cache[away_id] = fetch_team_hitting_advanced(away_id, season)
            except Exception:
                team_adv_cache[away_id] = {}

        home_pitcher_id = home_prob.get("id")
        away_pitcher_id = away_prob.get("id")

        if home_pitcher_id and home_pitcher_id not in pitcher_cache:
            try:
                pitcher_cache[home_pitcher_id] = fetch_pitcher_stats(home_pitcher_id, season)
            except Exception:
                pitcher_cache[home_pitcher_id] = {}
        if away_pitcher_id and away_pitcher_id not in pitcher_cache:
            try:
                pitcher_cache[away_pitcher_id] = fetch_pitcher_stats(away_pitcher_id, season)
            except Exception:
                pitcher_cache[away_pitcher_id] = {}

        if home_pitcher_id and home_pitcher_id not in pitcher_adv_cache:
            try:
                pitcher_adv_cache[home_pitcher_id] = fetch_pitcher_advanced(home_pitcher_id, season)
            except Exception:
                pitcher_adv_cache[home_pitcher_id] = {}
        if away_pitcher_id and away_pitcher_id not in pitcher_adv_cache:
            try:
                pitcher_adv_cache[away_pitcher_id] = fetch_pitcher_advanced(away_pitcher_id, season)
            except Exception:
                pitcher_adv_cache[away_pitcher_id] = {}

        odds = odds_map.get(matchup_key(home_name, away_name), {})

        weather = None
        try:
            game_dt = g.get("gameDate")
            venue_name = ((g.get("venue") or {}).get("name"))
            if game_dt and venue_name:
                weather = fetch_weather_for_game(game_dt, venue_name)
        except Exception:
            weather = None

        home_bp = bullpen_cache.get(home_id, {})
        away_bp = bullpen_cache.get(away_id, {})
        home_f = safe_int(home_bp.get("fatigue_score"))
        away_f = safe_int(away_bp.get("fatigue_score"))
        bp_edge = "neutral"
        if home_f is not None and away_f is not None:
            if home_f + 8 <= away_f:
                bp_edge = "home_fresher"
            elif away_f + 8 <= home_f:
                bp_edge = "away_fresher"

        def pitcher_view(s):
            return {
                "era": safe_float(s.get("era")),
                "whip": safe_float(s.get("whip")),
                "k_bb": safe_float(s.get("strikeoutWalkRatio")),
                "hr9": safe_float(s.get("homeRunsPer9")),
                "k9": safe_float(s.get("strikeoutsPer9Inn")),
            }

        def pitcher_advanced_view(s):
            return {
                "k9": safe_float(s.get("strikeoutsPer9")),
                "bb9": safe_float(s.get("baseOnBallsPer9")),
                "hr9": safe_float(s.get("homeRunsPer9")),
                "k_bb": safe_float(s.get("strikesoutsToWalks")),
                "obp_allowed": safe_float(s.get("obp")),
                "slg_allowed": safe_float(s.get("slg")),
                "ops_allowed": safe_float(s.get("ops")),
                "babip_allowed": safe_float(s.get("babip")),
            }

        def offense_view(s):
            return {
                "runs": safe_int(s.get("runs")),
                "ops": safe_float(s.get("ops")),
                "obp": safe_float(s.get("obp")),
                "slg": safe_float(s.get("slg")),
                "k": safe_int(s.get("strikeOuts")),
                "bb": safe_int(s.get("baseOnBalls")),
            }

        def offense_advanced_view(s):
            return {
                "iso": safe_float(s.get("iso")),
                "babip": safe_float(s.get("babip")),
                "bb_per_pa": safe_float(s.get("walksPerPlateAppearance")),
                "k_per_pa": safe_float(s.get("strikeoutsPerPlateAppearance")),
                "hr_per_pa": safe_float(s.get("homeRunsPerPlateAppearance")),
                "pitches_per_pa": safe_float(s.get("pitchesPerPlateAppearance")),
            }

        ml_open = odds.get("moneyline_open_home")
        ml_curr = odds.get("moneyline_current_home")
        implied_home = None
        if isinstance(ml_curr, int):
            if ml_curr < 0:
                implied_home = round(abs(ml_curr) / (abs(ml_curr) + 100), 4)
            elif ml_curr > 0:
                implied_home = round(100 / (ml_curr + 100), 4)

        matchup = {
            "game_pk": game_pk,
            "game_time": g.get("gameDate"),
            "status": (((g.get("status") or {}).get("detailedState")) or ""),
            "venue": (g.get("venue") or {}).get("name"),
            "home": {
                "id": home_id,
                "name": home_name,
                "offense": offense_view(team_cache.get(home_id, {})),
                "offense_advanced": offense_advanced_view(team_adv_cache.get(home_id, {})),
                "probable_pitcher": {
                    "id": home_pitcher_id,
                    "name": home_prob.get("fullName"),
                    "stats": pitcher_view(pitcher_cache.get(home_pitcher_id, {})),
                    "advanced": pitcher_advanced_view(pitcher_adv_cache.get(home_pitcher_id, {})),
                },
            },
            "away": {
                "id": away_id,
                "name": away_name,
                "offense": offense_view(team_cache.get(away_id, {})),
                "offense_advanced": offense_advanced_view(team_adv_cache.get(away_id, {})),
                "probable_pitcher": {
                    "id": away_pitcher_id,
                    "name": away_prob.get("fullName"),
                    "stats": pitcher_view(pitcher_cache.get(away_pitcher_id, {})),
                    "advanced": pitcher_advanced_view(pitcher_adv_cache.get(away_pitcher_id, {})),
                },
            },
            "lineups": {
                "both_announced": both_lineups_announced,
            },
            "market": {
                "source": odds_meta.get("source"),
                "moneyline_open_home": ml_open,
                "moneyline_current_home": ml_curr,
                "moneyline_move": (ml_curr - ml_open) if isinstance(ml_curr, int) and isinstance(ml_open, int) else None,
                "spread_open_home": odds.get("spread_open_home"),
                "spread_current_home": odds.get("spread_current_home"),
                "total_open": odds.get("total_open"),
                "total_current": odds.get("total_current"),
                "implied_home_prob": implied_home,
                "last_updated": odds.get("lastUpdated"),
            },
            "weather": weather,
            "bullpen": {
                "home_fatigue_score": home_f,
                "away_fatigue_score": away_f,
                "edge": bp_edge,
                "home_pitches_last_3d": safe_int(home_bp.get("pitches_last_3d")),
                "away_pitches_last_3d": safe_int(away_bp.get("pitches_last_3d")),
                "window": "last_3_days_pre_game",
            },
        }

        matchups.append(matchup)

    return {
        "generated_at": datetime.now(ET).isoformat(),
        "date": date_str,
        "odds_source": odds_meta,
        "count": len(matchups),
        "matchups": matchups,
    }


def main():
    date_str = os.environ.get("METRICS_DATE", "").strip() or est_today_str()
    repo_root = Path(__file__).resolve().parents[2]
    out_dir = repo_root / "data" / "matchup-metrics"
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = build(date_str)
    out_path = out_dir / f"{date_str}.json"
    out_path.write_text(json.dumps(payload, indent=2))

    print(f"Wrote matchup metrics: {out_path}")
    print(f"Games: {payload.get('count', 0)}")


if __name__ == "__main__":
    main()
