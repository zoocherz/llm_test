# QA baseline: traceability matrix

| Требование | Проверка | Автоматизация | Статус |
| --- | --- | --- | --- |
| Draft Dataset принимает preview без записи | duplicate external_id в preview | API integration | Проверяется |
| Published DatasetVersion неизменяем | commit после publish возвращает 409 | API integration | Проверяется |
| Benchmark не делает fallback | ExecutionPolicy отклоняет fallback_enabled | Unit | Проверяется |
| Judge weights валидируются | сумма weights не равна 1 | Unit | Проверяется |
| Несовместимый route не запускается | image Dataset + text route возвращает 422 | API integration | В работе |
| Ошибка item не останавливает Run | broken item завершает Run как completed_with_errors | Integration | Проверяется |
| RunSnapshot не содержит secret | snapshot API не содержит api_key | API integration | Проверяется |
| Cancel не меняет terminal Run | queued Run переводится в cancelled | API integration | Проверяется |
| UI happy path и legacy regression | Evaluation, Providers, Tasks, Test Runs открываются без failed load | Manual browser check | Ожидает QA-проверку |
| Реальные provider payloads | Google/OpenRouter mock contracts | Contract | Этап 2 |

## QA gate этапа 1

Gate пройден после зелёного offline suite, проверки UI в браузере и устранения P0-дефектов. Проверки с реальными ключами не входят в этот gate.
