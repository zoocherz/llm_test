# Requirements discovery: универсальная платформа оценки LLM

## Статус

Первый раунд аналитики завершён. Реализация кода отложена до утверждения решений с пометкой P0.

## Продуктовая модель

Единица сравнения — не «модель вообще», а конфигурация:

provider + model + prompt version + parameters + dataset version + evaluator configuration.

Сквозная цепочка:

DatasetVersion → PipelineVersion → RunConfiguration → RunSnapshot → RunItem/Attempt → EvaluationResult.

Food vision и аннотация звонков реализуются как task templates, без специальных таблиц, API или исполнителей в ядре.

## Функциональные границы ядра

### Датасеты

- Dataset содержит версионируемые examples с input, optional reference, metadata, tags/split и локальными media assets.
- Канонический формат — JSONL; CSV — удобная плоская проекция.
- Импорт всегда имеет preview и построчный validation report до записи.
- В MVP CSV использует столбцы `external_id`, `input`, `reference`, `metadata`, `tags`, где все поля кроме идентификатора являются JSON; JSONL содержит по одному каноническому DatasetItem на строку. Пустые `reference`, `metadata` и `tags` получают безопасные значения по умолчанию.
- Канонический DatasetItem требует непустой `external_id` и объект `input`. Неизвестные поля верхнего уровня отклоняются; импорт сторонней схемы в будущем использует только явный preview/mapping, без скрытых alias-преобразований.
- CSV preview распознаёт распространённые локальные кодировки (UTF-8/BOM, UTF-16 BOM, Windows-1251) и разделители (`,`, `;`, tab, `|`), показывает обнаруженные параметры до commit и не принимает одноколоночный результат молча.
- Изменение published dataset создаёт новую revision; run всегда использует snapshot.
- Поля, доступные prompt и evaluator, выбираются явно; metadata не передаётся модели неявно.

### Pipeline и варианты

- PipelineVersion — неизменяемый направленный граф с input/output contracts.
- MVP-редактор может создавать только линейную схему: Input → Template → LLM → Evaluators → Output.
- Внутренний контракт с первого дня хранит node IDs, bindings и edges, поэтому позднее возможны multi-agent chains, branches и arbiter.
- Experiment создаёт матрицу prompt versions × model routes × parameters и показывает число вызовов до старта.

### Провайдеры

- ModelRoute — конкретная provider/model пара с declared capabilities, а не строка model_name.
- Adapter contract: credentials validation, model discovery, capabilities, request validation, generation и error normalization.
- До вызова API проверяются modality, MIME, size, context и параметры.
- Google, OpenRouter и GigaChat подключаются отдельными адаптерами/contract tests; OpenAI-compatible APIs переиспользуют общий адаптер.

### Оценка

- Встроенные evaluators: latency, usage/cost, error, JSON schema, exact/contains, classification metrics и простые declarative rules.
- LLM Judge имеет свой route, prompt version, input bindings, JSON schema, шкалу, criteria/weights и failure policy.
- Judge error, invalid Judge JSON и candidate error имеют отдельные статусы; score не подставляется нулём.
- Script/plugin evaluators требуют отдельного SDK и sandbox; не входят в MVP.

### Запуски и результаты

- Run запускается асинхронно и сохраняет immutable snapshot dataset, prompts, pipeline, routes, evaluator configs, policies и runtime facts.
- RunItem сохраняет actual route, output, usage, cost, latency и error.
- Attempt хранит initial/retry/fallback, нормализованную ошибку и причины.
- Результаты представлены как summary matrix, per-item detail/trace и reproducible bundle CSV/JSON manifest.
- Benchmark и availability pool — разные режимы. В benchmark fallback выключен; results с fallback явно маркируются.

## Нефункциональные требования

- Secrets не возвращаются API/UI/экспортом и не попадают в логи.
- Локальный MVP не слушает сеть по умолчанию.
- Uploads имеют MIME, размер и path/SSRF validation; files хранятся вне web root.
- Bounded concurrency, retries/backoff только для temporary errors, budgets/timeouts и cancellation.
- UI не блокируется на длительном run; partial results durable.
- Unit/API/E2E test path не требует настоящих API keys; provider smoke — отдельный.

## P0-решения владельца

1. Pipeline MVP: линейный UI при внутренней graph-модели — подтвердить.
2. Media MVP: форматы, максимальный размер, количество изображений; требуется ли audio/transcription уже сейчас.
3. Privacy: можно ли отправлять реальные звонки/фото внешним providers; masking, deletion и retention policy.
4. Judge policy: шкала/criteria/weights, invalid JSON/timeout policy, required structured output.
5. Execution: partial errors продолжают run; fallback по умолчанию выключен — подтвердить.
6. Ограничения: ожидаемые rows × prompts × models, допустимое время, concurrency и бюджет.
7. Decision view: как выбрать победителя — quality threshold, затем latency/cost/error rate или configurable weights.
8. Первый UX priority: сначала matrix моделей на одном prompt или matrix prompts на одной модели.

## Следующий шаг discovery

Провести с владельцем короткую сессию P0 по блокам: Pipeline, Dataset/media, Evaluators/Judge, Execution/results, privacy/cost. После ответов подготовить утверждаемую спецификацию API, data model и wireframes, затем собрать 5–10 smoke examples для каждого шаблона.

## Результат P0-сессии владельца

Все P0 закрыты: linear UI при graph-модели; text и image; Dataset data через явные bindings; Judge JSON с настраиваемыми criteria/weights; no benchmark fallback; item errors продолжают run; изменяемые defaults запуска и timeout больше 60 seconds при необходимости; quality threshold перед latency/cost/error rate; первый UX — models при одном prompt.
## Дополнение discovery: сценарии владельца — 2026-09-17

Черновик `docs/scenarios.md` подтверждает сквозной цикл: подготовка Dataset → настройка candidate-конфигурации → получение outputs → настройка evaluators/Judge → оценка → сравнение вариантов.

Новые требования, принятые в backlog:

- Dataset имеет самостоятельный каталог и жизненный цикл, включая будущие media assets.
- Импорт готовых размеченных CSV/JSONL остаётся базовым потоком.
- Данные без эталонов требуют отдельного assisted-labeling workflow с обязательной пользовательской проверкой.
- Произвольный входной формат преобразуется через preview, явный field/schema mapping и сохраняемый transformation snapshot; обещание «любой формат без настройки» не принимается.
- Генерация синтетических данных и поиск внешних наборов являются отдельными post-MVP workflows.
- ModelRoute переиспользуется в ролях candidate, генератора эталона и Judge; роль не хранится внутри подключения.
- Критерии могут быть детерминированными либо Judge-based. Загрузка произвольного исполняемого алгоритма отложена до plugin SDK и sandbox.
- Результаты требуют summary matrix и просмотра отдельного исходного примера, output, attempt и evaluator verdict.
- Интерфейс разделяется по рабочим областям; legacy Task/TestRun не расширяются.

Открытые, но не блокирующие ближайший инкремент вопросы: нужна ли сущность Project для группировки артефактов; являются ли generation и evaluation стадиями одного Run или связанными Runs; какие declarative evaluator types нужны первыми.
