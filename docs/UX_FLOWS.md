# UX-потоки MVP

## Первый основной поток

1. Runs → New comparison.
2. Выбрать published DatasetVersion и один PromptVersion.
3. Выбрать от двух до пяти ModelRoutes и EvaluationSuite.
4. Проверить явные input bindings, providers, rows × routes, timeout, concurrency, budget и estimate calls.
5. Запустить durable Run.
6. Смотреть progress и errors.
7. Открыть matrix: route × quality, latency, cost, error rate.
8. Открыть item detail: outputs, attempts, Judge verdict и normalized error.

## Wireframe

Dataset version [ food-smoke v1 ]
Prompt version  [ identify-food v3 ]
Model routes   [ Google ] [ OpenRouter ]
Suite          [ Food rubric v1 ]

Rows 10   Timeout 60 s   Concurrency 3   Budget optional

Cancel                                      Start comparison

Decision сначала применяет quality threshold, затем latency, cost и error-rate rules. Run read-only после запуска; изменения создают новую version. Расширенные controls раскрывают bindings, parameters, retry policy, per-route timeout и budget. Следующий UX сравнивает prompt versions при одной модели.
## Управление конфигурацией

Перед запуском пользователь независимо создаёт и выбирает PromptVersion, линейный PipelineVersion, ModelRoute и EvaluationSuite. Форма каждого объекта показывает только его собственный контракт; создание одного объекта не создаёт скрыто остальные. После сохранения новая версия автоматически выбирается в форме Run, но остаётся доступна вместе с ранее сохранёнными версиями.

## Экспорт Run

В деталях terminal Run доступны два действия: JSON сохраняет snapshot и нормализованные item/attempt/result; CSV создаёт одну строку на RunItem с идентификаторами, статусом, output/error, score и latency. Экспорт не содержит raw credentials.
## Упрощение первого запуска по обратной связи владельца

Основной путь показывается как последовательность «Данные → Модель → Настройки оценки → Проверка и запуск». ModelRoute хранит отдельный черновик для каждого provider; переключение Google/OpenRouter восстанавливает соответствующие model ID и имя environment variable. Под формой виден список реально сохранённых маршрутов и boolean «ключ доступен».

Рекомендуемая настройка одной кнопкой создаёт три отдельные versioned-сущности: PromptVersion `{{text}}`, линейный PipelineVersion и EvaluationSuite с quality=1/threshold=0.7. Пользователь видит, что именно создано. Ручные JSON-формы остаются в раскрываемом блоке «Расширенные настройки».
## Управление ModelRoute и выбор модели

1. Пользователь выбирает provider и имя environment variable.
2. Workbench загружает актуальный каталог моделей через backend; raw credential не возвращается в браузер.
3. Модели доступны в searchable select. Для OpenRouter бесплатные модели и `openrouter/free` располагаются первыми и явно помечаются.
4. Если каталог временно недоступен, пользователь видит причину и может включить ручной ввод model identifier как fallback.
5. Кнопка «Сохранить» создаёт новый ModelRoute либо обновляет явно выбранный существующий маршрут. Таблица показывает активный выбор и предлагает «Изменить»/«Удалить».
6. Удаление требует подтверждения, убирает маршрут из будущего выбора и не изменяет уже созданные RunSnapshot.
7. Timeout описывается как максимальное общее время одного модельного вызова, включая повторную попытку.
## Быстрый запуск сравнения

1. Пользователь вставляет один или несколько коротких текстов; одна непустая строка становится одним DatasetItem.
2. Пользователь выбирает одну или несколько сохранённых моделей. Подключения с недоступным credential видны, но не выбираются.
3. До запуска UI показывает число входных строк, моделей и реальных candidate calls.
4. По кнопке «Запустить сравнение» создаётся и публикуется отдельный DatasetVersion. Зарезервированные default PromptVersion, linear PipelineVersion и EvaluationSuite создаются один раз и затем переиспользуются.
5. Создаётся обычный benchmark Run с fallback disabled и immutable RunSnapshot. Результаты появляются в общей истории и открываются тем же detail/export UI.
6. Подробные четыре шага остаются ниже для импорта CSV/JSONL, ручных prompt/pipeline/evaluator настроек и точной политики запуска.
## Разделение Workbench после пользовательской проверки

Одна длинная страница сохраняется только как временная реализация vertical slice. Целевой flow распределяется между URL:

- Главная — быстрый запуск и недавние Run.
- Датасеты — каталог, import/preview/publish, далее assets и assisted labeling.
- Модели — сохранённые ModelRoute, provider catalogs, capabilities и диагностика.
- Эксперименты — dataset + prompt + routes + pipeline + evaluation suite + estimate/start.
- Запуски — progress, summary matrix, item detail, snapshot и export.

Legacy `Providers`, `Tasks`, `Test Runs` не являются частью нового потока. В header они исчезают после появления новых route-level экранов; временный доступ по `/legacy/...` нужен только для совместимости и диагностики.

Полная информационная архитектура и критерии приёмки: `docs/INFORMATION_ARCHITECTURE.md`.
## Реализованные route-level разделы — 2026-09-17

- `/datasets` — импорт с preview и публикация DatasetVersion.
- `/models` — provider catalog и управление ModelRoute.
- `/runs`, `/runs/:runId` — история, summary и item detail.
- `/` — быстрый запуск; подробная конфигурация временно остаётся ниже до появления `/experiments`.
