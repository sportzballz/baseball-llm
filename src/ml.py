import json
from sklearn.ensemble import RandomForestClassifier
import os




class Sample:
    def __init__(self, avg: float, sos: float, rbi: float, winloss: bool):
        self.avg = avg
        self.sos = sos
        self.rbi = rbi
        self.winloss = winloss


def read_game_json(file):
    text_file = open(file, "r")
    json_str = text_file.read()
    text_file.close()
    return json_str


def load_game_files():
    stats = []
    directory = "resources/boxscore"  # Replace with the actual path
    for filename in os.listdir(directory):
        f = os.path.join(directory, filename)
        if os.path.isfile(f):
            stats.append(json.loads(read_game_json(f)))
    return stats


def get_winner_loser(game):
    away_runs = int(game['away']['teamStats']['batting']['runs'])
    home_runs = int(game['home']['teamStats']['batting']['runs'])
    if away_runs > home_runs:
        away_win = 1
        home_win = 0
    else:
        away_win = 0
        home_win = 1
    return away_win, home_win


def get_batting_stats(players):
    batting_stats_dict = {}
    for player_id in list(players):
        at_bats = float(players[player_id]['stats']['batting'].get('atBats', "0.0"))
        if float(at_bats) > 0:
            batting_stat_names = list(players[player_id]['seasonStats']['batting'])
            for batting_stat_name in batting_stat_names:
                if batting_stat_name in batting_stats_dict:
                    batting_stats_dict[batting_stat_name] += float(
                        players[player_id]['seasonStats']['batting'][batting_stat_name])
                else:
                    batting_stats_dict[batting_stat_name] = float(
                        players[player_id]['seasonStats']['batting'][batting_stat_name])
    return list(batting_stats_dict.values())


def get_pitching_stats(players):
    pitching_stats_dict = {}
    for player_id in list(players):
        innings_pitched = float(players[player_id]['stats']['pitching'].get('inningsPitched', "0.0"))
        stat = 0.0
        if float(innings_pitched) > 0:
            pitching_stat_names = list(players[player_id]['seasonStats']['pitching'])
            for pitching_stat_name in pitching_stat_names:
                if pitching_stat_name in pitching_stats_dict:
                    pitching_stats_dict[pitching_stat_name] += float(players[player_id]['seasonStats']['pitching'][pitching_stat_name])
                else:
                    pitching_stats_dict[pitching_stat_name] = float(players[player_id]['seasonStats']['pitching'][pitching_stat_name])
    return list(pitching_stats_dict.values())


def load_model_data(games: list):
    samples = []
    results = []

    for game in games:
        away_win, home_win = get_winner_loser(game)
        away_players = game['away']['players']
        home_players = game['home']['players']

        home_batting_stats = get_batting_stats(home_players)
        home_pitching_stats = get_pitching_stats(home_players)
        home_stats = home_batting_stats + home_pitching_stats

        away_batting_stats = get_batting_stats(away_players)
        away_pitching_stats = get_pitching_stats(away_players)
        away_stats = away_batting_stats + away_pitching_stats

        if len(away_stats) != 0 and len(home_stats) != 0 and len(away_stats) == len(home_stats):
            samples.append(away_stats)
            results.append(away_win)
            samples.append(home_stats)
            results.append(home_win)
    return samples, results


def train_model(clf, samples, results):
    clf.fit(samples, results)
    predicted_results = clf.predict(samples)
    correct = 0
    for i in range(len(predicted_results)):
        if results[i] == predicted_results[i]:
            correct += 1
    print("Training Data Sample Size: ", len(samples))
    print("Accuracy: ", correct / len(predicted_results) * 100, "%")
    return clf


def get_clf():
    games = load_game_files()
    samples, results = load_model_data(games)
    clf = train_model(RandomForestClassifier(random_state=0), samples, results)
    return clf, samples, results
