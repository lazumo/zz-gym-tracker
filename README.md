# zz-gym-tracker

長期追蹤 [臺北市中正運動中心](https://wsjjsc.com.tw/) 健身房（與游泳池）即時人潮。
GitHub Actions 每 15 分鐘自動 poll 一次，每週一早上 06:00 (UTC+8) 重產 heatmap。
你不需要做任何事 — repo 本身就是資料庫，週報自動 commit 進來。

## 最新 heatmap

![heatmap](reports/heatmap-latest.png)

文字版排名見 [reports/summary.md](reports/summary.md)。

## 想自己看現在多少人

直接打開官網：<https://wsjjsc.com.tw/>。本 repo 是給長期統計用的。

## 結構

| 檔案 | 用途 |
|---|---|
| `poller.py` | 抓首頁 HTML、regex 解析、寫入 SQLite + CSV |
| `report.py` | 由 CSV 計算 weekday×hour 平均使用率，產 PNG + summary.md |
| `.github/workflows/poll.yml` | 每 15 分鐘 cron poll |
| `.github/workflows/report.yml` | 每週日 22:00 UTC (= 週一 06:00 Taipei) cron 產報告 |
| `data/occupancy.db` | SQLite raw 資料（單表 `readings`） |
| `data/occupancy.csv` | 一樣的資料但 git diff 看得懂 |
| `reports/heatmap-latest.png` | 最新一張 heatmap |

## Schema

```
ts_utc TEXT PK | ts_local | weekday(0=Mon) | hour | minute
              | gym_count | gym_capacity | pool_count | pool_capacity
```

## 注意事項

- GitHub Actions cron 不保證準時，實際延遲可能 5–15 分鐘，少數情況會跳一次。對統計平均沒影響。
- 公開 repo 的 Actions 額度無上限，私人 repo 才有月配額。
- GitHub 對「60 天沒人 commit」的 repo 會停用 scheduled workflow。本 repo 每 15 分鐘自己 commit 一次，會自動續命。
- 想手動觸發：repo → Actions → poll / weekly-report → Run workflow。

## 本地測試

```bash
pip install -r requirements.txt
python poller.py    # 抓一次、寫一筆
python report.py    # 從 CSV 產 PNG
```
