from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
import secrets

from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import RegisterRequest, LoginRequest
from app.utils.security import hash_password, verify_password, hash_token, verify_token
from app.utils.jwt import create_access_token, create_refresh_token, verify_token as verify_jwt, parse_expiration
from app.config import settings


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register(self, data: RegisterRequest) -> Optional[User]:
        """
        Регистрация нового пользователя.
        """
        # Проверка существования пользователя
        result = await self.db.execute(
            select(User).where(
                (User.email == data.email) & (User.deleted_at.is_(None))
            )
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            return None
        
        # Генерация соли и хеширование пароля
        salt = secrets.token_hex(16)
        password_hash = hash_password(data.password, salt)
        
        # Создание пользователя
        user = User(
            email=data.email,
            phone=data.phone,
            password_hash=password_hash,
            salt=salt
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def login(self, data: LoginRequest, user_agent: Optional[str] = None) -> Optional[Tuple[User, str, str]]:
        """
        Вход пользователя.
        Возвращает (user, access_token, refresh_token) или None.
        """
        # Поиск пользователя по email
        result = await self.db.execute(
            select(User).where(
                (User.email == data.email) & (User.deleted_at.is_(None))
            )
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.password_hash:
            return None
        
        # Проверка пароля
        if not verify_password(data.password, user.password_hash, user.salt):
            return None
        
        # Генерация токенов
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        
        # Хеширование refresh токена для хранения в БД
        refresh_token_hash = hash_token(refresh_token)
        
        # Получение времени истечения refresh токена
        expire_seconds = parse_expiration(settings.JWT_REFRESH_EXPIRATION)
        expires_at = datetime.utcnow() + timedelta(seconds=expire_seconds)
        
        # Сохранение refresh токена в БД
        token_record = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent
        )
        
        self.db.add(token_record)
        await self.db.commit()
        
        return (user, access_token, refresh_token)
    
    async def refresh_tokens(self, refresh_token: str, user_agent: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """
        Обновление пары токенов по refresh токену.
        Возвращает (new_access_token, new_refresh_token) или None.
        """
        # Проверка JWT токена
        payload = verify_jwt(refresh_token, token_type="refresh")
        if not payload:
            return None
        
        user_id = int(payload.get("sub"))
        
        # Поиск пользователя
        result = await self.db.execute(
            select(User).where(
                (User.id == user_id) & (User.deleted_at.is_(None))
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Поиск хеша токена в БД
        result = await self.db.execute(
            select(RefreshToken).where(
                (RefreshToken.user_id == user_id) &
                (RefreshToken.is_revoked == False) &
                (RefreshToken.expires_at > datetime.utcnow())
            )
        )
        token_records = result.scalars().all()
        
        # Проверка, есть ли такой токен в БД
        token_found = False
        token_to_revoke = None
        for record in token_records:
            if verify_token(refresh_token, record.token_hash):
                token_found = True
                token_to_revoke = record
                break
        
        if not token_found:
            return None
        
        # Генерация новых токенов
        new_access_token = create_access_token({"sub": str(user.id)})
        new_refresh_token = create_refresh_token({"sub": str(user.id)})
        
        # Отзыв старого токена
        token_to_revoke.is_revoked = True
        
        # Сохранение нового refresh токена
        new_token_hash = hash_token(new_refresh_token)
        expire_seconds = parse_expiration(settings.JWT_REFRESH_EXPIRATION)
        new_expires_at = datetime.utcnow() + timedelta(seconds=expire_seconds)
        
        new_token_record = RefreshToken(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
            user_agent=user_agent
        )
        
        self.db.add(new_token_record)
        await self.db.commit()
        
        return (new_access_token, new_refresh_token)
    
    async def logout(self, refresh_token: str, user_id: int) -> bool:
        """
        Завершение текущей сессии (отзыв токена).
        """
        # Поиск и отзыв токена
        result = await self.db.execute(
            select(RefreshToken).where(
                (RefreshToken.user_id == user_id) &
                (RefreshToken.is_revoked == False)
            )
        )
        token_records = result.scalars().all()
        
        for record in token_records:
            if verify_token(refresh_token, record.token_hash):
                record.is_revoked = True
                await self.db.commit()
                return True
        
        return False
    
    async def logout_all(self, user_id: int) -> int:
        """
        Завершение всех сессий пользователя.
        Возвращает количество отозванных токенов.
        """
        result = await self.db.execute(
            select(RefreshToken).where(
                (RefreshToken.user_id == user_id) &
                (RefreshToken.is_revoked == False)
            )
        )
        token_records = result.scalars().all()
        
        count = 0
        for record in token_records:
            record.is_revoked = True
            count += 1
        
        await self.db.commit()
        return count
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Получение пользователя по ID.
        """
        result = await self.db.execute(
            select(User).where(
                (User.id == user_id) & (User.deleted_at.is_(None))
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Получение пользователя по email.
        """
        result = await self.db.execute(
            select(User).where(
                (User.email == email) & (User.deleted_at.is_(None))
            )
        )
        return result.scalar_one_or_none()
    
    async def create_or_get_oauth_user(
        self,
        provider: str,
        provider_id: str,
        email: str,
        phone: Optional[str] = None
    ) -> User:
        """
        Создание или получение пользователя через OAuth.
        """
        # Поиск существующего пользователя
        user = None
        
        if provider == "yandex":
            result = await self.db.execute(
                select(User).where(
                    (User.yandex_id == provider_id) & (User.deleted_at.is_(None))
                )
            )
            user = result.scalar_one_or_none()
        elif provider == "vk":
            result = await self.db.execute(
                select(User).where(
                    (User.vk_id == provider_id) & (User.deleted_at.is_(None))
                )
            )
            user = result.scalar_one_or_none()
        
        if user:
            return user
        
        # Поиск по email
        result = await self.db.execute(
            select(User).where(
                (User.email == email) & (User.deleted_at.is_(None))
            )
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Привязка OAuth ID к существующему пользователю
            if provider == "yandex":
                user.yandex_id = provider_id
            elif provider == "vk":
                user.vk_id = provider_id
            await self.db.commit()
            await self.db.refresh(user)
            return user
        
        # Создание нового пользователя
        user = User(
            email=email,
            phone=phone
        )
        
        if provider == "yandex":
            user.yandex_id = provider_id
        elif provider == "vk":
            user.vk_id = provider_id
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def get_user_by_oauth_id(self, provider: str, provider_id: str) -> Optional[User]:
        """
        Получение пользователя по OAuth ID.
        """
        if provider == "yandex":
            result = await self.db.execute(
                select(User).where(
                    (User.yandex_id == provider_id) & (User.deleted_at.is_(None))
                )
            )
        elif provider == "vk":
            result = await self.db.execute(
                select(User).where(
                    (User.vk_id == provider_id) & (User.deleted_at.is_(None))
                )
            )
        else:
            return None
        
        return result.scalar_one_or_none()
