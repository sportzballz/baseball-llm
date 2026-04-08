from  connector.stats import *


def evaluate(home_team_id, away_team_id, game_ids, adv_score):
    home_wins = 0
    away_wins = 0

    for game_id in game_ids:
        game = get_boxscore(game_id)
        if game['teamInfo']['home']['id'] == home_team_id:
            if game['home']['teamStats']['batting']['runs'] > game['away']['teamStats']['batting']['runs']:
                home_wins += 1
            else:
                away_wins += 1
        else:
            if game['away']['teamStats']['batting']['runs'] > game['home']['teamStats']['batting']['runs']:
                home_wins += 1
            else:
                away_wins += 1

    if home_wins > away_wins:
        adv_score.home += 1
        adv_score.home_stats.append("Most wins")
    else:
        adv_score.away += 1
        adv_score.away_stats.append("Most wins")



        ## last 10 games record head to head
        ## Season stats Lineup against pitcher
        ## Lineup against handedness
    return adv_score


