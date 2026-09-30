import json
import re

TOKEN = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*}}")


def validate_prompt(template: str) -> None:
    if not template.strip():
        raise ValueError('Введите текст инструкции модели.')
    # Preserve offsets/newlines for actionable diagnostics without echoing user data.
    remainder = list(template)
    for match in TOKEN.finditer(template):
        for index in range(match.start(), match.end()):
            if remainder[index] != '\n':
                remainder[index] = ' '
    invalid = ''.join(remainder).find('{{')
    if invalid >= 0:
        line = template.count('\n', 0, invalid) + 1
        column = invalid - template.rfind('\n', 0, invalid)
        raise ValueError(
            f'Некорректная переменная в промпте: строка {line}, столбец {column}. '
            'Используйте {{text}} или {{input.text}} — имя поля в двойных фигурных скобках. '
            'Выражения и вызовы функций не поддерживаются. Пример JSON-ответа пишите с обычными скобками: {"answer": "..."}.'
        )


def render_prompt(template: str, values: dict) -> str:
    validate_prompt(template)

    def replace(match):
        key = match.group(1)
        parts = key.split('.')
        if parts[0] == 'input' and 'input' not in values and len(parts) > 1:
            parts = parts[1:]
        value = values
        for part in parts:
            if not isinstance(value, dict) or part not in value:
                available = ', '.join(list(values)[:10]) or '(нет полей)'
                raise ValueError(
                    f'В данных нет поля «{key}», указанного в промпте. '
                    f'Доступные поля input: {available}. Исправьте переменную или выберите другой датасет.'
                )
            value = value[part]
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)

    return TOKEN.sub(replace, template)
