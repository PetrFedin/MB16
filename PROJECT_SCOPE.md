# MB16 MVP scope

## Входит

- Telegram Mini App;
- роль клиента + admin Telegram IDs;
- карточка товара: 3–5 фото, optional video, название, описание, артикул, категория, цена, цвета, размеры;
- каталог;
- выбор цвета/размера;
- подборка;
- запрос примерки;
- ручная проверка наличия;
- подтверждение/перенос времени;
- отметка фактического визита;
- отметка покупки клиентом;
- подтверждение продажи админом;
- история покупок;
- Telegram initData server-side authentication;
- PostgreSQL + Alembic migrations;
- local/S3 media adapter;
- Docker/Timeweb deployment configuration;
- API + PostgreSQL resilience + Chromium E2E CI.

## Не входит сейчас

- онлайн-оплата;
- количественные остатки по SKU;
- CRM;
- персональные менеджеры;
- AI-рекомендации и подбор образов;
- conversion analytics/dashboard;
- loyalty/promocodes;
- доставка;
- multi-showroom.

Эти блоки добавляются позже через отдельные модули/таблицы/интеграции и не должны усложнять первый showroom flow.

## Инварианты v0.4

- 3–5 фото обязательны; video опционален.
- Покупки отмечаются только после `completed`.
- Подтверждённую продажу нельзя удалить из истории или вернуть в каталог.
- Одна вещь не может быть одновременно подтверждена в двух примерках.
- Конкурирующие PostgreSQL-операции резервирования/продажи защищены row locks.
- Server запрещает время примерки/подтверждения в прошлом.
- Schema управляется Alembic, а не `create_all`.
- Частично записанные media удаляются при ошибке создания карточки.
- Production debug login отключён.
- Production startup: preflight -> migrations -> API.
