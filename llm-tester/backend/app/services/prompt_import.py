import yaml
from yaml.tokens import AliasToken, AnchorToken


class PromptLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValueError('Ключи YAML должны быть строками и не повторяться.')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


PromptLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def import_prompt_yaml(content: bytes) -> dict:
    if len(content) > 256 * 1024:
        raise ValueError('Максимальный размер YAML — 256 KiB.')
    try:
        text = content.decode('utf-8-sig')
        if any(isinstance(token, (AliasToken, AnchorToken)) for token in yaml.scan(text)):
            raise ValueError('Ссылки и якоря YAML не поддерживаются; используйте обычные текстовые поля.')
        value = yaml.load(text, Loader=PromptLoader)
    except UnicodeDecodeError:
        raise ValueError('YAML должен быть в UTF-8.') from None
    except (yaml.YAMLError, RecursionError):
        raise ValueError('Некорректный или неподдерживаемый YAML. Нужен один объект с текстовыми полями.') from None
    if not isinstance(value, dict):
        raise ValueError('Ожидается YAML-объект: name и template либо prompt/instructions.')
    if value.get('template') and any(value.get(k) for k in ('prompt', 'instructions')):
        raise ValueError('Укажите template или prompt/instructions, но не оба варианта одновременно.')
    sections = []
    for key in ('template', 'prompt', 'instructions', 'examples'):
        part = value.get(key)
        if part is not None and not isinstance(part, str):
            raise ValueError(f'Поле {key} должно содержать текст.')
        if part and part.strip():
            sections.append(part)
    if not sections:
        raise ValueError('В файле нет текста template, prompt или instructions.')
    name = value.get('name') or 'Импортированная инструкция'
    if not isinstance(name, str) or len(name) > 200:
        raise ValueError('Название должно быть строкой не длиннее 200 символов.')
    return {'name': name, 'template': '\n\n'.join(sections),
            'ignored_fields': sorted(set(value) - {'name', 'template', 'prompt', 'instructions', 'examples'}),
            'warnings': ['Импортируется текст, не настройки модели, response_schema, tools или уведомлений. Проверьте подстановку данных перед сохранением.']}
