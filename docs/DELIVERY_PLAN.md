# План поставки LLM Evaluation Workbench

## Актуальный приоритет — 2026-09-22

Дополнение по новой обратной связи: RESULTS_REFINEMENT.md / D-075–D-076. Внедрены повторы выбранных записей внутри исходного запуска, текстовые эталоны CSV, независимые шкалы и улучшение истории/результатов. Следующий gate — проверка владельцем этого сценария; затем recovery jobs (включая отменённые/аварийно прерванные Run) и evaluator library. Старые пункты ниже относятся к предыдущим инкрементам.

Отдельная оценка проверена владельцем. Исправления настройки Prompt/Pipeline/Suite реализованы по CONFIGURATION_UX.md: просмотр и новые копии, ранняя валидация, preview, критерии в таблице, локальные ошибки. Проверки: 24 backend tests, build, 8 browser E2E. Следующий gate — удобство новых форм на пользовательском промпте; затем evaluator library и recovery jobs. Ниже — исторический план, не текущие blockers.

## Предыдущий приоритет — 2026-09-18

Обновление: владелец подтвердил раздельный поток. Prompt rendering и отдельный text Judge реализованы; 22 backend tests и 6 browser E2E прошли. Следующий gate — реальный пользовательский smoke на одном сохранённом ответе (SEPARATE_EVALUATION_GUIDE.md). Затем удобный редактор критериев, evaluator library и recovery jobs. Ниже сохранён предыдущий анализ, не текущий blocker.

Компоненты результатов и конфигурации выделены, мёртвые формы удалены; автообновление Run защищено от гонок. Следующий функциональный приоритет — устранить ограничения executor (неприменяемый шаблон prompt и технический score вместо Judge), а не расширять импорт или косметику. До реализации согласовать отдельный/автоматический поток оценки по EVALUATION_NEXT_INCREMENT.md. Legacy UI/API пока не удалять: наличие нужных пользовательских данных не подтверждено.

## Текущая точка

Offline vertical slice работает: persistent v1 entities, RunSnapshot, очередь, item results, интеграционный тест и минимальный экран. Реальные provider calls и полноценный пользовательский flow ещё не реализованы.

## Этап 1 — QA baseline и закрытие foundation

**Цель:** доказать корректность offline-ядра до подключения внешних ключей.

1. QA составляет traceability matrix: требования → API/UI → тест → результат.
2. Добавляются unit и API integration tests:
   - Dataset preview, duplicate IDs, publish immutability;
   - ExecutionPolicy и запрет benchmark fallback;
   - Judge criteria/weights, failure semantics;
   - cancel Run и completed_with_errors;
   - snapshot immutability и отсутствие secrets в API.
3. Проверяется UI happy path в браузере и регрессия legacy views.
4. Исправляются найденные P0-дефекты.
5. **Gate:** offline test suite проходит без сети; пользователь подтверждает удобство базового UX.

## Этап 2 — Provider foundation

**Цель:** связать ModelRoute с безопасным реальным adapter contract.

1. Вводятся provider credential references без возврата secret через API, логи или экспорт.
2. Реализуются normalized request/response и capability validation.
3. Добавляются mocked contract tests для Google Vision и OpenRouter Vision.
4. Реализуются timeout, retry только для временных ошибок и нормализация ошибок.
5. **Gate:** тесты payload/capability проходят offline; ключи отсутствуют в репозитории и ответах API.

## Этап 3 — Controlled real-provider smoke

**Цель:** проверить реальный маршрут на данных и ключах владельца.

1. Пользователь добавляет минимальный Dataset и ключи локально.
2. Выполняется отдельный smoke для каждого выбранного provider/model.
3. QA фиксирует latency, usage/cost, ошибки, соответствие snapshot и masking secrets.
4. **Gate:** каждый заявленный route имеет успешный smoke либо явно помечен недоступным.

## Этап 4 — Рабочий UX сравнения

**Цель:** заменить offline-demo управляемым пользовательским flow.

1. Управление Dataset/CSV/JSONL/import preview/local assets.
2. Создание Prompt, linear Pipeline, ModelRoute и EvaluationSuite.
3. Estimate до запуска, Run matrix, item detail, cancel и export.
4. E2E-тест основного пользовательского сценария.
5. **Gate:** пользователь создаёт и сравнивает собственный набор без ручных API-вызовов.

## Порядок

Сначала этап 1, затем этап 2. Этап 3 требует ключи и минимальные данные владельца. Этап 4 развивается параллельно с этапом 2 после того, как API-контракт stabilised.

## Артефакты

- Текущее состояние: PROJECT_STATE.md
- Архитектурные решения: DECISION_LOG.md
- Тестовая стратегия: TEST_STRATEGY.md
- Детальный первоначальный foundation backlog: FOUNDATION_IMPLEMENTATION_PLAN.md
## Progress update — 2026-09-16

- Этап 1: offline QA baseline и browser E2E выполнены.
- Этап 2: безопасные credentials, Google/OpenRouter adapters, model catalogs, normalized errors и bounded timeout выполнены; GigaChat остаётся отдельным будущим adapter increment.
- Этап 3: успешный controlled smoke зафиксирован для `openrouter/free` и `gemini-3.6-flash`.
- Этап 4: managed Dataset/configuration/run/export flow и быстрый comparison flow реализованы. Следующий gap рабочего UX — summary matrix и удобный переход к item details.
## UX/IA update — 2026-09-17

Быстрый запуск принят владельцем. Перед дальнейшим наращиванием единого Workbench добавлен этап разделения интерфейса:

1. Завершить ценность Run: summary matrix по моделям и переход к item detail.
2. Разделить текущий Workbench на Главную, Датасеты, Модели, Эксперименты и Запуски, переиспользуя существующие v1 API и компоненты.
3. Убрать legacy `Providers/Tasks/Test Runs` из основной навигации; временно перенести их под `/legacy/...`.
4. Обновить E2E на новый сквозной flow и только затем удалить ненужные legacy UI/API.
5. Следующими предметными инкрементами развивать Dataset assets/import mapping, assisted labeling и библиотеку evaluators/Judge.

UX-спецификация: `docs/INFORMATION_ARCHITECTURE.md`. Пустые разделы «Оценка» и «Настройки» заранее не создаются.
## Progress — Run results and navigation split — 2026-09-17

- Summary matrix and expandable item detail are implemented for v1 Run.
- The first route-level boundary is implemented: `/runs` and `/runs/:runId`.
- Legacy navigation items are removed from the header; direct `/legacy/...` compatibility remains.
- Next migration slice: Datasets and Models, followed by Experiments and simplification of Home.
## Progress — Datasets and Models routes — 2026-09-17

- Route-level `/datasets` and `/models` are implemented and covered by the main E2E.
- Their long forms were removed from Home; the same v1 APIs and versioned domain entities are reused.
- Next slice is `/experiments`, followed by final Home cleanup. Evaluation remains inside Experiment until a reusable evaluator library exists.

## Progress — Dataset import diagnostics and lifecycle — 2026-09-17

- Text import now distinguishes JSON array from JSONL and provides actionable per-line parse/schema errors.
- Canonical DatasetItem validation prevents silent loss of noncanonical fields; external mapping remains an explicit previewable/versioned follow-up.
- Saved dataset contents are viewable. In-place edit is intentionally excluded for published versions; revision UX and retention-safe archive/delete remain backlog items.
- Backend 18/18, frontend build and browser E2E 1/1 passed.

## Progress — explicit text Dataset mapping — 2026-09-17

- Noncanonical CSV/JSONL fields can now be explicitly mapped to canonical `external_id`, `input.text` and optional `reference`.
- Mapping suggestions remain visible and require confirmation; the definition is stored with DatasetVersion for reproducibility.
- The real repository fixture is covered by backend and browser tests.
