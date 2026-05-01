# Auto Parts API (Lab 3)

REST API для управления автозапчастями с системой аутентификации и авторизации на стеке **FastAPI + PostgreSQL + SQLAlchemy + Alembic**.

Реализовано в рамках лабораторной работы №3:
- JWT аутентификация (Access + Refresh токены)
- OAuth 2.0 вход через Yandex ID
- HttpOnly cookies для безопасной передачи токенов
- Хеширование паролей с уникальной солью (bcrypt)
- Защита эндпоинтов через Middleware
- Проверка владения ресурсами

---

## 📋 Требования

- Python 3.10+
- PostgreSQL 16+
- Docker и Docker Compose

---

## 🚀 Быстрый старт

### 1. Настройка переменных окружения

Скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

Для работы OAuth через Yandex ID необходимо зарегистрировать приложение в [консоли разработчика Yandex](https://oauth.yandex.ru/) и получить `CLIENT_ID` и `CLIENT_SECRET`.

### 2. Запуск через Docker

```bash
docker compose -f docker-compose.lab3.yml up -d --build
```

API будет доступно на: **http://localhost:4203**

---

## 📖 API Endpoints

### Authentication

| Метод | Endpoint | Описание | Доступ |
|-------|----------|----------|--------|
| POST | `/auth/register` | Регистрация нового пользователя | Public |
| POST | `/auth/login` | Вход (установка cookies) | Public |
| POST | `/auth/refresh` | Обновление пары токенов | Public (требуется Refresh Cookie) |
| GET | `/auth/whoami` | Проверка статуса авторизации | Private |
| POST | `/auth/logout` | Завершение текущей сессии | Private |
| POST | `/auth/logout-all` | Завершение всех сессий | Private |
| GET | `/auth/oauth/yandex` | Инициация входа через Yandex | Public |
| GET | `/auth/oauth/yandex/callback` | Callback от Yandex | Public |

### Auto Parts (защищено авторизацией)

| Метод | Endpoint | Описание | Доступ |
|-------|----------|----------|--------|
| GET | `/api/v1/parts` | Получить список запчастей | Private |
| POST | `/api/v1/parts` | Создать запчасть | Private |
| GET | `/api/v1/parts/{id}` | Получить запчасть по ID | Private |
| PUT | `/api/v1/parts/{id}` | Полное обновление | Private (владелец) |
| PATCH | `/api/v1/parts/{id}` | Частичное обновление | Private (владелец) |
| DELETE | `/api/v1/parts/{id}` | Удалить (Soft Delete) | Private (владелец) |

---

## 🧪 Тестирование

### Через Swagger UI

Откройте **http://localhost:4203/docs** для интерактивного тестирования API.

### Пример регистрации и входа

```bash
# Регистрация
curl -X POST http://localhost:4203/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123",
    "phone": "+79991234567"
  }'

# Вход (токены устанавливаются в cookies)
curl -X POST http://localhost:4203/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }'

# Проверка статуса
curl http://localhost:4203/auth/whoami

# Создание запчасти (требуется авторизация)
curl -X POST http://localhost:4203/api/v1/parts \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=YOUR_TOKEN" \
  -d '{
    "name": "Тормозные колодки",
    "part_number": "BRK-001",
    "price": 1500,
    "description": "Передние"
  }'
```

---

## 🔐 Безопасность

### Пароли
- Хешируются с использованием bcrypt
- Уникальная соль для каждого пользователя
- Не хранятся в открытом виде

### Токены
- Access Token: 15 минут (короткое время жизни)
- Refresh Token: 7 дней (хранится в БД в хешированном виде)
- Передаются только через HttpOnly cookies
- Отзыв токенов через logout/logout-all

### OAuth 2.0
- Реализован поток Authorization Code Grant
- Проверка state параметра (защита от CSRF)
- Поддержка Yandex ID

---

## 📁 Структура проекта

```
auto_parts_api/
├── app/
│   ├── controllers/      # Контроллеры (роутеры)
│   │   ├── auth_controller.py
│   │   └── part_controller.py
│   ├── models/           # SQLAlchemy модели
│   │   ├── user.py
│   │   ├── refresh_token.py
│   │   └── part.py
│   ├── schemas/          # Pydantic схемы (DTO)
│   │   ├── auth.py
│   │   └── part.py
│   ├── services/         # Бизнес-логика
│   │   ├── auth_service.py
│   │   ├── oauth_service.py
│   │   └── part_service.py
│   ├── middleware/       # Middleware
│   │   └── auth.py
│   ├── utils/            # Утилиты
│   │   ├── security.py   # Хеширование
│   │   └── jwt.py        # JWT токены
│   ├── config.py         # Конфигурация
│   ├── database.py       # Подключение к БД
│   └── main.py           # Точка входа
├── alembic/              # Миграции БД
├── .env                  # Переменные окружения
├── .env.example          # Пример .env
├── docker-compose.lab3.yml    # Docker конфигурация
├── requirements.txt      # Зависимости
└── README.md
```

---

## 🐳 Docker

### Запуск
```bash
docker compose -f docker-compose.lab3.yml up -d
```

### Остановка
```bash
docker compose -f docker-compose.lab3.yml down
```

### Просмотр логов
```bash
docker compose -f docker-compose.lab3.yml logs -f app
docker compose -f docker-compose.lab3.yml logs -f postgres
```

### Пересборка
```bash
docker compose -f docker-compose.lab3.yml up -d --build
```

---

## 📝 Особенности реализации

- **Модульная архитектура** — разделение на Controller, Service, Model
- **Soft Delete** — записи помечаются `deleted_at` вместо удаления
- **Пагинация** — поддержка `page` и `limit` параметров
- **Валидация** — Pydantic схемы для всех запросов
- **Миграции** — Alembic для управления схемой БД
- **Асинхронность** — asyncio + asyncpg
- **Проверка владения** — пользователи могут редактировать только свои запчасти

---

## 👤 Автор

Студент: Гридин Дмитрий
Группа: 090304-РПИб-023

---

## 📄 Лицензия

Учебный проект для лабораторной работы.
