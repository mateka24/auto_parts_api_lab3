from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
import re


# --- Для регистрации ---
class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя")
    phone: Optional[str] = Field(None, description="Телефон пользователя")
    password: str = Field(..., min_length=8, description="Пароль (минимум 8 символов)")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not re.search(r'\d', v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v


# --- Для входа ---
class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., description="Пароль")


# --- Для обновления токена ---
class RefreshTokenRequest(BaseModel):
    pass  # Токен берётся из cookies


# --- Для сброса пароля ---
class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Email для сброса пароля")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Токен сброса пароля")
    new_password: str = Field(..., min_length=8, description="Новый пароль")
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not re.search(r'\d', v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v


# --- Ответ: профиль пользователя ---
class UserResponse(BaseModel):
    id: int
    email: str
    phone: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# --- Ответ для whoami ---
class WhoamiResponse(BaseModel):
    authenticated: bool
    user: Optional[UserResponse] = None
