# Спецификация модели данных v1

## Инварианты

Идентификаторы — UUID, время — UTC. Published DatasetVersion, PromptVersion, PipelineVersion и EvaluationSuiteVersion неизменяемы. Run создаёт immutable RunSnapshot без secrets.

## Сущности

| Сущность | Содержимое |
| --- | --- |
| DatasetVersion | schema, DatasetItems, Asset manifest |
| DatasetItem | external_id, input JSON, reference JSON, metadata, tags |
| Asset | local path вне web root, sha256, MIME, size |
| PromptVersion | template и explicit bindings |
| PipelineVersion | graph nodes, edges и contracts |
| ModelRoute | provider, model, capabilities, route policy |
| EvaluationSuiteVersion | evaluators, Judge config, decision rule |
| RunSnapshot | копии исполняемых versions и ExecutionPolicy |
| RunItem / Attempt | output, usage, cost, latency, status и error |
| EvaluationResult | evaluator status, value JSON, nullable score |

## Pipeline и Judge

MVP валидирует Input → Template → LLM call → zero-or-more Evaluators → Output. Формат graph готов к branch/merge. Judge config содержит route, prompt, JSON schema, scale, criteria, weights и quality threshold. Ошибка, timeout или невалидный JSON не создают score.

## ExecutionPolicy

Default: benchmark, concurrency 3, timeout 60 seconds, retry только temporary errors, fallback disabled. UI default: до 100 rows × 3 prompts × 5 routes. User может менять допустимые limits до enqueue; route/provider может требовать timeout больше 60 seconds. Policy входит в RunSnapshot.