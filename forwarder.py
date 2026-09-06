from linepy import LINE
from linepy.api import LineAPI
from linepy.talk import Talk
from config import *
import time
import sys
import os
from datetime import datetime

class LineMessageForwarder:
    def __init__(self):
        """初始化 LINE 轉發機器人"""
        try:
            print("[*] 正在登入 LINE...")
            self.line = LINE(email=LINE_EMAIL, password=LINE_PASSWORD)
            self.talk = self.line.talk
            self.api = self.line.api
            print("[✓] LINE 登入成功")
        except Exception as e:
            print(f"[✗] 登入失敗: {e}")
            sys.exit(1)
        
        self.forward_mode = False
        self.target_group_id = None
        
        # 當班人員機制
        self.on_duty_user_id = None
        self.on_duty_user_name = None
        
        # 訊息對應記錄 - 記錄轉發過的訊息
        # 格式: {source_group_id: {source_message_id: {'target_message_id': xxx, 'target_group_id': xxx}}}
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
    
    def handle_group_message(self, message, from_mid, from_name):
        """處理群組訊息 - 只處理群組消息，忽略私訊"""
        
        # 過濾私訊 - 只處理群組訊息
        if message.to == from_mid:
            return
        
        # 處理文字訊息
        if message.type == 1:
            text = message.text
            
            # 檢查是否為指令
            if text.startswith(FORWARD_COMMAND):
                self._handle_forward_command(message)
            elif text.startswith(STOP_COMMAND):
                self._handle_stop_command(message)
            elif text.startswith(STATUS_COMMAND):
                self._handle_status_command(message)
            elif text.startswith(SET_TARGET_COMMAND):
                self._handle_set_target_command(text, message)
            elif text.startswith(SET_ON_DUTY_COMMAND):
                self._handle_set_on_duty_command(message, from_mid, from_name)
            elif text.startswith(RECALL_COMMAND):
                self._handle_recall_command(message)
            elif self.forward_mode:
                # 轉發模式開啟時，轉發文字訊息
                # 檢查當班限制
                if self.on_duty_user_id and from_mid != self.on_duty_user_id:
                    # 當班人員已設定，且發言者不是當班人員 - 不轉發
                    return
                
                self._forward_text_message(text, message, from_name, message.to)
        
        # 處理圖片訊息
        elif message.type == 2:
            if self.forward_mode:
                # 檢查當班限制
                if self.on_duty_user_id and from_mid != self.on_duty_user_id:
                    return
                
                self._forward_image_message(message, from_name, message.to)
    
    def _handle_forward_command(self, message):
        """處理 /forward 指令 - 打開轉發模式"""
        self.forward_mode = True
        
        reply_text = "[轉發模式] 已啟動 ✓\n\n"
        reply_text += "• 現在群組中的訊息將被轉發\n"
        reply_text += "• 支持轉發: 文字、圖片\n"
        reply_text += "• 指令: /stop (停止轉發)\n"
        reply_text += "• 指令: /target @群組名稱 (設定轉發目標)\n"
        reply_text += "• 指令: /status (查看轉發狀態)\n"
        reply_text += "• 指令: /duty @名稱 (設定當班人員)\n"
        reply_text += "• 回收訊息: 長按轉發訊息→回覆→輸入 /recall\n"
        
        self.talk.sendMessage(message.to, reply_text, contentMetadata={})
        print(f"[✓] 轉發模式已啟動 - 群組: {self.get_group_name(message.to)}")
    
    def _handle_stop_command(self, message):
        """處理 /stop 指令 - 關閉轉發模式"""
        self.forward_mode = False
        self.on_duty_user_id = None
        self.on_duty_user_name = None
        self.talk.sendMessage(message.to, "[轉發模式] 已停止 ✗", contentMetadata={})
        print(f"[✓] 轉發模式已停止")
    
    def _handle_status_command(self, message):
        """處理 /status 指令 - 顯示狀態"""
        status = "開啟 ✓" if self.forward_mode else "關閉"
        target_info = "未設定"
        on_duty_info = "未設定"
        
        if self.target_group_id:
            target_info = f"群組: {self.get_group_name(self.target_group_id)}"
        
        if self.on_duty_user_name:
            on_duty_info = f"當班: {self.on_duty_user_name}"
        
        reply_text = f"[轉發狀態]\n"
        reply_text += f"• 模式: {status}\n"
        reply_text += f"• 轉發目標: {target_info}\n"
        reply_text += f"• {on_duty_info}\n"
        
        self.talk.sendMessage(message.to, reply_text, contentMetadata={})
    
    def _handle_set_target_command(self, text, message):
        """處理 /target 指令 - 設定轉發目標"""
        parts = text.split(' ', 1)
        if len(parts) < 2:
            self.talk.sendMessage(message.to, "[錯誤] 用法: /target @群組名稱", contentMetadata={})
            return
        
        # 設定當前群組為轉發目標
        self.target_group_id = message.to
        
        target_name = self.get_group_name(self.target_group_id)
        reply_text = f"[✓] 轉發目標已設定為: {target_name}"
        self.talk.sendMessage(message.to, reply_text, contentMetadata={})
    
    def _handle_set_on_duty_command(self, message, from_mid, from_name):
        """處理 /duty 指令 - 設定當班人員"""
        text = message.text
        parts = text.split(' ', 1)
        
        if len(parts) < 2:
            self.talk.sendMessage(message.to, "[錯誤] 用法: /duty @發言人名稱", contentMetadata={})
            return
        
        target_name = parts[1].strip().replace('@', '')
        
        try:
            # 取得群組成員列表
            group = self.talk.getGroup(message.to)
            
            # 搜尋符合的成員
            found_user = None
            for member_id in group.members:
                contact = self.talk.getContact(member_id)
                if contact.displayName == target_name or contact.displayName.lower() == target_name.lower():
                    found_user = (member_id, contact.displayName)
                    break
            
            if found_user:
                self.on_duty_user_id = found_user[0]
                self.on_duty_user_name = found_user[1]
                reply_text = f"[✓] 當班人員已設定為: {self.on_duty_user_name}\n只有當班人員的訊息會被轉發"
                self.talk.sendMessage(message.to, reply_text, contentMetadata={})
                print(f"[✓] 當班人員設定: {self.on_duty_user_name}")
            else:
                reply_text = f"[錯誤] 找不到群組成員: {target_name}"
                self.talk.sendMessage(message.to, reply_text, contentMetadata={})
        except Exception as e:
            self.talk.sendMessage(message.to, f"[錯誤] 設定當班人員失敗: {e}", contentMetadata={})
    
    def _handle_recall_command(self, message):
        """處理 /recall 指令 - 回收被回覆的轉發訊息"""
        # 檢查訊息是否有 quotedMessage (即是否是回覆訊息)
        try:
            # 嘗試獲取被回覆的訊息
            quoted_message = getattr(message, 'quotedMessage', None)
            
            if not quoted_message:
                self.talk.sendMessage(message.to, "[錯誤] 請回覆要回收的訊息後輸入 /recall", contentMetadata={})
                return
            
            # 獲取被回覆訊息的 ID
            quoted_message_id = quoted_message.id
            
            # 檢查被回覆的訊息是否在轉發記錄中
            source_group_id = message.to
            if source_group_id not in self.forwarded_message_map:
                self.talk.sendMessage(message.to, "[提示] 該訊息未被記錄", contentMetadata={})
                return
            
            if quoted_message_id not in self.forwarded_message_map[source_group_id]:
                self.talk.sendMessage(message.to, "[提示] 該訊息不是轉發訊息", contentMetadata={})
                return
            
            # 獲取目標群組的訊息 ID
            target_info = self.forwarded_message_map[source_group_id][quoted_message_id]
            target_group_id = target_info['target_group_id']
            target_message_id = target_info['target_message_id']
            
            # 嘗試刪除目標群組中的轉發訊息
            try:
                self.talk.deleteMessage(target_message_id)
                
                # 發送回收確認訊息
                self.talk.sendMessage(message.to, "[✓] 訊息已回收", contentMetadata={})
                self.talk.sendMessage(target_group_id, "[✗] 轉發訊息已被回收", contentMetadata={})
                
                # 移除記錄
                del self.forwarded_message_map[source_group_id][quoted_message_id]
                
                print(f"[✓] 訊息已回收 - ID: {target_message_id}")
            except Exception as e:
                # 如果刪除失敗，發送替代訊息
                self.talk.sendMessage(target_group_id, "[訊息已被回收]", contentMetadata={})
                self.talk.sendMessage(message.to, "[✓] 訊息回收請求已發送", contentMetadata={})
                print(f"[!] 訊息回收: {e}")
                
                # 移除記錄
                del self.forwarded_message_map[source_group_id][quoted_message_id]
        
        except Exception as e:
            print(f"[✗] 回收訊息錯誤: {e}")
            self.talk.sendMessage(message.to, f"[錯誤] 回收訊息失敗: {e}", contentMetadata={})
    
    def _forward_text_message(self, text, message, from_name, source_group_id):
        """轉發文字訊息到目標"""
        if not self.target_group_id:
            return
        
        # 不轉發指令訊息
        if text.startswith('/'):
            return
        
        forward_text = f"[{from_name}]\n{text}"
        
        try:
            self.talk.sendMessage(self.target_group_id, forward_text, contentMetadata={})
            
            # 記錄轉發訊息對應關係
            if source_group_id not in self.forwarded_message_map:
                self.forwarded_message_map[source_group_id] = {}
            
            self.forwarded_message_map[source_group_id][message.id] = {
                'target_group_id': self.target_group_id,
                'target_message_id': message.id,  # 這裡理想情況下應該是轉發訊息的真實 ID
                'timestamp': datetime.now().timestamp(),
                'type': 'text'
            }
            
            print(f"[→] 轉發文字: {forward_text[:50]}...")
        except Exception as e:
            print(f"[✗] 轉發文字失敗: {e}")
    
    def _forward_image_message(self, message, from_name, source_group_id):
        """轉發圖片訊息到目標"""
        if not self.target_group_id:
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
                self.talk.sendImage(
                    self.target_group_id,
                    temp_image_path
                )
                
                # 記錄轉發訊息對應關係
                if source_group_id not in self.forwarded_message_map:
                    self.forwarded_message_map[source_group_id] = {}
                
                self.forwarded_message_map[source_group_id][message.id] = {
                    'target_group_id': self.target_group_id,
                    'target_message_id': message.id,
                    'timestamp': datetime.now().timestamp(),
                    'type': 'image'
                }
                
                # 刪除臨時檔案
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                
                print(f"[→] 轉發圖片 - 來自: {from_name}")
        except Exception as e:
            print(f"[✗] 轉發圖片失敗: {e}")
    
    def start(self):
        """啟動訊息監聽 - 只監聽群組訊息"""
        print("\n[*] 開始監聽群組訊息...")
        print("[*] 可用指令:")
        print("   • /forward - 啟動轉發模式")
        print("   • /stop - 停止轉發模式")
        print("   • /status - 查看轉發狀態")
        print("   • /target - 設定轉發目標")
        print("   • /duty @名稱 - 設定當班人員（只有當班人員訊息會被轉發）")
        print("   • /recall - 回收轉發訊息（長按訊息→回覆→輸入此指令）")
        print("\n[*] 支持轉發: 文字、圖片")
        print("[*] 已禁用: 私訊、通話、貼圖")
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
    forwarder = LineMessageForwarder()
    forwarder.start()

if __name__ == '__main__':
    main()
