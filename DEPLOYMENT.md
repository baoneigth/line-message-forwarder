# 部署指南 (DEPLOYMENT)

本文件說明如何在生產環境中部署 LINE 訊息轉發工具，並啟用進程監控與自動重啟。

## 前置準備

```bash
git clone https://github.com/baoneigth/line-message-forwarder.git
cd line-message-forwarder
pip install -r requirements.txt
cp .env.example .env
# 編輯 .env 填入帳號資訊
```

`data/` 目錄用於存放執行期間產生的檔案（心跳檔、PID、日誌、重啟歷史），
無需手動建立，程式會自動建立。

## 方式一：Systemd（推薦於 Linux）

```bash
# 1. 複製配置文件
sudo cp system/line-forwarder.service /etc/systemd/system/
sudo cp system/line-forwarder-monitor.service /etc/systemd/system/

# 2. 重載 Systemd
sudo systemctl daemon-reload

# 3. 啟動服務
sudo systemctl start line-forwarder
sudo systemctl start line-forwarder-monitor

# 4. 設置開機自啟
sudo systemctl enable line-forwarder
sudo systemctl enable line-forwarder-monitor
```

或直接使用安裝腳本：

```bash
sudo bash system/install-systemd.sh
```

查看日誌：

```bash
sudo journalctl -u line-forwarder -f
sudo journalctl -u line-forwarder-monitor -f
```

## 方式二：Supervisor（跨平台）

```bash
# 1. 安裝 Supervisor
pip install supervisor

# 2. 複製配置
sudo cp system/supervisord.conf /etc/supervisor/conf.d/line-forwarder.conf

# 3. 重載配置
sudo supervisorctl reread
sudo supervisorctl update

# 4. 啟動
sudo supervisorctl start line-forwarder:*
```

或直接使用安裝腳本：

```bash
sudo bash system/install-supervisor.sh
```

## 方式三：獨立進程管理器

不想使用 systemd 或 supervisor 時，可以直接使用內建的 `process_manager.py`：

```bash
python process_manager.py start     # 啟動
python process_manager.py status    # 查詢狀態
python process_manager.py restart   # 重啟
python process_manager.py stop      # 停止
python process_manager.py cleanup   # 清理殭屍進程
```

若需要獨立的自動重啟監控，另外執行：

```bash
python monitors/process_monitor.py
```

## Web 儀表板

```bash
python web_dashboard.py 8080
```

瀏覽 `http://<host>:8080/` 即可查看進程狀態，並可透過畫面上的按鈕手動重啟
或停止服務。詳見 [MONITORING.md](MONITORING.md)。
