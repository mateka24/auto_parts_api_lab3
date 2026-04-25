from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta
import secrets

from app.database import get_db
from app.services.auth_service import AuthService
from app.services.oauth_service import YandexOAuthService
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    WhoamiResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest
)
from app.middleware.auth import require_auth, get_current_user_id
from app.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    max_age_access: int = 900,  # 15 минут
    max_age_refresh: int = 604800  # 7 дней
):
    """
    Установка HttpOnly cookies с токенами.
    """
    # Access token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=max_age_access,
        httponly=True,
        secure=False,  # True для HTTPS
        samesite="lax",
        path="/"
    )
    
    # Refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=max_age_refresh,
        httponly=True,
        secure=False,  # True для HTTPS
        samesite="lax",
        path="/"
    )


def clear_auth_cookies(response: Response):
    """
    Очистка cookies с токенами.
    """
    response.delete_cookie(
        key="access_token",
        path="/"
    )
    response.delete_cookie(
        key="refresh_token",
        path="/"
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Регистрация нового пользователя.
    """
    service = AuthService(db)
    
    user = await service.register(data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    return {"message": "Пользователь успешно зарегистрирован", "user": UserResponse.model_validate(user)}


@router.post("/login")
async def login(
    data: LoginRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Вход пользователя (установка cookies).
    """
    service = AuthService(db)
    user_agent = request.headers.get("user-agent")
    
    result = await service.login(data, user_agent)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    user, access_token, refresh_token = result
    
    # Установка cookies
    set_auth_cookies(response, access_token, refresh_token)
    
    return {"message": "Успешный вход", "user": UserResponse.model_validate(user)}


@router.post("/refresh")
async def refresh_tokens(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление пары токенов по refresh токену.
    """
    service = AuthService(db)
    user_agent = request.headers.get("user-agent")
    
    # Получаем refresh токен из cookies
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh токен не найден"
        )
    
    result = await service.refresh_tokens(refresh_token, user_agent)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истёкший refresh токен"
        )
    
    new_access_token, new_refresh_token = result
    
    # Установка новых cookies
    set_auth_cookies(response, new_access_token, new_refresh_token)
    
    return {"message": "Токены успешно обновлены"}


@router.get("/whoami", response_model=WhoamiResponse)
async def whoami(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Проверка статуса авторизации и получение данных пользователя.
    """
    user_id = get_current_user_id(request)
    
    if not user_id:
        return WhoamiResponse(authenticated=False, user=None)
    
    service = AuthService(db)
    user = await service.get_user_by_id(user_id)
    
    if not user:
        return WhoamiResponse(authenticated=False, user=None)
    
    return WhoamiResponse(
        authenticated=True,
        user=UserResponse.model_validate(user)
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Завершение текущей сессии.
    """
    service = AuthService(db)
    
    # Получаем токены из cookies
    refresh_token = request.cookies.get("refresh_token")
    user_id = get_current_user_id(request)
    
    if not user_id or not refresh_token:
        clear_auth_cookies(response)
        return {"message": "Выход выполнен"}
    
    # Отзыв токена
    await service.logout(refresh_token, user_id)
    
    # Очистка cookies
    clear_auth_cookies(response)
    
    return {"message": "Выход выполнен успешно"}


@router.post("/logout-all")
async def logout_all(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Завершение всех сессий пользователя.
    """
    user_id = require_auth(request)
    service = AuthService(db)
    
    # Отзыв всех токенов
    count = await service.logout_all(user_id)
    
    # Очистка cookies
    clear_auth_cookies(response)
    
    return {"message": f"Все сессии ({count}) завершены"}


# --- OAuth endpoints ---

@router.get("/oauth/{provider}")
async def oauth_initiate(
    provider: str,
    request: Request
):
    """
    Инициация входа через OAuth провайдера.
    """
    if provider not in ["yandex", "vk"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый OAuth провайдер: {provider}"
        )
    
    # Генерация state для защиты от CSRF
    state = secrets.token_urlsafe(32)
    
    if provider == "yandex":
        oauth_service = YandexOAuthService()
        auth_url = oauth_service.get_authorization_url(state)
        response = RedirectResponse(url=auth_url, status_code=302)
        
        # Установка cookie с state на финальный response
        response.set_cookie(
            key="oauth_state",
            value=state,
            max_age=300,  # 5 минут
            httponly=True,
            samesite="lax"
        )
        return response
    
    elif provider == "vk":
        # VK пока не настроен
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="VK OAuth ещё не настроен"
        )


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Обработка ответа от OAuth провайдера.
    """
    if provider != "yandex":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый OAuth провайдер: {provider}"
        )
    
    # Получаем ожидаемый state из cookies
    expected_state = request.cookies.get("oauth_state")
    
    if not expected_state or not state or state != expected_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невалидный state параметр. Возможна CSRF атака."
        )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код авторизации не получен"
        )
    
    # Аутентификация через Yandex
    oauth_service = YandexOAuthService()
    user_data = await oauth_service.authenticate(code, state, expected_state)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка аутентификации через Yandex"
        )
    
    # Создание или получение пользователя
    service = AuthService(db)
    # Было (строка 321):
    user = await service.create_or_get_oauth_user(
    provider=provider,
    provider_id=user_data["provider_id"],
    email=user_data["email"],
    phone=user_data.get("phone")  # ← возвращает словарь!
    )
    
    # Генерация токенов
    from app.utils.jwt import create_access_token, create_refresh_token, parse_expiration
    from app.utils.security import hash_token
    from app.models.refresh_token import RefreshToken
    from datetime import datetime, timedelta
    
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Сохранение refresh токена в БД
    refresh_token_hash = hash_token(refresh_token)
    expire_seconds = parse_expiration(settings.JWT_REFRESH_EXPIRATION)
    expires_at = datetime.utcnow() + timedelta(seconds=expire_seconds)
    
    token_record = RefreshToken(
        user_id=user.id,
        token_hash=refresh_token_hash,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent")
    )
    
    db.add(token_record)
    await db.commit()
    
    # Установка cookies и редирект на главную
    response = RedirectResponse(url="/", status_code=302)
    set_auth_cookies(response, access_token, refresh_token)
    
    # Очистка oauth_state cookie
    response.delete_cookie(key="oauth_state")
    
    return response


# --- Password reset endpoints (упрощённая реализация) ---

@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Запрос на сброс пароля.
    В реальной реализации здесь должна быть отправка email с токеном.
    """
    # Для учебных целей просто возвращаем успех
    # В продакшене: генерируем токен, сохраняем в БД, отправляем email
    return {"message": "Если пользователь существует, инструкция отправлена на email"}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Установка нового пароля по токену.
    """
    # Для учебных целей просто возвращаем успех
    # В продакшене: проверяем токен, обновляем пароль в БД
    return {"message": "Пароль успешно изменён"}
