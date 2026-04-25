from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import jwt

from app.utils.jwt import verify_token
from app.config import settings


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware для проверки JWT токена из cookies.
    Добавляет текущего пользователя в request.state.user если токен валиден.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Получаем токен из cookies
        access_token = request.cookies.get("access_token")
        
        request.state.user = None
        request.state.user_id = None
        
        if access_token:
            # Проверка токена
            payload = verify_token(access_token, token_type="access")
            
            if payload:
                user_id = payload.get("sub")
                if user_id:
                    request.state.user_id = int(user_id)
                    request.state.user = payload
        
        # Продолжаем обработку запроса
        response = await call_next(request)
        
        return response


def get_current_user_id(request: Request) -> Optional[int]:
    """
    Получение ID текущего пользователя из request.state.
    """
    return getattr(request.state, "user_id", None)


def require_auth(request: Request) -> int:
    """
    Требует аутентификации. Выбрасывает 401 если пользователь не авторизован.
    """
    user_id = get_current_user_id(request)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация"
        )
    
    return user_id
