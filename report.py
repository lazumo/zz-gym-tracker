#!/usr/bin/env python3
"""Generate a weekday x hour heatmap PNG from the polled CSV."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"
CSV_PATH = DATA_DIR / "occupancy.csv"

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
TAIPEI = timezone(timedelta(hours=8))


def main() -> int:
    REPORT_DIR.mkdir(exist_ok=True)
    if not CSV_PATH.exists():
        print(f"No data yet at {CSV_PATH}", flush=True)
        return 0

    df = pd.read_csv(CSV_PATH)
    df = df.dropna(subset=["gym_count", "gym_capacity"])
    if df.empty:
        print("No usable rows yet", flush=True)
        return 0

    df["pct"] = df["gym_count"] / df["gym_capacity"] * 100

    pct_pivot = (
        df.pivot_table(index="weekday", columns="hour", values="pct", aggfunc="mean")
        .reindex(index=range(7), columns=range(24))
    )
    count_pivot = (
        df.pivot_table(index="weekday", columns="hour", values="gym_count", aggfunc="mean")
        .reindex(index=range(7), columns=range(24))
    )
    capacity = int(df["gym_capacity"].mode().iat[0])

    fig, ax = plt.subplots(figsize=(13, 4.8))
    im = ax.imshow(pct_pivot, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=100)

    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{h:02d}" for h in range(24)])
    ax.set_yticks(range(7))
    ax.set_yticklabels(WEEKDAY_LABELS)
    ax.set_xlabel("Hour (Asia/Taipei)")
    ax.set_ylabel("Weekday")

    span = f"{df['ts_local'].min()[:10]} -> {df['ts_local'].max()[:10]}"
    n_readings = len(df)
    ax.set_title(
        f"Zhongzheng Gym Avg Occupancy   |   capacity={capacity}   |   {span}   |   n={n_readings}"
    )

    for i in range(7):
        for j in range(24):
            v = pct_pivot.iloc[i, j]
            c = count_pivot.iloc[i, j]
            if pd.notna(v):
                ax.text(
                    j, i, f"{c:.0f}\n{v:.0f}%",
                    ha="center", va="center",
                    fontsize=6.5,
                    linespacing=0.9,
                    color="black" if v < 55 else "white",
                )

    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("% of capacity")
    fig.tight_layout()

    fig.savefig(REPORT_DIR / "heatmap-latest.png", dpi=140)
    today = datetime.now(TAIPEI).strftime("%Y-%m-%d")
    fig.savefig(REPORT_DIR / f"heatmap-{today}.png", dpi=140)
    plt.close(fig)

    flat = pct_pivot.stack().reset_index()
    flat.columns = ["weekday", "hour", "pct"]
    flat = flat.dropna(subset=["pct"])
    flat["count"] = flat.apply(
        lambda r: count_pivot.loc[r["weekday"], r["hour"]], axis=1
    )
    flat["slot"] = (
        flat["weekday"].map(dict(enumerate(WEEKDAY_LABELS)))
        + " "
        + flat["hour"].astype(str).str.zfill(2)
        + ":00"
    )
    flat = flat.sort_values("pct")

    md = [
        "# 中正運動中心健身房 報告",
        "",
        f"資料區間: `{span}`, 共 **{n_readings}** 筆觀測，capacity = **{capacity}** 人",
        "",
        "![heatmap](heatmap-latest.png)",
        "",
        "## 最空的時段 (top 10)",
        "",
        "| 時段 | 平均人數 | 使用率 |",
        "|---|---:|---:|",
    ]
    for _, r in flat.head(10).iterrows():
        md.append(f"| {r['slot']} | {r['count']:.0f} 人 | {r['pct']:.0f}% |")
    md += [
        "",
        "## 最擠的時段 (top 10)",
        "",
        "| 時段 | 平均人數 | 使用率 |",
        "|---|---:|---:|",
    ]
    for _, r in flat.tail(10).iloc[::-1].iterrows():
        md.append(f"| {r['slot']} | {r['count']:.0f} 人 | {r['pct']:.0f}% |")

    (REPORT_DIR / "summary.md").write_text("\n".join(md), encoding="utf-8")

    print(f"Heatmap written. n={n_readings}, span={span}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
