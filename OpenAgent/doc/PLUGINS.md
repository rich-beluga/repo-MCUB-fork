# OpenAgent Plugins

## Overview

OpenAgent uses a **dynamic plugin system** similar to how MCUB loads modules:
the agent does **not** know in advance which plugins are installed.
Plugins are auto-discovered from two directories, loaded at runtime,
and register their tools into the shared registry.

Plugins replace the old hardcoded tool map.
This makes the tool set extensible without modifying the module itself.

---

## Architecture

```
OpenAgent-MCUB-repo.py          # module (loader, core tools, dispatch)
OpenAgent/
├── doc/                         # this documentation
└── plugins/                     # bundled plugins (shipped with repo)
    ├── terminal.py
    ├── web.py
    ├── mcub.py
    ├── message.py
    ├── dialog.py
    ├── chat.py
    ├── moderation.py
    ├── profile.py
    ├── file.py
    ├── contacts.py
    └── creation.py
```

**Scan order** (at startup):

1. `OpenAgent/plugins/` — bundled plugins (repo/main branch)
2. `openagent_plugins/` — external installed plugins (user's workspace)

External plugins override bundled ones with the same name without warning.

---

## Plugin Lifecycle

1. **Discovery** — `_load_installed_plugins()` scans both directories.
2. **Import** — `_register_plugin_from_file()` imports the `.py` file dynamically.
3. **Registration** — `_register_plugin()` stores the plugin and its config defaults.
4. **Tool map merge** — `_get_tool_map()` merges core entries with each plugin's `tool_map`.
5. **Dispatch** — `_dispatch_tool()` looks up the handler either from the plugin or from the module itself.

---

## Plugin API

### Base class (`OpenAgentPlugin`)

```python
class OpenAgentPlugin:
    name: str = ""                    # unique plugin identifier
    version: str = "0.1.0"
    tool_registry: tuple[str, ...] = ()    # advertised tool names
    tool_map: dict[str, str] = {}          # tool name → handler method
    config_defaults: dict[str, object] = {}  # optional config keys

    def __init__(self, agent):
        self._agent = agent

    @property
    def agent(self):
        return self._agent

    async def on_load(self):
        """Called after registration (optional)."""
```

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique plugin name. Used as tool group prefix. |
| `tool_registry` | `tuple[str]` | Tool names advertised to the model. |
| `tool_map` | `dict[str, str]` | Maps each tool name → a handler method name (string). |

### Handler methods

Each handler is an `async` method on the plugin class.
The dispatch system inspects the method signature and passes arguments by name.

**Supported parameter names (any subset, order irrelevant):**

| Parameter | Value |
|-----------|-------|
| `tool_name` | The matched tool name (e.g. `"message.send"`) |
| `attrs_raw` | Raw XML attributes string from the tool call |
| `body` | The body text (after attributes) |
| `source_event` | The Telegram `NewMessage.Event` that triggered the conversation |
| `command` | Same as `body` (for terminal-like tools) |
| `query` | Same as `body` (for search-like tools) |
| `mode` | One of `private`/`groups`/`all` (for dialog listing) |
| `target` | Target user/chat name |
| `kind` | `"group"` or `"channel"` (for creation tools) |

**Example:**

```python
class MyPlugin:
    name = "myplugin"
    tool_map = {
        "myplugin.hello": "cmd_hello",
    }

    async def cmd_hello(self, body: str) -> str:
        return f"Hello, {body or 'world'}!"
```

### Config defaults

If your plugin needs runtime configuration:

```python
class TerminalPlugin:
    name = "terminal"
    config_defaults = {
        "terminal_timeout": 30,       # int
        "terminal_enabled": True,     # bool
        "terminal_steps": 3,          # int
    }
```

The loader creates proper `ConfigValue` entries with automatic type detection
(`Boolean` for `bool`, `Integer` for `int`, `Float` for `float`,
`List` for `list`, `String` for everything else).

---

## Installing plugins

### From reply (`.oaplugin` on a `.py` file)

1. Send or forward a `.py` plugin file to the chat.
2. Reply to it with `.oaplugin`.
3. The plugin is validated (compiled), saved to `openagent_plugins/`, and registered.

```text
You:  .oaplugin
      ↑ reply to file.py
Bot:  Plugin installed: myplugin
```

### From catalog (`📦 Каталог`)

1. Run `.oaplugin` → tap `📦 Каталог`.
2. Browse plugins from the repository.
3. Tap `📥 Установить`.

Installed plugins appear in `⚙️ Менеджер` where you can also delete them.

---

## Creating a plugin

Simplest plugin skeleton:

```python
# scop: inline
# SPDX-License-Identifier: MIT

from typing import Any


class PingPlugin:
    name = "ping"
    version = "0.1.0"
    description = "Simple ping tool"

    tool_registry = ("ping.check",)
    tool_map = {
        "ping": "cmd_ping",
        "ping.check": "cmd_ping",
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def cmd_ping(self, body: str) -> str:
        return "pong"
```

Save it, reply with `.oaplugin`, done.

### Calling module internals

Plugins can access the agent's methods through `self.agent`:

```python
await self.agent._web_search(query)          # web search
await self.agent._run_mcub_command(cmd, ev)  # MCUB command
await self.agent._send_userbot_message(msg, ev, chat=...)  # send message
await self.agent._misc_tool(name, attrs, body, ev)         # misc Telegram ops
data = self.agent._parse_xml_attrs(attrs_raw)              # parse XML attributes
```

> ⚠️ Methods starting with `_` are not public API — they may change between versions.

---

## Bundled plugins

| File | Name | Tools | Description |
|------|------|-------|-------------|
| `terminal.py` | `terminal` | `terminal.run`, `.inspect`, `.list_files`, `.read_file`, `.git_status` | Shell commands |
| `web.py` | `web` | `web.search`, `.fetch_url`, `.read_html`, `.extract_links`, `.summarize_page` | Web search/fetch |
| `mcub.py` | `mcub` | `mcub.command`, `.config`, `.modules`, `.install`, `.reload` | MCUB kernel commands |
| `message.py` | `message` | `message.send*`, `.reply`, `.edit`, `.forward`, `.delete`, `.pin`, `.react`, `.get`, `.search`, `.history`, `.mark_read`, `.typing`, `.schedule`, `.draft` | Telegram messaging |
| `dialog.py` | `dialog` | `dialog.list_*`, `.search`, `.archive`, `.unarchive`, `.leave`, `.export_invite`, `.get_photo`, `.set_photo` | Dialog management |
| `chat.py` | `chat` | `chat.info`, `.participants`, `.admins`, `.permissions`, `.common_with_user`, `.set_*`, `.slowmode`, `.invite_link` | Chat settings |
| `moderation.py` | `moderation` | `moderation.mute`, `.unmute`, `.ban`, `.unban`, `.kick`, `.promote`, `.demote`, `.pin`, `.delete_messages`, `.get_admins` | Moderation |
| `profile.py` | `profile` | `profile.get*`, `.update_*`, `.set_photo`, `.download_photo`, `.common_chats` | User profile |
| `file.py` | `file` | `file.send`, `.download_media`, `.read_text` | File operations |
| `contacts.py` | `contacts` | `contacts.add`, `.delete`, `.block`, `.unblock`, `.entity` | Contact management |
| `creation.py` | `creation` | `creation.channel`, `.group`, `.bot`, `.private_invite` | Channel/group/bot creation |

---

## Tool dispatch rules

When the model calls a tool:

1. **Plugin `tool_map` is checked first** — exact match by tool name.
2. **Core map is checked** — module-tied tools (skills, code, context, todo, utility, thinking).
3. **Misc aliases** — legacy shortcuts like `get_admins`, `edit_message`, `block_user` are routed to `_misc_tool`.
4. If nothing matches, the closest tool names are suggested.

The tool group (first segment before `.`) is used to find the owning plugin,
but the tool map lookup can match any key regardless of group.
