# Session handoff — актуально 2026-09-25

## Публикация GitHub — 2026-09-30

- По запросу владельца подготовлен коммит накопленного инкремента для origin https://github.com/zoocherz/llm_test.git, ветка назначения main. Исходная история сохраняется, force push не используется. Решение D-082: далее коммиты завершённых проверенных инкрементов.
- Добавлены исключения БД/SQLite sidecars, пользовательских data/ и test/, локальных секретов и 1.txt. Рабочие данные остаются на диске. В коммит входят synthetic backend/tests и frontend/e2e.
- Обновлён корневой README с актуальными возможностями, установкой и запуском; прежнее описание в llm-tester/README помечено историческим. Убраны лишние пустые строки EOF в семи файлах, поведение кода не менялось.
- Проверки сегодня: backend 36/36; production build и Playwright 12/12 с GOMAXPROCS=2. Строгий UTF-8 и git diff --cached --check; проверка типичных шаблонов ключей не обнаружила совпадений. Реальные провайдеры не вызывались.
- Коммит реализации d572fcb опубликован в origin/main обычным fast-forward push (82df16c → d572fcb). Автор Git настроен локально как zoocherz с адресом noreply. Локальная рабочая ветка остаётся prompt-and-llm-model-testing-15646; для публикации используется git push origin HEAD:main. Текущая запись фиксируется отдельным документационным коммитом. Следующий продуктовый шаг: пользователь ещё не проверял интерфейс, YAML и ЦРТ МКО; ожидается обратная связь. Новых P0 нет.


## Возобновление — 2026-09-30

- Прочитаны AGENTS.md, актуальная точка остановки, SESSION_HANDOFF, WORKSPACE_ACCESS и решения до D-081.
- Launcher выполнен с Action Start; frontend http://localhost:3000 и backend /health отвечают HTTP 200. По API активных queued/running/cancelling запусков: 0.
- Владелец сообщил, что новый интерфейс, YAML и ЦРТ МКО ещё не проверял. Следующий шаг — пользовательская проверка по CRT_MKO_GUIDE.md и SEPARATE_EVALUATION_GUIDE.md, затем устранение конкретных замечаний.
- Код не менялся; новые генерации и оценки агентом не запускались. Последняя полная регрессия остаётся от 2026-09-24: backend 36/36, build, Playwright 12/12; сегодня повторно не запускалась.
- Новых P0-вопросов нет. Остальные провайдеры и расширение поиска/сортировки остаются последующими инкрементами.


## Точка остановки перед перезагрузкой — 2026-09-25

Работа приостановлена по просьбе владельца, не из-за ошибки. На момент проверки API доступен, активных queued/running/cancelling запусков: 0. Новые генерации не запускались; сервисы и ОС в этом шаге не останавливались.

Наработки находятся на диске E:\Projects\llm_test. Рабочая БД: llm-tester/backend/llm_tester.db; не удалять, не заменять тестовой. В Git есть изменённые и untracked файлы, включая БД и пользовательские data/test: это не чистый commit, массовые git add/clean/reset запрещены. Отдельный Git-коммит или резервный архив сейчас не создавались. История решений — DECISION_LOG.md (до D-081), история работы — разделы ниже, планы — DELIVERY_PLAN.md и RELIABILITY_UX_2026_09_23.md с учётом более свежего PROJECT_STATE.

После перезагрузки:
1. Прочитать AGENTS.md, PROJECT_STATE.md, SESSION_HANDOFF.md и WORKSPACE_ACCESS.md. Не повторять диагностику ACL: известен рабочий прямой codex.exe --codex-run-as-apply-patch.
2. Из корня проекта запустить: powershell.exe -ExecutionPolicy Bypass -File scripts\run.ps1 -Action Start. Адреса: http://localhost:3000 и http://localhost:8010/health. Не полагаться на старые PID.
3. Продолжать с завершённого инкремента от 2026-09-24: 36/36 backend, build, 12/12 Playwright уже прошли; это последний подтверждённый результат, сегодня повторно тесты не запускались.
4. Ожидается проверка владельцем нового интерфейса, YAML и ЦРТ МКО. Результаты этой проверки ещё не получены. Руководства: CRT_MKO_GUIDE.md и SEPARATE_EVALUATION_GUIDE.md.
5. Затем устранить замечания; следующие части плана — остальные провайдеры исходного списка, поиск/сортировка остальных таблиц, уточнение UX. Не считать их реализованными.
6. Разрешение на единственный реальный запрос ЦРТ МКО уже использовано (OK); автоматически не повторять. Генерация и оценка остаются раздельными, независимые критерии — без общего балла. Новых P0-вопросов нет.

Приоритет: эта точка остановки и итог от 2026-09-24 выше промежуточных записей от 2026-09-23 о незавершённом адаптере/тестах. Память ранее ограничивала тесты: запускать последовательно, frontend с GOMAXPROCS=2, чужие процессы не завершать.

## Актуальная точка — 2026-09-24, надёжность/UX и ЦРТ МКО

- Реализован ЦРТ МКО: каталог stc_llama, текстовый adapter, без ключа, явное согласие HTTP в ModelRoute/RunSnapshot. Единственный разрешённый реальный smoke уже использован (HTTP 200, OK); новых внешних вызовов не делать без разрешения. Поддержка output token limit этим сервисом не подтверждена.
- Реализованы импорт YAML с preview без автосохранения, Google final parts/finish_reason, диагностика усечения и Judge, отмена с состоянием cancelling, повтор отменённых строк, скрываемый preview инструкции.
- По предложению UX-дизайнера разделены Настройки/Запуск эксперимента; история и результаты рядом, детали строки в drawer, поиск/фильтры, явные Открыть/Повторить. Независимые критерии не агрегируются в одно число.
- Проверки: 36/36 backend unittest; production build; финальный полный Playwright 12/12. Новые browser tests проверяют YAML preview и HTTP consent без обращения к ЦРТ. Предыдущий сбой нового теста был из-за скрытого checkbox, исправлен нажатием видимой подписи с проверкой checked. GOMAXPROCS=2; прежняя нехватка памяти не помешала завершить текущий прогон.
- Проверка строгого UTF-8 выполнена для исходников, тестов и документации. git diff --check сохраняет прежнее предупреждение api/index.js о пустой строке EOF; пользовательские изменения не откатывались.
- Рабочие сервисы перезапущены только после проверки отсутствия queued/running/cancelling; health, frontend и новые OpenAPI-контракты проверены. Рабочие datasets/runs/snapshots не переписывались.
- Следующий шаг требует пользовательской проверки: новый layout, YAML из data/promt, подключение ЦРТ и реальная оценка выбранной моделью. Дальше — остальные providers исходного списка, расширение поиска/сортировки остальных таблиц и уточнение UX по обратной связи. Они НЕ объявляются реализованными. Новых P0-вопросов для текущего инкремента нет.
- Руководства: CRT_MKO_GUIDE.md, SEPARATE_EVALUATION_GUIDE.md; решения D-077—D-081. Доступ к файлам: WORKSPACE_ACCESS.md, прямой codex.exe --codex-run-as-apply-patch; ACL менять не нужно.

Ниже исторические checkpoints; при расхождениях актуален раздел от 2026-09-24.

## Актуальная точка — 2026-09-23

Новое: разрешённый один smoke ЦРТ МКО выполнен успешно (HTTP 200, OK, gemma3:4b). Не повторять: разрешение использовано. response.message.content — текст, done_reason — причина, prompt_eval_count/eval_count — usage. Подробности в RELIABILITY_UX_2026_09_23.md. Адаптер ещё не реализован, browser regression ещё не завершён, рабочее приложение не перезапущено.

Session 18432 прекращена: только своё дерево тестов PID 31688 остановлено через taskkill после подтверждения пути/родителей. Browser failures: Network Error и timeout при нехватке commit memory, PowerShell 800705af. YAML: 25/25 примеров читаются; 2 import tests прошли. Нужна финальная offline regression после освобождения памяти. Не запускать реальные calls ЦРТ без ответа на отправленный вопрос о synthetic smoke.

Продолжить по новому верхнему разделу PROJECT_STATE.md, RELIABILITY_UX_2026_09_23.md и UX_WORKSPACE_REVISION.md. Реализованы parsing/cancel/основной UX/YAML, но финальная проверка не завершена, провайдеры не добавлены. Последний backend: 31 tests до YAML; browser session 18432, GOMAXPROCS=2 после out-of-memory. Не путать результаты 28/10 предыдущего инкремента с текущими. Критически мало виртуальной памяти Windows; чужие процессы не останавливать. ЦРТ МКО без авторизации, ожидается разрешение на один synthetic generation smoke или образец ответа. Рабочее приложение не перезапускать до проверки и проверки отсутствия активных Run.

## Предыдущая точка — 2026-09-22, настройки эксперимента

Финальный прогон: 28/28 backend, build, 10/10 Playwright, UTF-8 21 файла. Следующий шаг — пользовательская проверка шести исправлений; открытых вопросов по требованиям нет. Реальные вызовы не делались; до restart активных Run 0. Упоминание выполняющегося regression ниже — промежуточная запись, финальный результат здесь.

Новое задание реализовано по RESULTS_REFINEMENT.md и D-075/D-076: повтор в исходном Run подтверждён владельцем, история попыток сохранена; текстовый эталон CSV, независимые шкалы, обработка пустых ответов и приоритет результатов над историей. 28 backend tests прошли; финальный browser regression выполняется. При первой browser-проверке найдена и исправлена пропажа mapping-panel после смены формата; новый тест checkbox переведён на видимый label Element Plus. Рабочие данные и старые completed не переписывались, реальные провайдеры не вызывались.

Исправления замечаний владельца завершены: открытие Prompt/Pipeline/Suite, сохранение новых копий без изменения оригиналов, ранняя валидация промпта, вложенные поля, preview первой строки без provider calls, Pipeline без ручного JSON, таблица критериев и ошибки рядом с действием. Основание: CONFIGURATION_UX.md, D-073/D-074. Пользователь ранее подтвердил успешную отдельную оценку.

Проверки: backend 24/24, build, Playwright 8/8. Новых P0 нет. Следующий шаг — проверка владельцем новых редакторов на реальной инструкции; затем согласованное планирование evaluator library/recovery. Не повторять прежний запрос подтверждения раздельной генерации и оценки. Рабочую БД и пользовательские изменения сохранять; доступ к файлам — по WORKSPACE_ACCESS.md.

## Предыдущая точка — 2026-09-18, раздельная генерация и оценка

- Владелец подтвердил раздельный поток (D-070). Реализован первый text-инкремент: generation Run получает ответы, evaluation Run оценивает сохранённые ответы без повторных candidate-вызовов. Старые snapshots/результаты сохранены.
- Генерация применяет PromptVersion.template из snapshot; {{field}} подставляется из input без eval. Недостающие переменные/неподдерживаемые схемы pipeline отклоняются до запуска. Правила оценки для генерации больше не обязательны; фиктивный score не создаётся, estimate считает только candidate calls.
- POST/GET /runs/{source_id}/evaluations: отдельный Run, source_run_id, snapshot Judge route/prompt/criteria и копии input/reference/output. Повторные оценки независимы. Строгая шкала 0..1, weighted score рассчитывается сервером; invalid JSON/шкала — failed с numeric_score=null.
- UI: «Оценить ответы», выбор судьи/правил/инструкции, количество вызовов до старта, отдельная страница результата и история оценок источника. В подробностях видны исходный ответ и rationale. Offline и legacy scores явно помечены тестовыми.
- Исправлена гонка начала worker до commit; SQL debug logging скрывает параметры. Миграция таблиц не требовалась. Ограничения: text-only Judge, один Judge route/prompt на оценку, один generate node; recovery после аварии и DAG остаются backlog.
- Проверки: 22/22 backend unittest, production build, 6/6 Playwright. Проверены exact provider prompt, отсутствие score при генерации, Judge-only calls, повторная оценка, invalid Judge response без нулевого score, сохранность source и snapshot удалённого Judge.
- E2E переведён на production preview (D-072) с изолированным backend вместо dev/HMR. Исправлены зависимость старого теста от пустой БД и закрытие multi-select до запуска. Финальный прогон зелёный; прежний ресурсный blocker не воспроизвёлся.
- Реальные providers не вызывались. Перед restart рабочего приложения проверено: активных Run 0. Нужен пользовательский smoke на одном ответе и доступной бесплатной Judge-модели по SEPARATE_EVALUATION_GUIDE.md.
- Следующий безопасный шаг: получить результат пользовательской проверки реального Judge; затем удобные формы критериев вместо JSON, evaluator library и устойчивое восстановление jobs. Новых продуктовых P0-вопросов нет; автоматическая оценка вместе с генерацией не добавляется.

## Предыдущая точка — 2026-09-18, компоненты и обновление Run

- Выделены общие RunResults, ExperimentConfiguration и useRunDetails. Удалён неиспользуемый Dataset/ModelRoute setup-код из Workbench; Home/Experiments пока остаются двумя режимами одной лёгкой страницы.
- Открытый незавершённый Run автоматически обновляется, временная ошибка повторяется; запросы не перекрываются, запоздалые ответы от предыдущего выбора игнорируются, уход со страницы останавливает polling. Экспорт и имена моделей из snapshot сохранены.
- Подтверждены существенные незакрытые ограничения: PromptVersion.template ещё не применяется executor, score — техническая заглушка, внешнего Judge нет. UI предупреждает об оценках. Это не результат регрессии текущего рефакторинга; полноценную оценку нельзя считать реализованной.
- Проверки: production build прошёл; исходный прогон E2E 5/5 прошёл. После добавления assertions заключительный полный прогон: 4/5, включая сквозной workflow, snapshot удалённой модели, предупреждение и три polling-теста. Навигация прервана Chrome ERR_INSUFFICIENT_RESOURCES; отдельный повтор дошёл до reload /models и превысил 30 секунд. Полностью зелёный финальный прогон не подтверждён: требуется освободить ресурсы машины и повторить npm.cmd run test:e2e. Backend не менялся, реальные providers не вызывались; рабочая БД не изменялась. Все изменённые файлы проверены на UTF-8. git diff --check указывает на прежнюю пустую строку EOF в src/api/index.js (файл не менялся в этом инкременте).
- D-067—D-069 фиксируют границы изменения. Рабочий прямой apply_patch и отличие от сломанной bat-обёртки описаны в WORKSPACE_ACCESS; менять ACL не требуется.
- Следующий шаг требует согласования требований: отдельная оценка сохранённых ответов или автоматическая оценка сразу при генерации. Предложение и ограничения — EVALUATION_NEXT_INCREMENT.md. После выбора сначала контракты/UX/тесты, затем реализация Prompt rendering и Judge. Legacy-удаление отложено до проверки нужных пользователю данных.

Ниже — история предыдущих инкрементов; при расхождении актуален этот раздел.

## Предыдущая передача — 2026-09-16

## Restore point

The local system is running:

- frontend: http://localhost:3000
- backend: http://localhost:8010
- launcher: powershell.exe -ExecutionPolicy Bypass -File scripts\run.ps1 -Action Restart

Runtime logs are in %LOCALAPPDATA%\LLMTester\runtime.

## Implemented and verified

- Universal v1 entities: Dataset, DatasetVersion, DatasetItem, PromptVersion, PipelineVersion, ModelRoute, EvaluationSuite, RunSnapshot, RunItem, Attempt, Result.
- Evaluation Workbench supports text Dataset JSON preview/publish, saved configuration selection, run estimate/launch, run history and snapshot/details.
- ModelRoute UI supports offline, Google and OpenRouter, and stores only env:VARIABLE credential references.
- Offline runner and Google/OpenRouter provider contracts are covered by 12 offline tests.
- The most recent successful checks were Python unittest discovery (12 tests) and frontend production build.

## Important constraints

- Do not reset or overwrite existing changes.
- Use C:\Users\zoode\AppData\Local\Programs\Python\Python311\python.exe for Python.
- Use npm.cmd, not npm, in PowerShell.
- Backend is port 8010; do not stop unrelated process on 8000.
- No keys are stored in repository, API responses, snapshots or logs.

## Next planned work

1. Add Dataset import from CSV and JSONL with non-persistent preview and explicit commit.
2. Add UI for custom Prompt/Pipeline/EvaluationSuite, replacing remaining convenience defaults.
3. Add export of Run results and browser E2E smoke.
4. Controlled real-provider smoke only after the owner provides environment variables containing keys.

## State of working tree

All implementation and documentation changes are intentionally uncommitted. The SQLite development database is llm-tester/backend/llm_tester.db.

## Update — CSV/JSONL import completed

- Implemented `POST /api/v1/datasets/import:preview` and `POST /api/v1/datasets/{version_id}/items:import`; both accept UTF-8 `.csv` or `.jsonl` multipart files, and preview remains non-persistent.
- CSV contract: `external_id`, plus JSON columns `input`, `reference`, `metadata`, `tags`. JSONL contract: one canonical DatasetItem JSON object per non-empty line.
- The Evaluation Workbench now supports file selection, preview, row-error display, explicit import commit and publish.
- Offline checks after this update: Python suite 13/13 and frontend production build passed. No service restart or real-provider call was performed after the source changes.
- Next planned work: replace the convenience base configuration action with custom Prompt/Pipeline/EvaluationSuite UI, then export and browser E2E smoke.
## Update — managed configuration, export and E2E completed

- Workbench has independent creation forms for PromptVersion, PipelineVersion and EvaluationSuite; new objects are selected for Run immediately.
- Run details support JSON reproducible bundle and flat CSV downloads. Dataset source fields, attempts and results are included; raw environment credential values are excluded and tested.
- Playwright was added as a dev dependency. `npm.cmd run test:e2e` uses installed Chrome, backend 8020, frontend 3010 and isolated `e2e_test.db`; the full browser scenario passed.
- Current automated gates: Python compileall, 13 backend tests, frontend production build, 1 Playwright E2E.
- Product work now reaches controlled real-provider smoke. The owner must set key environment variables locally and identify the Google/OpenRouter models to smoke; never place key values in chat or repository.
## Update — launcher verified across user contexts

- `scripts/run.ps1` now records per-process start-time ownership tokens and uses them for safe Stop/Restart. It no longer depends on WMI command-line access unavailable to nested PowerShell under the current user.
- Two consecutive Restart operations and Status passed; frontend 3000 and backend 8010 are running the current sources. Port 8000 was not touched.
- No saved external ModelRoute currently exists. Controlled provider smoke therefore requires the owner to set key environment variables locally and provide only the desired provider/model identifiers and variable names, never key values.
## Update — provider credentials, simplified UX and live smoke

- Windows User environment fallback fixes the repeated false `credential_unavailable` failure. Both saved external routes currently report `credential_available: true`; no key value is exposed or stored.
- Route forms are provider-specific, saved routes and credential status are visible, and a saved route can be restored explicitly. The recommended action creates/selects PromptVersion, PipelineVersion and EvaluationSuite together while preserving explicit domain objects.
- Provider failures are stored structurally and rendered as actionable Russian messages. A failed external call now also creates an Attempt with latency and safe error metadata.
- Live smoke Run `ec34d1fc-6c34-40cc-8179-b8508cd2bf08`: OpenRouter reached the provider and returned HTTP 402; Google `gemini-3.8-flash` timed out. Google Models API authenticated successfully, lists that exact model and declares `generateContent`; direct generation also timed out. The prior credential error is resolved.
- Latest gates: backend compileall; 15/15 backend tests; frontend production build; Playwright 1/1. Services were restarted and remain on frontend 3000/backend 8010. Temporary E2E artifacts were removed.
- External blocker: owner action is required to enable/fund OpenRouter billing. Google may be retried later or with another model selected from the account-specific model list. Never request or record raw key values.
## Update — editable routes, live model catalogs and bounded timeout

- Saved ModelRoute records now support PUT update and DELETE. Historical RunSnapshot definitions remain embedded and unchanged after route edit/delete.
- Workbench exposes user-facing saved models with Select/Edit/Delete, confirmation on delete, and no ModelRoute jargon in the primary flow.
- Google and OpenRouter model catalogs are fetched server-side. The UI provides searchable selection plus manual fallback. OpenRouter defaults to `openrouter/free` and filters to zero-price models unless the user explicitly disables «Только бесплатные модели». Google defaults to the user-verified `gemini-3.6-flash`.
- `timeout_seconds` is now a total wall-clock budget including retry/backoff; regression coverage prevents a 60-second setting from becoming two 60-second attempts.
- User live evidence: OpenRouter `openrouter/free` and Google `gemini-3.6-flash` both returned `PROVIDER_SMOKE_OK`. Live catalog verification returned both known Google models and placed 23 current zero-price OpenRouter models first.
- Latest gates: backend 18/18, frontend build passed, Playwright create/edit/run/delete 1/1 passed. A temporary live CRUD route was removed after verification.
- Next action requires owner UX verification in the running application; no credential or billing change is required for the free-first path.
## Update — quick comparison flow

- Owner accepted saved-model edit/delete as functionally sufficient; visual polish is deferred.
- The primary Workbench now starts with «Быстрый запуск»: newline-separated texts + one or more saved routes → fresh published DatasetVersion → ordinary immutable RunSnapshot.
- Reserved `quick-run-default-prompt`, `quick-run-default-pipeline` and `quick-run-default-suite` are reused instead of accumulating three hidden definitions per run. Quick runs disable judge-call estimation and focus on candidate outputs/latency/errors.
- The legacy offline demo button/handler was removed. Detailed Dataset/Prompt/Pipeline/Suite controls remain available below.
- Latest validation: frontend build passed; Playwright quick run + detailed run + exports + route edit/delete + legacy navigation passed 1/1. Backend baseline remains 18/18.
- Next owner check: quick run with the verified `openrouter/free` and/or `gemini-3.6-flash` routes. After acceptance, implement the model comparison summary matrix.
## Update — launcher stderr edge case

- `Stop-OwnedProcess` now treats `taskkill` stderr as non-terminal until the verified root PID is checked, then waits up to one second for process exit. Start-time ownership validation remains unchanged.
- Two consecutive Restart checks passed after the fix.
## Update — scenarios and information architecture — 2026-09-17

- Owner confirmed that quick comparison works.
- `docs/scenarios.md` was reviewed as a discovery draft and mapped to the universal v1 domain.
- Target primary sections are Home, Datasets, Models, Experiments and Runs. Evaluation and Settings appear only when they have independent usable workflows.
- Legacy Providers/Tasks/Test Runs are not part of the new product model. Remove them from primary navigation after replacement screens exist; keep temporary `/legacy/...` access until E2E/data compatibility is checked.
- `docs/INFORMATION_ARCHITECTURE.md` contains the detailed UX structure, dataset scope and migration order.
- No application code changed in this analysis pass.
- Next implementation: v1 Run summary matrix + item detail, followed by Workbench decomposition starting with Home and Runs.
## Update — Run summary and first UI split — 2026-09-17

- v1 Run detail now has a per-model summary (success/failure, score, latency, tokens and optional cost) and expandable per-item input/reference/output/attempt/result data.
- New `/runs` and `/runs/:runId` views provide addressable v1 history and restore details after refresh.
- Primary navigation contains only Home and Runs. Legacy screens moved out of the header to `/legacy/providers`, `/legacy/tasks` and `/legacy/test-runs`; old provider/task URLs redirect for compatibility.
- Frontend production build and Playwright E2E 1/1 passed. E2E covers the summary, expanded item, new Runs route and legacy compatibility redirect. Temporary E2E DB was removed.
- Next: extract Datasets and Models from the Workbench, then move detailed configuration to Experiments and leave quick start on Home.
## Update — launcher listener ownership — 2026-09-17

- Launcher now records actual 8010/3000 listener PIDs and start-time tokens, launches Vite directly through Node, normalizes duplicate process-scope PATH casing and writes unique per-launch logs recorded in `services.json`.
- Stop fallback always revalidates the token before `Stop-Process`.
- Two consecutive Restart checks passed in the current PowerShell context; final state PIDs equal listener PIDs and both services respond.
- In Codex-managed execution, use Process-scoped Bypass and invoke `.\scripts\run.ps1` in the current shell. Do not add a nested `powershell.exe`; normal interactive user instructions remain unchanged. See `docs/WORKSPACE_ACCESS.md`.
## Update — Datasets and Models routes — 2026-09-17

- Added `/datasets` for DatasetVersion preview/import/publish and saved-version listing.
- Added `/models` for v1 ModelRoute catalogs, credential status and create/edit/delete.
- Home no longer renders the long Dataset and ModelRoute forms; quick comparison still loads their saved v1 objects.
- Header now exposes Home, Datasets, Models and Runs. Legacy views remain direct-only under `/legacy/...`.
- Frontend build and the rewritten cross-route Playwright E2E passed 1/1. Temporary E2E DB was removed.
- Next: move Prompt/Pipeline/EvaluationSuite plus detailed estimate/start into `/experiments`, then simplify Home and remove dead setup code.

## Update — Dataset import diagnostics and viewing — 2026-09-17

- Dataset input has explicit JSON-array, JSONL-text and CSV/JSONL-file modes. JSONL accepts one object per line without commas or outer brackets and reports parser errors by line.
- DatasetItem validation is strict: `external_id` and object `input` are required; unknown top-level fields are rejected with row-level Russian diagnostics.
- The repository `test/dataset.jsonl` is syntactically valid UTF-8 JSONL but uses `id/transcript/reference_summary`. Live preview now explains this for all three rows instead of returning the truncated Pydantic heading. No silent alias mapping was introduced.
- Saved DatasetVersion rows can be opened and inspected through the new paginated items endpoint and UI dialog. Published versions remain immutable; revision and retention-safe archive/delete are explicit follow-up work.
- Latest gates: backend 18/18, frontend build, Playwright 1/1 including JSONL text and saved-version inspection. E2E DB removed; main services restarted on 3000/8010.
- Next owner check: manual JSONL, diagnostics for `test/dataset.jsonl`, and version viewing. Then design explicit field mapping and create-new-version UX before destructive deletion; `/experiments` remains the next navigation slice afterward.

## Update — browser multipart upload fixed — 2026-09-17

- Owner reproduced `Field required` only through the file picker. The shared Axios client forced `application/json` on FormData, so FastAPI received no multipart `file` field.
- Removed the global Content-Type override; Axios now derives JSON or multipart headers per request.
- Main Playwright E2E now uploads the repository `test/dataset.jsonl`, asserts 0/3 row diagnostics, then completes the canonical JSONL publish/view flow. Frontend build and E2E 1/1 passed.
- Main services must run the restarted frontend bundle on 3000; backend remains 8010.

## Update — explicit Dataset field mapping — 2026-09-17

- File preview now returns `source_fields` and supports an explicit text-dataset mapping: source ID, source text and optional source reference.
- UI suggests `id → external_id`, `transcript → input.text`, `reference_summary → reference` for the repository fixture, but requires an explicit «Применить сопоставление» action.
- Preview and commit share the same backend transformation. The accepted mapping is persisted in `DatasetVersion.schema_json.import_mapping`; a conflicting commit mapping is rejected.
- Latest gates: backend 18/18, frontend build, Playwright 1/1 using the actual `test/dataset.jsonl` and asserting 0/3 before mapping and 3/0 after mapping.
- Next owner check: upload that file, apply the visible suggestions, publish and inspect the three rows. Then implement create-new-version UX; deletion still requires a retention/reference decision.

## Update — source samples in Dataset mapping — 2026-09-17

- Mapping UI now renders the first three parsed source rows across detected fields, so choices can be validated by content rather than column names alone.
- Display values are capped at 500 characters; full values are still used for transformation/commit. Raw samples are preview-only and not persisted or logged.
- Backend 18/18, frontend build and Playwright 1/1 passed; E2E asserts three rows and visible transcript content from `test/dataset.jsonl`.
- Next owner check: mapping-table readability. Then implement create-new-version workflow.

## Update — noncanonical CSV can reach field mapping — 2026-09-17

- CSV preview no longer returns an early HTTP 422 when `external_id` is absent. It exposes headers/raw samples and canonical row errors so the same explicit mapping UI used for JSONL becomes available.
- Commit without a successful mapping remains rejected; canonical CSV behavior is unchanged.
- Backend 18/18, frontend build and Playwright 1/1 passed. Browser E2E includes an in-memory `id,transcript,reference_summary` CSV and asserts its sample value is visible.
- Next owner check: upload the reported CSV and apply mapping. Then implement Dataset revision UX.

## Update — CSV encodings and delimiters — 2026-09-18

- The reported repository file is `test/test1.csv` (not `test.csv`): Windows-1251, semicolon-delimited, with `id/transcript/reference_summary` headers.
- Import now detects UTF-8/BOM, UTF-16 BOM and Windows-1251; CSV delimiter detection supports comma, semicolon, tab and pipe. One-column silent fallback is replaced by an actionable unsupported-delimiter error.
- Preview/UI expose detected encoding and delimiter; commit stores them in `DatasetVersion.schema_json.import_source`.
- Gates: backend 18/18, frontend build, Playwright 1/1 using the exact `test/test1.csv` and asserting Windows-1251, semicolon and Russian sample text.
- Next owner check: reported CSV plus other delimiter variants. Then implement Dataset revision UX.

## Dataset revision workflow — 2026-09-18

- Реализован POST /api/v1/datasets/{dataset_id}/versions: пустой draft со следующим номером, проверкой принадлежности base_version_id и запретом второго draft. Published версии и строки сохраняются.
- В списке появился переход «Новая версия», форма принимает полный replacement-набор через существующий preview/import. Версия создаётся при сохранении; отмена открытия формы не создаёт записей.
- UI показывает номер и название Dataset, поддерживает переход к имеющемуся draft. Построчное редактирование и удаление не реализованы.
- Проверки: backend 18/18, production build, Playwright 1/1: v1 → v2 → публикация → просмотр; backend подтверждает сохранность строк v1.
- Следующий шаг: UX-проверка полной замены данных, затем выделение /experiments. Отдельно укрепить восстановление после частичного save (commit успешен, publish не завершён): повторный commit сейчас может упереться в duplicate external_id; атомарное сохранение/публикация остаётся открытым техническим пунктом.
## Experiments navigation and recoverable Dataset publication — 2026-09-18

- /experiments содержит подробные формы Prompt/Pipeline/EvaluationSuite, estimate/start; Главная оставляет быстрый запуск и результаты. Общий Workbench временно используется в двух явных режимах; удаление старого неиспользуемого setup-кода остаётся следующим техническим шагом.
- Выбранная конфигурация сохраняется в sessionStorage текущей вкладки. /evaluation перенаправляет в /experiments.
- Dataset save запоминает draft, сверяет все существующие строки с preview и при полном совпадении повторяет только публикацию. «Продолжить» загружает все строки черновика постранично. При несовпадении данные не перезаписываются.
- Playwright 1/1 прошёл с искусственным обрывом publish v2, повторной публикацией, переходом Главная → Эксперименты, подробным запуском и экспортом. Backend-контракт в этом инкременте не изменён.
- Следующая пользовательская проверка: расположение подробных настроек в Экспериментах. Следующий технический шаг: вынести переиспользуемые компоненты и удалить мёртвый setup-код Workbench.
## Синхронизация меню с маршрутом — 2026-09-18

Активный раздел определяется URL, поэтому переходы кнопками, browser Back и refresh показывают верную вкладку. Вложенный /runs/:id относится к «Запускам». Кнопки названы «Перейти в …», обозначая переход в самостоятельный раздел. Сборка и E2E 2/2 прошли, включая отдельную проверку трёх переходов и истории браузера. Следующий шаг: продолжить выделение компонентов Workbench; новых P0-вопросов нет.
