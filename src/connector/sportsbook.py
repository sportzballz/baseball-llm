import os
import http
import json
from datetime import datetime

import pytz


def get_odds():
    key = os.environ["SPORTSPAGE_API_KEY"]
    headers = {
        'X-RapidAPI-Key': key,
        'X-RapidAPI-Host': "sportspage-feeds.p.rapidapi.com"
    }
    today = str(datetime.now(pytz.timezone('US/Eastern')).date())

    # Robust fetch strategy:
    # 1) no status filter (provider can return 0 for scheduled later in the day)
    # 2) fallback merge from explicit statuses if needed
    def _fetch(path):
        conn = http.client.HTTPSConnection("sportspage-feeds.p.rapidapi.com")
        conn.request("GET", path, headers=headers)
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
