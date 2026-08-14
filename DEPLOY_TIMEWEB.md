# MB16 — запуск на Timeweb Cloud

Актуальный production-путь для MVP: **Timeweb App Platform + PostgreSQL DBaaS + S3**.

Приложение уже подготовлено для этого сценария: в корне репозитория есть `docker-compose.yml`, Dockerfile, production preflight и встроенный Docker `HEALTHCHECK` на `/health`.

## Что понадобится до начала

Подготовьте четыре вещи:

1. Telegram-бот и его `TELEGRAM_BOT_TOKEN`.
2. Числовой Telegram ID администратора — для `ADMIN_TELEGRAM_IDS`.
3. PostgreSQL в Timeweb Cloud.
4. S3-бакет в Timeweb Cloud для фото и видео.

Секреты **не добавлять в GitHub**. Они задаются только как переменные окружения Timeweb.

---

## Шаг 1. Создать приватную сеть и PostgreSQL

Сначала создайте или выберите приватную сеть в нужном регионе. **PostgreSQL и App Platform должны быть созданы в одном регионе и подключены к этой сети.** Это позволит приложению обращаться к базе по приватному адресу без публикации PostgreSQL в интернет.

В панели Timeweb Cloud:

1. Откройте **Базы данных**.
2. Создайте кластер PostgreSQL.
3. На шаге сети выберите подготовленную приватную сеть.
4. Для этого MVP не включайте публичный IPv4 для базы, если не нужен внешний административный доступ.
5. Для небольшого MVP достаточно одной базы и одного пользователя; не нужно заранее усложнять кластер репликами.
6. Сохраните:
   - host;
   - port;
   - database;
   - username;
   - password.

Timeweb для новых PostgreSQL использует TLS по умолчанию, поэтому production URL лучше формировать с `sslmode=require`:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require
```

Если пароль содержит `@`, `:`, `/`, `#` или другие специальные символы URL, его нужно URL-encode.

Приложение само создаст свои таблицы при первом запуске. Для текущего MVP отдельная ручная SQL-инициализация не требуется.

---

## Шаг 2. Создать S3 для фото и видео

Создайте S3-хранилище и отдельный бакет, например:

```text
mb16-showroom
```

Для текущей реализации изображения и видео должны быть доступны клиентскому Mini App по публичным URL, поэтому бакет/раздачу объектов нужно настроить на публичное чтение.

Переменные:

```env
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://s3.twcstorage.ru
S3_ACCESS_KEY_ID=<access key>
S3_SECRET_ACCESS_KEY=<secret key>
S3_BUCKET=mb16-showroom
S3_REGION=ru-1
S3_PUBLIC_BASE_URL=<публичный base URL бакета>
```

Не угадывайте `S3_PUBLIC_BASE_URL`: после создания бакета возьмите фактический публичный URL из настроек/панели и проверьте открытие тестового объекта в браузере.

---

## Шаг 3. Создать приложение в App Platform

В Timeweb Cloud:

1. Откройте **App Platform**.
2. Создайте новое приложение.
3. Подключите GitHub.
4. Выберите тот же регион и **ту же приватную сеть**, что использует PostgreSQL. Важно: Timeweb предупреждает, что приватную сеть App Platform после деплоя изменить нельзя.
5. Выберите репозиторий:

```text
PetrFedin/MB16
```

6. Ветка:

```text
main
```

7. Тип деплоя — **Docker Compose**.
8. Timeweb прочитает корневой `docker-compose.yml`.
9. Можно включить автоматический деплой по новым коммитам `main`.

---

## Шаг 4. Добавить production-переменные

В настройках приложения добавьте:

```env
APP_NAME=MB16 Showroom
APP_ENV=production
APP_TIMEZONE=Europe/Moscow

DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require

TELEGRAM_BOT_TOKEN=<BotFather token>
ADMIN_TELEGRAM_IDS=<numeric Telegram ID>
AUTH_MAX_AGE_SECONDS=86400

STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://s3.twcstorage.ru
S3_ACCESS_KEY_ID=<access key>
S3_SECRET_ACCESS_KEY=<secret key>
S3_BUCKET=mb16-showroom
S3_REGION=ru-1
S3_PUBLIC_BASE_URL=<public bucket base URL>

MAX_IMAGE_MB=10
MAX_VIDEO_MB=80
```

Если администраторов несколько:

```env
ADMIN_TELEGRAM_IDS=123456789,987654321
```

Production preflight не даст контейнеру запуститься, если отсутствует PostgreSQL URL, Telegram token, admin ID или обязательные S3-переменные. Это специально — лучше явная ошибка на деплое, чем полуработающее приложение.

---

## Шаг 5. Запустить deploy

Запустите сборку.

Что должно произойти:

1. Timeweb получает код из `main`.
2. Docker Compose собирает Dockerfile.
3. `python -m scripts.preflight` проверяет production-конфигурацию.
4. FastAPI стартует на порту `8000`.
5. Docker `HEALTHCHECK` вызывает `/health`.
6. `/health` выполняет `SELECT 1` в PostgreSQL, поэтому успешный healthcheck означает, что API действительно видит БД.

После успешного деплоя Timeweb выдаст бесплатный технический домен с HTTPS/SSL. Для первого MVP его достаточно — покупать и настраивать отдельный домен до проверки сценария не требуется.

Проверьте вручную:

```text
https://<timeweb-url>/health
```

Ожидается:

```json
{"ok":true}
```

Обычное открытие корневой страницы в браузере покажет интерфейс, но production API без Telegram `initData` не должен считать браузерного посетителя авторизованным. Полноценная проверка клиента выполняется внутри Telegram.

---

## Шаг 6. Привязать Mini App к Telegram-боту

Когда появился публичный HTTPS URL, есть два варианта.

### Вариант A — готовый скрипт проекта

На машине, где есть checkout репозитория:

```bash
TELEGRAM_BOT_TOKEN='...' \
PUBLIC_APP_URL='https://<timeweb-url>' \
python -m scripts.configure_telegram
```

Скрипт вызывает Bot API `setChatMenuButton` и делает кнопку меню бота **«Открыть шоурум»**.

### Вариант B — BotFather

Можно назначить Mini App URL через настройки бота в BotFather. Главное — использовать production HTTPS URL.

---

## Шаг 7. Проверка от имени администратора

Откройте бота с Telegram-аккаунта, ID которого находится в `ADMIN_TELEGRAM_IDS`.

Должна появиться вкладка **Админ**.

Проверьте один товар:

1. `+ Карточка`.
2. Добавить 3–5 фото.
3. Опционально видео.
4. Название.
5. Артикул.
6. Цена.
7. Категория.
8. Цвета.
9. Размеры.
10. Опубликовать.
11. Убедиться, что товар появился в каталоге.
12. Открыть `Изменить` и проверить сохранение цены/описания/цветов/размеров.

---

## Шаг 8. Проверка клиентского сценария

Используйте **другой Telegram-аккаунт**, который не является админом.

Пройдите весь сценарий:

1. Открыть каталог.
2. Открыть карточку.
3. Выбрать цвет.
4. Выбрать размер.
5. Добавить в подборку.
6. Открыть **Подборка**.
7. Нажать **Примерить**.
8. Выбрать будущую дату и время.
9. Отправить запрос.

После этого админ:

1. Открывает **Админ → Запросы**.
2. Для каждой вещи выбирает **Есть** или **Нет**.
3. Проверяет/меняет дату и время.
4. Нажимает **Подтвердить**.

После реального визита:

1. Админ нажимает **Клиент пришёл**.
2. У клиента появляется **Отметить, что купил**.
3. Клиент отмечает купленные позиции.
4. Админ видит эти позиции и нажимает **Продано**.
5. Проданный товар исчезает из каталога и активных подборок.
6. Вещь остается в разделе клиента **Покупки**.

---

## Что считать готовым MVP

Перед приглашением реальных клиентов должны одновременно выполняться все пункты:

- GitHub Actions зеленый;
- Timeweb deploy зеленый;
- `/health` возвращает `{"ok":true}`;
- 3–5 фото реально загружаются в S3 и открываются из Telegram;
- Mini App открывается из меню Telegram-бота;
- admin ID получает вкладку **Админ**;
- обычный клиент вкладку **Админ** не получает;
- полный тестовый цикл примерки и покупки проходит двумя реальными Telegram-аккаунтами;
- проданный товар исчезает из каталога;
- подтвержденная покупка остается в истории клиента.

После этого MVP лучше **не расширять сразу**, а дать его нескольким реальным пользователям и исправлять только то, что мешает сценарию карточка → подборка → примерка → покупка.

---

## Официальная документация

- Timeweb App Platform / Docker Compose и приватная сеть: `https://timeweb.cloud/docs/apps/deploying-with-docker-compose`
- Timeweb App Platform / переменные: `https://timeweb.cloud/docs/apps/variables`
- Timeweb App Platform / healthcheck: `https://timeweb.cloud/docs/apps/healthcheck-path`
- Timeweb PostgreSQL: `https://timeweb.cloud/docs/dbaas/postgresql`
- Timeweb подключение к БД: `https://timeweb.cloud/docs/dbaas/dbaas-manage/connect-to-database`
- Timeweb S3: `https://timeweb.cloud/docs/s3-storage`
- Timeweb S3 endpoint / region: `https://timeweb.cloud/docs/s3-storage/tools/rclone`
- Telegram Mini Apps: `https://core.telegram.org/bots/webapps`
- Telegram Bot API / setChatMenuButton: `https://core.telegram.org/bots/api`
