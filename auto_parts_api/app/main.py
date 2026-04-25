from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.controllers.part_controller import router as parts_router
from app.controllers.auth_controller import router as auth_router
from app.middleware.auth import AuthMiddleware

# Создаём приложение
app = FastAPI(
    title="Auto Parts API",
    description="API для управления запчастями с аутентификацией (JWT, OAuth)",
    version="3.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware (проверка JWT токенов)
app.add_middleware(AuthMiddleware)

# Подключаем роутеры
app.include_router(auth_router)  # Auth endpoints (префикс /auth уже в роутере)
app.include_router(parts_router, prefix="/api/v1")  # Parts endpoints


@app.get("/")
async def root():
    return {
        "message": "Auto Parts API v3.0 with Authentication",
        "docs": "/docs",
        "auth": "/auth/whoami"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Кастомная Swagger UI страница
@app.get("/docs", response_class=HTMLResponse)
async def custom_docs():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>Auto Parts API - Swagger UI</title>
    <meta charset="utf-8"/>
    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css">
    <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png"/>
    <style>
        .auto-fill-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
            font-size: 12px;
            display: inline-block;
        }
        .auto-fill-btn:hover { background: #45a049; }
        .auto-fill-info {
            background: #e3f2fd;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            font-size: 13px;
            border-left: 4px solid #2196F3;
        }
        .auto-fill-error {
            background: #ffebee;
            border-left-color: #f44336;
        }
        .part-preview {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .auth-status {
            background: #fff3cd;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            font-size: 13px;
            border-left: 4px solid #ffc107;
        }
        .auth-status.authenticated {
            background: #d4edda;
            border-left-color: #28a745;
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
    <script>
        const ui = SwaggerUIBundle({
            url: '/openapi.json',
            dom_id: '#swagger-ui',
            layout: 'BaseLayout',
            deepLinking: true,
            showExtensions: true,
            showCommonExtensions: true,
            tryItOutEnabled: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset
            ],
            onComplete: function() {
                console.log('Swagger UI loaded!');
                
                // Добавляем индикатор статуса аутентификации
                function updateAuthStatus() {
                    const hasAuthCookie = document.cookie.split(';').some(c => c.trim().startsWith('access_token='));
                    
                    const topBar = document.querySelector('.topbar');
                    if (topBar) {
                        let statusDiv = document.querySelector('.auth-status-indicator');
                        if (!statusDiv) {
                            statusDiv = document.createElement('div');
                            statusDiv.className = 'auth-status-indicator';
                            statusDiv.style.cssText = 'position: fixed; top: 10px; right: 10px; z-index: 9999;';
                            topBar.parentNode.insertBefore(statusDiv, topBar.nextSibling);
                        }
                        
                        if (hasAuthCookie) {
                            statusDiv.innerHTML = '<div class="auth-status authenticated">✅ Авторизован</div>';
                        } else {
                            statusDiv.innerHTML = '<div class="auth-status">⚠️ Не авторизован</div>';
                        }
                    }
                }
                
                // Обновляем статус при загрузке и при изменениях
                updateAuthStatus();
                setInterval(updateAuthStatus, 2000);
            }
        });
    </script>
</body>
</html>
""")
