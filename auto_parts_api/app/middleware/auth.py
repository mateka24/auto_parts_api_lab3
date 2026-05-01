from typing import Optional

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import async_session_maker
from app.services.auth_service import AuthService
from app.utils.jwt import verify_token


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        access_token = request.cookies.get("access_token")

        request.state.user = None
        request.state.user_id = None

        if access_token:
            payload = verify_token(access_token, token_type="access")
            if payload:
                user_id = payload.get("sub")
                if user_id:
                    async with async_session_maker() as session:
                        service = AuthService(session)
                        is_active = await service.is_access_token_active(access_token, int(user_id))
                        if is_active:
                            request.state.user_id = int(user_id)
                            request.state.user = payload

        response = await call_next(request)
        return response


def get_current_user_id(request: Request) -> Optional[int]:
    return getattr(request.state, "user_id", None)


def require_auth(request: Request) -> int:
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация",
        )
    return user_id
