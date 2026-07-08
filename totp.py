import hmac
import hashlib
import struct
import time
import base64
import urllib.parse
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class TOTPAccount:
    id: str
    name: str
    issuer: str
    secret: str
    digits: int = 6
    period: int = 30
    algorithm: str = "SHA1"
    card_mode: bool = False

    @property
    def label(self) -> str:
        if self.issuer:
            return f"{self.issuer} ({self.name})"
        return self.name


class TOTPGenerator:
    @staticmethod
    def _base32_decode(secret: str) -> bytes:
        secret = secret.upper().replace(" ", "").replace("-", "")
        padding = (8 - len(secret) % 8) % 8
        secret += "=" * padding
        return base64.b32decode(secret)

    @staticmethod
    def _hotp(key: bytes, counter: int, digits: int = 6, algorithm: str = "SHA1") -> str:
        counter_bytes = struct.pack(">Q", counter)
        
        if algorithm == "SHA1":
            hash_func = hashlib.sha1
        elif algorithm == "SHA256":
            hash_func = hashlib.sha256
        elif algorithm == "SHA512":
            hash_func = hashlib.sha512
        else:
            hash_func = hashlib.sha1

        hmac_result = hmac.new(key, counter_bytes, hash_func).digest()
        offset = hmac_result[-1] & 0x0F
        binary = struct.unpack(">I", hmac_result[offset:offset + 4])[0] & 0x7FFFFFFF
        otp = binary % (10 ** digits)
        return str(otp).zfill(digits)

    @classmethod
    def generate(cls, account: TOTPAccount, at_time: Optional[float] = None) -> str:
        if at_time is None:
            at_time = time.time()
        
        key = cls._base32_decode(account.secret)
        counter = int(at_time) // account.period
        return cls._hotp(key, counter, account.digits, account.algorithm)

    @staticmethod
    def time_remaining(period: int = 30, at_time: Optional[float] = None) -> int:
        if at_time is None:
            at_time = time.time()
        return period - (int(at_time) % period)

    @staticmethod
    def progress(period: int = 30, at_time: Optional[float] = None) -> float:
        if at_time is None:
            at_time = time.time()
        return (int(at_time) % period) / period

    @staticmethod
    def format_code(code: str) -> str:
        if len(code) == 6:
            return f"{code[:3]} {code[3:]}"
        elif len(code) == 8:
            return f"{code[:4]} {code[4:]}"
        return code

    @staticmethod
    def validate_secret(secret: str) -> bool:
        try:
            secret = secret.upper().replace(" ", "").replace("-", "")
            padding = (8 - len(secret) % 8) % 8
            secret += "=" * padding
            base64.b32decode(secret)
            return True
        except Exception:
            return False

    @staticmethod
    def generate_secret(length: int = 32) -> str:
        import secrets
        random_bytes = secrets.token_bytes(length)
        return base64.b32encode(random_bytes).decode("utf-8").rstrip("=")

    @staticmethod
    def parse_otpauth_url(url: str) -> Optional[Dict]:
        """Parse an otpauth:// URL and return account info dict.

        Supported format: otpauth://totp/[label]?secret=...&issuer=...&digits=6&period=30&algorithm=SHA1
        Returns dict with keys: name, issuer, secret, digits, period, algorithm
        """
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme != "otpauth":
                return None
            if parsed.netloc not in ("totp", "hotp"):
                return None

            params = urllib.parse.parse_qs(parsed.query)
            secret = params.get("secret", [""])[0].strip().upper()
            if not secret:
                return None

            # Label format: "issuer:account" or just "account"
            path = parsed.path.lstrip("/")
            path = urllib.parse.unquote(path)
            name = path
            issuer = ""
            if ":" in path:
                parts = path.split(":", 1)
                issuer = parts[0].strip()
                name = parts[1].strip()

            # Issuer from query param takes precedence
            if "issuer" in params:
                issuer = params["issuer"][0].strip()

            digits = int(params.get("digits", ["6"])[0])
            period = int(params.get("period", ["30"])[0])
            algorithm = params.get("algorithm", ["SHA1"])[0].upper()
            if algorithm not in ("SHA1", "SHA256", "SHA512"):
                algorithm = "SHA1"

            return {
                "name": name,
                "issuer": issuer,
                "secret": secret,
                "digits": digits,
                "period": period,
                "algorithm": algorithm,
            }
        except Exception:
            return None

    @staticmethod
    def generate_otpauth_url(account: TOTPAccount) -> str:
        """Generate an otpauth:// URL from a TOTP account."""
        label = urllib.parse.quote(account.name)
        if account.issuer:
            label = urllib.parse.quote(account.issuer) + ":" + label

        params = {
            "secret": account.secret,
            "issuer": account.issuer or "",
            "digits": str(account.digits),
            "period": str(account.period),
            "algorithm": account.algorithm,
        }
        # Remove empty issuer
        if not params["issuer"]:
            del params["issuer"]

        query = urllib.parse.urlencode(params)
        return f"otpauth://totp/{label}?{query}"
