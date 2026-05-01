import bcrypt
import hashlib
import secrets


def generate_salt() -> str:
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    salted_password = (password + salt).encode("utf-8")
    hashed = bcrypt.hashpw(salted_password, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    salted_password = (password + salt).encode("utf-8")
    hash_bytes = password_hash.encode("utf-8")
    return bcrypt.checkpw(salted_password, hash_bytes)


def get_token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_token(token: str) -> str:
    token_digest = get_token_digest(token)
    hashed = bcrypt.hashpw(token_digest.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_token(token: str, token_hash: str) -> bool:
    token_digest = get_token_digest(token)
    hash_bytes = token_hash.encode("utf-8")
    return bcrypt.checkpw(token_digest.encode("utf-8"), hash_bytes)
