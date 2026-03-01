"""
Notification Service for EdgeNVR
Supports Telegram bot notifications for security events
"""

import os
import requests
from typing import Optional
from datetime import datetime

from app.core.config import get_settings

settings = get_settings()


class NotificationService:
    """Send notifications for security events."""
    
    def __init__(self):
        self.telegram_enabled = bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)
        self.telegram_chat_id = settings.TELEGRAM_CHAT_ID
        self.telegram_bot_token = settings.TELEGRAM_BOT_TOKEN
        
        if self.telegram_enabled:
            print(f"📱 Telegram notifications enabled for chat {self.telegram_chat_id}")
        else:
            print("📱 Telegram notifications disabled (no config)")
    
    def send_telegram(self, message: str, photo_path: Optional[str] = None) -> bool:
        """Send message via Telegram."""
        if not self.telegram_enabled:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Telegram notification sent")
                return True
            else:
                print(f"❌ Telegram error: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Telegram notification failed: {e}")
            return False
    
    def send_photo_telegram(self, message: str, photo_path: str) -> bool:
        """Send photo with caption via Telegram."""
        if not self.telegram_enabled or not os.path.exists(photo_path):
            return self.send_telegram(message)
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendPhoto"
            with open(photo_path, 'rb') as photo:
                data = {
                    "chat_id": self.telegram_chat_id,
                    "caption": message,
                    "parse_mode": "HTML"
                }
                files = {"photo": photo}
                response = requests.post(url, data=data, files=files, timeout=30)
            
            if response.status_code == 200:
                return True
            else:
                print(f"❌ Telegram photo error: {response.text}")
                return self.send_telegram(message)
        except Exception as e:
            print(f"❌ Telegram photo failed: {e}")
            return self.send_telegram(message)
    
    def person_detected(self, camera_name: str, camera_id: str, 
                       confidence: float = None, snapshot_path: str = None):
        """Send person detection alert."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"🚨 <b>Person Detected</b>\n"
        message += f"📷 Camera: {camera_name}\n"
        message += f"⏰ Time: {timestamp}\n"
        
        if confidence:
            message += f"🎯 Confidence: {confidence:.1%}"
        
        if snapshot_path and os.path.exists(snapshot_path):
            return self.send_photo_telegram(message, snapshot_path)
        else:
            return self.send_telegram(message)
    
    def camera_offline(self, camera_name: str):
        """Send camera offline alert."""
        message = f"⚠️ <b>Camera Offline</b>\n"
        message += f"📷 {camera_name} is no longer responding"
        return self.send_telegram(message)
    
    def camera_online(self, camera_name: str):
        """Send camera back online notification."""
        message = f"✅ <b>Camera Online</b>\n"
        message += f"📷 {camera_name} is back online"
        return self.send_telegram(message)


# Global instance
notification_service = NotificationService()
