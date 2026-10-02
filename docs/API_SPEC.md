# HTTP API v1

## Общие правила

Актуализация 2026-09-24:

- POST /api/v1/prompts:import принимает multipart file (UTF-8 YAML, до 256 KiB), возвращает name/template/ignored_fields/warnings без сохранения PromptVersion.
- POST /api/v1/runs/{id}:cancel: queued переходит в cancelled; running в cancelling, затем после текущего вызова в cancelled. Повторный запрос отмены идемпотентен; другие terminal состояния возвращают 409. Retry теперь допускает cancelled с полным snapshot.
- policy.max_output_tokens и RunEvaluationRequest.max_output_tokens: default 4096, диапазон 128..65536. Старые snapshots без поля сохраняют прежнее поведение. У ЦРТ МКО поддержка лимита не подтверждена.
- ModelRoute provider_name=crt_mko требует capabilities.allow_insecure_http=true и credential_ref=null. Каталог /provider-models?provider_name=crt_mko доступен без ключа. Согласие HTTP входит в snapshot генерации и судьи.
- Усечённый ответ MAX_TOKENS/length получает truncated_response; текст Google собирается из финальных text parts без thought.

Актуализация повторов/шкал 2026-09-22:

- DatasetImportMapping.reference_format: text преобразует строку в reference.text, json требует объект. Отсутствующее поле сохраняет старое поведение json; UI явно передаёт text по умолчанию.
- POST /api/v1/runs/{id}:retry принимает {item_ids: UUID[]}, удаляет повторы ID, проверяет принадлежность всех записей. 202 возвращает тот же id и retry_calls. 409 — активный/отменённый или legacy Run, 422 — чужие ID. Доступны completed/completed_with_errors/failed. Атомарно переводит Run в queued; исполняются только выбранные элементы с исходным snapshot. Текущие output/error очищаются, история Attempt/Result не удаляется. Существующие оценки исходных ответов остаются неизменны.
- Details.results — оценки текущей попытки; result_history — все оценки, attempts — последовательная история. value_json._attempt связывает оценку с номером попытки. JSON-экспорт содержит историю; CSV — текущие результаты, criteria_scores и criteria_scales.
- Suite.scoring_mode: weighted (совместимый default) или independent. Критерии имеют min_score/max_score (default 0/1). Independent не требует суммы весов, не создаёт общий numeric_score/passed. Weighted сохраняет шкалу 0..1 и сумму весов 1. Режим и шкалы входят в snapshot; Judge проверяется по каждому диапазону.
- Пустой/пробельный текст провайдера: failed с empty_response, без фиктивного успеха. Исторические completed не мигрируются, интерфейс предупреждает.

Актуализация 2026-09-22: POST /api/v1/prompts:preview принимает {template, input}, возвращает {rendered}, не сохраняет данные и не вызывает провайдера. Ошибка шаблона/отсутствующее поле — 422. Создание Prompt проверяет синтаксис; поддержаны {{text}}, {{input.text}} и вложенные поля через точку, без выражений. Обычные фигурные скобки JSON остаются текстом. Создание Pipeline принимает только один generate node без edges и отклоняет неподдерживаемую схему. Редактор сохраняет изменённые конфигурации существующим POST как новый объект, не PATCH оригинала.

Актуализация 2026-09-18: generation и evaluation разделены (D-070, D-071).

- POST /runs и /runs:estimate относятся только к генерации; judge_enabled=false, true отклоняется. suite_version_id теперь optional, генерация не создаёт numeric_score. PromptVersion.template подставляет {{field}} из верхнего уровня input. Неподдерживаемые выражения/отсутствующие поля отклоняются до запуска. Executor поддерживает один generate node без edges.
- POST /runs/{source_id}/evaluations принимает {judge_route_id, judge_prompt_id, suite_version_id}; ответ 202 {id, status, source_run_id, judge_calls}. Источник завершён, не является оценкой и содержит completed text outputs. 404 — нет источника, 409 — неподходящий статус/тип, 422 — неверные настройки/нет ответов.
- GET /runs/{source_id}/evaluations возвращает историю id/status/progress_json/created_at. Polling, details и экспорт оценки используют обычные /runs/{id} API. Details дополнены evaluation_source с исходным ответом и source_item_id.
- Snapshot оценки: kind=evaluation, source_run_id, Judge route/prompt, criteria/weights/threshold и evaluation_inputs. Новый запуск не изменяет source или предыдущие оценки.
- Suite criterion принимает optional description и уникальный key. Judge возвращает JSON {scores: {criterion_key: number}, rationale: string}, шкала 0..1. Weighted score вычисляет сервер; ошибка JSON/шкалы — failed result, numeric_score=null.
- Старые технические результаты не мигрируются в настоящие оценки. Offline Judge — тестовая фикстура, явно обозначенная в UI и rationale.

Base path: /api/v1. JSON UTF-8. Ошибка содержит code, message и field_errors. Secrets не возвращаются, не echo-ятся и не экспортируются. Изменение published version возвращает 409.

## Endpoints

| Method | Path | Назначение |
| --- | --- | --- |
| POST / GET | /providers | создать provider / список без secret |
| POST | /providers/{id}/validate | проверить credentials |
| POST | /providers/{id}/models:refresh | models и capabilities |
| POST / GET | /model-routes | создать / получить routes |
| POST / GET | /datasets | создать / список datasets |
| POST | /datasets/{dataset_id}/versions | создать пустую draft DatasetVersion со следующим номером; optional base_version_id/schema, не более одного draft на Dataset |
| POST | /datasets/import:preview | multipart CSV/JSONL preview без записи |
| POST | /datasets/{version_id}/items:import | multipart CSV/JSONL explicit commit в draft DatasetVersion |
| GET | /dataset-versions/{version_id}/items | Просмотр DatasetItem опубликованной или draft-версии с limit/offset |
| POST | /datasets/{id}/versions/{version}:publish | publish version |
| POST | /assets | загрузить local asset |
| POST | /prompts, /pipelines, /evaluation-suites | создать definition |
| POST | /runs:estimate | calls, budget и compatibility |
| POST / GET | /runs | enqueue run / список |
| GET | /runs/{id} | status и summary matrix |
| GET | /runs/{id}/items | item results |
| GET | /runs/{id}/items/{item_id}/attempts | attempts trace |
| POST | /runs/{id}:cancel | cancel |
| GET | /runs/{id}/export | CSV или JSON bundle |

Preview возвращает source_format, source_fields, `source_preview` (до 3 исходных строк, значения до 500 символов), mapping_applied, total_count, valid_count, invalid_count, row_errors и нормализованные preview-строки; он не сохраняет файл, token или DatasetItem. Multipart preview/commit могут содержать optional `mapping_json` с явными `external_id_field`, `input_text_field`, `reference_field`. CSV без `external_id` также проходит неперсистентный preview и возвращает исходные колонки/строки; commit без корректного mapping остаётся запрещён. CSV decoder поддерживает UTF-8, UTF-8 BOM, UTF-16 BOM и Windows-1251; delimiter автоматически определяется среди comma, semicolon, tab и pipe. `source_encoding`/`source_delimiter` возвращаются preview и сохраняются при commit. Commit повторно получает тот же файл и допускается только для draft DatasetVersion, если все строки валидны; применённый mapping сохраняется в `DatasetVersion.schema_json.import_mapping` и не может отличаться от уже зафиксированного для версии. Run принимает version IDs, routes, prompts и ExecutionPolicy override. До enqueue сервер валидирует bindings, bounds, budget и capabilities.
## Run export

`GET /runs/{id}/export?format=json` возвращает attachment с Run snapshot, timestamps, исходными DatasetItem и нормализованными attempts/results. `format=csv` возвращает одну строку на RunItem: external ID, prompt/route IDs, status, output/error JSON, первый numeric score и суммарную latency attempts. Raw credential values не включаются ни в один формат.
## ModelRoute management and provider model catalog

- `PUT /api/v1/model-routes/{route_id}` replaces editable ModelRoute settings (`provider_name`, `model_identifier`, `capabilities`, `credential_ref`, `timeout_seconds`). Existing RunSnapshot payloads are not changed.
- `DELETE /api/v1/model-routes/{route_id}` removes the route from future selection and returns 204. Historical RunItem route IDs and embedded RunSnapshot definitions remain readable.
- `GET /api/v1/provider-models?provider_name=google|openrouter&credential_ref=env:NAME` resolves the credential only server-side and returns normalized rows: `id`, `display_name`, `provider_name`, `is_free`, `context_window`, `input_modalities`, `output_modalities`. Raw credentials and provider response bodies are not returned.
- Google catalog includes only models supporting `generateContent`. OpenRouter free status is derived from zero prompt/completion pricing; the `openrouter/free` router is included as a recommended free option.
- ModelRoute `timeout_seconds` is a total per-RunItem execution budget, including retries and backoff.

## Настраиваемый ЦРТ и прогресс (2026-10-02)

ModelRoute.capabilities.base_url обязателен для crt_mko; полный HTTP/HTTPS URL API без credentials/query/fragment. HTTP требует capabilities.allow_insecure_http=true. GET /provider-models принимает base_url и allow_insecure_http; неверный/отсутствующий адрес — 422 до сети. Адрес включён в RunSnapshot; update ModelRoute не меняет snapshot. Estimate/create/evaluate/retry валидируют соответствующий текущий или сохранённый адрес.

RunItem.status=running и Attempt появляются до вызова. progress_json во время обработки дополнительно содержит active_item_id, attempt (номер повтора строки), http_attempt, active_started_at (UTC), timeout_seconds. completed — число завершённых completed/failed строк, failed — отдельное подмножество; отменённые строки не выдаются за обработанные. Attempt.route_snapshot_json содержит sequence, started_at, http_attempts, completed_at; latency_ms=null означает незавершённую попытку. Terminal progress сохраняет прежние completed/total/failed для совместимости.

Details добавляет display_text для удобного чтения исторических ответов без изменения БД. Новые ответы ЦРТ имеют очищенный text; при изменении исходника сохраняются raw_text и normalization=crt_final_text_v1. Экспорт и snapshot сохраняют исторические данные. Invalid JSON имеет код invalid_json, error-envelope — provider_error; raw HTTP bodies не экспортируются. Ошибки входной валидации возвращают type/loc/msg без input/context, чтобы не отражать присланные секреты.