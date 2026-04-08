import os

import statsapi
# from pybaseball import *
# import pandas as pd

import requests
import json

from datetime import datetime, date, timedelta


def create_folder_if_not_exists(folder_path):
    """Creates a folder if it doesn't exist."""
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
    except Exception as e:
        pass


def write_stat_json(dir, file, json_str):
    try:
        create_folder_if_not_exists(dir)
        text_file = open(f'{dir}/{file}', "w")
        text_file.write(json_str)
        text_file.close()
    except Exception as e:
        pass


def read_stat_json(file):
    text_file = open(file, "r")
    json_str = text_file.read()
    text_file.close()
    return json_str


def get_pitcher_stats(player_id):
    return statsapi.player_stat_data(personId=player_id, group='pitching', type='season')


def get_pitcher_stats_by_date(player_id, d):
    year = d[:4]
    last_year = str(int(year) - 1)
    s = f"{last_year}-01-01"
    stmp = datetime.strptime(s, "%Y-%m-%d")
    etmp = datetime.strptime(d, "%Y-%m-%d")
    start = stmp.strftime("%m/%d/%Y")
    end = etmp.strftime("%m/%d/%Y")
    dir = f"resources/pitching/{str(d)}"
    fname = f"/{player_id}.json"
    if os.path.isfile(dir + fname):
        return json.loads(read_stat_json(dir + fname))
    else:
        url = f'https://statsapi.mlb.com/api/v1/people/{player_id}?hydrate=stats(group=[pitching],type=[byDateRange],startDate={start},endDate={end},season={year})'
        resp = requests.get(url)
        rjson = json.loads(resp.text)
        data = rjson['people'][0]
        write_stat_json(dir, fname, json.dumps(data))
        return data


def get_relief_stats_by_team(team_id, season):
    return statsapi.get("team_stats",
                 {"teamId": team_id, "season": season, "group": "pitching", "stats": "statSplits", "sitCodes": "rp"})

def get_hitter_stats_by_date(player_id, d):
    year = d[:4]
    last_year = str(int(year) - 1)
    s = f"{last_year}-01-01"
    stmp = datetime.strptime(s, "%Y-%m-%d")
    etmp = datetime.strptime(d, "%Y-%m-%d")
    start = stmp.strftime("%m/%d/%Y")
    end = etmp.strftime("%m/%d/%Y")
    dir = f"resources/hitting/{str(d)}"
    fname = f"/{player_id}.json"
    if os.path.isfile(dir + fname):
        return json.loads(read_stat_json(dir + fname))
    else:
        url = f'https://statsapi.mlb.com/api/v1/people/{player_id}?hydrate=stats(group=[hitting],type=[byDateRange],startDate={start},endDate={end},season={year})'
        resp = requests.get(url)
        rjson = json.loads(resp.text)
        data = rjson['people'][0]
        write_stat_json(dir, fname, json.dumps(data))
        return data


def get_todays_games(team_id, day):
    return statsapi.schedule(date=day, team=team_id)


def get_schedule_by_date(d):
    dir = f"resources/schedule"
    # etmp = datetime.strptime(d, "%Y-%m-%d").date()
    # formatted_date = etmp.strftime("%Y-%m-%d")
    fname = f"/{str(d)}.json"
    if os.path.isfile(dir + fname):
        return json.loads(read_stat_json(dir + fname))
    else:
        data = statsapi.schedule(start_date=d, end_date=d)
        write_stat_json(dir, fname, json.dumps(data))
        return data


def get_schedule_by_year(team_id, year):
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    retval = statsapi.schedule(start_date=start, end_date=end, team=team_id)
    return retval


def get_team_data(team_id):
    return statsapi.get("team", {"teamId": team_id})


def get_home_batters_by_gameid(game_id):
    game = get_boxscore(game_id)
    return game['homeBatters']


def get_away_batters_by_gameid(game_id):
    game = get_boxscore(game_id)
    return game['awayBatters']


def get_home_batting_total_by_game_id(game_id):
    game = get_boxscore(game_id)
    return game['homeBattingTotals']


def get_away_batting_total_by_game_id(game_id):
    game = get_boxscore(game_id)
    return game['awayBattingTotals']


def get_last_game_batters(team_id):
    last_game_id = statsapi.last_game(team_id)
    if last_game_id is None:
        return []
    last_boxscore = statsapi.boxscore_data(last_game_id)
    lbs = json.dumps(last_boxscore)
    if last_boxscore['teamInfo']['home']['id'] == team_id:
        return last_boxscore['homeBatters']
    else:
        return last_boxscore['awayBatters']


def get_lineup_batting_totals(lineup):
    dt = date.today().strftime("%Y-%m-%d")
    for player in lineup:
        stats = statsapi.player_stat_data(player.player_id, group="[hitting]", type="season", sportId=1)
        print(stats)


def get_last_game_by_date(team_id, d):
    while(1):
        delta = timedelta(days=1)
        d -= delta
        games = get_schedule_by_date(d)
        for game in games:
            if game['home_id'] == team_id or game['away_id'] == team_id:
                game_id = game['game_id']
                return game_id
                break


def get_last_game_batting_totals(team_id):
    last_game_id = statsapi.last_game(team_id)
    if last_game_id is None:
        return {}
    last_boxscore = statsapi.boxscore_data(last_game_id)
    if last_boxscore['teamInfo']['home']['id'] == team_id:
        return last_boxscore['homeBattingTotals']
    else:
        return last_boxscore['awayBattingTotals']


def get_game(game_id):
    dir = f"resources/game"
    fname = f"/{game_id}.json"
    if os.path.isfile(dir + fname):
        return json.loads(read_stat_json(dir + fname))
    else:
        data = statsapi.get("game", {"gamePk": game_id})
        write_stat_json(dir, fname, json.dumps(data))
        return data


def get_boxscore(game_id):
    dir = f"resources/boxscore"
    fname = f"/{game_id}.json"
    if os.path.isfile(dir + fname):
        return json.loads(read_stat_json(dir + fname))
    else:
        data = statsapi.boxscore_data(game_id)
        write_stat_json(dir, fname, json.dumps(data))
        return data



def get_vs_games(home, away):
    year = date.today().year
    start_date = f'03/31/{year}'
    end_date = date.today().strftime("%m/%d/%Y")
    games = statsapi.schedule(start_date=start_date, end_date=end_date, team=home, opponent=away)
    return games


def get_team_game_ids_before_date(team, d):
    game_id_list = []
    year = d[:4]
    last_year = str(int(year) - 1)
    start_date = f'03/31/{last_year}'
    end_date = str(d)
    dir = f"resources/schedule/by_team/{d}"
    fname = f"/{team}.json"
    if os.path.isfile(dir + fname):
        games = json.loads(read_stat_json(dir + fname))
    else:
        games = statsapi.schedule(start_date=start_date, end_date=end_date, team=team)
        write_stat_json(dir, fname, json.dumps(games))
    for game in games:
        game_id_list.append(game['game_id'])
    return game_id_list


def get_vs_game_ids_before_date(home, away, d):
    game_id_list = []
    year = d[:4]
    last_year = str(int(year) - 1)
    start_date = f'03/31/{last_year}'
    end_date = str(d)
    dir = f"resources/schedule/by_teams/{d}"
    fname = f"/{home}_{away}.json"
    if os.path.isfile(dir + fname):
        games = json.loads(read_stat_json(dir + fname))
    else:
        games = statsapi.schedule(start_date=start_date, end_date=end_date, team=home, opponent=away)
        write_stat_json(dir, fname, json.dumps(games))
    for game in games:
        game_id_list.append(game['game_id'])
    return game_id_list


def get_vs_game_ids(home, away):
    game_id_list = []
    year = date.today().year
    start_date = f'03/31/{year}'
    end_date = date.today().strftime("%m/%d/%Y")
    games = statsapi.schedule(start_date=start_date, end_date=end_date, team=home, opponent=away)
    for game in games:
        game_id_list.append(game['game_id'])
    return game_id_list


def get_game_contextMetrics(game_pk):
    return statsapi.get("game_contextMetrics", {"gamePk": game_pk})


def get_game_winProbability(game_pk):
    return statsapi.get("game_winProbability", {"gamePk": game_pk})