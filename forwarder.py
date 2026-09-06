from linepy import LINE
from linepy.api import LineAPI
from linepy.talk import Talk
from config import *
import time
import sys
import os

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
            elif self.forward_mode:
                # 轉發模式開啟時，轉發文字訊息
                self._forward_text_message(text, message, from_name)
        
        # 處理圖片訊息
        elif message.type == 2:
            if self.forward_mode:
                self._forward_image_message(message, from_name)
    
    def _handle_forward_command(self, message):
        """處��� /forward 指令 - 打開轉發模式"""
        self.forward_mode = True
        
        reply_text = "[轉發模式] 已啟動 ✓\n\n"
        reply_text += "• 現在群組中的訊息將被轉發\n"
        reply_text += "• 支持轉發: 文字、圖片\n"
        reply_text += "• 指令: /stop (停止轉發)\n"
        reply_text += "• 指令: /target @群組名稱 (設定轉發目標)\n"
        reply_text += "• 指令: /status (查看轉發狀態)\n"
        
        self.talk.sendMessage(message.to, reply_text, contentMetadata={})
        print(f"[✓] 轉發模式已啟動 - 群組: {self.get_group_name(message.to)}")
    
    def _handle_stop_command(self, message):
        """處理 /stop 指令 - 關閉轉發模式"""
        self.forward_mode = False
        self.talk.sendMessage(message.to, "[轉發模式] 已停止 ✗", contentMetadata={})
        print(f"[✓] 轉發模式已停止")
    
    def _handle_status_command(self, message):
        """處理 /status 指令 - 顯示狀態"""
        status = "開啟 ✓" if self.forward_mode else "關閉"
        target_info = "未設定"
        
        if self.target_group_id:
            target_info = f"群組: {self.get_group_name(self.target_group_id)}"
        
        reply_text = f"[轉發狀態]\n"
        reply_text += f"• 模式: {status}\n"
        reply_text += f"• 轉發目標: {target_info}\n"
        
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
    
    def _forward_text_message(self, text, message, from_name):
        """轉發文字訊息到目標"""
        if not self.target_group_id:
            return
        
        # 不轉發指令訊息
        if text.startswith('/'):
            return
        
        forward_text = f"[{from_name}]\n{text}"
        
        try:
            self.talk.sendMessage(self.target_group_id, forward_text, contentMetadata={})
            print(f"[→] 轉發文字: {forward_text[:50]}...")
        except Exception as e:
            print(f"[✗] 轉發文字失敗: {e}")
    
    def _forward_image_message(self, message, from_name):
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
