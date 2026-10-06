"""Documented text-provider profiles. No secret values leave request headers."""
import re
from urllib.parse import urlsplit
from uuid import uuid4
import httpx
from app.services.v1_providers import ProviderExecutionError


def profile(label, base_url, secret_name, *, catalog=True, token_field='max_tokens', help=''):
    return dict(label=label, base_url=base_url, secret_name=secret_name, catalog=catalog, token_field=token_field, help=help)


PRESETS = {
    'openai': profile('OpenAI', 'https://api.openai.com/v1', 'OPENAI_API_KEY', token_field='max_completion_tokens'),
    'anthropic': profile('Claude / Anthropic', 'https://api.anthropic.com/v1', 'ANTHROPIC_API_KEY', help='Messages API; выбирайте модель Claude из каталога.'),
    'groq': profile('Groq', 'https://api.groq.com/openai/v1', 'GROQ_API_KEY', token_field='max_completion_tokens'),
    'zai': profile('Z.ai / Zhipu', 'https://api.z.ai/api/paas/v4', 'ZAI_API_KEY', catalog=False, help='Обычный API, не Coding Plan. Для китайской платформы укажите её адрес и ключ.'),
    'gigachat': profile('GigaChat', 'https://api.giga.chat/v1', 'GIGACHAT_AUTH_KEY', help='OAuth: переменная содержит ключ авторизации Basic без префикса. При ошибке TLS настройте доверенный CA через SSL_CERT_FILE; проверка сертификатов включена.'),
    'mistral': profile('Mistral AI', 'https://api.mistral.ai/v1', 'MISTRAL_API_KEY'),
    'huggingface': profile('Hugging Face', 'https://router.huggingface.co/v1', 'HF_TOKEN', help='Токен с правом Inference Providers. Размещение и маршрутизацию определяет HF; для фиксации поставщика используйте model:provider.'),
    'nvidia': profile('NVIDIA Build / NIM', 'https://integrate.api.nvidia.com/v1', 'NVIDIA_API_KEY', catalog=False),
    'qwen': profile('Qwen / DashScope', '', 'DASHSCOPE_API_KEY', catalog=False, help='Введите HTTPS адрес compatible-mode/v1 из вашего Model Studio workspace. Регион адреса должен соответствовать ключу.'),
    'deepseek': profile('DeepSeek', 'https://api.deepseek.com/v1', 'DEEPSEEK_API_KEY'),
    'yandex': profile('Yandex AI Studio', 'https://ai.api.cloud.yandex.net/v1', 'YANDEX_API_KEY', catalog=False, help='API-ключ сервисного аккаунта, ID каталога и полный model URI gpt://folder/model/version.'),
    'vercel': profile('Vercel AI Gateway', 'https://ai-gateway.vercel.sh/v1', 'AI_GATEWAY_API_KEY', help='Шлюз: модель в формате provider/model. Внутреннюю маршрутизацию определяет Vercel.'),
}
SCOPES = {'GIGACHAT_API_PERS', 'GIGACHAT_API_B2B', 'GIGACHAT_API_CORP'}
OAUTH_URL = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'


def public_presets():
    return [{'id': name, **value} for name, value in PRESETS.items()]


def normalize_capabilities(provider, caps):
    result = dict(caps)
    value = result.get('base_url', PRESETS[provider]['base_url'])
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Укажите полный HTTPS адрес API выбранного сервиса.')
    value = value.strip().rstrip('/')
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.query or parsed.fragment
                or any(c.isspace() or ord(c) < 32 for c in value) or '\\' in value
                or '{' in value or '}' in value or parsed.port == 0):
            raise ValueError()
        httpx.URL(value)
    except (ValueError, httpx.InvalidURL):
        raise ValueError('Адрес должен быть HTTPS URL без логина, пароля, query, fragment и незаполненных шаблонов.') from None
    result['base_url'] = value
    if result.get('modalities', ['text']) != ['text']:
        raise ValueError('Новые адаптеры поддерживают только текст в текущем потоке.')
    result['modalities'] = ['text']
    result['sampling_policy'] = 'provider_default'
    if provider == 'gigachat':
        result.setdefault('auth_mode', 'oauth')
        result.setdefault('scope', 'GIGACHAT_API_PERS')
        if result['auth_mode'] not in {'oauth', 'access_token'} or result['scope'] not in SCOPES:
            raise ValueError('Проверьте тип ключа и scope GigaChat.')
    if provider == 'yandex':
        if not isinstance(result.get('folder_id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', result['folder_id']):
            raise ValueError('Укажите ID каталога Yandex Cloud.')
    return result


def checked_caps(provider, caps):
    try:
        return normalize_capabilities(provider, caps)
    except (ValueError, TypeError) as exc:
        raise ProviderExecutionError('invalid_provider_config', str(exc)) from None


def json_response(response):
    if response.status_code >= 300:
        raise ProviderExecutionError(f'http_{response.status_code}', 'Сервис отклонил запрос. Проверьте ключ, доступ к модели и лимиты.', response.status_code in {408, 429} or response.status_code >= 500)
    try:
        data = response.json()
    except ValueError:
        raise ProviderExecutionError('invalid_json', 'Сервис вернул не JSON; тело ответа не сохраняется.') from None
    if not isinstance(data, dict) or data.get('error'):
        raise ProviderExecutionError('invalid_response', 'Сервис вернул ошибку или неверную структуру ответа.')
    return data


async def headers_for(client, provider, key, caps):
    if provider == 'anthropic':
        return {'x-api-key': key, 'anthropic-version': '2023-06-01'}
    if provider == 'gigachat' and caps['auth_mode'] == 'oauth':
        # One token exchange per operation, bounded by the operation's total deadline.
        response = await client.post(OAUTH_URL, headers={'Authorization': 'Basic ' + key, 'RqUID': str(uuid4()), 'Accept': 'application/json'}, data={'scope': caps['scope']})
        data = json_response(response)
        key = data.get('access_token')
        if not isinstance(key, str) or not key.strip():
            raise ProviderExecutionError('invalid_response', 'GigaChat не вернул access token.')
    if provider == 'yandex':
        return {'Authorization': 'Api-Key ' + key, 'OpenAI-Project': caps['folder_id']}
    return {'Authorization': 'Bearer ' + key}


def build_request(provider, caps, request):
    if request.images:
        raise ProviderExecutionError('unsupported_modality', 'В этом адаптере пока поддержан только текст.')
    body = {'model': request.model, 'messages': [{'role': 'user', 'content': request.prompt}], PRESETS[provider]['token_field']: request.max_output_tokens, 'stream': False}
    if provider == 'yandex' and not request.model.startswith('gpt://'):
        body['model'] = 'gpt://' + caps['folder_id'] + '/' + request.model
    return caps['base_url'] + ('/messages' if provider == 'anthropic' else '/chat/completions'), body


def parse_response(provider, data):
    try:
        if provider == 'anthropic':
            blocks = data['content']
            if not isinstance(blocks, list): raise ValueError()
            text = ''.join(b['text'] for b in blocks if isinstance(b, dict) and b.get('type') == 'text' and isinstance(b.get('text'), str))
            reason = data.get('stop_reason')
            usage = data.get('usage') or {}
            prompt, completion = usage.get('input_tokens', 0), usage.get('output_tokens', 0)
            total = prompt + completion
            reason = {'max_tokens': 'length', 'refusal': 'content_filter'}.get(reason, reason)
        else:
            choice = data['choices'][0]
            text = choice['message'].get('content')
            if isinstance(text, list):
                text = ''.join(b['text'] for b in text if isinstance(b, dict) and b.get('type') == 'text' and isinstance(b.get('text'), str))
            if text is None: text = ''
            if not isinstance(text, str): raise ValueError()
            reason = choice.get('finish_reason')
            reason = {'blacklist': 'content_filter', 'model_length': 'length'}.get(reason, reason)
            usage = data.get('usage') or {}
            prompt, completion = usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0)
            total = usage.get('total_tokens', prompt + completion)
        if any(type(n) is not int or n < 0 for n in (prompt, completion, total)): raise ValueError()
        if reason in {'tool_calls', 'function_call', 'tool_use', 'pause_turn'}:
            raise ProviderExecutionError('unsupported_response', 'Модель запросила инструмент или продолжение; финальный ответ не получен.')
        return {'text': text, 'finish_reason': reason, 'usage': {'prompt': prompt, 'completion': completion, 'total': total}}
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        raise ProviderExecutionError('invalid_response', 'Не удалось разобрать текстовый ответ сервиса.') from None


async def list_models(provider, key, caps, transport=None):
    import asyncio
    if not PRESETS[provider]['catalog']:
        raise ProviderExecutionError('catalog_unavailable', 'У этого подключения модель вводится вручную по ID из кабинета сервиса.')
    rows, seen, cursor = [], set(), None
    try:
        async with asyncio.timeout(20):
            async with httpx.AsyncClient(timeout=20, transport=transport, follow_redirects=False) as client:
                headers = await headers_for(client, provider, key, caps)
                for _ in range(20):
                    params = {'limit': 1000, **({'after_id': cursor} if cursor else {})} if provider == 'anthropic' else None
                    payload = json_response(await client.get(caps['base_url'] + '/models', headers=headers, params=params))
                    raw_rows = payload.get('data')
                    if not isinstance(raw_rows, list):
                        raise ProviderExecutionError('invalid_response', 'Каталог моделей имеет неверную структуру.')
                    for raw in raw_rows:
                        if not isinstance(raw, dict) or not isinstance(raw.get('id'), str): continue
                        if raw['id'] in seen or raw.get('active') is False: continue
                        capabilities = raw.get('capabilities') or {}
                        if isinstance(capabilities, dict) and capabilities.get('completion_chat') is False: continue
                        seen.add(raw['id'])
                        rows.append({'id': raw['id'], 'display_name': raw.get('display_name') or raw.get('name') or raw['id'], 'provider_name': provider, 'is_free': None, 'input_modalities': ['text'], 'output_modalities': ['text']})
                    if provider != 'anthropic' or not payload.get('has_more'): break
                    next_cursor = payload.get('last_id')
                    if not next_cursor or next_cursor == cursor:
                        raise ProviderExecutionError('invalid_response', 'Каталог не вернул курсор следующей страницы.')
                    cursor = next_cursor
                else:
                    raise ProviderExecutionError('catalog_too_large', 'Каталог слишком велик; введите ID модели вручную.')
    except (httpx.TimeoutException, TimeoutError):
        raise ProviderExecutionError('timeout', 'Истекло время загрузки каталога.', True) from None
    except httpx.TransportError:
        raise ProviderExecutionError('network_error', 'Не удалось подключиться к сервису. Проверьте сеть и доверенные TLS сертификаты.', True) from None
    return sorted(rows, key=lambda row: row['display_name'].lower())
