# MB16 Showroom — Telegram Mini App MVP

Простой showroom внутри Telegram: карточки товаров, подборка на примерку, согласование визита и история покупок.

## Текущий функционал

### Клиент
- каталог только доступных товаров;
- карточка: 3–5 фото, optional video, название, описание, артикул, категория, цена, цвета, размеры;
- выбор цвета и размера;
- одна подборка;
- запрос даты/времени примерки;
- история своих примерок;
- после статуса `Клиент пришёл` — отметка купленных вещей;
- история покупок с признаком подтверждения продажи.

### Администратор
- доступ только Telegram ID из `ADMIN_TELEGRAM_IDS`;
- создание и публикация карточки;
- редактирование основных полей;
- предпросмотр фото;
- статусы товара `available / hidden / sold`;
- просмотр заявок;
- ручная проверка наличия каждой вещи;
- подтверждение/перенос времени;
- статусы заявки `new / confirmed / completed / declined / cancelled`;
- подтверждение продажи.

## Ключевые серверные гарантии

Текущая версия защищает бизнес-flow не только интерфейсом, но и API/БД:

- проданный товар нельзя вернуть в каталог после подтверждённой продажи;
- товар из confirmed-примерки нельзя вручную отметить проданным;
- одна вещь не может одновременно оказаться в двух confirmed-примерках;
- конкурентные подтверждения сериализуются через PostgreSQL row locks;
- наличие нельзя менять после подтверждения заявки;
- completed-заявку нельзя откатить назад;
- подтверждённую продажу клиент не может удалить из истории;
- повторное подтверждение продажи идемпотентно;
- повторное добавление одного варианта в подборку не создаёт дубль;
- частично загруженные медиа удаляются при ошибке создания карточки.

## Архитектура

```text
Telegram Mini App
      |
      v
FastAPI (UI + API)
      |
      +--> PostgreSQL
      |
      +--> Alembic migrations
      |
      +--> Local media (dev/VPS) or S3-compatible storage
      |
      +--> Telegram Bot API notifications
```

Frontend намеренно остаётся без отдельного build-system: FastAPI отдаёт `static/index.html`, CSS и JS. Для текущего MVP это уменьшает количество сервисов и точек отказа.

## База данных и миграции

Схема БД управляется Alembic. Приложение больше не создаёт таблицы через `Base.metadata.create_all()` при импорте.

Production container выполняет перед запуском API:

```bash
python -m scripts.preflight
alembic upgrade head
uvicorn app.main:app ...
```

CI дополнительно запускает `alembic check`, чтобы изменения моделей без migration revision не прошли незаметно.

При изменении `app/models.py` необходимо создать и проверить новую Alembic migration.

## Локальный запуск на MacBook

Требуется Docker Desktop.

```bash
git clone https://github.com/PetrFedin/MB16.git
cd MB16
git checkout main
make start-bg
make health
```

После старта:

- клиент: `http://localhost:8000/?debug_user=1001`
- админ: `http://localhost:8000/?debug_user=9001`
- API docs: `http://localhost:8000/docs`
- health: `http://localhost:8000/health`

Полезные команды:

```bash
make status
make logs
make stop
make test
```

`make start-bg` создаёт `.env` из `.env.example`, если его ещё нет. Docker startup применяет migrations автоматически.

Debug-вход отключён при `APP_ENV=production`.

## Telegram production auth

Backend принимает `Telegram.WebApp.initData` и проверяет HMAC-подпись и `auth_date` на сервере. Debug header в production игнорируется.

Для production нужны:

```env
APP_ENV=production
TELEGRAM_BOT_TOKEN=...
ADMIN_TELEGRAM_IDS=123456789
APP_TIMEZONE=Europe/Moscow
```

После получения production HTTPS URL кнопку Mini App можно настроить:

```bash
TELEGRAM_BOT_TOKEN='...' \
PUBLIC_APP_URL='https://your-app.example' \
python -m scripts.configure_telegram
```

## Timeweb Cloud

Рекомендуемый production-контур:

```text
Timeweb App Platform
  + PostgreSQL DBaaS
  + S3/Object Storage
  + HTTPS URL
```

Production variables включают `DATABASE_URL`, Telegram token/admin IDs и S3 credentials. Секреты не хранятся в GitHub.

Подробный порядок: `DEPLOY_TIMEWEB.md`.

## Проверка end-to-end

GitHub Actions проверяет:

- Python compile;
- configuration preflight;
- JS syntax;
- Alembic upgrade + model drift;
- API E2E на SQLite;
- API E2E на PostgreSQL 16;
- параллельное подтверждение одной вещи в PostgreSQL;
- rollback файлов при частичной ошибке media upload;
- Chromium mobile browser flow клиент + админ;
- Docker build.

Полная матрица: `E2E_QA.md`.

Основной автоматизированный UI-flow:

```text
admin creates product
-> client chooses color/size
-> selection
-> fitting request
-> admin availability check
-> confirmation
-> reschedule
-> client arrived
-> client marks purchase
-> admin confirms sale
-> product removed from catalog/selection
-> purchase preserved in history
```

## Структура

```text
app/
  auth.py
  config.py
  db.py
  main.py
  models.py
  schemas.py
  storage.py
  telegram.py
migrations/
  env.py
  versions/
static/
  index.html
  styles.css
  app.js
scripts/
  preflight.py
  configure_telegram.py
tests/
  test_flow.py
  test_browser_e2e.py
  test_postgres_resilience.py
alembic.ini
Dockerfile
docker-compose.local.yml
docker-compose.yml
Makefile
E2E_QA.md
DEPLOY_TIMEWEB.md
```

## Граница MVP

Пока намеренно не включены:

- онлайн-оплата;
- количественные остатки по SKU;
- CRM;
- персональный менеджер;
- AI-рекомендации/подбор образов;
- conversion analytics;
- loyalty/promocodes;
- доставка;
- multi-showroom.

Эти модули должны подключаться позже, после проверки базового сценария реальными пользователями, а не усложнять первый запуск.
