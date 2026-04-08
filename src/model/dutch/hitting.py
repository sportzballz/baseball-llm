from  common.util import *
from  model.dutch.weights import *


def evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile, test=False):
    # adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'r', R_WEIGHT)
    # adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'h', H_WEIGHT)
    # adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'hr', HR_WEIGHT)
    # adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'rbi', RBI_WEIGHT)
    # adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'bb', BB_WEIGHT)
    # adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'k', K_WEIGHT)
    # adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'lob', LOB_WEIGHT)

    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'avg', 'atBats', False, test=test)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'groundOuts', 'atBats', True, test=test)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'airOuts', 'atBats', True, test=test)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'runs', 'atBats', False, test=test)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'doubles', 'atBats', False, test=test)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'triples', 'atBats', False, test=test)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'homeRuns', 'atBats', False, test=test)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'rbi', 'atBats', False, test=test)
    return adv_score