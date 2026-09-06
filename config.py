import os
from dotenv import load_dotenv

load_dotenv()

# LINE 帳號設定
LINE_EMAIL = os.getenv('LINE_EMAIL')
LINE_PASSWORD = os.getenv('LINE_PASSWORD')

# 轉發設定
FORWARD_MODE = os.getenv('FORWARD_MODE', 'off').lower() == 'on'
TARGET_GROUP_ID = os.getenv('TARGET_GROUP_ID')
TARGET_USER_ID = os.getenv('TARGET_USER_ID')

# 觸發指令
FORWARD_COMMAND = '/forward'
STOP_COMMAND = '/stop'
STATUS_COMMAND = '/status'
SET_TARGET_COMMAND = '/target'

# 轉發設定
FORWARD_SETTINGS = {
    'text': True,
    'image': True,
    'sticker': True,
    'video': True,
    'audio': True,
}
