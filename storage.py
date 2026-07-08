import json
import os
import base64
import hashlib
from pathlib import Path
from typing import List, Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from totp import TOTPAccount


class SecureStorage:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(Path.home(), ".rintotp")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "accounts.enc"
        self.salt_file = self.data_dir / "salt"
        self._fernet: Optional[Fernet] = None
        self._password_hash: Optional[str] = None

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))

    def _hash_password(self, password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            100000
        ).hex()

    def has_password(self) -> bool:
        return self.salt_file.exists() and self.data_file.exists()

    def set_password(self, password: str) -> None:
        salt = os.urandom(16)
        with open(self.salt_file, "wb") as f:
            f.write(salt)
        
        key = self._derive_key(password, salt)
        self._fernet = Fernet(key)
        self._password_hash = self._hash_password(password, salt)
        
        if not self.data_file.exists():
            self._save_accounts([])

    def verify_password(self, password: str) -> bool:
        if not self.salt_file.exists():
            return False
        
        with open(self.salt_file, "rb") as f:
            salt = f.read()
        
        key = self._derive_key(password, salt)
        self._fernet = Fernet(key)
        self._password_hash = self._hash_password(password, salt)
        
        try:
            self.load_accounts()
            return True
        except InvalidToken:
            self._fernet = None
            self._password_hash = None
            return False

    def change_password(self, old_password: str, new_password: str) -> bool:
        if not self.verify_password(old_password):
            return False
        
        accounts = self.load_accounts()
        
        salt = os.urandom(16)
        with open(self.salt_file, "wb") as f:
            f.write(salt)
        
        key = self._derive_key(new_password, salt)
        self._fernet = Fernet(key)
        self._password_hash = self._hash_password(new_password, salt)
        
        self._save_accounts(accounts)
        return True

    def _save_accounts(self, accounts: List[TOTPAccount]) -> None:
        if self._fernet is None:
            raise RuntimeError("Not authenticated")
        
        data = []
        for acc in accounts:
            data.append({
                "id": acc.id,
                "name": acc.name,
                "issuer": acc.issuer,
                "secret": acc.secret,
                "digits": acc.digits,
                "period": acc.period,
                "algorithm": acc.algorithm,
                "card_mode": acc.card_mode,
            })
        
        json_data = json.dumps(data, ensure_ascii=False).encode("utf-8")
        encrypted = self._fernet.encrypt(json_data)
        
        with open(self.data_file, "wb") as f:
            f.write(encrypted)

    def load_accounts(self) -> List[TOTPAccount]:
        if self._fernet is None:
            raise RuntimeError("Not authenticated")
        
        if not self.data_file.exists():
            return []
        
        with open(self.data_file, "rb") as f:
            encrypted = f.read()
        
        json_data = self._fernet.decrypt(encrypted)
        data = json.loads(json_data.decode("utf-8"))
        
        accounts = []
        for item in data:
            accounts.append(TOTPAccount(
                id=item["id"],
                name=item["name"],
                issuer=item.get("issuer", ""),
                secret=item["secret"],
                digits=item.get("digits", 6),
                period=item.get("period", 30),
                algorithm=item.get("algorithm", "SHA1"),
                card_mode=item.get("card_mode", False),
            ))
        
        return accounts

    def save_accounts(self, accounts: List[TOTPAccount]) -> None:
        self._save_accounts(accounts)

    def export_data(self, password: str) -> Optional[str]:
        if not self.verify_password(password):
            return None
        accounts = self.load_accounts()
        data = []
        for acc in accounts:
            data.append({
                "name": acc.name,
                "issuer": acc.issuer,
                "secret": acc.secret,
                "digits": acc.digits,
                "period": acc.period,
                "algorithm": acc.algorithm,
                "card_mode": acc.card_mode,
            })
        return json.dumps(data, ensure_ascii=False, indent=2)

    def import_data(self, json_str: str) -> bool:
        if self._fernet is None:
            return False
        try:
            data = json.loads(json_str)
            accounts = self.load_accounts()
            existing_ids = {acc.id for acc in accounts}
            
            import uuid
            for item in data:
                new_id = str(uuid.uuid4())
                while new_id in existing_ids:
                    new_id = str(uuid.uuid4())
                    existing_ids.add(new_id)
                
                accounts.append(TOTPAccount(
                    id=new_id,
                    name=item.get("name", "Unknown"),
                    issuer=item.get("issuer", ""),
                    secret=item["secret"],
                    digits=item.get("digits", 6),
                    period=item.get("period", 30),
                    algorithm=item.get("algorithm", "SHA1"),
                    card_mode=item.get("card_mode", False),
                ))
            
            self._save_accounts(accounts)
            return True
        except Exception:
            return False

    def is_locked(self) -> bool:
        return self._fernet is None

    def lock(self) -> None:
        self._fernet = None
        self._password_hash = None
