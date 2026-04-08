from  connector.stats import *


def most_wins(home_team_id, away_team_id, game_ids, adv_score):
    home_wins = 0
    away_wins = 0

    for game_id in game_ids:
        game = get_boxscore(game_id)
        if game['teamInfo']['home']['id'] == home_team_id:
            if game['home']['teamStats']['batting']['runs'] > game['away']['teamStats']['batting']['runs']:
                home_wins += 1
            elif game['away']['teamStats']['batting']['runs'] > game['home']['teamStats']['batting']['runs']:
                away_wins += 1
        else:
            if game['away']['teamStats']['batting']['runs'] > game['home']['teamStats']['batting']['runs']:
                home_wins += 1
            elif game['home']['teamStats']['batting']['runs'] > game['away']['teamStats']['batting']['runs']:
                away_wins += 1
    if home_wins > away_wins:
        adv_score.home += 1
        adv_score.home_stats.append("Most wins")
    else:
        adv_score.away += 1
        adv_score.away_stats.append("Most wins")
    return adv_score


def hitters_vs_team(adv_score, home_team_id, away_team_id, game_ids):
    homeBAtBats = 0.0
    awayBAtBats = 0.0
    homeBhits = 0.0
    awayBhits = 0.0
    homeBruns = 0.0
    awayBruns = 0.0
    homeBwalks = 0.0
    awayBwalks = 0.0
    homeBhomeRuns = 0.0
    awayBhomeRuns = 0.0

    for game_id in game_ids:
        game = get_boxscore(game_id)
        if game['teamInfo']['home']['id'] == home_team_id:
            homeBatters = game['homeBatters']
            throw_away = homeBatters.pop(0)
            for batter in homeBatters:
                homeBAtBats = float(batter['ab'])
                if homeBAtBats == 0:
                    homeBAtBats = 1
                homeBhits += float(batter['h']) / homeBAtBats
                homeBruns += float(batter['r']) / homeBAtBats
                homeBwalks += float(batter['bb']) / homeBAtBats
                homeBhomeRuns += float(batter['hr']) / homeBAtBats
        if game['teamInfo']['home']['id'] == away_team_id:
            awayBatters = game['homeBatters']
            throw_away = awayBatters.pop(0)
            for batter in awayBatters:
                awayBAtBats = float(batter['ab'])
                if awayBAtBats == 0:
                    awayBAtBats = 1
                awayBhits += float(batter['h']) / awayBAtBats
                awayBruns += float(batter['r']) / awayBAtBats
                awayBwalks += float(batter['bb']) / awayBAtBats
                awayBhomeRuns += float(batter['hr']) / awayBAtBats
        if game['teamInfo']['away']['id'] == home_team_id:
            homeBatters = game['awayBatters']
            throw_away = homeBatters.pop(0)
            for batter in homeBatters:
                homeBAtBats = float(batter['ab'])
                if homeBAtBats == 0:
                    homeBAtBats = 1
                homeBhits += float(batter['h']) / homeBAtBats
                homeBruns += float(batter['r']) / homeBAtBats
                homeBwalks += float(batter['bb']) / homeBAtBats
                homeBhomeRuns += float(batter['hr']) / homeBAtBats
        if game['teamInfo']['away']['id'] == away_team_id:
            awayBatters = game['awayBatters']
            throw_away = awayBatters.pop(0)
            for batter in awayBatters:
                awayBAtBats = float(batter['ab'])
                if awayBAtBats == 0:
                    awayBAtBats = 1
                awayBhits += float(batter['h']) / awayBAtBats
                awayBruns += float(batter['r']) / awayBAtBats
                awayBwalks += float(batter['bb']) / awayBAtBats
                awayBhomeRuns += float(batter['hr']) / awayBAtBats

    if homeBhits > awayBhits:
        adv_score.home += 1
        adv_score.home_stats.append("Batters have most hits vs opposing pitcher")
    elif homeBhits < awayBhits:
        adv_score.away += 1
        adv_score.away_stats.append("Batters have most hits vs opposing pitcher")
    if homeBruns > awayBruns:
        adv_score.home += 1
        adv_score.home_stats.append("Batters have most runs vs opposing pitcher")
    elif homeBruns < awayBruns:
        adv_score.away += 1
        adv_score.away_stats.append("Batters have most runs vs opposing pitcher")
    if homeBwalks > awayBwalks:
        adv_score.home += 1
        adv_score.home_stats.append("Batters have most walks vs opposing pitcher")
    elif homeBwalks < awayBwalks:
        adv_score.away += 1
        adv_score.away_stats.append("Batters have most walks vs opposing pitcher")
    if homeBhomeRuns > awayBhomeRuns:
        adv_score.home += 1
        adv_score.home_stats.append("Batters have most home runs vs opposing pitcher")
    elif homeBhomeRuns < awayBhomeRuns:
        adv_score.away += 1
        adv_score.away_stats.append("Batters have most home runs vs opposing pitcher")

    return adv_score


def pitcher_vs_team(adv_score, home_pitcher_id, away_pitcher_id, game_ids):
    home_pitcher_stats = []
    away_pitcher_stats = []
    homePInningsPitched = 0.0
    awayPInningsPitched = 0.0
    homePhits = 0.0
    awayPhits = 0.0
    homePruns = 0.0
    awayPruns = 0.0
    homePearnedRuns = 0.0
    awayPearnedRuns = 0.0
    homePwalks = 0.0
    awayPwalks = 0.0
    homePhomeRuns = 0.0
    awayPhomeRuns = 0.0

    for game_id in game_ids:
        game = get_boxscore(game_id)
        for pitcher in game['homePitchers']:
            if pitcher['personId'] == home_pitcher_id:
                home_pitcher_stats.append(pitcher)
            if pitcher['personId'] == away_pitcher_id:
                away_pitcher_stats.append(pitcher)
        for pitcher in game['awayPitchers']:
            if pitcher['personId'] == home_pitcher_id:
                home_pitcher_stats.append(pitcher)
            if pitcher['personId'] == away_pitcher_id:
                away_pitcher_stats.append(pitcher)

    for home_pitcher_stat in home_pitcher_stats:
        homePInningsPitched += float(home_pitcher_stat['ip'])
        if homePInningsPitched == 0:
            homePInningsPitched = 1
        homePhits += float(home_pitcher_stat['h']) / homePInningsPitched
        homePruns += float(home_pitcher_stat['r']) / homePInningsPitched
        homePearnedRuns += float(home_pitcher_stat['er']) / homePInningsPitched
        homePwalks += float(home_pitcher_stat['bb']) / homePInningsPitched
        homePhomeRuns += float(home_pitcher_stat['hr']) / homePInningsPitched
    for away_pitcher_stat in away_pitcher_stats:
        awayPInningsPitched += float(away_pitcher_stat['ip'])
        if awayPInningsPitched == 0:
            awayPInningsPitched = 1
        awayPhits += float(away_pitcher_stat['h']) / awayPInningsPitched
        awayPruns += float(away_pitcher_stat['r']) / awayPInningsPitched
        awayPearnedRuns += float(away_pitcher_stat['er']) / awayPInningsPitched
        awayPwalks += float(away_pitcher_stat['bb']) / awayPInningsPitched
        awayPhomeRuns += float(away_pitcher_stat['hr']) / awayPInningsPitched

    # Makes sure that the pitcher stats are not empty so comparing them makes sense
    if len(home_pitcher_stats) == 0 or len(away_pitcher_stats) == 0:
        return adv_score

    if homePhits < awayPhits:
        adv_score.home += 1
        adv_score.home_stats.append("Pitcher has fewer hits vs opposing team")
    elif awayPhits < homePhits:
        adv_score.away += 1
        adv_score.away_stats.append("Pitcher has fewer hits vs opposing team")
    if homePruns < awayPruns:
        adv_score.home += 1
        adv_score.home_stats.append("Pitcher has fewer runs vs opposing team")
    elif awayPruns < homePruns:
        adv_score.away += 1
        adv_score.away_stats.append("Pitcher has fewer runs vs opposing team")
    if homePearnedRuns < awayPearnedRuns:
        adv_score.home += 1
        adv_score.home_stats.append("Pitcher has fewer earned runs vs opposing team")
    elif awayPearnedRuns < homePearnedRuns:
        adv_score.away += 1
        adv_score.away_stats.append("Pitcher has fewer earned runs vs opposing team")
    if homePwalks < awayPwalks:
        adv_score.home += 1
        adv_score.home_stats.append("Pitcher has fewer walks vs opposing team")
    elif awayPwalks < homePwalks:
        adv_score.away += 1
        adv_score.away_stats.append("Pitcher has fewer walks vs opposing team")
    if homePhomeRuns < awayPhomeRuns:
        adv_score.home += 1
        adv_score.home_stats.append("Pitcher has fewer home runs vs opposing team")
    elif awayPhomeRuns < homePhomeRuns:
        adv_score.away += 1
        adv_score.away_stats.append("Pitcher has fewer home runs vs opposing team")

    return adv_score


def away_vs_home_records(adv_score, home_team_id, away_team_id, d):
    away_game_ids = get_team_game_ids_before_date(away_team_id, d)
    home_game_ids = get_team_game_ids_before_date(home_team_id, d)

    home_wins = 0
    home_losses = 0
    away_wins = 0
    away_losses = 0
    home_game_ids = home_game_ids[-60:]
    away_game_ids = away_game_ids[-60:]
    for home_game_id in home_game_ids:
        home_game = get_game(home_game_id)
        if home_game['gameData']['teams']['home']['id'] == home_team_id:
            if home_game['liveData']['boxscore']['teams']['home']['teamStats']['batting']['runs'] > home_game['liveData']['boxscore']['teams']['away']['teamStats']['batting']['runs']:
                home_wins += 1
            else:
                home_losses += 1
    for away_game_id in away_game_ids:

        away_game = get_game(away_game_id)
        if away_game['gameData']['teams']['away']['id'] == away_team_id:
            if away_game['liveData']['boxscore']['teams']['away']['teamStats']['batting']['runs'] > away_game['liveData']['boxscore']['teams']['home']['teamStats']['batting']['runs']:
                away_wins += 1
            else:
                away_losses += 1
    home_win_percentage = home_wins / (home_wins + home_losses)
    away_win_percentage = away_wins / (away_wins + away_losses)

    if home_win_percentage > away_win_percentage:
        adv_score.home += 1
        adv_score.home_stats.append("Home team has better win percentage at home")
    elif away_win_percentage > home_win_percentage:
        adv_score.away += 1
        adv_score.away_stats.append("Away team has better win percentage on the road")

    return adv_score


def evaluate(adv_score, home_pitcher_id, away_pitcher_id, home_team_id, away_team_id, d, clf):
    game_ids = get_vs_game_ids_before_date(home_team_id, away_team_id, d)


    # game_ids = get_vs_game_ids(home_team_id, away_team_id)
    # games = get_vs_games(home_team_id, away_team_id)

    # head to head record
    adv_score = most_wins(home_team_id, away_team_id, game_ids, adv_score)

    # Season stats pitcher against this team
    adv_score = pitcher_vs_team(adv_score, home_pitcher_id, away_pitcher_id, game_ids)

    # Season stats batters against this team
    adv_score = hitters_vs_team(adv_score, home_team_id, away_team_id, game_ids)

    # away teams away record vs home teams home record
    # adv_score = away_vs_home_records(adv_score, home_team_id, away_team_id, d)

    return adv_score
