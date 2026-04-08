#!/usr/bin/env python3
from pathlib import Path
import os
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
SITE_REPO = REPO_ROOT.parent / "sportzballz.io"

sys.path.append(str(SRC_DIR))
from connector.pick_site_publish import publish_daily_site  # noqa: E402

DATE_HTML_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-plus-money|-run-line|-run-totals)?\.html$")


def find_dates_with_pending(site_root: Path):
    dates = set()
    for p in site_root.glob("*.html"):
        m = DATE_HTML_RE.match(p.name)
        if not m:
            continue
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if ">PENDING<" in txt:
            dates.add(m.group(1))
    return sorted(dates)


def main():
    dates = find_dates_with_pending(SITE_REPO)
    if not dates:
        print("No pending-result date pages found.")
        return 0

    # Local render only; OpenClaw cron handles final push.
    os.environ["AUTO_PUBLISH_SITE"] = "false"

    refreshed = []
    missing = []

    for d in dates:
        md = SRC_DIR / "picks" / f"{d}-pick.md"
        if not md.exists():
            missing.append(d)
            continue
        try:
            out = publish_daily_site(str(md), str(SITE_REPO))
            refreshed.append((d, out))
            print(f"Refreshed pending date {d} from {md.name}")
        except Exception as e:
            print(f"Failed refresh for {d}: {e}")

    print(f"Pending dates found: {len(dates)}")
    print(f"Refreshed: {len(refreshed)}")
    if missing:
        print("Missing markdown for dates: " + ", ".join(missing))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
