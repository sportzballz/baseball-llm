from  common.util import *
from  connector.sportsbook import get_odds
from  connector.stats import *


def analyze_first_run(game_data):
    return True


def main():
    teams = get_teams_list()
    odds_data = {"results": []}
    odds_data = get_odds()
    nrfi = []
    yrfi = []
    day = date.today()
    for team in teams:
        todays_games = get_todays_games(team.id, day)
        if len(todays_games) > 0:
            todays_game = todays_games[0]
            game_id = todays_game['game_id']
            game_data = statsapi.get("game", {"gamePk": game_id})

            if todays_game['home_name'] == team.name:
                if analyze_first_run(game_data):
                    nrfi.append(game_data, odds_data)
                else:
                    yrfi.append(game_data, odds_data)

    # write_csv(winners)
    # print_csv(winners)
    # print_str(winners)
    # post_to_slack(winners, model)