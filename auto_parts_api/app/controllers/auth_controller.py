import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import require_auth
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
    WhoamiResponse,
)
from app.services.auth_service import AuthService
from app.services.oauth_service import YandexOAuthService
from app.utils.jwt import parse_expiration


router = APIRouter(prefix="/auth", tags=["Authentication"])


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=parse_expiration(settings.JWT_ACCESS_EXPIRATION),
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=parse_expiration(settings.JWT_REFRESH_EXPIRATION),
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.register(data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует",
        )

    return {"message": "Пользователь успешно зарегистрирован", "user": UserResponse.model_validate(user)}


@router.post("/login")
async def login(
    data: LoginRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    result = await service.login(data, request.headers.get("user-agent"))

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    user, access_token, refresh_token = result
    set_auth_cookies(response, access_token, refresh_token)
    return {"message": "Успешный вход", "user": UserResponse.model_validate(user)}


@router.post("/refresh")
async def refresh_tokens(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh токен не найден",
        )

    result = await service.refresh_tokens(refresh_token, request.headers.get("user-agent"))
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истекший refresh токен",
        )

    new_access_token, new_refresh_token = result
    set_auth_cookies(response, new_access_token, new_refresh_token)
    return {"message": "Токены успешно обновлены"}


@router.get("/whoami", response_model=WhoamiResponse)
async def whoami(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = require_auth(request)
    service = AuthService(db)
    user = await service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    return WhoamiResponse(authenticated=True, user=UserResponse.model_validate(user))


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user_id = require_auth(request)
    service = AuthService(db)

    await service.logout(
        refresh_token=request.cookies.get("refresh_token"),
        access_token=request.cookies.get("access_token"),
        user_id=user_id,
    )
    clear_auth_cookies(response)
    return {"message": "Выход выполнен успешно"}


@router.post("/logout-all")
async def logout_all(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user_id = require_auth(request)
    service = AuthService(db)
    count = await service.logout_all(user_id)
    clear_auth_cookies(response)
    return {"message": f"Все сессии ({count}) завершены"}


@router.get("/oauth/{provider}")
async def oauth_initiate(provider: str):
    if provider not in ["yandex", "vk"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый OAuth провайдер: {provider}",
        )

    state = secrets.token_urlsafe(32)

    if provider == "yandex":
        oauth_service = YandexOAuthService()
        auth_url = oauth_service.get_authorization_url(state)
        response = RedirectResponse(url=auth_url, status_code=302)
        response.set_cookie(
            key="oauth_state",
            value=state,
            max_age=300,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return response

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="VK OAuth еще не настроен",
    )


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    if provider != "yandex":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый OAuth провайдер: {provider}",
        )

    expected_state = request.cookies.get("oauth_state")
    if not expected_state or not state or state != expected_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невалидный state параметр. Возможна CSRF атака.",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код авторизации не получен",
        )

    oauth_service = YandexOAuthService()
    user_data = await oauth_service.authenticate(code, state, expected_state)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка аутентификации через Yandex",
        )

    service = AuthService(db)
    user = await service.create_or_get_oauth_user(
        provider=provider,
        provider_id=user_data["provider_id"],
        email=user_data["email"],
        phone=user_data.get("phone"),
    )
    access_token, refresh_token = await service.create_session_tokens(
        user.id,
        request.headers.get("user-agent"),
    )

    response = RedirectResponse(url="/", status_code=302)
    set_auth_cookies(response, access_token, refresh_token)
    response.delete_cookie(key="oauth_state", path="/")
    return response


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    reset_token = await service.create_password_reset_token(data.email)

    response = {
        "message": "Если пользователь существует, инструкция по сбросу пароля сформирована",
    }
    if reset_token:
        response["reset_token"] = reset_token
    return response


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    success = await service.reset_password(data.token, data.new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невалидный или истекший токен сброса пароля",
        )

    return {"message": "Пароль успешно изменен"}
