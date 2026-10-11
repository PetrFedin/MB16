# MB16 — обязательные доработки / zero-new-cost execution

Snapshot: 2026-10-12. State: REQUIRED, not proof of implementation.

Canon: `README.md`, existing Telegram Mini App admin/client capabilities.

| ID | P | Требуемое действие | Сквозная связь | Definition of Done |
|---|---|---|---|---|
| MB-ZC-01 | P0 | Клиент: честный сценарий примерки | catalog → size/color → selection → request → confirmation | testable appointment with exact availability and statuses |
| MB-ZC-02 | P0 | Админ: остатки/продажа/история | admin stock verification → sold → hidden → purchase history | no sold item remains available; RBAC verified |
| MB-ZC-03 | P0 | Надёжность auth + DB | Telegram signed initData → auth → own PG → backups | signature and negative tests, restore, no secrets in repo |
| MB-ZC-04 | P1 | Мобильный UX и аналитика | mobile catalog → card → selection → visits → conversions | device screenshots, zero-paid integrations, actual cohort counts |

## Обязательный нулевой бюджет и безопасная передача
- Дополнительная стоимость внедрения/эксплуатации нового контура: **0 ₽**. Запрещено включать биллинг, pay-as-you-go, платные CI minutes/API/AI/БД/storage, платные публикации, платные провайдеры, приобретать серверы/домены или выполнять реальные платежи. Уже существующая инфраструктура не доказывает нулевой совокупной стоимости; фиксировать только **incremental cost**.
- Только локальные/open-source инструменты и **доказанные** свободные остатки бесплатных тарифов. Если бесплатные лимиты/учётная запись не проверены: `BLOCKED_NO_FREE_CAPACITY`.
- Не заменять production demo-приложением; не подключать чужие БД; не записывать секреты в GitHub; не обходить CI, review, migrations и RBAC.
- Сначала проверить latest main/PR/CI, затем взять первое доступное P0. Для каждой задачи: implementation files, exact SHA, passing unit+negative+browser/device tests, persistence/restore evidence где применимо, live deployed SHA где нужен, ledger стоимости, статус `PLANNED/IN_CODE/CI_PASS/LIVE_VERIFIED/BLOCKED`.
- Этот файл — **дополнение** к существующему authoritative technical specification / AGENTS.md, а не замена. Не утверждать внедрение на основании создания документа.

Следующий агент: продолжай с первого открытого P0, **делай код и тесты**, не создавай одни планы. В конце обнови issue/PR с evidence и источник истины проекта; merge — только по существующим политикам.
