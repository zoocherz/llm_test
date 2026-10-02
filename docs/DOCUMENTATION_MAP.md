# Карта документации

## Старт новой сессии

1. Прочитать корневой AGENTS.md.
2. Прочитать docs/PROJECT_STATE.md.
3. Проверить docs/DECISION_LOG.md и незакрытые P0-решения.
4. Только затем открывать требования, архитектуру или код.

## Документы

| Документ | Назначение |
| --- | --- |
| README.md | Актуальные возможности, локальный запуск, тесты и правила хранения данных в Git |
| docs/CRT_MKO_GUIDE.md | Подключение ЦРТ МКО без ключа, ограничения HTTP и импорт YAML |
| docs/RELIABILITY_UX_2026_09_23.md | Диагностика Google/Judge, отмена, YAML и новые providers |
| docs/UX_WORKSPACE_REVISION.md | Предложение привлечённого UX-дизайнера по компактным рабочим экранам |
| docs/RESULTS_REFINEMENT.md | Новые требования: текстовые эталоны, выборочные повторы, независимые шкалы и история |
| docs/CONFIGURATION_UX.md | Редактирование копий конфигураций, синтаксис промпта, Pipeline и критерии |
| docs/idea.md | Исходная идея владельца |
| docs/PROJECT_DISCOVERY.md | Первичная краткая спецификация |
| docs/PRD.md | Границы MVP и продуктовые сценарии |
| docs/UNIVERSAL_EVALUATION_MODEL.md | Универсальная модель Dataset/Pipeline/Evaluator/Run |
| docs/REQUIREMENTS_DISCOVERY.md | Требования, P0-решения и границы ядра |
| docs/ARCHITECTURE.md | Архитектурные принципы и адаптеры |
| docs/ANALYTICS_AND_DATA_PLAN.md | План discovery и подготовки datasets |
| docs/TEST_STRATEGY.md | Quality requirements и тестовая стратегия |
| docs/DECISION_LOG.md | Журнал принятых решений |
| docs/EVALUATION_NEXT_INCREMENT.md | Ограничения executor и предложение следующего потока: инструкции и оценка сохранённых ответов |
| docs/SEPARATE_EVALUATION_GUIDE.md | Короткая проверка раздельной генерации и оценки |
| docs/PROJECT_STATE.md | Точка продолжения после прерывания |
| docs/WORKSPACE_ACCESS.md | Диагностика ownership/ACL и безопасная настройка Git workspace |
| docs/TEAM.md | При необходимости: расширенный charter команды |

## Документы, которые появятся позже

- DATASET_CONTRACT.md: утверждённые CSV/JSONL schemas и templates.
- PIPELINE_SPEC.md: node types, bindings, graph validation и execution semantics.
- EVALUATOR_SPEC.md: встроенные метрики, Judge config и plugin SDK.
- PROVIDER_CAPABILITIES.md: adapter matrix и contract tests.
- API_SPEC.md: versioned HTTP contracts.
- UX_FLOWS.md: wireframes и пользовательские сценарии.
- ROADMAP.md: releases, milestones, risks и критерии перехода.
- ADR/: отдельные архитектурные решения, если одного журнала недостаточно.

Новые документы добавляются только с понятной ролью; карта обновляется одновременно с ними.

## Спецификации foundation

- docs/DATA_MODEL_SPEC.md — модель данных, версии и RunSnapshot.
- docs/API_SPEC.md — HTTP API v1.
- docs/UX_FLOWS.md — первый UX и wireframe.- docs/FOUNDATION_IMPLEMENTATION_PLAN.md — scope, порядок и readiness первого vertical slice.
## UX и продуктовые сценарии

- `docs/scenarios.md` — рабочий черновик владельца и источник discovery-гипотез; не каноническая спецификация.
- `docs/INFORMATION_ARCHITECTURE.md` — целевые разделы приложения, назначение экранов, судьба legacy-навигации и порядок миграции.
- `docs/UX_FLOWS.md` — конкретные пользовательские потоки и progressive disclosure.

- docs/CRT_PROGRESS_REFINEMENT.md — настраиваемый ЦРТ, live progress и разбор ответов.
