# Обратная связь 2026-09-23: надёжность и рабочие экраны

## Диагностика до реализации

- Google adapter читает только parts[0].text, не объединяет остальные части и не исключает thought. finishReason не сохраняется. Исправление: собирать все финальные text parts, исключать thought, хранить безопасный finish_reason; MAX_TOKENS/length — неполный ответ, не успешная оценка. Исходный raw envelope старых ответов не сохранялся: нельзя доказать причину конкретного старого фрагмента.
- NormalizedGenerationRequest жёстко ограничен 1024 output tokens. Для пустого ответа последней OpenRouter-оценки usage.completion=1024 — признак возможного исчерпания лимита, но без сохранённого finish_reason не доказательство.
- В трёх последних независимых оценках ТА1: 11 строк, 6 completed, 5 failed. Snapshot содержит independent и три критерия. Общий completed_with_errors не означает, что все строки провалились.
- Критерии/шкалы уже добавляются к инструкции судьи автоматически через judge_prompt, но отдельной system-role сейчас нет. Нельзя выдавать ошибку парсинга за ноль. Судья должен возвращать все ключи scores в их шкалах и rationale; строгая проверка диапазонов остаётся.
- Повторы есть, но скрыты целиком при !canRetry; длинные строки и широкие таблицы затрудняют их обнаружение.

## Первый инкремент

Продолжение 2026-09-24: добавить preset crt_mko с фиксированным http://super-project-work.ru:8001/api/v1, без авторизации и без передачи credential_ref. Сохранение подключения требует явного подтверждения HTTP в capabilities.allow_insecure_http; это значение входит в snapshot. Каталог использует GET /models и только stc_llama; генерация POST /completions, ответ message.content. Не задавать непроверенные параметры num_predict: лимит токенов для этого сервиса пока не гарантируется и явно поясняется в UI. Реальные вызовы больше не выполнять. Остальные providers — отдельный последующий инкремент.

Скрываемый preview; исправление Google parts и finish_reason; понятная диагностика Judge JSON без вывода входных данных; отмена queued немедленно, running через cancelling (текущий запрос может завершиться и быть оплачен, новые не начинаются); после остановки повтор выбранных cancelled записей в том же Run. Управление повтором всегда видно с disabled-причиной и действием конкретной строки. Независимые баллы показываются отдельно, без агрегата, с количеством успешных оценок.

UX-дизайнер подключён по прямому запросу владельца; схема страниц — UX_WORKSPACE_REVISION.md. Перед реализацией экранов прочитать её. Поиск/фильтры/сортировка: сначала история и результаты запусков; общий rollout остальных таблиц отдельным шагом.

## Требует уточнения

Обновление 2026-09-23: владелец разрешил ровно один synthetic completion. Выполнен один POST /api/v1/completions без авторизации и без повторов: model=gemma3:4b, engine=stc_llama, input_text=«Ответь только OK», stream=false, exclude_from_history=true, exclude_context=true. Ответ HTTP 200: message.content="OK\n", message.role=assistant, done=true, done_reason=stop. Это прямой объект, НЕ SchemaResponse.data и НЕ choices. Метрики: prompt_eval_count=27, eval_count=3; total_duration/load_duration/prompt_eval_duration/eval_duration — числовые поля. Для адаптера текст брать из message.content, причину завершения из done_reason; стоимость отсутствует. Разрешение на единственный внешний вызов использовано; новые генерации агентом не выполнять без нового разрешения. Пользовательские данные не отправлялись. Это проверка API, не завершение интеграции.

Ответы владельца получены: YAML-примеры в data/promt, 25 файлов разбираются импортом; ЦРТ МКО не требует авторизации. GET /api/v1/models возвращает SchemaResponse.data с 8 моделями. Ожидается только разрешение на один synthetic completion или пример ответа, так как успешный completion body в OpenAPI не описан. Groq изучен по https://console.groq.com/docs/openai и https://console.groq.com/docs/models; реализация других провайдеров остаётся следующим шагом.

- YAML: запрошен пример файла/структуры, чтобы не угадывать system/user/messages и не терять инструкции при импорте.
- ЦРТ МКО: public schema GET изучен, generation POST не выполнялся. Адрес HTTP, требуется подтверждённый способ безопасного подключения/авторизации и пример ответа completion (schema ответа пустая). Не передавать ключи/датасеты до уточнения.
- Исходный список: OpenAI, Claude, Google, OpenRouter, Z.ai, Grog (вероятно Groq), GigaChat, YandexAi. Подключать отдельными проверенными адаптерами, а не объявлять все OpenAI-совместимыми; приоритет новых сервисов уточнить.

## Источники

- https://ai.google.dev/api/generate-content — content parts и finishReason, MAX_TOKENS.
- http://super-project-work.ru:8001/schema/openapi.json — LLM Service 0.1.1, POST /api/v1/completions, GET /api/v1/models, POST /api/access/login. Не OpenAI chat/completions по умолчанию; securitySchemes в схеме не описан.

## Проверка

Offline tests: multi-part/thought/empty/truncated Google, неполный OpenRouter, diagnostics независимых scores, cancellation гонки и отсутствие новых вызовов после запроса отмены, видимость повторов и отдельных критериев. Рабочие runs/snapshots не переписывать, внешние модели не вызывать.
