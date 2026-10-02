# Текущее состояние проекта

## Настраиваемый ЦРТ и наглядный прогресс — 2026-10-02

- Реализованы четыре замечания владельца по CRT_PROGRESS_REFINEMENT.md, решения D-083—D-085. В runtime-коде и scripts больше нет прежнего сервера/порта ЦРТ.
- ModelRoute.capabilities.base_url задаёт полный адрес API, каталог/генерация используют его; HTTP требует согласия, HTTPS нет. Старые подключения требуют ручного заполнения адреса через «Модели → Изменить». Новые snapshots фиксируют адрес; старые не менялись. Повтор snapshot без адреса отклоняется до сети, нужен новый запуск.
- RunItem=running и Attempt сохраняются до запроса. Общая полоса активных запусков во всех разделах; проценты, spinner, ошибки, номер повтора строки и HTTP-попытки; таймер ожидания в закреплённой панели, закреплённый столбец статуса таблицы. История обновляется автоматически.
- Явные think/thought/analysis отделяются от финального текста ЦРТ, оригинал сохраняется. Drawer показывает обычный текст, JSON раскрывается отдельно. Исторические ответы получают display_text без перезаписи БД. Read-only проверка двух сохранённых ответов ЦРТ: разметка отделилась, финальный текст сохранился в обоих.
- Диагностика Run 06151d74: 2 успешных из 6; последние ошибки — 2 timeout (~120 секунд) и 2 execution_error. Причина старых execution_error не доказана (raw HTTP bodies отсутствуют). Новые не-JSON/error-envelope распознаются отдельно. Таймаут сервера этим изменением не устранён: для нового запуска можно увеличить ожидание подключения, затем при необходимости проверять сервер. Реальных вызовов агент не делал.
- Проверки: backend 40/40, production build, полный Playwright 14/14; после финального закрепления столбца повторены build и 4/4 run-details сценария. Скриншот с synthetic fixture просмотрен. UTF-8 и git diff --check пройдены. Первый browser-прогон 12/13 исправлен выбором созданной опции модели в тесте, финальные проверки зелёные.
- Перед перезапуском активных рабочих Run: 0. Launcher Restart завершён, frontend и /health HTTP 200, новый OpenAPI-контракт проверен. Рабочие datasets/runs/snapshots не переписывались.
- Следующий шаг: владелец задаёт актуальный URL ЦРТ в существующих подключениях, проверяет новый интерфейс и выполняет новый запуск с нужным timeout. По прежним execution_error для точной причины потребуется журнал сервера или новый ответ с уточнённой диагностикой. Новых P0-вопросов нет. Версионирование — отдельный проверенный инкремент по D-082.


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

## Актуальная точка — 2026-09-23, надёжность и UX (работа продолжается)

ЦРТ МКО smoke завершён по отдельному разрешению владельца: ровно один POST, gemma3:4b/stc_llama, безличный текст «Ответь только OK», HTTP 200, ответ OK. Формат прямой: message.content, done, done_reason, prompt_eval_count/eval_count; не choices/data. Контракт зафиксирован в RELIABILITY_UX_2026_09_23.md. Следующий шаг интеграции — отдельный adapter и offline fixtures, без новых real calls. Прежний вопрос о формате ответа закрыт; финальная регрессия/ограничение памяти и реализация адаптера остаются незавершёнными.

Последний checkpoint: все 25 пользовательских YAML из data/promt распарсились; 2/2 новых import unit tests прошли отдельно (31 остальных прошли ранее). Browser regression не завершён: после build с GOMAXPROCS=2 были Network Error/таймауты на критически низкой памяти; собственное дерево Playwright PID 31688 остановлено, включая тестовые backend 8020 и preview 3010. Рабочие процессы 8010/3000 не останавливались. PowerShell также падал 800705af. Перед следующим прогоном освободить память и проверить состояние ресурсов; финальный E2E зелёным НЕ считать. Выпуск/перезапуск новых изменений не выполнен.

- Обратная связь из 10 пунктов: RELIABILITY_UX_2026_09_23.md. По просьбе владельца подключён UX-дизайнер; результат UX_WORKSPACE_REVISION.md.
- В коде: Google final parts без thought, finish_reason, ошибка truncated_response, настраиваемый output token limit; cancelling/cancelled, безопасный повтор отменённых строк; скрываемый preview; явные действия строки; компактная таблица и drawer; поиск/фильтры истории и примеров; режимы Запуск/Настройки.
- Примеры YAML получены в data/promt. Добавлен безопасный text-only импорт через /prompts:import (PyYAML 6.0.3 установлен), preview в редакторе; service settings не переносятся. Новые import tests добавлены, ещё требуют выполнения.
- Проверки на текущем этапе: 31 backend tests прошли до добавления YAML. Первый browser build упал с out-of-memory; повтор с GOMAXPROCS=2 собрался, браузерный прогон ещё идёт. Windows: около 410 MiB свободной RAM и 36 MiB свободной виртуальной памяти; возможна необходимость помощи владельца. Не заявлять завершение/зелёный E2E.
- ЦРТ МКО: владелец подтвердил отсутствие авторизации. GET schema и GET models прочитаны, 8 моделей; адаптер ещё не реализован, schema completion response пустая. Запрошено разрешение на один безличный smoke «Ответь только OK» или пример успешного ответа. Новые внешние генерации НЕ выполнялись. Groq docs изучены как следующий стандартный provider; адаптер ещё не добавлен.
- Следующий безопасный шаг: закончить тесты после освобождения памяти, исправить регрессию если есть, затем ЦРТ МКО и расширение providers. Приложение с этим инкрементом пока НЕ перезапускалось; рабочие snapshots не менялись.

## Предыдущая точка — 2026-09-22, настройки эксперимента

Финальная проверка нового инкремента: 28/28 backend tests, production build, 10/10 Playwright; изменённые файлы существуют и читаются строгим UTF-8. Перед restart активных Run: 0. Реальные провайдеры не вызывались. Следующий безопасный шаг — пользовательская проверка текстового эталона CSV, выборочного повтора в исходном Run и независимых шкал. Прежний git diff --check warning о пустой строке EOF в api/index.js не относится к функциональным изменениям.

Новое продолжение — RESULTS_REFINEMENT.md, D-075/D-076. Владелец подтвердил повторы в исходном запуске. Реализованы текстовый/JSON эталон CSV с preview, retry выбранных RunItem в том же Run с сохранением Attempt/Result и snapshot, empty_response вместо ложного успеха, результаты выше истории с переходом после запуска, признаки generation/evaluation, независимые критерии min_score/max_score и отдельные колонки/экспорт без общего score. Старые weighted suites совместимы. Ограничения: повтор только terminal completed/completed_with_errors/failed; отменённые и legacy — пока нет. 28/28 backend tests прошли; финальный browser regression выполняется. Новых P0-вопросов нет.

- Владелец подтвердил успешный запуск отдельной оценки. Исправления по его замечаниям реализованы по CONFIGURATION_UX.md и D-073/D-074.
- Сохранённые PromptVersion, PipelineVersion и EvaluationSuite открываются в формах. Изменения сохраняются новой копией с новым ID; оригиналы и RunSnapshot не перезаписываются.
- Промпты проверяются при сохранении; поддержаны вложенные поля {{input.text}}/{{customer.name}} и обычные JSON-примеры. Ошибки объясняют синтаксис или недостающее поле. Предпросмотр инструкции на первой строке датасета не вызывает модель.
- Pipeline создаётся без ручного JSON: один шаг генерации; это порядок обработки, не схема ответа. Критерии редактируются таблицей с весами и порогом. Настройка судьи объясняет назначение инструкции и критериев и позволяет открыть сохранённую инструкцию.
- Ошибки проверки/запуска расположены рядом с кнопками. Проверки: 24/24 backend tests, production build, 8/8 Playwright (включая сохранность оригиналов и видимость ошибок).
- Новых P0-вопросов нет. Следующий безопасный шаг: пользовательская проверка новых форм на своём промпте; затем планирование evaluator library и восстановления прерванных jobs. Реальные провайдеры агентом не вызывались.

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

## Фаза

Первый vertical slice LLM Evaluation Workbench реализован и проверен offline. Legacy Task/TestCase не расширялся.

## Сделано

- Добавлены persistent-сущности v1: Dataset, DatasetVersion, DatasetItem, Asset, PromptVersion, PipelineVersion, ModelRoute, EvaluationSuiteVersion, RunSnapshot в составе Run, RunItem, Attempt и EvaluationResult.
- DatasetVersion остаётся draft до публикации; опубликованную версию нельзя изменять. Run создаётся только из опубликованного DatasetVersion.
- API /api/v1 создаёт версии, импортирует items с preview, публикует DatasetVersion, оценивает объём Run, создаёт durable Run и выдаёт статус и результаты.
- Snapshot Run содержит развёрнутые определения DatasetVersion, Pipeline, PromptVersions, ModelRoutes, EvaluationSuite и ExecutionPolicy. Ключи и raw secrets в него не попадают.
- Очередь запускает отдельную DB-session через background task. Offline executor записывает RunItem, Attempt, структурированный Judge result, progress и terminal status. Ошибка одного item ведёт к completed_with_errors.
- Добавлен минимальный экран Evaluation: одной кнопкой создаёт offline fixture, запускает Run и отображает progress и output.
- Добавлен tests/test_evaluation_v1.py: интеграционный сценарий Dataset → publish → versions → estimate → queued Run → completed result.

## Проверка

- Python 3.11: python -m compileall -q app tests — успешно.
- Offline integration test: python -m unittest tests.test_evaluation_v1 -q — успешно, 1 test.
- Frontend: npm.cmd run build — успешно.
- Зависимости backend установлены в C:\Users\zoode\AppData\Local\Programs\Python\Python311; обычная команда python у Antony Chub по-прежнему указывает на WindowsApps alias. Для backend использовать абсолютный путь к Python или настроить PATH.
- В PowerShell policy блокирует npm.ps1; работают npm.cmd install и npm.cmd run build.
- Vite сообщает только warning о крупном vendor chunk; сборка успешна.

## Следующий безопасный шаг

Подключить реальные provider adapters к v1 ModelRoute, добавить безопасное хранение ключей и real-provider smoke tests. Затем развить UI от offline-demo до управляемых Dataset/Prompt/Pipeline/Route/Suite.


## Локальный запуск

- Добавлен scripts/run.ps1: запускает backend и frontend в фоне, хранит PID и логи в LOCALAPPDATA\LLMTester\runtime.
- Команды: .\scripts\run.ps1 -Action Start, Restart, Stop или Status; параметр -OpenBrowser открывает интерфейс после старта.


## Исправление локального запуска

- Порт 8000 занят независимым приложением HealthOS. LLM Tester использует backend-порт 8010, а Vite proxy направляет /api на http://localhost:8010.
- Скрипт запуска управляет своим деревом npm/vite и не останавливает чужой сервис на 8000.
- Активная вкладка верхнего меню получила контрастный фон и белый текст.


## Delivery plan

Актуальный порядок работ и QA-gates зафиксированы в docs/DELIVERY_PLAN.md. Следующая активная фаза: Этап 1 — QA baseline и закрытие foundation.


## QA baseline: прогресс

- Добавлена QA traceability matrix: docs/QA_BASELINE.md.
- Offline suite расширен до 5 проверок: snapshot/results, immutable DatasetVersion, policy/Judge validation, capability rejection, cancel и completed_with_errors.
- Найден и исправлен P0-дефект: отсутствующий DatasetItem больше не выдаёт пустой успешный result.
- Проверки: unittest tests.test_evaluation_v1 — 5/5 успешно; frontend production build — успешно.
- Незакрыто: ручной browser smoke для всех legacy вкладок и автоматизированный E2E; provider contract tests относятся к этапу 2.

- Исправлен QA browser-smoke дефект Test Runs: /api/tasks/runs больше не перехватывается маршрутом /tasks/{task_id}; endpoint возвращает 200.


## Provider foundation: прогресс

- Добавлен docs/PROVIDER_ADAPTER_CONTRACT.md и изолированный v1 contract для Gemini и OpenRouter.
- Offline contract tests проверяют payload local image: Gemini inlineData/mimeType и OpenRouter image_url data URL.
- ModelRoute принимает только credential_ref формата env:NAME; SQLite-миграция совместима с текущей локальной БД.
- Проверки: 9 offline tests успешно. Следующий шаг: соединить runner с adapter и добавить response/error normalization без live вызова до smoke.

- Runner подключён к v1 adapter contract: offline route остаётся локальным; Google/OpenRouter используют credential_ref только при execution, timeout и retry для timeout/429/5xx/network errors.
- Ошибки сохраняются как безопасные codes/messages. QA suite: 10/10 успешно.

- Provider contract suite расширен до 12 тестов: успешные Google/OpenRouter responses и retry 429 проверяются через MockTransport без сети.
- Добавлены read-only v1 endpoints GET /prompts, /pipelines, /model-routes, /evaluation-suites для следующего управляемого UI.


## Управляемый запуск из UI

- Добавлен GET /api/v1/dataset-versions; вместе с существующими read-only v1 endpoints он даёт интерфейсу список сохранённых определений.
- Evaluation Workbench теперь позволяет выбрать опубликованную DatasetVersion, PromptVersion, PipelineVersion, один или несколько ModelRoute и EvaluationSuite, получить estimate и запустить Run. Demo-кнопка по-прежнему создаёт изолированный offline пример.
- Проверки: Python compileall; unittest discover -s tests -p 'test_*.py' -q — 12/12; frontend production build — успешно.
- Следующий безопасный шаг: добавить UI создания и импорта DatasetVersion с preview/commit/publish, затем экран истории Run с деталями попыток и результатов.


## Создание DatasetVersion из UI

- Evaluation Workbench получил форму текстового Dataset: название и JSON-массив строк с external_id/input.
- POST /api/v1/datasets/items:preview проверяет строки без сохранения. При успешной проверке UI создаёт Dataset, commit-ит строки и публикует версию; созданная версия автоматически выбирается для следующего Run.
- Проверки: чистый preview API проверен ответом duplicate-ID без изменения данных; Python suite — 12/12; frontend production build — успешно; локальные сервисы перезапущены.
- Следующий безопасный шаг: вывести историю Run и снимок конфигурации, затем добавить просмотр нормализованных Attempt/Result.


## Уточнение UX списка конфигураций

- Кнопка обновления переименована в «Загрузить сохранённые объекты»: она только перечитывает DatasetVersion, PromptVersion, PipelineVersion, ModelRoute и EvaluationSuite с API и не очищает форму.
- Список DatasetVersion показывает имя датасета и номер версии. После публикации UI подтверждает имя созданного датасета и сообщает, что эта версия уже выбрана для Run.
- Проверки: Python suite 12/12, frontend production build успешно; регрессия list DatasetVersion проверяет dataset_name.


## Recovery point — 2026-09-16

A complete restart handoff is in docs/SESSION_HANDOFF.md. Both services are running and responded successfully: frontend 3000, backend 8010. The next implementation task is CSV/JSONL Dataset import with preview/explicit commit. No provider key or owner decision is needed until the controlled real-provider smoke stage.

## Доступ к workspace — 2026-09-16

- Диагностирована разница владельца (`ZOODERZ\zoode`) и текущего пользователя (`ZOODERZ\Antony Chub`): ACL позволяет Modify, но Git выдавал `dubious ownership`.
- Для текущего пользователя добавлен точный Git `safe.directory` `E:/Projects/llm_test`; `git status` после этого работает.
- Корень не является NTFS reparse point. Ошибка Codex `apply_patch` про reparse point — дефект интеграции; разрешённый обход и границы зафиксированы в `docs/WORKSPACE_ACCESS.md`.
- Смена owner требует администратора или владельца `zoode`; текущему пользователю Windows отказал в ownership privilege. Не повторять рекурсивный `takeown` в обычной разработке.
- Следующий безопасный шаг по продукту остаётся прежним: CSV/JSONL Dataset import с preview и explicit commit. Начатые API-заготовки импорта не сохранены, чтобы не оставлять непроверенную частичную реализацию.
## CSV/JSONL Dataset import — 2026-09-16

- Реализован универсальный импорт DatasetItem из UTF-8 CSV и JSONL: CSV использует `external_id` и JSON-колонки `input`, `reference`, `metadata`, `tags`; JSONL содержит один канонический DatasetItem на строку.
- `POST /api/v1/datasets/import:preview` разбирает файл только в памяти, сообщает `source_format`, counts и построчные ошибки без создания Dataset или DatasetVersion. `POST /api/v1/datasets/{version_id}/items:import` повторно разбирает файл и сохраняет только полностью валидный набор в draft-версию.
- Evaluation Workbench позволяет выбрать JSON-массив либо CSV/JSONL, увидеть ошибки строк и сохранить/опубликовать только успешный preview. Изменение источника или JSON очищает предыдущий preview.
- Проверки: Python compileall; `unittest discover -s tests -p 'test_*.py' -q` — 13/13 успешно; frontend `npm.cmd run build` — успешно. Сеть и provider keys не использовались.
- Следующий безопасный шаг: UI создания custom PromptVersion, линейного PipelineVersion и EvaluationSuite вместо convenience «Базовых элементов конфигурации»; затем export результатов и browser E2E smoke.
## Custom configuration, Run export и browser E2E — 2026-09-16

- Convenience-карточка базовой конфигурации заменена отдельными формами PromptVersion, PipelineVersion и EvaluationSuite. Каждый объект сохраняется независимо и автоматически выбирается для следующего Run; ModelRoute остаётся отдельной формой.
- Добавлен `GET /api/v1/runs/{run_id}/export?format=json|csv`. JSON bundle включает snapshot, DatasetItem, attempts и results; CSV даёт плоскую строку на RunItem. Offline test подтверждает отсутствие значения environment credential в обоих форматах.
- Добавлен Playwright E2E с изолированной БД и сервисами 3010/8020: Dataset → custom configuration → estimate → completed Run → JSON/CSV downloads → legacy navigation. Последний прогон: passed.
- Проверки: Python compileall; offline suite 13/13; frontend production build; Playwright 1/1 — успешно. E2E-артефакты и временная БД удалены после проверки.
- Следующий этап, требующий участия владельца: controlled real-provider smoke. Нужны локально заданные environment variables с ключами и подтверждённые provider/model identifiers; ключи не передавать в чат и не сохранять в репозитории.
## Надёжность launcher — 2026-09-16

- Исправлена остановка процессов между разными Windows users/sandbox-контекстами: `services.json` теперь хранит PID и start-time ownership token для backend/frontend. Stop/Restart проверяет token и не зависит от недоступной дочернему PowerShell WMI command line.
- `taskkill /T` считается успешным по фактическому исчезновению корневого PID, поскольку дочерний Vite может завершиться раньше и дать ложный non-zero exit code.
- Защита чужих процессов сохранена: отсутствующий token или несовпадение start time запрещает остановку.
## Provider credentials, UX и controlled smoke — 2026-09-16

- Устранена причина `credential_unavailable` на Windows: resolver сначала читает окружение backend-процесса, затем persistent User environment текущего пользователя. Значения ключей не возвращаются API; `GET /api/v1/model-routes` сообщает только `credential_available`.
- Workbench хранит отдельный черновик полей для каждого provider, показывает сохранённые ModelRoute и состояние ключа. Выбор сохранённого маршрута восстанавливает его модель, имя environment variable и timeout.
- Основной путь разбит на четыре шага. PromptVersion, линейный PipelineVersion и EvaluationSuite можно создать и выбрать одной кнопкой; ручные формы оставлены в «Расширенных настройках».
- Ошибки внешнего provider теперь сохраняются как безопасные `code`, `message`, `retryable`, включая неуспешный Attempt. UI показывает название provider/model и понятные причины для billing/quota, timeout, network и credential errors.
- Controlled smoke Run `ec34d1fc-6c34-40cc-8179-b8508cd2bf08` подтвердил доступность обоих credentials и отсутствие прежней ошибки. OpenRouter `google/gemini-2.5-flash` вернул HTTP 402 — требуется billing/credits. Google `gemini-3.8-flash` завершился timeout; Google Models API с тем же ключом успешно подтвердил модель и `generateContent`, но прямой generation также истёк по timeout. Контрольный `gemini-2.5-flash` вернул 404 и не является подходящей заменой в текущем аккаунте/API.
- Проверки: Python compileall успешно; backend tests 15/15; frontend production build успешно; Playwright E2E 1/1. Рабочие frontend 3000 и backend 8010 перезапущены на актуальных исходниках.

## Следующий безопасный шаг

- Для продолжения live-проверки OpenRouter владельцу нужно проверить billing/credits в OpenRouter.
- Для Google повторить `gemini-3.8-flash` позже либо выбрать другую модель из доступного конкретному ключу списка. До этого продуктовую работу можно продолжать offline: следующий UX-инкремент — provider preflight/diagnostics и сокращённый мастер первого запуска без ручного знания внутренних versioned-сущностей.
## ModelRoute management, provider catalogs и total timeout — 2026-09-16

- Подтверждены пользовательские live-запуски: OpenRouter `openrouter/free` завершился успешно за 3,6 с; Google `gemini-3.6-flash` — успешно за 2,45 с. Эти модели теперь являются безопасными стартовыми значениями формы.
- Добавлены `PUT` и `DELETE /api/v1/model-routes/{id}`. Сохранённое подключение можно изменить на месте или удалить; исторические RunSnapshot/RunItem не меняются и остаются читаемыми.
- Добавлен `GET /api/v1/provider-models`: Google catalog берётся из Models API и фильтруется по `generateContent`; OpenRouter catalog нормализует model metadata и zero pricing. Credential разрешается только backend-ом, raw key не возвращается.
- Workbench получил searchable model picker, ручной fallback, кнопку обновления каталога и включённый по умолчанию OpenRouter-фильтр «Только бесплатные модели». На момент проверки API вернул 41 Google generation model и 443 OpenRouter model, включая 23 бесплатных; `openrouter/free` располагается первым.
- Таблица сохранённых моделей поддерживает «Выбрать», «Изменить», «Удалить» с подтверждением. Основной UI больше не требует знания термина ModelRoute.
- Исправлена семантика timeout: `timeout_seconds` теперь общий wall-clock бюджет одного RunItem, включая retry/backoff. Ранее run `1654e692-257b-4e5d-b610-210acc17cc4a` занял 114,5 с при timeout 60 с из-за двух последовательных попыток.
- Проверки: backend compileall; backend tests 18/18; frontend production build; Playwright E2E 1/1 с create → edit → run → delete; live catalog обоих providers; временный CRUD probe удалён.

## Следующий безопасный шаг после проверки владельцем

- Владелец проверяет в рабочем UI редактирование/удаление старых подключений и выбор моделей из каталогов. После UX-приёмки следующий продуктовый инкремент — мастер первого запуска, объединяющий Dataset, подключение модели и рекомендуемую оценку без показа внутренних versioned-сущностей.
## Владелец принял route management; быстрый запуск — 2026-09-16

- Владелец подтвердил, что редактирование и удаление сохранённых моделей функционально работает. Визуальная полировка CRUD отложена.
- Добавлена карточка «Быстрый запуск»: несколько непустых строк преобразуются в DatasetItems, пользователь выбирает сохранённые модели и запускает benchmark одной кнопкой. До запуска показывается число примеров, моделей и candidate calls.
- Быстрый путь создаёт свежий published DatasetVersion и обычный RunSnapshot, а зарезервированные `quick-run-default-*` PromptVersion/PipelineVersion/EvaluationSuite создаёт один раз и переиспользует. `judge_enabled=false`; быстрый результат предназначен для сравнения ответов, ошибок, usage и latency без ложного LLM Judge.
- Выбор/создание модели синхронизируется с быстрым запуском; недоступные credentials нельзя выбрать. Результат попадает в общую историю и поддерживает существующие JSON/CSV exports.
- Старый конкурирующий offline-demo path удалён из основного UI.
- Проверки: frontend production build успешно; Playwright E2E 1/1 за 1,1 мин проверил быстрый Run, затем полный подробный Run, exports, edit/delete модели и legacy navigation. Backend baseline остаётся 18/18.

## Следующий безопасный шаг после UX-проверки

- Владелец проверяет быстрый запуск на одной/двух сохранённых внешних моделях. Следующий самостоятельный инкремент — summary matrix по моделям: success/error rate, latency, usage/cost и переход к per-item details без чтения технической таблицы RunItem.
## Launcher follow-up — 2026-09-16

- После внедрения быстрого запуска обнаружен и исправлен edge case Restart: stderr `taskkill /T` больше не прерывает `Stop-OwnedProcess` до фактической проверки подтверждённого root PID. Ownership token и защита чужих процессов сохранены.
- Два последовательных Restart после исправления прошли; frontend 3000 и backend 8010 поднялись штатно.
## UX/IA review — 2026-09-17

- Владелец проверил быстрый запуск: flow работает.
- Изучен новый discovery-черновик `docs/scenarios.md`. Он подтверждает отдельные рабочие области Dataset, моделей, конфигурации эксперимента, evaluation/Judge и результатов.
- Фактический `EvaluationWorkbenchView` содержит 459 строк и смешивает быстрый запуск, Dataset, ModelRoute, Prompt/Pipeline/Suite, запуск, историю и detail. Он признан временным vertical-slice экраном, а не целевой информационной архитектурой.
- Legacy-вкладки `Providers`, `Tasks`, `Test Runs` используют старые сущности и не будут развиваться. Решено убрать их из основной навигации после появления v1 route-level экранов, временно сохранив только `/legacy/...` совместимость.
- Создан `docs/INFORMATION_ARCHITECTURE.md`; обновлены requirements, architecture, UX flow, delivery plan, decision log и documentation map.
- Код в ходе аналитического этапа не менялся.

## Следующий безопасный шаг

Реализовать summary matrix и item detail для v1 Run, затем начать декомпозицию Workbench с выделения Главной и Запусков. После появления заменяющих экранов обновить header и перенести legacy views под `/legacy/...`. Не вводить сущность Project и не удалять legacy API до отдельной проверки необходимости данных.
## Run summary и начало декомпозиции — 2026-09-17

- В деталях v1 Run добавлена сводка по ModelRoute: completed/total, failures, average score, average total attempt latency, total tokens и cost при наличии данных provider.
- Таблица отдельных примеров показывает external_id и раскрывает input/reference, output/error, attempts и evaluator results.
- Добавлен самостоятельный v1 экран `/runs` и адресуемый detail `/runs/:runId`; выбранный Run восстанавливается после refresh.
- Основная навигация теперь содержит только «Главная» и «Запуски». Старые Providers/Tasks/Test Runs убраны из header и доступны временно по `/legacy/providers`, `/legacy/tasks`, `/legacy/test-runs`; старые `/providers` и `/tasks` перенаправляются в legacy.
- Проверки: frontend production build успешно; Playwright E2E 1/1 проверяет summary, раскрытие item detail, новый Runs route, отсутствие legacy-пунктов в header и прямой compatibility redirect.
- Временная E2E SQLite база удалена после прогона.

## Следующий безопасный шаг

Выделить из Workbench самостоятельные v1-разделы «Датасеты» и «Модели» с переиспользуемыми компонентами. Затем оставить на Главной быстрый запуск/недавние Runs, а полную конфигурацию перенести в «Эксперименты». Не удалять legacy API до завершения миграции и проверки данных.
## Launcher race — 2026-09-17

При развёртывании нового frontend `taskkill` успешно завершал верифицированные backend/frontend деревья, но root PID не всегда исчезал за прежнее окно 1 секунду, поэтому Restart выдавал ложную ошибку. Ownership start-time tokens совпали; ручная остановка тех же подтверждённых PID прошла, сервисы затем штатно запущены. Принято увеличить только bounded polling verified PID до 5 секунд, не ослабляя защиту чужих процессов.
## Launcher final verification — 2026-09-17

- Причина серии ложных Restart failures разложена на три Windows-особенности: временный npm wrapper вместо listener PID, дубли `PATH/Path` во вложенной sandbox-оболочке и удержание redirect handles.
- Launcher теперь хранит PID фактических listeners и start-time tokens, повторно сверяет token перед fallback stop, запускает Vite напрямую через Node и использует уникальный launch ID для четырёх логов. Активные log paths сохраняются в `services.json`.
- Для Codex-проверки используется текущий PowerShell с Process-scoped execution-policy bypass, а не дополнительный вложенный `powershell.exe`. Правило записано в `docs/WORKSPACE_ACCESS.md`.
- Два последовательных Restart прошли. Финальный state: backend и listener PID совпадают; frontend и listener PID совпадают; frontend 3000 и backend 8010 отвечают.
## Датасеты и модели выделены из Главной — 2026-09-17

- Добавлен самостоятельный `/datasets`: JSON/CSV/JSONL preview, validation, explicit save/publish и таблица сохранённых DatasetVersion.
- Добавлен самостоятельный `/models`: provider-specific drafts, Google/OpenRouter catalog, free-only filter, credential availability, create/edit/delete ModelRoute и timeout.
- Верхнее меню теперь содержит «Главная», «Датасеты», «Модели», «Запуски». Подробные формы Dataset и ModelRoute удалены с Главной; быстрый запуск продолжает перечитывать опубликованные версии и сохранённые маршруты через v1 API.
- E2E переписан на новый поток между route-level разделами и прошёл 1/1: Dataset → ModelRoute create/edit → Home quick run → detailed run/export → ModelRoute delete → Runs/detail → legacy redirect.
- Frontend production build прошёл. Временная E2E SQLite база удалена.

## Следующий безопасный шаг

Создать самостоятельный раздел «Эксперименты», перенести туда PromptVersion/PipelineVersion/EvaluationSuite и подробную форму estimate/start. После этого оставить на Главной быстрый запуск и компактные ссылки/недавние Runs; удалить оставшийся неиспользуемый setup-код из Workbench.
## Dataset import defect analysis — 2026-09-17

- Проверен `test/dataset.jsonl`: файл является валидным UTF-8 JSONL, но использует неканонические поля `id`, `transcript`, `reference_summary` вместо `external_id`, `input`, `reference`.
- Реальный preview API вернул 0/3 valid, но backend обрезал Pydantic detail до бесполезного `1 validation error for DatasetItemInput`.
- Ручной textarea был подписан как JSON-массив, поэтому JSONL без запятых выдавал технический browser parser error. Дополнительно пример пользователя требует объект `input: {"text": ...}`, а не последовательность `"input": "text": ...`.
- Принято: отдельный JSONL textarea mode, русские построчные validation errors и явные canonical examples. Silent field alias mapping запрещён; будущий mapping должен быть previewable и versioned.
- Published DatasetVersion остаётся immutable. До безопасной delete/retention policy добавляется просмотр данных; изменение должно создавать новую версию, а не мутировать опубликованную.

## Dataset import validation and version inspection — 2026-09-17

- `/datasets` теперь явно разделяет JSON-массив, JSONL-текст и файл CSV/JSONL. JSONL разбирается построчно: запятые и внешние `[]` не требуются; синтаксическая ошибка содержит номер строки и подсказку по выбранному формату.
- Канонический DatasetItem требует `external_id` и объект `input`. Неизвестные поля верхнего уровня отклоняются, чтобы не терять данные молча. Preview возвращает русские причины по каждой строке и автоматически раскрывает их в UI.
- `test/dataset.jsonl` подтверждён как корректный UTF-8 JSONL, но не как канонический Dataset: его `id`, `transcript`, `reference_summary` требуют явного mapping. Live preview теперь прямо сообщает обе отсутствующие canonical-пары и все неизвестные поля для каждой из 3 строк.
- Добавлен `GET /api/v1/dataset-versions/{version_id}/items` и действие «Просмотреть» в списке версий. UI показывает первые 100 строк с input/reference/tags.
- Published DatasetVersion остаётся неизменяемой. Редактирование будет созданием новой версии; hard delete отложен до retention/reference policy, поскольку RunItem ссылается на DatasetItem.
- Проверки: backend 18/18; frontend production build; Playwright E2E 1/1 с JSONL без запятых и просмотром сохранённой версии; временная E2E DB удалена. Сервисы перезапущены, frontend 3000/backend 8010 отвечают.

## Следующий безопасный шаг

Владелец проверяет три сценария в `/datasets`: ручной JSONL, понятную диагностику `test/dataset.jsonl` и просмотр опубликованной версии. После подтверждения: спроектировать явный field mapping/import transformation и workflow «создать новую версию»; отдельно определить archive/delete retention policy. Затем продолжить выделение `/experiments`.

## Dataset browser upload transport fix — 2026-09-17

- По проверке владельца UI file preview отвечал `Field required`, хотя прямой multipart API и schema diagnostics работали.
- Причина: общий Axios instance задавал `Content-Type: application/json` для всех запросов, включая `FormData`; браузер не формировал корректный multipart boundary, поэтому FastAPI не получал поле `file`.
- Глобальный Content-Type удалён. Axios теперь выводит JSON/multipart заголовок из тела конкретного запроса.
- Playwright E2E расширен реальной загрузкой `test/dataset.jsonl`: preview принимает файл, возвращает 0 valid / 3 invalid и показывает строковую причину про отсутствующий `external_id`; затем тот же сценарий проверяет JSONL-text, публикацию и просмотр версии.
- Проверки: frontend production build; полный Playwright E2E 1/1. Решение зафиксировано как D-058.

## Explicit Dataset field mapping — 2026-09-17

- После исходного file preview `/datasets` показывает найденные поля и явную форму сопоставления для text Dataset: source ID → `external_id`, source text → `input.text`, optional source reference → `reference`.
- Для `test/dataset.jsonl` UI предлагает `id`, `transcript`, `reference_summary`, но не применяет их скрыто: пользователь нажимает «Применить сопоставление», после чего выполняется повторный preview.
- Backend preview/commit принимает optional multipart `mapping_json`; integer ID нормализуется в строку, transcript должен быть текстом, reference принимает объект или строку с JSON-объектом. Ошибки transformation возвращаются по строкам.
- Подтверждённый mapping сохраняется в `DatasetVersion.schema_json.import_mapping`; commit отклоняет несовпадающее с уже сохранённым определение.
- Проверки: backend 18/18; frontend production build; Playwright E2E 1/1 загружает реальный `test/dataset.jsonl`, видит 0/3 до mapping и 3/0 после явного применения, затем проверяет обычный publish/run flow.

## Следующий безопасный шаг

Владелец проверяет field mapping в рабочем `/datasets`. После UX-подтверждения реализовать «Создать новую версию» без мутации published DatasetVersion; hard delete остаётся заблокирован до retention/reference policy. Затем продолжить выделение `/experiments`.

## Dataset source-row preview for mapping — 2026-09-17

- Блок field mapping теперь показывает первые 3 успешно разобранные исходные строки файла в таблице по source fields. Пользователь видит не только `id/transcript/reference_summary`, но и реальные значения перед подтверждением.
- Каждое отображаемое значение ограничено 500 символами и помечено как preview; transformation и commit используют полное исходное значение. Preview не сохраняется в БД и не логируется.
- Backend возвращает `source_preview` отдельно от нормализованного canonical `preview`, поэтому повторный preview после mapping продолжает показывать исходные данные.
- Проверки: backend 18/18; frontend production build; Playwright 1/1 подтвердил 3 исходные строки и видимый фрагмент первого транскрипта из `test/dataset.jsonl`.

## Следующий безопасный шаг

Владелец проверяет читаемость таблицы исходных строк и корректность предложенного mapping. После подтверждения — workflow создания новой версии существующего Dataset.

## Noncanonical CSV preview enables mapping — 2026-09-17

- Устранён ранний отказ `CSV requires an external_id column or explicit field mapping`: CSV без `external_id` теперь разбирается как исходная таблица и возвращает source fields, первые строки и построчные canonical validation errors.
- После preview пользователь может сопоставить произвольную ID-колонку с `external_id`, текстовую колонку с `input.text` и optional reference. Commit без успешного mapping по-прежнему отклоняется.
- Канонический CSV с `external_id,input,reference,metadata,tags` продолжает использовать строгий JSON-column parser без изменения контракта.
- Проверки: backend 18/18 включает noncanonical CSV до/после mapping; frontend build; Playwright 1/1 загружает in-memory CSV без `external_id`, видит source sample и затем продолжает полный JSONL/run flow.

## Следующий безопасный шаг

Владелец повторно проверяет свой CSV и явное сопоставление. После подтверждения — workflow создания новой версии существующего Dataset.

## CSV encoding and delimiter detection — 2026-09-18

- Проверен реальный `test/test1.csv`: файл имеет Windows-1251, разделитель `;`, три колонки `id/transcript/reference_summary`; прежний UTF-8-only decoder объясняет ошибку владельца.
- Import decoder теперь поддерживает UTF-8, UTF-8 BOM, UTF-16 с BOM и Windows-1251. CSV delimiter автоматически определяется среди comma, semicolon, tab и pipe; при невозможности определить возвращается явная ошибка вместо молчаливой одной колонки.
- Preview возвращает и UI показывает `source_encoding` и `source_delimiter`. При commit параметры сохраняются в `DatasetVersion.schema_json.import_source` вместе с mapping для воспроизводимости.
- Подсказка file input перечисляет поддерживаемые кодировки/разделители.
- Проверки: backend 18/18 (Windows-1251 + semicolon, UTF-8 + pipe, canonical comma); frontend build; Playwright 1/1 загружает настоящий `test/test1.csv`, видит `windows-1251`, `;`, три строки и русский transcript.

## Следующий безопасный шаг

Владелец повторно проверяет `test/test1.csv` и другие CSV с альтернативными delimiters. После подтверждения — Dataset revision workflow.

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
