from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.access_token import AccessToken
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.utils.jwt import create_access_token, create_refresh_token, parse_expiration, verify_token as verify_jwt
from app.utils.security import (
    generate_salt,
    get_token_digest,
    hash_password,
    hash_token,
    verify_password,
    verify_token,
)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: RegisterRequest) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(
                (User.email == data.email) & (User.deleted_at.is_(None))
            )
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return None

        salt = generate_salt()
        password_hash = hash_password(data.password, salt)

        user = User(
            email=data.email,
            phone=data.phone,
            password_hash=password_hash,
            salt=salt,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(self, data: LoginRequest, user_agent: Optional[str] = None) -> Optional[Tuple[User, str, str]]:
        result = await self.db.execute(
            select(User).where(
                (User.email == data.email) & (User.deleted_at.is_(None))
            )
        )
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            return None

        if not verify_password(data.password, user.password_hash, user.salt):
            return None

        access_token, refresh_token = await self.create_session_tokens(user.id, user_agent)
        return user, access_token, refresh_token

    async def create_session_tokens(self, user_id: int, user_agent: Optional[str] = None) -> Tuple[str, str]:
        access_token = create_access_token({"sub": str(user_id)})
        refresh_token = create_refresh_token({"sub": str(user_id)})

        self.db.add(
            AccessToken(
                user_id=user_id,
                token_digest=get_token_digest(access_token),
                token_hash=hash_token(access_token),
                expires_at=self._build_expiration(settings.JWT_ACCESS_EXPIRATION),
                user_agent=user_agent,
            )
        )
        self.db.add(
            RefreshToken(
                user_id=user_id,
                token_digest=get_token_digest(refresh_token),
                token_hash=hash_token(refresh_token),
                expires_at=self._build_expiration(settings.JWT_REFRESH_EXPIRATION),
                user_agent=user_agent,
            )
        )

        await self.db.commit()
        return access_token, refresh_token

    async def refresh_tokens(self, refresh_token: str, user_agent: Optional[str] = None) -> Optional[Tuple[str, str]]:
        payload = verify_jwt(refresh_token, token_type="refresh")
        if not payload:
            return None

        user_id = int(payload.get("sub"))
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        token_record = await self._get_valid_refresh_token_record(refresh_token, user_id)
        if not token_record:
            return None

        token_record.is_revoked = True
        new_access_token, new_refresh_token = await self.create_session_tokens(user.id, user_agent)
        return new_access_token, new_refresh_token

    async def is_access_token_active(self, access_token: str, user_id: int) -> bool:
        token_record = await self._get_valid_access_token_record(access_token, user_id)
        return token_record is not None

    async def logout(self, refresh_token: Optional[str], access_token: Optional[str], user_id: int) -> bool:
        revoked_any = False

        if refresh_token:
            refresh_record = await self._get_valid_refresh_token_record(refresh_token, user_id)
            if refresh_record:
                refresh_record.is_revoked = True
                revoked_any = True

        if access_token:
            access_record = await self._get_valid_access_token_record(access_token, user_id)
            if access_record:
                access_record.is_revoked = True
                revoked_any = True

        if revoked_any:
            await self.db.commit()

        return revoked_any

    async def logout_all(self, user_id: int) -> int:
        count = 0
        now = datetime.utcnow()

        refresh_result = await self.db.execute(
            select(RefreshToken).where(
                (RefreshToken.user_id == user_id)
                & (RefreshToken.is_revoked == False)
                & (RefreshToken.expires_at > now)
            )
        )
        for record in refresh_result.scalars().all():
            record.is_revoked = True
            count += 1

        access_result = await self.db.execute(
            select(AccessToken).where(
                (AccessToken.user_id == user_id)
                & (AccessToken.is_revoked == False)
                & (AccessToken.expires_at > now)
            )
        )
        for record in access_result.scalars().all():
            record.is_revoked = True
            count += 1

        await self.db.commit()
        return count

    async def create_password_reset_token(self, email: str) -> Optional[str]:
        user = await self.get_user_by_email(email)
        if not user:
            return None

        result = await self.db.execute(
            select(PasswordResetToken).where(
                (PasswordResetToken.user_id == user.id)
                & (PasswordResetToken.is_used == False)
                & (PasswordResetToken.expires_at > datetime.utcnow())
            )
        )
        for record in result.scalars().all():
            record.is_used = True

        raw_token = generate_salt() + generate_salt()
        self.db.add(
            PasswordResetToken(
                user_id=user.id,
                token_digest=get_token_digest(raw_token),
                token_hash=hash_token(raw_token),
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
        )
        await self.db.commit()
        return raw_token

    async def reset_password(self, token: str, new_password: str) -> bool:
        token_record = await self._get_valid_password_reset_record(token)
        if not token_record:
            return False

        result = await self.db.execute(
            select(User).where(
                (User.id == token_record.user_id) & (User.deleted_at.is_(None))
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            return False

        salt = generate_salt()
        user.salt = salt
        user.password_hash = hash_password(new_password, salt)
        token_record.is_used = True

        await self._revoke_all_user_sessions(user.id)
        await self.db.commit()
        return True

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(
                (User.id == user_id) & (User.deleted_at.is_(None))
            )
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
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
        phone: Optional[str] = None,
    ) -> User:
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

        result = await self.db.execute(
            select(User).where(
                (User.email == email) & (User.deleted_at.is_(None))
            )
        )
        user = result.scalar_one_or_none()

        if user:
            if provider == "yandex":
                user.yandex_id = provider_id
            elif provider == "vk":
                user.vk_id = provider_id
            await self.db.commit()
            await self.db.refresh(user)
            return user

        user = User(
            email=email,
            phone=phone,
        )

        if provider == "yandex":
            user.yandex_id = provider_id
        elif provider == "vk":
            user.vk_id = provider_id

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    def _build_expiration(self, expiration_setting: str) -> datetime:
        expire_seconds = parse_expiration(expiration_setting)
        return datetime.utcnow() + timedelta(seconds=expire_seconds)

    async def _get_valid_refresh_token_record(self, refresh_token: str, user_id: int) -> Optional[RefreshToken]:
        return await self._get_valid_token_record(
            model=RefreshToken,
            token=refresh_token,
            user_id=user_id,
            revoked_field="is_revoked",
        )

    async def _get_valid_access_token_record(self, access_token: str, user_id: int) -> Optional[AccessToken]:
        return await self._get_valid_token_record(
            model=AccessToken,
            token=access_token,
            user_id=user_id,
            revoked_field="is_revoked",
        )

    async def _get_valid_password_reset_record(self, token: str) -> Optional[PasswordResetToken]:
        return await self._get_valid_token_record(
            model=PasswordResetToken,
            token=token,
            user_id=None,
            revoked_field="is_used",
        )

    async def _get_valid_token_record(self, model, token: str, user_id: Optional[int], revoked_field: str):
        conditions = [
            getattr(model, revoked_field) == False,
            model.expires_at > datetime.utcnow(),
        ]
        if user_id is not None:
            conditions.append(model.user_id == user_id)

        digest = get_token_digest(token)
        result = await self.db.execute(
            select(model).where(
                *conditions,
                model.token_digest == digest,
            )
        )
        record = result.scalar_one_or_none()

        if record and verify_token(token, record.token_hash):
            return record

        fallback_result = await self.db.execute(select(model).where(*conditions))
        for fallback_record in fallback_result.scalars().all():
            if verify_token(token, fallback_record.token_hash):
                return fallback_record

        return None

    async def _revoke_all_user_sessions(self, user_id: int) -> None:
        now = datetime.utcnow()

        refresh_result = await self.db.execute(
            select(RefreshToken).where(
                (RefreshToken.user_id == user_id)
                & (RefreshToken.is_revoked == False)
                & (RefreshToken.expires_at > now)
            )
        )
        for record in refresh_result.scalars().all():
            record.is_revoked = True

        access_result = await self.db.execute(
            select(AccessToken).where(
                (AccessToken.user_id == user_id)
                & (AccessToken.is_revoked == False)
                & (AccessToken.expires_at > now)
            )
        )
        for record in access_result.scalars().all():
            record.is_revoked = True
