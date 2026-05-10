---
name: MCUB-debugger-fixer
description: Run, interpret, and fix MCUB debugger warnings and errors while preserving module behavior and build history.
keywords:
  - debugger
  - debug
  - дебаггер
  - варн
  - warning
  - warnings
  - error
  - errors
  - MCUB0
  - pytest
---

# MCUB Debugger Fixer

Use this skill when the user asks to run, read, explain, or fix output from the MCUB debugger, especially:

- `python -m debugger.cli <module.py>`
- `mcub-debugger <module.py>`
- debugger warnings like `MCUB001`, `MCUB027`, etc.
- requests like “почини варны”, “debugger ругается”, “исправь модуль по дебаггеру”.

## Main goal

Turn debugger output into safe MCUB-compatible fixes without breaking module behavior. Treat debugger **errors** as blockers. Treat warnings as signals: fix real runtime/safety issues, but do not blindly rewrite valid MCUB patterns.

## Standard workflow

1. Identify the target file.
2. If the target is an `app-debug` module, preserve build history:
   - do not overwrite old `modules-debug-v*.py` builds;
   - create the next patch version when editing the module.
3. Run syntax check first when useful:

   ```bash
   python -m py_compile path/to/module.py
   ```

4. Run the debugger:

   ```bash
   python -m debugger.cli path/to/module.py
   ```

5. Group findings by severity:
   - errors/blockers;
   - real runtime warnings;
   - noisy/acceptable warnings.
6. Fix the smallest necessary code area.
7. Re-run `py_compile` and debugger.
8. Report exactly what was fixed and what remains intentionally unchanged.

## Common fixes

### Async command/callback handlers

MCUB userbot handlers should usually be async:

```python
@loader.command("name")
async def cmd_name(self, event):
    await self.edit(event, "ok")
```

If debugger says an async function has no await, do not add fake sleeps. Prefer making real awaited calls or converting only truly synchronous helpers to `def` when they are not handlers.

### Async without await

Valid async bodies may contain:

- `await ...`
- `async for ...`
- `async with ...`

Do not add useless `await asyncio.sleep(0)` unless there is no better fix and the function must remain async because MCUB expects it.

### Broad or silent except

For broad exceptions (`except Exception`, bare `except`):

```python
except Exception as e:
    await self.kernel.handle_error(e, source="ModuleName", event=event)
```

or:

```python
except Exception:
    self.log.exception("Failed to do ...")
    raise
```

For expected user input errors (`ValueError`, validation failures), replying to the user is acceptable:

```python
except ValueError:
    await self.edit(event, "Некорректный аргумент")
```

Never leave empty handlers, `pass`, or silent `return` for broad exceptions.

### Class-style MCUB modules

Correct style:

```python
import core.lib.loader.module_base as loader


class MyModule(loader.ModuleBase):
    name = "MyModule"
```

Do not convert to Hikka style:

```python
from .. import loader
class MyModule(loader.Module): ...
```

### Decorators

Class-style modules can use more than just `@command`:

- `@loader.command`
- `@loader.bot_command`
- `@loader.callback`
- `@loader.event`
- `@loader.watcher`
- `@loader.loop`

Do not force every handler to be named `cmd_*` if routing is already declared by decorators.

### Metadata warnings

Prefer fixing missing or incomplete metadata:

```python
name = "ModuleName"
version = "1.0.0"
author = "@username"
description = {"ru": "...", "en": "..."}
```

If publishing to repo, also preserve repo/meta headers when present.

## When a warning may be acceptable

Mention it clearly instead of hiding it if:

- debugger rule is too strict for a valid MCUB class-style pattern;
- a helper intentionally has a generic name and is not a command;
- a specific exception is handled by replying to the user;
- the warning is about style only and the user asked for minimal functional fix.

## Safety rules

- Do not edit unrelated files while fixing debugger output.
- Do not delete old `app-debug` builds.
- Do not hardcode secrets, tokens, phone numbers, or session strings.
- Do not silence warnings with `# noqa` unless the warning is truly false-positive and explain why.
- Do not replace MCUB APIs with Hikka/Heroku APIs.
- Do not change module behavior beyond what is needed to fix the debugger issue.

## Final response format

Keep the report short:

```text
Готово.
- Файл: ...
- Исправлено: ...
- Проверка: py_compile OK, debugger OK
- Осталось: ... / ничего
```
