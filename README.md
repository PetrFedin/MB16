# MB16 Showroom — Telegram Mini App MVP

Минимальный showroom внутри Telegram: карточки товаров, подборка на примерку, согласование визита и история покупок.

## Что есть сейчас

### Клиент
- каталог только доступных товаров;
- карточка с 3–5 фото, опциональным видео, названием, артикулом, категорией, ценой, цветами и размерами;
- выбор конкретного цвета и размера;
- одна простая подборка «Подборка»;
- запрос на примерку с датой, временем и комментарием;
- список своих примерок и их статусов;
- после фактического визита (админ нажал «Клиент пришёл») клиент отмечает, какие вещи купил;
- отдельный экран «Покупки» в личном кабинете.

### Администратор
- отдельная вкладка «Админ» только для Telegram ID из `ADMIN_TELEGRAM_IDS`;
- создание и немедленная публикация карточки;
- редактирование названия, артикула, цены, категории, цветов, размеров и информации;
- предпросмотр выбранных фото до публикации;
- статусы товара: `available`, `hidden`, `sold`;
- просмотр всех запросов на примерку;
- ручная проверка наличия каждой выбранной вещи: «Есть / Нет»;
- подтверждение или изменение даты и времени;
- завершение/отклонение заявки;
- подтверждение покупки клиента кнопкой «Продано»;
- после подтверждения продажи товар исчезает из каталога и активных подборок, но остается в истории покупки.

## Принцип MVP

Здесь намеренно нет оплаты, CRM, автоматических остатков, рекомендаций, AI, сложных ролей и аналитики. Их можно добавить позже, не меняя основной клиентский сценарий.

## Архитектура

```text
Telegram Mini App
      |
      v
FastAPI (HTML/CSS/JS + API)
      |
      +--> PostgreSQL
      |
      +--> Local media (Docker/VPS) OR S3-compatible storage (Timeweb App Platform)
      |
      +--> Telegram Bot API (опциональные уведомления)
```

Frontend специально не вынесен в отдельную сборку: FastAPI отдает и интерфейс, и API. Для MVP это уменьшает количество сервисов и упрощает Docker/Timeweb deployment.

## Локальный запуск через Docker

1. Создайте `.env`:

```bash
cp .env.example .env
```

2. Для локальной проверки можно оставить debug-пользователей:
- клиент: `1001`
- админ: `9001`

3. Запуск:

```bash
docker compose -f docker-compose.local.yml up --build
```

4. Откройте:

- клиент: `http://localhost:8000/?debug_user=1001`
- админ: `http://localhost:8000/?debug_user=9001`
- API docs: `http://localhost:8000/docs`
- health: `http://localhost:8000/health`

Debug-вход отключается автоматически при `APP_ENV=production`.

## Настройка Telegram

Для реального запуска нужны:

```env
APP_ENV=production
TELEGRAM_BOT_TOKEN=<token BotFather>
ADMIN_TELEGRAM_IDS=<ваш числовой Telegram ID>
APP_TIMEZONE=Europe/Moscow
```

Backend принимает `Telegram.WebApp.initData` и проверяет подпись на сервере перед использованием Telegram user data.

После деплоя можно привязать HTTPS URL к кнопке меню бота автоматически:

```bash
TELEGRAM_BOT_TOKEN=... PUBLIC_APP_URL=https://your-app.example python -m scripts.configure_telegram
```

Скрипт использует Telegram Bot API `setChatMenuButton` и добавляет команду `/start`.

## Timeweb Cloud App Platform

В корне уже находится `docker-compose.yml`, подготовленный для App Platform. Он не использует Docker volumes.

Для production на App Platform нужны:

1. Timeweb PostgreSQL (или другой внешний PostgreSQL).
2. Публичный S3 bucket для фото/видео.
3. Переменные окружения в App Platform.

Минимальный набор:

```env
APP_NAME=MB16 Showroom
APP_ENV=production
APP_TIMEZONE=Europe/Moscow
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
TELEGRAM_BOT_TOKEN=...
ADMIN_TELEGRAM_IDS=123456789
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://s3.twcstorage.ru
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
S3_BUCKET=...
S3_REGION=ru-1
S3_PUBLIC_BASE_URL=https://s3.twcstorage.ru/BUCKET_NAME
```

Если Timeweb выдает `DATABASE_URL` со схемой `postgresql://` или `postgres://`, приложение автоматически переключит её на драйвер `psycopg`.

Подробно: `DEPLOY_TIMEWEB.md`.

## Production preflight

Перед запуском контейнер выполняет `python -m scripts.preflight`. В production он не стартует, если не настроены PostgreSQL, токен Telegram, хотя бы один admin Telegram ID или обязательные S3-переменные.

## Если это обычный Timeweb VPS с Docker

Можно использовать `docker-compose.local.yml` и заменить значения `.env` на production. Тогда PostgreSQL и медиа будут жить в Docker volumes на сервере. Для самого быстрого частного MVP это допустимый вариант, но для App Platform используется внешний PostgreSQL + S3.

## Основные API

### Клиент
- `GET /api/products`
- `GET /api/selection`
- `POST /api/selection`
- `DELETE /api/selection/{item_id}`
- `POST /api/fittings`
- `GET /api/fittings/my`
- `POST /api/fittings/{id}/purchases`
- `GET /api/purchases/my`

### Администратор
- `GET /api/admin/products`
- `POST /api/admin/products`
- `PATCH /api/admin/products/{id}`
- `PATCH /api/admin/products/{id}/status`
- `GET /api/admin/fittings`
- `PATCH /api/admin/fittings/{id}/items/{item_id}`
- `PATCH /api/admin/fittings/{id}`
- `POST /api/admin/fittings/{id}/items/{item_id}/confirm-sale`

## Структура

```text
app/
  auth.py       Telegram auth + admin access
  config.py     environment configuration
  db.py         SQLAlchemy connection
  main.py       API and application routes
  models.py     data model
  schemas.py    request schemas
  storage.py    local/S3 media adapter
  telegram.py   optional bot notifications
scripts/
  preflight.py            production environment validation
  configure_telegram.py   bot menu / Mini App URL setup
static/
  index.html
  styles.css
  app.js
Dockerfile
docker-compose.yml          Timeweb App Platform / production
docker-compose.local.yml    local/VPS full stack
```

## Проверка

На текущей версии пройден end-to-end smoke test:

`создание карточки -> редактирование карточки -> каталог -> подборка -> запрос -> проверка наличия -> подтверждение -> клиент пришёл -> клиент отметил покупку -> админ подтвердил продажу -> товар скрыт -> покупка сохранена`.
