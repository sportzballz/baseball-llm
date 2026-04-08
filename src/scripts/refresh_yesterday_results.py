#!/usr/bin/env python3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import os
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
SITE_REPO = REPO_ROOT.parent / "sportzballz.io"

sys.path.append(str(SRC_DIR))

from connector.pick_site_publish import publish_daily_site  # noqa: E402


def yesterday_est_str():
    return (datetime.now(ZoneInfo("America/New_York")).date() - timedelta(days=1)).isoformat()


def main():
    y = yesterday_est_str()
    md = SRC_DIR / "picks" / f"{y}-pick.md"
    if not md.exists():
        print(f"No yesterday markdown found: {md}")
        return 0

    # Always local-only render update here; publish step handled by OpenClaw cron job.
    os.environ["AUTO_PUBLISH_SITE"] = "false"
    out = publish_daily_site(str(md), str(SITE_REPO))
    print(f"Refreshed yesterday results page set from {md.name} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
