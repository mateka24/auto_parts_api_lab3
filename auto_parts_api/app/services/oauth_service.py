import httpx
from typing import Optional, Dict, Any
from app.config import settings


class YandexOAuthService:
    """
    Сервис для работы с Yandex ID OAuth 2.0.
    Реализует поток Authorization Code Grant.
    """
    
    AUTHORIZATION_URL = "https://oauth.yandex.ru/authorize"
    TOKEN_URL = "https://oauth.yandex.ru/token"
    USER_INFO_URL = "https://login.yandex.ru/info"
    
    def __init__(self):
        self.client_id = settings.YANDEX_CLIENT_ID
        self.client_secret = settings.YANDEX_CLIENT_SECRET
        self.callback_url = settings.YANDEX_CALLBACK_URL
    
    def get_authorization_url(self, state: str) -> str:
        """
        Генерация URL для редиректа пользователя на Yandex ID.
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "state": state,
            "scope": "login:email login:info login:default_phone"
        }
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.AUTHORIZATION_URL}?{query_string}"
    
    async def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Обмен кода авторизации на токен доступа.
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.callback_url
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о пользователе от Yandex.
        """
        headers = {
            "Authorization": f"OAuth {access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.USER_INFO_URL, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
    
    async def authenticate(self, code: str, state: str, expected_state: str) -> Optional[Dict[str, Any]]:
        """
        Полный процесс аутентификации через Yandex.
        1. Проверка state
        2. Обмен кода на токен
        3. Получение информации о пользователе
        """
        # Проверка state (защита от CSRF)
        if state != expected_state:
            return None
        
        # Обмен кода на токен
        token_data = await self.exchange_code_for_token(code)
        if not token_data:
            return None
        
        access_token = token_data.get("access_token")
        if not access_token:
            return None
        
        # Получение информации о пользователе
        user_info = await self.get_user_info(access_token)
        if not user_info:
            return None
        
        # Извлекаем телефон правильно - Яндекс возвращает его как объект {id, number}
        default_phone = user_info.get("default_phone")
        phone = None
        if isinstance(default_phone, dict):
            phone = default_phone.get("number")
        elif isinstance(default_phone, str):
            phone = default_phone
        
        return {
            "provider_id": str(user_info.get("id")),
            "email": user_info.get("default_email"),
            "phone": phone,  # Теперь это просто строка с номером или None
            "name": user_info.get("display_name"),
            "first_name": user_info.get("first_name"),
            "last_name": user_info.get("last_name")
        }


class VKOAuthService:
    """
    Сервис для работы с VK ID OAuth 2.0.
    """
    
    AUTHORIZATION_URL = "https://id.vk.com/authorize"
    TOKEN_URL = "https://id.vk.com/oauth2/auth"
    USER_INFO_URL = "https://id.vk.com/oauth2/user_info"
    
    def __init__(self):
        # Для VK нужно настроить отдельно
        self.client_id = ""  # settings.VK_CLIENT_ID
        self.client_secret = ""  # settings.VK_CLIENT_SECRET
        self.callback_url = ""  # settings.VK_CALLBACK_URL
    
    def get_authorization_url(self, state: str) -> str:
        """
        Генерация URL для редиректа пользователя на VK ID.
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "state": state,
            "scope": "email phone profile"
        }
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.AUTHORIZATION_URL}?{query_string}"
    
    async def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Обмен кода авторизации на токен доступа.
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.callback_url
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о пользователе от VK.
        """
        params = {
            "access_token": access_token
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.USER_INFO_URL, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
