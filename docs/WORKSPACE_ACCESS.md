# Доступ к workspace и Git

## Рабочий apply_patch — 2026-09-18

Прямой запуск установленного codex.exe с --codex-run-as-apply-patch вне sandbox успешно изменяет файлы проекта. Встроенный инструмент всё ещё выдаёт ложную ошибку reparse point. Bat-обёртка повреждает многострочный аргумент; прямой exe принимает его корректно. Патчи следует делить на небольшие части из-за Windows-лимита длины командной строки. Изменение ACL и владельца не требуется.

## Подтверждённое состояние 2026-09-16

- Корень `E:\Projects\llm_test` и его `docs` не являются Windows reparse point: это подтверждено `fsutil reparsepoint query`.
- Владелец дерева — `ZOODERZ\zoode`; интерактивный пользователь разработки — `ZOODERZ\Antony Chub`.
- ACL предоставляет `ZOODERZ\Antony Chub` право `Modify`, поэтому чтение и запись через PowerShell разрешены.
- Git по умолчанию останавливает работу с таким репозиторием сообщением `detected dubious ownership`, поскольку owner не совпадает с текущим пользователем.
- Встроенный `apply_patch` в среде Codex ошибочно возвращает `path contains a reparse point` для обычных файлов этого workspace. Это не признак NTFS reparse point и не устраняется ACL.

## Настроенное исправление

Для текущего пользователя добавлен единственный доверенный путь Git:

```powershell
git config --global --add safe.directory E:/Projects/llm_test
```

После этого `git status` работает. Настройка доверяет только этому локальному пути; не использовать широкое значение `*`.

## Правила дальнейшей работы

1. Не пытаться повторно выполнять рекурсивный `takeown`: у текущего пользователя нет Windows ownership privilege, а ACL уже достаточен для обычной работы.
2. Если требуется реальная смена владельца всего дерева, её выполняет администратор или владелец `ZOODERZ\zoode` как отдельная административная операция.
3. При сбое `apply_patch` с ложным reparse-point использовать ограниченную PowerShell-запись в конкретный файл, явно сохраняя UTF-8 без BOM, затем проверить файл. Не использовать широкие массовые операции записи.
4. Перед диагностикой Git запускать `git status`; если ошибка вернулась, проверить `git config --global --get-all safe.directory` и наличие точного пути.
## Контекст запуска launcher — 2026-09-17

Обычная пользовательская команда остаётся:

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts\run.ps1 -Action Restart
```

Внутри управляемой Codex-сессии не следует создавать ещё один вложенный `powershell.exe`: sandbox может передать ему отличающееся process environment (`PATH` и `Path`) и иной контекст работы с файлами `%LOCALAPPDATA%\LLMTester\runtime`. Для агентской проверки использовать текущую оболочку:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& .\scripts\run.ps1 -Action Restart
```

Launcher нормализует `PATH` только в своём process scope, хранит PID фактических listeners 8010/3000 с start-time tokens, запускает Vite напрямую через Node и создаёт уникальные runtime logs на каждый старт. Два последовательных Restart в текущем контексте прошли; state PID совпали с PID listeners.
