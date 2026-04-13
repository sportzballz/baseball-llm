import json
import os
import random
import re
from datetime import datetime, timedelta

import pytz
import requests
import statsapi

from common.util import get_teams_list
from connector.matchup_metrics import get_metric_for_game, load_cached_metrics
from connector.mlbstartinglineups import get_starting_lineups

RECENT_LINEUP_GAMES = 5

ANALYST_STYLE_LADDER = [
    ("market maker", "Mack Ledger", "Market Maker"),
    ("matchup film room", "Nora Splitter", "Matchup Film Room"),
    ("quant", "Dex Numbers", "Quant"),
    ("momentum & vibes", "Rico Heatcheck", "Momentum & Vibes"),
    ("beat writer", "Grant Halberd", "Beat Writer"),
    ("data scientist", "Ivy Chen", "Data Scientist"),
    ("contrarian", "Toby Quinn", "Contrarian"),
    ("weather/umpire specialist", "Lena Park", "Weather/Umpire Specialist"),
    ("showman", "Vince Valentino", "Showman"),
    ("process coach", "Maya Rios", "Process Coach"),
    ("model whisperer", "Owen Pike", "Model Whisperer"),
    ("underdog hunter", "Jules Archer", "Underdog Hunter"),
    ("line movement hawk", "Roman Slate", "Line Movement Hawk"),
    ("injury/lineup impact", "Keira Bloom", "Injury/Lineup Impact"),
    ("totals architect", "Eli Mercer", "Totals Architect"),
    ("clv auditor", "Sanjay Vale", "CLV Auditor"),
]

ANALYST_BY_STYLE = {s: (n, t) for s, n, t in ANALYST_STYLE_LADDER}

DOME_VENUES = {
    "Rogers Centre",
    "Tropicana Field",
    "loanDepot park",
    "Minute Maid Park",
    "American Family Field",
    "Chase Field",
    "T-Mobile Park",
    "Globe Life Field",
}

# Conservative umpire run-context tendencies (can expand over time).
# +1 => slightly more run-friendly, -1 => slightly more run-suppressing.
UMPIRE_RUN_TENDENCY = {
    # hitter-friendly-ish examples
    "Laz Diaz": 1,
    "CB Bucknor": 1,
    # pitcher-friendly-ish examples
    "Pat Hoberg": -1,
    "Tripp Gibson": -1,
}


def _safe_get(dct, path, default=None):
    cur = dct
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def _normalize_abbr(abbr):
    # predictions can include markers like $, ., *
    return abbr.replace("$", "").replace(".", "").replace("*", "").strip().lower()


def _get_team_maps():
    teams = get_teams_list()
    abbr_to_name = {}
    name_to_id = {}
    for t in teams:
        abbr_to_name[t.abbreviation.strip().lower()] = t.name
        name_to_id[t.name] = t.id
    return abbr_to_name, name_to_id


def _build_schedule_lookup(game_date):
    games = statsapi.schedule(start_date=game_date, end_date=game_date)
    return games


def _find_game_for_pick(schedule, winner_name, loser_name):
    for g in schedule:
        home = g.get("home_name")
        away = g.get("away_name")
        if {winner_name, loser_name} == {home, away}:
            return g
    return None


def _extract_umpires(game_data):
    officials = _safe_get(game_data, ["liveData", "boxscore", "officials"], []) or []
    crew = []
    for o in officials:
        name = _safe_get(o, ["official", "fullName"], "Unknown")
        role = o.get("officialType", "Official")
        crew.append(f"{role}: {name}")
    return crew


def _extract_weather(game_data):
    weather = _safe_get(game_data, ["gameData", "weather"], {}) or {}
    venue = _safe_get(game_data, ["gameData", "venue", "name"], "Unknown Venue")
    dome = venue in DOME_VENUES

    if dome:
        return {
            "venue": venue,
            "dome": True,
            "summary": "Dome/retractable roof environment — external wind conditions not applicable.",
            "temp": None,
            "wind": None,
            "condition": None,
        }

    condition = weather.get("condition")
    temp = weather.get("temp")
    wind = weather.get("wind")

    if condition or temp or wind:
        summary_parts = []
        if condition:
            summary_parts.append(str(condition))
        if temp:
            summary_parts.append(f"{temp}°F")
        if wind:
            summary_parts.append(str(wind))
        summary = ", ".join(summary_parts)
    else:
        summary = "Weather data unavailable from MLB feed at run time."

    return {
        "venue": venue,
        "dome": False,
        "summary": summary,
        "temp": temp,
        "wind": wind,
        "condition": condition,
    }


def _get_injuries(team_id):
    try:
        url = (
            f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=injured"
        )
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return []
        data = resp.json()
        roster = data.get("roster", [])
        injuries = []
        for r in roster:
            name = _safe_get(r, ["person", "fullName"], "Unknown")
            status = _safe_get(r, ["status", "description"], "Injured list")
            injuries.append(f"{name} ({status})")
        return injuries[:8]
    except Exception:
        return []


def _extract_line_movement(odds_entry, winner_name):
    if not odds_entry:
        return {
            "current": None,
            "open": None,
            "movement": None,
            "text": "Line movement unavailable.",
        }

    teams = odds_entry.get("teams", {})
    side = "home" if _safe_get(teams, ["home", "team"]) == winner_name else "away"

    odds_obj = None
    if odds_entry.get("odds") and len(odds_entry["odds"]) > 0:
        odds_obj = odds_entry["odds"][0]

    current = _safe_get(odds_obj or {}, ["moneyline", "current", f"{side}Odds"])

    # Try multiple possible open keys from provider payloads
    open_odds = (
        _safe_get(odds_obj or {}, ["moneyline", "opening", f"{side}Odds"])
        or _safe_get(odds_obj or {}, ["moneyline", "open", f"{side}Odds"])
        or _safe_get(odds_obj or {}, ["moneyline", "opening", side])
        or _safe_get(odds_obj or {}, ["moneyline", "open", side])
    )

    movement = None
    if isinstance(current, (int, float)) and isinstance(open_odds, (int, float)):
        movement = current - open_odds

    if current is None:
        text = "Current moneyline unavailable."
    elif open_odds is None:
        text = f"Current moneyline: {current}. Opening line not available from feed."
    elif movement == 0:
        text = f"Moneyline unchanged at {current}."
    else:
        direction = "toward" if movement < 0 else "away from"
        text = f"Moneyline moved from {open_odds} to {current} ({movement:+}), {direction} the pick side."

    return {"current": current, "open": open_odds, "movement": movement, "text": text}


def _extract_total_market(odds_entry):
    if not odds_entry:
        return {
            "total_current": None,
            "over_odds": None,
            "under_odds": None,
            "total_open": None,
            "text": "Total line unavailable.",
            "movement_text": "Total movement unavailable.",
        }

    odds_obj = None
    if odds_entry.get("odds") and len(odds_entry["odds"]) > 0:
        odds_obj = odds_entry["odds"][0]

    total_current = _safe_get(odds_obj or {}, ["total", "current", "total"])
    over_odds = _safe_get(odds_obj or {}, ["total", "current", "overOdds"])
    under_odds = _safe_get(odds_obj or {}, ["total", "current", "underOdds"])
    total_open = _safe_get(odds_obj or {}, ["total", "open", "total"])

    if total_current is None:
        text = "Total line unavailable."
    else:
        over_txt = _format_odds(over_odds) if over_odds is not None else '—'
        under_txt = _format_odds(under_odds) if under_odds is not None else '—'
        text = f"{total_current} (Over {over_txt} / Under {under_txt})"

    if total_current is None or total_open is None:
        movement_text = "Total movement unavailable."
    else:
        diff = float(total_current) - float(total_open)
        if diff == 0:
            movement_text = f"Total unchanged at {total_current}."
        elif diff > 0:
            movement_text = (
                f"Total moved up from {total_open} to {total_current} (+{diff:g})."
            )
        else:
            movement_text = (
                f"Total moved down from {total_open} to {total_current} ({diff:g})."
            )

    return {
        "total_current": total_current,
        "over_odds": over_odds,
        "under_odds": under_odds,
        "total_open": total_open,
        "text": text,
        "movement_text": movement_text,
    }


def _format_odds(odds):
    try:
        o = int(odds)
        if o > 0:
            return f"+{o}"
        if o < 0:
            return str(o)
    except Exception:
        pass
    return "----"


def _signal_sentiment(signal_text: str, positive: bool = True) -> str:
    s = str(signal_text or "").lower()
    if not s or s == "no model signal list available.":
        return "model signal context was limited"

    offense = any(k in s for k in ["runs", "homer", "rbi", "avg", "hits", "doubles", "triples", "walk"])
    pitching = any(k in s for k in ["whip", "era", "strikeout", "walksper9", "hitsper9", "homerunsper9", "strikepercentage"])
    matchup = ("opposing pitcher" in s) or ("opposing team" in s)
    form = "most wins" in s

    parts = []
    if offense:
        parts.append("run creation quality")
    if pitching:
        parts.append("run prevention stability")
    if matchup:
        parts.append("matchup history leverage")
    if form:
        parts.append("recent form")

    if not parts:
        core = "overall matchup profile"
    elif len(parts) == 1:
        core = parts[0]
    elif len(parts) == 2:
        core = f"{parts[0]} and {parts[1]}"
    else:
        core = ", ".join(parts[:-1]) + f", and {parts[-1]}"

    return core if positive else f"volatility around {core}"


def _lineup_announced(team_token):
    token = str(team_token or "").strip()
    # Historical marker convention from prediction payload:
    # leading "." means lineup not yet posted for that team.
    # A leading "$" can also be present for in-game winner marker.
    token = token.lstrip("$")
    return not token.startswith(".")


def _lineup_status_text(winner_name, loser_name, winner_announced, loser_announced):
    if winner_announced and loser_announced:
        return "Both starting lineups were announced at publish time."
    if (not winner_announced) and (not loser_announced):
        return "Starting lineups were not announced for either team at publish time."
    if winner_announced and (not loser_announced):
        return f"{winner_name} lineup announced; {loser_name} lineup not announced at publish time."
    return f"{winner_name} lineup not announced; {loser_name} lineup announced at publish time."


def _today_lineups_by_team():
    out = {}
    try:
        for lu in get_starting_lineups() or []:
            ids = []
            for p in getattr(lu, "lineup_players", []) or []:
                try:
                    ids.append(int(p.get("personId")))
                except Exception:
                    continue
            if ids:
                out[int(lu.team_id)] = ids[:9]
    except Exception:
        return {}
    return out


def _recent_team_games(team_id, as_of_date, max_games=RECENT_LINEUP_GAMES):
    # Pull enough history window to capture previous few completed games.
    end_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() - timedelta(days=1)
    start_date = end_date - timedelta(days=25)
    try:
        games = statsapi.schedule(
            start_date=str(start_date),
            end_date=str(end_date),
            team=team_id,
        )
    except Exception:
        games = []

    games = sorted(games, key=lambda g: g.get("game_datetime") or "", reverse=True)
    return games[:max_games]


def _team_lineup_and_result_for_game(game_pk, team_id):
    try:
        game = statsapi.get("game", {"gamePk": game_pk})
    except Exception:
        return [], None

    home_id = _safe_get(game, ["gameData", "teams", "home", "id"])
    away_id = _safe_get(game, ["gameData", "teams", "away", "id"])
    side = "home" if home_id == team_id else ("away" if away_id == team_id else None)
    if not side:
        return [], None

    order = (
        _safe_get(game, ["liveData", "boxscore", "teams", side, "battingOrder"], [])
        or []
    )
    lineup_ids = []
    for pid in order[:9]:
        try:
            lineup_ids.append(int(pid))
        except Exception:
            continue

    team_runs = _safe_get(game, ["liveData", "linescore", "teams", side, "runs"])
    opp_side = "away" if side == "home" else "home"
    opp_runs = _safe_get(game, ["liveData", "linescore", "teams", opp_side, "runs"])
    won = None
    if isinstance(team_runs, int) and isinstance(opp_runs, int):
        won = team_runs > opp_runs

    return lineup_ids, won


def _lineup_change_impact(team_id, team_name, today_lineup_ids, as_of_date):
    if not today_lineup_ids:
        return ""

    recent = _recent_team_games(team_id, as_of_date, RECENT_LINEUP_GAMES)
    if not recent:
        return ""

    today_set = set(today_lineup_ids)
    overlaps = []
    turnover_wins = turnover_total = 0
    stable_wins = stable_total = 0

    for g in recent:
        game_pk = g.get("game_id")
        if not game_pk:
            continue
        prev_ids, won = _team_lineup_and_result_for_game(game_pk, team_id)
        if not prev_ids:
            continue
        shared = len(today_set.intersection(set(prev_ids)))
        overlaps.append(shared)

        if won is None:
            continue
        if shared <= 6:
            turnover_total += 1
            if won:
                turnover_wins += 1
        elif shared >= 8:
            stable_total += 1
            if won:
                stable_wins += 1

    if not overlaps:
        return ""

    avg_shared = round(sum(overlaps) / len(overlaps), 1)
    base = f"Compared with last {len(overlaps)} games, today's announced lineup shares {avg_shared}/9 starters on average."

    impact_bits = []
    if turnover_total >= 2:
        impact_bits.append(
            f"In higher-turnover comps (≤6 shared), {team_name} went {turnover_wins}-{turnover_total - turnover_wins}"
        )
    if stable_total >= 2:
        impact_bits.append(
            f"in stable-lineup comps (≥8 shared), {team_name} went {stable_wins}-{stable_total - stable_wins}"
        )

    if impact_bits:
        return base + " " + "; ".join(impact_bits) + "."
    return base


def _fallback_commentary(context):
    venue = context["venue"]
    weather = context["weather_summary"]
    movement = context["line_movement_text"]
    ump = context["umpire_summary"]
    lineup_status = context.get(
        "lineup_status_text", "Starting lineup status unavailable at publish time."
    )
    lineup_impact = context.get("lineup_change_impact", "")
    lineup_impact_sentence = f" {lineup_impact}" if lineup_impact else ""
    metrics_summary = context.get("metrics_summary_text", "")
    if metrics_summary:
        lineup_impact_sentence += f" Metrics context: {metrics_summary}"
    style = context.get("style", "market maker")
    analyst_name = context.get("analyst_name")
    analyst_title = context.get("analyst_title")
    if not analyst_name or not analyst_title:
        analyst_name, analyst_title = ANALYST_BY_STYLE.get(
            style, ("Mack Ledger", "Market Maker")
        )
    winner_signals_raw = context.get("winner_signals", "No model signal list available.")
    loser_signals_raw = context.get("loser_signals", "No model signal list available.")
    winner_signals = _signal_sentiment(winner_signals_raw, positive=True)
    loser_signals = _signal_sentiment(loser_signals_raw, positive=False)

    # Unified richer fallback paragraph to reduce repetitive templated wording.
    openers = [
        "Here’s the card:",
        "Game-day notebook:",
        "First-pitch read:",
        "This matchup sets up this way:",
    ]
    tone_by_style = {
        "market maker": "Price and matchup are aligned, so the read stays actionable.",
        "matchup film room": "The game script points to the side with the cleaner path over nine innings.",
        "quant": "The edge comes from stacked moderate signals rather than one noisy outlier.",
        "momentum & vibes": "The profile carries fewer soft spots once leverage innings arrive.",
        "beat writer": "One club enters with steadier two-way structure while the other needs extra variance.",
        "data scientist": "Directional probability and practical matchup context are rowing together.",
        "contrarian": "Market framing still leaves room for this side to win without a perfect script.",
        "weather/umpire specialist": "External context reinforces the base handicap instead of fighting it.",
        "showman": "This number and narrative line up in a way that is playable, not just loud.",
        "process coach": "This is a disciplined edge profile, not a chase setup.",
        "model whisperer": "Projection direction and on-field shape both support this side.",
        "underdog hunter": "Value case is built on stability and path quality, not noise.",
        "line movement hawk": "Price behavior confirms the read rather than contradicting it.",
        "injury/lineup impact": "Availability and continuity are meaningful in this matchup.",
        "totals architect": "Run-environment framing supports the side and narrows upset paths.",
        "clv auditor": "Process quality and entry discipline are still favorable at this number.",
    }

    paragraph = (
        f"{analyst_name} ({analyst_title}) — {random.choice(openers)} "
        f"{context['winner']} over {context['loser']} at {context['odds']}. "
        f"Model confidence is {context['confidence']} on {context['data_points']}. "
        f"{tone_by_style.get(style, 'The setup remains coherent across context and price.')} "
        f"The preferred side grades better on {winner_signals}, while the opposing profile still shows {loser_signals}. "
        f"Market movement reads: {movement}. Lineup status: {lineup_status}{lineup_impact_sentence} "
        f"Weather and crew context: {weather} / {ump}."
    )
    return re.sub(r"\s+", " ", paragraph).strip()

    if style == "market maker":
        return (
            f"{analyst_name} ({analyst_title}) — Market-first card: {context['winner']} over {context['loser']} at {context['odds']}. "
            f"Confidence ({context['confidence']}, data points {context['data_points']}) supports entry discipline, not chasing. "
            f"Primary support for {context['winner']}: {winner_signals}. "
            f"Resistance case for {context['loser']}: {loser_signals}. "
            f"Weather ({weather}), umpire context ({ump}), and move profile ({movement}) frame the risk. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "matchup film room":
        return (
            f"{analyst_name} ({analyst_title}) — Film-room lens: {context['winning_pitcher']} vs {context['losing_pitcher']} tilts toward {context['winner']} over {context['loser']}. "
            f"Model read is {context['confidence']} with {context['data_points']} data points. "
            f"Winning-side indicators: {winner_signals}. "
            f"Counter-indicators: {loser_signals}. "
            f"Add game environment ({weather}), crew texture ({ump}), and line action ({movement}) for final fit. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "quant":
        return (
            f"{analyst_name} ({analyst_title}) — Probability view: {context['winner']} over {context['loser']} at {context['odds']} with confidence {context['confidence']} ({context['data_points']}). "
            f"Edge set for {context['winner']}: {winner_signals}. "
            f"Negative offsets from {context['loser']}: {loser_signals}. "
            f"Exogenous factors: weather ({weather}), umpire ({ump}), market state ({movement}). "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "momentum & vibes":
        return (
            f"{analyst_name} ({analyst_title}) — Heatcheck angle: {context['winner']} over {context['loser']} has real juice at {context['odds']}. "
            f"The model confidence ({context['confidence']}, {context['data_points']}) says this isn’t random noise. "
            f"{context['winner']} momentum stack: {winner_signals}. "
            f"{context['loser']} pushback profile: {loser_signals}. "
            f"Conditions ({weather}), crew ({ump}), and number behavior ({movement}) all matter before first pitch. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "beat writer":
        return (
            f"{analyst_name} ({analyst_title}) — {venue} hosts {context['winner']} over {context['loser']} at {context['odds']}, with model confidence {context['confidence']} ({context['data_points']}). "
            f"The case for {context['winner']} is anchored by {winner_signals}. "
            f"The caution flags for {context['loser']} come from {loser_signals}. "
            f"Weather ({weather}), umpire assignment ({ump}), and line movement ({movement}) shape the read. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "data scientist":
        return (
            f"{analyst_name} ({analyst_title}) — Validation pass: {context['winner']} over {context['loser']} at {context['odds']} with confidence {context['confidence']} and {context['data_points']}. "
            f"Positive feature cluster: {winner_signals}. "
            f"Adverse feature cluster: {loser_signals}. "
            f"Context controls include weather ({weather}), umpire effects ({ump}), and market drift ({movement}). "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "contrarian":
        return (
            f"{analyst_name} ({analyst_title}) — Contrarian read: {context['winner']} over {context['loser']} at {context['odds']} looks playable if the market has overreacted. "
            f"Model confidence is {context['confidence']} ({context['data_points']}). "
            f"Why it still works: {winner_signals}. "
            f"Why it can fail: {loser_signals}. "
            f"Weather ({weather}), umpire setup ({ump}), and move direction ({movement}) decide whether price is truly mis-set. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "weather/umpire specialist":
        return (
            f"{analyst_name} ({analyst_title}) — Context-heavy read: {context['winner']} over {context['loser']} at {context['odds']}. "
            f"Confidence is {context['confidence']} with {context['data_points']} data points. "
            f"Skill edge for {context['winner']}: {winner_signals}. "
            f"Skill resistance for {context['loser']}: {loser_signals}. "
            f"Weather ({weather}) and umpire profile ({ump}) are core variables, with line behavior ({movement}) as confirmation. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "showman":
        return (
            f"{analyst_name} ({analyst_title}) — Spotlight pick: {context['winner']} over {context['loser']} at {context['odds']}—and yes, the numbers back the headline. "
            f"Model confidence checks in at {context['confidence']} ({context['data_points']}). "
            f"Headline support: {winner_signals}. "
            f"Trap-door risks: {loser_signals}. "
            f"Stage conditions are weather ({weather}), crew ({ump}), and market script ({movement}). "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "process coach":
        return (
            f"{analyst_name} ({analyst_title}) — Process-first: {context['winner']} over {context['loser']} at {context['odds']} with confidence {context['confidence']} ({context['data_points']}). "
            f"Keep sizing tied to edge quality, not emotion. "
            f"Support stack: {winner_signals}. "
            f"Failure points: {loser_signals}. "
            f"Environment ({weather}), umpire variable ({ump}), and line behavior ({movement}) complete the checklist. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "model whisperer":
        return (
            f"{analyst_name} ({analyst_title}) — Model translation: {context['winner']} over {context['loser']} at {context['odds']}, confidence {context['confidence']} with {context['data_points']}. "
            f"Top contributing signals for {context['winner']}: {winner_signals}. "
            f"Competing signal set for {context['loser']}: {loser_signals}. "
            f"External modifiers are weather ({weather}), umpire context ({ump}), and market movement ({movement}). "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "underdog hunter":
        return (
            f"{analyst_name} ({analyst_title}) — Dog-hunt lens: {context['winner']} over {context['loser']} at {context['odds']}. "
            f"Confidence/data point profile is {context['confidence']} ({context['data_points']}), so this is selective aggression, not blind plus-money chasing. "
            f"Underdog support: {winner_signals}. "
            f"Favorite-side risk controls: {loser_signals}. "
            f"Game conditions ({weather}), umpire setup ({ump}), and line behavior ({movement}) decide whether value survives to first pitch. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "line movement hawk":
        return (
            f"{analyst_name} ({analyst_title}) — Tape on the number: {context['winner']} over {context['loser']} at {context['odds']}. "
            f"Model confidence is {context['confidence']} ({context['data_points']}), but price behavior is the filter. "
            f"Fundamental support: {winner_signals}. "
            f"Resistance signals: {loser_signals}. "
            f"With weather ({weather}) and umpire context ({ump}), movement profile ({movement}) tells you if the edge is still there. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "injury/lineup impact":
        return (
            f"{analyst_name} ({analyst_title}) — Availability framing: {context['winner']} over {context['loser']} at {context['odds']}, confidence {context['confidence']} ({context['data_points']}). "
            f"Edge case for {context['winner']}: {winner_signals}. "
            f"Stress points from {context['loser']}: {loser_signals}. "
            f"Before bet placement, reconcile injury/load context with weather ({weather}), umpire assignment ({ump}), and market movement ({movement}). "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "totals architect":
        return (
            f"{analyst_name} ({analyst_title}) — Run-environment read supporting {context['winner']} over {context['loser']} at {context['odds']}. "
            f"Confidence sits at {context['confidence']} with {context['data_points']} data points. "
            f"Scoring pressure indicators: {winner_signals}. "
            f"Run-prevention resistance: {loser_signals}. "
            f"Weather ({weather}) and plate profile ({ump}) are primary context; line behavior ({movement}) confirms timing. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "clv auditor":
        return (
            f"{analyst_name} ({analyst_title}) — CLV discipline pass: {context['winner']} over {context['loser']} at {context['odds']}. "
            f"The model projects confidence {context['confidence']} with {context['data_points']}, but execution quality depends on price timing. "
            f"Core support: {winner_signals}. "
            f"Failure conditions: {loser_signals}. "
            f"Use weather ({weather}), umpire context ({ump}), and current move path ({movement}) to avoid paying peak tax. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )

    return (
        f"{analyst_name} ({analyst_title}) — Price-first view: {context['winner']} over {context['loser']} at {context['odds']} with model confidence {context['confidence']} ({context['data_points']}). "
        f"The strongest support for {context['winner']} comes from: {winner_signals}. "
        f"The best resistance case for {context['loser']} comes from: {loser_signals}. "
        f"Venue/weather ({venue}, {weather}), umpire notes ({ump}), and market movement ({movement}) keep this in the value bucket. "
        f"Lineup status: {lineup_status}{lineup_impact_sentence}"
    )


def _generate_commentary(context):
    # If OpenAI key exists, use get_pick_summary as requested to generate
    # commentary for this pick context; otherwise fall back deterministically.
    # if os.environ.get("OPENAI_API_KEY"):
    #     try:
    #         from connector.llm import get_pick_summary

    #         fallback = _fallback_commentary(context)
    #         model_name = context.get("model_name", "dutch")
    #         llm_text = get_pick_summary(context, fallback, model_name)
    #         if llm_text and str(llm_text).strip():
    #             return str(llm_text).strip()
    #     except Exception as e:
    #         print(f"LLM commentary generation failed, using fallback: {e}")

    return _fallback_commentary(context)


def _metrics_summary_for_commentary(metric, winner_name, loser_name):
    if not metric:
        return ""

    home = ((metric.get("home") or {}).get("name") or "")
    winner_is_home = str(winner_name).strip().lower() == str(home).strip().lower()

    bits = []

    market = metric.get("market") or {}
    implied_home = market.get("implied_home_prob")
    if isinstance(implied_home, (int, float)):
        implied_winner = implied_home if winner_is_home else (1 - implied_home)
        if implied_winner >= 0.56:
            bits.append("pricing context leans clearly toward this side")
        elif implied_winner >= 0.52:
            bits.append("pricing context gives a modest edge")
        else:
            bits.append("pricing context is closer to balanced")

    # Always surface bullpen fatigue context when available.
    bullpen = metric.get("bullpen") or {}
    hf = bullpen.get("home_fatigue_score")
    af = bullpen.get("away_fatigue_score")
    if isinstance(hf, (int, float)) and isinstance(af, (int, float)):
        diff = (af - hf) if winner_is_home else (hf - af)
        if diff >= 8:
            bits.append(f"bullpen fatigue context favors this side (freshness edge ~{int(diff)} points)")
        elif diff <= -8:
            bits.append(f"bullpen fatigue context leans against this side (~{int(abs(diff))} points)")
        else:
            bits.append("bullpen fatigue context is mostly even")

    # Always surface platoon split context when available.
    lineups = metric.get("lineups") or {}
    hp = lineups.get("home_platoon_score")
    ap = lineups.get("away_platoon_score")
    if isinstance(hp, (int, float)) and isinstance(ap, (int, float)):
        score = hp if winner_is_home else ap
        opp = ap if winner_is_home else hp
        delta = score - opp
        if delta >= 0.08:
            bits.append(f"platoon split setup supports this side (lineup fit +{delta:.2f})")
        elif delta <= -0.08:
            bits.append(f"platoon split setup is less favorable (lineup fit {delta:.2f})")
        else:
            bits.append("platoon split setup is close to neutral")

    consensus = market.get("consensus") or {}
    rng = consensus.get("moneyline_range")
    books = consensus.get("books")
    if isinstance(books, (int, float)) and books >= 4 and isinstance(rng, (int, float)):
        if rng <= 12:
            bits.append("books are tightly aligned")
        elif rng >= 30:
            bits.append("books show wider disagreement")

    park = metric.get("park_factors") or {}
    run_factor = park.get("run_factor")
    if isinstance(run_factor, (int, float)):
        if run_factor >= 1.08:
            bits.append("park environment can amplify scoring swings")
        elif run_factor <= 0.94:
            bits.append("park environment tends to suppress run volume")

    if not bits:
        return "Expanded matchup metrics were neutral."

    return "; ".join(bits[:4]).capitalize() + "."


def _bullpen_total_context(metric):
    bullpen = (metric or {}).get("bullpen") or {}
    hf = bullpen.get("home_fatigue_score")
    af = bullpen.get("away_fatigue_score")
    if not isinstance(hf, (int, float)) or not isinstance(af, (int, float)):
        return "Bullpen load unavailable"

    avg_fatigue = (float(hf) + float(af)) / 2.0
    diff = abs(float(hf) - float(af))
    if avg_fatigue >= 55:
        return "Both bullpens taxed (RUNS+)"
    if avg_fatigue <= 40:
        return "Both bullpens fresh (RUNS-)"
    if diff >= 12:
        return "Asymmetric bullpen fatigue (RUNS+ light)"
    return "Bullpen load mostly neutral"


def _platoon_total_context(metric):
    lineups = (metric or {}).get("lineups") or {}
    hp = lineups.get("home_platoon_score")
    ap = lineups.get("away_platoon_score")
    if not isinstance(hp, (int, float)) or not isinstance(ap, (int, float)):
        return "Platoon split signal unavailable"

    hp = float(hp)
    ap = float(ap)
    if hp >= 0.55 and ap >= 0.55:
        return "Both lineups show handedness edge (RUNS+)"
    if hp <= 0.45 and ap <= 0.45:
        return "Both lineups muted vs handedness (RUNS-)"
    return "Platoon split profile mixed"


def _umpire_total_context(umpire_summary):
    text = str(umpire_summary or "").strip()
    if not text or "unavailable" in text.lower():
        return "Umpire total tendency unavailable"

    hp_name = None
    for chunk in text.split(";"):
        c = chunk.strip()
        if c.lower().startswith("home plate:"):
            hp_name = c.split(":", 1)[1].strip()
            break

    if not hp_name:
        return "Home plate umpire not identified"

    lean = UMPIRE_RUN_TENDENCY.get(hp_name)
    if lean == 1:
        return f"Home plate umpire {hp_name} leans hitter-friendly (RUNS+)"
    if lean == -1:
        return f"Home plate umpire {hp_name} leans pitcher-friendly (RUNS-)"
    return f"Home plate umpire {hp_name} has no strong run lean on file"


def _starter_tto_total_context(metric):
    """Third-time-through-order risk proxy from starter quality indicators.
    Uses available advanced stats as a practical proxy when explicit TTO splits
    are not present in cached metrics.
    """
    if not metric:
        return "Starter TTO risk unavailable"

    def _risk(p):
        adv = (((p or {}).get("advanced")) or {})
        k9 = _safe_get(adv, ["k9"])
        bb9 = _safe_get(adv, ["bb9"])
        hr9 = _safe_get(adv, ["hr9"])
        opsa = _safe_get(adv, ["ops_allowed"])
        score = 0
        if isinstance(k9, (int, float)) and k9 <= 7.4:
            score += 1
        if isinstance(bb9, (int, float)) and bb9 >= 3.0:
            score += 1
        if isinstance(hr9, (int, float)) and hr9 >= 1.2:
            score += 1
        if isinstance(opsa, (int, float)) and opsa >= 0.730:
            score += 1
        return score

    hp = ((metric.get("home") or {}).get("probable_pitcher") or {})
    ap = ((metric.get("away") or {}).get("probable_pitcher") or {})
    hs = _risk(hp)
    as_ = _risk(ap)

    if hs + as_ >= 5:
        return "Both starters project elevated third-time-through-order leakage (RUNS+)"
    if hs + as_ <= 1:
        return "Starters project to hold shape through deeper turns (RUNS-)"
    if hs >= 3 or as_ >= 3:
        return "At least one starter carries notable TTO fade risk (RUNS+ light)"
    return "Starter TTO profile mixed"


def _pitch_mix_matchup_total_context(metric):
    """Pitch-mix matchup proxy using handedness/platoon + starter command.
    """
    if not metric:
        return "Pitch-mix matchup context unavailable"

    lineups = metric.get("lineups") or {}
    hp = lineups.get("home_platoon_score")
    ap = lineups.get("away_platoon_score")
    h_adv = (((metric.get("home") or {}).get("probable_pitcher") or {}).get("advanced") or {})
    a_adv = (((metric.get("away") or {}).get("probable_pitcher") or {}).get("advanced") or {})
    h_kbb = h_adv.get("k_bb")
    a_kbb = a_adv.get("k_bb")

    if all(isinstance(x, (int, float)) for x in (hp, ap, h_kbb, a_kbb)):
        hp = float(hp)
        ap = float(ap)
        h_kbb = float(h_kbb)
        a_kbb = float(a_kbb)

        if hp >= 0.55 and ap >= 0.55 and (h_kbb <= 2.6 or a_kbb <= 2.6):
            return "Lineups match pitcher handedness/pitch-shape well (RUNS+)"
        if hp <= 0.45 and ap <= 0.45 and h_kbb >= 3.4 and a_kbb >= 3.4:
            return "Pitch-shape/command profile suppresses hard contact windows (RUNS-)"
        if hp >= 0.55 or ap >= 0.55:
            return "One lineup has a favorable pitch-shape/platoon fit (RUNS+ light)"
        return "Pitch-mix matchup profile mixed"

    return "Pitch-mix matchup context unavailable"


def write_daily_pick_markdown(predictions, odds_data, model_name):
    valid = [p for p in predictions if p.winning_team != "-"]
    if not valid:
        return None

    eastern = pytz.timezone("US/Eastern")
    today = str(datetime.now(eastern).date())
    metrics_index = load_cached_metrics(today)

    abbr_to_name, name_to_id = _get_team_maps()
    schedule = _build_schedule_lookup(today)
    todays_lineups = _today_lineups_by_team()

    odds_lookup = {}
    for o in odds_data.get("results", []):
        home = _safe_get(o, ["teams", "home", "team"])
        away = _safe_get(o, ["teams", "away", "team"])
        if home and away:
            odds_lookup[frozenset([home, away])] = o

    lines = []
    lines.append(f"# MLB Picks Commentary — {today}")
    lines.append("")
    lines.append(f"- Model: `{model_name}`")
    lines.append(
        f"- Generated: {datetime.now(eastern).strftime('%Y-%m-%d %I:%M %p %Z')}"
    )
    try:
        from connector.llm import get_pick_summaries

        ai_summary = get_pick_summaries(valid, model_name)
        lines.append(f"- AI Summary Model Path: generated during markdown build")
        lines.append("")
        lines.append("## AI Pick Summary")
        lines.append("")
        lines.append(ai_summary)
        lines.append("")
        print("LLM summary generated in write_daily_pick_markdown")
    except Exception as e:
        print(f"LLM summary in markdown generation failed: {e}")
    lines.append("")

    for idx, p in enumerate(valid, start=1):
        winner_lineup_announced = _lineup_announced(p.winning_team)
        loser_lineup_announced = _lineup_announced(p.losing_team)

        winner_abbr = _normalize_abbr(p.winning_team)
        loser_abbr = _normalize_abbr(p.losing_team)

        winner_name = abbr_to_name.get(winner_abbr, winner_abbr.upper())
        loser_name = abbr_to_name.get(loser_abbr, loser_abbr.upper())

        game = _find_game_for_pick(schedule, winner_name, loser_name)
        game_data = statsapi.get("game", {"gamePk": game["game_id"]}) if game else {}
        metric = get_metric_for_game(metrics_index, game_data) if game_data else None

        weather = (
            _extract_weather(game_data)
            if game_data
            else {
                "venue": "Unknown Venue",
                "summary": "Weather unavailable.",
                "dome": False,
            }
        )

        umpires = _extract_umpires(game_data) if game_data else []
        ump_summary = (
            "; ".join(umpires) if umpires else "Umpire crew unavailable at run time."
        )

        winner_id = name_to_id.get(winner_name)
        loser_id = name_to_id.get(loser_name)
        winner_injuries = _get_injuries(winner_id) if winner_id else []
        loser_injuries = _get_injuries(loser_id) if loser_id else []

        winner_lineup_impact = (
            _lineup_change_impact(
                winner_id,
                winner_name,
                todays_lineups.get(winner_id, []),
                today,
            )
            if winner_id
            else ""
        )
        loser_lineup_impact = (
            _lineup_change_impact(
                loser_id,
                loser_name,
                todays_lineups.get(loser_id, []),
                today,
            )
            if loser_id
            else ""
        )

        impact_parts = []
        if winner_lineup_impact:
            impact_parts.append(f"{winner_name}: {winner_lineup_impact}")
        if loser_lineup_impact:
            impact_parts.append(f"{loser_name}: {loser_lineup_impact}")
        lineup_change_impact = " ".join(impact_parts)

        odds_entry = odds_lookup.get(frozenset([winner_name, loser_name]))
        line_move = _extract_line_movement(odds_entry, winner_name)
        total_market = _extract_total_market(odds_entry)

        style_array = [
            {"style": s, "analyst_name": n, "analyst_title": t}
            for s, n, t in ANALYST_STYLE_LADDER
        ]
        style_entry = style_array[(idx - 1) % len(style_array)]

        context = {
            "pick_index": idx,
            "style": style_entry["style"],
            "analyst_name": style_entry["analyst_name"],
            "analyst_title": style_entry["analyst_title"],
            "winner": winner_name,
            "loser": loser_name,
            "odds": _format_odds(p.odds),
            "confidence": p.confidence,
            "data_points": p.data_points,
            "winner_signals": ", ".join(p.winning_stats[:15])
            if p.winning_stats
            else "No model signal list available.",
            "loser_signals": ", ".join(p.losing_stats[:15])
            if p.losing_stats
            else "No model signal list available.",
            "venue": weather.get("venue", "Unknown Venue"),
            "weather_summary": weather.get("summary", "Weather unavailable."),
            "umpire_summary": ump_summary,
            "winner_injuries": ", ".join(winner_injuries)
            if winner_injuries
            else "No injured-list data available.",
            "loser_injuries": ", ".join(loser_injuries)
            if loser_injuries
            else "No injured-list data available.",
            "line_movement_text": line_move["text"],
            "total_line_text": total_market["text"],
            "total_movement_text": total_market["movement_text"],
            "winner_lineup_announced": winner_lineup_announced,
            "loser_lineup_announced": loser_lineup_announced,
            "lineup_status_text": _lineup_status_text(
                winner_name, loser_name, winner_lineup_announced, loser_lineup_announced
            ),
            "winner_lineup_trend": winner_lineup_impact,
            "loser_lineup_trend": loser_lineup_impact,
            "lineup_change_impact": lineup_change_impact,
            "metrics_summary_text": _metrics_summary_for_commentary(
                metric, winner_name, loser_name
            ),
            "bullpen_total_context": _bullpen_total_context(metric),
            "platoon_total_context": _platoon_total_context(metric),
            "umpire_total_context": _umpire_total_context(ump_summary),
            "starter_tto_total_context": _starter_tto_total_context(metric),
            "pitch_mix_total_context": _pitch_mix_matchup_total_context(metric),
            "winning_pitcher": p.winning_pitcher,
            "losing_pitcher": p.losing_pitcher,
            "model_name": model_name,
        }

        commentary = _generate_commentary(context)

        lines.append(f"## {idx}) {winner_name} over {loser_name}")
        lines.append("")
        lines.append(f"- **Pick Odds:** {context['odds']}")
        lines.append(
            f"- **Model Confidence:** {context['confidence']} (data points: {context['data_points']})"
        )
        lines.append(
            f"- **Pitching Matchup:** {context['winning_pitcher']} vs {context['losing_pitcher']}"
        )
        lines.append(f"- **{winner_name} Model Signals:** {context['winner_signals']}")
        lines.append(f"- **{loser_name} Model Signals:** {context['loser_signals']}")
        lines.append(f"- **Venue:** {context['venue']}")
        lines.append(f"- **Weather:** {context['weather_summary']}")
        lines.append(f"- **Umpire Crew:** {context['umpire_summary']}")
        lines.append(f"- **{winner_name} Injuries:** {context['winner_injuries']}")
        lines.append(f"- **{loser_name} Injuries:** {context['loser_injuries']}")
        lines.append(f"- **Starting Lineups:** {context['lineup_status_text']}")
        lines.append(
            f"- **{winner_name} Lineup Trend:** {context['winner_lineup_trend'] or 'n/a'}"
        )
        lines.append(
            f"- **{loser_name} Lineup Trend:** {context['loser_lineup_trend'] or 'n/a'}"
        )
        lines.append(
            f"- **Lineup Change Impact:** {context['lineup_change_impact'] or 'n/a'}"
        )
        lines.append(f"- **Line Movement:** {context['line_movement_text']}")
        lines.append(f"- **Total Line:** {context['total_line_text']}")
        lines.append(f"- **Total Movement:** {context['total_movement_text']}")
        lines.append(f"- **Bullpen Total Context:** {context['bullpen_total_context']}")
        lines.append(f"- **Platoon Total Context:** {context['platoon_total_context']}")
        lines.append(f"- **Umpire Total Context:** {context['umpire_total_context']}")
        lines.append(f"- **Starter TTO Context:** {context['starter_tto_total_context']}")
        lines.append(f"- **Pitch Mix Matchup Context:** {context['pitch_mix_total_context']}")
        lines.append("")
        lines.append("**Commentary**")
        lines.append("")
        lines.append(commentary)
        lines.append("")

    output_dir = "./picks"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{today}-pick.md")

    with open(output_path, "w") as f:
        f.write("\n".join(lines).strip() + "\n")

    return output_path
