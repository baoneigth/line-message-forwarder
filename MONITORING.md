# 監控指南 (MONITORING)

本文件說明進程監控與自動重啟機制的運作方式。

## 心跳檢測

- `forwarder_enhanced.py` 啟動後會透過 `HeartbeatManager` 每 30 秒（預設）
  更新一次 `data/heartbeat.json`，內容包含 PID、狀態與時間戳。
- `monitors/process_monitor.py` 中的 `ProcessMonitor` 每 60 秒（預設）檢查
  一次心跳，若心跳時間戳超過 2 分鐘（預設 `heartbeat_timeout=120` 秒）未更新，
  視為進程異常。

## 自動重啟

- 當偵測到進程未運行，或心跳超時，`ProcessMonitor.auto_restart_on_crash()`
  會自動呼叫 `restart_process()` 重啟服務。
- 每次重啟都會透過 `log_restart_event()` 記錄到：
  - `data/process_monitor.log`（純文字日誌）
  - `data/restart_history.json`（結構化重啟歷史）

## 重啟限制（防止無限循環）

- 預設在 60 秒 (`restart_window`) 內若重啟次數達到 3 次
  (`restart_limit`)，監控器會進入 5 分鐘 (`cooldown_period`) 的冷卻期，
  暫停自動重啟，避免無限重啟循環消耗資源。
- 冷卻期結束後，監控將恢復正常運作。

## 資源監控

`process_manager.py` 的 `ProcessManager.get_status()` 會回傳：

- `running` - 是否正在運行
- `pid` - 進程 ID
- `uptime_seconds` - 運行時間（秒）
- `memory_rss_bytes` - 記憶體占用（RSS，位元組）
- `cpu_percent` - CPU 使用率
- `heartbeat` - 最新的心跳內容

`cleanup_zombies()` 會清理由本進程管理器產生的殭屍（defunct）子進程。

## Web 儀表板 API

啟動 `python web_dashboard.py` 後，可使用以下 API：

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET  | `/api/process/status` | 進程狀態（運行中、PID、運行時間、記憶體…） |
| GET  | `/api/process/uptime` | 運行時間 |
| GET  | `/api/process/memory` | 記憶體占用 |
| GET  | `/api/process/restart-history` | 重啟歷史 |
| POST | `/api/process/restart` | 手動重啟 |
| POST | `/api/process/stop` | 手動停止 |

### 儀表板身份驗證

所有 `/api/process/*` 端點（包含查詢狀態與控制端點）皆需要驗證。若未設定
`DASHBOARD_TOKEN`，`web_dashboard.py` 會拒絕啟動，避免儀表板在未受保護的情況
下暴露於網路上。啟動前請先設定環境變數：

```bash
export DASHBOARD_TOKEN="請填入一組隨機字串"
python web_dashboard.py 8080
```

呼叫任一 API 端點時需在標頭附上 Token（`X-Dashboard-Token`）：

```bash
curl -X POST -H "X-Dashboard-Token: $DASHBOARD_TOKEN" \
  http://localhost:8080/api/process/restart
```

網頁介面上方也提供輸入框，貼上 Token 後即可使用重啟/停止按鈕。

## 自訂設定

`ProcessMonitor` 與 `ProcessManager` 的建構子皆接受自訂參數，例如：

```python
from monitors.process_monitor import ProcessMonitor

monitor = ProcessMonitor(
    heartbeat_timeout=120,   # 心跳逾時秒數
    restart_limit=3,         # 重啟次數上限
    restart_window=60,       # 統計重啟次數的時間窗（秒）
    cooldown_period=300,     # 超過限制後的冷卻時間（秒）
    check_interval=60,       # 監控檢查間隔（秒）
)
monitor.run()
```
