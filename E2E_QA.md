# MB16 end-to-end QA

Этот файл фиксирует, что должно быть зелёным до реального запуска MB16 в Telegram/Timeweb.

## Автоматические проверки

GitHub Actions запускается на push и pull request и проверяет:

1. Python compilation для `app/`, `scripts/`, `migrations/`.
2. Dependency consistency через `pip check`.
3. Development preflight.
4. JavaScript syntax через Node 22.
5. Alembic `upgrade head` на PostgreSQL 16.
6. `alembic check`: модели SQLAlchemy не расходятся с миграциями.
7. Полный API E2E на SQLite.
8. Тот же API E2E на PostgreSQL 16.
9. PostgreSQL resilience E2E: конкурентные действия + rollback media.
10. Реальный Chromium browser E2E клиент + админ на мобильном viewport.
11. Сборку production Docker image.
12. Запуск собранного production image: `preflight -> migrations -> uvicorn -> /health`.
13. Production container работает от UID `10001`, а не от root.

Ветка считается проверенной только по зелёному GitHub Actions run на актуальном head commit.

## Основной API E2E

`tests/test_flow.py` проверяет:

- `/` и `/health`;
- разделение client/admin;
- обязательные 3–5 фото;
- optional video;
- запрет дубликата артикула;
- редактирование карточки;
- нормализацию повторяющихся цветов/размеров;
- неверный цвет/размер;
- идемпотентное добавление в подборку;
- запрет примерки в прошлом;
- запрет подтверждения до проверки всех вещей;
- неизменность наличия после подтверждения;
- запрет ручной продажи зарезервированного товара;
- допустимые переходы статусов примерки;
- перенос confirmed-примерки;
- запрет второй confirmed-примерки на тот же товар;
- запрет отметки покупки до визита;
- запрет отката completed-заявки;
- идемпотентное подтверждение продажи;
- невозможность удалить подтверждённую продажу из истории;
- невозможность вернуть подтверждённую продажу в каталог;
- исчезновение проданного товара из каталога/подборок;
- сохранение покупки в истории;
- валидную Telegram initData подпись;
- malformed/future/expired `auth_date`;
- отключение debug-входа в production.

## PostgreSQL resilience E2E

`tests/test_postgres_resilience.py` запускается отдельным CI-шагом против PostgreSQL 16.

1. **Два параллельных подтверждения одной вещи.** Два запроса стартуют одновременно. Результат: строго один `200` и один `409`; в БД остаётся одна confirmed-примерка.
2. **Частичный сбой media upload.** Если после записи первых файлов следующий файл невалиден, карточка не создаётся, DB transaction откатывается, уже записанные файлы удаляются.

Product/fitting/purchase/sale операции используют PostgreSQL row locks там, где решение зависит от текущего состояния товара/заявки.

## Browser E2E

`tests/test_browser_e2e.py` запускает Chromium с мобильным viewport:

1. Admin создаёт карточку с тремя фото.
2. Client выбирает цвет/размер и добавляет товар в подборку.
3. Client отправляет fitting request.
4. Admin проверяет availability и подтверждает.
5. Admin переносит время через `Сохранить время`.
6. Admin отмечает `Клиент пришёл`.
7. Client отмечает покупку.
8. Admin подтверждает продажу.
9. Client видит исчезновение товара из каталога/подборки и подтверждённую покупку в истории.

Подменяется только внешний Telegram SDK script. MB16 HTML/JS/API/database/local-media работают реально.

## Production Docker runtime smoke

После `docker build` CI запускает именно собранный image в `APP_ENV=production` с тестовым PostgreSQL и local storage.

Проверяется:

```text
container start
-> production preflight
-> alembic upgrade head
-> uvicorn on custom PORT
-> GET /health
-> running UID == 10001
```

Это ловит ошибки, которые обычный `docker build` не видит: отсутствующий файл миграции, неверный CMD, права файлов, неправильный `PORT`, inability to start as non-root.

## Миграции БД

Схема не создаётся через `Base.metadata.create_all()` при импорте.

Источник истины: `migrations/` + Alembic. Production container выполняет:

```bash
alembic upgrade head
```

CI также выполняет:

```bash
alembic check
```

Изменение `models.py`, требующее schema change, должно сопровождаться новой migration revision.

## Зависимости

Прямые runtime/dev зависимости закреплены точными версиями в `requirements.txt` и `requirements-dev.txt`. Это делает CI, Mac и production build воспроизводимее. Обновлять версии нужно отдельным проверяемым изменением с полным CI, а не автоматически получать новые major/minor поведения при очередном deploy.

## Проверка на MacBook

После merge:

```bash
make start-bg
make health
make status
```

Клиент: `http://localhost:8000/?debug_user=1001`

Admin: `http://localhost:8000/?debug_user=9001`

Docker startup применяет Alembic migrations перед API.

## Что невозможно подтвердить без production-сервисов

### Telegram
- реальный `Telegram.WebApp.initData` от вашего bot;
- фактическую доставку notifications;
- Mini App menu button по production HTTPS URL.

### Timeweb PostgreSQL
- фактический production connection/private network;
- сохранение данных после конкретного restart/redeploy.

### Timeweb S3
- реальные bucket permissions/public URL;
- доступность фото/video после redeploy;
- фактический cleanup S3 при ошибке.

Эти пункты проходят production acceptance после выдачи реальных credentials/URL. Секреты в GitHub не коммитятся.

## Граница текущего MVP

В QA намеренно не входят online payment, quantitative SKU inventory, CRM, personal managers, AI styling/recommendations, conversion analytics, delivery, loyalty/promotions и multi-showroom: они пока не входят в простой MB16 showroom flow.
