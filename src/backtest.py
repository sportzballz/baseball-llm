import datetime
import json
import os

# from  analysis.pitching.pitchingevaluation import *
# from  analysis.batting.battingevaluation import *
# from  analysis.vs.vsevaluation import evaluate_vs_matchup
# from  common.util import *
# from  connector.stats import *
from datetime import date, timedelta, datetime
from time import sleep

import statsapi

from src import ennis
from  common.objects import AdvantageScore, BacktestMetrics, BankrollMetrics, WinLossMetrics, OddsMetrics, \
    ConfidenceMetrics, RuntimeMetrics
from  common.util import get_teams_list, select_winner, post_to_slack_backtest
from  connector import slack
from  connector.sportsbook import get_odds
from  connector.sportsbookreview import get_odds_by_date
from  connector.stats import get_schedule_by_date, get_boxscore, get_game
from  ml import get_clf


def format_odds_data(odds_data):
    results = []
    game_rows = odds_data['props']['pageProps']['oddsTables'][0]['oddsTableModel']['gameRows']
    for game_row in game_rows:
        teams = {}
        moneyline = {}
        current = {}
        odds = []
        teams.update({"home": {"team": game_row['gameView']['homeTeam']['fullName']}})
        teams.update({"away": {"team": game_row['gameView']['awayTeam']['fullName']}})

        if game_row['openingLineViews'][0] is None:
            moneyline = {"moneyline": {"current": {"homeOdds": 100,"awayOdds": 100}}}
        else:
            moneyline = {"moneyline": {"current": {"homeOdds": game_row['openingLineViews'][0]['currentLine']['homeOdds'],"awayOdds": game_row['openingLineViews'][0]['currentLine']['awayOdds']}}}

        odds.append(moneyline)
        results.append({"teams": teams, "odds": odds})
    return {"results": results}


def get_odds_data(date):
    if not os.path.exists(f"resources/odds/{date}.json"):
        get_odds_by_date(date)
    with open(f"resources/odds/{date}.json") as f:
        data = json.load(f)
    return format_odds_data(data)


def backtest_ml(start_date, end_date):
    delta = timedelta(days=1)
    samples = []
    results = []
    # for each day april through september
    while start_date <= end_date:
        start_date_str = start_date.strftime("%m/%d/%Y")
        print(start_date_str)
        teams = get_teams_list()
        games = get_schedule_by_date(start_date_str)
        for game in games:
            game_id = game['game_id']
            game_data = get_game(game_id)
            bx = get_boxscore(game_id)
            for team in teams:
                if game['home_name'] == team.name:
                    game_samples, game_results = ennis.ml_backest(game_data, str(start_date))
                    if len(game_samples[0]) > 0 and len(game_samples[1]) > 0:
                        samples.append(game_samples[0])
                        samples.append(game_samples[1])
                        results.append(game_results[0])
                        results.append(game_results[1])
                    else:
                        print("No samples")
        start_date += delta
    return samples, results



def backtest_one_pick(model, model_hitting_fn, model_pitching_fn, model_vs_fn, start_date, end_date, metrics):
    delta = timedelta(days=1)
    # for each day april through september
    while start_date <= end_date:
        start_date_str = start_date.strftime("%m/%d/%Y")
        odds_date_str = start_date.strftime("%Y-%m-%d")
        odds_data = get_odds_data(odds_date_str)
        print(start_date_str)
        teams = get_teams_list()
        # get the schedule for the day
        games = get_schedule_by_date(odds_date_str)
        # for each game in the schedule
        winners = []
        for game in games:
            # print(game["game_id"])
            game_id = game['game_id']
            game_data = get_game(game_id)
            for team in teams:
                if game['home_name'] == team.name:
                    home_stats = []
                    away_stats = []
                    adv_score = AdvantageScore(home=0, away=0, home_stats=home_stats, away_stats=away_stats, home_lineup_available=True, away_lineup_available=True)

                    adv_score = model_hitting_fn(adv_score, game_data, str(start_date))
                    adv_score = model_pitching_fn(adv_score, game_data, str(start_date))
                    adv_score = model_vs_fn(adv_score, game_data, str(start_date))
                    winner = select_winner(adv_score, game_data, odds_data)
                    # print(winner.to_string())
                    # print(adv_score.to_string())
                    winners.append(winner)

        metrics = post_to_slack_backtest(start_date_str, winners, model, metrics)
        start_date += delta


            # get the game data
            # pick the winner
            # add to winner list
    # find highest confidence pick
    # check if team with highest confidence pick won
    return metrics


def load_odds_data():
    start_date = date(2023, 3, 31)
    end_date = date(2023, 9, 30)
    delta = timedelta(days=1)
    current_date = start_date
    # for each day april through september
    while current_date <= end_date:
        current_date_str = current_date.strftime("%Y-%m-%d")
        get_odds_by_date(current_date_str)
        current_date += delta


def daily(event, context, metrics, model):
    yesterday = (datetime.strptime(str(date.today()), '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = yesterday
    end_date = yesterday
    return backtest_one_pick(model, ennis.hitting_backtest, ennis.pitching_backtest, ennis.vs_backtest, start_date, end_date, metrics)


def full_2024(metrics, model):
    # first half
    start_date = date(2023, 4, 1)
    end_date = date(2023, 7, 14)
    metrics = backtest_one_pick(model, ennis.hitting_backtest, ennis.pitching_backtest, ennis.vs_backtest, start_date, end_date, metrics)
    # slack.post_todays_pick_backtest("All Star Break", model)
    # second half
    start_date = date(2023, 7, 19)
    end_date = date(2023, 9, 30)
    metrics = backtest_one_pick(model, ennis.hitting_backtest, ennis.pitching_backtest, ennis.vs_backtest, start_date, end_date, metrics)
    return metrics


def full_ml():
    # first half 2023
    start_date = date(2023, 4, 1)
    end_date = date(2023, 7, 8)
    samples1, results1 = backtest_ml(start_date, end_date)

    # second half 2023
    start_date = date(2023, 7, 13)
    end_date = date(2023, 9, 30)
    samples2, results2 = backtest_ml(start_date, end_date)

    # first half 2024
    start_date = date(2024, 4, 1)
    end_date = date(2024, 7, 14)
    samples3, results3 = backtest_ml(start_date, end_date)

    # second half 2024
    start_date = date(2024, 7, 19)
    end_date = date(2024, 9, 30)
    samples4, results4 = backtest_ml(start_date, end_date)

    # first half 2025
    start_date = date(2025, 3, 30)
    end_date = date(2025, 4, 8)
    samples5, results5 = backtest_ml(start_date, end_date)

    return samples1 + samples2 + samples3 + samples4 + samples5, results1 + results2 + results3 + results4 + results5


def full_2023(metrics, model):
    # first half
    start_date = date(2023, 4, 1)
    end_date = date(2023, 7, 9)
    metrics = backtest_one_pick(model, ennis.hitting_backtest, ennis.pitching_backtest, ennis.vs_backtest, start_date, end_date, metrics)
    # slack.post_todays_pick_backtest("All Star Break", model)
    # second half
    start_date = date(2023, 7, 14)
    end_date = date(2023, 9, 30)
    metrics = backtest_one_pick(model, ennis.hitting_backtest, ennis.pitching_backtest, ennis.vs_backtest, start_date, end_date, metrics)
    return metrics


def adhoc(start_date, end_date, metrics, model):
    # first half
    backtest_one_pick(model, ennis.hitting_backtest, ennis.pitching_backtest, ennis.vs_backtest, start_date, end_date, metrics)


def main(event, context):
    # clf, samples, results = get_clf()
    new_samples, new_results = full_ml()

    # predicted_results = clf.predict(new_samples)
    # correct = 0
    # for i in range(len(predicted_results)):
    #     if results[i] == predicted_results[i]:
    #         correct += 1
    # print("Training Data Sample Size: ", len(samples))
    # print("Accuracy: ", correct / len(predicted_results) * 100, "%")


    # metrics = BacktestMetrics(
    #     BankrollMetrics(),
    #     WinLossMetrics(),
    #     OddsMetrics(),
    #     ConfidenceMetrics(),
    #     RuntimeMetrics())
    #
    # metrics.runtime_metrics.start_time = datetime.now()
    #slack.post_todays_pick_backtest(str(metrics.runtime_metrics.start_time), model)
    # daily(event, context, metrics, model)
    # metrics = full_2024(metrics, model)
    # adhoc(date(2024, 7, 25), date(2024, 8, 1), metrics, model)




    # metrics.complete()
    # print(metrics.toString())
    # slack.post_todays_pick_backtest(metrics.toString(), model)


main('event', 'context')
