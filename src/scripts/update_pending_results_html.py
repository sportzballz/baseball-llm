#!/usr/bin/env python3
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

SITE_REPO = Path('/Users/asmith/.openclaw/workspace/sportzballz.io')
ET = ZoneInfo('America/New_York')

ARTICLE_RE = re.compile(r'(<article class="pick-card">.*?</article>)', re.S)
H2_RE = re.compile(r'<h2>(.*?)</h2>', re.S)
RESULT_SPAN_RE = re.compile(r'<span class="res [^"]+">\s*(WIN|LOSS|PENDING|PUSH)\s*</span>', re.I)
LEAN_SIDE_RE = re.compile(r'Model lean side:\s*([^<]+)', re.I)
TOTAL_HEAD_RE = re.compile(r'^(.*?)\s+vs\s+(.*?)\s+—\s+(OVER|UNDER)\s+([0-9]+(?:\.[0-9]+)?)\s*$', re.I)
OVER_HEAD_RE = re.compile(r'^(.*?)\s+vs\s+(.*?)\s+—\s+OVER\s+([0-9]+(?:\.[0-9]+)?)\s*$', re.I)
UNDER_HEAD_RE = re.compile(r'^(.*?)\s+vs\s+(.*?)\s+—\s+UNDER\s+([0-9]+(?:\.[0-9]+)?)\s*$', re.I)
PICK_HEAD_RE = re.compile(r'^(.*?)\s+over\s+(.*?)\s*$', re.I)
DATE_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})(?:-plus-money|-run-line|-run-totals)?\.html$')


def _norm(s: str):
    return (s or '').strip().lower()


def _pair(a: str, b: str):
    return tuple(sorted([_norm(a), _norm(b)]))


def fetch_results_for_date(date_str: str):
    qs = urlencode({'sportId': 1, 'date': date_str, 'hydrate': 'linescore'})
    url = f'https://statsapi.mlb.com/api/v1/schedule?{qs}'
    data = json.loads(urlopen(url, timeout=30).read().decode('utf-8'))

    out = {}
    for d in data.get('dates', []) or []:
        for g in d.get('games', []) or []:
            status = ((g.get('status') or {}).get('detailedState') or '').lower()
            is_final = 'final' in status
            home = (((g.get('teams') or {}).get('home') or {}).get('team') or {}).get('name')
            away = (((g.get('teams') or {}).get('away') or {}).get('team') or {}).get('name')
            hr = (((g.get('teams') or {}).get('home') or {}).get('score'))
            ar = (((g.get('teams') or {}).get('away') or {}).get('score'))
            if not home or not away:
                continue
            out[_pair(home, away)] = {
                'home': home,
                'away': away,
                'home_runs': hr,
                'away_runs': ar,
                'is_final': is_final,
            }
    return out


def outcome_for_side(game, side_team: str):
    if not game or not game.get('is_final'):
        return None
    hr = game.get('home_runs')
    ar = game.get('away_runs')
    if hr is None or ar is None:
        return None
    if hr == ar:
        return 'PUSH'
    winner = game['home'] if hr > ar else game['away']
    return 'WIN' if _norm(side_team) == _norm(winner) else 'LOSS'


def outcome_for_total(game, direction: str, line: float):
    if not game or not game.get('is_final'):
        return None
    hr = game.get('home_runs')
    ar = game.get('away_runs')
    if hr is None or ar is None:
        return None
    total = float(hr + ar)
    if total == line:
        return 'PUSH'
    if direction.upper() == 'OVER':
        return 'WIN' if total > line else 'LOSS'
    return 'WIN' if total < line else 'LOSS'


def result_class(label: str):
    l = (label or '').upper()
    if l == 'WIN':
        return 'res-win'
    if l == 'LOSS':
        return 'res-loss'
    # Keep PUSH styled like pending pill for now.
    return 'res-pending'


def update_file(path: Path, games_map: dict):
    text = path.read_text(encoding='utf-8')
    changed = 0

    def update_article(article_html: str):
        nonlocal changed
        hm = H2_RE.search(article_html)
        if not hm:
            return article_html
        h2 = re.sub(r'<[^>]+>', '', hm.group(1)).strip()

        outcome = None
        if path.name.endswith('-run-totals.html'):
            m = TOTAL_HEAD_RE.match(h2)
            if not m:
                m2 = OVER_HEAD_RE.match(h2)
                if m2:
                    a, b, ln = m2.group(1), m2.group(2), m2.group(3)
                    m = (a, b, 'OVER', ln)
                else:
                    m3 = UNDER_HEAD_RE.match(h2)
                    if m3:
                        a, b, ln = m3.group(1), m3.group(2), m3.group(3)
                        m = (a, b, 'UNDER', ln)
            if isinstance(m, tuple):
                a, b, direction, ln = m
            else:
                a, b, direction, ln = m.group(1), m.group(2), m.group(3), m.group(4) if m else (None, None, None, None)
            if a and b and direction and ln:
                g = games_map.get(_pair(a, b))
                try:
                    outcome = outcome_for_total(g, direction, float(ln))
                except Exception:
                    outcome = None
        elif path.name.endswith('-run-line.html'):
            pair_m = re.match(r'^(.*?)\s+vs\s+(.*?)\s+—\s+Run Line Lean$', h2, re.I)
            lean_m = LEAN_SIDE_RE.search(article_html)
            if pair_m and lean_m:
                a, b = pair_m.group(1), pair_m.group(2)
                side = lean_m.group(1).strip()
                g = games_map.get(_pair(a, b))
                outcome = outcome_for_side(g, side)
        else:
            pick_m = PICK_HEAD_RE.match(h2)
            if pick_m:
                side, other = pick_m.group(1), pick_m.group(2)
                g = games_map.get(_pair(side, other))
                outcome = outcome_for_side(g, side)

        if not outcome:
            return article_html

        old = RESULT_SPAN_RE.search(article_html)
        if not old:
            return article_html
        new_span = f'<span class="res {result_class(outcome)}">{outcome}</span>'
        new_article = RESULT_SPAN_RE.sub(new_span, article_html, count=1)
        if new_article != article_html:
            changed += 1
        return new_article

    parts = []
    last = 0
    for m in ARTICLE_RE.finditer(text):
        parts.append(text[last:m.start()])
        parts.append(update_article(m.group(1)))
        last = m.end()
    parts.append(text[last:])

    new_text = ''.join(parts)
    if new_text != text:
        path.write_text(new_text, encoding='utf-8')
    return changed


def count_labels_in_file(path: Path):
    txt = path.read_text(encoding='utf-8')
    labels = re.findall(r'<span class="res [^"]+">\s*(WIN|LOSS|PENDING|PUSH)\s*</span>', txt, re.I)
    c = defaultdict(int)
    for l in labels:
        c[l.upper()] += 1
    return c


def update_history_counts(modified_dates):
    hist_path = SITE_REPO / 'data' / 'performance-history.json'
    if not hist_path.exists():
        return False
    history = json.loads(hist_path.read_text(encoding='utf-8'))
    by_date = {h.get('date'): h for h in history if isinstance(h, dict)}

    changed = False
    for d in modified_dates:
        row = by_date.get(d)
        if not row:
            continue

        daily = SITE_REPO / f'{d}.html'
        plus = SITE_REPO / f'{d}-plus-money.html'
        totals = SITE_REPO / f'{d}-run-totals.html'

        if daily.exists():
            c = count_labels_in_file(daily)
            total = sum(c.values())
            wins = c.get('WIN', 0)
            losses = c.get('LOSS', 0)
            decided = wins + losses
            pending = c.get('PENDING', 0) + c.get('PUSH', 0)
            row['total_picks'] = total
            row['wins'] = wins
            row['losses'] = losses
            row['decided'] = decided
            row['pending'] = pending
            row['win_rate'] = round((wins / decided) * 100, 1) if decided else None
            changed = True

            seg = (row.get('segments') or {}).get('all_picks')
            if isinstance(seg, dict):
                seg['total'] = total
                seg['wins'] = wins
                seg['losses'] = losses
                seg['decided'] = decided

        if plus.exists():
            c = count_labels_in_file(plus)
            total = sum(c.values())
            wins = c.get('WIN', 0)
            losses = c.get('LOSS', 0)
            decided = wins + losses
            row['plus_money_total'] = total
            row['plus_money_wins'] = wins
            row['plus_money_losses'] = losses
            row['plus_money_decided'] = decided
            row['plus_money_win_rate'] = round((wins / decided) * 100, 1) if decided else None
            changed = True

            seg = (row.get('segments') or {}).get('plus_money_picks')
            if isinstance(seg, dict):
                seg['total'] = total
                seg['wins'] = wins
                seg['losses'] = losses
                seg['decided'] = decided

        if totals.exists():
            c = count_labels_in_file(totals)
            total = sum(c.values())
            wins = c.get('WIN', 0)
            losses = c.get('LOSS', 0)
            decided = wins + losses
            seg = (row.get('segments') or {}).get('run_total_picks')
            if isinstance(seg, dict):
                seg['total'] = total
                seg['wins'] = wins
                seg['losses'] = losses
                seg['decided'] = decided
                changed = True

    if changed:
        hist_path.write_text(json.dumps(history, indent=2), encoding='utf-8')
    return changed


def main():
    today = datetime.now(ET).date()
    date_files = sorted([p for p in SITE_REPO.glob('*.html') if DATE_RE.match(p.name)])
    dates = sorted(set(DATE_RE.match(p.name).group(1) for p in date_files))
    target_dates = [d for d in dates if datetime.fromisoformat(d).date() < today]

    if not target_dates:
        print('No past date pages found to refresh.')
        return 0

    modified_dates = set()
    total_cards = 0
    for d in target_dates:
        games = fetch_results_for_date(d)
        files = [
            SITE_REPO / f'{d}.html',
            SITE_REPO / f'{d}-plus-money.html',
            SITE_REPO / f'{d}-run-line.html',
            SITE_REPO / f'{d}-run-totals.html',
        ]
        changed_for_date = 0
        for f in files:
            if not f.exists():
                continue
            changed_for_date += update_file(f, games)
        if changed_for_date > 0:
            modified_dates.add(d)
            total_cards += changed_for_date
            print(f'{d}: updated {changed_for_date} pending cards')

    hist_changed = update_history_counts(modified_dates)
    if hist_changed:
        print('Updated performance-history.json counts for modified dates')

    print(f'Modified dates: {len(modified_dates)} | cards updated: {total_cards}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
