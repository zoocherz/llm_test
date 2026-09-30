# Универсальная модель тестирования LLM

## Статус

Этот документ фиксирует продуктовую модель до начала реализации. Food vision и аннотация звонков — проверочные шаблоны, а не доменные сущности ядра.

## Базовая формула

Каждый эксперимент состоит из неизменяемых версий:

Dataset + Pipeline + Evaluation suite + Execution policy = Run snapshot

- Dataset — версионируемый набор входных строк, эталонов и метаданных.
- Pipeline — граф преобразований и модельных вызовов.
- Evaluation suite — набор технических, детерминированных и LLM-оценщиков.
- Execution policy — параллелизм, timeouts, retry, бюджет и явные fallback-маршруты.
- Run snapshot — сохранённое описание того, что реально было исполнено.

Новый тип задачи должен добавляться конфигурацией, без изменения модели данных, API или движка запуска.

## Универсальные данные

DatasetItem имеет обязательный идентификатор и три логических области: input, reference, metadata. Input и reference имеют произвольную JSON-схему. Asset хранит MIME type и позволяет использовать изображение, аудио, PDF, видео, таблицу или иной файл. CSV является табличным представлением этой структуры, JSONL — полным переносимым форматом.

Пример: id, input.transcript, input.instruction, reference.summary, metadata.language и assets.

## Pipeline вместо «одной модели»

Pipeline — ориентированный граф. Узел имеет тип, входные переменные, настройки, схему выхода и связи со следующими узлами.

| Тип узла | Назначение |
| --- | --- |
| Input | Получает поля DatasetItem и assets |
| LLM call | Вызывает один явно выбранный маршрут модели |
| Transform | Шаблонизация, mapping JSON, простое преобразование |
| Rule / plugin | Детерминированная пользовательская логика |
| Branch / merge | Параллельные ветви и объединение результатов |
| Judge | LLM-оценка промежуточного или итогового выхода |
| Output | Выбирает итоговые артефакты pipeline |

Линейный pipeline с одним LLM call — частный случай. Это покрывает аннотацию звонка, цепочку «аннотатор → проверяющий → исправляющий» и независимые ответы нескольких моделей с арбитром.

В первом UI допустимы только линейный pipeline и параллельная матрица маршрутов. Формат хранения и execution engine должны поддерживать граф с самого начала.

## Модель и провайдер

Пользователь выбирает ModelRoute: provider + model + declared capabilities.

Адаптер провайдера предоставляет validate_credentials, list_models, get_capabilities, validate_model, generate и stream.

Capabilities описывают modalities (text/image/audio/document), structured output, tools, embeddings, context, usage, pricing и rate limits. Запуск валидируется до обращения к API: image input нельзя отправить text-only маршруту.

OpenAI-compatible площадки используют общий адаптер. Провайдеры со специальным протоколом подключаются отдельными адаптерами. Нельзя добавлять в UI provider type, для которого нет рабочего адаптера.

## Оценщики

Evaluator имеет независимую конфигурацию, входы, выходную схему и правила агрегации.

1. Технические: latency, usage, cost, error rate.
2. Детерминированные: JSON Schema, exact match, classification accuracy, precision/recall/F1, regex, JSONPath и формулы.
3. LLM-as-a-Judge: отдельный route, prompt version, JSON schema, шкала, критерии и веса.
4. Позднее — изолированный script/plugin evaluator.

Judge может вернуть несколько метрик одним структурированным JSON-ответом или быть отдельным вызовом для каждой метрики. Ошибка Judge — отдельный статус, никогда не числовой score.

Пользовательские scripts нельзя исполнять в backend-процессе: будущий SDK получает только item, output, reference и metadata, а исполняется изолированно.

## Сравнение и результаты

Результат существует в трёх разрезах:

1. Summary: матрица route × prompt с quality, latency, cost, errors и порогами.
2. Item detail: вход, reference, outputs всех узлов, attempts, метрики, Judge verdicts и trace pipeline.
3. Reproducible bundle: snapshot датасета, pipeline, prompts, routes, параметров, оценщиков и результатов.

Это обеспечивает сравнение, аудит, экспорт CSV/JSON и повторный запуск на тех же условиях.

## Политика fallback

Сравнительный experiment не заменяет тестируемую модель. Retry применим к тому же route только для временных ошибок. Fallback возможен лишь в отдельном availability-mode или в заранее обозначенной pipeline-ветви; каждый переход фиксируется как attempt и не смешивается с чистыми сравнительными результатами.
