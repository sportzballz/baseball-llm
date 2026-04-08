import common.pickwinners as pickwinners
from src import ml
from util import *
import model.ennis.hitting as hitting
import model.ennis.pitching as pitching
import model.ennis.vs as vs
import src as src
from datetime import datetime, timedelta


def ml_backest(game_data, dt):
    batting_metrics = ['runs', 'doubles', 'triples', 'homeRuns', 'strikeOuts', 'baseOnBalls', 'hits', 'avg', 'atBats', 'obp', 'slg', 'ops', 'stolenBases', 'rbi', 'leftOnBase']
    pitching_metrics = ['runs', 'doubles', 'triples', 'homeRuns', 'strikeOuts', 'baseOnBalls', 'hits', 'atBats', 'obp', 'stolenBases', 'numberOfPitches', 'era', 'inningsPitched', 'wins', 'losses', 'holds', 'blownSaves', 'earnedRuns', 'pitchesThrown', 'strikes', 'rbi']
    home_pitching_sample = {}
    away_pitching_sample = {}
    home_hitting_sample = {}
    away_hitting_sample = {}
    samples = []
    results = []
    game = get_boxscore(game_data['gamePk'])
    ## seed samples
    for batting_metric in batting_metrics:
        home_hitting_sample[batting_metric] = 0.0
        away_hitting_sample[batting_metric] = 0.0
    for pitching_metric in pitching_metrics:
        home_pitching_sample[pitching_metric] = 0.0
        away_pitching_sample[pitching_metric] = 0.0
    ## PITCHING
    try:
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        game_date = game_data['gameData']['datetime']['officialDate']
        d = datetime.strptime(dt, "%Y-%m-%d").date()
        yesterday = (datetime.strptime(game_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

        away_pitcher = get_pitcher_stats_by_date(away_pitcher_id, yesterday)
        home_pitcher = get_pitcher_stats_by_date(home_pitcher_id, yesterday)

        if len(home_pitcher['stats']) == 0 or len(away_pitcher['stats']) == 0:
            print("No pitcher stats found for yesterday. Skipping...")
            # for pitching_metric in pitching_metrics:
            #     home_pitching_sample[pitching_metric] = 0.0
            #     away_pitching_sample[pitching_metric] = 0.0
        elif len(home_pitcher['stats'][0]['splits']) == 0 or len(away_pitcher['stats'][0]['splits']) == 0:
            print("No pitcher splits found for yesterday. Skipping...")
            # for pitching_metric in pitching_metrics:
            #     home_pitching_sample[pitching_metric] = 0.0
            #     away_pitching_sample[pitching_metric] = 0.0
        else:

            for pitching_metric in pitching_metrics:
                splits_count = len(home_pitcher['stats'][0]['splits'])
                if splits_count > 0:
                    pitcher_stats = home_pitcher['stats'][0]['splits'][splits_count - 1]['stat']
                    for pitcher_stat in pitcher_stats:
                        if pitcher_stat == pitching_metric:
                            a1 = home_pitching_sample.get(pitcher_stat, 0)
                            a2 = pitcher_stats[pitcher_stat]
                            home_pitching_sample[pitcher_stat] = float(home_pitching_sample.get(pitcher_stat, 0)) + float(pitcher_stats[pitcher_stat])
                            break

            for pitching_metric in pitching_metrics:
                splits_count = len(away_pitcher['stats'][0]['splits'])
                if splits_count > 0:
                    pitcher_stats = away_pitcher['stats'][0]['splits'][splits_count - 1]['stat']
                    for pitcher_stat in pitcher_stats:
                        if pitcher_stat == pitching_metric:
                            a1 = away_pitching_sample.get(pitcher_stat, 0)
                            a2 = pitcher_stats[pitcher_stat]
                            away_pitching_sample[pitcher_stat] = float(away_pitching_sample.get(pitcher_stat, 0)) + float(pitcher_stats[pitcher_stat])
                            break



        # get last game id for each team (this may not be used)
        home_last_game_id = get_last_game_by_date(game_data['gameData']['teams']['home']['id'], d)
        away_last_game_id = get_last_game_by_date(game_data['gameData']['teams']['away']['id'], d)

        # get current games lineup
        home_batters = get_home_batters_by_gameid(game_data['gamePk'])
        away_batters = get_away_batters_by_gameid(game_data['gamePk'])

        # get stats as of yesterday for todays lineup
        home_lineup_profiles = get_lineup_profile_by_date(home_batters, yesterday)
        away_lineup_profiles = get_lineup_profile_by_date(away_batters, yesterday)

        for batting_metric in batting_metrics:
            for lineup_profile in home_lineup_profiles:
                splits_count = len(lineup_profile['stats'][0]['splits'])
                if splits_count > 0:
                    batter_stats = lineup_profile['stats'][0]['splits'][splits_count - 1]['stat']
                    for batter_stat in batter_stats:
                        if batter_stat == batting_metric:
                            a1 = home_hitting_sample.get(batter_stat, 0)
                            a2 = batter_stats[batter_stat]
                            home_hitting_sample[batter_stat] = float(home_hitting_sample.get(batter_stat, 0)) + float(batter_stats[batter_stat])
                            break
        for batting_metric in batting_metrics:
            for lineup_profile in away_lineup_profiles:
                splits_count = len(lineup_profile['stats'][0]['splits'])
                if splits_count > 0:
                    batter_stats = lineup_profile['stats'][0]['splits'][splits_count - 1]['stat']
                    for batter_stat in batter_stats:
                        if batter_stat == batting_metric:
                            away_hitting_sample[batter_stat] = float(away_hitting_sample.get(batter_stat, 0.0)) + float(batter_stats[batter_stat])
                            break

        home_sample = list(home_hitting_sample.values()) + list(home_pitching_sample.values())
        away_sample = list(away_hitting_sample.values()) + list(away_pitching_sample.values())

        samples.append(home_sample)
        samples.append(away_sample)

        away_win, home_win = ml.get_winner_loser(game)
        results.append(home_win)
        results.append(away_win)

        return samples, results

    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Stats: {d} {e}')
        return [[], []], [[], []]


def pitching_backtest(adv_score, game_data, year):
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
            home_splits_count = len(home_pitcher['stats'][0]['splits'])
            away_splits_count = len(away_pitcher['stats'][0]['splits'])
            home_pitcher_stats = home_pitcher['stats'][0]['splits'][home_splits_count - 1]['stat']
            away_pitcher_stats = away_pitcher['stats'][0]['splits'][away_splits_count - 1]['stat']
        return ennis.pitching.evaluate(adv_score, home_pitcher_stats, away_pitcher_stats, test=True)
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Stats: {d} {e}')
        return adv_score


def hitting_backtest(adv_score, game_data, dt):
    try:
        d = datetime.strptime(dt, "%Y-%m-%d").date()
        yesterday = (datetime.strptime(dt, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

        # get last game id for each team (this may not be used)
        home_last_game_id = get_last_game_by_date(game_data['gameData']['teams']['home']['id'], d)
        away_last_game_id = get_last_game_by_date(game_data['gameData']['teams']['away']['id'], d)

        # get current games lineup
        home_batters = get_home_batters_by_gameid(game_data['gamePk'])
        away_batters = get_away_batters_by_gameid(game_data['gamePk'])

        # get yesterdays batting totals (this may not be used
        away_batting_totals = get_away_batting_total_by_game_id(away_last_game_id)
        home_batting_totals = get_home_batting_total_by_game_id(home_last_game_id)

        # get stats as of yesterday for todays lineup
        home_lineup_profile = get_lineup_profile_by_date(home_batters, yesterday)
        away_lineup_profile = get_lineup_profile_by_date(away_batters, yesterday)

        return ennis.hitting.evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile, test=True)
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Hitting Stats: {d} {e}')
        return adv_score


def vs_backtest(adv_score, game_data, dt):
    try:
        d = datetime.strptime(dt, "%Y-%m-%d").date()
        yesterday = (datetime.strptime(dt, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        away_team_id = game_data['gameData']['teams']['away']['id']
        home_team_id = game_data['gameData']['teams']['home']['id']
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        return ennis.vs.evaluate(adv_score, home_pitcher_id, away_pitcher_id, home_team_id, away_team_id, yesterday)
    except Exception as e:
        print(f'Unable to get VS Stats: {e}')
        return adv_score


def pitching(adv_score, game_data, model, lineups):
    try:
        yesterday = (datetime.strptime(str(date.today()), '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        away_pitcher = get_pitcher_stats_by_date(away_pitcher_id, yesterday)
        home_pitcher = get_pitcher_stats_by_date(home_pitcher_id, yesterday)

        if len(home_pitcher['stats']) == 0 or len(away_pitcher['stats']) == 0:
            # print("No pitcher stats found for yesterday. Skipping...")
            return adv_score
        elif len(home_pitcher['stats'][0]['splits']) == 0 or len(away_pitcher['stats'][0]['splits']) == 0:
            # print("No pitcher splits found for yesterday. Skipping...")
            return adv_score
        else:
            home_splits_count = len(home_pitcher['stats'][0]['splits'])
            away_splits_count = len(away_pitcher['stats'][0]['splits'])
            home_pitcher_stats = home_pitcher['stats'][0]['splits'][home_splits_count - 1]['stat']
            away_pitcher_stats = away_pitcher['stats'][0]['splits'][away_splits_count - 1]['stat']
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Stats: {d} {e}')
        return adv_score
    return ennis.pitching.evaluate(adv_score, home_pitcher_stats, away_pitcher_stats)


def hitting(adv_score, game_data, model, lineups):
    yesterday = (datetime.strptime(str(date.today()), '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

    away_team_id = game_data['gameData']['teams']['away']['id']
    home_team_id = game_data['gameData']['teams']['home']['id']
    home_lineup = []
    away_lineup = []
    for lineup in lineups:
        if lineup.team_id == away_team_id:
            away_lineup = lineup.lineup_players
        elif lineup.team_id == home_team_id:
            home_lineup = lineup.lineup_players

    away_last_batters = get_last_game_batters(away_team_id)
    home_last_batters = get_last_game_batters(home_team_id)
    away_batting_totals = get_last_game_batting_totals(away_team_id)
    home_batting_totals = get_last_game_batting_totals(home_team_id)

    # if todays lineups are available use them, otherwise use yesterdays
    if len(home_lineup) > 0:
        adv_score.home_lineup_available = True
        home_lineup_profile = get_lineup_profile_by_date(home_lineup, yesterday)
        print(f'home lineup avalable: {adv_score.to_string()}')
    else:
        home_lineup_profile = get_lineup_profile_by_date(home_last_batters, yesterday)
    if len(away_lineup) > 0:
        adv_score.away_lineup_available = True
        away_lineup_profile = get_lineup_profile_by_date(away_lineup, yesterday)
        print(f'away lineup avalable: {adv_score.to_string()}')
    else:
        away_lineup_profile = get_lineup_profile_by_date(away_last_batters, yesterday)

    return ennis.hitting.evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile)


def vs(adv_score, game_data, model, lineups):
    yesterday = (datetime.strptime(str(date.today()), '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        away_team_id = game_data['gameData']['teams']['away']['id']
        home_team_id = game_data['gameData']['teams']['home']['id']
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']

        return ennis.vs.evaluate(adv_score, home_pitcher_id, away_pitcher_id, home_team_id, away_team_id, yesterday)
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Vs Stats: {d} {e}')
        return adv_score


def main(event, context):
    print(event)
    model = "dutch"
    pickwinners.main(model, hitting, pitching, vs)


if __name__ == "__main__":
    main('', '')