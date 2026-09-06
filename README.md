# LINE 個人帳號訊息轉發工具

使用個人 LINE 帳號直接轉發群組中的訊息到指定群組或用戶。

## ⚠️ 重要警告

**本工具使用個人 LINE 帳號的非官方 API，可能違反 LINE 服務條款。使用本工具導致帳號被封或其他後果，作者不負責任何責任。**

## 功能特性

- ✓ 文字訊息轉發
- ✓ 圖片轉發
- ✓ 貼圖轉發
- ✓ 視頻/音頻轉發
- ✓ 指令控制轉發模式
- ✓ 靈活的轉發目標設定

## 安裝

### 1. 克隆仓库
```bash
git clone https://github.com/baoneigth/line-message-forwarder.git
cd line-message-forwarder
```

### 2. 安裝依賴
```bash
pip install -r requirements.txt
```

### 3. 配置環境變數
```bash
cp .env.example .env
```

編輯 `.env` 文件，填入你的 LINE 帳號信息：
```env
LINE_EMAIL=your_email@example.com
LINE_PASSWORD=your_password
```

## 使用方法

### 啟動轉發機器人
```bash
python forwarder.py
```

### 可用指令

在 LINE 群組中輸入以下指令來控制轉發：

| 指令 | 說明 |
|------|------|
| `/forward` | 啟動轉發模式 |
| `/stop` | 停止轉發模式 |
| `/status` | 查看轉發狀態 |
| `/target @群組名稱` | 設定轉發目標群組 |

### 工作流程

1. **啟動程式**
   ```bash
   python forwarder.py
   ```

2. **在群組中啟動轉發模式**
   ```
   輸入: /forward
   回應: [轉發模式] 已啟動 ✓
   ```

3. **設定轉發目標**
   ```
   輸入: /target @目標群組
   回應: [✓] 轉發目標已設定為: 目標群組
   ```

4. **群組中的訊息將被自動轉發**
   - 所有文字訊息
   - 圖片
   - 貼圖
   - 視頻/音頻

5. **停止轉發**
   ```
   輸入: /stop
   回應: [✓] 轉發模式已停止
   ```

## 文件結構

```
line-message-forwarder/
├── config.py              # 配置文件
├── forwarder.py           # 主程式邏輯
├── requirements.txt       # 依賴包列表
├── .env.example          # 環境變數範本
└── README.md             # 說明文件
```

## 技術棧

- **Python 3.7+**
- **linepy** - LINE 非官方 API 庫
- **python-dotenv** - 環境變數管理

## 常見問題

### Q: 登入時出現 "QR Code required" 錯誤
**A:** LINE 帳號可能需要 QR Code 驗證。請稍候片刻重新嘗試或更新 linepy 版本。

### Q: 轉發訊息時出現延遲
**A:** 這是正常現象，因為使用的是非官方 API。可以在 `forwarder.py` 中調整 `time.sleep()` 的值。

### Q: 能否同時轉發到多個群組？
**A:** 可以，修改 `_forward_message()` 方法支持多個目標 ID。

## 進階設定

編輯 `config.py` 中的 `FORWARD_SETTINGS` 來自定義要轉發的訊息類型：

```python
FORWARD_SETTINGS = {
    'text': True,      # 轉發文字
    'image': True,     # 轉發圖片
    'sticker': True,   # 轉發貼圖
    'video': True,     # 轉發視頻
    'audio': True,     # 轉發音頻
}
```

## 貢獻

歡迎提交 Issue 和 Pull Request！

## 許可

MIT License

## 免責聲明

本工具僅供學習和研究使用。使用本工具導致的任何損失（包括但不限於帳號被封）均由使用者自行承擔。
