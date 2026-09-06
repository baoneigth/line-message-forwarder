#!/bin/bash
# 安裝 line-forwarder 的 Supervisor 配置
set -e

CONF_DIR="/etc/supervisor/conf.d"

echo "[*] 檢查 Supervisor 是否已安裝..."
if ! command -v supervisorctl &> /dev/null; then
    echo "[!] 未偵測到 Supervisor，正在安裝..."
    pip install supervisor
fi

echo "[*] 複製配置文件..."
sudo mkdir -p "$CONF_DIR"
sudo cp "$(dirname "$0")/supervisord.conf" "$CONF_DIR/line-forwarder.conf"

echo "[*] 重載 Supervisor 配置..."
sudo supervisorctl reread
sudo supervisorctl update

echo "[✓] 安裝完成。使用以下指令啟動服務："
echo "    sudo supervisorctl start line-forwarder:*"
