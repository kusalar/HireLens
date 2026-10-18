from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
import jwt
import bcrypt
from app.core.config import settings

def get_password_hash(password: str) -> str:
    """Hash password using direct bcrypt library."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

def create_access_token(
    subject: Union[str, Any],
    session_id: Optional[Union[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create signed JWT access token with UTC expiration and optional session tracking."""
    now_utc = datetime.now(timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "iat": now_utc,
        "sub": str(subject),
        "type": "access",
    }
    if session_id:
        to_encode["sid"] = str(session_id)
        
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(
    subject: Union[str, Any],
    session_id: Optional[Union[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create signed JWT refresh token with optional session tracking."""
    now_utc = datetime.now(timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "exp": expire,
        "iat": now_utc,
        "sub": str(subject),
        "type": "refresh",
    }
    if session_id:
        to_encode["sid"] = str(session_id)
        
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def get_fernet_suite():
    """Obtain initialized Fernet instance for OAuth token encryption."""
    from cryptography.fernet import Fernet
    import base64
    import hashlib

    raw_key = settings.TOKEN_ENCRYPTION_KEY
    if not raw_key:
        raw_key = settings.SECRET_KEY

    # Ensure key is a 32-byte url-safe base64 string
    try:
        # Check if already a valid Fernet key
        key_bytes = raw_key.encode("utf-8") if isinstance(raw_key, str) else raw_key
        # Test base64 decoding
        decoded = base64.urlsafe_b64decode(key_bytes)
        if len(decoded) == 32:
            return Fernet(key_bytes)
    except Exception:
        pass

    # Deterministically derive 32-byte key from secret using SHA-256
    derived = hashlib.sha256(raw_key.encode("utf-8")).digest()
    b64_key = base64.urlsafe_b64encode(derived)
    return Fernet(b64_key)


def encrypt_token(plain_token: Optional[str]) -> Optional[str]:
    """Encrypt OAuth token at rest using authenticated symmetric encryption (Fernet)."""
    if not plain_token:
        return None
    fernet = get_fernet_suite()
    encrypted = fernet.encrypt(plain_token.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_token(cipher_token: Optional[str]) -> Optional[str]:
    """Decrypt encrypted OAuth token in memory."""
    if not cipher_token:
        return None
    fernet = get_fernet_suite()
    decrypted = fernet.decrypt(cipher_token.encode("utf-8"))
    return decrypted.decode("utf-8")

