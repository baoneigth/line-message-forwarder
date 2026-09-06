from linepy import LINE
from linepy.api import LineAPI
from linepy.talk import Talk
from config import *
import time
import sys
import os
from datetime import datetime

class LineMessageForwarder:
    def __init__(self, target_groups=None):
        """初始化 LINE 轉發機器人
        
        Args:
            target_groups: 要監聽的群組 ID 列表，例如 ['C...xxx', 'C...yyy']
        """
        try:
            print("[*] 正在登入 LINE...")
            self.line = LINE(email=LINE_EMAIL, password=LINE_PASSWORD)
            self.talk = self.line.talk
            self.api = self.line.api
            print("[✓] LINE 登入成功")
        except Exception as e:
            print(f"[✗] 登入失敗: {e}")
            sys.exit(1)
        
        # 設定要監聽的群組列表
        self.target_groups = target_groups or []
        
        if not self.target_groups:
            print("[!] 警告: 未指定監聽群組，請傳入群組 ID 列表")
        
        # 每個群組的獨立設定
        # 格式: {group_id: {'forward_mode': bool, 'target_group_id': str, 'on_duty_user_id': str, 'on_duty_user_name': str}}
        self.group_settings = {}
        for group_id in self.target_groups:
            self.group_settings[group_id] = {
                'forward_mode': False,
                'target_group_id': None,
                'on_duty_user_id': None,
                'on_duty_user_name': None
            }
        
        # 訊息對應記錄 - 記錄轉發過的訊息
        # 格式: {source_group_id: {source_message_id: {'target_group_id': xxx, ...}}}
        self.forwarded_message_map = {}
        
        # 建立臨時資料夾用於存放圖片
        if not os.path.exists('temp_images'):
            os.makedirs('temp_images')
    
    def get_group_name(self, group_id):
        """取得群組名稱"""
        try:
            group = self.talk.getGroup(group_id)
            return group.name
        except:
            return "未知群組"
    
    def is_monitored_group(self, group_id):
        """檢查是否為監聽的群組"""
        return group_id in self.target_groups
    
    def handle_group_message(self, message, from_mid, from_name):
        """處理群組訊息 - 只處理群組消息，忽略私訊"""
        
        group_id = message.to
        
        # 檢查是否為監聽的群組
        if not self.is_monitored_group(group_id):
            return
        
        # 過濾私訊 - 只處理群組訊息
        if group_id == from_mid:
            return
        
        # 處理文字訊息
        if message.type == 1:
            text = message.text
            
            # 檢查是否為指令
            if text.startswith(FORWARD_COMMAND):
                self._handle_forward_command(message, group_id)
            elif text.startswith(STOP_COMMAND):
                self._handle_stop_command(message, group_id)
            elif text.startswith(STATUS_COMMAND):
                self._handle_status_command(message, group_id)
            elif text.startswith(SET_TARGET_COMMAND):
                self._handle_set_target_command(text, message, group_id)
            elif text.startswith(SET_ON_DUTY_COMMAND):
                self._handle_set_on_duty_command(message, group_id, from_mid, from_name)
            elif text.startswith(RECALL_COMMAND):
                self._handle_recall_command(message, group_id)
            elif self.group_settings[group_id]['forward_mode']:
                # 轉發模式開啟時，轉發文字訊息
                # 檢查當班限制
                on_duty_user_id = self.group_settings[group_id]['on_duty_user_id']
                if on_duty_user_id and from_mid != on_duty_user_id:
                    # 當班人員已設定，且發言者不是當班人員 - 不轉發
                    return
                
                self._forward_text_message(text, message, from_name, group_id)
        
        # 處理圖片訊息
        elif message.type == 2:
            if self.group_settings[group_id]['forward_mode']:
                # 檢查當班限制
                on_duty_user_id = self.group_settings[group_id]['on_duty_user_id']
                if on_duty_user_id and from_mid != on_duty_user_id:
                    return
                
                self._forward_image_message(message, from_name, group_id)
    
    def _handle_forward_command(self, message, group_id):
        """處理 /forward 指令 - 打開轉發模式"""
        self.group_settings[group_id]['forward_mode'] = True
        
        reply_text = "[轉發模式] 已啟動 ✓\n\n"
        reply_text += "• 現在群組中的訊息將被轉發\n"
        reply_text += "• 支持轉發: 文字、圖片\n"
        reply_text += "• 指令: /stop (停止轉發)\n"
        reply_text += "• 指令: /target @群組名稱 (設定轉發目標)\n"
        reply_text += "• 指令: /status (查看轉發狀態)\n"
        reply_text += "• 指令: /duty @名稱 (設定當班人員)\n"
        reply_text += "• 回收訊息: 長按轉發訊息→回覆→輸入 /recall\n"
        
        self.talk.sendMessage(group_id, reply_text, contentMetadata={})
        print(f"[✓] 轉發模式已啟動 - 群組: {self.get_group_name(group_id)}")
    
    def _handle_stop_command(self, message, group_id):
        """處理 /stop 指令 - 關閉轉發模式"""
        self.group_settings[group_id]['forward_mode'] = False
        self.group_settings[group_id]['on_duty_user_id'] = None
        self.group_settings[group_id]['on_duty_user_name'] = None
        self.talk.sendMessage(group_id, "[轉發模式] 已停止 ✗", contentMetadata={})
        print(f"[✓] 轉發模式已停止 - 群組: {self.get_group_name(group_id)}")
    
    def _handle_status_command(self, message, group_id):
        """處理 /status 指令 - 顯示狀態"""
        settings = self.group_settings[group_id]
        
        status = "開啟 ✓" if settings['forward_mode'] else "關閉"
        target_info = "未設定"
        on_duty_info = "未設定"
        
        if settings['target_group_id']:
            target_info = f"群組: {self.get_group_name(settings['target_group_id'])}"
        
        if settings['on_duty_user_name']:
            on_duty_info = f"當班: {settings['on_duty_user_name']}"
        
        reply_text = f"[轉發狀態]\n"
        reply_text += f"• 模式: {status}\n"
        reply_text += f"• 轉發目標: {target_info}\n"
        reply_text += f"• {on_duty_info}\n"
        
        self.talk.sendMessage(group_id, reply_text, contentMetadata={})
    
    def _handle_set_target_command(self, text, message, group_id):
        """處理 /target 指令 - 設定轉發目標"""
        parts = text.split(' ', 1)
        if len(parts) < 2:
            self.talk.sendMessage(group_id, "[錯誤] 用法: /target @群組名稱", contentMetadata={})
            return
        
        # 設定當前群組為轉發目標
        self.group_settings[group_id]['target_group_id'] = group_id
        
        target_name = self.get_group_name(group_id)
        reply_text = f"[✓] 轉發目標已設定為: {target_name}"
        self.talk.sendMessage(group_id, reply_text, contentMetadata={})
    
    def _handle_set_on_duty_command(self, message, group_id, from_mid, from_name):
        """處理 /duty 指令 - 設定當班人員"""
        text = message.text
        parts = text.split(' ', 1)
        
        if len(parts) < 2:
            self.talk.sendMessage(group_id, "[錯誤] 用法: /duty @發言人名稱", contentMetadata={})
            return
        
        target_name = parts[1].strip().replace('@', '')
        
        try:
            # 取得群組成員列表
            group = self.talk.getGroup(group_id)
            
            # 搜尋符合的成員
            found_user = None
            for member_id in group.members:
                contact = self.talk.getContact(member_id)
                if contact.displayName == target_name or contact.displayName.lower() == target_name.lower():
                    found_user = (member_id, contact.displayName)
                    break
            
            if found_user:
                self.group_settings[group_id]['on_duty_user_id'] = found_user[0]
                self.group_settings[group_id]['on_duty_user_name'] = found_user[1]
                reply_text = f"[✓] 當班人員已設定為: {found_user[1]}\n只有當班人員的訊息會被轉發"
                self.talk.sendMessage(group_id, reply_text, contentMetadata={})
                print(f"[✓] 當班人員設定: {found_user[1]} - 群組: {self.get_group_name(group_id)}")
            else:
                reply_text = f"[錯誤] 找不到群組成員: {target_name}"
                self.talk.sendMessage(group_id, reply_text, contentMetadata={})
        except Exception as e:
            self.talk.sendMessage(group_id, f"[錯誤] 設定當班人員失敗: {e}", contentMetadata={})
    
    def _handle_recall_command(self, message, group_id):
        """處理 /recall 指令 - 回收被回覆的轉發訊息"""
        try:
            # 嘗試獲取被回覆的訊息
            quoted_message = getattr(message, 'quotedMessage', None)
            
            if not quoted_message:
                self.talk.sendMessage(group_id, "[錯誤] 請回覆要回收的訊息後輸入 /recall", contentMetadata={})
                return
            
            # 獲取被回覆訊息的 ID
            quoted_message_id = quoted_message.id
            
            # 檢查被回覆的訊息是否在轉發記錄中
            if group_id not in self.forwarded_message_map:
                self.talk.sendMessage(group_id, "[提示] 該訊息未被記錄", contentMetadata={})
                return
            
            if quoted_message_id not in self.forwarded_message_map[group_id]:
                self.talk.sendMessage(group_id, "[提示] 該訊息不是轉發訊息", contentMetadata={})
                return
            
            # 獲取目標群組的訊息 ID
            target_info = self.forwarded_message_map[group_id][quoted_message_id]
            target_group_id = target_info['target_group_id']
            target_message_id = target_info['target_message_id']
            
            # 嘗試刪除目標群組中的轉發訊息
            try:
                self.talk.deleteMessage(target_message_id)
                
                # 發送回收確認訊息
                self.talk.sendMessage(group_id, "[✓] 訊息已回收", contentMetadata={})
                self.talk.sendMessage(target_group_id, "[✗] 轉發訊息已被回收", contentMetadata={})
                
                # 移除記錄
                del self.forwarded_message_map[group_id][quoted_message_id]
                
                print(f"[✓] 訊息已回收 - 群組: {self.get_group_name(group_id)}")
            except Exception as e:
                # 如果刪除失敗，發送替代訊息
                self.talk.sendMessage(target_group_id, "[訊息已被回收]", contentMetadata={})
                self.talk.sendMessage(group_id, "[✓] 訊息回收請求已發送", contentMetadata={})
                print(f"[!] 訊息回收: {e}")
                
                # 移除記錄
                del self.forwarded_message_map[group_id][quoted_message_id]
        
        except Exception as e:
            print(f"[✗] 回收訊息錯誤: {e}")
            self.talk.sendMessage(group_id, f"[錯誤] 回收訊息失敗: {e}", contentMetadata={})
    
    def _forward_text_message(self, text, message, from_name, source_group_id):
        """轉發文字訊息到目標"""
        target_group_id = self.group_settings[source_group_id]['target_group_id']
        
        if not target_group_id:
            return
        
        # 不轉發指令訊息
        if text.startswith('/'):
            return
        
        forward_text = f"[{from_name}]\n{text}"
        
        try:
            self.talk.sendMessage(target_group_id, forward_text, contentMetadata={})
            
            # 記錄轉發訊息對應關係
            if source_group_id not in self.forwarded_message_map:
                self.forwarded_message_map[source_group_id] = {}
            
            self.forwarded_message_map[source_group_id][message.id] = {
                'target_group_id': target_group_id,
                'target_message_id': message.id,
                'timestamp': datetime.now().timestamp(),
                'type': 'text'
            }
            
            print(f"[→] 轉發文字: {forward_text[:50]}... | 來源: {self.get_group_name(source_group_id)}")
        except Exception as e:
            print(f"[✗] 轉發文字失敗: {e}")
    
    def _forward_image_message(self, message, from_name, source_group_id):
        """轉發圖片訊息到目標"""
        target_group_id = self.group_settings[source_group_id]['target_group_id']
        
        if not target_group_id:
            return
        
        try:
            # 下載圖片
            image_data = self.talk.downloadObjectById(message.id)
            
            if image_data:
                # 建立臨時檔名
                temp_image_path = f"temp_images/{message.id}.jpg"
                
                # 儲存圖片到臨時資料夾
                with open(temp_image_path, 'wb') as f:
                    f.write(image_data)
                
                # 發送圖片到目標群組
                self.talk.sendImage(target_group_id, temp_image_path)
                
                # 記錄轉發訊息對應關係
                if source_group_id not in self.forwarded_message_map:
                    self.forwarded_message_map[source_group_id] = {}
                
                self.forwarded_message_map[source_group_id][message.id] = {
                    'target_group_id': target_group_id,
                    'target_message_id': message.id,
                    'timestamp': datetime.now().timestamp(),
                    'type': 'image'
                }
                
                # 刪除臨時檔案
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                
                print(f"[→] 轉發圖片 - 來自: {from_name} | 群組: {self.get_group_name(source_group_id)}")
        except Exception as e:
            print(f"[✗] 轉發圖片失敗: {e}")
    
    def start(self):
        """啟動訊息監聽 - 只監聽指定的群組"""
        print("\n[*] 開始監聽群組訊息...")
        print(f"[*] 監聽群組數: {len(self.target_groups)}")
        for group_id in self.target_groups:
            print(f"   • {self.get_group_name(group_id)} ({group_id})")
        
        print("\n[*] 可用指令:")
        print("   • /forward - 啟動轉發模式")
        print("   • /stop - 停止轉發模式")
        print("   • /status - 查看轉發狀態")
        print("   • /target - 設定轉發目標")
        print("   • /duty @名稱 - 設定當班人員")
        print("   • /recall - 回收訊息（在回覆訊息時輸入）")
        print("\n[*] 支持轉發: 文字、圖片")
        print("[*] 按 Ctrl+C 退出\n")
        
        while True:
            try:
                for message in self.talk.fetchOps(self.talk.poll()):
                    try:
                        self._process_message(message)
                    except Exception as e:
                        print(f"[✗] 處理訊息錯誤: {e}")
                
                time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n[*] 已退出")
                break
            except Exception as e:
                print(f"[✗] 監聽錯誤: {e}")
                time.sleep(1)
    
    def _process_message(self, op):
        """處理訊息操作"""
        if op.type == 25:  # 訊息類型
            message = op.message
            from_mid = message.from_
            
            try:
                contact = self.talk.getContact(from_mid)
                from_name = contact.displayName
            except:
                from_name = "未知用戶"
            
            # 處理群組訊息
            self.handle_group_message(message, from_mid, from_name)

def main():
    # 在這裡指定要監聽的群組 ID
    # 例如: ['C0abc123...', 'C0def456...', ...]
    target_groups = [
        # 請在此處添加您要監聽的群組 ID
        # 'C0abc123...',
        # 'C0def456...',
    ]
    
    if not target_groups:
        print("[!] 錯誤: 請在 main() 函數中指定要監聽的群組 ID")
        print("[*] 使用方式:")
        print("    target_groups = ['C0abc123...', 'C0def456...', ...]")
        sys.exit(1)
    
    forwarder = LineMessageForwarder(target_groups=target_groups)
    forwarder.start()

if __name__ == '__main__':
    main()
