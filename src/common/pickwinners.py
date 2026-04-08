

import os
import json
from pathlib import Path
from  common.util import *
from  connector.sportsbook import get_odds
from  connector.stats import *
from  connector.mlbstartinglineups import *
from connector.matchup_metrics import load_cached_metrics, apply_cached_metrics_to_advantage
from connector.pick_markdown import write_daily_pick_markdown
from connector.pick_site_publish import publish_daily_site
from  common.objects import AdvantageScore


def _lineup_announced(team_token):
    token = str(team_token or "").strip().lstrip("$")
    return not token.startswith(".")


def _norm_team_token(token):
    t = str(token or "").strip().lstrip("$.")
    if t.endswith("*"):
        t = t[:-1]
    return t


def _pick_key(prediction):
    a = _norm_team_token(getattr(prediction, "winning_team", ""))
    b = _norm_team_token(getattr(prediction, "losing_team", ""))
    pair = sorted([a, b])
    return "|".join(pair)


def _pick_to_dict(p):
    return {
        "winning_team": getattr(p, "winning_team", ""),
        "losing_team": getattr(p, "losing_team", ""),
        "winning_pitcher": getattr(p, "winning_pitcher", ""),
        "losing_pitcher": getattr(p, "losing_pitcher", ""),
        "gameDate": getattr(p, "gameDate", ""),
        "gameTime": getattr(p, "gameTime", ""),
        "ampm": getattr(p, "ampm", ""),
        "odds": getattr(p, "odds", 0),
        "confidence": getattr(p, "confidence", "0"),
        "data_points": getattr(p, "data_points", "0/0"),
        "winning_stats": getattr(p, "winning_stats", []) or [],
        "losing_stats": getattr(p, "losing_stats", []) or [],
    }


def _apply_pick_dict(p, d):
    p.winning_team = d.get("winning_team", p.winning_team)
    p.losing_team = d.get("losing_team", p.losing_team)
    p.winning_pitcher = d.get("winning_pitcher", p.winning_pitcher)
    p.losing_pitcher = d.get("losing_pitcher", p.losing_pitcher)
    p.gameDate = d.get("gameDate", p.gameDate)
    p.gameTime = d.get("gameTime", p.gameTime)
    p.ampm = d.get("ampm", p.ampm)
    p.odds = d.get("odds", p.odds)
    p.confidence = d.get("confidence", p.confidence)
    p.data_points = d.get("data_points", p.data_points)
    p.winning_stats = d.get("winning_stats", p.winning_stats)
    p.losing_stats = d.get("losing_stats", p.losing_stats)


def _state_path_for_day(day_str):
    return Path(__file__).resolve().parents[2] / "logs" / f"local-publish-state-{day_str}.json"


def _load_day_state(day_str):
    path = _state_path_for_day(day_str)
    if not path.exists():
        return {"picks": {}}, path
    try:
        return json.loads(path.read_text()), path
    except Exception:
        return {"picks": {}}, path


def _save_day_state(day_str, winners):
    state, path = _load_day_state(day_str)
    state["updatedAt"] = datetime.now(pytz.timezone('US/Eastern')).isoformat()
    state["picks"] = {_pick_key(w): _pick_to_dict(w) for w in winners if getattr(w, "winning_team", "-") != "-"}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def _pick_changed(cur, prev_dict):
    if not prev_dict:
        return True
    fields = [
        "winning_team", "losing_team", "winning_pitcher", "losing_pitcher",
        "odds", "confidence", "data_points",
    ]
    cur_d = _pick_to_dict(cur)
    return any(str(cur_d.get(f, "")) != str(prev_dict.get(f, "")) for f in fields)


def main(model, model_hitting_fn, model_pitching_fn, model_vs_fn):
    teams = get_teams_list()
    lineups = get_starting_lineups()

    odds_data = get_odds()
    # odds_data = {'results': []}

    use_cached_metrics = os.environ.get("USE_CACHED_MATCHUP_METRICS", "true").strip().lower() in ("1", "true", "yes", "on")
    try:
        metrics_weight = float(os.environ.get("CACHED_METRICS_WEIGHT", "1.0"))
    except Exception:
        metrics_weight = 1.0
    metrics_index = load_cached_metrics() if use_cached_metrics else {"by_game_pk": {}, "by_matchup": {}, "meta": {"found": False}}
    if use_cached_metrics:
        meta = metrics_index.get("meta", {})
        print(f"Cached metrics enabled: found={meta.get('found')} count={meta.get('count', 0)} source={meta.get('odds_source', {}).get('source')}")

    winners = []
    day = datetime.now(pytz.timezone('US/Eastern')).date()
    for team in teams:
        if team.name == 'Athletics':
            pass
        todays_games = get_todays_games(team.id, day)
        print(f'{team.name} will play {len(todays_games)} games today')
        # if len(todays_games) > 0:
        for todays_game in todays_games:
            game_id = todays_game['game_id']
            game_data = statsapi.get("game", {"gamePk": game_id})

            if todays_game['home_name'] == team.name:
                home_stats = []
                away_stats = []
                adv_score = AdvantageScore(home=1, away=0, home_stats=home_stats, away_stats=away_stats, home_lineup_available=False, away_lineup_available=False)
                adv_score = model_hitting_fn(adv_score, game_data, model, lineups)
                adv_score = model_pitching_fn(adv_score, game_data, model, lineups)
                adv_score = model_vs_fn(adv_score, game_data, model, lineups)
                if use_cached_metrics:
                    adv_score, metrics_applied = apply_cached_metrics_to_advantage(
                        adv_score, game_data, metrics_index, weight=metrics_weight
                    )
                    if metrics_applied and metrics_applied.get("applied"):
                        print(
                            "Cached metrics adjustment "
                            f"home+={metrics_applied.get('home_bonus')} away+={metrics_applied.get('away_bonus')} "
                            f"reasons={';'.join(metrics_applied.get('reasons', []))}"
                        )
                winners.append(select_winner(adv_score, game_data, odds_data))
                print(adv_score.to_string())

    # write_csv(winners)
    # print_csv(winners)
    # print_str(winners)

    runtime_mode = os.environ.get("BASEBALL_RUNTIME_MODE", "").strip().lower()
    in_aws_lambda = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME")) or os.environ.get(
        "AWS_EXECUTION_ENV", ""
    ).startswith("AWS_Lambda")

    if runtime_mode == "lambda":
        effective_mode = "lambda"
    elif runtime_mode == "local":
        effective_mode = "local"
    elif runtime_mode == "both":
        effective_mode = "both"
    else:
        # Auto mode: lambda environments do Slack-only; everything else does local LLM/html-only.
        effective_mode = "lambda" if in_aws_lambda else "local"

    print(f"Baseball runtime mode: {effective_mode}")

    if effective_mode in ("lambda", "both"):
        try:
            post_to_slack(winners, model)
        except Exception as e:
            print(f"Slack post failed (continuing): {e}")
    else:
        print("Skipping Slack posting in local mode")

    if effective_mode in ("local", "both"):
        local_winners = winners
        day_str = datetime.now(pytz.timezone('US/Eastern')).date().isoformat()
        state, _ = _load_day_state(day_str)
        prior = state.get("picks") or {}
        is_first_local_publish = len(prior) == 0

        if is_first_local_publish:
            print("Local first run of day: publishing full slate")
        else:
            changed_with_both_lineups = 0
            for w in local_winners:
                if getattr(w, "winning_team", "-") == "-":
                    continue
                key = _pick_key(w)
                prev = prior.get(key)
                changed = _pick_changed(w, prev)
                both_announced = _lineup_announced(getattr(w, "winning_team", "")) and _lineup_announced(getattr(w, "losing_team", ""))

                if changed and both_announced:
                    changed_with_both_lineups += 1
                elif changed and prev is not None and not both_announced:
                    # Freeze to last published values until both lineups are announced.
                    _apply_pick_dict(w, prev)

            if changed_with_both_lineups == 0:
                print("Subsequent local run: no lineup-confirmed pick changes; skipping publish")
                return
            print(f"Subsequent local run: publishing {changed_with_both_lineups} lineup-confirmed pick changes")

        # Write rich daily markdown commentary (weather, umpires, injuries, line movement)
        try:
            output_path = write_daily_pick_markdown(local_winners, odds_data, model)
            if output_path:
                print(f"Wrote pick commentary: {output_path}")

                # Auto-publish to sportzballz.io as yyyy-mm-dd.html + refresh top-level index
                try:
                    site_repo = os.environ.get('SPORTZBALLZ_SITE_REPO')
                    published_path = publish_daily_site(output_path, site_repo)
                    if published_path:
                        print(f"Published picks page: {published_path}")
                        _save_day_state(day_str, local_winners)
                except Exception as pe:
                    print(f"Failed to publish picks site: {pe}")
        except Exception as e:
            print(f"Failed to write markdown commentary: {e}")
    else:
        print("Skipping markdown/html generation in lambda mode")
