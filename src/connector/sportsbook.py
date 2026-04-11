import os
import http
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pytz


def _secret(name: str):
    v = os.environ.get(name)
    if v:
        return v
    repo_root = Path(__file__).resolve().parents[2]
    for env_name in (".env.local", ".env"):
        p = repo_root / env_name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            t = line.strip()
            if not t or t.startswith("#") or "=" not in t:
                continue
            k, val = t.split("=", 1)
            if k.strip() == name:
                return val.strip().strip('"').strip("'")
    return None


def _safe_int(v):
    try:
        return int(float(v))
    except Exception:
        return None


def _safe_float(v):
    try:
        return float(v)
    except Exception:
        return None


def _avg(nums):
    vals = [float(x) for x in nums if x is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _american_to_prob(odds):
    try:
        o = int(odds)
    except Exception:
        return None
    if o == 0:
        return None
    if o > 0:
        return 100.0 / (o + 100.0)
    return abs(o) / (abs(o) + 100.0)


def _prob_to_american(prob):
    try:
        p = float(prob)
    except Exception:
        return None
    if not (0 < p < 1):
        return None
    if p >= 0.5:
        return -int(round((p / (1.0 - p)) * 100.0))
    return int(round(((1.0 - p) / p) * 100.0))


def _consensus_american(prices):
    probs = [_american_to_prob(x) for x in prices if x is not None]
    probs = [p for p in probs if p is not None]
    if not probs:
        return None
    return _prob_to_american(sum(probs) / len(probs))


def _odds_api_mlb(today):
    key = _secret("ODDS_API_KEY") or _secret("THE_ODDS_API_KEY")
    if not key:
        return None

    qs = urlencode(
        {
            "apiKey": key,
            "regions": "us",
            "markets": "h2h,totals",
            "oddsFormat": "american",
            "dateFormat": "iso",
        }
    )
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?{qs}"
    with urlopen(url, timeout=25) as res:
        data = json.loads(res.read().decode("utf-8"))

    results = []
    for g in data or []:
        home = g.get("home_team")
        away = g.get("away_team")
        home_ml = []
        away_ml = []
        totals = []
        over_prices = []
        under_prices = []

        for b in g.get("bookmakers") or []:
            for m in b.get("markets") or []:
                mk = m.get("key")
                outcomes = m.get("outcomes") or []
                if mk == "h2h":
                    oh = next((o for o in outcomes if o.get("name") == home), None)
                    oa = next((o for o in outcomes if o.get("name") == away), None)
                    if oh:
                        home_ml.append(_safe_int(oh.get("price")))
                    if oa:
                        away_ml.append(_safe_int(oa.get("price")))
                elif mk == "totals":
                    oo = next((o for o in outcomes if str(o.get("name", "")).lower() == "over"), None)
                    ou = next((o for o in outcomes if str(o.get("name", "")).lower() == "under"), None)
                    if oo:
                        totals.append(_safe_float(oo.get("point")))
                        over_prices.append(_safe_int(oo.get("price")))
                    if ou:
                        under_prices.append(_safe_int(ou.get("price")))

        home_cur = _consensus_american(home_ml)
        away_cur = _consensus_american(away_ml)
        total_cur = _avg(totals)
        over_cur = _consensus_american(over_prices)
        under_cur = _consensus_american(under_prices)

        results.append(
            {
                "teams": {"home": {"team": home}, "away": {"team": away}},
                "odds": [
                    {
                        "moneyline": {
                            "open": {"homeOdds": home_cur, "awayOdds": away_cur},
                            "current": {"homeOdds": home_cur, "awayOdds": away_cur},
                        },
                        "total": {
                            "open": {"total": round(total_cur, 2) if total_cur is not None else None},
                            "current": {
                                "total": round(total_cur, 2) if total_cur is not None else None,
                                "overOdds": over_cur,
                                "underOdds": under_cur,
                            },
                        },
                    }
                ],
            }
        )

    return {"results": results}


def _sportspage_mlb(today):
    key = _secret("SPORTSPAGE_API_KEY") or _secret("SPORTSBOOK_API_KEY")
    if not key:
        return None

    headers = {
        'X-RapidAPI-Key': key,
        'X-RapidAPI-Host': "sportspage-feeds.p.rapidapi.com"
    }


def get_odds():
    today = str(datetime.now(pytz.timezone('US/Eastern')).date())

    # Prefer The Odds API first to reduce dependency on SPORTSPAGE_API_KEY.
    try:
        odds_api = _odds_api_mlb(today)
        if odds_api and odds_api.get("results"):
            return odds_api
    except Exception:
        pass

    sportspage = _sportspage_mlb(today)
    if not sportspage:
        return {"results": []}

    # Robust fetch strategy:
    # 1) no status filter (provider can return 0 for scheduled later in the day)
    # 2) fallback merge from explicit statuses if needed
    def _fetch(path):
        conn = http.client.HTTPSConnection("sportspage-feeds.p.rapidapi.com")
        conn.request("GET", path, headers=sportspage)
        res = conn.getresponse()
        data = res.read().decode("utf-8").replace("'", '"')
        return json.loads(data)

    try:
        data_list = _fetch(f"/games?odds=moneyline&league=MLB&date={today}")
    except Exception:
        data_list = {"results": []}

    results = data_list.get("results", []) if isinstance(data_list, dict) else []
    if results:
        return data_list

    merged = []
    seen = set()
    for status in ["scheduled", "inprogress", "final"]:
        try:
            part = _fetch(f"/games?odds=moneyline&status={status}&league=MLB&date={today}")
            for r in part.get("results", []):
                home = (((r.get("teams") or {}).get("home") or {}).get("team"))
                away = (((r.get("teams") or {}).get("away") or {}).get("team"))
                if not home or not away:
                    continue
                key_matchup = tuple(sorted([home, away]))
                if key_matchup in seen:
                    continue
                seen.add(key_matchup)
                merged.append(r)
        except Exception:
            continue

    return {"results": merged}
