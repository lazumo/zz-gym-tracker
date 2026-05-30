#!/usr/bin/env python3
"""Poll Zhongzheng Sports Center (wsjjsc.com.tw) and store one occupancy reading."""
from __future__ import annotations

import csv
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

URL = "https://wsjjsc.com.tw/"
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "occupancy.db"
CSV_PATH = DATA_DIR / "occupancy.csv"
TAIPEI = timezone(timedelta(hours=8), name="Asia/Taipei")

GYM_RE = re.compile(
    r'健身房\s*<div class="notice">\s*(\d+)\s*</div>\s*人\s*<span>\s*容留\s*(\d+)\s*人\s*</span>'
)
POOL_RE = re.compile(
    r'游泳池\s*<div class="notice">\s*(\d+)\s*</div>\s*人\s*<span>\s*容留\s*(\d+)\s*人\s*</span>'
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    ts_utc        TEXT NOT NULL PRIMARY KEY,
    ts_local      TEXT NOT NULL,
    weekday       INTEGER NOT NULL,
    hour          INTEGER NOT NULL,
    minute        INTEGER NOT NULL,
    gym_count     INTEGER,
    gym_capacity  INTEGER,
    pool_count    INTEGER,
    pool_capacity INTEGER
);
CREATE INDEX IF NOT EXISTS idx_weekday_hour ON readings(weekday, hour);
"""

CSV_HEADER = [
    "ts_utc", "ts_local", "weekday", "hour", "minute",
    "gym_count", "gym_capacity", "pool_count", "pool_capacity",
]


def parse(html: str) -> tuple[int | None, int | None, int | None, int | None]:
    g = GYM_RE.search(html)
    p = POOL_RE.search(html)
    gym = (int(g.group(1)), int(g.group(2))) if g else (None, None)
    pool = (int(p.group(1)), int(p.group(2))) if p else (None, None)
    return gym[0], gym[1], pool[0], pool[1]


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0 (zz-gym-tracker; +https://github.com)"}
    try:
        r = requests.get(URL, headers=headers, timeout=30)
        r.raise_for_status()
        gym_count, gym_cap, pool_count, pool_cap = parse(r.text)
    except Exception as e:
        print(f"ERROR fetching/parsing: {e}", file=sys.stderr)
        gym_count = gym_cap = pool_count = pool_cap = None

    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    now_local = now_utc.astimezone(TAIPEI)
    row = {
        "ts_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ts_local": now_local.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "weekday": now_local.weekday(),
        "hour": now_local.hour,
        "minute": now_local.minute,
        "gym_count": gym_count,
        "gym_capacity": gym_cap,
        "pool_count": pool_count,
        "pool_capacity": pool_cap,
    }

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR IGNORE INTO readings VALUES "
            "(:ts_utc, :ts_local, :weekday, :hour, :minute, "
            ":gym_count, :gym_capacity, :pool_count, :pool_capacity)",
            row,
        )
        conn.commit()
    finally:
        conn.close()

    is_new = not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADER)
        if is_new:
            w.writeheader()
        w.writerow(row)

    print(
        f"{row['ts_local']}  gym={gym_count}/{gym_cap}  pool={pool_count}/{pool_cap}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
