#!/bin/bash
# LINE 訊息轉發工具 - macOS/Linux 運行腳本

echo "[*] LINE 訊息轉發工具"
echo ""

# 檢查 .env 文件
if [ ! -f .env ]; then
    echo "[!] 錯誤: .env 文件不存在"
    echo "[*] 請先運行 ./install.sh"
    exit 1
fi

# 檢查 Python
if ! command -v python3 &> /dev/null; then
    echo "[!] 錯誤: 未安裝 Python 3"
    exit 1
fi

# 運行程式
echo "[*] 正在啟動轉發機器人..."
echo ""
python3 forwarder.py
