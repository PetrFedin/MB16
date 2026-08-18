# MB16 — production deploy на Timeweb Cloud

Рекомендуемый контур MVP:

```text
GitHub: PetrFedin/MB16
        |
        v
Timeweb App Platform
   |            |
   v            v
PostgreSQL      S3/Object Storage
        |
        v
Telegram Mini App
```

## 1. Что подготовить

Нужны:

1. Telegram bot token.
2. Числовой Telegram ID хотя бы одного администратора.
3. PostgreSQL в Timeweb Cloud.
4. S3 bucket для фото/видео.
5. App Platform, связанный с GitHub.

Секреты не коммитятся в репозиторий.

## 2. PostgreSQL

Создайте PostgreSQL и приложение в одном регионе/приватной сети, если используете private networking.

Production URL:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require
```

Если Timeweb выдаёт `postgresql://` или `postgres://`, `app/db.py` автоматически переключает схему на драйвер psycopg.

### Миграции

Схема больше не создаётся через `Base.metadata.create_all()`.

Источник истины — Alembic:

```text
alembic.ini
migrations/
```

Docker container перед Uvicorn выполняет:

```bash
alembic upgrade head
```

Это означает:

- первый deploy создаёт схему миграцией `0001_initial`;
- следующие изменения схемы должны добавляться новыми migration revisions;
- production-данные не должны требовать ручного `CREATE TABLE`.

Для текущего MVP используйте один application replica во время первого migration/deploy. Масштабирование на несколько replicas имеет смысл только после появления реальной нагрузки и отдельного deployment migration step.

## 3. S3

Создайте bucket, например `mb16-showroom`, и настройте публичную выдачу объектов, чтобы Mini App мог отображать фото/видео.

```env
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://s3.twcstorage.ru
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
S3_BUCKET=mb16-showroom
S3_REGION=ru-1
S3_PUBLIC_BASE_URL=<фактический public base URL>
```

`S3_PUBLIC_BASE_URL` берите из реальной конфигурации bucket, не угадывайте.

При ошибке создания карточки сервер делает best-effort cleanup уже загруженных объектов, чтобы не оставлять media-orphans.

## 4. App Platform

Подключите репозиторий:

```text
PetrFedin/MB16
```

Production deploy должен идти из `main` после зелёного CI.

Используйте корневой `docker-compose.yml` / `Dockerfile`.

Минимальные variables:

```env
APP_NAME=MB16 Showroom
APP_ENV=production
APP_TIMEZONE=Europe/Moscow
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require

TELEGRAM_BOT_TOKEN=...
ADMIN_TELEGRAM_IDS=123456789
AUTH_MAX_AGE_SECONDS=86400

STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://s3.twcstorage.ru
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
S3_BUCKET=mb16-showroom
S3_REGION=ru-1
S3_PUBLIC_BASE_URL=...

MAX_IMAGE_MB=10
MAX_VIDEO_MB=80
```

Если администраторов несколько:

```env
ADMIN_TELEGRAM_IDS=123456789,987654321
```

## 5. Startup sequence

Контейнер запускается так:

```text
preflight
-> alembic upgrade head
-> uvicorn
-> Docker healthcheck /health
```

`/health` выполняет `SELECT 1`, поэтому успешный ответ подтверждает доступ приложения к БД:

```json
{"ok":true}
```

## 6. Telegram Mini App

После получения HTTPS URL можно настроить menu button:

```bash
TELEGRAM_BOT_TOKEN='...' \
PUBLIC_APP_URL='https://<timeweb-url>' \
python -m scripts.configure_telegram
```

Production API принимает Telegram `initData`, проверяет подпись и срок действия. Debug user header при `APP_ENV=production` не даёт доступ.

## 7. Production acceptance

Проверять двумя реальными Telegram-аккаунтами: admin и client.

### Admin

1. Открыть вкладку Admin.
2. Создать карточку с 3–5 фото.
3. Проверить optional video.
4. Изменить основные поля карточки.

### Client

1. Открыть карточку.
2. Выбрать цвет/размер.
3. Добавить в подборку.
4. Создать запрос на примерку на будущую дату.

### Admin продолжение

1. Проверить наличие каждой вещи.
2. Подтвердить или перенести время.
3. После визита нажать `Клиент пришёл`.

### Client продолжение

1. Отметить купленные вещи.

### Admin завершение

1. Подтвердить продажу.
2. Убедиться, что товар исчез из активного каталога/подборок.
3. Убедиться, что покупка остаётся в истории клиента.

## 8. Что уже проверяет CI до production

GitHub Actions проверяет:

- Alembic migration на PostgreSQL 16;
- отсутствие schema drift через `alembic check`;
- API E2E на SQLite и PostgreSQL;
- конкурентные подтверждения одной вещи на PostgreSQL;
- rollback частично загруженных media;
- Chromium mobile UI E2E;
- Telegram initData validation;
- Docker build.

Подробно: `E2E_QA.md`.

## 9. Что нельзя подтвердить без реальных credentials

До фактической настройки Timeweb/Telegram нельзя честно подтвердить:

- private network connectivity конкретной БД;
- реальные S3 permissions/public URLs;
- доставку Telegram notifications;
- menu button production URL;
- сохранность данных после конкретного Timeweb redeploy.

Эти пункты являются последним production acceptance, а не задачей unit/CI тестов.
