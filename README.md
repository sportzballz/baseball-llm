# Baseball 

## Run Locally via Cron (Mac mini)

This project currently runs as an AWS Lambda (`handler = dutch.main`).
If you want it running locally as a scheduled cron job:

1) **Set up local Python env**
```bash
./cron/setup-local.sh
```

2) **Configure secrets/env vars**
```bash
cp .env.local.example .env.local
# then edit .env.local with real keys
```

3) **Test one local run**
```bash
./cron/run-local.sh
```

4) **Install cron schedule** (default: daily 12:00 PM)
```bash
./cron/install-cron.sh
```

Optional custom schedule:
```bash
./cron/install-cron.sh "0 17 * * 1-5"   # weekdays at 5 PM
```

Logs are written to `logs/<model>-YYYY-MM-DD.log`.

Each run also generates rich pick commentary markdown at:
- `picks/YYYY-MM-DD-pick.md`

Each local run now also refreshes matchup metrics cache at:
- `data/matchup-metrics/YYYY-MM-DD.json`
- script: `src/scripts/build_matchup_metrics.py`
- toggle: `REFRESH_MATCHUP_METRICS=true|false` (default `true`)

The commentary includes (best effort):
- venue + weather context (or dome note when not applicable)
- umpire crew
- injured-list snapshot for both teams
- odds line movement (when opening line is available in feed)
- deterministic commentary summary for each pick (no external LLM dependency)

## Matchup Metrics Source Map (implemented)

### Source endpoints
- MLB schedule + probable pitchers:
  - `https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=YYYY-MM-DD&hydrate=probablePitcher,team,linescore`
- MLB live feed (lineup status):
  - `https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live`
- Team season hitting stats:
  - `https://statsapi.mlb.com/api/v1/teams/{teamId}/stats?stats=season&group=hitting&season=YYYY`
- Probable pitcher season stats:
  - `https://statsapi.mlb.com/api/v1/people/{playerId}/stats?stats=season&group=pitching&season=YYYY`
- Odds (Sportspage RapidAPI):
  - `https://sportspage-feeds.p.rapidapi.com/games?odds=moneyline&league=MLB&date=YYYY-MM-DD`
- Weather (Open-Meteo, by ballpark coordinates):
  - `https://api.open-meteo.com/v1/forecast?...`

### Output contract (`data/matchup-metrics/YYYY-MM-DD.json`)
- `date`, `generated_at`, `count`
- `matchups[]` with:
  - `game_pk`, `game_time`, `status`, `venue`
  - `home/away`: team info, offense snapshot, probable pitcher snapshot
  - `lineups.both_announced`
  - `market`: open/current lines + movement + implied home probability
  - `weather`: temp/wind/humidity/precip snapshot
  - `bullpen.fatigue_score` (placeholder for next phase)

### Recommended cadence
- pre-model local run: refresh matchup metrics once per run (implemented)
- optional future: separate every-10m intraday line-move refresher

## TODO for Ennis Model
- [ x ] away team road record
- [ x ] home team home record
- [ ] Add over/under to the model
- [ ] Add runline to the model
- [ ] team vs time of day
- [ ] team vs weather
- [ ] team vs umpire
- [ ] pitcher historical innings pitched
- [ ] batters vs bullpen
- [ ] pitcher vs bench
- [ ] play with weights

## Todays Pick Notification Logic
- [ ] IF (Mon-Fri AND 5pm) || (Mon-Fri AND Game Start Before 5pm AND Lineups available)
- [ ]   ANNOUNCE
- [ ] IF (SAT or SUN AND 12pm) || (SAT or SUN AND Game Start AFTER 12pm AND Lineups available)
- [ ]   ANNOUNCE


## Relevent Stats
- [ ] OBP (On Base Percentage)
- [ ] SLG (number of bases player has reached / plate appearances)
- [ ] OPS (OBP + SLG)
- [ ] WHIP (Walks plus hits per inning pitched)

## Pitching
### Starting Pitching
- [x] Season win percentage
- [ ] Season win percentage vs team
- [ ] Last 10 start win percentage
- [ ] Last 10 start win percentage vs team
- [ ] Last 05 start win percentage
- [ ] Last 05 start win percentage vs team
- [ ] Last start in weather conditions
- [ ] win percentage day vs night
- [ ] ERA
- [x] WHIP
- [ ] Avg innings pitched
- [ ] Avg pitch count
- [ ] Home vs Away

### Bull Pen
- [ ] Available relievers
- [ ] Relievers era

## Batting
- [ ] Team avg OPS (On Base Percentage (how often player reached base) + Slugging ())
- [ ] OPS vs Starting Pitcher
- [ ] Home vs Away

## Intangibles
- [ ] Weather
- [ ] Venue
- [ ] Crowd size
- [ ] Wind direction
- [ ] temperature

### Advanced metrics now wired into scoring
- Team offense advanced: ISO, BABIP, BB/PA, K/PA, HR/PA, pitches/PA
- Probable pitcher advanced: K/9, BB/9, HR/9, K/BB, OBP/SLG/OPS allowed
- Bullpen freshness: 3-day workload-derived home/away fatigue and freshness edge
- Market consensus dispersion: books count, moneyline range/stddev, outlier-book count
- Park factors: run factor and HR factor per venue (neutral fallback)
- Lineup platoon edge: announced lineup handedness vs opposing probable pitcher throw hand

### Weight tuning helper
- Script: `src/scripts/tune_metric_weights.py`
- Runs a quick grid sweep against finalized cached-metric games and prints recommended values for:
  - `METRIC_WEIGHT_MARKET`
  - `METRIC_WEIGHT_PITCHING`
  - `METRIC_WEIGHT_OFFENSE`
  - `METRIC_WEIGHT_BULLPEN`
  - `METRIC_WEIGHT_CONTEXT`
