# План реализации foundation

## Цель вертикального среза

Пользователь создаёт generic DatasetVersion с text и local image asset, публикует linear Pipeline, выбирает два capability-compatible ModelRoutes и настроенный Judge, запускает benchmark и получает immutable RunSnapshot, summary matrix и item details.

## Порядок работ

1. Создать новые domain models и SQLite migrations для Dataset, versions, assets, prompts, pipelines, routes, suites, runs, attempts и evaluation results.
2. Реализовать validation и import preview для JSONL/CSV без записи до commit.
3. Реализовать ProviderAdapter contract, capability validation и mocked Google/OpenRouter contract tests.
4. Реализовать linear Pipeline executor, durable Run queue, ExecutionPolicy, cancellation и item-level errors.
5. Реализовать deterministic evaluators и structured Judge parser.
6. Реализовать API из API_SPEC для vertical slice.
7. Реализовать Vue flow New comparison, Runs matrix и item detail согласно UX_FLOWS.
8. Добавить CSV/JSON export с RunSnapshot manifest, без secrets и assets.
9. Пройти unit, API integration и browser E2E без внешней сети; отдельно провести user-owned provider smoke.

## Out of scope

Audio/ASR, graph editor, branches, plugin evaluators, prompt-comparison screen, provider types без contract-tested adapter и расширение legacy Task/TestCase.

## Готовность vertical slice

- Новый код использует Dataset, Pipeline, ModelRoute, Evaluator и RunSnapshot.
- Один success и один item failure завершают run как completed_with_errors.
- Route без image capability отклоняется до HTTP call.
- Judge failure даёт unavailable score, а не ноль.
- Benchmark не использует fallback.
- Snapshot, results и export сохраняются после restart.