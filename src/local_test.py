import datetime
import os

from  ashburn import *
from  bowa import *
from  common.util import *
from  connector.stats import *
from  common.pickwinners import main
import sys
from datetime import datetime, timedelta
import ashburn as ashburn
import bowa as bowa
import carlton as carlton
import ennis as ennis


def test(run_type, year, model):
    if run_type == 'today':
        if model == 'ashburn':
            ashburn.main(None, None)
        elif model == 'bowa':
            bowa.main(None, None)
        elif model == 'carlton':
            carlton.main(None, None)
        elif model == 'ennis':
            ennis.main(None, None)
    elif run_type == 'one-pick':
        start_date = date(int(year), 4, 1)
        end_date = date(int(year), 10, 1)
        delta = timedelta(days=1)
        odds_data = {"results": []}
        todays_picks = []
        picks_of_the_day = []
        teams_dict = get_teams_dict()
        team_ids_dict = get_team_ids_dict()
        winning_count = 0
        losing_count = 0
        while start_date <= end_date:
            games = get_schedule_by_date(start_date.strftime("%Y-%m-%d"))
            for game in games:
                game_data = statsapi.get("game", {"gamePk": game['game_id']})
                if game['game_type'] == 'R':
                    adv_score = AdvantageScore(1, 0)
                    adv_score = pitching_backtest(adv_score, game_data, year)
                    adv_score = hitting_backtest(adv_score, game_data, year)
                    projected_winner = select_winner(adv_score, game_data, odds_data)
                    if int(game['away_score']) > int(game['home_score']):
                        actual_winner_full_name = game['away_name']
                        actual_winner = teams_dict[actual_winner_full_name]
                    else:
                        actual_winner_full_name = game['home_name']
                        actual_winner = teams_dict[actual_winner_full_name] + '*'
                    todays_picks.append(PredictionActual(projected_winner, actual_winner))
            highest_confidence = 0.000
            for pick in todays_picks:
                if float(pick.prediction.confidence) > highest_confidence:
                    highest_confidence = float(pick.prediction.confidence)
                    if len(picks_of_the_day) == 0:
                        picks_of_the_day.append(pick)
                    else:
                        picks_of_the_day[0] = pick
            if picks_of_the_day[0].prediction.winning_team == picks_of_the_day[0].actual:
                msg = f"W: Date: {start_date} Projected: {picks_of_the_day[0].prediction.winning_team} | Actual: {picks_of_the_day[0].actual} | C: {picks_of_the_day[0].prediction.confidence} | DP: {picks_of_the_day[0].prediction.data_points} "
                post_to_slack_backtest(msg, model)
                print(msg)
                winning_count += 1
            else:
                msg = f"L: Date: {start_date} Projected: {picks_of_the_day[0].prediction.winning_team} | Actual: {picks_of_the_day[0].actual} | C: {picks_of_the_day[0].prediction.confidence} | DP: {picks_of_the_day[0].prediction.data_points} "
                post_to_slack_backtest(msg, model)
                print(msg)
                losing_count += 1
            todays_picks = []
            picks_of_the_day = []
            start_date += delta
        print(f"{year}: Winning Count: {winning_count} | Losing Count: {losing_count}")
    else:
        start_time = datetime.now()
        print(f'Start Time: {start_time}')
        teams = get_teams_list()
        odds_data = {"results": []}

        winners = []
        winning_count = 0
        losing_count = 0
        no_count = 0

        for team in teams:
            try:
                team_schedule = get_schedule_by_year(team.id, year)
                yesterdays_game_id = team_schedule[0]['game_id']
                yesterdays_game_data = statsapi.get("game", {"gamePk": yesterdays_game_id})
                # cm = get_game_contextMetrics(yesterdays_game_id)

                try:
                    for todays_game in team_schedule:
                        game_id = todays_game['game_id']
                        game_data = statsapi.get("game", {"gamePk": game_id})
                        if todays_game['game_type'] == 'R' and todays_game['home_name'] == team.name:
                            try:
                                wp = get_game_winProbability(game_id)
                                print(wp)
                                adv_score = AdvantageScore(0, 0)
                                adv_score = evaluate_pitching_matchup_backtest(adv_score, game_data)
                                adv_score = evaluate_hitting_matchup_backtest(adv_score, yesterdays_game_data)
                                # adv_score = evaluate_vs_matchup(adv_score, game_data)
                                projected_winner = select_winner(adv_score, game_data, odds_data).winning_team
                                actual_winner = todays_game['winning_team']
                                d = game_data['gameData']['datetime']['officialDate']
                                print(f"Team: {team.name} Date: {d} Projected Winner: {projected_winner} | Actual Winner: {actual_winner}")
                                if projected_winner == '-' or actual_winner == '-':
                                    no_count += 1
                                elif projected_winner == actual_winner:
                                    winning_count += 1
                                else:
                                    losing_count += 1
                            except Exception as e:
                                d = game_data['gameData']['datetime']['officialDate']
                                print(f'Error: {team.name} | {d} : {e}')
                                pass
                        yesterdays_game_data = game_data
                except Exception as e:
                    print(f'Error: {team.name} : {e}')
                    pass
            except Exception as e:
                pass

        # write_csv(winners)
        # print_csv(winners)
        print(f"Winning Count: {winning_count} | Losing Count: {losing_count} | No Pick Count: {no_count}")
        end_time = datetime.now()
        print(f'End Time: {end_time}')
        print(f'Time Elapsed: {end_time - start_time}')

        # print_str(winners)
        # post_to_slack(winners)


test(sys.argv[1],sys.argv[2], sys.argv[3])
