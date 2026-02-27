from cryptography.fernet import Fernet
import base64
import hashlib
import os


class SecurityManager:
    def __init__(self, secret_key: str = None):
        if secret_key is None:
            secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
        key = hashlib.sha256(secret_key.encode()).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key[:32]))
    
    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()


_security_manager = None


def get_security_manager() -> SecurityManager:
    global _security_manager
    if _security_manager is None:
        from app.core.config import get_settings
        settings = get_settings()
        _security_manager = SecurityManager(settings.SECRET_KEY)
    return _security_manager
