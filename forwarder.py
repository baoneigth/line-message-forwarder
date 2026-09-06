from linepy import LINE
from linepy.api import LineAPI
from linepy.talk import Talk
from config import *
import time
import sys

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
        self.target_user_id = None
        self.message_buffer = None  # 暫存要轉發的訊息
    
    def get_group_name(self, group_id):
        """取得群組名稱"""
        try:
            group = self.talk.getGroup(group_id)
            return group.name
        except:
            return "未知群組"
    
    def get_user_name(self, user_id):
        """取得用戶名稱"""
        try:
            contact = self.talk.getContact(user_id)
            return contact.displayName
        except:
            return "未知用戶"
    
    def handle_text_message(self, message, from_mid, from_name):
        """處理文字訊息"""
        text = message.text
        
        # 檢查是否為指令
        if text.startswith(FORWARD_COMMAND):
            self._handle_forward_command(message, from_mid)
        elif text.startswith(STOP_COMMAND):
            self._handle_stop_command()
        elif text.startswith(STATUS_COMMAND):
            self._handle_status_command(message)
        elif text.startswith(SET_TARGET_COMMAND):
            self._handle_set_target_command(text, message)
        elif self.forward_mode:
            # 轉發模式開啟時，轉發訊息
            self._forward_message(text, message, from_name)
    
    def _handle_forward_command(self, message, from_mid):
        """處理 /forward 指令 - 打開轉發模式"""
        self.forward_mode = True
        self.message_buffer = None
        
        reply_text = "[轉發模式] 已啟動 ✓\n\n"
        reply_text += "• 現在群組中的訊息將被轉發\n"
        reply_text += "• 指令: /stop (停止轉發)\n"
        reply_text += "• 指令: /target @群組名稱或@用戶名稱 (設定轉發目標)\n"
        reply_text += "• 指令: /status (查看轉發狀態)\n"
        
        self.talk.sendMessage(message.to, reply_text, contentMetadata={})
        print(f"[✓] 轉發模式已啟動")
    
    def _handle_stop_command(self):
        """處理 /stop 指令 - 關閉轉發模式"""
        self.forward_mode = False
        print(f"[✓] 轉發模式已停止")
    
    def _handle_status_command(self, message):
        """處理 /status 指令 - 顯示狀態"""
        status = "開啟 ✓" if self.forward_mode else "關閉"
        target_info = "未設定"
        
        if self.target_group_id:
            target_info = f"群組: {self.get_group_name(self.target_group_id)}"
        elif self.target_user_id:
            target_info = f"用戶: {self.get_user_name(self.target_user_id)}"
        
        reply_text = f"[轉發狀態]\n"
        reply_text += f"• 模式: {status}\n"
        reply_text += f"• 轉發目標: {target_info}\n"
        
        self.talk.sendMessage(message.to, reply_text, contentMetadata={})
    
    def _handle_set_target_command(self, text, message):
        """處理 /target 指令 - 設定轉發目標"""
        parts = text.split(' ', 1)
        if len(parts) < 2:
            self.talk.sendMessage(message.to, "[錯誤] 用法: /target @群組名稱 或 /target @用戶名稱", contentMetadata={})
            return
        
        # 在實務中，這需要解析群組/用戶名稱
        # 這裡簡化為直接使用 message.to (當前群組)
        self.target_group_id = message.to
        
        target_name = self.get_group_name(self.target_group_id)
        reply_text = f"[✓] 轉發目標已設定為: {target_name}"
        self.talk.sendMessage(message.to, reply_text, contentMetadata={})
    
    def _forward_message(self, text, message, from_name):
        """轉發文字訊息到目標"""
        if not self.target_group_id and not self.target_user_id:
            return
        
        target_id = self.target_group_id or self.target_user_id
        forward_text = f"[{from_name}]\n{text}"
        
        try:
            self.talk.sendMessage(target_id, forward_text, contentMetadata={})
            print(f"[→] 轉發訊息: {forward_text[:50]}...")
        except Exception as e:
            print(f"[✗] 轉發失敗: {e}")
    
    def handle_image_message(self, message, from_name):
        """處理圖片訊息"""
        if not self.forward_mode or (not self.target_group_id and not self.target_user_id):
            return
        
        try:
            target_id = self.target_group_id or self.target_user_id
            image_data = self.talk.downloadObjectById(message.id)
            
            # 準備圖片訊息
            self.talk.sendMessage(
                target_id,
                text=f"[{from_name}] 傳送了圖片",
                contentMetadata={}
            )
            print(f"[→] 轉發圖片")
        except Exception as e:
            print(f"[✗] 轉發圖片失敗: {e}")
    
    def handle_sticker_message(self, message, from_name):
        """處理貼圖訊息"""
        if not self.forward_mode or (not self.target_group_id and not self.target_user_id):
            return
        
        try:
            target_id = self.target_group_id or self.target_user_id
            # 轉發貼圖
            self.talk.sendMessage(
                target_id,
                text=f"[{from_name}] 傳送了貼圖",
                contentMetadata={}
            )
            print(f"[→] 轉發貼圖")
        except Exception as e:
            print(f"[✗] 轉發貼圖失敗: {e}")
    
    def start(self):
        """啟動訊息監聽"""
        print("\n[*] 開始監聽訊息...")
        print("[*] 可用指令:")
        print("   • /forward - 啟動轉發模式")
        print("   • /stop - 停止轉發模式")
        print("   • /status - 查看轉發狀態")
        print("   • /target - 設定轉發目標")
        print("\n[*] 按 Ctrl+C 退出\n")
        
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
            
            # 根據訊息類型處理
            if message.type == 1:  # 文字訊息
                self.handle_text_message(message, from_mid, from_name)
            elif message.type == 2:  # 圖片訊息
                self.handle_image_message(message, from_name)
            elif message.type == 7:  # 貼圖訊息
                self.handle_sticker_message(message, from_name)

def main():
    forwarder = LineMessageForwarder()
    forwarder.start()

if __name__ == '__main__':
    main()
