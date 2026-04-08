from  common.util import *
from  model.ashburn.weights import *


def evaluate(adv_score, home_pitcher_stats, away_pitcher_stats, test=False):
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'whip', WHIP_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'winPercentage', WIN_PERCENTAGE_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'strikeoutWalkRatio', STRIKEOUT_WALK_RATIO_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'strikeoutsPer9Inn', STRIKEOUTS_PER_9_INN_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'walksPer9Inn', WALKS_PER_9_INN_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'hitsPer9Inn', HITS_PER_9_INN_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'runsScoredPer9', RUNS_SCORED_PER_9_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'homeRunsPer9', HOME_RUNS_PER_9_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'stolenBasePercentage', STOLEN_BASE_PERCENTAGE_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'groundIntoDoublePlay', GROUND_INTO_DOUBLE_PLAY_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'era', ERA_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'completeGames', COMPLETE_GAMES_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'shutouts', SHUTOUTS_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'strikePercentage', STRIKE_PERCENTAGE_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'hitBatsmen', HIT_BATSMAN_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'balks', BALKS_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'wildPitches', WILD_PITCHES_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'pickoffs', PICKOFFS_WEIGHT)

    return adv_score
