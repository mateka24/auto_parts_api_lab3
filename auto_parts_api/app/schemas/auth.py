import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


PHONE_PATTERN = re.compile(r"^\+?[1-9]\d{10,14}$")


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя")
    phone: Optional[str] = Field(None, description="Телефон пользователя")
    password: str = Field(..., min_length=8, description="Пароль")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not PHONE_PATTERN.match(value):
            raise ValueError("Телефон должен быть в международном формате, например +79991234567")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not re.search(r"[a-z]", value):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")
        if not re.search(r"\d", value):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        return value


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., description="Пароль")


class RefreshTokenRequest(BaseModel):
    pass


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Email для сброса пароля")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Токен сброса пароля")
    new_password: str = Field(..., min_length=8, description="Новый пароль")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not re.search(r"[a-z]", value):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")
        if not re.search(r"\d", value):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        return value


class UserResponse(BaseModel):
    id: int
    email: str
    phone: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WhoamiResponse(BaseModel):
    authenticated: bool
    user: Optional[UserResponse] = None
