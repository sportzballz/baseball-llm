import common.pickwinners as pickwinners
from  common.util import *
import model.carlton.hitting as hitting
import model.carlton.pitching as pitching
import model.carlton.vs as vs
import src as src
from datetime import datetime, timedelta
# from pybaseball import pitching_stats, chadwick_register, playerid_lookup


def pitching_backtest(adv_score, game_data, model):
    try:
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        game_date = game_data['gameData']['datetime']['officialDate']
        yesterday = (datetime.strptime(game_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        away_pitcher = get_pitcher_stats_by_date(away_pitcher_id, yesterday)
        home_pitcher = get_pitcher_stats_by_date(home_pitcher_id, yesterday)
        if len(home_pitcher['stats']) == 0 or len(away_pitcher['stats']) == 0:
            # print("No pitcher stats found for yesterday. Skipping...")
            return adv_score
        elif len(home_pitcher['stats'][0]['splits']) == 0 or len(away_pitcher['stats'][0]['splits']) == 0:
            # print("No pitcher splits found for yesterday. Skipping...")
            return adv_score
        else:
            home_pitcher_stats = home_pitcher['stats'][0]['splits'][0]['stat']
            away_pitcher_stats = away_pitcher['stats'][0]['splits'][0]['stat']
            return model.carlton.pitching.evaluate(adv_score, home_pitcher_stats, away_pitcher_stats, test=True)
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Stats: {d} {e}')
        return adv_score


def hitting_backtest(adv_score, game_data, year):
    try:
        home_last_game_data = get_last_game_data(game_data['gameData']['teams']['home']['id'], year, game_data['gamePk'])
        away_last_game_data = get_last_game_data(game_data['gameData']['teams']['away']['id'], year, game_data['gamePk'])

        away_last_batters = get_away_batters_by_gameid(away_last_game_data['gamePk'])
        home_last_batters = get_home_batters_by_gameid(home_last_game_data['gamePk'])
        away_batting_totals = get_away_batting_total_by_game_id(away_last_game_data['gamePk'])
        home_batting_totals = get_home_batting_total_by_game_id(home_last_game_data['gamePk'])
        home_lineup_profile = get_lineup_profile_by_date(home_last_batters, home_last_game_data['gameData']['datetime']['officialDate'])
        away_lineup_profile = get_lineup_profile_by_date(away_last_batters, away_last_game_data['gameData']['datetime']['officialDate'])

        return model.carlton.hitting.evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile, test=True)
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Hitting Stats: {d} {e}')
        return adv_score


def pitching(adv_score, game_data, model, lineups):
    try:
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        away_pitcher_full_name = game_data['gameData']['probablePitchers']['away']['fullName'].split()
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        away_pitcher = get_pitcher_stats(away_pitcher_id)
        home_pitcher = get_pitcher_stats(home_pitcher_id)

        home_pitcher_stats = home_pitcher['stats'][0]['stats']
        away_pitcher_stats = away_pitcher['stats'][0]['stats']
        # s = pybaseball_statcast("2019-06-24", "2019-06-25")
        # chadwick = chadwick_register()
        # player = playerid_lookup(away_pitcher_full_name[1], away_pitcher_full_name[0])
        #
        # # # print(chadwick['key_mlbam'])
        # # for mlbam in chadwick['key_mlbam']:
        # #     if mlbam['key_mlbam'] == away_pitcher_id:
        # #         print(mlbam['key_fangraphs'])
        # #         fan_id = mlbam['key_fangraphs']
        # pid = player['key_fangraphs'].values[0]
        # data = pitching_stats(2024, players=pid)
        # print(data['Stuff+'])
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Stats: {d} {e}')
        return adv_score
    return model.carlton.pitching.evaluate(adv_score, home_pitcher_stats, away_pitcher_stats)


def hitting(adv_score, game_data, model, lineups):
    away_team_id = game_data['gameData']['teams']['away']['id']
    home_team_id = game_data['gameData']['teams']['home']['id']
    away_last_batters = get_last_game_batters(away_team_id)
    home_last_batters = get_last_game_batters(home_team_id)
    away_batting_totals = get_last_game_batting_totals(away_team_id)
    home_batting_totals = get_last_game_batting_totals(home_team_id)
    home_lineup_profile = get_lineup_profile(home_last_batters)
    away_lineup_profile = get_lineup_profile(away_last_batters)
    return model.carlton.hitting.evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile)


def vs(adv_score, game_data, model, lineups):
    try:
        away_team_id = game_data['gameData']['teams']['away']['id']
        home_team_id = game_data['gameData']['teams']['home']['id']
        # away_last_batters = get_last_game_batters(away_team_id)
        # home_last_batters = get_last_game_batters(home_team_id)
        # away_batting_totals = get_last_game_batting_totals(away_team_id)
        # home_batting_totals = get_last_game_batting_totals(home_team_id)
        # home_lineup_profile = get_lineup_profile(home_last_batters)
        # away_lineup_profile = get_lineup_profile(away_last_batters)

        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']

        return model.carlton.vs.evaluate(adv_score, home_pitcher_id, away_pitcher_id, home_team_id, away_team_id)
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Vs Stats: {d} {e}')
        return adv_score


def main(event, context):
    print(event)
    model = "carlton"
    pickwinners.main(model, hitting, pitching, vs)


if __name__ == "__main__":
    main('', '')