# LLM Tester

Локальная web-платформа для воспроизводимой оценки LLM-конфигураций. Универсальное ядро: Dataset, Pipeline, ModelRoute, Evaluator и RunSnapshot. Генерация ответов и оценка сохранённых ответов запускаются отдельно.

## Текущие возможности

- Версии датасетов, импорт JSON/JSONL/CSV с предварительным просмотром и сопоставлением полей.
- Инструкции с подстановками, импорт YAML и сохранение новых вариантов настроек.
- Текстовые подключения: Google, OpenRouter, ЦРТ МКО, OpenAI, Claude, Groq, Z.ai, GigaChat, Mistral, Hugging Face, NVIDIA, Qwen, DeepSeek, Yandex и Vercel; отдельный LLM-Judge и независимые шкалы критериев. [Настройка новых провайдеров](docs/PROVIDERS_EXPANSION.md).
- История запусков, неизменяемые snapshots, просмотр результатов, экспорт, отмена и выборочный повтор строк с историей попыток.
- Offline fixtures и браузерные тесты без реальных вызовов провайдеров.

Функциональность продолжает развиваться. Поддержка произвольных DAG, восстановление jobs после аварии остаются в плане. Актуальные ограничения и точка продолжения: [PROJECT_STATE](docs/PROJECT_STATE.md).

## Локальный запуск

Нужны Python 3.11, Node.js и npm. Из корня репозитория:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r llm-tester/backend/requirements.txt
npm --prefix llm-tester/frontend ci
$env:LLM_TESTER_PYTHON = (Resolve-Path .\.venv\Scripts\python.exe).Path
powershell.exe -ExecutionPolicy Bypass -File scripts\run.ps1 -Action Start
```

Интерфейс: http://localhost:3000. API: http://localhost:8010/docs. Проверка доступности: http://localhost:8010/health.

Launcher поддерживает `Start`, `Status`, `Restart`, `Stop`. Перед перезапуском завершите активные эксперименты. Рабочая SQLite БД создаётся локально в `llm-tester/backend/llm_tester.db`; она не входит в Git. Для переноса истории нужна отдельная резервная копия БД.

Подключения v1 хранят ссылку `env:VARIABLE_NAME`; значение ключа задаётся в окружении backend перед запуском. Не помещайте ключи в исходники или Git. Пользовательские папки `data/` и `test/`, базы, логи и `.env` исключены из репозитория.

## Проверки

Backend (из `llm-tester/backend`, Python с установленными зависимостями):

```powershell
python -m unittest discover -s tests -v
```

Frontend (из `llm-tester/frontend`):

```powershell
$env:GOMAXPROCS = '2'
npm.cmd run build
npm.cmd run test:e2e
```

Текущая конфигурация Playwright рассчитана на исходную Windows-машину: в `playwright.config.js` заданы абсолютные пути к Python и Chrome. Для другой машины их нужно настроить. E2E использует отдельную БД `e2e_test.db` и порты 8020/3010; рабочую БД не подменяет.

## Документация

- [Карта документации](docs/DOCUMENTATION_MAP.md)
- [Текущее состояние](docs/PROJECT_STATE.md) и [журнал решений](docs/DECISION_LOG.md)
- [Раздельная генерация и оценка](docs/SEPARATE_EVALUATION_GUIDE.md)
- [ЦРТ МКО и импорт YAML](docs/CRT_MKO_GUIDE.md)
- [Правила работы](AGENTS.md)

Изменения фиксируются коммитами после проверки. Публикация в GitHub сохраняет историю, без принудительного перезаписывания веток.
