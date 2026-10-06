# Провайдеры исходных обзоров — 2026-10-07

Владелец подтвердил: все недостающие из двух обзоров и требований. Добавляются OpenAI, Anthropic/Claude, Groq, Z.ai, GigaChat, Mistral, Hugging Face, NVIDIA, Qwen/DashScope, DeepSeek, Yandex AI Studio и Vercel AI Gateway. Google, OpenRouter и ЦРТ сохраняются. Первый поток — текстовые Dataset/Pipeline, генерация и отдельный Judge; изображение/streaming/tools не объявляются реализованными.

## Решения и UX до реализации

- Единый backend-реестр presets: название, адрес API, имя env-переменной, доступность каталога, подсказки. UI добавляет presets к текущим сервисам, хранит черновик каждого отдельно. Адрес новых сервисов редактируемый HTTPS; у Qwen адрес рабочего пространства/региона задаётся явно. ModelRoute хранит безопасные параметры в capabilities, RunSnapshot фиксирует их; секреты только env: references.
- Совместимый chat wire-format используется только для документированных сервисов с отдельными настройками token field/auth. OpenAI/Groq используют max_completion_tokens; остальные max_tokens. Temperature по умолчанию у новых adapters не отправляется, чтобы не ломать модели с ограничениями sampling. Claude — Messages API с text blocks и stop_reason. Yandex — Chat Completions с Api-Key и folder/project. GigaChat — OAuth Basic authorization key → краткоживущий Bearer (или готовый access token); scope выбирается явно. OAuth входит в общий timeout, токены не сохраняются в БД/ответах.
- TLS не отключается. Для доверенных корневых сертификатов GigaChat используется SSL_CERT_FILE в окружении backend. Redirects не выполняются. Введённый endpoint показывается пользователю: ключ отправляется именно этому адресу.
- Каталоги моделей загружаются по явному действию пользователя; модели можно вводить вручную. Для Z.ai, NVIDIA, Qwen и Yandex в этом инкременте ручной ID вместо неподтверждённого каталога. Никаких выдуманных моделей/квот/обещаний бесплатности. HF/Vercel — шлюзы, фактическое размещение определяется ими; platform fallback не включается.
- При усечении/блокировке/неверном envelope выдаётся диагностическая ошибка; reasoning/tool blocks не выдаются за финальный текст. Все новые адаптеры проверяются mock transport и сквозным generation → Judge. Никаких внешних генераций или поиска ключей для smoke.

## Официальные контракты

- OpenAI: https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create
- Claude: https://platform.claude.com/docs/en/api/messages/create и /en/api/models/list
- Groq: https://console.groq.com/docs/openai и /docs/api-reference
- Z.ai: https://docs.z.ai/api-reference/llm/chat-completion
- GigaChat: https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/gigachat-api и /post-chat
- Mistral: https://docs.mistral.ai/api
- Hugging Face: https://huggingface.co/docs/inference-providers/tasks/chat-completion и /en/hub-api
- NVIDIA: https://docs.api.nvidia.com/nim/reference/llm-apis
- Qwen: https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope
- DeepSeek: https://api-docs.deepseek.com/api/create-chat-completion/ и /api/list-models/
- Yandex: https://aistudio.yandex.ru/ru/docs/ai-studio/operations/generation/completions-structured
- Vercel: https://vercel.com/docs/ai-gateway/sdks-and-apis/openai-chat-completions

Оригинальные обзоры — исторические материалы; модели и тарифы в них не являются актуальным контрактом. Реальная доступность зависит от аккаунта, региона и модели. Пользовательская проверка инкремента 2026-10-02 пока не выполнена и этим шагом не подменяется.

## Как подключить

1. Задайте значение ключа в окружении backend (или пользовательской переменной Windows), вне репозитория. В интерфейсе указывается только имя переменной, без значения.
2. Откройте «Модели», выберите сервис. Проверьте адрес API и имя переменной. Нажмите «Обновить список» либо введите точный ID текстовой chat-модели вручную. Каталог может содержать модели других типов; наличие ID не гарантирует доступ аккаунта.
3. Для GigaChat выберите OAuth и scope своего аккаунта либо готовый access token. OAuth-переменная содержит Basic authorization key без слова Basic; готовый access token истекает и требует обновления. При TLS-ошибке установите доверенную цепочку CA через SSL_CERT_FILE в окружении backend; отключения проверки TLS нет.
4. Для Yandex заполните ID каталога и model URI; короткое имя автоматически дополняется gpt://<folder>/. Для Qwen скопируйте полный compatible-mode/v1 URL своего workspace; регион должен совпадать с ключом.
5. Сохраните подключение. Оно доступно как кандидат эксперимента и как отдельный Judge. Старые запуски продолжают использовать снимок прежних настроек; изменение подключения применяется к новым запускам.

| Сервис | Имя переменной по умолчанию |
| --- | --- |
| OpenAI | OPENAI_API_KEY |
| Claude | ANTHROPIC_API_KEY |
| Groq | GROQ_API_KEY |
| Z.ai | ZAI_API_KEY |
| GigaChat | GIGACHAT_AUTH_KEY |
| Mistral | MISTRAL_API_KEY |
| Hugging Face | HF_TOKEN |
| NVIDIA | NVIDIA_API_KEY |
| Qwen | DASHSCOPE_API_KEY |
| DeepSeek | DEEPSEEK_API_KEY |
| Yandex | YANDEX_API_KEY |
| Vercel | AI_GATEWAY_API_KEY |

GET /api/v1/provider-presets возвращает публичные настройки. ModelRoute.capabilities фиксирует base_url, modalities=[text], sampling_policy=provider_default, а для GigaChat — auth_mode/scope, для Yandex — folder_id. GET /api/v1/provider-models принимает те же настройки и credential_ref. Значения ключей и OAuth-токенов эти endpoints не возвращают.

Ограничения: только текст; без tools/streaming/vision. Reasoning блоки не являются финальным ответом. Модели с нестандартным контрактом или обязательными дополнительными параметрами могут потребовать отдельной настройки адаптера. Платформа не обещает бесплатность, фиксированные тарифы и неизменность серверных alias моделей. Проверка реальных аккаунтов и их лимитов остаётся отдельным шагом.

## Результат проверки

Backend: 48/48. Production build: успешно. Playwright: 15/15. Все 12 адаптеров проверены через mock transport и сквозную генерацию с отдельной оценкой. Реальные API с ключами не вызывались; доступ аккаунтов, квоты и поведение выбранных моделей требуют пользовательской проверки.
