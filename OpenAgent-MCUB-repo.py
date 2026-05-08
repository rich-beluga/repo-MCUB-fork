# -- repo data --
# scop: kernel min v1.3.0
# repo: https://github.com/hairpin01/repo-MCUB-fork/
# -- end --
# SPDX-License-Identifier: MIT
# requires: aiohttp
# scop: inline

from __future__ import annotations

import asyncio
import base64
import contextlib
import html
import io
import mimetypes
import random
import re
import tempfile
import time
import uuid
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import aiohttp
from telethon import Button, events
from telethon.tl.functions.account import (
    UpdateProfileRequest,
    UpdateUsernameRequest as UpdateAccountUsernameRequest,
)
from telethon.tl.functions.channels import (
    CreateChannelRequest,
    EditAdminRequest,
    EditPhotoRequest,
    EditTitleRequest,
    JoinChannelRequest,
    ToggleSlowModeRequest,
    UpdateUsernameRequest,
)
from telethon.tl.functions.contacts import (
    AddContactRequest,
    BlockRequest,
    DeleteContactsRequest,
    UnblockRequest,
)
from telethon.tl.functions.messages import (
    EditChatAboutRequest,
    ExportChatInviteRequest,
    ImportChatInviteRequest,
    SaveDraftRequest,
)
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import ChannelParticipantsAdmins, ChatAdminRights

from core.lib.loader.module_base import ModuleBase, command
from core.lib.loader.module_config import (
    Boolean,
    Choice,
    ConfigValue,
    Float,
    Integer,
    List,
    ModuleConfig,
    Secret,
    String,
)


class OpenAgent(ModuleBase):
    name = "OpenAgent"
    version = "0.5.1"
    author = "@dev_dolbaeb"
    description = {
        "ru": "ИИ агент в юзерботе с новой архитектурой инструментов",
        "en": "AI agent in userbot with refreshed tool architecture",
    }

    strings = {
        "ru": {
            "need_text": "Usage: .oa <request>",
            "thinking": "Thinking...",
            "running_terminal": "Running terminal command...",
            "running_search": "Searching the web...",
            "no_key": "API key is not configured. Use .cfg OpenAgent api_key",
            "bad_provider": "Unknown provider. Available: {providers}",
            "provider_saved": "Provider saved: {provider}",
            "key_saved": "Provider and API key saved: {provider}",
            "disabled": "Provider {provider} is not available yet",
            "error": "OpenAgent error: {error}",
        },
        "en": {
            "need_text": "Usage: .oa <request>",
            "thinking": "Thinking...",
            "running_terminal": "Running terminal command...",
            "running_search": "Searching the web...",
            "no_key": "API key is not configured. Use .cfg OpenAgent api_key",
            "bad_provider": "Unknown provider. Available: {providers}",
            "provider_saved": "Provider saved: {provider}",
            "key_saved": "Provider and API key saved: {provider}",
            "disabled": "Provider {provider} is not available yet",
            "error": "OpenAgent error: {error}",
        },
    }

    PROVIDERS = ("openai", "google", "ollama.cloud", "other")
    PROVIDER_LABELS = {
        "openai": "OpenAI",
        "google": "Google",
        "ollama.cloud": "Ollama Cloud",
        "other": "Other",
    }
    DEFAULT_MODELS = {
        "openai": "gpt-5.5",
        "google": "gemini-1.5-flash",
        "ollama.cloud": "llama3.1",
        "other": "gpt-4o-mini",
    }
    BASE_URLS = {
        "openai": "https://api.openai.com/v1",
        "google": "https://generativelanguage.googleapis.com/v1beta",
    }
    WEB_SEARCH_RE = re.compile(
        r"<web_search>\s*(.*?)\s*</web_search>", re.DOTALL | re.I
    )
    SEND_RE = re.compile(
        r'<send_message(?:\s+chat=["\']([^"\']+)["\'])?\s*>(.*?)</send_message>',
        re.DOTALL | re.I,
    )
    SKILL_RE = re.compile(
        r'<skill\s+name=["\']([^"\']+)["\']\s*>(.*?)</skill>', re.DOTALL | re.I
    )
    CREATE_CHANNEL_RE = re.compile(
        r"<create_channel([^>]*)>(.*?)</create_channel>", re.DOTALL | re.I
    )
    CREATE_GROUP_RE = re.compile(
        r"<create_group([^>]*)>(.*?)</create_group>", re.DOTALL | re.I
    )
    CREATE_BOT_RE = re.compile(
        r"<create_bot([^>]*)>(.*?)</create_bot>", re.DOTALL | re.I
    )
    SEARCH_MESSAGES_RE = re.compile(
        r"<search_messages([^>]*)>(.*?)</search_messages>", re.DOTALL | re.I
    )
    UPDATE_PROFILE_RE = re.compile(
        r"<update_profile([^>]*)>(.*?)</update_profile>", re.DOTALL | re.I
    )
    SET_PROFILE_PHOTO_RE = re.compile(
        r"<set_profile_photo([^>]*)>(.*?)</set_profile_photo>", re.DOTALL | re.I
    )
    DELETE_MESSAGES_RE = re.compile(
        r"<delete_messages([^>]*)>(.*?)</delete_messages>", re.DOTALL | re.I
    )
    FORWARD_MESSAGE_RE = re.compile(
        r"<forward_message([^>]*)>(.*?)</forward_message>", re.DOTALL | re.I
    )
    DOWNLOAD_MEDIA_RE = re.compile(
        r"<download_media([^>]*)>(.*?)</download_media>", re.DOTALL | re.I
    )
    GENERATED_FILE_RE = re.compile(
        r'<file\s+name=["\']([^"\']+)["\']\s*>(.*?)</file>',
        re.DOTALL | re.I,
    )
    MCUB_DOCS_URL = "https://x0.at/y2rb.md"
    TOOL_CALL_RE = re.compile(r"<([a-z0-9._]+)([^>]*)>(.*?)</\1>|<([a-z0-9._]+)([^>]*)/?>", re.DOTALL | re.I)
    TOOL_REGISTRY = (
        "terminal.run", "terminal.inspect", "terminal.list_files", "terminal.read_file", "terminal.git_status",
        "web.search", "web.fetch_url", "web.read_html", "web.extract_links", "web.summarize_page",
        "mcub.command", "mcub.config", "mcub.modules", "mcub.install", "mcub.reload",
        "message.send_current", "message.send_target", "message.reply", "message.edit", "message.forward",
        "message.delete", "message.pin", "message.react", "message.get", "message.search",
        "message.history", "message.mark_read", "message.typing", "message.schedule", "message.draft",
        "file.send", "file.download_media", "file.read_text", "file.attach_image", "file.attach_video",
        "dialog.list_private", "dialog.list_groups", "dialog.list_all", "dialog.search", "dialog.archive",
        "dialog.unarchive", "dialog.leave", "dialog.export_invite", "dialog.get_photo", "dialog.set_photo",
        "chat.info", "chat.participants", "chat.admins", "chat.permissions", "chat.common_with_user",
        "chat.set_title", "chat.set_about", "chat.set_username", "chat.slowmode", "chat.invite_link",
        "moderation.mute", "moderation.unmute", "moderation.ban", "moderation.unban", "moderation.kick",
        "moderation.promote", "moderation.demote", "moderation.pin", "moderation.delete_messages", "moderation.get_admins",
        "profile.get", "profile.get_full", "profile.get_me", "profile.update_name", "profile.update_bio",
        "profile.update_username", "profile.set_photo", "profile.download_photo", "profile.get_photos", "profile.common_chats",
        "contacts.add", "contacts.delete", "contacts.block", "contacts.unblock", "contacts.entity",
        "creation.channel", "creation.group", "creation.bot", "creation.channel_avatar", "creation.private_invite",
        "skills.list", "skills.read", "skills.import_md", "skills.export_md", "skills.save_from_ai",
        "code.generate_file", "code.generate_mcub_module", "code.choose_filename", "code.attach_result", "code.read_docs",
        "context.remember", "context.clear", "context.regenerate", "context.reply_context", "context.media_context",
        "account.blacklist", "account.saved_messages", "account.effects", "account.reactions", "account.available_reactions",
        "utility.token_usage", "utility.placeholders", "utility.random_template", "utility.agent_log", "utility.error_file",
    )

    config = ModuleConfig(
        ConfigValue(
            "provider",
            "openai",
            description="Provider: openai, google, ollama.cloud, other",
            validator=Choice(choices=list(PROVIDERS), default="openai"),
        ),
        ConfigValue(
            "api_key",
            "",
            description="API key for the selected provider",
            validator=Secret(default=""),
        ),
        ConfigValue(
            "model",
            "",
            description="Model name. Empty means provider default",
            validator=String(default=""),
        ),
        ConfigValue(
            "custom_base_url",
            "",
            description="Endpoint for provider=other, e.g. https://api.deepseek.com/v1",
            validator=String(default=""),
        ),
        ConfigValue(
            "system_prompt",
            "You are OpenAgent inside a Telegram userbot. Help the user directly. You may inspect the local workspace through terminal commands when needed.",
            description="System prompt for the agent",
            validator=String(
                default="You are OpenAgent inside a Telegram userbot. Help the user directly. You may inspect the local workspace through terminal commands when needed."
            ),
        ),
        ConfigValue(
            "temperature",
            0.7,
            description="Sampling temperature",
            validator=Float(default=0.7, min=0.0, max=2.0),
        ),
        ConfigValue(
            "max_tokens",
            1200,
            description="Maximum response tokens",
            validator=Integer(default=1200, min=64, max=32768),
        ),
        ConfigValue(
            "timeout",
            90,
            description="HTTP timeout seconds",
            validator=Integer(default=90, min=10, max=300),
        ),
        ConfigValue(
            "terminal_enabled",
            True,
            description="Allow the agent to execute terminal commands",
            validator=Boolean(default=True),
        ),
        ConfigValue(
            "terminal_steps",
            3,
            description="Maximum terminal commands per request",
            validator=Integer(default=3, min=0, max=10),
        ),
        ConfigValue(
            "terminal_timeout",
            30,
            description="Terminal command timeout seconds",
            validator=Integer(default=30, min=3, max=120),
        ),
        ConfigValue(
            "web_search_enabled",
            True,
            description="Allow the agent to search the web",
            validator=Boolean(default=True),
        ),
        ConfigValue(
            "web_search_steps",
            3,
            description="Maximum web searches per request",
            validator=Integer(default=3, min=0, max=10),
        ),
        ConfigValue(
            "mcub_use",
            False,
            description="Allow the agent to execute MCUB userbot commands",
            validator=Boolean(default=False),
        ),
        ConfigValue(
            "mcub_steps",
            3,
            description="Maximum MCUB commands per request",
            validator=Integer(default=3, min=0, max=10),
        ),
        ConfigValue(
            "send_messages_enabled",
            True,
            description="Allow the agent to send messages as the userbot",
            validator=Boolean(default=True),
        ),
        ConfigValue(
            "send_message_steps",
            3,
            description="Maximum userbot messages sent per request",
            validator=Integer(default=3, min=0, max=10),
        ),
        ConfigValue(
            "create_chats_enabled",
            True,
            description="Allow the agent to create channels/groups",
            validator=Boolean(default=True),
        ),
        ConfigValue(
            "create_chat_steps",
            2,
            description="Maximum channels/groups created per request",
            validator=Integer(default=2, min=0, max=5),
        ),
        ConfigValue(
            "create_bots_enabled",
            True,
            description="Allow the agent to create Telegram bots via BotFather",
            validator=Boolean(default=True),
        ),
        ConfigValue(
            "create_bot_steps",
            1,
            description="Maximum Telegram bots created per request",
            validator=Integer(default=1, min=0, max=3),
        ),
        ConfigValue(
            "account_tools_enabled",
            True,
            description="Allow the agent to edit profile/join chats/read/search messages",
            validator=Boolean(default=True),
        ),
        ConfigValue(
            "account_tool_steps",
            5,
            description="Maximum account-level tools per request",
            validator=Integer(default=5, min=0, max=15),
        ),
        ConfigValue(
            "chat_management_enabled",
            True,
            description="Allow the agent to manage chats: mute, ban, promote, title, slowmode",
            validator=Boolean(default=True),
        ),
        ConfigValue(
            "chat_management_steps",
            5,
            description="Maximum chat-management tools per request",
            validator=Integer(default=5, min=0, max=15),
        ),
        ConfigValue(
            "media_max_bytes",
            8_000_000,
            description="Maximum replied media bytes sent to AI",
            validator=Integer(default=8_000_000, min=1024, max=25_000_000),
        ),
        ConfigValue(
            "context_enabled",
            True,
            description="Remember chat context between .oa requests",
            validator=Boolean(default=True),
        ),
        ConfigValue(
            "context_turns",
            10,
            description="How many user/assistant turns to remember per chat",
            validator=Integer(default=10, min=0, max=50),
        ),
        ConfigValue(
            "tool_memory_enabled",
            False,
            description="Remember concise notes from tool outputs for next requests",
            validator=Boolean(default=False),
        ),
        ConfigValue(
            "tool_memory_items",
            20,
            description="Maximum remembered tool notes per chat",
            validator=Integer(default=20, min=1, max=200),
        ),
        ConfigValue(
            "tool_memory_max_chars",
            500,
            description="Maximum characters per remembered tool note",
            validator=Integer(default=500, min=80, max=4000),
        ),
        ConfigValue(
            "response_header",
            "🍇 <i>OpenAgent</i> | <b>🕐 {elapsed}s</b> | 🧧 {provider}",
            description="Final response header template. Supports placeholders from placeholders field",
            validator=String(default="🍇 <i>OpenAgent</i> | <b>🕐 {elapsed}s</b> | 🧧 {provider}"),
        ),
        ConfigValue(
            "request_label",
            "<b>📝 Запрос:</b>",
            description="Request block label template. Supports placeholders from placeholders field",
            validator=String(default="<b>📝 Запрос:</b>"),
        ),
        ConfigValue(
            "response_label",
            "<b>💬 Ответ:</b>",
            description="Response block label template. Supports placeholders from placeholders field",
            validator=String(default="<b>💬 Ответ:</b>"),
        ),
        ConfigValue(
            "thinking_template",
            "{random}",
            description="Thinking message template. Supports placeholders from placeholders field",
            validator=String(default="{random}"),
        ),
        ConfigValue(
            "random_strings",
            ["Thinking...", "Думаю...", "Генерирую..."],
            description="Random lines for {random}",
            validator=List(default=["Thinking...", "Думаю...", "Генерирую..."], item_type=str),
        ),
        ConfigValue(
            "placeholders",
            "",
            description="Available OpenAgent placeholders (auto-generated)",
            validator=String(default=""),
        ),
        ConfigValue(
            "repo_context_enabled",
            True,
            description="Inject local workspace snapshot into system prompt",
            validator=Boolean(default=True),
        ),
        ConfigValue(
            "repo_context_max_chars",
            7000,
            description="Maximum chars used for repo context in system prompt",
            validator=Integer(default=7000, min=500, max=30000),
        ),
    )

    async def on_load(self) -> None:
        await super().on_load()
        defaults = {
            "provider": "openai",
            "api_key": "",
            "model": "",
            "custom_base_url": "",
            "system_prompt": (
                "You are OpenAgent inside a Telegram userbot. Help the user directly. "
                "You may inspect the local workspace through terminal commands when needed."
            ),
            "temperature": 0.7,
            "max_tokens": 1200,
            "timeout": 90,
            "terminal_enabled": True,
            "terminal_steps": 3,
            "terminal_timeout": 30,
            "web_search_enabled": True,
            "web_search_steps": 3,
            "mcub_use": False,
            "mcub_steps": 3,
            "send_messages_enabled": True,
            "send_message_steps": 3,
            "create_chats_enabled": True,
            "create_chat_steps": 2,
            "create_bots_enabled": True,
            "create_bot_steps": 1,
            "account_tools_enabled": True,
            "account_tool_steps": 5,
            "chat_management_enabled": True,
            "chat_management_steps": 5,
            "media_max_bytes": 8_000_000,
            "context_enabled": True,
            "context_turns": 10,
            "tool_memory_enabled": False,
            "tool_memory_items": 20,
            "tool_memory_max_chars": 500,
            "response_header": "🍇 <i>OpenAgent</i> | <b>🕐 {elapsed}s</b> | 🧧 {provider}",
            "request_label": "<b>📝 Запрос:</b>",
            "response_label": "<b>💬 Ответ:</b>",
            "thinking_template": "{random}",
            "random_strings": ["Thinking...", "Думаю...", "Генерирую..."],
            "placeholders": "",
            "repo_context_enabled": True,
            "repo_context_max_chars": 7000,
        }
        config_dict = await self.kernel.get_module_config(self.name, defaults)
        if isinstance(config_dict.get("random_strings"), str):
            config_dict["random_strings"] = [
                line.strip()
                for line in config_dict["random_strings"].splitlines()
                if line.strip()
            ] or defaults["random_strings"]
        config_dict["placeholders"] = self._format_placeholders()
        provider = self._normalize_provider(str(config_dict.get("provider", "openai")))
        config_dict["provider"] = provider if provider in self.PROVIDERS else "openai"
        self.config.from_dict(config_dict)
        self.kernel.store_module_config_schema(self.name, self.config)
        clean = {k: v for k, v in self.config.to_dict().items() if v is not None}
        if clean:
            await self.kernel.save_module_config(self.name, clean)
        self._last_request_at = 0.0
        self._skills_dir = self._resolve_skills_dir()
        self._chat_history: dict[int, list[dict[str, str]]] = {}
        self._tool_memory: dict[int, list[str]] = {}
        self._cancelled_generations: set[str] = set()
        self._regen_payloads: dict[str, dict[str, Any]] = {}
        self._last_token_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
        self.log.info("OpenAgent loaded")

    def _provider(self) -> str:
        provider = str(self.config.get("provider", "openai")).lower().strip()
        return provider if provider in self.PROVIDERS else "openai"

    def _normalize_provider(self, provider: str) -> str:
        aliases = {
            "ollama": "ollama.cloud",
            "ollama_cloud": "ollama.cloud",
            "custom": "other",
            "deepseek": "other",
        }
        provider = provider.lower().strip()
        return aliases.get(provider, provider)

    def _model(self, provider: str | None = None) -> str:
        provider = provider or self._provider()
        model = str(self.config.get("model", "")).strip()
        return model or self.DEFAULT_MODELS[provider]

    def _api_key(self) -> str:
        return str(self.config.get("api_key", "") or "").strip()

    def _provider_label(self) -> str:
        return self.PROVIDER_LABELS.get(self._provider(), "Custom")

    def _response_title(self, elapsed: float) -> str:
        return self._render_template(
            str(self.config.get("response_header", ""))
            or "🍇 <i>OpenAgent</i> | <b>🕐 {elapsed}s</b> | 🧧 {provider}",
            elapsed=elapsed,
        )

    def _placeholder_values(self, *, elapsed: float | None = None) -> dict[str, str]:
        raw_random = self.config.get("random_strings", []) or []
        if isinstance(raw_random, str):
            raw_random = raw_random.splitlines()
        random_lines = [str(line).strip() for line in raw_random if str(line).strip()]
        random_value = random.choice(random_lines) if random_lines else "Thinking..."
        return {
            "provider": self._provider_label(),
            "provider_key": self._provider(),
            "model": self._model(),
            "tool_count": str(len(self.TOOL_REGISTRY)),
            "elapsed": f"{elapsed:.1f}" if elapsed is not None else "0.0",
            "input_tokens": str(self._last_token_usage.get("input_tokens", 0)),
            "output_tokens": str(self._last_token_usage.get("output_tokens", 0)),
            "total_tokens": str(self._last_token_usage.get("total_tokens", 0)),
            "random": random_value,
            "prefix": getattr(self.kernel, "custom_prefix", ".") or ".",
            "time": time.strftime("%H:%M:%S"),
            "date": time.strftime("%Y-%m-%d"),
        }

    def _render_template(self, template: str, *, elapsed: float | None = None) -> str:
        values = self._placeholder_values(elapsed=elapsed)
        result = template or ""
        for key, value in values.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    def _thinking_text(self) -> str:
        return self._render_template(
            str(self.config.get("thinking_template", "") or "{random}")
        )

    def _format_placeholders(self) -> str:
        return "\n".join(
            [
                "{provider} - Provider label",
                "{provider_key} - Provider config key",
                "{model} - Current model",
                "{tool_count} - Registered OpenAgent tool operation count",
                "{elapsed} - Generation time seconds",
                "{input_tokens} - Input/prompt tokens accepted by provider",
                "{output_tokens} - Output/completion tokens returned by provider",
                "{total_tokens} - Total tokens for last provider response",
                "{random} - Random line from random_strings",
                "{prefix} - Current command prefix",
                "{time} - Current local time",
                "{date} - Current local date",
            ]
        )

    def _tool_registry_prompt(self) -> str:
        lines = []
        for index, name in enumerate(self.TOOL_REGISTRY, 1):
            lines.append(f"{index}. {name}")
        return "\n".join(lines)

    def _request_label(self, *, elapsed: float | None = None) -> str:
        return self._render_template(
            str(self.config.get("request_label", "") or "<b>📝 Запрос:</b>"),
            elapsed=elapsed,
        )

    def _response_label(self, *, elapsed: float | None = None) -> str:
        return self._render_template(
            str(self.config.get("response_label", "") or "<b>💬 Ответ:</b>"),
            elapsed=elapsed,
        )

    def _remember_context(self, chat_id: int | None, prompt: str, answer: str) -> None:
        if not chat_id or not self.config["context_enabled"]:
            return
        history = self._chat_history.setdefault(int(chat_id), [])
        history.extend(
            [
                {"role": "user", "content": prompt[-8000:]},
                {"role": "assistant", "content": answer[-8000:]},
            ]
        )
        max_messages = int(self.config["context_turns"]) * 2
        if max_messages <= 0:
            history.clear()
        else:
            del history[:-max_messages]

    def _history_for_chat(self, chat_id: int | None) -> list[dict[str, str]]:
        if not chat_id or not self.config["context_enabled"]:
            return []
        return list(self._chat_history.get(int(chat_id), []))

    def _tool_memory_note(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        if not text:
            return ""
        max_chars = int(self.config.get("tool_memory_max_chars", 500) or 500)
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + "..."
        return text

    def _remember_tool_output(self, chat_id: int | None, tool_name: str, output: str) -> None:
        if not chat_id or not bool(self.config.get("tool_memory_enabled", False)):
            return
        note = self._tool_memory_note(output)
        if not note:
            return
        memory = self._tool_memory.setdefault(int(chat_id), [])
        memory.append(f"{tool_name}: {note}")
        max_items = int(self.config.get("tool_memory_items", 20) or 20)
        if max_items <= 0:
            memory.clear()
        else:
            del memory[:-max_items]

    def _tool_memory_prompt(self, chat_id: int | None) -> str:
        if not chat_id or not bool(self.config.get("tool_memory_enabled", False)):
            return ""
        notes = self._tool_memory.get(int(chat_id), [])
        if not notes:
            return ""
        return "Recent tool memory:\n" + "\n".join(f"- {line}" for line in notes[-int(self.config.get("tool_memory_items", 20) or 20):])

    def _base_url(self, provider: str) -> str:
        if provider == "other":
            return str(self.config.get("custom_base_url", "") or "").strip().rstrip("/")
        return self.BASE_URLS[provider].rstrip("/")

    def _args_raw(self, event: events.NewMessage.Event) -> str:
        return self.args_raw(event).strip()

    async def _set_config_value(self, key: str, value: Any) -> None:
        self.config[key] = value
        await self.save_config()

    def _resolve_skills_dir(self) -> Path:
        path = Path.cwd() / "openagent_skills"
        path.mkdir(exist_ok=True)
        return path

    def _workspace_dir(self) -> str:
        work_dir = getattr(self.kernel, "WORK_DIR", None)
        if work_dir:
            path = Path(str(work_dir)).expanduser()
            if path.exists() and path.is_dir():
                return str(path)
        return str(Path.cwd())

    def _repo_context_prompt(self) -> str:
        if not bool(self.config.get("repo_context_enabled", True)):
            return ""
        workspace = Path(self._workspace_dir())
        max_chars = int(self.config.get("repo_context_max_chars", 7000) or 7000)
        lines: list[str] = [f"Workspace: {workspace}"]
        try:
            entries = sorted(
                workspace.iterdir(),
                key=lambda p: (p.is_file(), p.name.lower()),
            )
            top = []
            for item in entries[:80]:
                marker = "/" if item.is_dir() else ""
                top.append(item.name + marker)
            if top:
                lines.append("Top-level:")
                lines.extend(f"- {name}" for name in top)
        except Exception as exc:
            lines.append(f"Top-level unavailable: {exc}")
            return "\n".join(lines)[:max_chars]

        key_files = ["README.md", "pyproject.toml", "requirements.txt", "config.example.json", "modules.ini"]
        for name in key_files:
            file_path = workspace / name
            if not file_path.is_file():
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace").strip()
            except Exception as exc:
                lines.append(f"{name}: read error: {exc}")
                continue
            if name.endswith(".json"):
                try:
                    obj = json.loads(text)
                    short = json.dumps(obj, ensure_ascii=False, indent=2)[:1200]
                except Exception:
                    short = text[:1200]
            else:
                short = text[:1200]
            lines.append(f"{name}:\n{short}")

        module_dirs = [workspace / "modules", workspace / "modules_loaded"]
        for mdir in module_dirs:
            if not mdir.is_dir():
                continue
            try:
                mod_names = sorted(p.name for p in mdir.iterdir() if p.is_file())[:120]
            except Exception as exc:
                lines.append(f"{mdir.name}: unavailable: {exc}")
                continue
            lines.append(f"{mdir.name} files ({len(mod_names)} shown):")
            lines.extend(f"- {mn}" for mn in mod_names)

        text = "\n".join(lines)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [repo context truncated]"
        return "\n\nLocal MCUB workspace snapshot:\n" + text

    def _safe_skill_name(self, name: str) -> str:
        name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", name.strip()).strip("._")
        return name[:64] or "skill"

    def _skill_path(self, name: str) -> Path:
        if not getattr(self, "_skills_dir", None):
            self._skills_dir = self._resolve_skills_dir()
        return self._skills_dir / f"{self._safe_skill_name(name)}.md"

    def _list_skills(self) -> list[Path]:
        if not getattr(self, "_skills_dir", None):
            self._skills_dir = self._resolve_skills_dir()
        try:
            self._skills_dir.mkdir(parents=True, exist_ok=True)
            return sorted(self._skills_dir.glob("*.md"), key=lambda p: p.name.lower())
        except Exception as e:
            self.log.warning(f"OpenAgent skills directory unavailable: {e}")
            return []

    def _load_skills_prompt(self) -> str:
        chunks = []
        for path in self._list_skills()[:20]:
            try:
                text = path.read_text(encoding="utf-8")[:4000]
            except Exception:
                continue
            chunks.append(f"## Skill: {path.stem}\n{text}")
        if not chunks:
            return ""
        return "\n\nLoaded OpenAgent skills. Use them when relevant:\n" + "\n\n".join(chunks)

    async def _save_skill(self, name: str, content: str) -> str:
        safe_name = self._safe_skill_name(name)
        path = self._skill_path(safe_name)
        path.write_text(content.strip() + "\n", encoding="utf-8")
        return safe_name


    def _system_prompt(self) -> str:
        prompt = str(self.config["system_prompt"]).strip()
        tlist = ", ".join(sorted(self._get_tool_map().keys()))
        prompt += (
            f"\n\nOpenAgent 0.5.0 refreshed architecture is active. You have access to {len(self.TOOL_REGISTRY)} tool operations.\n"
            "To use a tool, output exactly one XML tag per turn: <tool.name attr=\"val\">body</tool.name> or <tool.name/>.\n"
            f"Available tool names: {tlist}\n"
            "\nCore guidelines:\n"
            "1. Use terminal.run for shell commands (cwd is dynamic).\n"
            "2. Use web.search for search or web.fetch_url for direct page reading.\n"
            "3. Use message.send_current or message.send_target for sending messages.\n"
            "4. Use chat.* and profile.* for management.\n"
            "5. If you need to create a skill for later use, use skills.save_from_ai.\n"
            "Never explain the tool call. Just output it and wait for results."
        )
        prompt += self._load_skills_prompt()
        prompt += self._repo_context_prompt()
        return prompt

    async def _run_terminal(self, command: str) -> str:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=self._workspace_dir(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=int(self.config["terminal_timeout"])
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return f"Command timed out after {self.config['terminal_timeout']}s"

        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
        result = f"exit_code={proc.returncode}\n"
        if out:
            result += f"stdout:\n{out}\n"
        if err:
            result += f"stderr:\n{err}\n"
        return result[-6000:]

    def _looks_like_url(self, value: str) -> bool:
        value = value.strip()
        if value.startswith(("http://", "https://")):
            return True
        parsed = urlparse("https://" + value)
        return "." in parsed.netloc and " " not in parsed.netloc

    def _html_to_text(self, value: str) -> str:
        value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
        value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
        title_match = re.search(r"<title[^>]*>(.*?)</title>", value, flags=re.I | re.S)
        title = html.unescape(re.sub(r"<[^>]+>", " ", title_match.group(1))).strip() if title_match else ""
        links = []
        for href, text in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', value, flags=re.I | re.S)[:40]:
            text_clean = html.unescape(re.sub(r"<[^>]+>", " ", text)).strip()
            if text_clean and href:
                links.append(f"- {text_clean}: {href}")
        body = html.unescape(re.sub(r"<[^>]+>", " ", value))
        body = re.sub(r"\s+", " ", body).strip()
        parts = []
        if title:
            parts.append(f"Title: {title}")
        if body:
            parts.append("Content:\n" + body[:12000])
        if links:
            parts.append("Links:\n" + "\n".join(links))
        return "\n\n".join(parts) or "No readable content"

    async def _web_search(self, query: str) -> str:
        query = query.strip()
        if self._looks_like_url(query):
            url = query if query.startswith(("http://", "https://")) else "https://" + query
            headers = {"User-Agent": "Mozilla/5.0"}
            timeout = aiohttp.ClientTimeout(total=int(self.config["timeout"]))
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url, allow_redirects=True) as resp:
                    text = await resp.text(errors="replace")
                    if resp.status >= 400:
                        raise RuntimeError(f"Fetch HTTP {resp.status}: {text[:500]}")
                    content_type = resp.headers.get("Content-Type", "")
            if "html" in content_type.lower():
                return f"Fetched URL: {url}\n\n" + self._html_to_text(text)
            return f"Fetched URL: {url}\nContent-Type: {content_type}\n\n{text[:12000]}"

        url = f"https://duckduckgo.com/html/?q={quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        timeout = aiohttp.ClientTimeout(total=int(self.config["timeout"]))
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise RuntimeError(f"Search HTTP {resp.status}: {text[:500]}")

        results = []
        blocks = re.findall(
            r'<a[^>]+class="result__a"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>',
            text,
            flags=re.DOTALL | re.I,
        )
        if not blocks:
            blocks = re.findall(
                r'<a[^>]+class="result__a"[^>]*>(.*?)</a>',
                text,
                flags=re.DOTALL | re.I,
            )
            blocks = [(title, "") for title in blocks]

        for title, snippet in blocks[:5]:
            title_text = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
            snippet_text = html.unescape(re.sub(r"<[^>]+>", "", snippet)).strip()
            if title_text:
                results.append(f"- {title_text}: {snippet_text}".strip())
        return "\n".join(results) or "No search results found"

    async def _fetch_mcub_docs(self) -> str:
        timeout = aiohttp.ClientTimeout(total=int(self.config["timeout"]))
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(self.MCUB_DOCS_URL) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise RuntimeError(f"Docs HTTP {resp.status}: {text[:500]}")
                return text[:60000]

    def _format_entity_profile(self, entity: Any) -> str:
        username = f"@{entity.username}" if getattr(entity, "username", None) else ""
        name = " ".join(
            p
            for p in (
                getattr(entity, "first_name", None),
                getattr(entity, "last_name", None),
            )
            if p
        ) or getattr(entity, "title", None) or "Unknown"
        return (
            f"Name: {name}\n"
            f"Username: {username}\n"
            f"ID: {getattr(entity, 'id', None)}\n"
            f"Access hash: {getattr(entity, 'access_hash', None)}\n"
            f"Bot: {getattr(entity, 'bot', None)}\n"
            f"Verified: {getattr(entity, 'verified', None)}\n"
            f"Premium: {getattr(entity, 'premium', None)}\n"
            f"Scam: {getattr(entity, 'scam', None)}\n"
            f"Fake: {getattr(entity, 'fake', None)}\n"
            f"Deleted: {getattr(entity, 'deleted', None)}\n"
            f"Contact: {getattr(entity, 'contact', None)}\n"
            f"Mutual contact: {getattr(entity, 'mutual_contact', None)}\n"
            f"Restricted: {getattr(entity, 'restricted', None)}\n"
            f"Support: {getattr(entity, 'support', None)}\n"
            f"Bot chat history: {getattr(entity, 'bot_chat_history', None)}\n"
            f"Bot no chats: {getattr(entity, 'bot_nochats', None)}\n"
            f"Language code: {getattr(entity, 'lang_code', None)}\n"
            f"Phone visible: {'yes' if getattr(entity, 'phone', None) else 'no'}\n"
            f"Photo object: {getattr(entity, 'photo', None)}\n"
            f"Emoji status: {getattr(entity, 'emoji_status', None)}"
        )

    async def _format_full_profile(self, entity: Any) -> str:
        lines = [self._format_entity_profile(entity)]
        try:
            full = await self.client(GetFullUserRequest(entity))
            full_user = getattr(full, "full_user", None)
            if full_user is not None:
                lines.append(
                    "Full profile:\n"
                    f"About: {getattr(full_user, 'about', None)}\n"
                    f"Common chats count: {getattr(full_user, 'common_chats_count', None)}\n"
                    f"Blocked: {getattr(full_user, 'blocked', None)}\n"
                    f"Phone calls available: {getattr(full_user, 'phone_calls_available', None)}\n"
                    f"Video calls available: {getattr(full_user, 'video_calls_available', None)}\n"
                    f"Voice messages forbidden: {getattr(full_user, 'voice_messages_forbidden', None)}\n"
                    f"Stories pinned available: {getattr(full_user, 'stories_pinned_available', None)}\n"
                    f"Profile photo: {getattr(full_user, 'profile_photo', None)}"
                )
        except Exception as exc:
            lines.append(f"Full profile unavailable: {exc}")

        try:
            photos = await self.client.get_profile_photos(entity, limit=1)
            lines.append(f"Profile photos count fetched: {len(photos)}")
        except Exception as exc:
            lines.append(f"Profile photos unavailable: {exc}")

        try:
            directory = Path.cwd() / "openagent_profiles"
            directory.mkdir(parents=True, exist_ok=True)
            path = await self.client.download_profile_photo(
                entity,
                file=str(directory / f"profile_{getattr(entity, 'id', 'unknown')}.jpg"),
            )
            if path:
                lines.append(
                    "Avatar: Telegram does not expose a permanent public avatar URL via client API.\n"
                    f"Avatar local file: {path}"
                )
            else:
                lines.append("Avatar: no accessible profile photo")
        except Exception as exc:
            lines.append(f"Avatar download failed: {exc}")

        try:
            common = await self.client.get_common_chats(entity, limit=10)
            if common:
                formatted = []
                for chat in common:
                    title = getattr(chat, "title", None) or getattr(chat, "first_name", None) or "Unknown"
                    username = f"@{chat.username}" if getattr(chat, "username", None) else ""
                    formatted.append(f"{title} {username} [id={getattr(chat, 'id', None)}]".strip())
                lines.append("Common chats:\n" + "\n".join(formatted))
        except Exception:
            pass

        return "\n\n".join(lines)

    def _safe_generated_filename(self, filename: str) -> str:
        filename = Path(filename.strip() or "generated.py").name
        filename = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename).strip("._")
        if not filename:
            filename = "generated.py"
        if "." not in filename:
            filename += ".py"
        return filename[:96]

    def _extract_generated_file(self, answer: str, fallback_name: str = "generated.py") -> tuple[str, str]:
        match = self.GENERATED_FILE_RE.search(answer or "")
        if match:
            return self._safe_generated_filename(match.group(1)), match.group(2).strip("\n")

        fence = re.search(r"```([A-Za-z0-9_+.-]*)\n(.*?)```", answer or "", re.DOTALL)
        if fence:
            lang = (fence.group(1) or "").lower()
            ext = {
                "python": ".py",
                "py": ".py",
                "javascript": ".js",
                "js": ".js",
                "typescript": ".ts",
                "ts": ".ts",
                "html": ".html",
                "css": ".css",
                "json": ".json",
                "yaml": ".yaml",
                "yml": ".yml",
                "bash": ".sh",
                "sh": ".sh",
                "sql": ".sql",
                "md": ".md",
                "markdown": ".md",
            }.get(lang, Path(fallback_name).suffix or ".txt")
            return self._safe_generated_filename("generated" + ext), fence.group(2).strip("\n")

        return self._safe_generated_filename(fallback_name), (answer or "").strip()

    def _is_text_file(self, mime_type: str, file_name: str) -> bool:
        if mime_type.startswith("text/"):
            return True
        suffix = Path(file_name or "").suffix.lower()
        return suffix in {
            ".txt",
            ".md",
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".csv",
            ".log",
            ".xml",
            ".html",
            ".css",
            ".sh",
            ".sql",
        }

    async def _extract_video_frame(self, data: bytes, suffix: str) -> bytes | None:
        suffix = suffix if suffix.startswith(".") else ".webm"
        with tempfile.TemporaryDirectory(prefix="openagent_media_") as tmp:
            src = Path(tmp) / f"input{suffix}"
            dst = Path(tmp) / "frame.png"
            src.write_bytes(data)
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-y",
                "-i",
                str(src),
                "-frames:v",
                "1",
                "-vf",
                "scale='min(1024,iw)':-1",
                str(dst),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                await asyncio.wait_for(proc.communicate(), timeout=15)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return None
            if proc.returncode != 0 or not dst.exists():
                return None
            return dst.read_bytes()

    async def _reply_context(
        self, event: events.NewMessage.Event
    ) -> tuple[str, list[dict[str, str]]]:
        reply = await event.get_reply_message()
        if not reply:
            return "", []

        parts = []
        attachments: list[dict[str, str]] = []
        try:
            sender = await reply.get_sender()
        except Exception:
            sender = None
        if sender is not None:
            parts.append("Replied sender profile:\n" + self._format_entity_profile(sender))

        reply_text = getattr(reply, "raw_text", None) or getattr(reply, "text", "") or ""
        if reply_text:
            parts.append(f"Replied message text:\n{reply_text[:12000]}")

        if not getattr(reply, "media", None):
            return "\n\n".join(parts), attachments

        file_obj = getattr(reply, "file", None)
        file_name = getattr(file_obj, "name", None) or "attachment"
        mime_type = getattr(file_obj, "mime_type", None) or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        size = getattr(file_obj, "size", None) or 0
        parts.append(f"Replied media: name={file_name}, mime={mime_type}, size={size}")

        try:
            data = await reply.download_media(file=bytes)
        except Exception as exc:
            parts.append(f"Could not download replied media: {exc}")
            return "\n\n".join(parts), attachments

        if not data:
            return "\n\n".join(parts), attachments

        if self._is_text_file(mime_type, file_name):
            text = data.decode("utf-8", errors="replace")
            parts.append(f"File content ({file_name}):\n{text[:20000]}")
            return "\n\n".join(parts), attachments

        if len(data) > int(self.config["media_max_bytes"]):
            parts.append("Media is too large to send to AI; metadata only was included.")
            return "\n\n".join(parts), attachments

        if mime_type.startswith("video/"):
            frame = await self._extract_video_frame(data, Path(file_name).suffix or ".webm")
            if frame:
                attachments.append(
                    {
                        "name": f"{file_name}_first_frame.png",
                        "mime_type": "image/png",
                        "data": base64.b64encode(frame).decode("ascii"),
                    }
                )
                parts.append("First frame extracted from replied video/sticker and attached as image.")
            else:
                attachments.append(
                    {
                        "name": file_name,
                        "mime_type": mime_type,
                        "data": base64.b64encode(data).decode("ascii"),
                    }
                )
                parts.append("Could not extract video frame; raw video attached only for providers that support it.")
        elif mime_type.startswith(("image/", "audio/")):
            attachments.append(
                {
                    "name": file_name,
                    "mime_type": mime_type,
                    "data": base64.b64encode(data).decode("ascii"),
                }
            )
            parts.append("Media bytes attached to AI request when provider supports it.")
        else:
            parts.append("Unsupported binary media type; metadata only was included.")
        return "\n\n".join(parts), attachments

    def _build_openai_content(
        self, prompt: str, attachments: list[dict[str, str]]
    ) -> str | list[dict[str, Any]]:
        if not attachments:
            return prompt
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        skipped = []
        for item in attachments:
            mime_type = item["mime_type"]
            if mime_type.startswith("image/"):
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{item['data']}"
                        },
                    }
                )
            else:
                skipped.append(f"{item['name']} ({mime_type})")
        if skipped:
            content[0]["text"] += "\n\nProvider note: non-image media not sent to OpenAI-compatible endpoint: " + ", ".join(skipped)
        return content

    def _build_google_parts(
        self, content: str | list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if isinstance(content, str):
            return [{"text": content}]
        parts = []
        for item in content:
            if item.get("type") == "text":
                parts.append({"text": item.get("text", "")})
            elif item.get("type") == "media":
                parts.append(
                    {
                        "inline_data": {
                            "mime_type": item["mime_type"],
                            "data": item["data"],
                        }
                    }
                )
        return parts or [{"text": ""}]

    def _build_google_content(
        self, prompt: str, attachments: list[dict[str, str]]
    ) -> str | list[dict[str, Any]]:
        if not attachments:
            return prompt
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for item in attachments:
            content.append({"type": "media", **item})
        return content

    class _MCUBEvent:
        def __init__(self, outer: "OpenAgent", source_event: Any, text: str) -> None:
            self._outer = outer
            self._source_event = source_event
            self.text = text
            self.raw_text = text
            self.message = self
            self.client = outer.client
            self.chat_id = getattr(source_event, "chat_id", None)
            self.sender_id = getattr(outer.kernel, "ADMIN_ID", None) or getattr(
                source_event, "sender_id", None
            )
            self.id = getattr(source_event, "id", 0)
            self.out = True
            self.piped = False
            self.pipe_input = None
            self.pipe_output = None
            self.pipe_exit_code = 0
            self.no_add_args_to_input = False
            self._outputs: list[str] = []

        async def edit(self, text: str, *args: Any, **kwargs: Any) -> "OpenAgent._MCUBEvent":
            self._outputs.append(str(text))
            return self

        async def reply(self, text: str, *args: Any, **kwargs: Any) -> "OpenAgent._MCUBEvent":
            self._outputs.append(str(text))
            return self

        async def respond(self, text: str, *args: Any, **kwargs: Any) -> "OpenAgent._MCUBEvent":
            self._outputs.append(str(text))
            return self

        async def delete(self, *args: Any, **kwargs: Any) -> None:
            return None

        async def get_reply_message(self) -> Any:
            if hasattr(self._source_event, "get_reply_message"):
                return await self._source_event.get_reply_message()
            return None

        async def get_chat(self) -> Any:
            if hasattr(self._source_event, "get_chat"):
                return await self._source_event.get_chat()
            return None

        async def get_sender(self) -> Any:
            if hasattr(self._source_event, "get_sender"):
                return await self._source_event.get_sender()
            return None

        @property
        def output(self) -> str:
            return "\n\n".join(self._outputs).strip()

    async def _run_mcub_command(self, command: str, source_event: Any) -> str:
        command = command.strip()
        if not command:
            return "Empty MCUB command"
        prefix = getattr(self.kernel, "custom_prefix", ".") or "."
        if not command.startswith(prefix):
            command = prefix + command

        cmd_name = command[len(prefix) :].split(maxsplit=1)[0].lower()
        if cmd_name in {"oa", "agent"}:
            return "Blocked recursive OpenAgent command"

        event = self._MCUBEvent(self, source_event, command)
        try:
            handled = await self.kernel.process_command(event)
        except Exception as exc:
            await self.kernel.handle_error(exc, source="OpenAgent:mcub", event=source_event)
            return f"MCUB command failed: {exc}"
        output = event.output or f"Command handled: {handled}"
        return output[-6000:]

    async def _dialogs_tool(self, mode: str) -> str:
        mode = (mode or "private").strip().lower()
        lines = []
        try:
            async for dialog in self.client.iter_dialogs(limit=80):
                entity = dialog.entity
                is_user = bool(getattr(entity, "first_name", None) or getattr(entity, "last_name", None))
                is_bot = bool(getattr(entity, "bot", False))
                is_group = bool(getattr(entity, "megagroup", False) or getattr(entity, "broadcast", False))
                if mode in {"private", "pm", "dm", "лс"} and (not is_user or is_bot):
                    continue
                if mode in {"groups", "group", "chats", "группы"} and not is_group:
                    continue
                username = f"@{entity.username}" if getattr(entity, "username", None) else ""
                name = getattr(dialog, "name", None) or " ".join(
                    p
                    for p in (
                        getattr(entity, "first_name", None),
                        getattr(entity, "last_name", None),
                    )
                    if p
                ) or getattr(entity, "title", None) or "Unknown"
                unread = getattr(dialog, "unread_count", 0)
                lines.append(
                    f"{name} {username} [id={getattr(entity, 'id', None)}] unread={unread}".strip()
                )
                if len(lines) >= 40:
                    break
        except Exception as exc:
            return f"Could not list dialogs: {exc}"
        return "\n".join(lines) or "No dialogs found"

    async def _chat_tool(self, query: str, source_event: Any) -> str:
        query = (query or "info").strip().lower()
        chat_id = getattr(source_event, "chat_id", None)
        if not chat_id:
            return "No chat context available"

        if query in {"participants", "members", "users"}:
            lines = []
            try:
                async for user in self.client.iter_participants(chat_id, limit=30):
                    username = f"@{user.username}" if getattr(user, "username", None) else ""
                    name = " ".join(
                        p for p in (getattr(user, "first_name", None), getattr(user, "last_name", None)) if p
                    ) or "Unknown"
                    lines.append(f"{name} {username} [{user.id}]".strip())
            except Exception as exc:
                return f"Could not list participants: {exc}"
            return "\n".join(lines) or "No participants found"

        try:
            chat = await source_event.get_chat()
        except Exception:
            chat = await self.client.get_entity(chat_id)
        title = getattr(chat, "title", None) or getattr(chat, "first_name", None) or "Unknown"
        username = f"@{chat.username}" if getattr(chat, "username", None) else ""
        return (
            f"Chat title: {title}\n"
            f"Username: {username}\n"
            f"ID: {getattr(chat, 'id', chat_id)}\n"
            f"Megagroup: {getattr(chat, 'megagroup', None)}\n"
            f"Broadcast: {getattr(chat, 'broadcast', None)}"
        )

    async def _profile_tool(self, target: str, source_event: Any) -> str:
        target = (target or "").strip()
        try:
            if not target or target.lower() in {"reply", "replied"}:
                reply = await source_event.get_reply_message()
                entity = await reply.get_sender() if reply else await source_event.get_sender()
            else:
                try:
                    entity = await self.client.get_entity(int(target))
                except ValueError:
                    entity = await self.client.get_entity(target)
        except Exception as exc:
            return f"Could not resolve profile: {exc}"

        return await self._format_full_profile(entity)

    async def _send_userbot_message(
        self,
        text: str,
        source_event: Any,
        chat: str | None = None,
    ) -> str:
        text = (text or "").strip()
        if not text:
            return "Message text is empty"
        if chat:
            chat = chat.strip()
            try:
                entity: Any = int(chat)
            except ValueError:
                entity = chat
        else:
            entity = getattr(source_event, "chat_id", None)
        if entity is None:
            return "No target chat available"
        try:
            sent = await self.client.send_message(entity, text)
        except Exception as exc:
            return f"Could not send message: {exc}"
        target = chat or str(getattr(source_event, "chat_id", entity))
        return f"Message sent to {target}, id={getattr(sent, 'id', None)}"

    def _parse_xml_attrs(self, attrs: str) -> dict[str, str]:
        parsed: dict[str, str] = {}
        for key, value in re.findall(r"([a-zA-Z_][\w.-]*)=[\"']([^\"']*)[\"']", attrs or ""):
            parsed[key.lower()] = html.unescape(value.strip())
        return parsed

    async def _fetch_url_bytes(self, url: str) -> tuple[bytes, str] | None:
        timeout = aiohttp.ClientTimeout(total=int(self.config["timeout"]))
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status >= 400:
                    return None
                data = await resp.read()
                content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
                return data, content_type

    async def _set_channel_avatar(
        self,
        channel: Any,
        attrs: dict[str, str],
        source_event: Any | None,
    ) -> str | None:
        data: bytes | None = None
        mime_type = "image/jpeg"
        avatar_url = attrs.get("avatar_url") or attrs.get("avatar") or attrs.get("photo_url")
        if avatar_url:
            fetched = await self._fetch_url_bytes(avatar_url)
            if fetched:
                data, mime_type = fetched
        elif source_event is not None and attrs.get("avatar_reply", "").lower() in {"1", "true", "yes"}:
            reply = await source_event.get_reply_message()
            if reply and getattr(reply, "media", None):
                data = await reply.download_media(file=bytes)
                file_obj = getattr(reply, "file", None)
                mime_type = getattr(file_obj, "mime_type", None) or "image/jpeg"

        if not data:
            return None
        if not mime_type.startswith("image/"):
            return "avatar skipped: media is not an image"
        ext = mimetypes.guess_extension(mime_type) or ".jpg"
        buf = io.BytesIO(data)
        buf.name = f"avatar{ext}"
        uploaded = await self.client.upload_file(buf)
        await self.client(EditPhotoRequest(channel=channel, photo=uploaded))
        return "avatar set"

    async def _create_channel_or_group(
        self,
        kind: str,
        attrs_raw: str,
        body: str,
        source_event: Any | None,
    ) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        title = attrs.get("title") or (body.strip().splitlines()[0] if body.strip() else "OpenAgent Chat")
        about = attrs.get("about") or attrs.get("description") or "\n".join(body.strip().splitlines()[1:]).strip()
        username = (attrs.get("username") or attrs.get("public") or "").lstrip("@")
        invite_title = attrs.get("invite_title") or attrs.get("invite") or "OpenAgent invite"
        is_group = kind == "group"

        result = await self.client(
            CreateChannelRequest(
                title=title[:128],
                about=about[:255] if about else "",
                megagroup=is_group,
                broadcast=not is_group,
            )
        )
        channel = result.chats[0]
        channel_id = getattr(channel, "id", None)
        lines = [f"Created {kind}: {title} [id={channel_id}]"]

        if about:
            try:
                await self.client(EditChatAboutRequest(peer=channel, about=about[:255]))
                lines.append("description set")
            except Exception as exc:
                lines.append(f"description failed: {exc}")

        if username:
            try:
                await self.client(UpdateUsernameRequest(channel=channel, username=username))
                lines.append(f"public link: https://t.me/{username}")
            except Exception as exc:
                lines.append(f"public username failed: {exc}")

        try:
            avatar_result = await self._set_channel_avatar(channel, attrs, source_event)
            if avatar_result:
                lines.append(avatar_result)
        except Exception as exc:
            lines.append(f"avatar failed: {exc}")

        if not username or attrs.get("private_link", "").lower() in {"1", "true", "yes"} or invite_title:
            try:
                invite = await self.client(
                    ExportChatInviteRequest(peer=channel, title=invite_title[:32])
                )
                link = getattr(invite, "link", None)
                if link:
                    lines.append(f"private invite: {link}")
            except Exception as exc:
                lines.append(f"private invite failed: {exc}")
        return "\n".join(lines)

    async def _create_bot_via_botfather(self, attrs_raw: str, body: str) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        name = attrs.get("name") or attrs.get("title") or (body.strip().splitlines()[0] if body.strip() else "OpenAgent Bot")
        username = (attrs.get("username") or attrs.get("user") or "").lstrip("@")
        description = attrs.get("description") or attrs.get("about") or "\n".join(body.strip().splitlines()[1:]).strip()
        if not username:
            return "Bot username is required"
        if not username.lower().endswith("bot"):
            return "Bot username must end with 'bot'"

        token_re = re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b")
        try:
            async with self.client.conversation("BotFather", timeout=120, exclusive=False) as conv:
                await conv.send_message("/newbot")
                await conv.get_response()
                await conv.send_message(name[:64])
                await conv.get_response()
                await conv.send_message(username[:32])
                response = await conv.get_response()
                text = getattr(response, "raw_text", None) or getattr(response, "text", "") or ""
                token_match = token_re.search(text)
                if not token_match:
                    return f"BotFather did not return token. Response: {text[:1000]}"
                token = token_match.group(0)

                if description:
                    try:
                        await conv.send_message("/setdescription")
                        await conv.get_response()
                        await conv.send_message(f"@{username}")
                        await conv.get_response()
                        await conv.send_message(description[:512])
                        await conv.get_response()
                    except Exception as exc:
                        return f"Bot created @{username}\nToken: {token}\nDescription failed: {exc}"
        except Exception as exc:
            return f"Bot creation failed: {exc}"

        return f"Bot created: @{username}\nName: {name}\nToken: {token}"

    async def _resolve_tool_chat(self, chat: str | None, source_event: Any | None) -> Any:
        chat = (chat or "").strip()
        if not chat or chat.lower() in {"current", "this", "here"}:
            if source_event is not None and getattr(source_event, "chat_id", None) is not None:
                return getattr(source_event, "chat_id")
            return "me"
        try:
            return int(chat)
        except ValueError:
            return chat

    async def _resolve_tool_user(self, user: str | None, source_event: Any | None) -> Any:
        user = (user or "").strip()
        if user:
            try:
                return int(user)
            except ValueError:
                return user
        if source_event is not None:
            reply = await source_event.get_reply_message()
            if reply:
                sender = await reply.get_sender()
                if sender is not None:
                    return sender
        raise ValueError("user is required or reply to a user's message")

    async def _history_tool(self, attrs_raw: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        limit = max(1, min(int(attrs.get("limit", "20") or 20), 100))
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        lines = []
        try:
            async for msg in self.client.iter_messages(chat, limit=limit):
                sender = await msg.get_sender()
                name = self._format_sender_short(sender)
                text = getattr(msg, "raw_text", None) or getattr(msg, "text", "") or ""
                media = " [media]" if getattr(msg, "media", None) else ""
                lines.append(f"#{msg.id} {name}: {text[:500]}{media}".strip())
        except Exception as exc:
            return f"Could not read history: {exc}"
        return "\n".join(reversed(lines)) or "No messages found"

    async def _search_messages_tool(
        self, attrs_raw: str, body: str, source_event: Any | None
    ) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        query = attrs.get("query") or body.strip()
        if not query:
            return "Search query is empty"
        limit = max(1, min(int(attrs.get("limit", "20") or 20), 100))
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        lines = []
        try:
            async for msg in self.client.iter_messages(chat, search=query, limit=limit):
                sender = await msg.get_sender()
                name = self._format_sender_short(sender)
                text = getattr(msg, "raw_text", None) or getattr(msg, "text", "") or ""
                lines.append(f"#{msg.id} {name}: {text[:500]}")
        except Exception as exc:
            return f"Could not search messages: {exc}"
        return "\n".join(lines) or "No messages found"

    def _format_sender_short(self, sender: Any) -> str:
        if sender is None:
            return "Unknown"
        username = f"@{sender.username}" if getattr(sender, "username", None) else ""
        name = " ".join(
            p
            for p in (getattr(sender, "first_name", None), getattr(sender, "last_name", None))
            if p
        ) or getattr(sender, "title", None) or "Unknown"
        return f"{name} {username}".strip()

    async def _update_profile_tool(self, attrs_raw: str, body: str) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        first_name = attrs.get("first_name") or attrs.get("name")
        last_name = attrs.get("last_name")
        about = attrs.get("about") or attrs.get("bio") or body.strip() or None
        username = attrs.get("username")
        lines = []
        try:
            if first_name or last_name or about:
                await self.client(
                    UpdateProfileRequest(
                        first_name=first_name,
                        last_name=last_name,
                        about=about,
                    )
                )
                lines.append("profile updated")
            if username:
                await self.client(UpdateAccountUsernameRequest(username=username.lstrip("@")))
                lines.append(f"username set: @{username.lstrip('@')}")
        except Exception as exc:
            return f"Could not update profile: {exc}"
        return "\n".join(lines) or "Nothing to update"

    async def _set_profile_photo_tool(
        self, attrs_raw: str, source_event: Any | None
    ) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        data: bytes | None = None
        mime_type = "image/jpeg"
        url = attrs.get("url") or attrs.get("avatar_url") or attrs.get("photo_url")
        if url:
            fetched = await self._fetch_url_bytes(url)
            if fetched:
                data, mime_type = fetched
        elif source_event is not None and attrs.get("avatar_reply", "").lower() in {"1", "true", "yes"}:
            reply = await source_event.get_reply_message()
            if reply and getattr(reply, "media", None):
                data = await reply.download_media(file=bytes)
                file_obj = getattr(reply, "file", None)
                mime_type = getattr(file_obj, "mime_type", None) or "image/jpeg"
        if not data:
            return "No photo data found"
        if not mime_type.startswith("image/"):
            return "Profile photo must be an image"
        ext = mimetypes.guess_extension(mime_type) or ".jpg"
        buf = io.BytesIO(data)
        buf.name = f"profile{ext}"
        try:
            uploaded = await self.client.upload_file(buf)
            await self.client(UploadProfilePhotoRequest(file=uploaded))
        except Exception as exc:
            return f"Could not set profile photo: {exc}"
        return "profile photo updated"

    async def _join_chat_tool(self, attrs_raw: str, body: str) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        target = attrs.get("chat") or attrs.get("url") or body.strip()
        if not target:
            return "Join target is empty"
        target = target.strip()
        try:
            invite_match = re.search(r"(?:joinchat/|\+)([A-Za-z0-9_-]+)", target)
            if invite_match:
                result = await self.client(ImportChatInviteRequest(invite_match.group(1)))
                return f"joined by invite: {getattr(result, 'chats', [])}"
            entity = target.replace("https://t.me/", "").lstrip("@")
            result = await self.client(JoinChannelRequest(entity))
            return f"joined: {getattr(result, 'chats', [])}"
        except Exception as exc:
            return f"Could not join chat: {exc}"

    async def _message_id_from_attrs(
        self, attrs: dict[str, str], body: str, source_event: Any | None
    ) -> int | None:
        raw = attrs.get("id") or attrs.get("message_id") or body.strip()
        if raw and raw.lower() not in {"reply", "replied"}:
            try:
                return int(raw.split(",")[0].strip())
            except ValueError:
                return None
        if source_event is not None:
            reply = await source_event.get_reply_message()
            if reply:
                return getattr(reply, "id", None)
        return None

    async def _pin_message_tool(self, attrs_raw: str, body: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        msg_id = await self._message_id_from_attrs(attrs, body, source_event)
        if not msg_id:
            return "Message id is required or reply to a message"
        notify = attrs.get("notify", "false").lower() in {"1", "true", "yes"}
        try:
            await self.client.pin_message(chat, msg_id, notify=notify)
        except Exception as exc:
            return f"Could not pin message: {exc}"
        return f"Pinned message {msg_id} in {chat}"

    async def _delete_messages_tool(self, attrs_raw: str, body: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        raw_ids = attrs.get("ids") or attrs.get("id") or body.strip()
        ids: list[int] = []
        if raw_ids and raw_ids.lower() not in {"reply", "replied"}:
            for part in re.split(r"[\s,]+", raw_ids):
                if part.strip().isdigit():
                    ids.append(int(part.strip()))
        elif source_event is not None:
            reply = await source_event.get_reply_message()
            if reply:
                ids.append(reply.id)
        if not ids:
            return "Message ids are required or reply to a message"
        try:
            result = await self.client.delete_messages(chat, ids)
        except Exception as exc:
            return f"Could not delete messages: {exc}"
        return f"Delete requested for {len(ids)} message(s): {result}"

    async def _forward_message_tool(self, attrs_raw: str, body: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        src = await self._resolve_tool_chat(attrs.get("from") or attrs.get("src"), source_event)
        dst = await self._resolve_tool_chat(attrs.get("to") or attrs.get("dst") or body.strip(), source_event)
        msg_id = await self._message_id_from_attrs(attrs, "", source_event)
        if not msg_id:
            return "Message id is required or reply to a message"
        try:
            sent = await self.client.forward_messages(dst, msg_id, from_peer=src)
        except Exception as exc:
            return f"Could not forward message: {exc}"
        return f"Forwarded message {msg_id} to {dst}, new id={getattr(sent, 'id', None)}"

    async def _download_media_tool(self, attrs_raw: str, body: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        if source_event is None:
            return "No source event available"
        reply = await source_event.get_reply_message()
        if not reply or not getattr(reply, "media", None):
            return "Reply to a media message first"
        directory = Path(attrs.get("path") or body.strip() or "openagent_downloads")
        if not directory.is_absolute():
            directory = Path.cwd() / directory
        directory.mkdir(parents=True, exist_ok=True)
        try:
            path = await reply.download_media(file=str(directory))
        except Exception as exc:
            return f"Could not download media: {exc}"
        return f"Media downloaded: {path}"

    async def _send_file_tool(self, attrs_raw: str, body: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        path_raw = attrs.get("path") or attrs.get("file")
        if not path_raw:
            return "File path is required"
        path = Path(path_raw).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists() or not path.is_file():
            return f"File not found: {path}"
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        caption = body.strip() or attrs.get("caption") or None
        try:
            sent = await self.client.send_file(chat, str(path), caption=caption)
        except Exception as exc:
            return f"Could not send file: {exc}"
        return f"File sent to {chat}, id={getattr(sent, 'id', None)}"

    async def _mute_user_tool(self, attrs_raw: str, body: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        user = await self._resolve_tool_user(attrs.get("user"), source_event)
        minutes = max(1, int(attrs.get("minutes", "60") or 60))
        until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        try:
            await self.client.edit_permissions(chat, user, until_date=until, send_messages=False)
        except Exception as exc:
            return f"Could not mute user: {exc}"
        return f"Muted user for {minutes} minute(s). Reason: {body.strip() or 'not specified'}"

    async def _unmute_user_tool(self, attrs_raw: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        user = await self._resolve_tool_user(attrs.get("user"), source_event)
        try:
            await self.client.edit_permissions(chat, user, send_messages=True)
        except Exception as exc:
            return f"Could not unmute user: {exc}"
        return "User unmuted"

    async def _ban_user_tool(self, attrs_raw: str, body: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        user = await self._resolve_tool_user(attrs.get("user"), source_event)
        try:
            await self.client.edit_permissions(chat, user, view_messages=False)
        except Exception as exc:
            return f"Could not ban user: {exc}"
        return f"User banned. Reason: {body.strip() or 'not specified'}"

    async def _unban_user_tool(self, attrs_raw: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        user = await self._resolve_tool_user(attrs.get("user"), source_event)
        try:
            await self.client.edit_permissions(chat, user, view_messages=True, send_messages=True)
        except Exception as exc:
            return f"Could not unban user: {exc}"
        return "User unbanned"

    async def _kick_user_tool(self, attrs_raw: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        user = await self._resolve_tool_user(attrs.get("user"), source_event)
        try:
            await self.client.kick_participant(chat, user)
        except Exception as exc:
            return f"Could not kick user: {exc}"
        return "User kicked"

    async def _promote_user_tool(self, attrs_raw: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        user = await self._resolve_tool_user(attrs.get("user"), source_event)
        rank = attrs.get("rank") or "Admin"
        rights = ChatAdminRights(
            change_info=True,
            delete_messages=True,
            ban_users=True,
            invite_users=True,
            pin_messages=True,
            manage_call=True,
            manage_topics=True,
        )
        try:
            await self.client(EditAdminRequest(channel=chat, user_id=user, admin_rights=rights, rank=rank[:16]))
        except Exception as exc:
            return f"Could not promote user: {exc}"
        return f"User promoted with rank: {rank}"

    async def _demote_user_tool(self, attrs_raw: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        user = await self._resolve_tool_user(attrs.get("user"), source_event)
        rights = ChatAdminRights()
        try:
            await self.client(EditAdminRequest(channel=chat, user_id=user, admin_rights=rights, rank=""))
        except Exception as exc:
            return f"Could not demote user: {exc}"
        return "User demoted"

    async def _set_slowmode_tool(self, attrs_raw: str, body: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        seconds = int(attrs.get("seconds") or body.strip() or 0)
        seconds = max(0, min(seconds, 3600))
        try:
            await self.client(ToggleSlowModeRequest(channel=chat, seconds=seconds))
        except Exception as exc:
            return f"Could not set slowmode: {exc}"
        return f"Slowmode set to {seconds}s"

    async def _set_chat_title_tool(self, attrs_raw: str, body: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        title = (attrs.get("title") or body.strip())[:128]
        if not title:
            return "Title is empty"
        try:
            await self.client(EditTitleRequest(channel=chat, title=title))
        except Exception as exc:
            return f"Could not set chat title: {exc}"
        return f"Chat title set: {title}"

    async def _set_chat_about_tool(self, attrs_raw: str, body: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
        about = (attrs.get("about") or attrs.get("description") or body.strip())[:255]
        try:
            await self.client(EditChatAboutRequest(peer=chat, about=about))
        except Exception as exc:
            return f"Could not set chat about: {exc}"
        return "Chat description updated"

    async def _misc_tool(self, name: str, attrs_raw: str, body: str, source_event: Any | None) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        try:
            if name == "search_dialogs":
                query = (attrs.get("query") or body.strip()).lower()
                limit = max(1, min(int(attrs.get("limit", "20") or 20), 100))
                if not query:
                    return "query is required"
                lines = []
                async for dialog in self.client.iter_dialogs(limit=300):
                    entity = dialog.entity
                    username = getattr(entity, "username", None) or ""
                    title = getattr(dialog, "name", None) or getattr(entity, "title", None) or " ".join(
                        p
                        for p in (getattr(entity, "first_name", None), getattr(entity, "last_name", None))
                        if p
                    )
                    haystack = f"{title} {username}".lower()
                    if query in haystack:
                        lines.append(f"{title} @{username} [id={getattr(entity, 'id', None)}]".strip())
                    if len(lines) >= limit:
                        break
                return "\n".join(lines) or "No dialogs found"

            if name == "get_permissions":
                chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
                user = await self._resolve_tool_user(attrs.get("user"), source_event)
                perms = await self.client.get_permissions(chat, user)
                return "\n".join(
                    f"{key}: {value}"
                    for key, value in sorted(vars(perms).items())
                    if not key.startswith("_")
                )[:4000]

            if name == "get_common_chats":
                user = await self._resolve_tool_user(attrs.get("user") or body.strip(), source_event)
                limit = max(1, min(int(attrs.get("limit", "20") or 20), 100))
                chats = await self.client.get_common_chats(user, limit=limit)
                lines = []
                for chat in chats:
                    title = getattr(chat, "title", None) or getattr(chat, "first_name", None) or "Unknown"
                    username = f"@{chat.username}" if getattr(chat, "username", None) else ""
                    lines.append(f"{title} {username} [id={getattr(chat, 'id', None)}]".strip())
                return "\n".join(lines) or "No common chats found"

            if name == "get_profile_photos":
                user = await self._resolve_tool_user(attrs.get("user") or body.strip(), source_event)
                limit = max(1, min(int(attrs.get("limit", "3") or 3), 20))
                directory = Path(attrs.get("path") or "openagent_downloads")
                if not directory.is_absolute():
                    directory = Path.cwd() / directory
                directory.mkdir(parents=True, exist_ok=True)
                photos = await self.client.get_profile_photos(user, limit=limit)
                paths = []
                for idx, photo in enumerate(photos, 1):
                    path = await self.client.download_media(photo, file=str(directory / f"profile_photo_{idx}.jpg"))
                    paths.append(str(path))
                return "\n".join(paths) or "No profile photos found"

            if name == "schedule_message":
                chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
                at_raw = attrs.get("at") or attrs.get("time")
                if not at_raw:
                    return "at/time attribute is required"
                text = body.strip()
                if not text:
                    return "message text is empty"
                at = datetime.fromisoformat(at_raw.replace("Z", "+00:00"))
                if at.tzinfo is None:
                    at = at.astimezone()
                sent = await self.client.send_message(chat, text, schedule=at)
                return f"Message scheduled to {chat} at {at.isoformat()}, id={getattr(sent, 'id', None)}"

            if name == "get_me":
                return await self._format_full_profile(await self.client.get_me())

            if name == "get_entity":
                target = attrs.get("target") or attrs.get("user") or attrs.get("chat") or body.strip()
                if not target:
                    return "target is required"
                try:
                    entity = await self.client.get_entity(int(target))
                except ValueError:
                    entity = await self.client.get_entity(target)
                return await self._format_full_profile(entity)

            if name == "get_admins":
                chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
                lines = []
                async for user in self.client.iter_participants(chat, filter=ChannelParticipantsAdmins):
                    lines.append(self._format_sender_short(user) + f" [id={getattr(user, 'id', None)}]")
                return "\n".join(lines) or "No admins found"

            if name == "export_invite":
                chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
                invite = await self.client(ExportChatInviteRequest(peer=chat, title=attrs.get("title") or "OpenAgent"))
                return getattr(invite, "link", str(invite))

            if name == "mark_read":
                chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
                await self.client.send_read_acknowledge(chat)
                return "Marked as read"

            if name in {"archive_dialog", "unarchive_dialog"}:
                chat = await self._resolve_tool_chat(attrs.get("chat") or body.strip(), source_event)
                await self.client.edit_folder(chat, 1 if name == "archive_dialog" else 0)
                return "Dialog archived" if name == "archive_dialog" else "Dialog unarchived"

            if name == "leave_chat":
                chat = await self._resolve_tool_chat(attrs.get("chat") or body.strip(), source_event)
                await self.client.delete_dialog(chat)
                return f"Left/deleted dialog: {chat}"

            if name in {"block_user", "unblock_user", "delete_contact"}:
                user = await self._resolve_tool_user(attrs.get("user") or body.strip(), source_event)
                input_user = await self.client.get_input_entity(user)
                if name == "block_user":
                    await self.client(BlockRequest(input_user))
                    return "User blocked"
                if name == "unblock_user":
                    await self.client(UnblockRequest(input_user))
                    return "User unblocked"
                await self.client(DeleteContactsRequest([input_user]))
                return "Contact deleted"

            if name == "add_contact":
                user = await self._resolve_tool_user(attrs.get("user"), source_event)
                input_user = await self.client.get_input_entity(user)
                await self.client(
                    AddContactRequest(
                        id=input_user,
                        first_name=attrs.get("first_name") or attrs.get("name") or "Contact",
                        last_name=attrs.get("last_name") or "",
                        phone=attrs.get("phone") or "",
                    )
                )
                return "Contact added"

            if name == "save_draft":
                chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
                await self.client(SaveDraftRequest(peer=chat, message=body.strip()))
                return "Draft saved"

            if name in {"edit_message", "reply_message", "react_message", "get_message"}:
                chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
                msg_id = await self._message_id_from_attrs(attrs, "", source_event)
                if not msg_id:
                    return "message id is required or reply to a message"
                if name == "edit_message":
                    await self.client.edit_message(chat, msg_id, body.strip())
                    return "Message edited"
                if name == "reply_message":
                    sent = await self.client.send_message(chat, body.strip(), reply_to=msg_id)
                    return f"Reply sent, id={getattr(sent, 'id', None)}"
                if name == "react_message":
                    if not hasattr(self.client, "send_reaction"):
                        return "send_reaction is not available"
                    await self.client.send_reaction(chat, msg_id, reaction=(body.strip() or attrs.get("reaction") or "👍"))
                    return "Reaction sent"
                msg = await self.client.get_messages(chat, ids=msg_id)
                text = getattr(msg, "raw_text", None) or getattr(msg, "text", "") or ""
                return f"#{msg_id}: {text[:3000]}"

            if name == "typing":
                chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
                seconds = max(1, min(int(attrs.get("seconds", "3") or 3), 15))
                async with self.client.action(chat, "typing"):
                    await asyncio.sleep(seconds)
                return f"Typing action shown for {seconds}s"

            if name == "set_chat_username":
                chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
                username = (attrs.get("username") or body.strip()).lstrip("@")
                await self.client(UpdateUsernameRequest(channel=chat, username=username))
                return f"Chat username set: @{username}"

            if name == "set_chat_photo":
                chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
                result = await self._set_channel_avatar(chat, attrs, source_event)
                return result or "No photo data found"

            if name == "get_chat_photo":
                chat = await self._resolve_tool_chat(attrs.get("chat"), source_event)
                directory = Path(attrs.get("path") or "openagent_downloads")
                if not directory.is_absolute():
                    directory = Path.cwd() / directory
                directory.mkdir(parents=True, exist_ok=True)
                path = await self.client.download_profile_photo(chat, file=str(directory))
                return f"Chat photo downloaded: {path}"

        except Exception as exc:
            return f"{name} failed: {exc}"
        return f"Unknown tool: {name}"

    async def _show_agent_action(
        self,
        event: Any,
        title: str,
        value: str,
        log: list[str],
    ) -> None:
        safe_value = value if len(value) <= 1200 else value[:1200] + "..."
        log_text = "\n".join(log[-8:])
        if len(log_text) > 1800:
            log_text = log_text[-1800:]
        text = (
            f"<b>{html.escape(title)}</b>\n"
            f"<code>{html.escape(safe_value)}</code>\n\n"
            f"<blockquote expandable><b>Agent Log</b>\n{html.escape(log_text)}</blockquote>"
        )
        try:
            await self.edit(event, text, as_html=True)
        except Exception:
            await self.edit(event, html.escape(title), as_html=True)


    async def _ask_agent(
        self,
        prompt: str,
        status_event: Any | None = None,
        source_event: Any | None = None,
        attachments: list[dict[str, str]] | None = None,
        cancel_token: str | None = None,
        system_override: str | None = None,
    ) -> tuple[str, list[str]]:
        provider = self._provider()
        if provider == "ollama.cloud":
            raise RuntimeError(self.strings("disabled", provider=self.PROVIDER_LABELS[provider]))

        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(self.strings["no_key"])

        attachments = attachments or []
        if provider == "google":
            user_content = self._build_google_content(prompt, attachments)
        else:
            user_content = self._build_openai_content(prompt, attachments)

        chat_id = getattr(source_event, "chat_id", None) if source_event is not None else None
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_override or self._system_prompt()}
        ]
        tool_memory = self._tool_memory_prompt(chat_id)
        if tool_memory:
            messages.append({"role": "system", "content": tool_memory})
        messages.extend(self._history_for_chat(chat_id))
        messages.append({"role": "user", "content": user_content})

        agent_log: list[str] = []
        max_steps = 15  # Architectural limit for tool chaining in 0.5.0
        answer = ""

        for _ in range(max_steps):
            if cancel_token and cancel_token in self._cancelled_generations:
                raise RuntimeError("Generation cancelled")
                
            if provider in ("openai", "other"):
                answer = await self._ask_openai_compatible(provider, messages, api_key)
            elif provider == "google":
                answer = await self._ask_google(messages, api_key)
            else:
                raise RuntimeError(self.strings("bad_provider", providers=", ".join(self.PROVIDERS)))

            match = self.TOOL_CALL_RE.search(answer or "")
            if not match:
                return (answer or "").strip(), agent_log

            # Extract tool name and content
            # TOOL_CALL_RE = re.compile(r"<([a-z0-9._]+)([^>]*)>(.*?)</>|<([a-z0-9._]+)([^>]*)/?>")
            if match.group(1): # Block format <tool>...</tool>
                tool_name, attrs_raw, body = match.group(1), match.group(2), match.group(3)
            else: # Self-closing format <tool/>
                tool_name, attrs_raw, body = match.group(4), match.group(5), ""

            output = await self._dispatch_tool(tool_name, attrs_raw, body, source_event, status_event, agent_log)
            self._remember_tool_output(chat_id, tool_name, output)
            
            messages.append({"role": "assistant", "content": answer})
            messages.append({"role": "user", "content": f"Tool <{tool_name}> output:\n{output}"})
        # Force one final pass without tool calls if tool-chain limit was reached.
        messages.append(
            {
                "role": "user",
                "content": (
                    "Stop using tools. Give the final user-facing answer now, in plain text only. "
                    "Do not output XML tags or tool calls."
                ),
            }
        )
        if provider in ("openai", "other"):
            answer = await self._ask_openai_compatible(provider, messages, api_key)
        elif provider == "google":
            answer = await self._ask_google(messages, api_key)
        else:
            raise RuntimeError(self.strings("bad_provider", providers=", ".join(self.PROVIDERS)))
        clean = (answer or "").strip()
        if clean:
            return clean, agent_log
        return "Инструменты выполнены, но модель не сформировала финальный текст.", agent_log

    def _agent_log_html(self, log: list[str]) -> str:
        if not log:
            return ""
        return (
            "\n\n<blockquote expandable><b>Agent Log</b>\n"
            f"{html.escape(chr(10).join(log))}</blockquote>"
        )

    def _uses_completion_tokens(self, provider: str) -> bool:
        model = self._model(provider).lower()
        return provider == "openai" and (
            model.startswith("gpt-5")
            or model.startswith("o1")
            or model.startswith("o3")
            or model.startswith("o4")
        )

    def _set_token_usage(self, usage: dict[str, Any] | None, provider: str) -> None:
        usage = usage or {}
        if provider == "google":
            input_tokens = int(usage.get("promptTokenCount") or 0)
            output_tokens = int(usage.get("candidatesTokenCount") or 0)
            total_tokens = int(usage.get("totalTokenCount") or input_tokens + output_tokens)
        else:
            input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            output_tokens = int(
                usage.get("completion_tokens")
                or usage.get("output_tokens")
                or 0
            )
            total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
        self._last_token_usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    async def _ask_openai_compatible(
        self,
        provider: str,
        messages: list[dict[str, str]],
        api_key: str,
    ) -> str:
        base_url = self._base_url(provider)
        if not base_url:
            raise RuntimeError("custom_base_url is not configured")
        url = f"{base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self._model(provider),
            "messages": messages,
            "temperature": float(self.config["temperature"]),
        }
        if self._uses_completion_tokens(provider):
            payload["max_completion_tokens"] = int(self.config["max_tokens"])
        else:
            payload["max_tokens"] = int(self.config["max_tokens"])

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            data = await self._post_json(url, payload, headers=headers)
        except RuntimeError as exc:
            error_text = str(exc).lower()
            if "max_completion_tokens" in error_text and "unsupported" in error_text:
                value = payload.pop("max_completion_tokens", None)
                if value is not None:
                    payload["max_tokens"] = value
                    data = await self._post_json(url, payload, headers=headers)
                else:
                    raise
            elif "max_tokens" in error_text and "unsupported" in error_text:
                value = payload.pop("max_tokens", None)
                if value is not None:
                    payload["max_completion_tokens"] = value
                    data = await self._post_json(url, payload, headers=headers)
                else:
                    raise
            elif "temperature" in error_text and "unsupported" in error_text:
                payload.pop("temperature", None)
                data = await self._post_json(url, payload, headers=headers)
            else:
                raise
        try:
            self._set_token_usage(data.get("usage"), provider)
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected {provider} response: {data}") from exc

    async def _ask_google(self, messages: list[dict[str, str]], api_key: str) -> str:
        model = self._model("google")
        url = f"{self._base_url('google')}/models/{model}:generateContent?key={api_key}"
        system_text = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                continue
            role = "model" if msg["role"] == "assistant" else "user"
            content = msg["content"]
            parts = self._build_google_parts(content)
            contents.append({"role": role, "parts": parts})
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": float(self.config["temperature"]),
                "maxOutputTokens": int(self.config["max_tokens"]),
            },
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        data = await self._post_json(url, payload)
        try:
            self._set_token_usage(data.get("usageMetadata"), "google")
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(str(part.get("text", "")) for part in parts).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected google response: {data}") from exc

    async def _post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        timeout = aiohttp.ClientTimeout(total=int(self.config["timeout"]))
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise RuntimeError(f"HTTP {resp.status}: {text[:800]}")
                try:
                    return await resp.json()
                except Exception as exc:
                    raise RuntimeError(f"Invalid JSON response: {text[:800]}") from exc

    def _format_inline_markdown(self, text: str) -> str:
        text = html.escape(text)
        text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
        return text

    def _format_agent_markdown(self, text: str) -> str:
        parts: list[str] = []
        pos = 0
        pattern = re.compile(r"```([a-zA-Z0-9_+-]*)\n?(.*?)```", re.DOTALL)
        for match in pattern.finditer(text or ""):
            parts.append(self._format_inline_markdown(text[pos : match.start()]))
            lang = match.group(1).strip()
            code = html.escape(match.group(2).strip("\n"))
            if lang:
                parts.append(f'<pre language="{html.escape(lang)}">{code}</pre>')
            else:
                parts.append(f"<pre>{code}</pre>")
            pos = match.end()
        parts.append(self._format_inline_markdown((text or "")[pos:]))
        return "".join(parts)

    def _sanitize_answer(self, text: str) -> str:
        patterns = [
            r"\s*Use the above message and context to generate a prompt and call the task tool with subagent:\s*\w+\s*",
            r"\s*call the task tool with subagent:\s*\w+\s*",
            r"<(?:terminal|web|mcub|message|file|dialog|chat|moderation|profile|contacts|creation|skills|context|utility|code)\.[^>]+>",
            r"</(?:terminal|web|mcub|message|file|dialog|chat|moderation|profile|contacts|creation|skills|context|utility|code)\.[^>]+>",
        ]
        for pattern in patterns:
            text = re.sub(pattern, " ", text, flags=re.I)
        return text.strip()

    async def _send_answer_file(
        self,
        event: Any,
        title: str,
        prompt: str,
        answer: str,
        agent_log: list[str],
        buttons: list[list[Any]] | None = None,
    ) -> None:
        content = f"{title}\n\nЗапрос:\n{prompt}\n\nОтвет:\n{answer}"
        if agent_log:
            content += "\n\nAgent Log:\n" + "\n".join(agent_log)
        buf = io.BytesIO(content.encode("utf-8"))
        buf.name = "openagent_answer.txt"
        caption = f"{title}\n\n<b>Ответ слишком длинный, отправляю файлом.</b>"
        chat_id = getattr(event, "chat_id", None)
        if chat_id is not None:
            try:
                await self.client.send_file(
                    chat_id,
                    buf,
                    caption=caption,
                    parse_mode="html",
                )
            except Exception:
                await self.client.send_file(chat_id, buf, caption="OpenAgent answer")
            if buttons:
                with contextlib.suppress(Exception):
                    await self.inline(
                        chat_id,
                        "<b>OpenAgent controls</b>",
                        buttons=buttons,
                        ttl=900,
                        parse_mode="html",
                    )
        else:
            if hasattr(event, "reply"):
                await self.reply(event, caption, file=buf, as_html=True)

    async def _reply_text(
        self,
        event: Any,
        text: str,
        *,
        title: str = "OpenAgent",
        prompt: str = "",
        agent_log: list[str] | None = None,
        buttons: list[list[Any]] | None = None,
        edit_current: bool = False,
    ) -> None:
        text = self._sanitize_answer(text or "")
        formatted = self._format_agent_markdown(text)
        formatted_prompt = self._format_agent_markdown(prompt or "")
        request_label = self._request_label()
        response_label = self._response_label()
        agent_log_html = self._agent_log_html(agent_log or [])
        if len(formatted) + len(formatted_prompt) + len(agent_log_html) > 3500:
            await self._send_answer_file(event, title, prompt, text or "", agent_log or [], buttons)
            return
        chunks = [formatted[i : i + 3500] for i in range(0, len(formatted), 3500)] or [""]
        for index, chunk in enumerate(chunks):
            header = title if index == 0 else f"{title} <i>continued</i>"
            if index == 0:
                body = (
                    f"{header}\n\n"
                    f"{request_label}\n<blockquote expandable>{formatted_prompt}</blockquote>\n\n"
                    f"{response_label}\n<blockquote expandable>{chunk}</blockquote>"
                )
            else:
                body = f"{header}\n\n{response_label}\n<blockquote expandable>{chunk}</blockquote>"
            if index == len(chunks) - 1:
                body += self._agent_log_html(agent_log or [])
            chat_id = getattr(event, "chat_id", None)
            if edit_current and hasattr(event, "edit"):
                try:
                    await event.edit(
                        body,
                        parse_mode="html",
                        buttons=buttons if index == len(chunks) - 1 else None,
                    )
                    continue
                except Exception:
                    pass
            if chat_id is not None:
                if buttons and index == len(chunks) - 1:
                    try:
                        await self.inline(
                            chat_id,
                            body,
                            buttons=buttons,
                            ttl=900,
                            parse_mode="html",
                        )
                    except Exception:
                        await self.client.send_message(chat_id, body, parse_mode="html")
                else:
                    await self.client.send_message(
                        chat_id,
                        body,
                        parse_mode="html",
                    )
            else:
                if hasattr(event, "reply"):
                    await self.reply(event, body, as_html=True)

    async def _cancel_generation(self, event: Any, token: str) -> None:
        self._cancelled_generations.add(token)
        try:
            await event.answer("Отменено", alert=False)
        except Exception:
            pass

    async def _clear_context(self, event: Any, chat_id: int | None) -> None:
        if chat_id is not None:
            self._chat_history.pop(int(chat_id), None)
        try:
            await event.answer("Контекст очищен", alert=True)
        except Exception:
            pass

    def _direct_button(self, text: str, kind: str, payload: dict[str, Any]) -> Any:
        if kind == "cancel":
            return self.Button.inline(text, self._cancel_generation, args=(payload.get("token", ""),), style="danger")
        if kind == "clear":
            return self.Button.inline(text, self._clear_context, args=(payload.get("chat_id"),), style="danger")
        if kind == "regen":
            return self.Button.inline(text, self._regenerate_response, args=(payload.get("token", ""),), style="primary")
        return self.Button.inline(text, self._clear_context, args=(None,), style="danger")

    def _final_buttons(
        self,
        chat_id: int | None,
        prompt: str,
        full_prompt: str,
        attachments: list[dict[str, str]],
    ) -> list[list[Any]]:
        regen_token = str(uuid.uuid4())
        self._regen_payloads[regen_token] = {
            "chat_id": chat_id,
            "prompt": prompt,
            "full_prompt": full_prompt,
            "attachments": attachments,
            "created_at": time.time(),
        }
        if len(self._regen_payloads) > 50:
            stale = sorted(
                self._regen_payloads,
                key=lambda key: self._regen_payloads[key].get("created_at", 0),
            )[:-50]
            for key in stale:
                self._regen_payloads.pop(key, None)
        clear_button = self._direct_button("🧹 Очистить", "clear", {"chat_id": chat_id})
        regen_button = self._direct_button("🔃 Регенерировать", "regen", {"token": regen_token})
        return [[clear_button, regen_button]]

    async def _regenerate_response(self, event: Any, token: str) -> None:
        payload = self._regen_payloads.get(token)
        if not payload:
            try:
                await event.answer("Запрос устарел", alert=True)
            except Exception:
                pass
            return

        try:
            await event.answer("Регенерирую...", alert=False)
        except Exception:
            pass

        cancel_token = str(uuid.uuid4())
        cancel_button = self._direct_button("Отмена", "cancel", {"token": cancel_token})
        try:
            edited = await event.edit(
                self._thinking_text(),
                buttons=[[cancel_button]],
                parse_mode="html",
            )
            loading = edited if edited and not isinstance(edited, bool) else event
        except Exception:
            loading = event

        started = time.monotonic()
        try:
            answer, agent_log = await self._ask_agent(
                payload["full_prompt"],
                status_event=loading or event,
                source_event=event,
                attachments=payload.get("attachments") or [],
                cancel_token=cancel_token,
            )
            elapsed = time.monotonic() - started
            self._remember_context(payload.get("chat_id"), payload["full_prompt"], answer)
            await self._reply_text(
                loading or event,
                answer,
                title=self._response_title(elapsed),
                prompt=payload["prompt"],
                agent_log=agent_log,
                buttons=self._final_buttons(
                    payload.get("chat_id"),
                    payload["prompt"],
                    payload["full_prompt"],
                    payload.get("attachments") or [],
                ),
                edit_current=True,
            )
            self._cancelled_generations.discard(cancel_token)
            try:
                await (loading or event).delete()
            except Exception:
                pass
        except Exception as exc:
            self._cancelled_generations.discard(cancel_token)
            await self.kernel.handle_error(exc, source="OpenAgent:regenerate", event=event)
            try:
                await event.edit(
                    html.escape(self.strings("error", error=str(exc))),
                    parse_mode="html",
                )
            except Exception:
                pass

    @command("oa", alias=["agent"], doc_ru="<запрос> спросить ИИ агента", doc_en="<prompt> ask AI agent")
    async def cmd_oa(self, event: events.NewMessage.Event) -> None:
        prompt = self._args_raw(event)
        reply_context, attachments = await self._reply_context(event)
        if not prompt and reply_context:
            prompt = "Проанализируй вложение/сообщение из reply."
        if not prompt:
            await self.edit(event, self.strings["need_text"])
            return

        full_prompt = prompt
        if reply_context:
            full_prompt += f"\n\nReply context:\n{reply_context}"

        cancel_token = str(uuid.uuid4())
        cancel_button = self._direct_button("Отмена", "cancel", {"token": cancel_token})
        try:
            edited = await event.edit(
                self._thinking_text(),
                buttons=[[cancel_button]],
                parse_mode="html",
            )
            loading = edited if edited and not isinstance(edited, bool) else event
        except Exception:
            loading = await self.edit(event, self._thinking_text())
        started = time.monotonic()
        try:
            answer, agent_log = await self._ask_agent(
                full_prompt,
                status_event=loading or event,
                source_event=event,
                attachments=attachments,
                cancel_token=cancel_token,
            )
            self._last_request_at = time.time()
            elapsed = time.monotonic() - started
            self._remember_context(getattr(event, "chat_id", None), full_prompt, answer)
            await self._reply_text(
                loading or event,
                answer,
                title=self._response_title(elapsed),
                prompt=prompt,
                agent_log=agent_log,
                buttons=self._final_buttons(
                    getattr(event, "chat_id", None),
                    prompt,
                    full_prompt,
                    attachments,
                ),
            )
            self._cancelled_generations.discard(cancel_token)
            try:
                await (loading or event).delete()
            except Exception:
                pass
        except Exception as exc:
            self._cancelled_generations.discard(cancel_token)
            await self.kernel.handle_error(exc, source="OpenAgent", event=event)
            await self.edit(
                loading or event,
                html.escape(self.strings("error", error=str(exc))),
                as_html=True,
            )

    @command("code", doc_ru="<запрос> сгенерировать код файлом", doc_en="<prompt> generate code file")
    async def cmd_code(self, event: events.NewMessage.Event) -> None:
        prompt = self._args_raw(event)
        if not prompt:
            await self.edit(event, "Usage: .code <request>")
            return

        try:
            loading = await event.edit("<b>🧬 Пишу код...</b>", parse_mode="html")
        except Exception:
            loading = await self.edit(event, "<b>🧬 Пишу код...</b>", as_html=True)

        try:
            docs = await self._fetch_mcub_docs()
            system = (
                "You are a senior software engineer and MCUB module developer. "
                "Generate exactly one complete source file for the user's request. "
                "If the request is for a MCUB module, use the MCUB documentation below and produce production-ready MCUB code. "
                "Choose the best filename and extension yourself. "
                "Return ONLY this exact wrapper and raw code inside it, with no explanations, no Markdown fences, no comments outside code:\n"
                "<file name=\"chosen_filename.ext\">\n...code...\n</file>\n\n"
                f"MCUB documentation:\n{docs}"
            )
            answer, _agent_log = await self._ask_agent(
                prompt,
                status_event=loading or event,
                source_event=None,
                system_override=system,
            )
            filename, code = self._extract_generated_file(answer)
            if not code:
                raise RuntimeError("model returned empty code")
            buf = io.BytesIO(code.encode("utf-8"))
            buf.name = filename
            await self.client.send_file(
                event.chat_id,
                buf,
                caption=f"<b>🧬 Code:</b> <code>{html.escape(filename)}</code>",
                parse_mode="html",
                reply_to=getattr(event, "id", None),
            )
            with contextlib.suppress(Exception):
                await (loading or event).delete()
        except Exception as exc:
            await self.kernel.handle_error(exc, source="OpenAgent:code", event=event)
            await self.edit(
                loading or event,
                html.escape(self.strings("error", error=str(exc))),
                as_html=True,
            )

    @command("skills", doc_ru="список скиллов OpenAgent", doc_en="list OpenAgent skills")
    async def cmd_skills(self, event: events.NewMessage.Event) -> None:
        skills = self._list_skills()
        if not skills:
            await self.edit(event, "No OpenAgent skills installed")
            return
        lines = []
        for path in skills:
            try:
                first_line = path.read_text(encoding="utf-8").splitlines()[0]
            except Exception:
                first_line = ""
            title = first_line.lstrip("# ").strip() if first_line.startswith("#") else path.stem
            lines.append(f"- {path.stem}: {title}")
        await self.edit(event, "<pre>" + html.escape("\n".join(lines)) + "</pre>", as_html=True)

    @command("sendss", doc_ru="<name> отправить .md скилл", doc_en="<name> send skill .md")
    async def cmd_sendss(self, event: events.NewMessage.Event) -> None:
        name = self._args_raw(event)
        if not name:
            await self.edit(event, "Usage: .sendss <skill_name>")
            return
        path = self._skill_path(name)
        if not path.exists():
            await self.edit(event, "Skill not found")
            return
        await self.client.send_file(
            event.chat_id,
            str(path),
            caption=f"<b>Skill:</b> <code>{html.escape(path.stem)}</code>",
            parse_mode="html",
        )
        try:
            await event.delete()
        except Exception:
            pass

    @command("imss", doc_ru="[name] импортировать .md скилл из reply", doc_en="[name] import .md skill from reply")
    async def cmd_imss(self, event: events.NewMessage.Event) -> None:
        reply = await event.get_reply_message()
        if not reply:
            await self.edit(event, "Reply to a .md file or markdown message")
            return

        name = self._args_raw(event)
        file_name = getattr(getattr(reply, "file", None), "name", None) or ""
        content = ""
        try:
            data = await reply.download_media(file=bytes)
            if data:
                content = data.decode("utf-8", errors="replace")
        except Exception:
            content = ""

        if not content:
            content = getattr(reply, "raw_text", None) or getattr(reply, "text", "") or ""
        if not content.strip():
            await self.edit(event, "Skill content is empty")
            return

        if not name:
            if file_name.lower().endswith(".md"):
                name = Path(file_name).stem
            else:
                match = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
                name = match.group(1).strip() if match else "skill"

        saved_name = await self._save_skill(name, content)
        await self.edit(event, f"Skill imported: <code>{html.escape(saved_name)}</code>", as_html=True)

    @command("delss", doc_ru="<name> удалить скилл", doc_en="<name> delete skill")
    async def cmd_delss(self, event: events.NewMessage.Event) -> None:
        name = self._args_raw(event)
        if not name:
            await self.edit(event, "Usage: .delss <skill_name>")
            return
        path = self._skill_path(name)
        if not path.exists():
            await self.edit(event, "Skill not found")
            return
        path.unlink()
        await self.edit(event, f"Skill deleted: <code>{html.escape(path.stem)}</code>", as_html=True)


    def _tool_attr_or_body(self, attrs_raw: str, body: str, *keys: str) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        for key in keys:
            value = attrs.get(key)
            if value:
                return value.strip()
        return (body or "").strip()

    async def _terminal_registry_tool(self, tool_name: str, attrs_raw: str, body: str) -> str:
        """Handle structured terminal.* aliases advertised to the model."""
        attrs = self._parse_xml_attrs(attrs_raw)
        if tool_name == "terminal.git_status":
            return await self._run_terminal("git status --short")
        if tool_name == "terminal.list_files":
            path = attrs.get("path") or body.strip() or "."
            return await self._run_terminal(f"python - <<'PY'\nfrom pathlib import Path\np=Path({path!r})\nprint('\\n'.join(sorted(x.name + ('/' if x.is_dir() else '') for x in p.iterdir())))\nPY")
        if tool_name == "terminal.read_file":
            path = attrs.get("path") or attrs.get("file") or body.strip()
            if not path:
                return "path is required"
            return await self._run_terminal(f"python - <<'PY'\nfrom pathlib import Path\np=Path({path!r})\nprint(p.read_text(encoding='utf-8', errors='replace')[:12000])\nPY")
        if tool_name == "terminal.inspect":
            command = body.strip() or attrs.get("command") or attrs.get("cmd") or "pwd"
            return await self._run_terminal(command)
        return await self._run_terminal(body.strip())

    async def _file_read_text_tool(self, attrs_raw: str, body: str) -> str:
        path_raw = self._tool_attr_or_body(attrs_raw, body, "path", "file", "name")
        if not path_raw:
            return "File path is required"
        path = Path(path_raw).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        try:
            if not path.is_file():
                return f"File not found: {path}"
            return path.read_text(encoding="utf-8", errors="replace")[:12000]
        except Exception as exc:
            return f"Could not read file: {exc}"

    async def _skills_registry_tool(self, tool_name: str, attrs_raw: str, body: str) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        if tool_name == "skills.list":
            skills = self._list_skills()
            return "\n".join(path.stem for path in skills) or "No OpenAgent skills installed"
        if tool_name in {"skills.read", "skills.export_md"}:
            name = attrs.get("name") or body.strip()
            if not name:
                return "skill name is required"
            path = self._skill_path(name)
            if not path.exists():
                return "Skill not found"
            return path.read_text(encoding="utf-8", errors="replace")[:12000]
        if tool_name in {"skills.save_from_ai", "skills.import_md", "skill.save", "skill"}:
            name = attrs.get("name") or attrs.get("title") or "skill"
            if not body.strip():
                return "skill content is empty"
            saved = await self._save_skill(name, body)
            return f"Skill saved: {saved}"
        return f"Unknown skills tool: {tool_name}"

    async def _context_registry_tool(self, tool_name: str, attrs_raw: str, body: str, source_event: Any | None) -> str:
        chat_id = getattr(source_event, "chat_id", None) if source_event is not None else None
        if tool_name == "context.clear":
            if chat_id is not None:
                self._chat_history.pop(int(chat_id), None)
                self._tool_memory.pop(int(chat_id), None)
            return "Context cleared"
        if tool_name == "context.remember":
            if chat_id is None:
                return "No chat context available"
            self._remember_context(chat_id, "Memory note", body.strip())
            return "Remembered in current chat context"
        if tool_name in {"context.reply_context", "context.media_context"} and source_event is not None:
            reply_context, _attachments = await self._reply_context(source_event)
            return reply_context or "No reply/media context available"
        if tool_name == "context.regenerate":
            return "Use the regenerate button under the last OpenAgent response"
        return f"Unknown context tool: {tool_name}"

    async def _utility_registry_tool(self, tool_name: str, attrs_raw: str, body: str) -> str:
        if tool_name == "utility.placeholders":
            return self._format_placeholders()
        if tool_name == "utility.random_template":
            return self._thinking_text()
        if tool_name == "utility.token_usage":
            usage = self._last_token_usage
            return "\n".join(f"{key}: {value}" for key, value in usage.items())
        if tool_name == "utility.agent_log":
            return "Agent log is shown under the final answer when tools are used"
        if tool_name == "utility.error_file":
            return "Errors are reported through the MCUB kernel error handler"
        return f"Unknown utility tool: {tool_name}"


    def _get_tool_map(self) -> dict[str, str]:
        """Unified mapping of tool tags to internal methods."""
        return {
            "terminal": "_run_terminal",
            "terminal.run": "_run_terminal",
            "terminal.inspect": "_terminal_registry_tool",
            "terminal.list_files": "_terminal_registry_tool",
            "terminal.read_file": "_terminal_registry_tool",
            "terminal.git_status": "_terminal_registry_tool",
            "web_search": "_web_search",
            "web.search": "_web_search",
            "web.fetch_url": "_web_search",
            "web.read_html": "_web_search",
            "web.extract_links": "_web_search",
            "web.summarize_page": "_web_search",
            "mcub": "_run_mcub_command",
            "mcub.command": "_run_mcub_command",
            "mcub.config": "_run_mcub_command",
            "mcub.modules": "_run_mcub_command",
            "mcub.install": "_run_mcub_command",
            "mcub.reload": "_run_mcub_command",
            "send_message": "_send_userbot_message",
            "message.send": "_send_userbot_message",
            "message.send_current": "_send_userbot_message",
            "message.send_target": "_send_userbot_message",
            "dialogs": "_dialogs_tool",
            "dialog.list": "_dialogs_tool",
            "dialog.list_private": "_dialogs_tool",
            "dialog.list_groups": "_dialogs_tool",
            "dialog.list_all": "_dialogs_tool",
            "skill": "_save_skill",
            "skill.save": "_save_skill",
            "skills.list": "_skills_registry_tool",
            "skills.read": "_skills_registry_tool",
            "skills.import_md": "_skills_registry_tool",
            "skills.export_md": "_skills_registry_tool",
            "skills.save_from_ai": "_skills_registry_tool",
            "chat": "_chat_tool",
            "chat.info": "_chat_tool",
            "chat.participants": "_chat_tool",
            "chat.admins": "_misc_tool",
            "moderation.get_admins": "_misc_tool",
            "chat.permissions": "_misc_tool",
            "chat.common_with_user": "_misc_tool",
            "profile": "_profile_tool",
            "profile.get": "_profile_tool",
            "profile.get_full": "_profile_tool",
            "profile.get_me": "_misc_tool",
            "profile.get_photos": "_misc_tool",
            "profile.common_chats": "_misc_tool",
            "profile.set_photo": "_set_profile_photo_tool",
            "set_profile_photo": "_set_profile_photo_tool",
            "create_channel": "_create_channel_or_group",
            "creation.channel": "_create_channel_or_group",
            "create_group": "_create_channel_or_group",
            "creation.group": "_create_channel_or_group",
            "create_bot": "_create_bot_via_botfather",
            "creation.bot": "_create_bot_via_botfather",
            "history": "_history_tool",
            "message.history": "_history_tool",
            "search_messages": "_search_messages_tool",
            "message.search": "_search_messages_tool",
            "update_profile": "_update_profile_tool",
            "profile.update": "_update_profile_tool",
            "profile.update_name": "_update_profile_tool",
            "profile.update_bio": "_update_profile_tool",
            "profile.update_username": "_update_profile_tool",
            "join_chat": "_join_chat_tool",
            "pin_message": "_pin_message_tool",
            "message.pin": "_pin_message_tool",
            "moderation.pin": "_pin_message_tool",
            "delete_messages": "_delete_messages_tool",
            "message.delete": "_delete_messages_tool",
            "moderation.delete_messages": "_delete_messages_tool",
            "forward_message": "_forward_message_tool",
            "message.forward": "_forward_message_tool",
            "download_media": "_download_media_tool",
            "file.download": "_download_media_tool",
            "file.download_media": "_download_media_tool",
            "send_file": "_send_file_tool",
            "file.send": "_send_file_tool",
            "file.read_text": "_file_read_text_tool",
            "mute_user": "_mute_user_tool",
            "chat.mute": "_mute_user_tool",
            "moderation.mute": "_mute_user_tool",
            "unmute_user": "_unmute_user_tool",
            "chat.unmute": "_unmute_user_tool",
            "moderation.unmute": "_unmute_user_tool",
            "ban_user": "_ban_user_tool",
            "chat.ban": "_ban_user_tool",
            "moderation.ban": "_ban_user_tool",
            "unban_user": "_unban_user_tool",
            "chat.unban": "_unban_user_tool",
            "moderation.unban": "_unban_user_tool",
            "kick_user": "_kick_user_tool",
            "chat.kick": "_kick_user_tool",
            "moderation.kick": "_kick_user_tool",
            "promote_user": "_promote_user_tool",
            "chat.promote": "_promote_user_tool",
            "moderation.promote": "_promote_user_tool",
            "demote_user": "_demote_user_tool",
            "chat.demote": "_demote_user_tool",
            "moderation.demote": "_demote_user_tool",
            "set_slowmode": "_set_slowmode_tool",
            "chat.slowmode": "_set_slowmode_tool",
            "set_chat_title": "_set_chat_title_tool",
            "chat.set_title": "_set_chat_title_tool",
            "set_chat_about": "_set_chat_about_tool",
            "chat.set_about": "_set_chat_about_tool",
            "dialog.search": "_misc_tool",
            "dialog.archive": "_misc_tool",
            "dialog.unarchive": "_misc_tool",
            "dialog.leave": "_misc_tool",
            "dialog.export_invite": "_misc_tool",
            "dialog.get_photo": "_misc_tool",
            "dialog.set_photo": "_misc_tool",
            "chat.set_username": "_misc_tool",
            "chat.invite_link": "_misc_tool",
            "message.edit": "_misc_tool",
            "message.reply": "_misc_tool",
            "message.react": "_misc_tool",
            "message.get": "_misc_tool",
            "message.mark_read": "_misc_tool",
            "message.typing": "_misc_tool",
            "message.schedule": "_misc_tool",
            "message.draft": "_misc_tool",
            "contacts.add": "_misc_tool",
            "contacts.delete": "_misc_tool",
            "contacts.block": "_misc_tool",
            "contacts.unblock": "_misc_tool",
            "contacts.entity": "_misc_tool",
            "profile.download_photo": "_misc_tool",
            "context.remember": "_context_registry_tool",
            "context.clear": "_context_registry_tool",
            "context.regenerate": "_context_registry_tool",
            "context.reply_context": "_context_registry_tool",
            "context.media_context": "_context_registry_tool",
            "code.read_docs": "_fetch_mcub_docs",
            "utility.token_usage": "_utility_registry_tool",
            "utility.placeholders": "_utility_registry_tool",
            "utility.random_template": "_utility_registry_tool",
            "utility.agent_log": "_utility_registry_tool",
            "utility.error_file": "_utility_registry_tool",
        }

    async def _dispatch_tool(self, name: str, attrs_raw: str, body: str, source_event: Any, status_event: Any, agent_log: list[str]) -> str:
        name = name.lower().strip()
        tmap = self._get_tool_map()
        misc_aliases = {
            "chat.admins": "get_admins",
            "moderation.get_admins": "get_admins",
            "chat.permissions": "get_permissions",
            "chat.common_with_user": "get_common_chats",
            "profile.get_me": "get_me",
            "profile.get_photos": "get_profile_photos",
            "profile.common_chats": "get_common_chats",
            "dialog.search": "search_dialogs",
            "dialog.archive": "archive_dialog",
            "dialog.unarchive": "unarchive_dialog",
            "dialog.leave": "leave_chat",
            "dialog.export_invite": "export_invite",
            "dialog.get_photo": "get_chat_photo",
            "dialog.set_photo": "set_chat_photo",
            "chat.set_username": "set_chat_username",
            "chat.invite_link": "export_invite",
            "message.edit": "edit_message",
            "message.reply": "reply_message",
            "message.react": "react_message",
            "message.get": "get_message",
            "message.mark_read": "mark_read",
            "message.typing": "typing",
            "message.schedule": "schedule_message",
            "message.draft": "save_draft",
            "contacts.add": "add_contact",
            "contacts.delete": "delete_contact",
            "contacts.block": "block_user",
            "contacts.unblock": "unblock_user",
            "contacts.entity": "get_entity",
            "profile.download_photo": "get_profile_photos",
        }
        
        # 1. Direct match or alias
        method_name = tmap.get(name)
        
        # 2. Misc tool check (handles 50+ tools)
        misc_tools = {
            "get_me", "get_entity", "get_admins", "export_invite", "mark_read",
            "archive_dialog", "unarchive_dialog", "leave_chat", "block_user", 
            "unblock_user", "add_contact", "delete_contact", "save_draft", 
            "edit_message", "reply_message", "react_message", "typing", 
            "get_message", "set_chat_username", "set_chat_photo", "get_chat_photo",
            "search_dialogs", "get_permissions", "get_common_chats", 
            "get_profile_photos", "schedule_message", "blocked_users"
        }
        
        handler_method = None
        is_misc = False
        
        if method_name:
            handler_method = getattr(self, method_name, None)
            is_misc = method_name == "_misc_tool"
        elif name in misc_tools:
            handler_method = self._misc_tool
            is_misc = True
            
        if not handler_method:
            return f"Error: Tool <{name}> not found in registry."

        agent_log.append(name)
        if status_event:
            await self._show_agent_action(status_event, f"Executing {name}...", attrs_raw or body, agent_log)
            
        try:
            # Normalize arguments based on method signature
            import inspect
            sig = inspect.signature(handler_method)
            params = sig.parameters
            
            kwargs = {}
            if is_misc:
                return await handler_method(misc_aliases.get(name, name), attrs_raw, body, source_event)
            
            if "tool_name" in params: kwargs["tool_name"] = name
            if "attrs_raw" in params: kwargs["attrs_raw"] = attrs_raw
            if "body" in params: kwargs["body"] = body
            if "source_event" in params: kwargs["source_event"] = source_event
            if "kind" in params:
                kwargs["kind"] = "group" if name.endswith("group") else "channel"
            if "command" in params: kwargs["command"] = body.strip() # for _run_terminal
            if "query" in params: kwargs["query"] = body.strip() or attrs_raw # fallback
            if "mode" in params:
                if name.endswith("list_groups"):
                    kwargs["mode"] = "groups"
                elif name.endswith("list_all"):
                    kwargs["mode"] = "all"
                else:
                    kwargs["mode"] = body.strip() or self._parse_xml_attrs(attrs_raw).get("mode") or "private"
            if "target" in params: kwargs["target"] = body.strip() or self._parse_xml_attrs(attrs_raw).get("target", "")
            
            # Special case for send_message (it doesnt use body/attrs_raw directly in sig)
            if method_name == "_send_userbot_message":
                attrs = self._parse_xml_attrs(attrs_raw)
                chat = attrs.get("chat") or attrs.get("to") or attrs.get("target")
                if name == "message.send_current":
                    chat = None
                return await self._send_userbot_message(body.strip(), source_event, chat=chat)
            if method_name == "_run_mcub_command" and not kwargs.get("command"):
                command_map = {
                    "mcub.modules": "modules",
                    "mcub.config": "cfg",
                    "mcub.install": "dlm",
                    "mcub.reload": "restart",
                }
                kwargs["command"] = command_map.get(name, "")
            if method_name == "_save_skill":
                attrs = self._parse_xml_attrs(attrs_raw)
                return await self._skills_registry_tool(name, attrs_raw, body or attrs.get("content", ""))

            return await handler_method(**kwargs)
        except Exception as e:
            return f"Tool <{name}> execution failed: {e}"
