import os
import re
import html
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
import statsapi


SITE_BASE_URL = os.environ.get('SPORTZBALLZ_SITE_URL', 'https://sportzballz.io').rstrip('/')
HIT_COUNTER_ENDPOINT = os.environ.get('SPORTZBALLZ_HIT_COUNTER_ENDPOINT', 'https://5pakmkcroalpibvk2y7did66pu0extmx.lambda-url.us-east-1.on.aws/').strip()

ANALYST_PANEL = [
    {'id': 'mack-ledger', 'name': 'Mack Ledger', 'title': 'Market Maker', 'voice': 'sharp, odds-first, risk language, no fluff'},
    {'id': 'nora-splitter', 'name': 'Nora Splitter', 'title': 'Matchup Film Room', 'voice': 'tactical, pitcher-hitter context, game-script focus'},
    {'id': 'dex-numbers', 'name': 'Dex Numbers', 'title': 'Quant', 'voice': 'highly educated quantitative framing and probability-first language'},
    {'id': 'rico-heatcheck', 'name': 'Rico Heatcheck', 'title': 'Momentum & Vibes', 'voice': 'energetic and fan-readable confidence framing'},
    {'id': 'grant-halberd', 'name': 'Grant Halberd', 'title': 'Beat Writer', 'voice': 'polished concise journalist-style lead paragraphs'},
    {'id': 'ivy-chen', 'name': 'Ivy Chen', 'title': 'Data Scientist', 'voice': 'analytical precision and edge validation'},
    {'id': 'toby-quinn', 'name': 'Toby Quinn', 'title': 'Contrarian', 'voice': 'hunts overreactions and pricing mistakes'},
    {'id': 'lena-park', 'name': 'Lena Park', 'title': 'Weather/Umpire Specialist', 'voice': 'context-rich with practical game impact'},
    {'id': 'vince-valentino', 'name': 'Vince Valentino', 'title': 'Showman', 'voice': 'charismatic and entertaining with bold openers'},
    {'id': 'maya-rios', 'name': 'Maya Rios', 'title': 'Process Coach', 'voice': 'calm and disciplined with bankroll awareness'},
    {'id': 'owen-pike', 'name': 'Owen Pike', 'title': 'Model Whisperer', 'voice': 'probability-heavy but plain language'},
    {'id': 'jules-archer', 'name': 'Jules Archer', 'title': 'Underdog Hunter', 'voice': 'plus-money specialist with selective aggression'},
    {'id': 'roman-slate', 'name': 'Roman Slate', 'title': 'Line Movement Hawk', 'voice': 'serious edge-focused market movement analysis'},
    {'id': 'keira-bloom', 'name': 'Keira Bloom', 'title': 'Injury/Lineup Impact', 'voice': 'availability and roster-impact framing'},
    {'id': 'eli-mercer', 'name': 'Eli Mercer', 'title': 'Totals Architect', 'voice': 'run-environment and scoring-profile specialist'},
    {'id': 'sanjay-vale', 'name': 'Sanjay Vale', 'title': 'CLV Auditor', 'voice': 'closing-line-value discipline and process rigor'},
]


def _pick_analyst(pick, idx, date_text=''):
    seed = f"{date_text}|{pick.get('winner','')}|{pick.get('loser','')}|{idx}"
    digest = hashlib.sha256(seed.encode('utf-8')).hexdigest()
    pos = int(digest[:8], 16) % len(ANALYST_PANEL)
    return ANALYST_PANEL[pos]


def _site_url(path: str):
    p = path if path.startswith('/') else f'/{path}'
    return f"{SITE_BASE_URL}{p}"


def _render_robots_txt():
    return f"""User-agent: *
Allow: /

Sitemap: {_site_url('/sitemap.xml')}
"""


def _render_sitemap_xml(archive_dates):
    urls = [
        _site_url('/'),
        _site_url('/dashboard.html'),
        _site_url('/media-kit.html'),
        _site_url('/rate-card.html'),
        _site_url('/contact.html'),
    ]

    for d in sorted(set(archive_dates), reverse=True):
        urls.append(_site_url(f'/{d}.html'))
        urls.append(_site_url(f'/{d}-run-line.html'))
        urls.append(_site_url(f'/{d}-plus-money.html'))
        urls.append(_site_url(f'/{d}-run-totals.html'))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        lines.append(f'  <url><loc>{html.escape(u)}</loc></url>')
    lines.append('</urlset>')
    return '\n'.join(lines)


def _render_ad_slot(slot_id: str, label: str, cta: str = '/media-kit.html'):
    return f'''<section class="ad-slot" data-slot="{html.escape(slot_id)}">
      <div class="ad-label">Sponsored</div>
      <div class="ad-copy">{html.escape(label)} • Your brand could be here.</div>
      <a class="ad-cta" href="{html.escape(cta)}">Advertise on SportzBallz</a>
    </section>'''


def _render_media_kit():
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http://www.w3.org/2000/svg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Ctext%20y%3D%22.9em%22%20font-size%3D%2290%22%3E%E2%9A%BE%3C/text%3E%3C/svg%3E" />
  <title>SportzBallz | Media Kit</title>
  <meta name="description" content="SportzBallz media kit: audience, sponsorship inventory, and ad opportunities." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/media-kit.html')}" />
  <style>
    :root {{ --bg:#0b1020; --panel:#121c35; --ink:#e8efff; --muted:#9db1dc; --line:#2a3f72; --accent:#63d2ff; --accent2:#7cffc7; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(1000px 650px at 10% -10%, #20356f, var(--bg)); color:var(--ink); font-family:Inter,system-ui,sans-serif; }}
    .wrap {{ max-width:980px; margin:0 auto; padding:24px 16px 48px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:16px; margin-bottom:14px; }}
    h1 {{ margin:0 0 8px; }} h2 {{ margin:0 0 10px; font-size:22px; }}
    .muted {{ color:var(--muted); }}
    ul {{ margin:8px 0 0 18px; }} li {{ margin:6px 0; }}
    .btn {{ display:inline-block; margin-right:8px; margin-top:8px; padding:8px 12px; border-radius:10px; text-decoration:none; color:#081224; background:linear-gradient(90deg,var(--accent),var(--accent2)); font-weight:700; }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="card">
      <h1>SportzBallz Media Kit</h1>
      <p class="muted">Daily MLB picks, plus-money cards, run-total leans, and performance tracking.</p>
      <a class="btn" href="/rate-card.html">View Rate Card</a>
      <a class="btn" href="/">Back to Homepage</a>
    </section>
    <section class="card"><h2>Audience & Format</h2><ul><li>MLB bettors seeking daily picks with structured context</li><li>Underdog/plus-money focused readers</li><li>Users who value transparent performance tracking</li></ul></section>
    <section class="card"><h2>Sponsorship Inventory</h2><ul><li>Homepage hero sponsor</li><li>Daily picks page sponsored placement</li><li>Plus money page sponsor</li><li>Run totals page sponsor</li><li>Dashboard sponsor</li></ul></section>
    <section class="card"><h2>Contact</h2><p>To sponsor SportzBallz, contact: <strong>info@sportzballz.io</strong>.</p></section>
  </main>
  {_embed_mode_script()}
  {_hit_counter_script()}
</body>
</html>
'''


def _render_rate_card():
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http://www.w3.org/2000/svg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Ctext%20y%3D%22.9em%22%20font-size%3D%2290%22%3E%E2%9A%BE%3C/text%3E%3C/svg%3E" />
  <title>SportzBallz | Rate Card</title>
  <meta name="description" content="SportzBallz sponsorship pricing and ad package options." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/rate-card.html')}" />
  <style>
    :root {{ --bg:#0b1020; --panel:#121c35; --ink:#e8efff; --muted:#9db1dc; --line:#2a3f72; --accent:#63d2ff; --accent2:#7cffc7; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(1000px 650px at 10% -10%, #20356f, var(--bg)); color:var(--ink); font-family:Inter,system-ui,sans-serif; }}
    .wrap {{ max-width:980px; margin:0 auto; padding:24px 16px 48px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:16px; margin-bottom:14px; }}
    table {{ width:100%; border-collapse:collapse; }} th, td {{ padding:10px 8px; border-bottom:1px solid #2a3f70; text-align:left; }}
    th {{ font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:#cfe0ff; }}
    .muted {{ color:var(--muted); }}
    .btn {{ display:inline-block; margin-right:8px; margin-top:8px; padding:8px 12px; border-radius:10px; text-decoration:none; color:#081224; background:linear-gradient(90deg,var(--accent),var(--accent2)); font-weight:700; }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="card">
      <h1>SportzBallz Rate Card</h1>
      <p class="muted">Starter pricing — tune as traffic and conversion data matures.</p>
      <a class="btn" href="/media-kit.html">Media Kit</a><a class="btn" href="/contact.html">Contact</a><a class="btn" href="/">Homepage</a>
    </section>
    <section class="card">
      <table><thead><tr><th>Placement</th><th>Pricing</th><th>Notes</th></tr></thead><tbody>
        <tr><td>Homepage sponsor</td><td>$250–$750 / month</td><td>Prime brand placement on index.</td></tr>
        <tr><td>Daily picks sponsor</td><td>$150–$500 / month</td><td>Appears on core daily card pages.</td></tr>
        <tr><td>Plus-money sponsor</td><td>$125–$400 / month</td><td>Targets underdog/value readers.</td></tr>
        <tr><td>Run totals sponsor</td><td>$125–$400 / month</td><td>Targets totals-focused readers.</td></tr>
        <tr><td>Dashboard sponsor</td><td>$150–$500 / month</td><td>Performance page audience.</td></tr>
        <tr><td>Bundle package</td><td>$600–$1,500 / month</td><td>Index + daily + dashboard bundle.</td></tr>
      </tbody></table>
    </section>
  </main>
  {_embed_mode_script()}
  {_hit_counter_script()}
</body>
</html>
'''


def _render_contact_page():
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http://www.w3.org/2000/svg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Ctext%20y%3D%22.9em%22%20font-size%3D%2290%22%3E%E2%9A%BE%3C/text%3E%3C/svg%3E" />
  <title>SportzBallz | Contact</title>
  <meta name="description" content="Contact SportzBallz for partnerships, feedback, picks questions, and sponsorship inquiries." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/contact.html')}" />
  <style>
    :root {{ --bg:#060b17; --panel:#0b1328; --ink:#e6f1ff; --muted:#93a7cc; --line:#28436d; --accent:#00d1ff; --accent2:#7cff7a; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(1200px 700px at 80% -10%, #1b3a7a 0%, transparent 55%), radial-gradient(900px 600px at 0% 0%, #0b4f66 0%, transparent 45%), #050a14; color:var(--ink); font-family:Inter,system-ui,sans-serif; }}
    .wrap {{ max-width:920px; margin:0 auto; padding:24px 16px 56px; }}
    .card {{ background:linear-gradient(180deg,#0a142a,#0b1730); border:1px solid #2d4f86; border-radius:16px; padding:18px; margin-bottom:14px; }}
    h1 {{ margin:0 0 8px; }}
    .muted {{ color:var(--muted); }}
    label {{ display:block; margin:10px 0 6px; font-size:13px; color:#cfe0ff; }}
    input, textarea {{ width:100%; border:1px solid #355b92; border-radius:10px; background:#0d1930; color:#edf5ff; padding:10px 12px; font:inherit; }}
    textarea {{ min-height:140px; resize:vertical; }}
    .row {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
    .btn {{ display:inline-block; margin-right:8px; margin-top:12px; padding:9px 13px; border-radius:10px; text-decoration:none; color:#081224; background:linear-gradient(90deg,var(--accent),var(--accent2)); font-weight:700; border:none; cursor:pointer; }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="card">
      <h1>Contact SportzBallz</h1>
      <p class="muted">Questions, feedback, sponsorships, or collaboration ideas — send a note and we’ll get back to you.</p>
      <p><strong>Email:</strong> <a href="mailto:info@sportzballz.io?subject=SportzBallz%20Inquiry" style="color:#9fe7ff">info@sportzballz.io</a></p>
    </section>

    <section class="card">
      <h2 style="margin-top:0">Quick message</h2>
      <form id="contactForm">
        <div class="row">
          <div><label for="name">Name</label><input id="name" required /></div>
          <div><label for="email">Email</label><input id="email" type="email" required /></div>
        </div>
        <label for="topic">Topic</label><input id="topic" placeholder="Sponsorship / Feedback / Picks Question" />
        <label for="message">Message</label><textarea id="message" required></textarea>
        <button class="btn" type="submit">Open Email Draft</button>
        <a class="btn" href="/">Back to Homepage</a>
      </form>
      <p class="muted" style="margin-top:10px">This form opens your email app with a prefilled message.</p>
    </section>
  </main>

  <script>
    document.getElementById('contactForm')?.addEventListener('submit', (e) => {{
      e.preventDefault();
      const name = document.getElementById('name').value.trim();
      const email = document.getElementById('email').value.trim();
      const topic = document.getElementById('topic').value.trim() || 'General Inquiry';
      const msg = document.getElementById('message').value.trim();
      const subject = encodeURIComponent(`SportzBallz Contact: ${{topic}}`);
      const body = encodeURIComponent(`Name: ${{name}}\nEmail: ${{email}}\nTopic: ${{topic}}\n\nMessage:\n${{msg}}`);
      window.location.href = `mailto:info@sportzballz.io?subject=${{subject}}&body=${{body}}`;
    }});
  </script>
  {_embed_mode_script()}
  {_hit_counter_script()}
</body>
</html>
'''


def _toolbar_css():
    return '''
    .nav-toolbar { margin:14px 0 18px; display:grid; grid-template-columns:1fr 1.25fr 1fr; gap:10px; align-items:start; }
    .toolbar-group { border:1px solid #2d446f; border-radius:12px; padding:10px; background:#0f1a30; min-height:56px; display:flex; flex-direction:column; justify-content:flex-start; }
    .toolbar-group summary { cursor:pointer; color:#e6efff; font-size:12px; text-transform:uppercase; letter-spacing:.08em; font-weight:800; list-style:none; text-align:center; border:1px solid #375486; border-radius:10px; padding:10px 12px; background:#132241; }
    .toolbar-group summary::-webkit-details-marker { display:none; }
    .toolbar-group[open] summary { margin-bottom:8px; }
    .toolbar-group summary a { color:#e6efff; text-decoration:none; font-size:12px; text-transform:uppercase; letter-spacing:.08em; font-weight:800; }
    .nav-toolbar > .toolbar-group > summary { min-height:44px; display:flex; align-items:center; justify-content:center; }
    .toolbar-links { display:flex; gap:8px; flex-wrap:wrap; justify-content:center; }
    .toolbar-links a { color:#e7f0ff; text-decoration:none; border:1px solid #355184; border-radius:8px; padding:8px 10px; font-size:13px; background:#12203d; }
    .toolbar-links a:hover { border-color:var(--accent, #63d2ff); }
    .archive-group { border:1px solid #2d446f; border-radius:10px; padding:10px 12px; background:#101c34; margin-bottom:10px; }
    .archive-group summary { cursor:pointer; font-weight:700; color:#dfeeff; }
    .archive-links { margin-top:10px; display:grid; gap:8px; }
    .archive-links a { color:var(--ink, #ebf1ff); text-decoration:none; border:1px solid #355184; border-radius:8px; padding:8px 10px; background:#12203d; }
    .archive-links a:hover { border-color:var(--accent, #63d2ff); }
    .pill { font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:#dff4ff; background:#1b3d67; border:1px solid #2f679f; border-radius:999px; padding:3px 7px; white-space:nowrap; }
    @media (max-width:1100px) { .nav-toolbar { grid-template-columns:1fr; } }
'''


def _render_global_toolbar(latest_date: str, archive_dates):
    latest_href = f"/{latest_date}.html"
    latest_plus_href = f"/{latest_date}-plus-money.html"
    latest_totals_href = f"/{latest_date}-run-totals.html"

    archive_toolbar_groups = []
    for i, d in enumerate(sorted(set(archive_dates), reverse=True)):
        latest_pill = ' <span class="pill">Latest</span>' if i == 0 else ''
        archive_toolbar_groups.append(f'''
          <details class="archive-group">
            <summary>{d}{latest_pill}</summary>
            <div class="archive-links">
              <a href="/{d}.html">Daily Picks</a>
              <a href="/{d}-plus-money.html">Plus Money Picks</a>
              <a href="/{d}-run-totals.html">Run Total Picks</a>
            </div>
          </details>
        ''')

    return f'''
      <div class="nav-toolbar">
        <details class="toolbar-group">
          <summary><a href="https://sportzballz.io">⚾ Latest Daily Picks</a></summary>
        </details>
        <details class="toolbar-group">
          <summary>🗂️ Archive</summary>
          {''.join(archive_toolbar_groups)}
        </details>
        <details class="toolbar-group">
          <summary><a href="/dashboard.html">📊 Performance Dashboard</a></summary>
        </details>
      </div>
    '''


def _embed_mode_script():
    return '''
  <script>
    (() => {
      try {
        document.querySelectorAll('[data-reload="1"]').forEach((el) => {
          el.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.reload();
          });
        });
        const params = new URLSearchParams(window.location.search || '');
        if (params.get('embed') === '1') {
          document.querySelectorAll('.nav-toolbar').forEach((el) => el.remove());
        }
      } catch (_e) {}
    })();
  </script>
'''


def _hit_counter_script():
    endpoint = html.escape(HIT_COUNTER_ENDPOINT)
    return f'''
  <script>window.SBZ_HIT_ENDPOINT = "{endpoint}";</script>
  <script defer src="/assets/hit-counter.js"></script>
'''


def _parse_confidence(conf_text: str):
    if not conf_text:
        return None
    m = re.search(r'([0-9]+\.[0-9]+|[0-9]+)', conf_text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _parse_data_points(conf_text: str):
    if not conf_text:
        return None
    m = re.search(r'data points:\s*(\d+)\/(\d+)', conf_text, re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _confidence_bucket(conf):
    if conf is None:
        return "unclear"
    if conf >= 0.45:
        return "high-conviction"
    if conf >= 0.25:
        return "solid"
    if conf >= 0.10:
        return "moderate"
    return "thin"


def _line_movement_note(text):
    t = (text or "").lower()
    if not t or "unavailable" in t:
        return "Market movement is limited in the feed, so this leans more on matchup signals than tape-reading the number."
    if "toward the pick side" in t:
        return "The market has drifted toward the pick side, which supports the model read but can compress value at the margin."
    if "away from the pick side" in t:
        return "The number has moved away from the pick side, which can improve price value if you trust the underlying edge."
    if "unchanged" in t:
        return "The line has held steady, suggesting a relatively stable market view into first pitch."
    return f"Line context: {text}"


def _total_odds_pick(total_line_text):
    # expected: "8 (Over -115 / Under -105)"
    if not total_line_text:
        return None, None, None
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*\(Over\s*([+-]?\d+|—)\s*/\s*Under\s*([+-]?\d+|—)\)', total_line_text)
    if not m:
        return None, None, None
    total = float(m.group(1))
    over_odds = None if m.group(2) == '—' else int(m.group(2))
    under_odds = None if m.group(3) == '—' else int(m.group(3))
    return total, over_odds, under_odds


def _run_total_lean(pick):
    winner, loser = pick['winner'], pick['loser']
    weather = _field(pick, 'Weather', '')
    venue = _field(pick, 'Venue', '')
    w_sig = _field(pick, f'{winner} Model Signals', '')
    l_sig = _field(pick, f'{loser} Model Signals', '')
    total_line_text = _field(pick, 'Total Line', '')
    total_move_text = _field(pick, 'Total Movement', '')

    total, over_odds, under_odds = _total_odds_pick(total_line_text)
    if total is None:
        return None

    sig_text = f"{w_sig}, {l_sig}".lower()
    over_score = 0
    under_score = 0
    reasons = []

    # Weather heuristics
    w = weather.lower()
    if 'dome' in w or 'roof' in w:
        reasons.append('roof-controlled environment')
    wind_m = re.search(r'(\d+)\s*mph', w)
    wind = int(wind_m.group(1)) if wind_m else 0
    if 'out to' in w and wind >= 10:
        over_score += 2
        reasons.append('wind blowing out')
    if 'in from' in w and wind >= 10:
        under_score += 2
        reasons.append('wind blowing in')

    temp_m = re.search(r'(\d+)°f', w)
    temp = int(temp_m.group(1)) if temp_m else None
    if temp is not None and temp >= 78:
        over_score += 1
        reasons.append('warm run environment')
    if temp is not None and temp <= 52:
        under_score += 1
        reasons.append('cool run environment')
    if 'rain' in w:
        under_score += 1
        reasons.append('rain suppression risk')

    # Signal heuristics (internal only, not exposing raw names)
    over_terms = ['runs', 'homeruns', 'doubles', 'triples', 'rbi', 'runsscoredper9', 'homerunsper9', 'batters have most runs', 'batters have most home runs']
    under_terms = ['era', 'whip', 'strikeoutsper9', 'strikepercentage', 'pitcher has fewer runs', 'pitcher has fewer earned runs', 'pitcher has fewer home runs']

    over_hits = sum(1 for t in over_terms if t in sig_text)
    under_hits = sum(1 for t in under_terms if t in sig_text)
    if over_hits > under_hits:
        over_score += 1
        reasons.append('offensive indicator edge')
    elif under_hits > over_hits:
        under_score += 1
        reasons.append('run-prevention indicator edge')

    # Market nudge
    tm = total_move_text.lower()
    if 'moved up' in tm:
        over_score += 1
        reasons.append('market moved total up')
    elif 'moved down' in tm:
        under_score += 1
        reasons.append('market moved total down')

    if over_score == under_score:
        side = 'OVER' if (over_odds or 0) >= (under_odds or 0) else 'UNDER'
    else:
        side = 'OVER' if over_score > under_score else 'UNDER'

    conf_text = _field(pick, 'Model Confidence', '0')
    conf = _parse_confidence(conf_text) or 0
    edge = abs(over_score - under_score)
    total_conf = round((edge * 0.15) + (conf * 0.35), 3)

    return {
        'winner': winner,
        'loser': loser,
        'venue': venue,
        'pick': side,
        'line': total,
        'over_odds': over_odds,
        'under_odds': under_odds,
        'confidence': total_conf,
        'weather': weather,
        'total_movement': total_move_text,
        'reasons': reasons[:4],
    }


def _run_total_result_for_pick(pick, lean):
    game = pick.get('_game') or {}
    home_score = game.get('home_score')
    away_score = game.get('away_score')
    is_final = bool(game.get('is_final'))

    if not (is_final and home_score is not None and away_score is not None):
        return 'PENDING'

    total_runs = int(home_score) + int(away_score)
    line = lean.get('line')
    if line is None:
        return 'UNKNOWN'

    if total_runs > float(line):
        actual_side = 'OVER'
    elif total_runs < float(line):
        actual_side = 'UNDER'
    else:
        actual_side = 'PUSH'

    if actual_side == 'PUSH':
        return 'UNKNOWN'
    return 'WIN' if actual_side == lean.get('pick') else 'LOSS'


def _weather_note(venue, weather):
    w = weather or ""
    if "dome/retractable roof" in w.lower() or "not applicable" in w.lower():
        return f"At {venue}, roof conditions mute weather volatility, keeping this matchup more talent-and-execution driven."

    wind_match = re.search(r'(\d+)\s*mph', w.lower())
    wind = int(wind_match.group(1)) if wind_match else None
    if wind and wind >= 12:
        return f"Weather is a real variable here ({weather}); that wind profile can materially influence run environment and ball carry."
    if w and "unavailable" not in w.lower():
        return f"Conditions at {venue} ({weather}) are worth tracking, but they don’t look extreme enough to override core matchup factors."
    return f"Weather detail is limited from {venue}, so this reads primarily through pitcher profile, lineup edge, and market context."


def _injury_note(winner, loser, winner_inj, loser_inj):
    def cnt(txt):
        if not txt or txt.lower().startswith('n/a'):
            return 0
        return max(1, txt.count(',') + 1)

    w = cnt(winner_inj)
    l = cnt(loser_inj)
    if w == 0 and l == 0:
        return "Injury reporting is light in this feed, so availability risk appears neutral on both sides."
    if l - w >= 2:
        return f"Availability leans slightly toward {winner}; {loser} is carrying a heavier listed injury load."
    if w - l >= 2:
        return f"Injury depth leans against {winner}, so this position depends more heavily on matchup execution than roster health."
    return "Injury load looks relatively balanced, so this projects as a baseball-context and pricing decision more than a health fade."


def _umpire_note(ump):
    if not ump or "unavailable" in ump.lower():
        return "Umpire assignment is unclear at publish time, so plate-profile impact remains a late variable."
    hp = None
    for part in ump.split(';'):
        p = part.strip()
        if p.lower().startswith('home plate:'):
            hp = p.split(':', 1)[1].strip()
            break
    if hp:
        return f"Home plate assignment ({hp}) is in place, which sharp bettors will monitor for zone tendencies once game action starts."
    return f"Crew assignment is posted ({ump}), adding context for in-game strike-zone texture and pace."


def _lineup_status_note(text):
    t = (text or "").strip()
    if not t or t.lower() in ("n/a", "unavailable"):
        return "Starting lineup status is unavailable at publish time."
    tl = t.lower()
    if "not announced" in tl:
        return f"Lineup status check: {t}"
    if "both starting lineups were announced" in tl:
        return "Both starting lineups are posted, reducing pregame uncertainty around batting-order context."
    return f"Lineup status: {t}"


def _lineup_change_impact_note(text):
    t = (text or "").strip()
    if not t or t.lower() in ("n/a", "unavailable"):
        return ""
    if "unavailable" in t.lower():
        return f"Lineup trend context: {t}"
    return f"Lineup-change trend: {t}"


def _polish_commentary(text):
    t = (text or "").strip()
    if not t:
        return ""

    # Normalize spacing/punctuation artifacts from generated prose.
    t = re.sub(r'\s+', ' ', t)
    t = t.replace('..', '.')
    t = t.replace(' .', '.')
    t = t.replace(' ;', ';')

    # Soft cleanup of repetitive boilerplate phrasing.
    t = t.replace('Lineup status check:', 'Lineup status:')
    t = t.replace('market context, and market movement', 'market context and line movement')

    # Remove immediate duplicate sentences if any slipped in.
    parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+', t) if p.strip()]
    deduped = []
    seen = set()
    for p in parts:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)
    return ' '.join(deduped)


def _parse_markdown(md_text: str):
    lines = md_text.splitlines()
    date_str = ""
    model = "dutch"
    picks = []
    current = None
    in_commentary = False
    commentary_lines = []

    for line in lines:
        if line.startswith('# MLB Picks Commentary — '):
            date_str = line.split('—', 1)[1].strip()
            continue

        if line.startswith('- Model: '):
            m = re.search(r'`([^`]+)`', line)
            model = m.group(1) if m else line.split(':', 1)[1].strip()
            continue

        if line.startswith('## '):
            if current and commentary_lines:
                current['commentary'] = '\n'.join(commentary_lines).strip()
                commentary_lines = []
            title = line[3:].strip()
            m = re.match(r'\d+\)\s+(.*?)\s+over\s+(.*)$', title)
            if not m:
                # Non-pick markdown section (e.g., AI summary heading)
                in_commentary = False
                continue
            if current:
                picks.append(current)
            current = {
                'winner': m.group(1).strip() if m else title,
                'loser': m.group(2).strip() if m else '',
                'fields': {},
                'commentary': '',
            }
            in_commentary = False
            continue

        if current:
            if line.strip() == '**Commentary**':
                in_commentary = True
                commentary_lines = []
                continue

            if in_commentary:
                commentary_lines.append(line)
                continue

            # markdown format currently: - **Pick Odds:** -109
            m1 = re.match(r'^- \*\*(.+?):\*\*\s*(.*)$', line)
            if m1:
                current['fields'][m1.group(1).strip()] = m1.group(2).strip()
                continue

            # fallback format: - **Pick Odds**: -109
            m2 = re.match(r'^- \*\*(.+?)\*\*:\s*(.*)$', line)
            if m2:
                current['fields'][m2.group(1).strip()] = m2.group(2).strip()
                continue

    if current:
        if commentary_lines:
            current['commentary'] = '\n'.join(commentary_lines).strip()
        picks.append(current)

    return {
        'date': date_str,
        'model': model,
        'picks': picks,
    }


def _field(pick, key, default='n/a'):
    fields = pick.get('fields') if isinstance(pick, dict) else None
    if isinstance(fields, dict):
        return fields.get(key, default)
    # Some derived rows (e.g., run totals) store display keys at top-level.
    if isinstance(pick, dict):
        return pick.get(key, default)
    return default


def _massage_commentary_with_llm(commentary_text, pick, date_text=''):
    text = (commentary_text or '').strip()
    if not text:
        return text
    if os.environ.get('ENABLE_COMMENTARY_MASSAGE', 'false').strip().lower() not in ('1', 'true', 'yes', 'on'):
        return text
    if not os.environ.get('OPENAI_API_KEY') and not os.environ.get('OPENROUTER_API_KEY'):
        return text

    try:
        from connector.llm import massage_commentary

        context = {
            'date': date_text,
            'winner': pick.get('winner', ''),
            'loser': pick.get('loser', ''),
            'odds': _field(pick, 'Pick Odds', '----'),
            'confidence': _field(pick, 'Model Confidence', 'n/a'),
            'pitching_matchup': _field(pick, 'Pitching Matchup', 'n/a'),
            'venue': _field(pick, 'Venue', 'n/a'),
            'weather': _field(pick, 'Weather', 'n/a'),
            'umpire': _field(pick, 'Umpire Crew', 'n/a'),
            'line_movement': _field(pick, 'Line Movement', 'n/a'),
            'starting_lineups': _field(pick, 'Starting Lineups', 'n/a'),
            'lineup_change_impact': _field(pick, 'Lineup Change Impact', 'n/a'),
        }
        improved = massage_commentary(text, context)
        if improved and str(improved).strip():
            return str(improved).strip()
    except Exception as e:
        print(f'Commentary massage failed, using source text: {e}')

    return text


def _pick_commentary_text(pick, idx, date_text=''):
    base = (pick.get('commentary') or '').strip()
    if not base:
        base = _analysis_paragraph(pick, idx, date_text)
    base = _massage_commentary_with_llm(base, pick, date_text)
    return _polish_commentary(base)


def _odds_value(odds_text: str):
    if not odds_text:
        return None
    t = str(odds_text).strip()
    if t in ('----', 'n/a', 'N/A'):
        return None
    try:
        return int(t)
    except Exception:
        m = re.search(r'([+-]?\d+)', t)
        if not m:
            return None


def _safe_int(v):
    try:
        return int(v)
    except Exception:
        return None


def _build_matchup_games(game_date: str):
    games = statsapi.schedule(start_date=game_date, end_date=game_date)
    matchups = {}
    for g in games:
        home = g.get('home_name')
        away = g.get('away_name')
        if not home or not away:
            continue
        key = tuple(sorted([home, away]))

        home_score = _safe_int(g.get('home_score'))
        away_score = _safe_int(g.get('away_score'))
        status = str(g.get('status', ''))
        is_final = 'final' in status.lower()

        winner = g.get('winning_team')
        if not winner and is_final and home_score is not None and away_score is not None:
            winner = home if home_score > away_score else away

        matchups.setdefault(key, []).append({
            'status': status,
            'is_final': is_final,
            'winner': winner,
            'game_datetime': g.get('game_datetime') or '',
            'home': home,
            'away': away,
            'home_score': home_score,
            'away_score': away_score,
        })

    # keep deterministic order for doubleheaders
    for key in matchups:
        matchups[key].sort(key=lambda x: x.get('game_datetime', ''))

    return matchups


def _evaluate_picks(parsed):
    matchups = _build_matchup_games(parsed['date'])
    seen_idx = {}
    evaluated = []

    for p in parsed['picks']:
        winner = p['winner']
        loser = p['loser']
        key = tuple(sorted([winner, loser]))
        idx = seen_idx.get(key, 0)
        seen_idx[key] = idx + 1

        games = matchups.get(key, [])
        game = games[idx] if idx < len(games) else None

        result = 'PENDING'
        status = 'Not found'
        actual_winner = None

        if game:
            status = game.get('status', 'Unknown')
            actual_winner = game.get('winner')
            if game.get('is_final') and actual_winner:
                result = 'WIN' if actual_winner == winner else 'LOSS'
            elif game.get('is_final') and not actual_winner:
                result = 'UNKNOWN'

        ev = dict(p)
        ev['result'] = result
        ev['game_status'] = status
        ev['actual_winner'] = actual_winner
        ev['_game'] = game
        evaluated.append(ev)

    decided = [x for x in evaluated if x['result'] in ('WIN', 'LOSS')]
    wins = len([x for x in decided if x['result'] == 'WIN'])
    losses = len([x for x in decided if x['result'] == 'LOSS'])
    pending = len([x for x in evaluated if x['result'] == 'PENDING'])

    plus = [x for x in evaluated if (_odds_value(_field(x, 'Pick Odds', '')) or -99999) > 0]
    plus_decided = [x for x in plus if x['result'] in ('WIN', 'LOSS')]
    plus_wins = len([x for x in plus_decided if x['result'] == 'WIN'])
    plus_losses = len([x for x in plus_decided if x['result'] == 'LOSS'])

    stake = 100.0

    def _profit_for_pick(p):
        result = p.get('result')
        if result not in ('WIN', 'LOSS'):
            return 0.0
        odds = _odds_value(_field(p, 'Pick Odds', ''))
        if odds is None:
            return 0.0 if result == 'WIN' else -stake
        if result == 'LOSS':
            return -stake
        if odds > 0:
            return stake * (odds / 100.0)
        if odds < 0:
            return stake * (100.0 / abs(odds))
        return 0.0

    def _segment_stats(segment_picks):
        seg_decided = [x for x in segment_picks if x.get('result') in ('WIN', 'LOSS')]
        seg_wins = len([x for x in seg_decided if x.get('result') == 'WIN'])
        seg_losses = len([x for x in seg_decided if x.get('result') == 'LOSS'])
        seg_profit = round(sum(_profit_for_pick(x) for x in seg_decided), 2)
        seg_roi = round((seg_profit / (len(seg_decided) * stake)) * 100, 2) if seg_decided else None
        return {
            'total': len(segment_picks),
            'decided': len(seg_decided),
            'wins': seg_wins,
            'losses': seg_losses,
            'profit': seg_profit,
            'roi_pct': seg_roi,
            'stake_per_pick': stake,
        }

    by_conf = sorted(
        evaluated,
        key=lambda p: _parse_confidence(_field(p, 'Model Confidence', '')) or -1,
        reverse=True,
    )
    best_conf = by_conf[:1]
    top3_conf = by_conf[:3]

    run_totals = []
    for ev in evaluated:
        lean = _run_total_lean(ev)
        if not lean:
            continue

        game = ev.get('_game') or {}
        home_score = game.get('home_score')
        away_score = game.get('away_score')
        is_final = bool(game.get('is_final'))

        chosen_odds = lean['over_odds'] if lean['pick'] == 'OVER' else lean['under_odds']
        rt = {
            'winner': ev.get('winner'),
            'loser': ev.get('loser'),
            'pick': lean['pick'],
            'line': lean['line'],
            'Pick Odds': str(chosen_odds) if chosen_odds is not None else '----',
            'result': 'PENDING',
            'actual_total_side': None,
            'game_total_runs': None,
        }

        if is_final and home_score is not None and away_score is not None:
            total_runs = int(home_score) + int(away_score)
            rt['game_total_runs'] = total_runs
            if total_runs > float(lean['line']):
                actual_side = 'OVER'
            elif total_runs < float(lean['line']):
                actual_side = 'UNDER'
            else:
                actual_side = 'PUSH'
            rt['actual_total_side'] = actual_side

            if actual_side == 'PUSH':
                rt['result'] = 'UNKNOWN'
            else:
                rt['result'] = 'WIN' if actual_side == lean['pick'] else 'LOSS'

        run_totals.append(rt)

    segments = {
        'all_picks': _segment_stats(evaluated),
        'best_confidence_pick': _segment_stats(best_conf),
        'top3_confidence_picks': _segment_stats(top3_conf),
        'plus_money_picks': _segment_stats(plus),
        'run_total_picks': _segment_stats(run_totals),
    }

    summary = {
        'date': parsed['date'],
        'total_picks': len(evaluated),
        'decided': len(decided),
        'wins': wins,
        'losses': losses,
        'pending': pending,
        'win_rate': round((wins / len(decided)) * 100, 1) if decided else None,
        'plus_money_total': len(plus),
        'plus_money_decided': len(plus_decided),
        'plus_money_wins': plus_wins,
        'plus_money_losses': plus_losses,
        'plus_money_win_rate': round((plus_wins / len(plus_decided)) * 100, 1) if plus_decided else None,
        'segments': segments,
    }

    return evaluated, summary


def _render_tracker_block(summary):
    wr = f"{summary['win_rate']}%" if summary['win_rate'] is not None else "—"
    pwr = f"{summary['plus_money_win_rate']}%" if summary['plus_money_win_rate'] is not None else "—"
    return f'''
    <section class="tracker">
      <div class="tracker-grid">
        <div class="tcard"><span>Total Picks</span><strong>{summary['total_picks']}</strong></div>
        <div class="tcard"><span>Decided</span><strong>{summary['decided']}</strong></div>
        <div class="tcard"><span>Record</span><strong>{summary['wins']}-{summary['losses']}</strong></div>
        <div class="tcard"><span>Win Rate</span><strong>{wr}</strong></div>
        <div class="tcard"><span>Plus Money Record</span><strong>{summary['plus_money_wins']}-{summary['plus_money_losses']}</strong></div>
        <div class="tcard"><span>Plus Money Win %</span><strong>{pwr}</strong></div>
      </div>
    </section>
    '''


def _analysis_paragraph(pick, idx, date_text=''):
    winner, loser = pick['winner'], pick['loser']
    conf_text = _field(pick, 'Model Confidence', 'n/a')
    conf = _parse_confidence(conf_text)
    dp = _parse_data_points(conf_text)
    dp_text = f"{dp[0]}/{dp[1]}" if dp else "n/a"
    bucket = _confidence_bucket(conf)

    odds = _field(pick, 'Pick Odds', '----')
    pitching = _field(pick, 'Pitching Matchup', 'n/a')
    venue = _field(pick, 'Venue', 'n/a')
    weather = _field(pick, 'Weather', 'n/a')
    ump = _field(pick, 'Umpire Crew', 'n/a')
    line_move = _field(pick, 'Line Movement', 'n/a')
    w_sig = _field(pick, f'{winner} Model Signals', 'n/a')
    l_sig = _field(pick, f'{loser} Model Signals', 'n/a')
    w_sig_count = 0 if not w_sig or w_sig == 'n/a' else len([s for s in w_sig.split(',') if s.strip()])
    l_sig_count = 0 if not l_sig or l_sig == 'n/a' else len([s for s in l_sig.split(',') if s.strip()])
    w_inj = _field(pick, f'{winner} Injuries', 'n/a')
    l_inj = _field(pick, f'{loser} Injuries', 'n/a')
    lineups = _field(pick, 'Starting Lineups', 'n/a')
    lineup_impact = _field(pick, 'Lineup Change Impact', 'n/a')

    analyst = _pick_analyst(pick, idx, date_text)

    lead = (
        f"{winner} over {loser} grades as a {bucket} spot at {odds}. "
        f"Confidence is {conf_text} with a {dp_text} split, pitching context is {pitching}, "
        f"and signal balance leans {w_sig_count} to {l_sig_count}."
    )

    return (
        f"{analyst['name']} ({analyst['title']}) — {lead} "
        f"Voice: {analyst['voice']}. "
        f"{_weather_note(venue, weather)} "
        f"{_umpire_note(ump)} "
        f"{_lineup_status_note(lineups)} "
        f"{_lineup_change_impact_note(lineup_impact)} "
        f"{_injury_note(winner, loser, w_inj, l_inj)} "
        f"{_line_movement_note(line_move)}"
    )


def _is_game_started_or_done(pick):
    # Freeze commentary once game is no longer pre-game/scheduled.
    result = str(pick.get('result', '')).upper()
    if result in ('WIN', 'LOSS', 'UNKNOWN'):
        return True

    status = str(pick.get('game_status', '')).lower()
    if not status:
        return False

    pregame_tokens = ('scheduled', 'pre-game', 'preview')
    return not any(tok in status for tok in pregame_tokens)


def _result_badge(pick, result):
    rr = str(result or 'PENDING').upper()
    if rr == 'PENDING' and _is_game_started_or_done(pick):
        return 'In Progress', 'res-inprogress'
    if rr == 'WIN':
        return 'WIN', 'res-win'
    if rr == 'LOSS':
        return 'LOSS', 'res-loss'
    if rr == 'UNKNOWN':
        return 'UNKNOWN', 'res-pending'
    return 'PENDING', 'res-pending'


def _extract_existing_commentary_map(html_path: Path):
    if not html_path.exists():
        return {}
    try:
        text = html_path.read_text()
    except Exception:
        return {}

    out = {}
    pattern = re.compile(r'<h2>\s*(.*?)\s+over\s+(.*?)\s*</h2>.*?<p class="lede">(.*?)</p>', re.S)
    for m in pattern.finditer(text):
        winner = html.unescape(re.sub(r'<[^>]+>', '', m.group(1)).strip())
        loser = html.unescape(re.sub(r'<[^>]+>', '', m.group(2)).strip())
        commentary = html.unescape(re.sub(r'<[^>]+>', '', m.group(3)).strip())
        if winner and loser and commentary:
            out[f"{winner}|||{loser}"] = commentary
    return out


def _extract_existing_odds_map(html_path: Path):
    if not html_path.exists():
        return {}
    try:
        text = html_path.read_text()
    except Exception:
        return {}

    out = {}
    pattern = re.compile(
        r'<h2>\s*(.*?)\s+over\s+(.*?)\s*</h2>.*?<div><span>Odds</span><strong>(.*?)</strong></div>',
        re.S,
    )
    for m in pattern.finditer(text):
        winner = html.unescape(re.sub(r'<[^>]+>', '', m.group(1)).strip())
        loser = html.unescape(re.sub(r'<[^>]+>', '', m.group(2)).strip())
        odds = html.unescape(re.sub(r'<[^>]+>', '', m.group(3)).strip())
        if winner and loser and odds:
            out[f"{winner}|||{loser}"] = odds
    return out


def _render_daily_html(parsed, evaluated_picks=None, summary=None, frozen_commentary=None, latest_date=None, archive_dates=None):
    picks_source = evaluated_picks if evaluated_picks is not None else parsed['picks']
    picks = sorted(
        picks_source,
        key=lambda p: _parse_confidence(_field(p, 'Model Confidence', '')) or -1,
        reverse=True,
    )
    date_str = parsed['date']
    latest_date = latest_date or date_str
    archive_dates = archive_dates or [date_str]
    toolbar_html = _render_global_toolbar(latest_date, archive_dates)
    model = parsed['model']
    now = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    frozen_commentary = frozen_commentary or {}
    cards = []
    for i, p in enumerate(picks, 1):
        winner, loser = p['winner'], p['loser']
        result_label, result_class = _result_badge(p, p.get('result', 'PENDING'))
        key = f"{winner}|||{loser}"
        if _is_game_started_or_done(p) and key in frozen_commentary:
            analysis = frozen_commentary[key]
        else:
            analysis = _pick_commentary_text(p, i, date_str)

        cards.append(f'''
      <article class="pick-card">
        <div class="pick-head">
          <div class="pick-num">Pick {i}</div>
          <h2>{html.escape(winner)} over {html.escape(loser)}</h2>
          <span class="res {result_class}">{result_label}</span>
        </div>
        <div class="seo-line">{html.escape(winner)} vs {html.escape(loser)} prediction — {html.escape(date_str)}</div>
        <div class="meta-grid">
          <div><span>Odds</span><strong>{html.escape(_field(p,'Pick Odds','----'))}</strong></div>
          <div><span>Confidence</span><strong>{html.escape(_field(p,'Model Confidence','n/a'))}</strong></div>
          <div><span>Pitching</span><strong>{html.escape(_field(p,'Pitching Matchup','n/a'))}</strong></div>
          <div><span>Venue</span><strong>{html.escape(_field(p,'Venue','n/a'))}</strong></div>
        </div>
        <p class="lede">{analysis}</p>
        <details>
          <summary>Expanded game context</summary>
          <ul>
            <li><strong>Weather:</strong> {html.escape(_field(p,'Weather','n/a'))}</li>
            <li><strong>Umpire Crew:</strong> {html.escape(_field(p,'Umpire Crew','n/a'))}</li>
            <li><strong>{html.escape(winner)} Injuries:</strong> {html.escape(_field(p,f'{winner} Injuries','n/a'))}</li>
            <li><strong>{html.escape(loser)} Injuries:</strong> {html.escape(_field(p,f'{loser} Injuries','n/a'))}</li>
            <li><strong>Starting Lineups:</strong> {html.escape(_field(p,'Starting Lineups','n/a'))}</li>
            <li><strong>Lineup Change Impact:</strong> {html.escape(_field(p,'Lineup Change Impact','n/a'))}</li>
            <li><strong>Line Movement:</strong> {html.escape(_field(p,'Line Movement','n/a'))}</li>
          </ul>
        </details>
      </article>
    ''')

    tracker_html = _render_tracker_block(summary) if summary else ''

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http://www.w3.org/2000/svg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Ctext%20y%3D%22.9em%22%20font-size%3D%2290%22%3E%E2%9A%BE%3C/text%3E%3C/svg%3E" />
  <title>SportzBallz | MLB Predictions {html.escape(date_str)} (Team vs Team)</title>
  <meta name="description" content="MLB team vs team predictions for {html.escape(date_str)} from SportzBallz, including confidence, odds, and matchup context." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/' + date_str + '.html')}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="SportzBallz" />
  <meta property="og:title" content="SportzBallz MLB Predictions — {html.escape(date_str)}" />
  <meta property="og:description" content="Team vs team predictions for {html.escape(date_str)} with confidence, pricing context, plus-money and run-total analysis." />
  <meta property="og:url" content="{_site_url('/' + date_str + '.html')}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="SportzBallz MLB Predictions — {html.escape(date_str)}" />
  <meta name="twitter:description" content="Team vs team predictions for {html.escape(date_str)} with confidence, pricing context, plus-money and run-total analysis." />
  <style>
    :root {{ --bg:#0a1020; --panel:#101a33; --ink:#eaf0ff; --muted:#a7b7df; --line:#273a6b; --accent:#5cc9ff; --accent2:#88f2c7; }}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:Inter,system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:linear-gradient(180deg, #0b1220 0%, #0a1020 100%);color:var(--ink);line-height:1.65}}
    .wrap{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}}
    header{{background:linear-gradient(135deg, rgba(92,201,255,.18), rgba(136,242,199,.09));border:1px solid var(--line);border-radius:16px;padding:22px;margin-bottom:16px}}
    .kicker{{font:600 12px/1.2 Inter,system-ui,sans-serif;letter-spacing:.12em;color:var(--muted);text-transform:uppercase}}
    h1{{margin:8px 0 10px;font-size:clamp(30px,5vw,46px);line-height:1.05}}
    .sub{{color:var(--muted);font-family:Inter,system-ui,sans-serif;font-size:14px}}
    .header-row{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}}
    .reload-btn{{display:inline-block;border:1px solid #4c6db0;background:#10203b;color:#dff2ff;border-radius:10px;padding:8px 12px;font:600 12px Inter,system-ui,sans-serif;cursor:pointer;text-decoration:none}}
    .ad-slot{{background:rgba(255,255,255,.03);border:1px dashed #3b5a96;border-radius:12px;padding:12px 14px;margin:0 0 14px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    .ad-label{{font:700 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:#9cc4ff}}
    .ad-copy{{color:#d9e6ff;font:500 14px/1.3 Inter,system-ui,sans-serif}}
    .ad-cta{{display:inline-block;padding:7px 10px;border-radius:8px;border:1px solid #4c6db0;color:#dff2ff;text-decoration:none;font:600 12px Inter,system-ui,sans-serif}}
    {_toolbar_css()}
    .pick-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:0 0 14px 0;box-shadow:0 8px 22px rgba(2,8,24,.32)}}
    .pick-head h2{{margin:4px 0 8px;font-size:27px;line-height:1.15}}
    .seo-line{{font:600 12px/1.3 Inter,system-ui,sans-serif;color:#a9c6ff;letter-spacing:.02em;margin-top:2px}}
    .pick-head{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
    .pick-num{{font:600 12px/1 Inter,system-ui,sans-serif;color:var(--accent);letter-spacing:.12em;text-transform:uppercase}}
    .res{{font:700 11px/1 Inter,system-ui,sans-serif;padding:5px 8px;border-radius:999px;border:1px solid #31508e;}}
    .res-win{{color:#7CFFB3;border-color:#2f8f57;background:rgba(52,211,153,.12)}}
    .res-loss{{color:#ff9ca0;border-color:#a13d47;background:rgba(239,68,68,.14)}}
    .res-pending{{color:#cfe1ff;border-color:#3c5c97;background:rgba(59,130,246,.12)}}
    .res-inprogress{{color:#fde68a;border-color:#f59e0b;background:rgba(245,158,11,.18)}}
    .tracker{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin-bottom:16px}}
    .tracker-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}
    .tcard{{border:1px dashed #31508e;border-radius:10px;padding:8px 10px;background:rgba(255,255,255,.02)}}
    .tcard span{{display:block;color:var(--muted);font:600 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}}
    .tcard strong{{font:700 16px/1.25 Inter,system-ui,sans-serif;color:#e7f0ff}}
    .meta-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px 12px;padding:10px 0 2px}}
    .meta-grid div{{border:1px dashed #31508e;border-radius:10px;padding:8px 10px;background:rgba(255,255,255,.02)}}
    .meta-grid span{{display:block;color:var(--muted);font:600 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px}}
    .meta-grid strong{{font:600 15px/1.35 Inter,system-ui,sans-serif;color:#dce8ff}}
    .lede{{font-size:18px;line-height:1.55;margin:12px 0 8px;color:#f2f6ff}}
    details{{margin-top:8px;border-top:1px solid #264377;padding-top:8px}}
    summary{{cursor:pointer;font:600 14px Inter,system-ui,sans-serif;color:var(--accent)}}
    ul{{margin:10px 0 0 18px;padding:0}}
    li{{margin:6px 0}}
    footer{{margin-top:10px;color:var(--muted);font:12px Inter,system-ui,sans-serif;text-align:right}}
    @media (max-width:720px){{.lede{{font-size:18px}} .pick-head h2{{font-size:24px}}}}
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <div class="header-row">
        <div>
          <div class="kicker">SportzBallz Daily Desk</div>
          <h1>MLB Daily Notebook — {html.escape(date_str)}</h1>
          <div class="sub">Model: {html.escape(model)} • Updated {html.escape(now)}</div>
        </div>
        <a class="reload-btn" href="" data-reload="1">Reload</a>
      </div>
    </header>
    {toolbar_html}
    {_render_ad_slot('daily-top', 'Daily Notebook Sponsorship')}
    {tracker_html}
    {''.join(cards)}
    <footer>Published by SportzBallz.io</footer>
  </main>
  {_embed_mode_script()}
  {_hit_counter_script()}
</body>
</html>
'''


def _render_plus_money_html(parsed, evaluated_picks=None, summary=None, frozen_commentary=None, latest_date=None, archive_dates=None):
    source = evaluated_picks if evaluated_picks is not None else parsed['picks']
    all_picks = sorted(
        source,
        key=lambda p: _parse_confidence(_field(p, 'Model Confidence', '')) or -1,
        reverse=True,
    )
    plus_picks = []
    for p in all_picks:
        ov = _odds_value(_field(p, 'Pick Odds', ''))
        if ov is not None and ov > 0:
            plus_picks.append(p)

    date_str = parsed['date']
    latest_date = latest_date or date_str
    archive_dates = archive_dates or [date_str]
    toolbar_html = _render_global_toolbar(latest_date, archive_dates)
    model = parsed['model']
    now = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    frozen_commentary = frozen_commentary or {}
    cards = []
    for i, p in enumerate(plus_picks, 1):
        winner, loser = p['winner'], p['loser']
        result_label, result_class = _result_badge(p, p.get('result', 'PENDING'))
        key = f"{winner}|||{loser}"
        if _is_game_started_or_done(p) and key in frozen_commentary:
            analysis = frozen_commentary[key]
        else:
            analysis = _pick_commentary_text(p, i, date_str)

        cards.append(f'''
      <article class="pick-card">
        <div class="pick-head">
          <div class="pick-num">Underdog {i}</div>
          <h2>{html.escape(winner)} over {html.escape(loser)}</h2>
          <span class="res {result_class}">{result_label}</span>
        </div>
        <div class="seo-line">{html.escape(winner)} vs {html.escape(loser)} prediction — {html.escape(date_str)}</div>
        <div class="meta-grid">
          <div><span>Odds</span><strong>{html.escape(_field(p,'Pick Odds','----'))}</strong></div>
          <div><span>Confidence</span><strong>{html.escape(_field(p,'Model Confidence','n/a'))}</strong></div>
          <div><span>Pitching</span><strong>{html.escape(_field(p,'Pitching Matchup','n/a'))}</strong></div>
          <div><span>Venue</span><strong>{html.escape(_field(p,'Venue','n/a'))}</strong></div>
        </div>
        <p class="lede">{analysis}</p>
        <details>
          <summary>Expanded game context</summary>
          <ul>
            <li><strong>Weather:</strong> {html.escape(_field(p,'Weather','n/a'))}</li>
            <li><strong>Umpire Crew:</strong> {html.escape(_field(p,'Umpire Crew','n/a'))}</li>
            <li><strong>{html.escape(winner)} Injuries:</strong> {html.escape(_field(p,f'{winner} Injuries','n/a'))}</li>
            <li><strong>{html.escape(loser)} Injuries:</strong> {html.escape(_field(p,f'{loser} Injuries','n/a'))}</li>
            <li><strong>Starting Lineups:</strong> {html.escape(_field(p,'Starting Lineups','n/a'))}</li>
            <li><strong>Lineup Change Impact:</strong> {html.escape(_field(p,'Lineup Change Impact','n/a'))}</li>
            <li><strong>Line Movement:</strong> {html.escape(_field(p,'Line Movement','n/a'))}</li>
          </ul>
        </details>
      </article>
    ''')

    if not cards:
        cards.append(
            '<article class="pick-card"><h2>No Plus Money Picks Today</h2><p class="lede">No underdog selections met publication criteria for this slate.</p></article>'
        )

    pm_summary_html = ''
    if summary:
        pwr = f"{summary['plus_money_win_rate']}%" if summary['plus_money_win_rate'] is not None else "—"
        pm_summary_html = f'''
        <section class="tracker">
          <div class="tracker-grid">
            <div class="tcard"><span>Plus Money Picks</span><strong>{summary['plus_money_total']}</strong></div>
            <div class="tcard"><span>Decided</span><strong>{summary['plus_money_decided']}</strong></div>
            <div class="tcard"><span>Record</span><strong>{summary['plus_money_wins']}-{summary['plus_money_losses']}</strong></div>
            <div class="tcard"><span>Win Rate</span><strong>{pwr}</strong></div>
          </div>
        </section>
        '''

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http://www.w3.org/2000/svg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Ctext%20y%3D%22.9em%22%20font-size%3D%2290%22%3E%E2%9A%BE%3C/text%3E%3C/svg%3E" />
  <title>SportzBallz | Plus Money Picks</title>
  <meta name="description" content="SportzBallz underdog MLB picks for {html.escape(date_str)}." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/' + date_str + '-plus-money.html')}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="SportzBallz" />
  <meta property="og:title" content="SportzBallz Plus Money Picks — {html.escape(date_str)}" />
  <meta property="og:description" content="Underdog-only MLB picks with confidence and matchup context." />
  <meta property="og:url" content="{_site_url('/' + date_str + '-plus-money.html')}" />
  <meta name="twitter:card" content="summary_large_image" />
  <style>
    :root {{ --bg:#0a1020; --panel:#101a33; --ink:#eaf0ff; --muted:#a7b7df; --line:#273a6b; --accent:#5cc9ff; --accent2:#88f2c7; --plus:#22c55e; }}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:Inter,system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:linear-gradient(180deg, #0b1220 0%, #0a1020 100%);color:var(--ink);line-height:1.65}}
    .wrap{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}}
    header{{background:linear-gradient(135deg, rgba(34,197,94,.20), rgba(92,201,255,.10));border:1px solid var(--line);border-radius:16px;padding:22px;margin-bottom:16px}}
    .kicker{{font:600 12px/1.2 Inter,system-ui,sans-serif;letter-spacing:.12em;color:var(--muted);text-transform:uppercase}}
    h1{{margin:8px 0 10px;font-size:clamp(30px,5vw,46px);line-height:1.05}}
    .sub{{color:var(--muted);font-family:Inter,system-ui,sans-serif;font-size:14px}}
    .header-row{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}}
    .reload-btn{{display:inline-block;border:1px solid #4c6db0;background:#10203b;color:#dff2ff;border-radius:10px;padding:8px 12px;font:600 12px Inter,system-ui,sans-serif;cursor:pointer;text-decoration:none}}
    .ad-slot{{background:rgba(255,255,255,.03);border:1px dashed #3b5a96;border-radius:12px;padding:12px 14px;margin:0 0 14px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    .ad-label{{font:700 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:#9cc4ff}}
    .ad-copy{{color:#d9e6ff;font:500 14px/1.3 Inter,system-ui,sans-serif}}
    .ad-cta{{display:inline-block;padding:7px 10px;border-radius:8px;border:1px solid #4c6db0;color:#dff2ff;text-decoration:none;font:600 12px Inter,system-ui,sans-serif}}
    .pick-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:0 0 14px 0;box-shadow:0 8px 22px rgba(2,8,24,.32)}}
    .pick-head h2{{margin:4px 0 8px;font-size:27px;line-height:1.15}}
    .seo-line{{font:600 12px/1.3 Inter,system-ui,sans-serif;color:#a9c6ff;letter-spacing:.02em;margin-top:2px}}
    .pick-head{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
    {_toolbar_css()}
    .pick-num{{font:600 12px/1 Inter,system-ui,sans-serif;color:var(--plus);letter-spacing:.12em;text-transform:uppercase}}
    .res{{font:700 11px/1 Inter,system-ui,sans-serif;padding:5px 8px;border-radius:999px;border:1px solid #31508e;}}
    .res-win{{color:#7CFFB3;border-color:#2f8f57;background:rgba(52,211,153,.12)}}
    .res-loss{{color:#ff9ca0;border-color:#a13d47;background:rgba(239,68,68,.14)}}
    .res-pending{{color:#cfe1ff;border-color:#3c5c97;background:rgba(59,130,246,.12)}}
    .res-inprogress{{color:#fde68a;border-color:#f59e0b;background:rgba(245,158,11,.18)}}
    .tracker{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin-bottom:16px}}
    .tracker-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}
    .tcard{{border:1px dashed #31508e;border-radius:10px;padding:8px 10px;background:rgba(255,255,255,.02)}}
    .tcard span{{display:block;color:var(--muted);font:600 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}}
    .tcard strong{{font:700 16px/1.25 Inter,system-ui,sans-serif;color:#e7f0ff}}
    .meta-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px 12px;padding:10px 0 2px}}
    .meta-grid div{{border:1px dashed #31508e;border-radius:10px;padding:8px 10px;background:rgba(255,255,255,.02)}}
    .meta-grid span{{display:block;color:var(--muted);font:600 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px}}
    .meta-grid strong{{font:600 15px/1.35 Inter,system-ui,sans-serif;color:#dce8ff}}
    .lede{{font-size:18px;line-height:1.55;margin:12px 0 8px;color:#f2f6ff}}
    details{{margin-top:8px;border-top:1px solid #264377;padding-top:8px}}
    summary{{cursor:pointer;font:600 14px Inter,system-ui,sans-serif;color:var(--accent)}}
    ul{{margin:10px 0 0 18px;padding:0}}
    li{{margin:6px 0}}
    footer{{margin-top:10px;color:var(--muted);font:12px Inter,system-ui,sans-serif;text-align:right}}
    @media (max-width:720px){{.lede{{font-size:18px}} .pick-head h2{{font-size:24px}}}}
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <div class="header-row">
        <div>
          <div class="kicker">SportzBallz Plus Money Desk</div>
          <h1>Plus Money Picks — {html.escape(date_str)}</h1>
          <div class="sub">Model: {html.escape(model)} • Updated {html.escape(now)}</div>
        </div>
        <a class="reload-btn" href="" data-reload="1">Reload</a>
      </div>
    </header>
    {toolbar_html}
    {_render_ad_slot('plus-money-top', 'Plus Money Card Sponsorship')}
    {pm_summary_html}
    {''.join(cards)}
    <footer>Published by SportzBallz.io</footer>
  </main>
  {_embed_mode_script()}
  {_hit_counter_script()}
</body>
</html>
'''


def _render_run_totals_html(parsed, evaluated_picks=None, latest_date=None, archive_dates=None):
    source = evaluated_picks if evaluated_picks is not None else parsed['picks']
    leans = []
    for p in source:
        lean = _run_total_lean(p)
        if lean:
            leans.append((p, lean))

    leans.sort(key=lambda x: x[1]['confidence'], reverse=True)

    date_str = parsed['date']
    latest_date = latest_date or date_str
    archive_dates = archive_dates or [date_str]
    toolbar_html = _render_global_toolbar(latest_date, archive_dates)
    model = parsed['model']
    now = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    cards = []
    for i, (src_pick, l) in enumerate(leans, 1):
        price = l['over_odds'] if l['pick'] == 'OVER' else l['under_odds']
        result_label, result_class = _result_badge(src_pick, _run_total_result_for_pick(src_pick, l))
        cards.append(f'''
      <article class="pick-card">
        <div class="pick-head">
          <div class="pick-num">Run Total {i}</div>
          <h2>{html.escape(l['winner'])} vs {html.escape(l['loser'])} — {l['pick']} {l['line']}</h2>
          <span class="res {result_class}">{result_label}</span>
        </div>
        <div class="meta-grid">
          <div><span>Lean</span><strong>{l['pick']} {l['line']}</strong></div>
          <div><span>Price</span><strong>{price if price is not None else '—'}</strong></div>
          <div><span>Confidence</span><strong>{l['confidence']}</strong></div>
          <div><span>Venue</span><strong>{html.escape(l['venue'])}</strong></div>
        </div>
        <p class="lede">Run-total lens: {l['pick']} {l['line']} in {l['winner']} vs {l['loser']}. Supporting context includes {', '.join(l['reasons']) if l['reasons'] else 'balanced conditions and market context'}.</p>
        <details>
          <summary>Expanded total context</summary>
          <ul>
            <li><strong>Weather:</strong> {html.escape(l['weather'])}</li>
            <li><strong>Total Movement:</strong> {html.escape(l['total_movement'])}</li>
          </ul>
        </details>
      </article>
    ''')

    if not cards:
        cards.append('<article class="pick-card"><h2>No Run Total Leans Today</h2><p class="lede">Total-line data unavailable for today’s slate.</p></article>')

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http://www.w3.org/2000/svg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Ctext%20y%3D%22.9em%22%20font-size%3D%2290%22%3E%E2%9A%BE%3C/text%3E%3C/svg%3E" />
  <title>SportzBallz | Run Total Picks</title>
  <meta name="description" content="SportzBallz MLB run total picks for {html.escape(date_str)}." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/' + date_str + '-run-totals.html')}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="SportzBallz" />
  <meta property="og:title" content="SportzBallz Run Total Picks — {html.escape(date_str)}" />
  <meta property="og:description" content="MLB totals leans built from confidence, pricing, weather and movement context." />
  <meta property="og:url" content="{_site_url('/' + date_str + '-run-totals.html')}" />
  <meta name="twitter:card" content="summary_large_image" />
  <style>
    :root {{ --bg:#0a1020; --panel:#101a33; --ink:#eaf0ff; --muted:#a7b7df; --line:#273a6b; --accent:#f59e0b; --accent2:#5cc9ff; }}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:Inter,system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:linear-gradient(180deg, #0b1220 0%, #0a1020 100%);color:var(--ink);line-height:1.65}}
    .wrap{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}}
    header{{background:linear-gradient(135deg, rgba(245,158,11,.20), rgba(92,201,255,.10));border:1px solid var(--line);border-radius:16px;padding:22px;margin-bottom:16px}}
    .kicker{{font:600 12px/1.2 Inter,system-ui,sans-serif;letter-spacing:.12em;color:var(--muted);text-transform:uppercase}}
    h1{{margin:8px 0 10px;font-size:clamp(30px,5vw,46px);line-height:1.05}}
    .sub{{color:var(--muted);font-family:Inter,system-ui,sans-serif;font-size:14px}}
    .header-row{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}}
    .reload-btn{{display:inline-block;border:1px solid #4c6db0;background:#10203b;color:#dff2ff;border-radius:10px;padding:8px 12px;font:600 12px Inter,system-ui,sans-serif;cursor:pointer;text-decoration:none}}
    .ad-slot{{background:rgba(255,255,255,.03);border:1px dashed #3b5a96;border-radius:12px;padding:12px 14px;margin:0 0 14px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    .ad-label{{font:700 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:#9cc4ff}}
    .ad-copy{{color:#d9e6ff;font:500 14px/1.3 Inter,system-ui,sans-serif}}
    .ad-cta{{display:inline-block;padding:7px 10px;border-radius:8px;border:1px solid #4c6db0;color:#dff2ff;text-decoration:none;font:600 12px Inter,system-ui,sans-serif}}
    .pick-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:0 0 14px 0;box-shadow:0 8px 22px rgba(2,8,24,.32)}}
    .pick-head h2{{margin:4px 0 8px;font-size:27px;line-height:1.15}}
    .seo-line{{font:600 12px/1.3 Inter,system-ui,sans-serif;color:#a9c6ff;letter-spacing:.02em;margin-top:2px}}
    .pick-head{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
    .res{{display:inline-flex;align-items:center;justify-content:center;padding:5px 9px;border-radius:999px;border:1px solid #35518f;font:700 11px/1 Inter,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#dce8ff;background:rgba(255,255,255,.04)}}
    .res-win{{color:#7CFFB3;border-color:#2f8f57;background:rgba(52,211,153,.12)}}
    .res-loss{{color:#ff9ca0;border-color:#a13d47;background:rgba(239,68,68,.14)}}
    .res-pending{{color:#cfe1ff;border-color:#3c5c97;background:rgba(59,130,246,.12)}}
    .res-inprogress{{color:#fde68a;border-color:#f59e0b;background:rgba(245,158,11,.18)}}
    .pick-num{{font:600 12px/1 Inter,system-ui,sans-serif;color:var(--accent);letter-spacing:.12em;text-transform:uppercase}}
    .meta-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px 12px;padding:10px 0 2px}}
    .meta-grid div{{border:1px dashed #31508e;border-radius:10px;padding:8px 10px;background:rgba(255,255,255,.02)}}
    .meta-grid span{{display:block;color:var(--muted);font:600 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px}}
    .meta-grid strong{{font:600 15px/1.35 Inter,system-ui,sans-serif;color:#dce8ff}}
    .lede{{font-size:18px;line-height:1.55;margin:12px 0 8px;color:#f2f6ff}}
    details{{margin-top:8px;border-top:1px solid #264377;padding-top:8px}}
    summary{{cursor:pointer;font:600 14px Inter,system-ui,sans-serif;color:#fbbf24}}
    ul{{margin:10px 0 0 18px;padding:0}}
    li{{margin:6px 0}}
    {_toolbar_css()}
    footer{{margin-top:10px;color:var(--muted);font:12px Inter,system-ui,sans-serif;text-align:right}}
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <div class="header-row">
        <div>
          <div class="kicker">SportzBallz Totals Desk</div>
          <h1>Run Total Picks — {html.escape(date_str)}</h1>
          <div class="sub">Model: {html.escape(model)} • Updated {html.escape(now)}</div>
        </div>
        <a class="reload-btn" href="" data-reload="1">Reload</a>
      </div>
    </header>
    {toolbar_html}
    {_render_ad_slot('run-totals-top', 'Run Totals Sponsorship')}
    {''.join(cards)}
    <footer>Published by SportzBallz.io</footer>
  </main>
  {_embed_mode_script()}
  {_hit_counter_script()}
</body>
</html>
'''


def _render_run_line_html(parsed, evaluated_picks=None, frozen_commentary=None, latest_date=None, archive_dates=None):
    picks_source = evaluated_picks if evaluated_picks is not None else parsed['picks']
    picks = sorted(
        picks_source,
        key=lambda p: _parse_confidence(_field(p, 'Model Confidence', '')) or -1,
        reverse=True,
    )
    date_str = parsed['date']
    latest_date = latest_date or date_str
    archive_dates = archive_dates or [date_str]
    toolbar_html = _render_global_toolbar(latest_date, archive_dates)
    model = parsed['model']
    now = datetime.now().strftime('%Y-%m-%d %I:%M %p')
    frozen_commentary = frozen_commentary or {}

    cards = []
    for i, p in enumerate(picks, 1):
        winner, loser = p['winner'], p['loser']
        result_label, result_class = _result_badge(p, p.get('result', 'PENDING'))

        key = f"{winner}|||{loser}"
        if _is_game_started_or_done(p) and key in frozen_commentary:
            analysis = frozen_commentary[key]
        else:
            analysis = _pick_commentary_text(p, i, date_str)

        cards.append(f'''
      <article class="pick-card">
        <div class="pick-head">
          <div class="pick-num">Run Line {i}</div>
          <h2>{html.escape(winner)} vs {html.escape(loser)} — Run Line Lean</h2>
          <span class="res {result_class}">{result_label}</span>
        </div>
        <div class="seo-line">{html.escape(winner)} vs {html.escape(loser)} run line prediction — {html.escape(date_str)}</div>
        <div class="meta-grid">
          <div><span>Run Line</span><strong>Model lean side: {html.escape(winner)}</strong></div>
          <div><span>Confidence</span><strong>{html.escape(_field(p,'Model Confidence','n/a'))}</strong></div>
          <div><span>Pitching</span><strong>{html.escape(_field(p,'Pitching Matchup','n/a'))}</strong></div>
          <div><span>Venue</span><strong>{html.escape(_field(p,'Venue','n/a'))}</strong></div>
        </div>
        <p class="lede">{analysis}</p>
      </article>
    ''')

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http://www.w3.org/2000/svg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Ctext%20y%3D%22.9em%22%20font-size%3D%2290%22%3E%E2%9A%BE%3C/text%3E%3C/svg%3E" />
  <title>SportzBallz | Run Line Picks {html.escape(date_str)}</title>
  <meta name="description" content="MLB run line predictions for {html.escape(date_str)} from SportzBallz." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/' + date_str + '-run-line.html')}" />
  <style>
    :root {{ --bg:#0a1020; --panel:#101a33; --ink:#eaf0ff; --muted:#a7b7df; --line:#273a6b; --accent:#f97316; }}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:Inter,system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:linear-gradient(180deg, #0b1220 0%, #0a1020 100%);color:var(--ink);line-height:1.65}}
    .wrap{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}}
    header{{background:linear-gradient(135deg, rgba(249,115,22,.20), rgba(92,201,255,.10));border:1px solid var(--line);border-radius:16px;padding:22px;margin-bottom:16px}}
    .kicker{{font:600 12px/1.2 Inter,system-ui,sans-serif;letter-spacing:.12em;color:var(--muted);text-transform:uppercase}}
    h1{{margin:8px 0 10px;font-size:clamp(30px,5vw,46px);line-height:1.05}}
    .sub{{color:var(--muted);font-family:Inter,system-ui,sans-serif;font-size:14px}}
    .header-row{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}}
    .reload-btn{{display:inline-block;border:1px solid #4c6db0;background:#10203b;color:#dff2ff;border-radius:10px;padding:8px 12px;font:600 12px Inter,system-ui,sans-serif;cursor:pointer;text-decoration:none}}
    .pick-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:0 0 14px 0;box-shadow:0 8px 22px rgba(2,8,24,.32)}}
    .pick-head h2{{margin:4px 0 8px;font-size:27px;line-height:1.15}}
    .pick-head{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
    .pick-num{{font:600 12px/1 Inter,system-ui,sans-serif;color:var(--accent);letter-spacing:.12em;text-transform:uppercase}}
    .seo-line{{font:600 12px/1.3 Inter,system-ui,sans-serif;color:#a9c6ff;letter-spacing:.02em;margin-top:2px}}
    .res{{font:700 11px/1 Inter,system-ui,sans-serif;padding:5px 8px;border-radius:999px;border:1px solid #31508e;}}
    .res-win{{color:#7CFFB3;border-color:#2f8f57;background:rgba(52,211,153,.12)}}
    .res-loss{{color:#ff9ca0;border-color:#a13d47;background:rgba(239,68,68,.14)}}
    .res-pending{{color:#cfe1ff;border-color:#3c5c97;background:rgba(59,130,246,.12)}}
    .res-inprogress{{color:#fde68a;border-color:#f59e0b;background:rgba(245,158,11,.18)}}
    .meta-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px 12px;padding:10px 0 2px}}
    .meta-grid div{{border:1px dashed #31508e;border-radius:10px;padding:8px 10px;background:rgba(255,255,255,.02)}}
    .meta-grid span{{display:block;color:var(--muted);font:600 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px}}
    .meta-grid strong{{font:600 15px/1.35 Inter,system-ui,sans-serif;color:#dce8ff}}
    .lede{{font-size:18px;line-height:1.55;margin:12px 0 8px;color:#f2f6ff}}
    {_toolbar_css()}
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <div class="header-row">
        <div>
          <div class="kicker">SportzBallz Run Line Desk</div>
          <h1>Run Line Picks — {html.escape(date_str)}</h1>
          <div class="sub">Model: {html.escape(model)} • Updated {html.escape(now)}</div>
        </div>
        <a class="reload-btn" href="" data-reload="1">Reload</a>
      </div>
    </header>
    {toolbar_html}
    {''.join(cards)}
  </main>
  {_embed_mode_script()}
  {_hit_counter_script()}
</body>
</html>
'''


def _render_top_index(latest_date: str, archive_dates, latest_picks=None, frozen_commentary=None):
    latest_href = f"/{latest_date}.html"
    latest_plus_href = f"/{latest_date}-plus-money.html"
    latest_totals_href = f"/{latest_date}-run-totals.html"
    latest_picks = latest_picks or []
    frozen_commentary = frozen_commentary or {}
    latest_stamp = datetime.now().strftime('%y-%b-%d %I:%M %p')

    archive_groups = []
    archive_toolbar_groups = []
    for i, d in enumerate(sorted(set(archive_dates), reverse=True)):
        latest_pill = ' <span class="pill">Latest</span>' if i == 0 else ''
        archive_groups.append(f'''
          <details class="archive-group">
            <summary>{d}{latest_pill}</summary>
            <div class="archive-links">
              <a href="/{d}.html">Daily Picks</a>
              <a href="/{d}-plus-money.html">Plus Money Picks</a>
              <a href="/{d}-run-totals.html">Run Total Picks</a>
            </div>
          </details>
        ''')
        archive_toolbar_groups.append(f'''
          <details class="archive-group">
            <summary>{d}{latest_pill}</summary>
            <div class="archive-links">
              <a href="/{d}.html">Daily Picks</a>
              <a href="/{d}-plus-money.html">Plus Money Picks</a>
              <a href="/{d}-run-totals.html">Run Total Picks</a>
            </div>
          </details>
        ''')

    latest_sorted = sorted(
        latest_picks,
        key=lambda p: _parse_confidence(_field(p, 'Model Confidence', '')) or -1,
        reverse=True,
    )
    latest_plus = [p for p in latest_sorted if ((_odds_value(_field(p, 'Pick Odds', '')) or -99999) > 0)]
    latest_totals = []
    for p in latest_sorted:
        lean = _run_total_lean(p)
        if lean:
            latest_totals.append((p, lean))
    def _result_badge_for(pick, result):
        return _result_badge(pick, result)

    latest_items = []
    for i, p in enumerate(latest_sorted, 1):
        winner, loser = p.get('winner', 'TBD'), p.get('loser', 'TBD')
        key = f"{winner}|||{loser}"
        if _is_game_started_or_done(p) and key in frozen_commentary:
            analysis = frozen_commentary[key]
        else:
            analysis = _pick_commentary_text(p, i, latest_date)
        result = p.get('result', 'PENDING')
        result_label, result_class = _result_badge_for(p, result)
        latest_items.append(f'''
          <article class="pick-card">
            <div class="pick-head">
              <div class="pick-num">Pick {i}</div>
              <h3>{html.escape(winner)} over {html.escape(loser)}</h3>
              <span class="res {result_class}">{result_label}</span>
            </div>
            <div class="meta-grid">
              <div><span>Odds</span><strong>{html.escape(_field(p,'Pick Odds','----'))}</strong></div>
              <div><span>Confidence</span><strong>{html.escape(_field(p,'Model Confidence','n/a'))}</strong></div>
              <div><span>Pitching</span><strong>{html.escape(_field(p,'Pitching Matchup','n/a'))}</strong></div>
              <div><span>Venue</span><strong>{html.escape(_field(p,'Venue','n/a'))}</strong></div>
            </div>
            <div class="lede-inline">{analysis}</div>
            <details class="pick-details">
              <summary>Expanded game context</summary>
              <ul>
                <li><strong>Weather:</strong> {html.escape(_field(p,'Weather','n/a'))}</li>
                <li><strong>Umpire Crew:</strong> {html.escape(_field(p,'Umpire Crew','n/a'))}</li>
                <li><strong>{html.escape(winner)} Injuries:</strong> {html.escape(_field(p,f'{winner} Injuries','n/a'))}</li>
                <li><strong>{html.escape(loser)} Injuries:</strong> {html.escape(_field(p,f'{loser} Injuries','n/a'))}</li>
                <li><strong>Line Movement:</strong> {html.escape(_field(p,'Line Movement','n/a'))}</li>
              </ul>
            </details>
          </article>
        ''')

    latest_picks_html = ''.join(latest_items) if latest_items else "<p class='meta'>No picks available yet for this date.</p>"

    plus_items = []
    for i, p in enumerate(latest_plus, 1):
        winner, loser = p.get('winner', 'TBD'), p.get('loser', 'TBD')
        key = f"{winner}|||{loser}"
        if _is_game_started_or_done(p) and key in frozen_commentary:
            analysis = frozen_commentary[key]
        else:
            analysis = _pick_commentary_text(p, i, latest_date)
        result = p.get('result', 'PENDING')
        result_label, result_class = _result_badge_for(p, result)
        plus_items.append(f'''
          <article class="pick-card">
            <div class="pick-head">
              <div class="pick-num">Underdog {i}</div>
              <h3>{html.escape(winner)} over {html.escape(loser)}</h3>
              <span class="res {result_class}">{result_label}</span>
            </div>
            <div class="meta-grid">
              <div><span>Odds</span><strong>{html.escape(_field(p,'Pick Odds','----'))}</strong></div>
              <div><span>Confidence</span><strong>{html.escape(_field(p,'Model Confidence','n/a'))}</strong></div>
              <div><span>Pitching</span><strong>{html.escape(_field(p,'Pitching Matchup','n/a'))}</strong></div>
              <div><span>Venue</span><strong>{html.escape(_field(p,'Venue','n/a'))}</strong></div>
            </div>
            <div class="lede-inline">{analysis}</div>
          </article>
        ''')
    latest_plus_html = (
        ''.join(plus_items)
        if plus_items else "<p class='meta'>No plus money picks today.</p>"
    )

    total_items = []
    for i, (p, lean) in enumerate(latest_totals, 1):
        line = lean.get('line')
        side = lean.get('pick')
        price = lean.get('over_odds') if side == 'OVER' else lean.get('under_odds')
        result_label, result_class = _result_badge_for(p, _run_total_result_for_pick(p, lean))
        reasons = ', '.join(lean.get('reasons') or []) or 'balanced conditions and market context'
        rt_analysis = f"Run-total lens: {side} {line} in {p.get('winner','TBD')} vs {p.get('loser','TBD')}. Supporting context includes {reasons}."
        total_items.append(f'''
          <article class="pick-card">
            <div class="pick-head">
              <div class="pick-num">Run Total {i}</div>
              <h3>{html.escape(p.get('winner','TBD'))} vs {html.escape(p.get('loser','TBD'))} — {side} {line}</h3>
              <span class="res {result_class}">{result_label}</span>
            </div>
            <div class="meta-grid">
              <div><span>Lean</span><strong>{side} {line}</strong></div>
              <div><span>Odds</span><strong>{price if price is not None else '—'}</strong></div>
              <div><span>Confidence</span><strong>{lean.get('confidence')}</strong></div>
              <div><span>Venue</span><strong>{html.escape(lean.get('venue') or 'n/a')}</strong></div>
            </div>
            <div class="lede-inline">{rt_analysis}</div>
          </article>
        ''')
    latest_totals_html = (
        ''.join(total_items)
        if total_items else "<p class='meta'>No run total leans available yet.</p>"
    )

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http://www.w3.org/2000/svg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Ctext%20y%3D%22.9em%22%20font-size%3D%2290%22%3E%E2%9A%BE%3C/text%3E%3C/svg%3E" />
  <title>SportzBallz | Daily MLB Picks</title>
  <meta name="description" content="SportzBallz daily MLB picks, commentary, and betting context." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/')}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="SportzBallz" />
  <meta property="og:title" content="SportzBallz | Daily MLB Picks" />
  <meta property="og:description" content="Daily MLB picks plus underdog and run-total cards, with performance dashboard tracking." />
  <meta property="og:url" content="{_site_url('/')}" />
  <meta name="twitter:card" content="summary_large_image" />
  <style>
    :root {{ --bg:#0a1020; --panel:#111a33; --line:#2a3e72; --ink:#ebf1ff; --muted:#9fb2de; --accent:#63d2ff; --accent2:#7cffc7; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; color:var(--ink); background:radial-gradient(1100px 700px at 10% -5%, #1e2f66 0%, transparent 60%), radial-gradient(900px 600px at 95% 0%, #1b355f 0%, transparent 55%), var(--bg); font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif; min-height:100vh; }}
    .wrap {{ max-width:1500px; margin:0 auto; padding:26px 16px 52px; }}
    .hero {{ border:1px solid var(--line); border-radius:18px; padding:28px 24px; background:linear-gradient(135deg, rgba(99,210,255,.14), rgba(124,255,199,.08)); box-shadow:0 22px 45px rgba(0,0,0,.30); text-align:center; }}
    .kicker {{ color:var(--muted); text-transform:uppercase; letter-spacing:.12em; font-size:12px; margin-bottom:10px; font-weight:700; }}
    .logo {{ margin:0; line-height:1; font-size:clamp(52px, 11vw, 120px); font-weight:900; letter-spacing:.01em; text-transform:uppercase; font-family:Impact,Haettenschweiler,'Arial Narrow Bold',sans-serif; color:#f8fbff; text-shadow:0 2px 0 #0d162e, 2px 2px 0 #0d162e, 3px 3px 0 #0d162e, 4px 4px 0 #0d162e, 0 0 20px rgba(99,210,255,.25); }}
    .logo .z {{ color:#ff5c5c; text-shadow:0 2px 0 #2a0b0b, 2px 2px 0 #2a0b0b, 3px 3px 0 #2a0b0b, 0 0 14px rgba(239,68,68,.35); }}
    .brand-logo {{ display:block; max-width:min(52vw, 320px); margin:0 auto 6px; height:auto; }}
    .tagline {{ margin:12px 0 0; color:#d9e5ff; font-size:clamp(17px,2.2vw,24px); max-width:760px; line-height:1.35; }}
    .nav-toolbar {{ margin-top:12px; display:grid; grid-template-columns:1.2fr 1.4fr .8fr; gap:10px; align-items:start; }}
    .toolbar-group {{ border:1px solid #304b87; border-radius:10px; padding:10px; background:rgba(255,255,255,.03); }}
    .toolbar-group summary {{ cursor:pointer; color:#dff0ff; font-size:12px; text-transform:uppercase; letter-spacing:.08em; font-weight:800; list-style:none; text-align:center; border:1px solid #3f61a0; border-radius:10px; padding:10px 12px; background:linear-gradient(135deg, rgba(99,210,255,.18), rgba(124,255,199,.10)); }}
    .toolbar-group summary::-webkit-details-marker {{ display:none; }}
    .toolbar-group[open] summary {{ margin-bottom:8px; }}
    .toolbar-group summary a {{ color:#dff0ff; text-decoration:none; font-size:12px; text-transform:uppercase; letter-spacing:.08em; font-weight:800; }}
    .toolbar-links {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:center; }}
    .toolbar-links a {{ color:#dfeeff; text-decoration:none; border:1px solid #3b5a95; border-radius:8px; padding:7px 10px; font-size:13px; background:rgba(255,255,255,.02); }}
    .toolbar-links a:hover {{ border-color:var(--accent); }}
    .btn {{ display:inline-block; padding:10px 14px; border-radius:10px; text-decoration:none; color:#081224; background:linear-gradient(90deg,var(--accent),var(--accent2)); font-weight:700; margin-top:8px; }}
    .cards {{ margin-top:18px; display:grid; grid-template-columns:1fr; gap:14px; }}
    .card {{ border:1px solid var(--line); border-radius:14px; background:var(--panel); padding:16px; }}
    .card h2 {{ margin:0 0 10px; font-size:21px; line-height:1.2; }}
    .pick-tabs {{ display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 12px; }}
    .pick-tab {{ border:1px solid #3b5a95; background:rgba(255,255,255,.03); color:#dfeeff; border-radius:9px; padding:9px 12px; font-weight:700; font-size:14px; cursor:pointer; }}
    .pick-tab.active {{ color:#081224; border-color:transparent; background:linear-gradient(90deg,var(--accent),var(--accent2)); }}
    .pick-panel {{ display:none; }}
    .pick-panel.active {{ display:block; }}
    .pick-embed {{ width:100%; min-height:1200px; border:1px solid #2e467d; border-radius:12px; background:#0f1830; }}
    .meta {{ font-size:14px; color:var(--muted); margin-top:10px; }}
    .archive-group {{ border:1px solid #304b87; border-radius:10px; padding:10px 12px; background:rgba(255,255,255,.02); margin-bottom:10px; }}
    .archive-group summary {{ cursor:pointer; font-weight:700; color:#dfeeff; }}
    .archive-links {{ margin-top:10px; display:grid; gap:8px; }}
    .archive-links a {{ color:var(--ink); text-decoration:none; border:1px solid #3b5a95; border-radius:8px; padding:8px 10px; background:rgba(255,255,255,.02); }}
    .archive-links a:hover {{ border-color:var(--accent); }}
    .pill {{ font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:#dff4ff; background:rgba(99,210,255,.18); border:1px solid rgba(99,210,255,.35); border-radius:999px; padding:3px 7px; white-space:nowrap; }}
    .ad-slot{{background:rgba(255,255,255,.03);border:1px dashed #3b5a96;border-radius:12px;padding:12px 14px;margin:14px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    .ad-label{{font:700 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:#9cc4ff}}
    .ad-copy{{color:#d9e6ff;font:500 14px/1.3 Inter,system-ui,sans-serif}}
    .ad-cta{{display:inline-block;padding:7px 10px;border-radius:8px;border:1px solid #4c6db0;color:#dff2ff;text-decoration:none;font:600 12px Inter,system-ui,sans-serif}}
    footer {{ margin-top:16px; color:var(--muted); font-size:12px; display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }}
    .footer-links a {{ color:#c8dbff; text-decoration:none; margin-right:10px; }}
    @media (max-width:1100px) {{ .nav-toolbar {{ grid-template-columns:1fr; }} }}
    @media (max-width:860px) {{ .cards {{ grid-template-columns:1fr; }} .logo {{ font-size:clamp(44px,18vw,90px); }} }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div class="kicker">SportzBallz Daily MLB Desk</div>
      <img class="brand-logo" src="/assets/sportzballz.png" alt="SportzBallz logo" />
      <h1 class="logo" style="display:none;">SPORT<span class="z">Z</span>BALL<span class="z">Z</span></h1>

      <div class="nav-toolbar">
        <details class="toolbar-group">
          <summary><a href="https://sportzballz.io">⚾ Latest Daily Picks</a></summary>
        </details>
        <details class="toolbar-group">
          <summary>🗂️ Archive</summary>
          {''.join(archive_toolbar_groups)}
        </details>
        <details class="toolbar-group">
          <summary><a href="/dashboard.html">📊 Performance Dashboard</a></summary>
        </details>
      </div>
    </section>

    <section class="cards">
      <article class="card">
        <h2>Latest Daily Picks</h2>
        <p>Last Updated: {latest_stamp}</p>
        <div class="pick-tabs" role="tablist" aria-label="Pick type tabs">
          <button class="pick-tab active" data-target="panel-daily" role="tab" aria-selected="true">Money Line</button>
          <button class="pick-tab" data-target="panel-plus" role="tab" aria-selected="false">Plus Money</button>
          <button class="pick-tab" data-target="panel-totals" role="tab" aria-selected="false">Run Total</button>
        </div>

        <section id="panel-daily" class="pick-panel active" role="tabpanel">
          <iframe class="pick-embed" src="{latest_href}?embed=1" title="Daily Picks"></iframe>
        </section>
        <section id="panel-plus" class="pick-panel" role="tabpanel">
          <iframe class="pick-embed" src="{latest_plus_href}?embed=1" title="Plus Money Picks"></iframe>
        </section>
        <section id="panel-totals" class="pick-panel" role="tabpanel">
          <iframe class="pick-embed" src="{latest_totals_href}?embed=1" title="Run Total Picks"></iframe>
        </section>
        {_render_ad_slot('index-hero', 'Homepage Sponsorship')}
      </article>

    </section>

    <footer>
      <span>© SportzBallz.io</span>
      <span class="footer-links"><a href="/media-kit.html">Media Kit</a><a href="/rate-card.html">Rate Card</a><a href="/contact.html">Contact</a></span>
    </footer>
  </main>
  <script>
    (() => {{
      const tabs = Array.from(document.querySelectorAll('.pick-tab'));
      const panels = Array.from(document.querySelectorAll('.pick-panel'));
      const iframes = Array.from(document.querySelectorAll('.pick-embed'));

      function fitIframe(frame) {{
        try {{
          const doc = frame.contentDocument || frame.contentWindow.document;
          if (!doc) return;
          const h = Math.max(doc.body.scrollHeight, doc.documentElement.scrollHeight);
          frame.style.height = Math.max(900, h + 20) + 'px';
        }} catch (_e) {{
          // same-origin expected; ignore if inaccessible
        }}
      }}

      function activate(targetId) {{
        tabs.forEach((t) => {{
          const on = t.dataset.target === targetId;
          t.classList.toggle('active', on);
          t.setAttribute('aria-selected', on ? 'true' : 'false');
        }});
        panels.forEach((p) => p.classList.toggle('active', p.id === targetId));
        const active = document.querySelector(`#${{targetId}} .pick-embed`);
        if (active) setTimeout(() => fitIframe(active), 120);
      }}

      iframes.forEach((f) => f.addEventListener('load', () => fitIframe(f)));
      tabs.forEach((t) => t.addEventListener('click', () => activate(t.dataset.target)));
      const first = document.querySelector('.pick-embed');
      if (first) setTimeout(() => fitIframe(first), 220);
    }})();
  </script>
</body>
</html>
'''


def _find_archive_dates(site_repo: Path):
    dates = []
    pattern = re.compile(r'^(\d{4}-\d{2}-\d{2})\.html$')
    for p in site_repo.glob('*.html'):
        m = pattern.match(p.name)
        if m:
            dates.append(m.group(1))
    return sorted(set(dates), reverse=True)


def _load_history(site_repo: Path):
    data_dir = site_repo / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    history_path = data_dir / 'performance-history.json'
    if not history_path.exists():
        return history_path, []
    try:
        data = json.loads(history_path.read_text())
        if isinstance(data, list):
            return history_path, data
    except Exception:
        pass
    return history_path, []


def _upsert_history(history, summary):
    out = [h for h in history if h.get('date') != summary.get('date')]
    out.append(summary)
    out.sort(key=lambda x: x.get('date', ''), reverse=True)
    return out


def _render_dashboard(history, latest_date=None, archive_dates=None):
    category_defs = [
        ('all_picks', 'All Picks', '#5cc9ff'),
        ('best_confidence_pick', 'Best Confidence Pick', '#a78bfa'),
        ('top3_confidence_picks', 'Top 3 Confidence Picks', '#34d399'),
        ('plus_money_picks', 'Plus Money Picks', '#f59e0b'),
        ('run_total_picks', 'Run Total Picks', '#fb7185'),
    ]

    def _legacy_segment(h, key):
        if key == 'all_picks':
            decided = h.get('decided', 0)
            wins = h.get('wins', 0)
            losses = h.get('losses', 0)
            return {
                'total': h.get('total_picks', 0),
                'decided': decided,
                'wins': wins,
                'losses': losses,
                'profit': 0.0,
                'roi_pct': None,
                'stake_per_pick': 100.0,
            }
        if key == 'plus_money_picks':
            decided = h.get('plus_money_decided', 0)
            wins = h.get('plus_money_wins', 0)
            losses = h.get('plus_money_losses', 0)
            return {
                'total': h.get('plus_money_total', 0),
                'decided': decided,
                'wins': wins,
                'losses': losses,
                'profit': 0.0,
                'roi_pct': None,
                'stake_per_pick': 100.0,
            }
        if key == 'run_total_picks':
            return {
                'total': 0,
                'decided': 0,
                'wins': 0,
                'losses': 0,
                'profit': 0.0,
                'roi_pct': None,
                'stake_per_pick': 100.0,
            }
        return {
            'total': 0,
            'decided': 0,
            'wins': 0,
            'losses': 0,
            'profit': 0.0,
            'roi_pct': None,
            'stake_per_pick': 100.0,
        }

    def _seg(h, key):
        return (h.get('segments') or {}).get(key) or _legacy_segment(h, key)

    totals = {}
    for key, _label, _color in category_defs:
        decided = sum(_seg(h, key).get('decided', 0) for h in history)
        wins = sum(_seg(h, key).get('wins', 0) for h in history)
        losses = sum(_seg(h, key).get('losses', 0) for h in history)
        profit = round(sum(float(_seg(h, key).get('profit', 0.0) or 0.0) for h in history), 2)
        roi = round((profit / (decided * 100.0)) * 100, 2) if decided else None
        totals[key] = {
            'decided': decided,
            'wins': wins,
            'losses': losses,
            'profit': profit,
            'roi_pct': roi,
            'total': sum(_seg(h, key).get('total', 0) for h in history),
        }

    def _svg_line(values, color):
        w, h, pad = 360, 120, 10
        if not values:
            return f"<svg viewBox='0 0 {w} {h}' class='spark'><line x1='{pad}' y1='{h-pad}' x2='{w-pad}' y2='{h-pad}' stroke='#31508e' /></svg>"
        vmin, vmax = min(values), max(values)
        span = (vmax - vmin) if vmax != vmin else 1
        pts = []
        for i, v in enumerate(values):
            x = pad + (i * (w - 2 * pad) / max(1, len(values) - 1))
            y = h - pad - ((v - vmin) / span) * (h - 2 * pad)
            pts.append(f"{x:.1f},{y:.1f}")
        return f"<svg viewBox='0 0 {w} {h}' class='spark'><line x1='{pad}' y1='{h-pad}' x2='{w-pad}' y2='{h-pad}' stroke='#31508e' /><polyline fill='none' stroke='{color}' stroke-width='2.5' points='{' '.join(pts)}' /></svg>"

    asc = sorted(history, key=lambda x: x.get('date', ''))
    chart_cards = []
    for key, label, color in category_defs:
        running = 0.0
        series = []
        for h in asc:
            running += float(_seg(h, key).get('profit', 0.0) or 0.0)
            series.append(round(running, 2))
        t = totals[key]
        roi_txt = f"{t['roi_pct']}%" if t['roi_pct'] is not None else '—'
        chart_cards.append(
            f"""
            <div class='chart-card'>
              <h3>{label}</h3>
              <div class='chart-meta'>Record: {t['wins']}-{t['losses']} • Profit: ${t['profit']:.2f} • ROI: {roi_txt}</div>
              {_svg_line(series, color)}
              <div class='chart-foot'>Cumulative profit (flat $100 per decided pick)</div>
            </div>
            """
        )

    rows = []
    for h in history:
        d = h.get('date', '')
        s_all = _seg(h, 'all_picks')
        s_best = _seg(h, 'best_confidence_pick')
        s_top3 = _seg(h, 'top3_confidence_picks')
        s_pm = _seg(h, 'plus_money_picks')
        s_rt = _seg(h, 'run_total_picks')
        rows.append(
            f"<tr>"
            f"<td><a href='/{d}.html'>{d}</a></td>"
            f"<td>{s_all.get('wins',0)}-{s_all.get('losses',0)} (${float(s_all.get('profit',0) or 0):.2f})</td>"
            f"<td>{s_best.get('wins',0)}-{s_best.get('losses',0)} (${float(s_best.get('profit',0) or 0):.2f})</td>"
            f"<td>{s_top3.get('wins',0)}-{s_top3.get('losses',0)} (${float(s_top3.get('profit',0) or 0):.2f})</td>"
            f"<td>{s_pm.get('wins',0)}-{s_pm.get('losses',0)} (${float(s_pm.get('profit',0) or 0):.2f})</td>"
            f"<td>{s_rt.get('wins',0)}-{s_rt.get('losses',0)} (${float(s_rt.get('profit',0) or 0):.2f})</td>"
            f"<td>{h.get('pending',0)}</td>"
            f"</tr>"
        )

    all_total = totals['all_picks']
    pm_total = totals['plus_money_picks']
    rt_total = totals['run_total_picks']
    all_roi_txt = f"{all_total['roi_pct']}%" if all_total['roi_pct'] is not None else '—'
    pm_roi_txt = f"{pm_total['roi_pct']}%" if pm_total['roi_pct'] is not None else '—'
    rt_roi_txt = f"{rt_total['roi_pct']}%" if rt_total['roi_pct'] is not None else '—'

    if not latest_date:
        latest_date = history[0].get('date') if history else datetime.now().strftime('%Y-%m-%d')
    archive_dates = archive_dates or [h.get('date') for h in history if h.get('date')]
    toolbar_html = _render_global_toolbar(latest_date, archive_dates)

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http://www.w3.org/2000/svg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Ctext%20y%3D%22.9em%22%20font-size%3D%2290%22%3E%E2%9A%BE%3C/text%3E%3C/svg%3E" />
  <title>SportzBallz | Performance Dashboard</title>
  <meta name="description" content="SportzBallz historical MLB pick performance, records, and plus-money metrics." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/dashboard.html')}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="SportzBallz" />
  <meta property="og:title" content="SportzBallz | Performance Dashboard" />
  <meta property="og:description" content="Track win rates, records, and plus-money outcomes over time." />
  <meta property="og:url" content="{_site_url('/dashboard.html')}" />
  <meta name="twitter:card" content="summary_large_image" />
  <style>
    :root {{ --bg:#0a1020; --panel:#101a33; --ink:#eaf0ff; --muted:#a7b7df; --line:#273a6b; --accent:#5cc9ff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:linear-gradient(180deg, #0b1220 0%, #0a1020 100%); color:var(--ink); font-family:Inter,system-ui,sans-serif; }}
    .wrap {{ max-width:1100px; margin:0 auto; padding:24px 16px 48px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:14px; margin-bottom:14px; }}
    h1 {{ margin:0 0 8px; font-size:34px; }}
    .meta {{ color:var(--muted); margin-bottom:8px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:10px; }}
    .ad-slot{{background:rgba(255,255,255,.03);border:1px dashed #3b5a96;border-radius:12px;padding:12px 14px;margin:12px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    .ad-label{{font:700 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:#9cc4ff}}
    .ad-copy{{color:#d9e6ff;font:500 14px/1.3 Inter,system-ui,sans-serif}}
    .ad-cta{{display:inline-block;padding:7px 10px;border-radius:8px;border:1px solid #4c6db0;color:#dff2ff;text-decoration:none;font:600 12px Inter,system-ui,sans-serif}}
    {_toolbar_css()}
    .k {{ border:1px dashed #31508e; border-radius:10px; padding:10px; }}
    .k span {{ display:block; color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; margin-bottom:4px; }}
    .k strong {{ font-size:20px; }}
    .chart-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:10px; }}
    .chart-card {{ border:1px dashed #31508e; border-radius:10px; padding:10px; background:rgba(255,255,255,.02); }}
    .chart-card h3 {{ margin:0 0 6px; font-size:16px; }}
    .chart-meta {{ color:#cfe1ff; font-size:12px; margin-bottom:6px; }}
    .chart-foot {{ color:var(--muted); font-size:11px; margin-top:4px; }}
    .spark {{ width:100%; height:120px; display:block; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ border-bottom:1px solid #2a3f70; padding:10px 8px; text-align:left; }}
    th {{ color:#cfe0ff; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
    td {{ color:#e2ecff; }}
    a {{ color:#8ad8ff; text-decoration:none; }}
    .links a {{ display:inline-block; margin-right:8px; border:1px solid #31508e; border-radius:8px; padding:6px 10px; }}
  </style>
</head>
<body>
  <main class="wrap">
    {toolbar_html}
    <div class="card">
      <h1>Performance Dashboard</h1>
      <div class="meta">Auto-tracked from published daily picks. Assumption: flat <strong>$100 stake</strong> on each decided pick in each strategy bucket.</div>
      <div class="links"><a href="/">Home</a> <a href="/media-kit.html">Media Kit</a> <a href="/rate-card.html">Rate Card</a> <a href="/contact.html">Contact</a></div>
      {_render_ad_slot('dashboard-top', 'Dashboard Sponsorship')}
      <div class="grid">
        <div class="k"><span>Total Picks Logged</span><strong>{all_total['total']}</strong></div>
        <div class="k"><span>All Picks Record</span><strong>{all_total['wins']}-{all_total['losses']}</strong></div>
        <div class="k"><span>All Picks Profit</span><strong>${all_total['profit']:.2f}</strong></div>
        <div class="k"><span>All Picks ROI</span><strong>{all_roi_txt}</strong></div>
        <div class="k"><span>Plus Money Record</span><strong>{pm_total['wins']}-{pm_total['losses']}</strong></div>
        <div class="k"><span>Plus Money ROI</span><strong>{pm_roi_txt}</strong></div>
        <div class="k"><span>Run Totals Record</span><strong>{rt_total['wins']}-{rt_total['losses']}</strong></div>
        <div class="k"><span>Run Totals ROI</span><strong>{rt_roi_txt}</strong></div>
      </div>
    </div>

    <div class="card">
      <h2 style="margin-top:0">Season Strategy Charts</h2>
      <div class="chart-grid">
        {''.join(chart_cards)}
      </div>
    </div>

    <div class="card">
      <h2 style="margin-top:0">Daily Performance</h2>
      <table>
        <thead><tr><th>Date</th><th>All Picks</th><th>Best Confidence</th><th>Top 3 Confidence</th><th>Plus Money</th><th>Run Totals</th><th>Pending</th></tr></thead>
        <tbody>
          {''.join(rows) if rows else '<tr><td colspan="7">No history yet.</td></tr>'}
        </tbody>
      </table>
    </div>
  </main>
  {_embed_mode_script()}
  {_hit_counter_script()}
</body>
</html>
'''


def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


def _preferred_theme_css() -> str:
    return """
    :root{--bg:#060b17!important;--panel:#0b1328!important;--ink:#e6f1ff!important;--muted:#93a7cc!important;--line:#28436d!important;--accent:#00d1ff!important;--accent2:#7cff7a!important}
    body{background:radial-gradient(1200px 700px at 80% -10%, #1b3a7a 0%, transparent 55%), radial-gradient(900px 600px at 0% 0%, #0b4f66 0%, transparent 45%), #050a14!important}
    .wrap{max-width:1320px!important}
    header,.hero{background:linear-gradient(135deg,rgba(0,209,255,.14),rgba(124,255,122,.10))!important;border-color:#2f5489!important}
    .pick-card,.card{border-radius:18px!important;border-color:#2d4f86!important;background:linear-gradient(180deg,#0a142a,#0b1730)!important;box-shadow:0 16px 40px rgba(0,0,0,.36)!important}
    .meta-grid div,.tcard{background:rgba(255,255,255,.04)!important;border-color:#345d96!important}
    .lede{font-size:18px!important;line-height:1.68!important;color:#f0f7ff!important}
    h1,h2{letter-spacing:.02em!important}
    .nav-toolbar .toolbar-group{background:rgba(11,19,40,.9)!important;border-color:#2d4f86!important}
    .nav-toolbar .toolbar-group summary{background:linear-gradient(135deg,rgba(0,209,255,.20),rgba(124,255,122,.14))!important;border-color:#3f6daf!important}
    .res-win{background:rgba(34,197,94,.18)!important;color:#86efac!important;border-color:#34d399!important}
    .res-loss{background:rgba(239,68,68,.18)!important;color:#fca5a5!important;border-color:#fb7185!important}
    .res-pending{background:rgba(59,130,246,.18)!important;color:#bfdbfe!important;border-color:#60a5fa!important}
    .res-inprogress{background:rgba(245,158,11,.25)!important;color:#fde68a!important;border-color:#f59e0b!important}
    """


def _apply_preferred_theme(html_text: str) -> str:
    inject = f"<style id=\"preferred-theme\">{_preferred_theme_css()}</style>"
    if "<style id=\"preferred-theme\">" in html_text:
        return re.sub(r'<style id="preferred-theme">.*?</style>', inject, html_text, flags=re.S)
    if "</head>" in html_text:
        return html_text.replace("</head>", inject + "\n</head>", 1)
    return html_text


def _apply_preferred_theme_files(site_repo: Path, parsed_date: str):
    files = [
        f"{parsed_date}.html",
        f"{parsed_date}-plus-money.html",
        f"{parsed_date}-run-line.html",
        f"{parsed_date}-run-totals.html",
        "index.html",
        "dashboard.html",
    ]
    for name in files:
        p = site_repo / name
        if not p.exists():
            continue
        raw = p.read_text(encoding="utf-8", errors="ignore")
        themed = _apply_preferred_theme(raw)
        if themed != raw:
            p.write_text(themed, encoding="utf-8")


def publish_daily_site(markdown_path: str, site_repo_path: str = None):
    md_file = Path(markdown_path)
    if not md_file.exists():
        return None

    parsed = _parse_markdown(md_file.read_text())
    if not parsed['date']:
        # derive from filename fallback: YYYY-MM-DD-pick.md
        m = re.search(r'(\d{4}-\d{2}-\d{2})', md_file.name)
        if not m:
            return None
        parsed['date'] = m.group(1)

    if site_repo_path:
        site_repo = Path(site_repo_path)
    else:
        site_repo = Path(__file__).resolve().parents[3] / 'sportzballz.io'

    if not site_repo.exists():
        print(f"Site repo not found: {site_repo}")
        return None

    evaluated_picks, summary = _evaluate_picks(parsed)

    archive = _find_archive_dates(site_repo)
    if parsed['date'] not in archive:
        archive = [parsed['date']] + archive
    archive = sorted(set(archive), reverse=True)
    latest_global = archive[0] if archive else parsed['date']

    date_html = site_repo / f"{parsed['date']}.html"
    frozen_commentary = _extract_existing_commentary_map(date_html)
    frozen_odds = _extract_existing_odds_map(date_html)

    # Do not update odds once game has started or concluded.
    for p in evaluated_picks:
        key = f"{p.get('winner', '')}|||{p.get('loser', '')}"
        if _is_game_started_or_done(p) and key in frozen_odds:
            p.setdefault('fields', {})['Pick Odds'] = frozen_odds[key]

    date_html.write_text(_render_daily_html(parsed, evaluated_picks, summary, frozen_commentary, latest_global, archive))

    plus_html = site_repo / f"{parsed['date']}-plus-money.html"
    plus_html.write_text(_render_plus_money_html(parsed, evaluated_picks, summary, frozen_commentary, latest_global, archive))

    run_line_html = site_repo / f"{parsed['date']}-run-line.html"
    run_line_html.write_text(_render_run_line_html(parsed, evaluated_picks, frozen_commentary, latest_global, archive))

    totals_html = site_repo / f"{parsed['date']}-run-totals.html"
    totals_html.write_text(_render_run_totals_html(parsed, evaluated_picks, latest_global, archive))

    history_path, history = _load_history(site_repo)
    history = _upsert_history(history, summary)
    history_path.write_text(json.dumps(history, indent=2))
    (site_repo / 'dashboard.html').write_text(_render_dashboard(history, latest_global, archive))
    (site_repo / 'media-kit.html').write_text(_render_media_kit())
    (site_repo / 'rate-card.html').write_text(_render_rate_card())
    (site_repo / 'contact.html').write_text(_render_contact_page())

    (site_repo / 'index.html').write_text(_render_top_index(parsed['date'], archive, evaluated_picks, frozen_commentary))
    (site_repo / 'robots.txt').write_text(_render_robots_txt())
    (site_repo / 'sitemap.xml').write_text(_render_sitemap_xml(archive))

    # Apply preferred visual theme (formerly redesign 2) to primary pages.
    _apply_preferred_theme_files(site_repo, parsed['date'])

    auto_publish = os.environ.get('AUTO_PUBLISH_SITE', 'true').lower() in ('1', 'true', 'yes', 'on')
    if not auto_publish:
        return str(date_html)

    # Commit + push any changes
    add = _run([
        'git', 'add', 'index.html', 'dashboard.html', 'data/performance-history.json',
        'media-kit.html', 'rate-card.html', 'contact.html', 'robots.txt', 'sitemap.xml',
        f"{parsed['date']}.html", f"{parsed['date']}-plus-money.html", f"{parsed['date']}-run-line.html", f"{parsed['date']}-run-totals.html"
    ], site_repo)
    if add.returncode != 0:
        print(add.stderr.strip())
        return str(date_html)

    status = _run(['git', 'status', '--porcelain'], site_repo)
    if status.returncode != 0 or not status.stdout.strip():
        return str(date_html)

    commit_msg = f"Auto-publish daily picks {parsed['date']}"
    commit = _run(['git', 'commit', '-m', commit_msg], site_repo)
    if commit.returncode != 0:
        print(commit.stderr.strip() or commit.stdout.strip())
        return str(date_html)

    push = _run(['git', 'push', 'origin', 'main'], site_repo)
    if push.returncode != 0:
        print(push.stderr.strip() or push.stdout.strip())
    else:
        print(f"Auto-published site for {parsed['date']}")

    return str(date_html)
