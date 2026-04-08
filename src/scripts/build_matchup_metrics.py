#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ET = ZoneInfo("America/New_York")

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


def fetch_live_feed(game_pk: int):
    return get_json(f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live")


def fetch_team_hitting(team_id: int, season: int):
    qs = urlencode({"stats": "season", "group": "hitting", "season": season})
    data = get_json(f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?{qs}")
    splits = (((data or {}).get("stats") or [{}])[0].get("splits") or [])
    return (splits[0].get("stat") if splits else {}) or {}


def fetch_pitcher_stats(player_id: int, season: int):
    qs = urlencode({"stats": "season", "group": "pitching", "season": season})
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


def fetch_sportspage_odds(date_str: str):
    key = os.environ.get("SPORTSPAGE_API_KEY") or os.environ.get("SPORTSBOOK_API_KEY")
    if not key:
        return {}

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
    return out


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


def build(date_str: str):
    season = int(date_str[:4])
    sched = fetch_schedule(date_str)
    dates = (sched or {}).get("dates") or []
    games = dates[0].get("games") if dates else []

    odds_map = fetch_sportspage_odds(date_str)

    team_cache = {}
    pitcher_cache = {}
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

        odds = odds_map.get(matchup_key(home_name, away_name), {})

        weather = None
        try:
            game_dt = g.get("gameDate")
            venue_name = ((g.get("venue") or {}).get("name"))
            if game_dt and venue_name:
                weather = fetch_weather_for_game(game_dt, venue_name)
        except Exception:
            weather = None

        def pitcher_view(s):
            return {
                "era": safe_float(s.get("era")),
                "whip": safe_float(s.get("whip")),
                "k_bb": safe_float(s.get("strikeoutWalkRatio")),
                "hr9": safe_float(s.get("homeRunsPer9")),
                "k9": safe_float(s.get("strikeoutsPer9Inn")),
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
                "probable_pitcher": {
                    "id": home_pitcher_id,
                    "name": home_prob.get("fullName"),
                    "stats": pitcher_view(pitcher_cache.get(home_pitcher_id, {})),
                },
            },
            "away": {
                "id": away_id,
                "name": away_name,
                "offense": offense_view(team_cache.get(away_id, {})),
                "probable_pitcher": {
                    "id": away_pitcher_id,
                    "name": away_prob.get("fullName"),
                    "stats": pitcher_view(pitcher_cache.get(away_pitcher_id, {})),
                },
            },
            "lineups": {
                "both_announced": both_lineups_announced,
            },
            "market": {
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
                "fatigue_score": None,
                "note": "placeholder: derive from rolling reliever usage"
            },
        }

        matchups.append(matchup)

    return {
        "generated_at": datetime.now(ET).isoformat(),
        "date": date_str,
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
