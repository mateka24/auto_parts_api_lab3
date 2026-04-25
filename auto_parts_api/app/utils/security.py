import bcrypt
import secrets
import hashlib


def generate_salt() -> str:
    """Генерация уникальной соли для каждого пароля."""
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    """
    Хеширование пароля с использованием соли.
    Соль объединяется с паролем и хешируется через bcrypt.
    """
    # Объединяем пароль с солью и хешируем
    salted_password = (password + salt).encode('utf-8')
    hashed = bcrypt.hashpw(salted_password, bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """
    Проверка пароля путём сравнения хешей.
    """
    salted_password = (password + salt).encode('utf-8')
    hash_bytes = password_hash.encode('utf-8')
    
    return bcrypt.checkpw(salted_password, hash_bytes)


def hash_token(token: str) -> str:
    """
    Хеширование токена для хранения в БД.
    Сначала хешируем через SHA256 для уменьшения длины, затем bcrypt.
    """
    # SHA256 хеш для уменьшения длины токена до 64 байт
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    hashed = bcrypt.hashpw(token_hash.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_token(token: str, token_hash: str) -> bool:
    """
    Проверка токена по хешу.
    """
    token_hash_computed = hashlib.sha256(token.encode('utf-8')).hexdigest()
    hash_bytes = token_hash.encode('utf-8')
    
    return bcrypt.checkpw(token_hash_computed.encode('utf-8'), hash_bytes)
