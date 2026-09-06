#!/bin/bash
# 安裝 line-forwarder 的 Systemd 服務
set -e

INSTALL_DIR="/opt/line-message-forwarder"
SERVICE_DIR="/etc/systemd/system"

echo "[*] 安裝 Systemd 服務..."

sudo mkdir -p "$INSTALL_DIR/data"
sudo cp "$(dirname "$0")/line-forwarder.service" "$SERVICE_DIR/"
sudo cp "$(dirname "$0")/line-forwarder-monitor.service" "$SERVICE_DIR/"

echo "[*] 重載 Systemd..."
sudo systemctl daemon-reload

echo "[*] 設置開機自啟..."
sudo systemctl enable line-forwarder
sudo systemctl enable line-forwarder-monitor

echo "[✓] 安裝完成。使用以下指令啟動服務："
echo "    sudo systemctl start line-forwarder"
echo "    sudo systemctl start line-forwarder-monitor"
