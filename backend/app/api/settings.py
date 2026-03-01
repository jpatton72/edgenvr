from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from app.services.notifications import notification_service
from app.core.config import get_settings, Settings

router = APIRouter(prefix="/api/settings", tags=["settings"])
settings = get_settings()


class TelegramConfig(BaseModel):
    bot_token: str
    chat_id: str


class SettingsUpdate(BaseModel):
    detection_threshold: Optional[float] = None
    detection_interval: Optional[int] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


@router.get("/notifications")
def get_notification_settings():
    """Get current notification settings."""
    return {
        "telegram_enabled": notification_service.telegram_enabled,
        "telegram_chat_id": settings.TELEGRAM_CHAT_ID if settings.TELEGRAM_CHAT_ID else None
    }


@router.post("/notifications/telegram")
def configure_telegram(config: TelegramConfig):
    """Configure Telegram bot for notifications."""
    # Validate token by making a test request
    try:
        import requests
        url = f"https://api.telegram.org/bot{config.bot_token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Invalid bot token")
        
        # Save to environment (for runtime, not persisted)
        os.environ["TELEGRAM_BOT_TOKEN"] = config.bot_token
        os.environ["TELEGRAM_CHAT_ID"] = config.chat_id
        
        # Reinitialize notification service
        notification_service.telegram_bot_token = config.bot_token
        notification_service.telegram_chat_id = config.chat_id
        notification_service.telegram_enabled = True
        
        return {"status": "success", "message": "Telegram configured successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to configure Telegram: {str(e)}")


@router.post("/notifications/test")
def test_notification():
    """Send a test notification."""
    success = notification_service.send_telegram(
        "🔔 Test notification from EdgeNVR\n"
        "If you're receiving this, Telegram alerts are working!"
    )
    
    if success:
        return {"status": "success", "message": "Test notification sent"}
    else:
        raise HTTPException(status_code=400, detail="Failed to send notification. Check Telegram configuration.")
