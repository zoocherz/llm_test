# Архитектура MVP

## Подход

Раздельная оценка (2026-09-18): существующие Run/RunItem/Attempt/Result переиспользуются без миграции таблиц. Snapshot.kind различает generation и evaluation. Оценка хранит source_run_id и копии input/reference/candidate output для каждого нового item. route_id/prompt_version_id items сохраняют candidate-измерения; реально вызванный Judge хранится в snapshot.judge и Attempt.route_snapshot_json. Повторная оценка не меняет источник.

Run/items commit-ятся перед постановкой фоновой задачи. Генерация применяет snapshot-промпт и не создаёт Result. SQL debug logging скрывает параметры (input/reference/output и секретные значения). Ограничения: text-only Judge, одна модель/инструкция и несколько критериев с весами на оценку; один generate node для генерации. In-process jobs и восстановление running после аварии остаются техническим долгом, durable внешний worker не добавлялся.

Модульный монолит: Vue-клиент, FastAPI API и SQLite для локального режима. Длительные запуски выполняются как фоновые jobs, а не в HTTP-запросе. Позднее SQLite-очередь можно заменить Redis-worker без изменения доменного сервиса.

## Основные сущности

- Provider и ProviderModel: секрет и совместимая пара провайдера с моделью/capabilities.
- Dataset, DatasetItem и Asset: данные, строки и локальные изображения.
- Prompt и PromptVersion: неизменяемые шаблоны.
- EvaluationSuite и SuiteRoute: конфигурация сравнения и явные candidate/Judge маршруты.
- Run, RunItem и Attempt: запуск, построчный результат и каждое обращение к API.
- EvaluationResult: метрика или Judge-вердикт.

Старые сущности Task/TestCase/TestRun остаются legacy и не должны расширяться: они смешивают задачу, датасет, судью и один строковый model name.

## API v1

- Providers: CRUD без выдачи secret, validate, refresh/list models.
- Datasets: CRUD, preview/import CSV/JSONL, добавление items и локальных assets.
- Prompts: создание и версионирование.
- Suites: создание, validation, явные routes.
- Runs: enqueue, status, items, attempts, cancel, export.

Статические маршруты объявляются раньше `/{id}`, чтобы не повторить поломку старых `/tasks/runs` и `/providers/pool/validate`.

## Адаптер провайдера

Контракт адаптера: `validate_credentials`, `list_models`, `get_capabilities`, `validate_model`, `generate(normalized_request)`. Нормализованный запрос содержит текстовые части, media parts, параметры и correlation id.

Первый рабочий набор: Google Vision и OpenRouter Vision. GigaChat подключается только после отдельной проверки актуального API и его capabilities. Нельзя дать пользователю выбрать ProviderType без реализованного адаптера.

## Безопасность

Секреты не входят в response schemas, логи и экспорт. В MVP они защищаются локальным master key из environment; production-план потребует managed secret storage. Изображения лежат вне static-каталога. Все API-запросы имеют ограничение размера, MIME и timeout.

## Повторы

Retry разрешён только для временных network/timeout/429/5xx ошибок на том же маршруте. Fallback разрешён только между заранее выбранными compatible routes. 401, неверная модель, невалидный запрос и неподдерживаемое изображение не делают fallback.

## Подтверждённые execution defaults

ExecutionPolicy snapshot хранит configurable timeout, concurrency и budget. Стартовый timeout — 60 seconds, но route/provider policy может задать большее значение. Перед запуском UI показывает providers и явные input bindings. Quality threshold и decision rules принадлежат version EvaluationSuite и копируются в RunSnapshot.
## Frontend boundaries и навигация

Frontend остаётся одним Vue-приложением, но не одним рабочим экраном. Route-level разделы соответствуют пользовательским задачам и универсальным агрегатам: Главная/быстрый запуск, Датасеты, Модели, Эксперименты и Запуски. Общие формы и таблицы выделяются в компоненты, а состояние конкретного объекта восстанавливается из URL и API, не из единственного долгоживущего component state.

«Что тестируем» представляется комбинацией PipelineVersion, PromptVersion, ModelRoute и параметров Experiment, а не новой сущностью, дублирующей RunConfiguration. Роль одной ModelRoute (candidate, generator или Judge) задаётся ссылкой из pipeline/evaluation configuration.

Legacy `Provider/Task/TestCase/TestRun` не участвуют в новой навигации. На миграционном этапе старые views могут быть доступны по `/legacy/...`; новый UI и API на них не развиваются. Подробная информационная архитектура и порядок миграции находятся в `docs/INFORMATION_ARCHITECTURE.md`.
