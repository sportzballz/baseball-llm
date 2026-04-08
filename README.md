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

The commentary includes (best effort):
- venue + weather context (or dome note when not applicable)
- umpire crew
- injured-list snapshot for both teams
- odds line movement (when opening line is available in feed)
- deterministic commentary summary for each pick (no external LLM dependency)

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
