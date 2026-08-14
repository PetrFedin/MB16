# Deploy MB16 Showroom to Timeweb Cloud

Конфигурация проверена по актуальной документации Timeweb Cloud на 14 августа 2026.

## Рекомендуемый вариант — App Platform + PostgreSQL + S3

### 1. PostgreSQL
Создайте управляемую PostgreSQL в Timeweb Cloud и получите host, port, database, user, password.

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
```

Приложение также принимает URL, начинающийся с `postgresql://` или `postgres://`, и переключает его на драйвер psycopg.

### 2. Фото и видео
Создайте публичный S3 bucket. Timeweb Cloud предоставляет S3-совместимое хранилище.

```env
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://s3.twcstorage.ru
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
S3_BUCKET=mb16-showroom
S3_REGION=ru-1
S3_PUBLIC_BASE_URL=https://s3.twcstorage.ru/mb16-showroom
```

Для публичного бакета объект будет доступен по схеме:

```text
https://s3.twcstorage.ru/<bucket>/<object>
```

### 3. Telegram

```env
APP_NAME=MB16 Showroom
APP_ENV=production
TELEGRAM_BOT_TOKEN=<token BotFather>
ADMIN_TELEGRAM_IDS=<numeric Telegram ID; несколько ID через запятую>
AUTH_MAX_AGE_SECONDS=86400
MAX_IMAGE_MB=10
MAX_VIDEO_MB=80
```

Переменные `DEBUG_*` не дают debug-доступ при `APP_ENV=production`.

### 4. App Platform
1. Создайте приложение в Timeweb Cloud App Platform.
2. Выберите деплой через Docker Compose.
3. Подключите GitHub и репозиторий `PetrFedin/MB16`.
4. Выберите ветку `main`.
5. В проекте уже есть корневой `docker-compose.yml`.
6. Добавьте переменные окружения из разделов выше через настройки App Platform.
7. После сборки проверьте `GET /health` — ответ должен быть `{"ok": true}`.
8. Скопируйте публичный HTTPS URL приложения.

App Platform поддерживает деплой Docker Compose из подключенного GitHub/GitLab/Bitbucket-репозитория и переменные окружения.

### 5. Telegram Mini App
В BotFather назначьте полученный HTTPS URL как URL Mini App для вашего бота. Backend проверяет подпись Telegram `initData`; в production вход по debug-заголовку отключен.

## Альтернатива — обычный Timeweb VPS с Docker

```bash
git clone https://github.com/PetrFedin/MB16.git
cd MB16
cp .env.example .env
# заполнить .env
docker compose -f docker-compose.local.yml up -d --build
```

В этом варианте PostgreSQL и загруженные медиа находятся в Docker volumes. Для публичного запуска нужен HTTPS через reverse proxy и домен.

## Проверка после deploy

- `/health` возвращает `{"ok": true}`;
- Mini App открывается внутри Telegram;
- клиент видит каталог;
- admin Telegram ID видит вкладку «Админ»;
- карточка с 3–5 фото создается и публикуется;
- клиент выбирает цвет/размер и собирает подборку;
- заявка на примерку появляется у админа;
- админ отмечает наличие и подтверждает дату/время;
- клиент отмечает купленные позиции;
- админ подтверждает продажу, товар исчезает из каталога, покупка остается в истории.

## Официальные источники
- Docker Compose в App Platform: https://timeweb.cloud/docs/apps/deploying-with-docker-compose
- Переменные App Platform: https://timeweb.cloud/docs/apps/variables
- S3: https://timeweb.cloud/docs/s3-storage
- S3 endpoint / region: https://timeweb.cloud/docs/s3-storage/tools/rclone
