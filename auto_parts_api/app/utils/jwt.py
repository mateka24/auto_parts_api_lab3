import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.config import settings


def parse_expiration(expiration_str: str) -> int:
    """
    Парсинг строки времени жизни токена (например, '15m', '7d') в секунды.
    """
    unit = expiration_str[-1].lower()
    value = int(expiration_str[:-1])
    
    if unit == 's':
        return value
    elif unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400
    else:
        raise ValueError(f"Неизвестная единица времени: {unit}")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание Access JWT токена.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire_seconds = parse_expiration(settings.JWT_ACCESS_EXPIRATION)
        expire = datetime.utcnow() + timedelta(seconds=expire_seconds)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_ACCESS_SECRET,
        algorithm="HS256"
    )
    
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание Refresh JWT токена.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire_seconds = parse_expiration(settings.JWT_REFRESH_EXPIRATION)
        expire = datetime.utcnow() + timedelta(seconds=expire_seconds)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_REFRESH_SECRET,
        algorithm="HS256"
    )
    
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Проверка и декодирование JWT токена.
    Возвращает payload токена или None если токен невалиден.
    """
    try:
        secret = settings.JWT_ACCESS_SECRET if token_type == "access" else settings.JWT_REFRESH_SECRET
        
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"]
        )
        
        if payload.get("type") != token_type:
            return None
        
        return payload
        
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_expiration(token: str) -> Optional[datetime]:
    """
    Получение времени истечения токена.
    """
    try:
        # Декодируем без проверки подписи (только для получения exp)
        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            return datetime.fromtimestamp(exp_timestamp)
    except jwt.InvalidTokenError:
        pass
    
    return None
