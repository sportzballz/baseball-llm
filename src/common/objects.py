import statistics
from datetime import datetime

import pytz


class WinLossMetrics:
    def __init__(self, win_count=0, loss_count=0, current_consecutive_loss_streak=0, current_consecutive_win_streak=0,
                 consecutive_loss_list=[], consecutive_win_list=[], last_loss=False):
        self.win_count = win_count
        self.loss_count = loss_count
        self.current_consecutive_loss_streak = current_consecutive_loss_streak
        self.current_consecutive_win_streak = current_consecutive_win_streak
        self.consecutive_loss_list = consecutive_loss_list
        self.consecutive_win_list = consecutive_win_list
        self.last_loss = last_loss

    def complete(self):
        if self.last_loss:
            self.consecutive_loss_list.append(self.current_consecutive_loss_streak)
        else:
            self.consecutive_win_list.append(self.current_consecutive_win_streak)

    def addWin(self):
        self.win_count += 1
        if self.last_loss:
            self.current_consecutive_win_streak = 1
            self.consecutive_loss_list.append(self.current_consecutive_loss_streak)
            self.current_consecutive_loss_streak = 0
        else:
            self.current_consecutive_win_streak += 1
        self.last_loss = False

    def addLoss(self):
        self.loss_count += 1
        if self.last_loss:
            self.current_consecutive_loss_streak += 1
        else:
            self.current_consecutive_loss_streak = 1
            self.consecutive_win_list.append(self.current_consecutive_win_streak)
            self.current_consecutive_win_streak = 0
        self.last_loss = True

    def toString(self):
        return "-----------------------\n" \
               "Win Loss Metrics\n" \
               "-----------------------\n" \
               f'Win Count: {self.win_count},\n' \
               f'Loss Count: {self.loss_count},\n' \
               f'Win Percentage: {round(self.win_count / (self.win_count + self.loss_count) * 100, 2)}%,\n' \
               f'Consecutive Loss Min: {self.getLosingMin()},\n' \
               f'Consecutive Loss Max: {self.getLosingMax()},\n' \
               f'Consecutive Loss Mean: {self.getLosingMean()},\n' \
               f'Consecutive Loss Median: {self.getLosingMedian()},\n' \
               f'Consecutive Win Min: {self.getWinningMin()},\n' \
               f'Consecutive Win Max: {self.getWinningMax()},\n' \
               f'Consecutive Win Mean: {self.getWinningMean()},\n' \
               f'Consecutive Win Median: {self.getWinningMedian()}'


# f'Consecutive Loss List: {self.consecutive_loss_list},\n' \
# f'Consecutive Win List: {self.consecutive_win_list}\n, \'' \

    def getWinningMin(self):
        return min(self.consecutive_win_list)

    def getLosingMin(self):
        return min(self.consecutive_loss_list)

    def getWinningMax(self):
        return max(self.consecutive_win_list)

    def getLosingMax(self):
        return max(self.consecutive_loss_list)

    def getWinningMean(self):
        return statistics.mean(self.consecutive_win_list)

    def getLosingMean(self):
        return statistics.mean(self.consecutive_loss_list)

    def getWinningMedian(self):
        if len(self.consecutive_win_list) == 0:
            return 0
        m = statistics.median(self.consecutive_win_list)
        return m

    def getLosingMedian(self):
        if len(self.consecutive_loss_list) == 0:
            return 0
        m = statistics.median(self.consecutive_loss_list)
        return m


class OddsMetrics:
    def __init__(self, winning_odds_data=[], losing_odds_data=[]):
        self.winning_odds_data = winning_odds_data
        self.losing_odds_data = losing_odds_data

    def addWin(self, odds_data):
        self.winning_odds_data.append(odds_data)

    def addLoss(self, odds_data):
        self.losing_odds_data.append(odds_data)


    def getWinningMin(self):
        return min(self.winning_odds_data)

    def getLosingMin(self):
        return min(self.losing_odds_data)

    def getWinningMax(self):
        return max(self.winning_odds_data)

    def getLosingMax(self):
        return max(self.losing_odds_data)

    def getWinningMean(self):
        return sum(self.winning_odds_data) / len(self.winning_odds_data)

    def getLosingMean(self):
        return sum(self.losing_odds_data) / len(self.losing_odds_data)

    def getWinningMedian(self):
        return statistics.median(self.winning_odds_data)

    def getLosingMedian(self):
        return statistics.median(self.losing_odds_data)

    def toString(self):
        return "-----------------------\n" \
               "Odds Metrics\n" \
               "-----------------------\n" \
               f'Losing Odds Min: {self.getLosingMin()},\n' \
               f'Winning Odds Max: {self.getWinningMax()},\n' \
               f'Winning Odds Mean: {self.getWinningMean()},\n' \
               f'Losing Odds Mean: {self.getLosingMean()},\n'
               # f'Winning Odds Median: {self.getWinningMedian()},\n' \
               # f'Losing Odds Median: {self.getLosingMedian()}'
                # f'Losing Odds Max: {self.getLosingMax()},\n' \
                # f'Winning Odds Data: {self.winning_odds_data},\n' \
                # f'Losing Odds Data: {self.losing_odds_data}\n' \
                # f'Winning Odds Min: {self.getWinningMin()},\n' \


class ConfidenceMetrics:
    def __init__(self, winning_confidence_data=[], losing_confidence_data=[]):
        self.winning_confidence_data = winning_confidence_data
        self.losing_confidence_data = losing_confidence_data

    def addWin(self, confidence_data):
        self.winning_confidence_data.append(confidence_data)

    def addLoss(self, confidence_data):
        self.losing_confidence_data.append(confidence_data)

    def getWinningMin(self):
        return min(self.winning_confidence_data)

    def getLosingMin(self):
        return min(self.losing_confidence_data)

    def getWinningMax(self):
        return max(self.winning_confidence_data)

    def getLosingMax(self):
        return max(self.losing_confidence_data)

    def getWinningMean(self):
        return sum(self.winning_confidence_data) / len(self.winning_confidence_data)

    def getLosingMean(self):
        return sum(self.losing_confidence_data) / len(self.losing_confidence_data)

    def getWinningMedian(self):
        return statistics.median(self.winning_confidence_data)

    def getLosingMedian(self):
        return statistics.median(self.losing_confidence_data)

    def toString(self):
        return "-----------------------\n" \
               "Confidence Metrics\n" \
               "-----------------------\n" \
               f'Losing Confidence Min: {self.getLosingMin()},\n' \
               f'Winning Confidence Max: {self.getWinningMax()},\n' \
               f'Winning Confidence Mean: {self.getWinningMean()},\n' \
               f'Losing Confidence Mean: {self.getLosingMean()},\n'
               # f'Winning Confidence Median: {self.getWinningMedian()},\n' \
               # f'Losing Confidence Median: {self.getLosingMedian()}'
                # f'Losing Confidence Max: {self.getLosingMax()},\n' \
                # f'Winning Confidence Data: {self.winning_confidence_data},\n' \
                # f' Losing Confidence Data: {self.losing_confidence_data}\n' \
                # f'Winning Confidence Min: {self.getWinningMin()},\n' \


class BankrollMetrics:
    def __init__(self, current_bankroll=1000, max_bankroll=1000, min_bankroll=1000):
        self.current_bankroll = current_bankroll
        self.max_bankroll = max_bankroll
        self.min_bankroll = min_bankroll

    def setBankroll(self, amt):
        self.current_bankroll = amt
        if self.current_bankroll > self.max_bankroll:
            self.max_bankroll = self.current_bankroll
        if self.current_bankroll < self.min_bankroll:
            self.min_bankroll = self.current_bankroll

    def getCurrentBankroll(self):
        return f"Current Bankroll: ${self.current_bankroll}"

    def toString(self):
        return "-----------------------\n" \
               "Bankroll Metrics\n" \
               "-----------------------\n" \
               f"Current Bankroll: {self.current_bankroll}\n" \
               f"Max Bankroll: {self.max_bankroll}\n" \
               f"Min Bankroll: {self.min_bankroll}"


class RuntimeMetrics:
    def __init__(self, start_time=None, end_time=None):
        self.start_time = start_time
        self.end_time = end_time

    def complete(self):
        self.end_time = datetime.now(pytz.timezone('US/Eastern'))

    def getRuntime(self):
        return self.end_time - self.start_time

    def toString(self):
        return "-----------------------\n" \
               "Runtime Metrics\n" \
               "-----------------------\n" \
               f"Start Time: {self.start_time}\n" \
               f"End Time: {self.end_time}\n" \
               f"Runtime: {self.getRuntime()}"


class BacktestMetrics:
    def __init__(self, bankroll: BankrollMetrics, win_loss: WinLossMetrics, odds_metrics: OddsMetrics,
                 confidence_metrics: ConfidenceMetrics, runtime_metrics: RuntimeMetrics):
        self.bankroll = bankroll
        self.win_loss = win_loss
        self.odds_metrics = odds_metrics
        self.confidence_metrics = confidence_metrics
        self.runtime_metrics = runtime_metrics

    def toString(self):
        return "@@@@@@@@@@@@@@@@@@@@@@@@\n" \
               "Backtest Metrics\n" \
               "@@@@@@@@@@@@@@@@@@@@@@@@\n" \
               f"{self.odds_metrics.toString()}\n" \
               f"{self.confidence_metrics.toString()}\n" \
               f"{self.runtime_metrics.toString()}\n" \
               f"{self.bankroll.toString()}\n" \
               f"{self.win_loss.toString()}\n, " \
               "^^^^^^^^^^^^^^^^^^^^^^^^^^^^"

    def complete(self):
        self.win_loss.complete()
        self.runtime_metrics.complete()


class Prediction:
    def __init__(self, winning_team: str, losing_team: str, winning_pitcher: str, losing_pitcher: str, gameDate: str,
                 gameTime: str, ampm: str,
                 odds: int, confidence: str, data_points: str = '0/0',
                 winning_stats=None, losing_stats=None):
        self.winning_team = winning_team
        self.losing_team = losing_team
        self.winning_pitcher = winning_pitcher
        self.losing_pitcher = losing_pitcher
        self.gameDate = gameDate
        self.gameTime = gameTime
        self.ampm = ampm
        self.odds = odds
        self.confidence = confidence
        self.data_points = data_points
        self.winning_stats = winning_stats or []
        self.losing_stats = losing_stats or []

    def print_string(self):
        print(self.to_string())

    def to_string(self):
        try:
            self.odds = int(self.odds)
        except ValueError:
            self.odds = 0
        if self.odds > 0:
            self.odds = f"+{self.odds}"
        elif self.odds == 0:
            self.odds = "----"
        return f"```{self.odds} {self.winning_team.upper()} over {self.losing_team.upper()} c:{self.confidence} dp:{self.data_points} {self.gameTime}{self.ampm}, {self.winning_pitcher} / {self.losing_pitcher}```"

    def to_csv(self):
        print(f"{self.odds},{self.winning_team},{self.losing_team},{self.gameDate},{self.winning_pitcher}")

    def get_csv(self):
        return f",{self.odds},{self.winning_team},{self.losing_team},{self.gameDate},{self.winning_pitcher}"


class PredictionActual:
    def __init__(self, prediction: Prediction, actual: str):
        self.prediction = prediction
        self.actual = actual


class PitchingMatchup:
    def __init__(self, whip_advantage: int, win_percentage_advantage: int):
        self.whip_advantage = whip_advantage
        self.win_percentage_advantage = win_percentage_advantage


class Team:
    def __init__(self, abbreviation: str, id: int, name: str):
        self.abbreviation = abbreviation
        self.name = name
        self.id = id


class AdvantageScore:
    def __init__(self, home: int = 0, away: int = 0, home_stats=[], away_stats=[], home_lineup_available=False,
                 away_lineup_available=False):
        self.home = home
        self.away = away
        self.home_stats = home_stats
        self.away_stats = away_stats
        self.home_lineup_available = home_lineup_available
        self.away_lineup_available = away_lineup_available

    def to_string(self):
        return f'home: {str(self.home)} away: {str(self.away)}, home stats: {str(self.home_stats)}, away stats {str(self.away_stats)}, home lineup available {str(self.home_lineup_available)}, away lineup available {str(self.away_lineup_available)}'


class WEIGHT:
    def __init__(self, weight: int, lower_is_better: bool):
        self.weight = weight
        self.lower_is_better = lower_is_better


class LineupPlayer:
    def __init__(self, player_id, player_name, player_position, player_batting_order):
        self.player_id = player_id
        self.player_name = player_name
        self.player_position = player_position
        self.player_batting_order = player_batting_order


class Lineup:
    def __init__(self, team_id, lineup_players):
        self.team_id = team_id
        self.lineup_players = lineup_players
