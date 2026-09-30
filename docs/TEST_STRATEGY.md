# Стратегия тестирования MVP

## Пирамида

- Unit: dataset validation, prompt variables, capabilities, fallback policy, Judge JSON parsing и расчёт score.
- Contract: mock HTTP для Google/OpenRouter Vision и форматов изображений.
- API integration: временная SQLite, CRUD, импорт, очередь, run, экспорт и masking secrets.
- E2E: один happy path в браузере от добавления провайдера до просмотра результата.
- Smoke: отдельный ручной/CI-набор с реальными ключами; сеть не используется в обычных тестах.

## Обязательные проверки

1. Кейc с изображением отклоняется до HTTP-вызова, если маршрут не vision-capable.
2. Google получает base64 + MIME для local asset; OpenRouter получает корректный OpenAI-compatible media payload.
3. Preview импорта сообщает строку и причину ошибки, но не записывает данные.
4. Повторяющийся external id обрабатывается по явной политике fail/skip/update.
5. Успешный target сохраняет output, provider, model, latency и usage.
6. Сбой Judge даёт отдельный status и `judge_score=null`, а не ноль.
7. Один успех и одна ошибка дают run status `completed_with_errors`.
8. Fallback использует только явно разрешённые vision-routes; 401 не повторяется и не подменяется.
9. Provider API никогда не возвращает ключ.
10. Snapshot run остаётся неизменным после изменения датасета.
11. Данные переживают перезапуск приложения.

## Гейт перед подключением реальных ключей

Unit и API integration проходят полностью без сети; секреты отсутствуют в репозитории; ручной smoke запускается только с ключами пользователя и минимальным датасетом.

## Acceptance criteria первого vertical slice

Проверяется поток из FOUNDATION_IMPLEMENTATION_PLAN.md: generic Dataset с text/image, linear Pipeline, два compatible routes, configured Judge, immutable RunSnapshot и results. Все offline tests выполняются без сети и ключей. Реальный provider smoke использует только данные и ключи владельца. Дополнительно проверяются matrix bounds, configurable timeout, явные data bindings и отсутствие secrets в responses/exports.
## Автоматизированный browser E2E

Playwright smoke поднимает изолированные frontend/backend на 3010/8020 и отдельную SQLite. Сценарий создаёт Dataset, PromptVersion, PipelineVersion, offline ModelRoute и EvaluationSuite, выполняет estimate и Run, скачивает JSON/CSV export и открывает все legacy-вкладки. Используется установленный системный Chrome; provider keys и сеть не нужны.
## Verification update — 2026-09-16 provider/UX feedback

- Added regression coverage for Windows User environment credential resolution without exposing the resolved value.
- Added runner regression coverage proving provider failures retain `code`, `message`, `retryable` in RunItem and Attempt.
- Current automated result: backend 15/15, frontend production build passed, Playwright managed offline flow 1/1 passed.
- Controlled live smoke is diagnostic, not a deterministic CI gate: OpenRouter returned HTTP 402 and Google generation timed out after credential resolution succeeded.
## Verification update — route management and catalogs

- Provider contract tests cover normalized Google/OpenRouter catalogs, filtering Google models by `generateContent`, free-price detection and free-first ordering.
- Timeout regression uses a delayed retryable response and asserts that retry/backoff cannot exceed the route total budget.
- API integration covers create → update → list → delete for ModelRoute.
- Browser E2E covers create → edit same route → complete Run → delete route while preserving displayed Run history.
- Current automated result: backend 18/18, frontend production build passed, Playwright 1/1 passed. Live read-only catalogs for both configured providers also passed.
## Verification update — quick comparison flow

- Browser E2E now executes two durable Runs in one scenario: the new quick comparison path and the detailed managed path.
- It verifies quick input → selected saved route → terminal completed status, then estimate/run, JSON/CSV exports, route deletion with retained history and legacy navigation.
- Latest result: Playwright 1/1 passed in 1.1 minutes; production build passed after removal of the unused legacy demo path.
