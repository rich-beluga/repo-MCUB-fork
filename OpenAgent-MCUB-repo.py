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
import difflib
import html
import inspect
import io
import mimetypes
import random
import re
import tempfile
import time
import uuid
import json
import importlib
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import aiohttp
from telethon import events
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

from core.lib.loader.module_base import ModuleBase, callback, command
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


class OpenAgentPlugin:
    """Base class for OpenAgent plugins."""
    name: str = ""
    version: str = "0.1.0"
    tool_registry: tuple[str, ...] = ()
    tool_map: dict[str, str] = {}
    config_defaults: dict[str, object] = {}
    
    def __init__(self, agent: "OpenAgent") -> None:
        self._agent = agent
    
    @property
    def agent(self) -> "OpenAgent":
        return self._agent
    
    async def on_load(self) -> None:
        """Called after plugin is registered."""
        pass

class OpenAgent(ModuleBase):
    name = "OpenAgent"
    version = "0.6.5"
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

    PROVIDERS = (
        "openai",
        "google",
        "openrouter",
        "groq",
        "deepseek",
        "xai",
        "other",
    )
    PROVIDER_LABELS = {
        "openai": "OpenAI",
        "google": "Google",
        "openrouter": "OpenRouter",
        "groq": "Groq",
        "deepseek": "DeepSeek",
        "xai": "xAI",
        "other": "Other",
    }
    DEFAULT_MODELS = {
        "openai": "gpt-5.5",
        "google": "gemini-1.5-flash",
        "openrouter": "openai/gpt-4o-mini",
        "groq": "llama-3.3-70b-versatile",
        "deepseek": "deepseek-chat",
        "xai": "grok-2-latest",
        "other": "gpt-4o-mini",
    }
    BASE_URLS = {
        "openai": "https://api.openai.com/v1",
        "google": "https://generativelanguage.googleapis.com/v1beta",
        "openrouter": "https://openrouter.ai/api/v1",
        "groq": "https://api.groq.com/openai/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "xai": "https://api.x.ai/v1",
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
    TOOL_CALL_JSON_RE = re.compile(r"```tool_call\s*(.*?)```", re.DOTALL | re.I)
    TOOL_REGISTRY = (
        # Core/module-tied tools. Most tools should come from plugins.
        "thinking.note",
        "skills.list", "skills.read", "skills.activate", "skills.import_md", "skills.export_md", "skills.save_from_ai", "skills.install", "skills.repo_list",
        "code.generate_file", "code.generate_mcub_module", "code.choose_filename", "code.attach_result", "code.read_docs",
        "context.remember", "context.clear", "context.regenerate", "context.reply_context", "context.media_context",
        "todo.add", "todo.delete", "todo.edit", "todo.current", "todo.close", "todo.closeall", "todo.clear",
        "utility.token_usage", "utility.placeholders", "utility.random_template", "utility.agent_log", "utility.error_file",
    )
    AGENT_MAX_STEPS = 15

    config = ModuleConfig(
        ConfigValue(
            "provider",
            "openai",
            description="Provider: openai, google, openrouter, groq, deepseek, xai, other",
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
            "reasoning_effort",
            "off",
            description="Reasoning effort for models/providers that support it: off, low, medium, high, xhigh",
            validator=Choice(choices=["off", "low", "medium", "high", "xhigh"], default="off"),
        ),
        ConfigValue(
            "timeout",
            180,
            description="HTTP timeout seconds for each provider request. Increase for slow reasoning/code tasks.",
            validator=Integer(default=180, min=10, max=600),
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
            "context_compaction_enabled",
            True,
            description="Automatically summarize old chat context when it becomes too large",
            validator=Boolean(default=True),
        ),
        ConfigValue(
            "context_compaction_chars",
            18000,
            description="Compact remembered chat context after this many characters",
            validator=Integer(default=18000, min=2000, max=200000),
        ),
        ConfigValue(
            "context_compaction_keep_turns",
            2,
            description="Recent user/assistant turns to keep verbatim after compaction",
            validator=Integer(default=2, min=0, max=10),
        ),
        ConfigValue(
            "context_compaction_max_tokens",
            900,
            description="Maximum tokens used for the compaction summary response",
            validator=Integer(default=900, min=128, max=4096),
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
            "<blockquote><a href=\"tg://emoji?id=6010179991944305029\">☺️</a> <strong>OpenAgent</strong>: <a href=\"tg://emoji?id=5325872701032635449\">⏳</a>  <em>{elapsed}</em>s\n• <u>{provider}/{model}</u>  •  <code>{reasoning_effort}</code>\n| | | | | | | | | | | | | | | | | | | | | | | | | | |\n<a href=\"tg://emoji?id=5408994848084624514\">💸</a> <strong>in</strong> <em>{input_tokens}</em>, <strong>out</strong> <em>{output_tokens}</em> | <b>total</b>\n<i>{total_tokens}</i> | <strong>tool use:</strong> <em>{tool_count}</em></blockquote>\n<blockquote expandable><i>{thinking}</i></blockquote>",
            description="Final response header template. Placeholders: {provider}, {provider_key}, {model}, {reasoning_effort}, {elapsed}, {tool_count}, {input_tokens}, {output_tokens}, {total_tokens}, {thinking}, {random}, {prefix}, {time}, {date}",
            validator=String(default="<blockquote><a href=\"tg://emoji?id=6010179991944305029\">☺️</a> <strong>OpenAgent</strong>: <a href=\"tg://emoji?id=5325872701032635449\">⏳</a>  <em>{elapsed}</em>s\n• <u>{provider}/{model}</u>  •  <code>{reasoning_effort}</code>\n| | | | | | | | | | | | | | | | | | | | | | | | | | |\n<a href=\"tg://emoji?id=5408994848084624514\">💸</a> <strong>in</strong> <em>{input_tokens}</em>, <strong>out</strong> <em>{output_tokens}</em> | <b>total</b>\n<i>{total_tokens}</i> | <strong>tool use:</strong> <em>{tool_count}</em></blockquote>\n<blockquote expandable><i>{thinking}</i></blockquote>"),
        ),
        ConfigValue(
            "request_label",
            "<a href=\"tg://emoji?id=6010352868672936598\"><strong>🐈‍⬛</strong></a><strong></strong><strong> Prompt:</strong>",
            description="Request block label template. Placeholders: {provider}, {provider_key}, {model}, {reasoning_effort}, {elapsed}, {tool_count}, {input_tokens}, {output_tokens}, {total_tokens}, {thinking}, {random}, {prefix}, {time}, {date}",
            validator=String(default="<a href=\"tg://emoji?id=6010352868672936598\"><strong>🐈‍⬛</strong></a><strong></strong><strong> Prompt:</strong>"),
        ),
        ConfigValue(
            "response_label",
            "<a href=\"tg://emoji?id=6010286885090368072\"><strong>❌</strong></a><strong></strong><strong> Answer:</strong>",
            description="Response block label template. Placeholders: {provider}, {provider_key}, {model}, {reasoning_effort}, {elapsed}, {tool_count}, {input_tokens}, {output_tokens}, {total_tokens}, {thinking}, {random}, {prefix}, {time}, {date}",
            validator=String(default="<a href=\"tg://emoji?id=6010286885090368072\"><strong>❌</strong></a><strong></strong><strong> Answer:</strong>"),
        ),
        ConfigValue(
            "thinking_template",
            "<blockquote><a href=\"tg://emoji?id=6010292571627069263\">😎</a> <u>{provider}/{model}</u> • <em>prepares the response...</em></blockquote >\n<blockquote><a href=\"tg://emoji?id=5404857686477015710\">🔄</a><strong><em> {random}</em></strong><em></em></blockquote>",
            description="Initial loading/thinking message template. Placeholders: {provider}, {provider_key}, {model}, {reasoning_effort}, {elapsed}, {tool_count}, {input_tokens}, {output_tokens}, {total_tokens}, {thinking}, {random}, {prefix}, {time}, {date}",
            validator=String(default="<blockquote><a href=\"tg://emoji?id=6010292571627069263\">😎</a> <u>{provider}/{model}</u> • <em>prepares the response...</em></blockquote >\n<blockquote><a href=\"tg://emoji?id=5404857686477015710\">🔄</a><strong><em> {random}</em></strong><em></em></blockquote>"),
        ),
        ConfigValue(
            "tool_display_template",
            "<blockquote expandable><i>{thinking_line}</i></blockquote>\n<blockquote expandable><strong>┌|</strong> {status_emoji_html} <em>{status_text}</em> <code>{tool}</code>\n<strong>└|</strong> <a href=\"tg://emoji?id=6010570945637392851\">🥳</a>  <b>Round:</b> <code>{round}/{round_total}</code> • <b>Reasoning:</b>\n<code>{reasoning_effort}</code>\n</blockquote><blockquote><a href=\"tg://emoji?id=5310041868191407556\">🩸</a> <strong>{activity_line}</strong></blockquote>\n<blockquote expandable><a href=\"tg://emoji?id=6012361831035705571\">😪</a> <strong>Log tools</strong>\n<code>{log_lines}</code></blockquote>",
            description="Tool execution status template. Raw: {tool}, {title}, {value}, {log}, {step}. Semantic: {round}, {round_total}, {progress_bar}, {progress_percent}, {status_emoji}, {status_icon}, {status_emoji_html}, {status_icon_html}, {status_text}, {tool_group}, {tool_short}, {tool_input}, {tool_input_block}, {thinking_line}, {thinking_block}, {log_lines}, {log_block}, {log_count}, {elapsed_line}, {token_line}, {model_line}, {activity_line}. General: {provider}, {model}, {reasoning_effort}, {elapsed}, {thinking}, {random}, {prefix}, {time}, {date}",
            validator=String(
                default="<blockquote expandable><i>{thinking_line}</i></blockquote>\n<blockquote expandable><strong>┌|</strong> {status_emoji_html} <em>{status_text}</em> <code>{tool}</code>\n<strong>└|</strong> <a href=\"tg://emoji?id=6010570945637392851\">🥳</a>  <b>Round:</b> <code>{round}/{round_total}</code> • <b>Reasoning:</b>\n<code>{reasoning_effort}</code>\n</blockquote><blockquote><a href=\"tg://emoji?id=5310041868191407556\">🩸</a> <strong>{activity_line}</strong></blockquote>\n<blockquote expandable><a href=\"tg://emoji?id=6012361831035705571\">😪</a> <strong>Log tools</strong>\n<code>{log_lines}</code></blockquote>"
            ),
        ),
        ConfigValue(
            "tool_status_emojis",
            "thinking=❔\nterminal=🖥\nweb=🌐\nfile=📦\nmcub=🧲\nmessage=💬\ndialog=🗂\nchat=🐈‍⬛\nmoderation=🛡\nprofile=👤\ncontacts=👥\ncreation=✨\nskills=🧠\ncode=🧬\ncontext=🧾\nutility=🛠\ndefault=🛠",
            description="Custom emoji/icon map for {status_emoji}/{status_icon}. Format: group_or_tool=emoji per line. Tool-specific keys like terminal.run or thinking.note override groups like terminal/thinking. Premium emoji HTML is allowed via {status_emoji_html}/{status_icon_html}.",
            validator=String(default="thinking=❔\nterminal=🖥\nweb=🌐\nfile=📦\nmcub=🧲\nmessage=💬\ndialog=🗂\nchat=🐈‍⬛\nmoderation=🛡\nprofile=👤\ncontacts=👥\ncreation=✨\nskills=🧠\ncode=🧬\ncontext=🧾\nutility=🛠\ndefault=🛠"),
        ),
        ConfigValue(
            "tool_display_max_chars",
            1200,
            description="Maximum chars from current tool input shown in status form",
            validator=Integer(default=1200, min=80, max=4000),
        ),
        ConfigValue(
            "tool_display_log_lines",
            8,
            description="How many recent tool names to show in status form",
            validator=Integer(default=8, min=0, max=30),
        ),
        ConfigValue(
            "thinking_display_limit",
            3,
            description="How many recent thinking.note entries to show in {thinking}",
            validator=Integer(default=3, min=0, max=20),
        ),
        ConfigValue(
            "thinking_empty_text",
            "Модель ещё не думала.",
            description="Text for {thinking} when no thinking.note entries exist",
            validator=String(default="Модель ещё не думала."),
        ),
        ConfigValue(
            "thinking_bullet",
            "•",
            description="Prefix marker for each thinking.note line in {thinking}. Empty disables the marker",
            validator=String(default="•"),
        ),
        ConfigValue(
            "random_strings",
            ["Thinking...", "Думаю...", "Генерирую..."],
            description="Random lines for {random}",
            validator=List(default=["Thinking...", "Думаю...", "Генерирую..."], item_type=str),
        ),
        ConfigValue(
            "todo_status_emojis",
            "pending=...\nopen=>>>\nclosed=---",
            description="State markers for {todo}. Format: pending=..., open=>>>, closed=---",
            validator=String(default="pending=...\nopen=>>>\nclosed=---"),
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
        ConfigValue(
            "skills_enabled",
            True,
            description="Enable loading OpenAgent skills into the system prompt",
            validator=Boolean(default=True),
        ),
        ConfigValue(
            "skills_trigger_mode",
            "auto",
            description="When to load skills: auto = only on keyword match, always = every request, off = never",
            validator=String(default="auto"),
        ),
        ConfigValue(
            "skill_repo_url",
            "https://raw.githubusercontent.com/hairpin01/repo-MCUB-fork/main/OpenAgent/skills",
            description="Base URL for installable OpenAgent skills repository",
            validator=String(default="https://raw.githubusercontent.com/hairpin01/repo-MCUB-fork/main/OpenAgent/skills"),
        ),
        ConfigValue(
            "tool_confirmation_enabled",
            True,
            description="Ask for confirmation before tools that can change files, chats, account state, or run commands",
            validator=Boolean(default=True),
        ),
        ConfigValue(
            "tool_confirmation_mode",
            "medium",
            description="How often to ask before tools: low = only critical/destructive, medium = write/actions, high = almost every non-read tool",
            validator=Choice(choices=["low", "medium", "high"], default="medium"),
        ),
        ConfigValue(
            "tool_confirmation_template",
            "<blockquote><a href=\"tg://emoji?id=6010201728773790293\">😈</a> Continue?\n<a href=\"tg://emoji?id=6012317326584583729\">😐</a> Tool: {tool} • {elapsed}s</blockquote>\n<blockquote expandable><a href=\"tg://emoji?id=6010394680179562842\">😶</a> <b>What will be completed</b>\n<a href=\"tg://emoji?id=6010292550152230657\">☀️</a> <code>{value}</code></blockquote>",
            description="Confirmation form template. Placeholders: {tool}, {value}, {elapsed}, {elapsed_line}",
            validator=String(default="<blockquote><a href=\"tg://emoji?id=6010201728773790293\">😈</a> Continue?\n<a href=\"tg://emoji?id=6012317326584583729\">😐</a> Tool: {tool} • {elapsed}s</blockquote>\n<blockquote expandable><a href=\"tg://emoji?id=6010394680179562842\">😶</a> <b>What will be completed</b>\n<a href=\"tg://emoji?id=6010292550152230657\">☀️</a> <code>{value}</code></blockquote>"),
        ),
        ConfigValue(
            "tool_confirmation_yes_text",
            "Выполнить",
            description="Confirm button text for dangerous tools",
            validator=String(default="Выполнить"),
        ),
        ConfigValue(
            "tool_confirmation_no_text",
            "Не сейчас",
            description="Cancel button text for dangerous tools",
            validator=String(default="Не сейчас"),
        ),
        ConfigValue(
            "tool_confirmation_timeout",
            900,
            description="Seconds to wait for dangerous tool confirmation",
            validator=Integer(default=900, min=10, max=3600),
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
            "reasoning_effort": "off",
            "timeout": 180,
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
            "context_compaction_enabled": True,
            "context_compaction_chars": 18000,
            "context_compaction_keep_turns": 2,
            "context_compaction_max_tokens": 900,
            "tool_memory_enabled": False,
            "tool_memory_items": 20,
            "tool_memory_max_chars": 500,
            "response_header": "<blockquote><a href=\"tg://emoji?id=6010179991944305029\">☺️</a> <strong>OpenAgent</strong>: <a href=\"tg://emoji?id=5325872701032635449\">⏳</a>  <em>{elapsed}</em>s\n• <u>{provider}/{model}</u>  •  <code>{reasoning_effort}</code>\n| | | | | | | | | | | | | | | | | | | | | | | | | | |\n<a href=\"tg://emoji?id=5408994848084624514\">💸</a> <strong>in</strong> <em>{input_tokens}</em>, <strong>out</strong> <em>{output_tokens}</em> | <b>total</b>\n<i>{total_tokens}</i> | <strong>tool use:</strong> <em>{tool_count}</em></blockquote>\n<blockquote expandable><i>{thinking}</i></blockquote>",
            "request_label": "<a href=\"tg://emoji?id=6010352868672936598\"><strong>🐈‍⬛</strong></a><strong></strong><strong> Prompt:</strong>",
            "response_label": "<a href=\"tg://emoji?id=6010286885090368072\"><strong>❌</strong></a><strong></strong><strong> Answer:</strong>",
            "thinking_template": "<blockquote><a href=\"tg://emoji?id=6010292571627069263\">😎</a> <u>{provider}/{model}</u> • <em>prepares the response...</em></blockquote >\n<blockquote><a href=\"tg://emoji?id=5404857686477015710\">🔄</a><strong><em> {random}</em></strong><em></em></blockquote>",
            "tool_display_template": "<blockquote expandable><i>{thinking_line}</i></blockquote>\n<blockquote expandable><strong>┌|</strong> {status_emoji_html} <em>{status_text}</em> <code>{tool}</code>\n<strong>└|</strong> <a href=\"tg://emoji?id=6010570945637392851\">🥳</a>  <b>Round:</b> <code>{round}/{round_total}</code> • <b>Reasoning:</b>\n<code>{reasoning_effort}</code>\n</blockquote><blockquote><a href=\"tg://emoji?id=5310041868191407556\">🩸</a> <strong>{activity_line}</strong></blockquote>\n<blockquote expandable><a href=\"tg://emoji?id=6012361831035705571\">😪</a> <strong>Log tools</strong>\n<code>{log_lines}</code></blockquote>",
            "tool_status_emojis": "thinking=❔\nterminal=🖥\nweb=🌐\nfile=📦\nmcub=🧲\nmessage=💬\ndialog=🗂\nchat=🐈‍⬛\nmoderation=🛡\nprofile=👤\ncontacts=👥\ncreation=✨\nskills=🧠\ncode=🧬\ncontext=🧾\nutility=🛠\ndefault=🛠",
            "tool_display_max_chars": 1200,
            "tool_display_log_lines": 8,
            "thinking_display_limit": 3,
            "thinking_empty_text": "Модель ещё не думала.",
            "thinking_bullet": "•",
            "random_strings": ["Thinking...", "Думаю...", "Генерирую..."],
            "todo_status_emojis": "pending=...\nopen=>>>\nclosed=---",
            "placeholders": "",
            "repo_context_enabled": True,
            "repo_context_max_chars": 7000,
            "skills_enabled": True,
            "skills_trigger_mode": "auto",
            "skill_repo_url": "https://raw.githubusercontent.com/hairpin01/repo-MCUB-fork/main/OpenAgent/skills",
            "tool_confirmation_enabled": True,
            "tool_confirmation_mode": "medium",
            "tool_confirmation_template": "<blockquote><a href=\"tg://emoji?id=6010201728773790293\">😈</a> Continue?\n<a href=\"tg://emoji?id=6012317326584583729\">😐</a> Tool: {tool} • {elapsed}s</blockquote>\n<blockquote expandable><a href=\"tg://emoji?id=6010394680179562842\">😶</a> <b>What will be completed</b>\n<a href=\"tg://emoji?id=6010292550152230657\">☀️</a> <code>{value}</code></blockquote>",
            "tool_confirmation_yes_text": "Выполнить",
            "tool_confirmation_no_text": "Не сейчас",
            "tool_confirmation_timeout": 900,
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
        self._inline_status_waiters: dict[str, asyncio.Future[Any]] = {}
        self._tool_confirmation_waiters: dict[str, asyncio.Future[bool]] = {}
        self._last_token_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
        self._todo_items_cache: list[dict[str, str]] = []
        self._plugins: dict[str, OpenAgentPlugin] = {}
        self._plugin_files: dict[str, Path] = {}
        self._plugins_cache: list[dict] = []
        self._tool_map_cache: dict[str, str] | None = None
        await self._load_todo_items_storage()
        await self._load_installed_plugins()
        self.log.info("OpenAgent loaded")

    def _provider(self) -> str:
        provider = str(self.config.get("provider", "openai")).lower().strip()
        return provider if provider in self.PROVIDERS else "openai"

    def _normalize_provider(self, provider: str) -> str:
        aliases = {
            "custom": "other",
            "open_router": "openrouter",
            "open-router": "openrouter",
            "grok": "xai",
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

    def _response_title(
        self,
        elapsed: float,
        *,
        tool_count: int = 0,
        thinking_notes: list[str] | None = None,
    ) -> str:
        return self._render_template(
            str(self.config.get("response_header", ""))
            or "<blockquote><a href=\"tg://emoji?id=6010179991944305029\">☺️</a> <strong>OpenAgent</strong>: <a href=\"tg://emoji?id=5325872701032635449\">⏳</a>  <em>{elapsed}</em>s\n• <u>{provider}/{model}</u>  •  <code>{reasoning_effort}</code>\n| | | | | | | | | | | | | | | | | | | | | | | | | | |\n<a href=\"tg://emoji?id=5408994848084624514\">💸</a> <strong>in</strong> <em>{input_tokens}</em>, <strong>out</strong> <em>{output_tokens}</em> | <b>total</b>\n<i>{total_tokens}</i> | <strong>tool use:</strong> <em>{tool_count}</em></blockquote>\n<blockquote expandable><i>{thinking}</i></blockquote>",
            elapsed=elapsed,
            tool_count=tool_count,
            thinking_notes=thinking_notes,
        )

    def _format_thinking_notes(self, thinking_notes: list[str] | None = None) -> str:
        notes = [str(note).strip() for note in (thinking_notes or []) if str(note).strip()]
        limit = int(self.config.get("thinking_display_limit", 3) or 0)
        if limit > 0:
            notes = notes[-limit:]
        else:
            notes = []
        if not notes:
            return str(self.config.get("thinking_empty_text", "Модель ещё не думала.") or "Модель ещё не думала.")
        bullet = str(self.config.get("thinking_bullet", "•") or "").strip()
        prefix = f"{bullet} " if bullet else ""
        return "\n".join(f"{prefix}{note}" for note in notes)

    def _placeholder_values(
        self,
        *,
        elapsed: float | None = None,
        tool_count: int | None = None,
        thinking_notes: list[str] | None = None,
    ) -> dict[str, str]:
        raw_random = self.config.get("random_strings", []) or []
        if isinstance(raw_random, str):
            raw_random = raw_random.splitlines()
        random_lines = [str(line).strip() for line in raw_random if str(line).strip()]
        random_value = random.choice(random_lines) if random_lines else "Thinking..."
        return {
            "provider": self._provider_label(),
            "provider_key": self._provider(),
            "model": self._model(),
            "reasoning_effort": self._reasoning_effort(),
            "tool_count": str(tool_count if tool_count is not None else 0),
            "available_tool_count": str(len(self._effective_tool_registry())),
            "elapsed": f"{elapsed:.1f}" if elapsed is not None else "0.0",
            "input_tokens": str(self._last_token_usage.get("input_tokens", 0)),
            "output_tokens": str(self._last_token_usage.get("output_tokens", 0)),
            "total_tokens": str(self._last_token_usage.get("total_tokens", 0)),
            "thinking": self._format_thinking_notes(thinking_notes),
            "todo": self._format_todo_placeholder(),
            "random": random_value,
            "prefix": getattr(self.kernel, "custom_prefix", ".") or ".",
            "time": time.strftime("%H:%M:%S"),
            "date": time.strftime("%Y-%m-%d"),
        }

    def _render_template(
        self,
        template: str,
        *,
        elapsed: float | None = None,
        tool_count: int | None = None,
        thinking_notes: list[str] | None = None,
    ) -> str:
        values = self._placeholder_values(
            elapsed=elapsed,
            tool_count=tool_count,
            thinking_notes=thinking_notes,
        )
        result = template or ""
        for key, value in values.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    def _thinking_text(self) -> str:
        return self._render_template(
            str(self.config.get("thinking_template", "") or "<blockquote><a href=\"tg://emoji?id=6010292571627069263\">😎</a> <u>{provider}/{model}</u> • <em>prepares the response...</em></blockquote >\n<blockquote><a href=\"tg://emoji?id=5404857686477015710\">🔄</a><strong><em> {random}</em></strong><em></em></blockquote>")
        )

    def _format_placeholders(self) -> str:
        return "\n".join(
            [
                "Template placeholders available in response_header, request_label, response_label, thinking_template, and tool_display_template:",
                "",
                "General",
                "{provider} - Provider label",
                "{provider_key} - Provider config key",
                "{model} - Current model",
                "{reasoning_effort} - Current reasoning effort mode: off, low, medium, high, or xhigh",
                "{tool_count} - How many tools the agent used in this request",
                "{available_tool_count} - Registered OpenAgent tool operation count",
                "{elapsed} - Generation time seconds",
                "{input_tokens} - Input/prompt tokens accepted by provider",
                "{output_tokens} - Output/completion tokens returned by provider",
                "{total_tokens} - Total tokens for last provider response",
                "{thinking} - Recent thinking.note entries or thinking_empty_text",
                "{todo} - Persistent TODO list rendered with state markers",
                "{todo_html} - Same as {todo}, but intended for raw HTML insertion in tool_display_template",
                "{random} - Random line from random_strings",
                "{prefix} - Current command prefix",
                "{time} - Current local time",
                "{date} - Current local date",
                "",
                "Raw tool display",
                "{tool} - Current tool name in tool_display_template",
                "{title} - Current tool status title in tool_display_template",
                "{value} - Current tool input in tool_display_template",
                "{log} - Recent tool log in tool_display_template",
                "{step} - Current tool step number in tool_display_template",
                "",
                "Semantic tool display",
                "{round} - Alias for current tool step number",
                "{round_total} - Maximum tool rounds per request",
                "{progress_bar} - Text progress bar for current round",
                "{progress_percent} - Current round progress percent",
                "{status_emoji} - Emoji/icon for current tool category from tool_status_emojis",
                "{status_icon} - Alias for status_emoji",
                "{status_emoji_html} - Raw HTML emoji/icon for current tool category; use for premium <a> emoji",
                "{status_icon_html} - Alias for status_emoji_html",
                "{status_text} - Human-readable current tool action",
                "{tool_group} - Current tool namespace/category",
                "{tool_short} - Current tool name without namespace",
                "{tool_input} - Escaped current tool input; empty for thinking.note",
                "{tool_input_block} - Ready HTML block with tool input; empty for thinking.note/no input",
                "{thinking_line} - Recent thinking notes as escaped text",
                "{thinking_block} - Ready HTML block with recent thinking notes",
                "{log_lines} - Recent tool log as escaped text",
                "{log_block} - Ready HTML block with recent tool log",
                "{log_count} - Number of tools in current request log",
                "{elapsed_line} - Ready text with elapsed seconds",
                "{token_line} - Ready text with token usage",
                "{model_line} - Ready text with provider/model",
                "{activity_line} - Ready text with random status and elapsed seconds",
                "",
                "Config tips",
                "tool_status_emojis format: one mapping per line, e.g. terminal=🖥 or thinking.note=<a href=\"tg://emoji?id=...\">❔</a>",
                "tool-specific emoji keys override group keys; default=... is used as fallback.",
                "todo_status_emojis format: pending=..., open=>>>, closed=--- (aliases: active/todo and done/completed).",
            ]
        )

    def _parse_todo_items_raw(self, raw: str | None) -> list[dict[str, str]]:
        raw_text = str(raw or "").strip()
        if not raw_text:
            return []
        try:
            parsed = json.loads(raw_text)
        except Exception:
            return []
        if not isinstance(parsed, list):
            return []
        cleaned: list[dict[str, str]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            text = self._todo_parse_html_text(str(item.get("text", "") or ""))
            status = self._todo_normalize_status(str(item.get("status", "pending") or "pending"))
            if text:
                cleaned.append({"text": text[:500], "status": status})
        return cleaned

    def _todo_parse_html_text(self, text: str) -> str:
        value = html.unescape(str(text or "")).strip()
        value = re.sub(r"\s+", " ", value).strip()
        return value[:500]

    def _todo_items(self) -> list[dict[str, str]]:
        cached = getattr(self, "_todo_items_cache", None)
        if isinstance(cached, list):
            return [dict(item) for item in cached if isinstance(item, dict)]
        return []

    async def _load_todo_items_storage(self) -> None:
        self._todo_items_cache = []

    def _todo_normalize_status(self, status: str) -> str:
        status = (status or "").strip().lower()
        mapping = {
            "open": "open",
            "active": "open",
            "todo": "open",
            "new": "open",
            "pending": "pending",
            "later": "pending",
            "wait": "pending",
            "backlog": "pending",
            "closed": "closed",
            "close": "closed",
            "done": "closed",
            "completed": "closed",
            "complete": "closed",
            "finished": "closed",
        }
        return mapping.get(status, "pending")

    def _todo_status_map(self) -> dict[str, str]:
        mapping = {
            "pending": "...",
            "open": ">>>",
            "closed": "---",
        }
        raw = str(self.config.get("todo_status_emojis", "") or "")
        for line in raw.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = self._todo_normalize_status(key.strip().lower())
            value = value.strip()
            if key and value:
                mapping[key] = value
        return mapping

    def _format_todo_placeholder(self) -> str:
        items = self._todo_items()
        if not items:
            return "TODO empty"
        status_map = self._todo_status_map()
        return "\n".join(
            f"{status_map.get(item['status'], '...')} {item['text']}"
            for item in items
        )

    async def _save_todo_items(self, items: list[dict[str, str]]) -> list[dict[str, str]]:
        cleaned: list[dict[str, str]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            text = self._todo_parse_html_text(str(item.get("text", "") or ""))
            if not text:
                continue
            cleaned.append(
                {
                    "text": text[:500],
                    "status": self._todo_normalize_status(str(item.get("status", "pending") or "pending")),
                }
            )
        self._todo_items_cache = cleaned
        await asyncio.sleep(0)
        return cleaned

    def _todo_target_index(
        self,
        items: list[dict[str, str]],
        attrs: dict[str, str],
        body: str,
        *,
        allow_body_text: bool = True,
    ) -> tuple[int | None, str]:
        target_raw = (
            attrs.get("index")
            or attrs.get("idx")
            or attrs.get("id")
            or attrs.get("number")
            or attrs.get("target")
            or attrs.get("item")
            or ""
        ).strip()
        body_raw = (body or "").strip()
        if not target_raw and body_raw and "\n" not in body_raw and "|" not in body_raw:
            target_raw = body_raw
        if not target_raw:
            return None, "todo index/text is required"
        if target_raw.isdigit():
            idx = int(target_raw) - 1
            if 0 <= idx < len(items):
                return idx, ""
            return None, f"todo index out of range: {target_raw}"
        if allow_body_text:
            needle = target_raw.lower()
            for idx, item in enumerate(items):
                if needle in item["text"].lower():
                    return idx, ""
        return None, "todo item not found"

    def _tool_group(self, tool_name: str) -> str:
        tool_name = (tool_name or "").lower().strip()
        if "." in tool_name:
            return tool_name.split(".", 1)[0]
        if tool_name in {"terminal", "web_search", "send_message", "dialogs", "history", "search_messages"}:
            return {
                "web_search": "web",
                "send_message": "message",
                "dialogs": "dialog",
                "history": "message",
                "search_messages": "message",
            }.get(tool_name, tool_name)
        return tool_name or "tool"

    def _tool_status_emoji(self, tool_name: str) -> str:
        tool_name = (tool_name or "").lower().strip()
        group = self._tool_group(tool_name)
        configured: dict[str, str] = {}
        raw = self.config.get("tool_status_emojis", "") if hasattr(self, "config") else ""
        for line in str(raw or "").splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lower()
            value = value.strip()
            if key and value:
                configured[key] = value
        if tool_name in configured:
            return configured[tool_name]
        if group in configured:
            return configured[group]
        if "default" in configured:
            return configured["default"]
        return {
            "thinking": "❔",
            "terminal": "🖥",
            "web": "🌐",
            "file": "📦",
            "mcub": "🧲",
            "message": "💬",
            "dialog": "🗂",
            "chat": "🐈‍⬛",
            "moderation": "🛡",
            "profile": "👤",
            "contacts": "👥",
            "creation": "✨",
            "skills": "🧠",
            "code": "🧬",
            "context": "🧾",
            "todo": "📝",
            "utility": "🛠",
        }.get(group, "🛠")

    def _tool_status_text(self, tool_name: str, title: str) -> str:
        tool_name = (tool_name or "").lower().strip()
        group = self._tool_group(tool_name)
        if tool_name == "thinking.note":
            return "Думаю"
        if group == "terminal":
            return "Выполняю команду"
        if group == "web":
            return "Работаю с web"
        if group == "file":
            return "Работаю с файлом"
        if group == "mcub":
            return "Выполняю MCUB-команду"
        if group == "message":
            return "Работаю с сообщениями"
        if group == "chat":
            return "Проверяю чат"
        if group == "dialog":
            return "Проверяю диалоги"
        if group == "code":
            return "Готовлю код"
        if group == "todo":
            return "Обновляю TODO"
        return title or f"Выполняю {tool_name or 'tool'}"

    def _progress_bar(self, step: int, total: int, width: int = 10) -> str:
        total = max(1, total)
        step = max(0, min(step, total))
        filled = max(0, min(width, round(width * step / total)))
        return "▰" * filled + "▱" * (width - filled)

    def _tool_display_semantic_values(
        self,
        *,
        title: str,
        tool_name: str,
        safe_value: str,
        log_text: str,
        log: list[str],
        elapsed: float | None,
        thinking_notes: list[str] | None,
    ) -> dict[str, str]:
        step = len(log)
        total = self.AGENT_MAX_STEPS
        group = self._tool_group(tool_name)
        short = (tool_name or title or "tool").split(".")[-1]
        status_emoji = self._tool_status_emoji(tool_name)
        status_text = self._tool_status_text(tool_name, title)
        thinking_line = self._format_thinking_notes(thinking_notes)
        log_lines = html.escape(log_text)
        tool_input = "" if (tool_name or "").lower().strip() == "thinking.note" else html.escape(safe_value)
        tool_input_block = (
            f"<blockquote expandable><b>📦 Tool input</b>\n<code>{tool_input}</code></blockquote>"
            if tool_input
            else ""
        )
        log_block = (
            f"<blockquote expandable><b>😪 Log tools</b>\n<code>{log_lines}</code></blockquote>"
            if log_lines
            else ""
        )
        thinking_block = f"<blockquote expandable><b>❔ Thinking</b>\n{thinking_line}</blockquote>"
        elapsed_text = f"{elapsed:.1f}s" if elapsed is not None else "0.0s"
        token_line = (
            f"💸 in {self._last_token_usage.get('input_tokens', 0)}, "
            f"out {self._last_token_usage.get('output_tokens', 0)} | "
            f"total {self._last_token_usage.get('total_tokens', 0)}"
        )
        progress_percent = str(int(round(100 * min(step, total) / max(1, total))))
        return {
            "round": str(step),
            "round_total": str(total),
            "progress_bar": self._progress_bar(step, total),
            "progress_percent": progress_percent,
            "status_emoji": html.escape(status_emoji),
            "status_icon": html.escape(status_emoji),
            "status_emoji_html": status_emoji,
            "status_icon_html": status_emoji,
            "status_text": html.escape(status_text),
            "tool_group": html.escape(group),
            "tool_short": html.escape(short),
            "tool_input": tool_input,
            "tool_input_block": tool_input_block,
            "thinking_line": thinking_line,
            "thinking_block": thinking_block,
            "log_lines": log_lines,
            "log_block": log_block,
            "log_count": str(len(log)),
            "elapsed_line": f"⏳ {elapsed_text}",
            "token_line": html.escape(token_line),
            "model_line": html.escape(f"{self._provider_label()} / {self._model()}"),
            "activity_line": html.escape(f"{self._placeholder_values(elapsed=elapsed).get('random', 'Thinking...')} {elapsed_text}"),
        }

    def _render_tool_display(
        self,
        *,
        title: str,
        tool_name: str,
        value: str,
        log: list[str],
        elapsed: float | None = None,
        thinking_notes: list[str] | None = None,
    ) -> str:
        max_chars = int(self.config.get("tool_display_max_chars", 1200) or 1200)
        log_lines = int(self.config.get("tool_display_log_lines", 8) or 8)
        safe_value = value if len(value) <= max_chars else value[:max_chars] + "..."
        log_text = "\n".join(log[-log_lines:]) if log_lines > 0 else ""
        if len(log_text) > 1800:
            log_text = log_text[-1800:]
        placeholder_values = self._placeholder_values(
            elapsed=elapsed,
            tool_count=len(log),
            thinking_notes=thinking_notes,
        )
        values = {
            key: html.escape(value)
            for key, value in placeholder_values.items()
        }
        todo_raw = placeholder_values.get("todo", "")
        values["todo"] = todo_raw
        values["todo_html"] = todo_raw
        values.update({
            "title": html.escape(title),
            "tool": html.escape(tool_name or title),
            "value": html.escape(safe_value),
            "log": html.escape(log_text),
            "step": str(len(log)),
            "tool_count": str(len(log)),
        })
        values.update(
            self._tool_display_semantic_values(
                title=title,
                tool_name=tool_name,
                safe_value=safe_value,
                log_text=log_text,
                log=log,
                elapsed=elapsed,
                thinking_notes=thinking_notes,
            )
        )
        template = str(self.config.get("tool_display_template", "") or "")
        if not template:
            template = "<blockquote expandable><i>{thinking_line}</i></blockquote>\n<blockquote expandable><strong>┌|</strong> {status_emoji_html} <em>{status_text}</em> <code>{tool}</code>\n<strong>└|</strong> <a href=\"tg://emoji?id=6010570945637392851\">🥳</a>  <b>Round:</b> <code>{round}/{round_total}</code> • <b>Reasoning:</b>\n<code>{reasoning_effort}</code>\n</blockquote><blockquote><a href=\"tg://emoji?id=5310041868191407556\">🩸</a> <strong>{activity_line}</strong></blockquote>\n<blockquote expandable><a href=\"tg://emoji?id=6012361831035705571\">😪</a> <strong>Log tools</strong>\n<code>{log_lines}</code></blockquote>"
        for key, item in values.items():
            template = template.replace("{" + key + "}", item)
        return template

    def _tool_registry_prompt(self) -> str:
        lines = []
        for index, name in enumerate(self._effective_tool_registry(), 1):
            lines.append(f"{index}. {name}")
        return "\n".join(lines)

    def _request_label(
        self,
        *,
        elapsed: float | None = None,
        thinking_notes: list[str] | None = None,
    ) -> str:
        return self._render_template(
            str(self.config.get("request_label", "") or "<a href=\"tg://emoji?id=6010352868672936598\"><strong>🐈‍⬛</strong></a><strong></strong><strong> Prompt:</strong>"),
            elapsed=elapsed,
            thinking_notes=thinking_notes,
        )

    def _response_label(
        self,
        *,
        elapsed: float | None = None,
        thinking_notes: list[str] | None = None,
    ) -> str:
        return self._render_template(
            str(self.config.get("response_label", "") or "<a href=\"tg://emoji?id=6010286885090368072\"><strong>❌</strong></a><strong></strong><strong> Answer:</strong>"),
            elapsed=elapsed,
            thinking_notes=thinking_notes,
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
        elif history and history[0].get("role") == "system" and str(history[0].get("content", "")).startswith("Compacted previous OpenAgent session context:"):
            keep_tail = max(0, max_messages - 1)
            tail_source = history[1:]
            self._chat_history[int(chat_id)] = [history[0], *tail_source[-keep_tail:]] if keep_tail else [history[0]]
        else:
            del history[:-max_messages]

    def _history_for_chat(self, chat_id: int | None) -> list[dict[str, str]]:
        if not chat_id or not self.config["context_enabled"]:
            return []
        return list(self._chat_history.get(int(chat_id), []))

    def _history_chars(self, history: list[dict[str, str]]) -> int:
        return sum(len(str(item.get("content", ""))) for item in history)

    def _format_history_for_compaction(self, history: list[dict[str, str]]) -> str:
        parts = []
        for index, item in enumerate(history, 1):
            role = str(item.get("role", "unknown"))
            content = str(item.get("content", ""))
            parts.append(f"[{index}] {role}:\n{content}")
        return "\n\n".join(parts)

    def _compaction_system_prompt(self) -> str:
        return (
            "You compact an OpenAgent chat session. Read the full prior context and "
            "write a concise continuity summary that lets the assistant continue work "
            "without needing the omitted messages. Preserve: user goals, decisions, "
            "constraints, files changed/read, commands run, test results, current TODOs, "
            "open questions, and important warnings. Do not invent facts. Do not include "
            "irrelevant chatter. Output plain text markdown only."
        )

    async def _compact_chat_history_if_needed(
        self,
        chat_id: int | None,
        provider: str,
        api_key: str,
    ) -> bool:
        if not chat_id or not bool(self.config.get("context_enabled", True)):
            return False
        if not bool(self.config.get("context_compaction_enabled", True)):
            return False

        history = self._chat_history.get(int(chat_id), [])
        threshold = int(self.config.get("context_compaction_chars", 18000) or 18000)
        if not history or self._history_chars(history) <= threshold:
            return False

        keep_messages = max(0, int(self.config.get("context_compaction_keep_turns", 2) or 2) * 2)
        old_history = history[:-keep_messages] if keep_messages else history
        recent_history = history[-keep_messages:] if keep_messages else []
        if not old_history:
            return False

        max_chars = max(threshold * 2, threshold + 4000)
        compact_input = self._format_history_for_compaction(old_history)
        if len(compact_input) > max_chars:
            compact_input = compact_input[-max_chars:]

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._compaction_system_prompt()},
            {
                "role": "user",
                "content": (
                    "Compact this OpenAgent session context. The assistant will continue "
                    "after your summary, with the newest turns kept separately.\n\n"
                    f"{compact_input}"
                ),
            },
        ]
        max_tokens = int(self.config.get("context_compaction_max_tokens", 900) or 900)
        try:
            if provider in ("openai", "openrouter", "groq", "deepseek", "xai", "other"):
                summary = await self._ask_openai_compatible(
                    provider,
                    messages,
                    api_key,
                    max_tokens_override=max_tokens,
                )
            elif provider == "google":
                summary = await self._ask_google(
                    messages,
                    api_key,
                    max_tokens_override=max_tokens,
                )
            else:
                return False
        except Exception as exc:
            self.log.warning(f"OpenAgent context compaction failed: {exc}")
            return False

        summary = (summary or "").strip()
        if not summary:
            return False

        self._chat_history[int(chat_id)] = [
            {
                "role": "system",
                "content": "Compacted previous OpenAgent session context:\n" + summary[-12000:],
            },
            *recent_history,
        ]
        return True

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
        path = Path(self._workspace_dir()) / "openagent_skills"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _legacy_skills_dir(self) -> Path:
        return Path(self._workspace_dir()) / "openagent_skills"

    def _workspace_dir(self) -> str:
        work_dir = getattr(self.kernel, "WORK_DIR", None)
        if work_dir:
            path = Path(str(work_dir)).expanduser()
            if path.exists() and path.is_dir():
                return str(path)
        return str(Path.cwd())

    def _resolve_plugins_dir(self) -> Path:
        """Directory for installed plugins on the real machine."""
        path = Path(self._workspace_dir()) / "openagent_plugins"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _builtin_plugins_dir(self) -> Path:
        """Directory with bundled plugins shipped with OpenAgent."""
        return Path(__file__).resolve().parent / "OpenAgent" / "plugins"

    def _plugin_scan_dirs(self) -> list[Path]:
        dirs: list[Path] = []
        for candidate in (self._builtin_plugins_dir(), self._resolve_plugins_dir()):
            if candidate.exists() and candidate.is_dir() and candidate not in dirs:
                dirs.append(candidate)
        return dirs

    async def _load_installed_plugins(self) -> None:
        """Scan bundled + external plugin directories and register all plugins.
        External plugins override bundled ones without warning."""
        for plugins_dir in self._plugin_scan_dirs():
            for fpath in sorted(plugins_dir.glob("*.py")):
                if fpath.name.startswith("_") or fpath.name == "__init__.py":
                    continue
                try:
                    await self._register_plugin_from_file(fpath)
                except Exception as exc:
                    self.log.warning(f"Plugin load failed: {fpath.name} - {exc}")

    async def _register_plugin_from_file(self, fpath: Path) -> None:
        """Import a .py file, find *Plugin class, register it."""
        module_name = f"openagent_plugins_{fpath.parent.name}_{fpath.stem}_{uuid.uuid4().hex[:8]}"
        spec = importlib.util.spec_from_file_location(module_name, fpath)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load {fpath}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        plugin_cls = None
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if isinstance(attr, type) and attr_name.endswith("Plugin") and attr is not OpenAgentPlugin:
                plugin_cls = attr
                break
        if not plugin_cls:
            raise ValueError(f"No *Plugin class found in {fpath.name}")
        plugin = plugin_cls(self)
        self._register_plugin(plugin)
        self._plugin_files[str(plugin.name).lower()] = fpath
        on_load = getattr(plugin, "on_load", None)
        if callable(on_load):
            maybe_awaitable = on_load()
            if asyncio.iscoroutine(maybe_awaitable):
                await maybe_awaitable

    def _register_plugin(self, plugin: OpenAgentPlugin) -> None:
        """Register plugin: add config_defaults, tools, handlers."""
        name = str(getattr(plugin, "name", "") or "").strip().lower()
        if not name:
            name = plugin.__class__.__name__.replace("Plugin", "").strip().lower()
        plugin.name = name
        if name in self._plugins:
            self.log.debug(f"Plugin {name} already registered, external overrides bundled")
        # Set default config values if not already set
        for key, value in getattr(plugin, "config_defaults", {}).items():
            if key not in self.config.keys():
                self.config._values[key] = self._plugin_config_value(key, value)
        self._plugins[name] = plugin
        self._tool_map_cache = None  # invalidate after plugin list changes
        self.log.info(f"Plugin registered: {name} v{plugin.version}")

    def _plugin_config_value(self, key: str, value: object) -> ConfigValue:
        description = f"OpenAgent plugin setting: {key}"
        if isinstance(value, bool):
            validator = Boolean(default=value)
        elif isinstance(value, int):
            validator = Integer(default=value)
        elif isinstance(value, float):
            validator = Float(default=value)
        elif isinstance(value, list):
            validator = List(default=value)
        else:
            validator = String(default=str(value or ""))
        return ConfigValue(key, value, description=description, validator=validator)

    def _effective_tool_registry(self) -> tuple[str, ...]:
        names = set(self.TOOL_REGISTRY)
        for plugin in self._plugins.values():
            for tool_name in getattr(plugin, "tool_registry", ()):
                if tool_name:
                    names.add(str(tool_name).strip().lower())
            for tool_name in getattr(plugin, "tool_map", {}).keys():
                if tool_name:
                    names.add(str(tool_name).strip().lower())
        return tuple(sorted(names))

    def _unregister_plugin(self, name: str) -> None:
        """Remove a plugin by name."""
        name = str(name or "").strip().lower()
        self._plugins.pop(name, None)
        self._plugin_files.pop(name, None)
        self._tool_map_cache = None  # invalidate after plugin list changes
        self.log.info(f"Plugin unregistered: {name}")

    def _get_plugin_for_tool(self, tool_name: str) -> OpenAgentPlugin | None:
        """Find which plugin handles a given tool name."""
        tool_name = (tool_name or "").lower().strip()
        for candidate in self._plugins.values():
            if tool_name in getattr(candidate, "tool_map", {}):
                return candidate
        group = self._tool_group(tool_name)
        plugin = self._plugins.get(group)
        if plugin is not None:
            return plugin
        return None

    async def _fetch_repo_plugins(self) -> list[dict]:
        """Fetch list of available plugins from GitHub repo."""
        url = "https://api.github.com/repos/hairpin01/repo-MCUB-fork/contents/OpenAgent/plugins"
        try:
            session = aiohttp.ClientSession()
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                files = await resp.json()
        except Exception:
            return []
        finally:
            await session.close()

        plugins = []
        for f in files:
            fname = f.get("name", "")
            if not fname.endswith(".py") or fname == "__init__.py":
                continue
            raw_url = f.get("download_url", "")
            meta = await self._parse_plugin_meta(raw_url)
            meta["file_name"] = fname
            meta["plugin_name"] = fname.replace(".py", "")
            meta["download_url"] = raw_url
            plugins.append(meta)
        self._plugins_cache = plugins
        return plugins

    async def _parse_plugin_meta(self, raw_url: str) -> dict:
        """Parse plugin metadata from raw .py file via regex."""
        meta: dict = {"name": "?", "version": "?", "author": "?", "description": "?", "tools": []}
        try:
            session = aiohttp.ClientSession()
            async with session.get(raw_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return meta
                code = await resp.text()
        except Exception:
            return meta
        finally:
            await session.close()

        name_m = re.search(r'name\s*=\s*["](.+?)["]', code) or re.search(r"name\s*=\s*['](.+?)[']", code)
        ver_m = re.search(r'version\s*=\s*["](.+?)["]', code) or re.search(r"version\s*=\s*['](.+?)[']", code)
        author_m = re.search(r'author\s*=\s*["](.+?)["]', code) or re.search(r"author\s*=\s*['](.+?)[']", code)
        desc_m = re.search(r'"ru"\s*:\s*"(.+?)"', code)
        if not desc_m:
            desc_m = re.search(r'"en"\s*:\s*"(.+?)"', code)
        tools_m = re.findall(r'"((?:terminal|web|mcub|message|file|dialog|chat|moderation|profile|contacts|creation|account|code|utility|skills|context|todo|thinking)\.[\w.]+)"', code)

        if name_m: meta["name"] = name_m.group(1)
        if ver_m: meta["version"] = ver_m.group(1)
        if author_m: meta["author"] = author_m.group(1)
        if desc_m: meta["description"] = desc_m.group(1)
        if tools_m: meta["tools"] = tools_m
        return meta

    async def _install_plugin_from_repo(self, name: str) -> str:
        """Download a plugin from repo and install it."""
        raw_url = f"https://raw.githubusercontent.com/hairpin01/repo-MCUB-fork/main/OpenAgent/plugins/{name}.py"
        session = aiohttp.ClientSession()
        try:
            async with session.get(raw_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    raise ValueError(f"Plugin {name} not found in repo")
                code = await resp.text()
        finally:
            await session.close()
        
        plugins_dir = self._resolve_plugins_dir()
        fpath = plugins_dir / f"{name}_plugin.py"
        fpath.write_text(code, encoding="utf-8")
        await self._register_plugin_from_file(fpath)
        return name

    def _safe_plugin_name(self, name: str) -> str:
        name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(name or "").strip()).strip("._")
        if name.endswith("_plugin"):
            name = name[:-7]
        return (name[:64] or "plugin").lower()

    async def _install_plugin_from_code(self, name: str, code: str) -> str:
        """Install a plugin from raw Python code into openagent_plugins/."""
        code = (code or "").strip()
        if not code:
            raise ValueError("Plugin code is empty")
        compile(code, f"<openagent-plugin:{name or 'reply'}>", "exec")
        safe_name = self._safe_plugin_name(name)
        fpath = self._resolve_plugins_dir() / f"{safe_name}.py"
        fpath.write_text(code + "\n", encoding="utf-8")
        try:
            await self._register_plugin_from_file(fpath)
        except Exception:
            with contextlib.suppress(Exception):
                fpath.unlink()
            raise
        return next((pname for pname, path in self._plugin_files.items() if path == fpath), safe_name)

    async def _install_plugin_from_reply(self, event: events.NewMessage.Event) -> str:
        reply = await event.get_reply_message()
        if not reply:
            raise ValueError("Reply to a .py plugin file or Python plugin code")
        arg_name = self._args_raw(event)
        file_name = getattr(getattr(reply, "file", None), "name", None) or ""
        code = ""
        try:
            data = await reply.download_media(file=bytes)
            if data:
                code = data.decode("utf-8", errors="replace")
        except Exception:
            code = ""
        if not code:
            code = getattr(reply, "raw_text", None) or getattr(reply, "text", "") or ""
        if not code.strip():
            raise ValueError("Plugin code is empty")
        name = arg_name.strip()
        if not name and file_name.lower().endswith(".py"):
            name = Path(file_name).stem
        if not name:
            class_match = re.search(r"class\s+(\w+Plugin)\b", code)
            name = class_match.group(1).replace("Plugin", "") if class_match else "plugin"
        return await self._install_plugin_from_code(name, code)

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
        return self._skills_dir / self._safe_skill_name(name) / "SKILL.md"

    def _skill_name_from_path(self, path: Path) -> str:
        if path.name == "SKILL.md" and path.parent.name:
            return path.parent.name
        return path.stem

    def _find_skill_path(self, name: str) -> Path:
        path = self._skill_path(name)
        if path.exists():
            return path

        legacy_path = self._legacy_skills_dir() / f"{self._safe_skill_name(name)}.md"
        if legacy_path.exists():
            return legacy_path

        return path

    def _list_skills(self) -> list[Path]:
        if not getattr(self, "_skills_dir", None):
            self._skills_dir = self._resolve_skills_dir()
        try:
            self._skills_dir.mkdir(parents=True, exist_ok=True)
            skills = list(self._skills_dir.glob("*/SKILL.md"))

            # Backward compatibility for older OpenAgent exports. OpenCode-style
            # skills in openagent_skills/<name>/SKILL.md win on name conflicts.
            seen = {self._skill_name_from_path(path).lower() for path in skills}
            legacy_dir = self._legacy_skills_dir()
            if legacy_dir.is_dir():
                for path in legacy_dir.glob("*.md"):
                    if path.stem.lower() not in seen:
                        skills.append(path)
                        seen.add(path.stem.lower())

            return sorted(skills, key=lambda p: self._skill_name_from_path(p).lower())
        except Exception as e:
            self.log.warning(f"OpenAgent skills directory unavailable: {e}")
            return []

    def _should_load_skills(self, prompt: str = "") -> bool:
        if not bool(self.config.get("skills_enabled", True)):
            return False

        mode = str(self.config.get("skills_trigger_mode", "auto") or "auto").strip().lower()
        if mode in {"off", "false", "disabled", "disable", "never", "0"}:
            return False
        if mode in {"always", "all", "on", "true", "1"}:
            return True

        text = (prompt or "").lower()
        if not text.strip():
            return False

        return bool(self._matching_skill_paths(prompt))

    def _skill_frontmatter(self, text: str) -> dict[str, str]:
        if not text.startswith("---"):
            return {}
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, flags=re.DOTALL)
        if not match:
            return {}

        data: dict[str, str] = {}
        current_key = ""
        current_lines: list[str] = []
        for line in match.group(1).splitlines():
            key_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
            if key_match:
                if current_key:
                    data[current_key] = "\n".join(current_lines).strip()
                current_key = key_match.group(1).strip().lower()
                current_lines = [key_match.group(2).strip()]
            elif current_key:
                current_lines.append(line.strip())
        if current_key:
            data[current_key] = "\n".join(current_lines).strip()
        return data

    def _skill_keywords_from_text(self, text: str, fallback_name: str) -> list[str]:
        frontmatter = self._skill_frontmatter(text)
        raw = frontmatter.get("keywords", "")
        keywords: list[str] = []

        if raw.startswith("[") and raw.endswith("]"):
            keywords.extend(part.strip().strip("'\"") for part in raw.strip("[]").split(","))
        else:
            for line in raw.splitlines():
                cleaned = line.strip().lstrip("-").strip().strip("'\"")
                if cleaned:
                    keywords.append(cleaned)

        if not keywords:
            keywords.append(fallback_name)
            description = frontmatter.get("description", "")
            keywords.extend(re.findall(r"[\wА-Яа-яЁё.-]{4,}", description)[:6])

        return [keyword.lower() for keyword in keywords if keyword.strip()]

    def _skill_matches_prompt(self, path: Path, prompt: str) -> bool:
        text = (prompt or "").lower()
        if not text.strip():
            return False
        try:
            skill_text = path.read_text(encoding="utf-8", errors="replace")[:2000]
        except Exception:
            return False
        keywords = self._skill_keywords_from_text(skill_text, self._skill_name_from_path(path))
        return any(keyword in text for keyword in keywords)

    def _matching_skill_paths(self, prompt: str = "") -> list[Path]:
        mode = str(self.config.get("skills_trigger_mode", "auto") or "auto").strip().lower()
        skills = self._list_skills()
        if mode in {"always", "all", "on", "true", "1"}:
            return skills
        if mode in {"off", "false", "disabled", "disable", "never", "0"}:
            return []
        return [path for path in skills if self._skill_matches_prompt(path, prompt)]

    def _installed_skill_match_score(self, path: Path, query: str) -> int:
        query = (query or "").lower().strip()
        if not query:
            return 0
        name = self._skill_name_from_path(path).lower()
        safe_query = self._safe_skill_name(query).lower()
        safe_name = self._safe_skill_name(name).lower()
        score = 0
        if safe_query == safe_name:
            score = max(score, 100)
        elif safe_name.startswith(safe_query) or safe_query.startswith(safe_name):
            score = max(score, 80)
        elif safe_query in safe_name or safe_name in safe_query:
            score = max(score, 60)
        try:
            skill_text = path.read_text(encoding="utf-8", errors="replace")[:4000]
        except Exception:
            skill_text = ""
        frontmatter = self._skill_frontmatter(skill_text)
        keywords = self._skill_keywords_from_text(skill_text, self._skill_name_from_path(path))
        query_words = set(re.findall(r"[\wА-Яа-яЁё.-]{3,}", query))
        for keyword in keywords:
            keyword = keyword.lower().strip()
            if not keyword:
                continue
            if keyword in query:
                score = max(score, 50)
            if keyword in query_words:
                score = max(score, 70)
        haystack = " ".join(
            [name, frontmatter.get("description", "")]
            + keywords
        ).lower()
        overlap = sum(1 for word in query_words if word in haystack)
        if overlap:
            score = max(score, min(65, 25 + overlap * 10))
        return score

    def _installed_skill_candidates(self, query: str) -> list[Path]:
        ranked = [
            (self._installed_skill_match_score(path, query), path)
            for path in self._list_skills()
        ]
        return [path for score, path in sorted(ranked, key=lambda item: item[0], reverse=True) if score > 0]

    def _activate_skill_text(self, query: str) -> str:
        query = (query or "").strip()
        if not query:
            return "skill name or query is required"
        candidates = self._installed_skill_candidates(query)
        if not candidates:
            installed = ", ".join(self._skill_name_from_path(path) for path in self._list_skills())
            return "No installed skill matched. Installed skills: " + (installed or "none")
        path = candidates[0]
        text = path.read_text(encoding="utf-8", errors="replace")[:16000]
        return f"Activated OpenAgent skill: {self._skill_name_from_path(path)}\n\n{text}"

    def _load_skills_prompt(self, prompt: str = "") -> str:
        if not self._should_load_skills(prompt):
            return ""

        chunks = []
        for path in self._matching_skill_paths(prompt)[:20]:
            try:
                text = path.read_text(encoding="utf-8")[:4000]
            except Exception:
                continue
            chunks.append(f"## Skill: {self._skill_name_from_path(path)}\n{text}")
        if not chunks:
            return ""
        return "\n\nLoaded OpenAgent skills. Use them when relevant:\n" + "\n\n".join(chunks)

    def _normalize_skill_content(self, name: str, content: str) -> str:
        text = content.strip()
        if text.startswith("---"):
            return text + "\n"

        safe_name = self._safe_skill_name(name)
        first_heading = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
        description = first_heading.group(1).strip() if first_heading else safe_name
        frontmatter = (
            "---\n"
            f"name: {safe_name}\n"
            f"description: {description}\n"
            "---\n\n"
        )
        return frontmatter + text + "\n"

    def _save_skill(self, name: str, content: str) -> str:
        safe_name = self._safe_skill_name(name)
        path = self._skill_path(safe_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._normalize_skill_content(safe_name, content), encoding="utf-8")
        return safe_name

    def _skill_repo_base_url(self) -> str:
        return str(
            self.config.get(
                "skill_repo_url",
                "https://raw.githubusercontent.com/hairpin01/repo-MCUB-fork/main/OpenAgent/skills",
            )
            or ""
        ).strip().rstrip("/")

    async def _fetch_text_url(self, url: str, *, max_chars: int = 120000) -> str:
        timeout = aiohttp.ClientTimeout(total=int(self.config["timeout"]))
        headers = {"User-Agent": "OpenAgent/skills"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as resp:
                text = await resp.text(errors="replace")
                if resp.status >= 400:
                    raise RuntimeError(f"HTTP {resp.status}: {text[:500]}")
                return text[:max_chars]

    async def _fetch_skill_repo_index(self) -> list[dict[str, Any]]:
        base_url = self._skill_repo_base_url()
        if not base_url:
            raise RuntimeError("skill_repo_url is not configured")
        raw = await self._fetch_text_url(f"{base_url}/index.json", max_chars=60000)
        data = json.loads(raw)
        if isinstance(data, dict):
            items = data.get("skills") or []
        elif isinstance(data, list):
            items = data
        else:
            items = []
        return [item for item in items if isinstance(item, dict)]

    def _repo_skill_match_score(self, query: str, item: dict[str, Any]) -> int:
        needle = self._safe_skill_name(query).lower()
        names = [
            str(item.get("name") or ""),
            str(item.get("id") or ""),
            Path(str(item.get("path") or "")).parent.name,
        ]
        names.extend(str(alias) for alias in item.get("aliases") or [] if alias)
        normalized = [self._safe_skill_name(name).lower() for name in names if name]
        if needle in normalized:
            return 100
        if any(value.startswith(needle) for value in normalized):
            return 75
        if any(needle in value for value in normalized):
            return 50
        haystack = " ".join(
            [str(item.get("description") or "")]
            + [str(keyword) for keyword in item.get("keywords") or []]
        ).lower()
        return 25 if query.lower() in haystack else 0

    async def _repo_skill_candidates(self, query: str) -> list[dict[str, Any]]:
        index = await self._fetch_skill_repo_index()
        ranked = [
            (self._repo_skill_match_score(query, item), item)
            for item in index
        ]
        return [item for score, item in sorted(ranked, key=lambda pair: pair[0], reverse=True) if score > 0]

    async def _install_repo_skill(self, name: str) -> str:
        query = (name or "").strip()
        if not query:
            raise RuntimeError("skill name is required")
        base_url = self._skill_repo_base_url()
        candidates = await self._repo_skill_candidates(query)
        if not candidates:
            raise RuntimeError(f"Skill not found in repo: {query}")
        item = candidates[0]
        path = str(item.get("path") or f"{self._safe_skill_name(str(item.get('name') or query))}/SKILL.md").lstrip("/")
        content = await self._fetch_text_url(f"{base_url}/{quote(path)}", max_chars=200000)
        saved_name = self._save_skill(str(item.get("name") or query), content)
        return saved_name

    async def _format_skill_repo_list(self) -> str:
        items = await self._fetch_skill_repo_index()
        if not items:
            return "No skills in repository"
        lines = []
        for item in items:
            name = str(item.get("name") or item.get("id") or Path(str(item.get("path") or "")).parent.name or "skill")
            description = str(item.get("description") or "").strip()
            lines.append(f"- {name}: {description}" if description else f"- {name}")
        return "\n".join(lines)


    def _thinking_system_prompt(self) -> str:
        base = str(self.config["system_prompt"]).strip()
        return (
            f"{base}\n\n"
            "Your ONLY task right now: output exactly one ```tool_call``` block using thinking.note.\n"
            "The note must be one concise user-facing sentence (max 180 chars).\n"
            "Say what you understood from the request and the immediate next step.\n"
            "Do NOT write a generic heartbeat. Do NOT put any tool call JSON inside the note text.\n\n"
            "Output ONLY this, nothing else:\n"
            "```tool_call\n"
            "{\"tool\":\"thinking.note\",\"args\":{\"note\":\"Understood: <brief summary>. Next: <next step>.\"}}\n"
            "```"
        )

    def _system_prompt(self, user_prompt: str = "") -> str:
        prompt = str(self.config["system_prompt"]).strip()
        tlist = ", ".join(sorted(self._get_tool_map().keys()))
        todo_snapshot = self._format_todo_placeholder()
        prompt += (
            f"\n\nOpenAgent 0.6.5 is active. You have access to {len(self._effective_tool_registry())} tool operations.\n"
            "\n## Tool call format\n"
            "Output one or more fenced JSON blocks. Each block is ONE tool call:\n"
            "```tool_call\n"
            "{\"tool\":\"tool.name\",\"args\":{\"key\":\"value\"},\"body\":\"optional long text\"}\n"
            "```\n"
            "Use `args` for structured parameters. Use `body` for commands, messages, file content, or long text.\n"
            "\n## Batching — emit multiple blocks in ONE turn to save steps\n"
            "```tool_call\n"
            "{\"tool\":\"thinking.note\",\"args\":{\"note\":\"Listing files to find the config\"}}\n"
            "```\n"
            "```tool_call\n"
            "{\"tool\":\"terminal.run\",\"args\":{\"cmd\":\"ls -la\"}}\n"
            "```\n"
            "RULE: thinking.note body/note MUST be plain text. NEVER put a tool call JSON inside thinking.note.\n"
            "WRONG: {\"tool\":\"thinking.note\",\"args\":{\"note\":\"{\\\"tool\\\":\\\"terminal.run\\\",\\\"args\\\":{\\\"cmd\\\":\\\"ls\\\"}}\"}}\n"
            "RIGHT: two separate ```tool_call``` blocks as shown above.\n"
            "\n## Format rules\n"
            "- ONLY ```tool_call``` fenced JSON blocks. No XML tags. No plain JSON outside fences.\n"
            "- When no tool is needed: reply in plain text with no ```tool_call``` blocks at all.\n"
            f"Available tool names: {tlist}\n"
            "\n## Guidelines\n"
            "1. Use only tools from 'Available tool names'. Wrong names fail immediately.\n"
            "2. mcub.* tools: omit the userbot prefix (body='ping', not '.ping').\n"
            "3. Unknown domain? Call skills.activate first. To persist knowledge: skills.save_from_ai.\n"
            "4. Simple greetings/questions: answer in plain text, no tools.\n"
            "5. thinking.note: use for meaningful progress updates only — findings, risky actions, approach changes.\n"
            "6. Multi-step tasks: keep todo.* in sync (todo.add → todo.current → todo.close → todo.clear).\n"
            "Never explain tool calls. Output the block(s) and wait for results."
        )
        prompt += "\n\nCurrent TODO state:\n" + todo_snapshot
        prompt += self._load_skills_prompt(user_prompt)
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
            await asyncio.sleep(0)
            self._outputs.append(str(text))
            return self

        async def reply(self, text: str, *args: Any, **kwargs: Any) -> "OpenAgent._MCUBEvent":
            await asyncio.sleep(0)
            self._outputs.append(str(text))
            return self

        async def respond(self, text: str, *args: Any, **kwargs: Any) -> "OpenAgent._MCUBEvent":
            await asyncio.sleep(0)
            self._outputs.append(str(text))
            return self

        async def delete(self, *args: Any, **kwargs: Any) -> None:
            await asyncio.sleep(0)
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


    async def _resolve_tool_chat(self, chat: str | None, source_event: Any | None) -> Any:
        await asyncio.sleep(0)
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


    async def _show_agent_action(
        self,
        event: Any,
        title: str,
        value: str,
        log: list[str],
        tool_name: str = "",
        elapsed: float | None = None,
        thinking_notes: list[str] | None = None,
    ) -> None:
        text = self._render_tool_display(
            title=title,
            tool_name=tool_name,
            value=value,
            log=log,
            elapsed=elapsed,
            thinking_notes=thinking_notes,
        )
        try:
            buttons = getattr(event, "_openagent_status_buttons", None)
            if buttons is not None and hasattr(event, "edit"):
                await event.edit(text, buttons=buttons, parse_mode="html")
            else:
                await self.edit(event, text, as_html=True)
        except Exception:
            await self.edit(event, html.escape(title), as_html=True)

    def _dangerous_terminal_command(self, command: str) -> bool:
        command = (command or "").lower().strip()
        if not command:
            return False
        compact = re.sub(r"\s+", " ", command)
        dangerous_patterns = [
            r"\brm\s+-[a-z]*[rf][a-z]*\s+/(?:\s|$|\*)",
            r"\brm\s+-[a-z]*[rf][a-z]*\s+--no-preserve-root\b",
            r"\bsudo\s+rm\s+-[a-z]*[rf][a-z]*\s+/(?:\s|$|\*)",
            r"\bmkfs(?:\.[a-z0-9]+)?\b",
            r"\bdd\b.*\bof=/dev/",
            r"\b(shutdown|reboot|poweroff|halt)\b",
            r">\s*/dev/(sd[a-z]|nvme\d+n\d+|mapper/)",
        ]
        return any(re.search(pattern, compact) for pattern in dangerous_patterns)

    def _requires_tool_confirmation(self, tool_name: str, attrs_raw: str = "", body: str = "") -> bool:
        if not bool(self.config.get("tool_confirmation_enabled", True)):
            return False
        name = (tool_name or "").lower().strip()
        group = self._tool_group(name)
        safe_read_tools = {
            "message.get", "message.search", "message.history", "message.typing",
            "dialog.list_private", "dialog.list_groups", "dialog.list_all", "dialog.search",
            "chat.info", "chat.participants", "chat.admins", "chat.permissions", "chat.common_with_user",
            "profile.get", "profile.get_full", "profile.get_me", "profile.get_photos", "profile.common_chats",
            "context.reply_context", "context.media_context", "skills.list", "skills.read", "skills.activate",
            "skills.repo_list", "utility.token_usage", "utility.placeholders", "utility.random_template",
            "todo.add", "todo.delete", "todo.edit", "todo.current", "todo.close", "todo.closeall", "todo.clear",
            "thinking.note",
        }
        if name in safe_read_tools:
            return False

        mode = str(self.config.get("tool_confirmation_mode", "medium") or "medium").lower().strip()
        attrs = self._parse_xml_attrs(attrs_raw)
        command = body.strip() or attrs.get("command") or attrs.get("cmd") or attrs.get("query") or attrs.get("text") or ""
        low_tools = {
            "profile.update_name", "profile.update_bio", "profile.update_username", "profile.set_photo",
            "contacts.add", "contacts.delete", "contacts.block", "contacts.unblock",
        }
        critical_tools = {
            "terminal.run", "terminal.inspect",
            "mcub.command", "mcub.install", "mcub.reload",
            "message.send_current", "message.send_target", "message.edit", "message.delete",
            "message.forward", "message.pin", "message.schedule", "message.draft",
            "file.send", "file.download_media", "file.attach_image", "file.attach_video",
            "moderation.mute", "moderation.unmute", "moderation.ban", "moderation.unban",
            "moderation.kick", "moderation.promote", "moderation.demote", "moderation.pin",
            "moderation.delete_messages",
            "profile.update_name", "profile.update_bio", "profile.update_username", "profile.set_photo",
            "contacts.add", "contacts.delete", "contacts.block", "contacts.unblock",
            "creation.channel", "creation.group", "creation.bot", "creation.channel_avatar", "creation.private_invite",
            "chat.set_title", "chat.set_about", "chat.set_username", "chat.slowmode", "chat.invite_link",
            "dialog.archive", "dialog.unarchive", "dialog.leave", "dialog.set_photo",
            "context.clear",
            "skills.install", "skills.import_md", "skills.save_from_ai",
            "code.generate_file", "code.generate_mcub_module", "code.attach_result",
        }
        critical_groups = {"terminal", "mcub", "message", "file", "moderation", "profile", "contacts", "creation"}
        medium_groups = {
            "terminal", "mcub", "message", "file", "moderation", "profile",
            "contacts", "creation", "chat", "dialog", "context", "skills", "code",
        }
        if mode == "low":
            return name in low_tools or self._dangerous_terminal_command(command)
        if mode == "high":
            return group not in {"utility", "thinking"}
        return name in critical_tools or group in medium_groups

    @callback(ttl=900)
    async def _confirm_tool_action(
        self,
        call: events.CallbackQuery.Event,
        token: str | None = None,
        approved: bool = False,
    ) -> None:
        if token:
            future = self._tool_confirmation_waiters.get(token)
            if future is not None and not future.done():
                future.set_result(bool(approved))
        with contextlib.suppress(Exception):
            await call.answer("Выполняю" if approved else "Отменено", alert=False)

    async def _confirm_dangerous_tool(
        self,
        event: Any,
        tool_name: str,
        value: str,
        *,
        elapsed: float | None = None,
    ) -> bool:
        token = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()
        self._tool_confirmation_waiters[token] = future
        safe_tool = html.escape(tool_name or "tool")
        safe_value = html.escape((value or "").strip()[:1800])
        elapsed_value = f"{elapsed:.1f}" if elapsed is not None else "0.0"
        elapsed_line = f"\n⏳ {elapsed_value}s" if elapsed is not None else ""
        template = str(self.config.get("tool_confirmation_template", "") or "").strip()
        if not template:
            template = "<blockquote><a href=\"tg://emoji?id=6010201728773790293\">😈</a> Continue?\n<a href=\"tg://emoji?id=6012317326584583729\">😐</a> Tool: {tool} • {elapsed}s</blockquote>\n<blockquote expandable><a href=\"tg://emoji?id=6010394680179562842\">😶</a> <b>What will be completed</b>\n<a href=\"tg://emoji?id=6010292550152230657\">☀️</a> <code>{value}</code></blockquote>"
        body = template
        for key, item in {
            "tool": safe_tool,
            "value": safe_value,
            "elapsed": html.escape(elapsed_value),
            "elapsed_line": elapsed_line,
        }.items():
            body = body.replace("{" + key + "}", item)
        buttons = [[
            self.Button.inline(
                str(self.config.get("tool_confirmation_yes_text", "Выполнить") or "Выполнить"),
                self._confirm_tool_action,
                args=(token, True),
                style="primary",
            ),
            self.Button.inline(
                str(self.config.get("tool_confirmation_no_text", "Не сейчас") or "Не сейчас"),
                self._confirm_tool_action,
                args=(token, False),
            ),
        ]]
        try:
            if hasattr(event, "edit"):
                await event.edit(body, buttons=buttons, parse_mode="html")
            else:
                await self.edit(event, body, as_html=True)
            return await asyncio.wait_for(
                future,
                timeout=int(self.config.get("tool_confirmation_timeout", 900) or 900),
            )
        except asyncio.TimeoutError:
            return False
        except Exception:
            return False
        finally:
            self._tool_confirmation_waiters.pop(token, None)

    @callback(ttl=900)
    async def _activate_inline_status(self, call: events.CallbackQuery.Event, token: str | None = None) -> None:
        if token:
            future = self._inline_status_waiters.get(token)
            if future is not None and not future.done():
                future.set_result(call)
        with contextlib.suppress(Exception):
            await call.answer()

    async def _start_inline_status(
        self,
        event: Any,
        text: str,
        buttons: list[list[Any]],
    ) -> Any:
        chat_id = getattr(event, "chat_id", None)
        if chat_id is None:
            return await self.edit(event, text, as_html=True)

        token = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._inline_status_waiters[token] = future
        try:
            _unit, sms = await self.inline(
                chat_id,
                text,
                buttons=[[self.Button.inline(" ", self._activate_inline_status, args=(token,))]],
                ttl=900,
                parse_mode="html",
            )
            if sms:
                with contextlib.suppress(Exception):
                    await sms.click(0)
            try:
                call = await asyncio.wait_for(future, timeout=5)
            except asyncio.TimeoutError:
                call = sms or event
            if hasattr(call, "edit"):
                with contextlib.suppress(Exception):
                    await call.edit(text, buttons=buttons, parse_mode="html")
            with contextlib.suppress(Exception):
                setattr(call, "_openagent_status_buttons", buttons)
            with contextlib.suppress(Exception):
                setattr(call, "_openagent_source_chat_id", chat_id)
            with contextlib.suppress(Exception):
                await event.delete()
            return call or sms or event
        except Exception:
            return await self.edit(event, text, as_html=True)
        finally:
            self._inline_status_waiters.pop(token, None)


    async def _ask_agent(
        self,
        prompt: str,
        status_event: Any | None = None,
        source_event: Any | None = None,
        attachments: list[dict[str, str]] | None = None,
        cancel_token: str | None = None,
        system_override: str | None = None,
        started_at: float | None = None,
    ) -> tuple[str, list[str], list[str]]:
        provider = self._provider()
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(self.strings["no_key"])

        attachments = attachments or []
        if provider == "google":
            user_content = self._build_google_content(prompt, attachments)
        else:
            user_content = self._build_openai_content(prompt, attachments)

        chat_id = getattr(source_event, "chat_id", None) if source_event is not None else None
        compacted_context = await self._compact_chat_history_if_needed(chat_id, provider, api_key)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_override or self._system_prompt(prompt)}
        ]
        tool_memory = self._tool_memory_prompt(chat_id)
        if tool_memory:
            messages.append({"role": "system", "content": tool_memory})
        messages.extend(self._history_for_chat(chat_id))
        messages.append({"role": "user", "content": user_content})

        agent_log: list[str] = []
        if compacted_context:
            agent_log.append("context.compact")
        thinking_notes: list[str] = []
        max_steps = self.AGENT_MAX_STEPS  # Architectural limit for tool chaining in 0.5.0
        invalid_tool_retries = 0
        answer = ""

        if cancel_token and cancel_token in self._cancelled_generations:
            raise RuntimeError("Generation cancelled")
        think_messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._thinking_system_prompt()}
        ]
        think_messages.extend(self._history_for_chat(chat_id))
        think_messages.append({"role": "user", "content": user_content})
        if provider in ("openai", "openrouter", "groq", "deepseek", "xai", "other"):
            think_answer = await self._ask_openai_compatible(provider, think_messages, api_key)
        elif provider == "google":
            think_answer = await self._ask_google(think_messages, api_key)
        else:
            raise RuntimeError(self.strings("bad_provider", providers=", ".join(self.PROVIDERS)))

        think_calls = [
            call
            for call in self._extract_tool_calls(think_answer or "")
            if (call[0] or "").lower().strip() == "thinking.note"
        ]
        if not think_calls:
            fallback_note = re.sub(r"```.*?```", " ", think_answer or "", flags=re.DOTALL).strip()
            think_calls = [("thinking.note", "", fallback_note or "Понял задачу, начинаю выполнение.")]
        thinking_outputs: list[str] = []
        for tool_name, attrs_raw, body in think_calls[:1]:
            if cancel_token and cancel_token in self._cancelled_generations:
                raise RuntimeError("Generation cancelled")
            output = await self._dispatch_tool(
                tool_name,
                attrs_raw,
                body,
                source_event,
                status_event,
                agent_log,
                started_at=started_at,
                thinking_notes=thinking_notes,
            )
            self._remember_tool_output(chat_id, tool_name, output)
            thinking_outputs.append(f"Tool <{tool_name}> output:\n{output}")
        messages.append({"role": "assistant", "content": think_answer or ""})
        messages.append(
            {
                "role": "user",
                "content": "\n\n".join(thinking_outputs) + "\n\nNow proceed with the actual task.",
            }
        )

        for _ in range(max_steps):
            if cancel_token and cancel_token in self._cancelled_generations:
                raise RuntimeError("Generation cancelled")
                
            if provider in ("openai", "openrouter", "groq", "deepseek", "xai", "other"):
                answer = await self._ask_openai_compatible(provider, messages, api_key)
            elif provider == "google":
                answer = await self._ask_google(messages, api_key)
            else:
                raise RuntimeError(self.strings("bad_provider", providers=", ".join(self.PROVIDERS)))

            tool_calls = self._extract_tool_calls(answer or "")
            if not tool_calls:
                tool_error = self._invalid_tool_call_error(answer or "")
                if tool_error:
                    invalid_tool_retries += 1
                    agent_log.append(f"tool_error: {tool_error[:220]}")
                    if invalid_tool_retries > 2:
                        return tool_error, agent_log, thinking_notes
                    messages.append({"role": "assistant", "content": answer or ""})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"{tool_error}\n\n"
                                "Это результат валидации твоего tool_call. Исправь tool_call и повтори прямо сейчас. "
                                "Fix the tool call and try again now. Use only valid OpenAgent tool names, "
                                "valid JSON, and args as a JSON object. If no tool is needed, answer the user "
                                "in plain text with no JSON/tool_call."
                            ),
                        }
                    )
                    continue
                clean_answer = (answer or "").strip()
                if clean_answer or not agent_log:
                    return clean_answer, agent_log, thinking_notes
                break
            invalid_tool_retries = 0

            outputs: list[str] = []
            for tool_name, attrs_raw, body in tool_calls:
                if cancel_token and cancel_token in self._cancelled_generations:
                    raise RuntimeError("Generation cancelled")
                output = await self._dispatch_tool(
                    tool_name,
                    attrs_raw,
                    body,
                    source_event,
                    status_event,
                    agent_log,
                    started_at=started_at,
                    thinking_notes=thinking_notes,
                )
                self._remember_tool_output(chat_id, tool_name, output)
                outputs.append(f"Tool <{tool_name}> output:\n{output}")
            
            messages.append({"role": "assistant", "content": answer})
            followup = "\n\n".join(outputs)
            if any(name != "thinking.note" for name, _attrs, _body in tool_calls):
                followup += (
                    "\n\nProgress reminder: if you need more tools, include a fresh thinking.note "
                    "with the next tool_call batch unless the task is ready for the final answer."
                )
            messages.append({"role": "user", "content": followup})
        # Force one final pass without tool calls if tool-chain limit was reached.
        messages.append(
            {
                "role": "user",
                "content": (
                    "Stop using tools. Give the final user-facing answer now, in plain text only. "
                    "Do not output tool_call fenced blocks, XML tags, or tool calls."
                ),
            }
        )
        if provider in ("openai", "openrouter", "groq", "deepseek", "xai", "other"):
            answer = await self._ask_openai_compatible(provider, messages, api_key)
        elif provider == "google":
            answer = await self._ask_google(messages, api_key)
        else:
            raise RuntimeError(self.strings("bad_provider", providers=", ".join(self.PROVIDERS)))
        clean = (answer or "").strip()
        if not clean and provider in ("openai", "openrouter", "groq", "deepseek", "xai", "other") and self._uses_completion_tokens(provider):
            max_tokens = int(self.config["max_tokens"])
            if int(self._last_token_usage.get("output_tokens", 0) or 0) >= max_tokens:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous final answer was empty because the completion budget was exhausted. "
                            "Answer now in 800 characters or less. Plain text only. No tools."
                        ),
                    }
                )
                answer = await self._ask_openai_compatible(
                    provider,
                    messages,
                    api_key,
                    max_tokens_override=max(4096, max_tokens * 2),
                )
                clean = (answer or "").strip()
        if clean:
            return clean, agent_log, thinking_notes
        return "Инструменты выполнены, но модель не сформировала финальный текст.", agent_log, thinking_notes

    def _tool_names(self) -> set[str]:
        """Single whitelist source for executable tool names and aliases."""
        return set(self._get_tool_map())

    def _json_tool_to_legacy(self, payload: dict[str, Any]) -> tuple[str, str, str] | None:
        """Convert the new JSON tool protocol into legacy attrs/body for handlers."""
        tool_name = str(payload.get("tool") or payload.get("name") or "").lower().strip()
        if tool_name not in self._tool_names():
            return None
        args_raw = payload.get("args") or {}
        if not isinstance(args_raw, dict):
            args_raw = {}
        body_value = payload.get("body")
        if body_value is None:
            for key in ("body", "content", "text", "message", "command", "query", "prompt"):
                if key in args_raw:
                    body_value = args_raw.get(key)
                    break
        body = "" if body_value is None else str(body_value)
        attrs: list[str] = []
        for key, value in args_raw.items():
            if value is None or key == "body":
                continue
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, ensure_ascii=False)
            safe_key = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(key).strip())
            if not safe_key:
                continue
            attrs.append(f'{safe_key}="{html.escape(str(value), quote=True)}"')
        return tool_name, " ".join(attrs), body

    def _iter_json_tool_payloads(self, raw: str) -> list[dict[str, Any]]:
        """Parse one JSON tool payload or a list of payloads without raising."""
        try:
            payload = json.loads((raw or "").strip())
        except Exception:
            return []
        payloads = payload if isinstance(payload, list) else [payload]
        return [item for item in payloads if isinstance(item, dict)]

    def _codex_recipient_tool_name(self, header: str) -> str:
        """Return a registry tool name from a Harmony `to=...` header when possible."""
        match = re.search(r"(?:^|\s)to=([^\s<]+)", header or "")
        if not match:
            return ""
        recipient = match.group(1).strip().strip('"\'').lower()
        aliases = {
            "tool.send_message": "message.send_current",
            "tool.send_current": "message.send_current",
            "tool.thinking_note": "thinking.note",
            "tool.thinking.note": "thinking.note",
        }
        if recipient in aliases:
            return aliases[recipient]
        if recipient.startswith("tool."):
            recipient = recipient[5:]
        return recipient if recipient in self._tool_names() else ""

    def _extract_codex_tool_calls(self, text: str) -> list[tuple[str, str, str]]:
        """Extract Codex/OpenAI Harmony style tool JSON from raw model text.

        Some local OpenAI-compatible models do not follow the fenced `tool_call`
        instruction and instead emit text like:
        `<|start|>assistant<|channel|>commentary ... <|message|>{...}<|call|>`.
        Treat the JSON between `<|message|>` and `<|call|>` as a normal tool
        payload so it is executed instead of being shown to the user.
        """
        calls: list[tuple[str, str, str]] = []
        pattern = r"(?P<header>.*?)<\|message\|>(?P<body>.*?)(?:<\|call\|>|$)"
        for match in re.finditer(pattern, text or "", re.DOTALL):
            fallback_tool = self._codex_recipient_tool_name(match.group("header"))
            raw = match.group("body").strip()
            if not raw:
                continue
            for item in self._iter_json_tool_payloads(raw):
                if fallback_tool and not (item.get("tool") or item.get("name")):
                    item = {**item, "tool": fallback_tool}
                tool_call = self._json_tool_to_legacy(item)
                if tool_call:
                    calls.append(tool_call)
        return calls

    def _extract_json_tool_calls(self, text: str) -> list[tuple[str, str, str]]:
        calls: list[tuple[str, str, str]] = []
        stripped = (text or "").strip()
        if stripped.startswith("{") or stripped.startswith("["):
            for item in self._iter_json_tool_payloads(stripped):
                tool_call = self._json_tool_to_legacy(item)
                if tool_call:
                    calls.append(tool_call)
        for match in self.TOOL_CALL_JSON_RE.finditer(text or ""):
            raw = match.group(1).strip()
            if not raw:
                continue
            for item in self._iter_json_tool_payloads(raw):
                tool_call = self._json_tool_to_legacy(item)
                if tool_call:
                    calls.append(tool_call)
        return calls

    def _invalid_tool_call_error(self, text: str) -> str:
        """Return a user-facing error when the model attempted an invalid tool call."""
        # First check: did the model put a real tool call inside thinking.note?
        for match in self.TOOL_CALL_JSON_RE.finditer(text or ""):
            raw = match.group(1).strip()
            for item in self._iter_json_tool_payloads(raw):
                tool_name = str(item.get("tool") or item.get("name") or "").lower().strip()
                if tool_name == "thinking.note":
                    note_val = ""
                    args = item.get("args") or {}
                    if isinstance(args, dict):
                        note_val = str(args.get("note") or args.get("text") or "").strip()
                    if not note_val:
                        note_val = str(item.get("body") or "").strip()
                    embedded = self._extract_json_tool_calls(note_val)
                    real = [c for c in embedded if c[0] != "thinking.note"]
                    if real:
                        names = ", ".join(c[0] for c in real)
                        return (
                            f"[FORMAT ERROR] You put tool call(s) ({names}) inside thinking.note. "
                            "They were NOT executed. Each tool must be its own separate ```tool_call``` block:\n"
                            "```tool_call\n"
                            "{\"tool\":\"thinking.note\",\"args\":{\"note\":\"your plain-text note\"}}\n"
                            "```\n"
                            "```tool_call\n"
                            f"{{\"tool\":\"{real[0][0]}\",\"args\":{{...}}}}\n"
                            "```\n"
                            "Retry now with separate blocks."
                        )
        raw_items: list[str] = []
        stripped = (text or "").strip()
        if stripped.startswith("{") or stripped.startswith("["):
            raw_items.append(stripped)
        raw_items.extend(match.group(1).strip() for match in self.TOOL_CALL_JSON_RE.finditer(text or ""))
        for raw in raw_items:
            try:
                payload = json.loads(raw)
            except Exception as exc:
                preview = raw.strip().replace("\n", " ")[:500]
                return (
                    f"Ошибка tool call: модель вернула некорректный JSON ({exc}).\n"
                    f"Фрагмент: {preview}"
                )
            payloads = payload if isinstance(payload, list) else [payload]
            for item in payloads:
                if not isinstance(item, dict):
                    return "Ошибка tool call: элемент вызова инструмента должен быть JSON-объектом."
                tool_name = str(item.get("tool") or item.get("name") or "").lower().strip()
                if not tool_name:
                    continue
                if tool_name not in self._tool_names():
                    candidates = sorted(self._tool_names())
                    nearest = ", ".join(difflib.get_close_matches(tool_name, candidates, n=5, cutoff=0.45))
                    available = ", ".join(candidates[:30])
                    hint = f" Ближайшие: {nearest}." if nearest else ""
                    return f"Ошибка tool call: неизвестный инструмент '{tool_name}'.{hint} Доступные примеры: {available}."
                args_raw = item.get("args") or {}
                if not isinstance(args_raw, dict):
                    return f"Ошибка tool call: args для '{tool_name}' должен быть JSON-объектом."
        return ""

    def _extract_json_tool_call(self, text: str) -> tuple[str, str, str] | None:
        calls = self._extract_json_tool_calls(text)
        return calls[0] if calls else None

    def _extract_xml_tool_calls(self, text: str) -> list[tuple[str, str, str]]:
        """Return executable XML fallback calls, ignoring ordinary HTML/XML tags."""
        tool_names = self._tool_names()
        calls: list[tuple[str, str, str]] = []
        for match in self.TOOL_CALL_RE.finditer(text or ""):
            if match.group(1):
                tool_name, attrs_raw, body = match.group(1), match.group(2), match.group(3)
            else:
                tool_name, attrs_raw, body = match.group(4), match.group(5), ""
            tool_name = (tool_name or "").lower().strip()
            if tool_name in tool_names:
                calls.append((tool_name, attrs_raw or "", body or ""))
        return calls

    def _extract_xml_tool_call(self, text: str) -> tuple[str, str, str] | None:
        calls = self._extract_xml_tool_calls(text)
        return calls[0] if calls else None

    def _rescue_embedded_tool_calls(
        self, calls: list[tuple[str, str, str]]
    ) -> list[tuple[str, str, str]]:
        """When the model puts a real tool call inside thinking.note body, surface it.

        Models occasionally emit:
            ```tool_call
            {"tool":"thinking.note","args":{"note":"{\"tool\":\"terminal.run\",\"args\":{\"cmd\":\"ls\"}}"}}
            ```
        instead of two separate blocks. This method rescues those embedded calls
        so they are executed in the same step, while preserving the thinking.note
        itself (its handler will return a FORMAT ERROR that teaches the model).
        """
        result: list[tuple[str, str, str]] = []
        for name, attrs_raw, body in calls:
            result.append((name, attrs_raw, body))
            if name == "thinking.note":
                raw = (body or "").strip()
                # Also check the note= arg if body is empty
                if not raw:
                    try:
                        for item in self._iter_json_tool_payloads(attrs_raw):
                            raw = str(item.get("note") or item.get("text") or "").strip()
                            if raw:
                                break
                    except Exception:
                        pass
                embedded = self._extract_json_tool_calls(raw)
                for emb_name, emb_attrs, emb_body in embedded:
                    if emb_name != "thinking.note":
                        result.append((emb_name, emb_attrs, emb_body))
        return result

    def _extract_tool_calls(self, text: str) -> list[tuple[str, str, str]]:
        """Return executable tool calls; JSON/Codex protocols first, XML fallback second."""
        calls = self._extract_json_tool_calls(text)
        if calls:
            return self._rescue_embedded_tool_calls(calls)
        calls = self._extract_codex_tool_calls(text)
        if calls:
            return self._rescue_embedded_tool_calls(calls)
        calls = self._extract_xml_tool_calls(text)
        return self._rescue_embedded_tool_calls(calls) if calls else calls

    def _extract_tool_call(self, text: str) -> tuple[str, str, str] | None:
        """Return the first executable tool call; kept for compatibility."""
        calls = self._extract_tool_calls(text)
        return calls[0] if calls else None

    def _compact_agent_log(self, log: list[str]) -> list[str]:
        if not log:
            return []
        compacted: list[str] = []
        current = str(log[0])
        count = 1
        for raw in log[1:]:
            item = str(raw)
            if item == current:
                count += 1
                continue
            compacted.append(f"{current} * {count}" if count > 1 else current)
            current = item
            count = 1
        compacted.append(f"{current} * {count}" if count > 1 else current)
        return compacted

    def _agent_log_html(self, log: list[str]) -> str:
        if not log:
            return ""
        compacted = self._compact_agent_log(log)
        return (
            "\n\n<blockquote expandable><b>Agent Log</b>\n"
            f"{html.escape(chr(10).join(compacted))}</blockquote>"
        )

    def _uses_completion_tokens(self, provider: str) -> bool:
        model = self._model(provider).lower()
        return provider == "openai" and (
            model.startswith("gpt-5")
            or model.startswith("o1")
            or model.startswith("o3")
            or model.startswith("o4")
        )

    def _reasoning_effort(self) -> str:
        effort = str(self.config.get("reasoning_effort", "off") or "off").lower().strip()
        return effort if effort in {"low", "medium", "high", "xhigh"} else "off"

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
        *,
        max_tokens_override: int | None = None,
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
        reasoning_effort = self._reasoning_effort()
        if reasoning_effort != "off":
            payload["reasoning_effort"] = reasoning_effort
        max_tokens = int(max_tokens_override or self.config["max_tokens"])
        if self._uses_completion_tokens(provider):
            payload["max_completion_tokens"] = max_tokens
        else:
            payload["max_tokens"] = max_tokens

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
            elif "reasoning_effort" in error_text or "reasoning effort" in error_text:
                payload.pop("reasoning_effort", None)
                data = await self._post_json(url, payload, headers=headers)
            else:
                raise
        try:
            self._set_token_usage(data.get("usage"), provider)
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected {provider} response: {data}") from exc

    async def _ask_google(
        self,
        messages: list[dict[str, str]],
        api_key: str,
        *,
        max_tokens_override: int | None = None,
    ) -> str:
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
                "maxOutputTokens": int(max_tokens_override or self.config["max_tokens"]),
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
        timeout_seconds = int(self.config["timeout"])
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        raise RuntimeError(f"HTTP {resp.status}: {text[:800]}")
                    try:
                        return await resp.json()
                    except Exception as exc:
                        raise RuntimeError(f"Invalid JSON response: {text[:800]}") from exc
        except TimeoutError as exc:
            raise RuntimeError(
                f"Provider request timed out after {timeout_seconds}s. "
                "Increase OpenAgent timeout or use a faster model for this task."
            ) from exc

    def _format_inline_markdown(self, text: str) -> str:
        text = html.escape(html.unescape(text or ""))
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
            code = html.escape(html.unescape(match.group(2).strip("\n")))
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
        thinking_notes: list[str] | None = None,
        buttons: list[list[Any]] | None = None,
    ) -> None:
        content = f"{title}\n\nЗапрос:\n{prompt}\n\nОтвет:\n{answer}"
        content += "\n\nThinking:\n" + self._format_thinking_notes(thinking_notes)
        if agent_log:
            content += "\n\nAgent Log:\n" + "\n".join(self._compact_agent_log(agent_log))
        data = content.encode("utf-8")

        def make_buf() -> io.BytesIO:
            buf = io.BytesIO(data)
            buf.name = "openagent_answer.txt"
            return buf

        caption = f"{title}\n\n<b>Ответ слишком длинный, отправляю файлом.</b>"
        last_error: Exception | None = None
        if hasattr(event, "edit"):
            try:
                await event.edit(
                    caption,
                    file=make_buf(),
                    buttons=buttons,
                    parse_mode="html",
                )
            except Exception as exc:
                last_error = exc
            else:
                return
        error = f"\n\n<code>{html.escape(str(last_error)[:500])}</code>" if last_error else ""
        fallback = html.escape(content[:3000])
        await self.edit(
            event,
            f"{caption}\n\n<b>Не удалось прикрепить файл к форме, показываю начало:</b>{error}\n\n<blockquote expandable>{fallback}</blockquote>",
            as_html=True,
        )

    async def _reply_text(
        self,
        event: Any,
        text: str,
        *,
        title: str = "OpenAgent",
        prompt: str = "",
        agent_log: list[str] | None = None,
        thinking_notes: list[str] | None = None,
        buttons: list[list[Any]] | None = None,
        edit_current: bool = False,
    ) -> None:
        text = self._sanitize_answer(text or "")
        formatted = self._format_agent_markdown(text)
        formatted_prompt = self._format_agent_markdown(prompt or "")
        request_label = self._request_label(thinking_notes=thinking_notes)
        response_label = self._response_label(thinking_notes=thinking_notes)
        agent_log_html = self._agent_log_html(agent_log or [])
        if len(formatted) + len(formatted_prompt) + len(agent_log_html) > 3500:
            await self._send_answer_file(
                event,
                title,
                prompt,
                text or "",
                agent_log or [],
                thinking_notes,
                buttons,
            )
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
            with contextlib.suppress(Exception):
                setattr(loading, "_openagent_status_buttons", [[cancel_button]])
            with contextlib.suppress(Exception):
                setattr(loading, "_openagent_source_chat_id", payload.get("chat_id"))
        except Exception:
            loading = event

        started = time.monotonic()
        try:
            answer, agent_log, thinking_notes = await self._ask_agent(
                payload["full_prompt"],
                status_event=loading or event,
                source_event=event,
                attachments=payload.get("attachments") or [],
                cancel_token=cancel_token,
                started_at=started,
            )
            elapsed = time.monotonic() - started
            self._remember_context(payload.get("chat_id"), payload["full_prompt"], answer)
            await self._reply_text(
                loading or event,
                answer,
                title=self._response_title(
                    elapsed,
                    tool_count=len(agent_log),
                    thinking_notes=thinking_notes,
                ),
                prompt=payload["prompt"],
                agent_log=agent_log,
                thinking_notes=thinking_notes,
                buttons=self._final_buttons(
                    payload.get("chat_id"),
                    payload["prompt"],
                    payload["full_prompt"],
                    payload.get("attachments") or [],
                ),
                edit_current=True,
            )
            self._cancelled_generations.discard(cancel_token)
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
        loading = await self._start_inline_status(
            event,
            self._thinking_text(),
            [[cancel_button]],
        )
        started = time.monotonic()
        try:
            answer, agent_log, thinking_notes = await self._ask_agent(
                full_prompt,
                status_event=loading or event,
                source_event=event,
                attachments=attachments,
                cancel_token=cancel_token,
                started_at=started,
            )
            self._last_request_at = time.time()
            elapsed = time.monotonic() - started
            self._remember_context(getattr(event, "chat_id", None), full_prompt, answer)
            await self._reply_text(
                loading or event,
                answer,
                title=self._response_title(
                    elapsed,
                    tool_count=len(agent_log),
                    thinking_notes=thinking_notes,
                ),
                prompt=prompt,
                agent_log=agent_log,
                thinking_notes=thinking_notes,
                buttons=self._final_buttons(
                    getattr(event, "chat_id", None),
                    prompt,
                    full_prompt,
                    attachments,
                ),
                edit_current=True,
            )
            self._cancelled_generations.discard(cancel_token)
        except Exception as exc:
            self._cancelled_generations.discard(cancel_token)
            await self.kernel.handle_error(exc, source="OpenAgent", event=event)
            await self.edit(
                loading or event,
                html.escape(self.strings("error", error=str(exc))),
                as_html=True,
            )

    @command("skills", doc_ru="список скиллов OpenAgent", doc_en="list OpenAgent skills")
    async def cmd_skills(self, event: events.NewMessage.Event) -> None:
        arg = self._args_raw(event)
        if arg in {"-repo", "--repo", "repo"}:
            try:
                text = await self._format_skill_repo_list()
            except Exception as exc:
                await self.edit(event, html.escape(self.strings("error", error=str(exc))), as_html=True)
                return
            await self.edit(event, "<pre>" + html.escape(text) + "</pre>", as_html=True)
            return

        skills = self._list_skills()
        if not skills:
            await self.edit(event, "No OpenAgent skills installed")
            return
        lines = []
        for path in skills:
            try:
                text = path.read_text(encoding="utf-8")
                first_line = text.splitlines()[0] if text.splitlines() else ""
                frontmatter_name = re.search(r"^name:\s*(.+)$", text, flags=re.MULTILINE)
                frontmatter_description = re.search(r"^description:\s*(.+)$", text, flags=re.MULTILINE)
            except Exception:
                first_line = ""
                frontmatter_name = None
                frontmatter_description = None
            name = frontmatter_name.group(1).strip() if frontmatter_name else self._skill_name_from_path(path)
            title = frontmatter_description.group(1).strip() if frontmatter_description else first_line.lstrip("# ").strip() if first_line.startswith("#") else name
            lines.append(f"- {name}: {title}")
        await self.edit(event, "<pre>" + html.escape("\n".join(lines)) + "</pre>", as_html=True)

    @command("skillinstall", alias=["ssinstall"], doc_ru="<name> установить OpenAgent skill из repo", doc_en="<name> install OpenAgent skill from repo")
    async def cmd_skillinstall(self, event: events.NewMessage.Event) -> None:
        name = self._args_raw(event)
        if not name:
            await self.edit(event, "Usage: .skillinstall <skill_name>")
            return
        try:
            saved_name = await self._install_repo_skill(name)
        except Exception as exc:
            await self.edit(event, html.escape(self.strings("error", error=str(exc))), as_html=True)
            return
        await self.edit(event, f"Skill installed: <code>{html.escape(saved_name)}</code>", as_html=True)

    @command("sendss", doc_ru="<name> отправить .md скилл", doc_en="<name> send skill .md")
    async def cmd_sendss(self, event: events.NewMessage.Event) -> None:
        name = self._args_raw(event)
        if not name:
            await self.edit(event, "Usage: .sendss <skill_name>")
            return
        path = self._find_skill_path(name)
        if not path.exists():
            await self.edit(event, "Skill not found")
            return
        await self.client.send_file(
            event.chat_id,
            str(path),
            caption=f"<b>Skill:</b> <code>{html.escape(self._skill_name_from_path(path))}</code>",
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

        saved_name = self._save_skill(name, content)
        await self.edit(event, f"Skill imported: <code>{html.escape(saved_name)}</code>", as_html=True)

    @command("delss", doc_ru="<name> удалить скилл", doc_en="<name> delete skill")
    async def cmd_delss(self, event: events.NewMessage.Event) -> None:
        name = self._args_raw(event)
        if not name:
            await self.edit(event, "Usage: .delss <skill_name>")
            return
        path = self._find_skill_path(name)
        if not path.exists():
            await self.edit(event, "Skill not found")
            return
        path.unlink()
        try:
            if path.name == "SKILL.md" and not any(path.parent.iterdir()):
                path.parent.rmdir()
        except Exception:
            pass
        await self.edit(event, f"Skill deleted: <code>{html.escape(self._skill_name_from_path(path))}</code>", as_html=True)


    # ── Plugin manager ──

    @command("oaplugin", doc_ru="управление плагинами OpenAgent", doc_en="manage OpenAgent plugins")
    async def cmd_oaplugin(self, event: events.NewMessage.Event) -> None:
        """Show plugin manager or install a plugin from replied .py file."""
        if await event.get_reply_message():
            try:
                saved_name = await self._install_plugin_from_reply(event)
            except Exception as exc:
                await self.edit(event, f"Plugin install failed: <code>{html.escape(str(exc))}</code>", as_html=True)
                return
            await self.edit(event, f"Plugin installed: <code>{html.escape(saved_name)}</code>", as_html=True)
            return

        installed = self._plugins
        text = "<b>🧩 Включёные плагины:</b>\n"
        if not installed:
            text += "\nНет установленных плагинов\n"
        else:
            for pname, plugin in installed.items():
                desc = getattr(plugin, "description", "?") or "?"
                author = getattr(plugin, "author", "?") or "?"
                text += f"<blockquote>{pname} - {desc} | by {author}</blockquote>\n"
        text += f"\n<b>Всего плагинов:</b> {len(installed)}"

        buttons = [[
            self.Button.inline("📦 Каталог", self._oaplugin_catalog, args=(0,)),
            self.Button.inline("⚙️ Менеджер", self._oaplugin_manager, args=(0,)),
        ], [
            self.Button.inline("❌ Закрыть", self._oaplugin_close),
        ]]

        chat_id = getattr(event, "chat_id", None)
        if chat_id:
            try:
                await self.inline(chat_id, text, buttons=buttons, ttl=900, parse_mode="html")
                await event.delete()
            except Exception:
                await self.edit(event, text, as_html=True)
        else:
            await self.edit(event, text, as_html=True)

    @callback(ttl=900)
    async def _oaplugin_close(self, call: events.CallbackQuery.Event) -> None:
        try:
            await call.delete()
        except Exception:
            await call.answer()

    @callback(ttl=900)
    async def _oaplugin_catalog(self, call: events.CallbackQuery.Event, page: int = 0) -> None:
        """Show available plugins from repo (xheta-style)."""
        plugins = self._plugins_cache
        if not plugins:
            plugins = await self._fetch_repo_plugins()
        if not plugins:
            await call.answer("❌ Нет плагинов в репозитории", alert=True)
            return
        if page < 0 or page >= len(plugins):
            await call.answer()
            return
        m = plugins[page]
        name = m.get("name", "?")
        author = m.get("author", "?")
        version = m.get("version", "?")
        desc = m.get("description", "Нет описания")
        tools = m.get("tools", [])
        fname = m.get("file_name", "")
        installed = fname.replace(".py", "") in {p.name for p in self._plugins.values()}

        text = f"📦 <b>{name}</b> v{version} by <code>{author}</code>\n\n"
        text += f"📝 {desc}\n"
        if tools:
            tools_str = ", ".join(f"<code>{t}</code>" for t in tools[:8])
            if len(tools) > 8:
                tools_str += f" ...и ещё {len(tools) - 8}"
            text += f"\n🔧 <b>Tools:</b> {tools_str}"
        text += f"\n\n🔢 {page + 1}/{len(plugins)}"

        buttons = []
        raw_url = m.get("download_url", "")
        if installed:
            buttons.append([self.Button.inline("✅ Установлен", self._oaplugin_noop)])
        else:
            buttons.append([self.Button.inline("📥 Установить", self._oaplugin_install, args=(fname.replace(".py", ""), page))])
        if raw_url:
            buttons[0].append(self.Button.url("📄 Код", raw_url))

        nav = []
        if page > 0:
            nav.append(self.Button.inline("⬅️", self._oaplugin_catalog, args=(page - 1,)))
        nav.append(self.Button.inline(f"📋 {page + 1}/{len(plugins)}", self._oaplugin_noop))
        if page < len(plugins) - 1:
            nav.append(self.Button.inline("➡️", self._oaplugin_catalog, args=(page + 1,)))
        if nav:
            buttons.append(nav)
        buttons.append([self.Button.inline("🔙 Назад", self._oaplugin_main)])

        try:
            await call.edit(text, buttons=buttons, parse_mode="html")
        except Exception:
            pass

    @callback(ttl=900)
    async def _oaplugin_noop(self, call: events.CallbackQuery.Event) -> None:
        await call.answer()

    @callback(ttl=900)
    async def _oaplugin_main(self, call: events.CallbackQuery.Event) -> None:
        """Return to main plugin page."""
        installed = self._plugins
        text = "<b>🧩 Включёные плагины:</b>\n"
        if not installed:
            text += "\nНет установленных плагинов\n"
        else:
            for pname, plugin in installed.items():
                desc = getattr(plugin, "description", "?") or "?"
                author = getattr(plugin, "author", "?") or "?"
                text += f"<blockquote>{pname} - {desc} | by {author}</blockquote>\n"
        text += f"\n<b>Всего плагинов:</b> {len(installed)}"
        buttons = [[
            self.Button.inline("📦 Каталог", self._oaplugin_catalog, args=(0,)),
            self.Button.inline("⚙️ Менеджер", self._oaplugin_manager, args=(0,)),
        ], [
            self.Button.inline("❌ Закрыть", self._oaplugin_close),
        ]]
        try:
            await call.edit(text, buttons=buttons, parse_mode="html")
        except Exception:
            pass

    @callback(ttl=900)
    async def _oaplugin_install(self, call: events.CallbackQuery.Event, name: str, page: int = 0) -> None:
        """Download and install a plugin from repo."""
        await call.answer("⏳ Устанавливаю...", alert=False)
        try:
            saved_name = await self._install_plugin_from_repo(name)
            await call.answer(f"✅ {saved_name} установлен!", alert=True)
        except Exception as exc:
            await call.answer(f"❌ Ошибка: {exc}", alert=True)
            return
        plugins = self._plugins_cache
        if plugins and page < len(plugins):
            await self._oaplugin_catalog(call, page)
        else:
            await self._oaplugin_catalog(call, 0)

    @callback(ttl=900)
    async def _oaplugin_manager(self, call: events.CallbackQuery.Event, page: int = 0) -> None:
        """Show installed plugins with delete option."""
        installed = list(self._plugins.values())
        if not installed:
            await call.answer("Нет установленных плагинов", alert=True)
            return
        if page < 0 or page >= len(installed):
            await call.answer()
            return
        plugin = installed[page]
        text = f"<b>⚙️ {plugin.name}</b>\n"
        text += f"Версия: {getattr(plugin, 'version', '?')}\n"
        text += f"Tools: {len(getattr(plugin, 'tool_registry', ()))}\n\n"
        text += "<b>Действия:</b>"
        row1 = [self.Button.inline("🗑 Удалить", self._oaplugin_uninstall, args=(plugin.name, page))]
        buttons = [row1]
        if len(installed) > 1:
            nav = []
            if page > 0:
                nav.append(self.Button.inline("⬅️", self._oaplugin_manager, args=(page - 1,)))
            nav.append(self.Button.inline(f"{page + 1}/{len(installed)}", self._oaplugin_noop))
            if page < len(installed) - 1:
                nav.append(self.Button.inline("➡️", self._oaplugin_manager, args=(page + 1,)))
            buttons.append(nav)
        buttons.append([self.Button.inline("🔙 Назад", self._oaplugin_main)])
        try:
            await call.edit(text, buttons=buttons, parse_mode="html")
        except Exception:
            pass

    @callback(ttl=900)
    async def _oaplugin_uninstall(self, call: events.CallbackQuery.Event, name: str, page: int = 0) -> None:
        """Delete a plugin."""
        try:
            name = str(name or "").strip().lower()
            fpath = self._plugin_files.get(name)
            self._unregister_plugin(name)
            plugins_dir = self._resolve_plugins_dir()
            if fpath and fpath.exists():
                try:
                    fpath.relative_to(plugins_dir)
                    fpath.unlink()
                except ValueError:
                    pass
            for extra in (plugins_dir / f"{name}.py", plugins_dir / f"{name}_plugin.py"):
                if extra.exists():
                    extra.unlink()
            await call.answer(f"🗑 {name} удалён", alert=True)
        except Exception as exc:
            await call.answer(f"❌ Ошибка: {exc}", alert=True)
            return
        await self._oaplugin_manager(call, min(page, len(self._plugins) - 1) if self._plugins else 0)

    def _tool_attr_or_body(self, attrs_raw: str, body: str, *keys: str) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        for key in keys:
            value = attrs.get(key)
            if value:
                return value.strip()
        return (body or "").strip()


    async def _skills_registry_tool(self, tool_name: str, attrs_raw: str, body: str) -> str:
        await asyncio.sleep(0)
        attrs = self._parse_xml_attrs(attrs_raw)
        if tool_name == "skills.list":
            skills = self._list_skills()
            return "\n".join(self._skill_name_from_path(path) for path in skills) or "No OpenAgent skills installed"
        if tool_name == "skills.repo_list":
            return await self._format_skill_repo_list()
        if tool_name == "skills.install":
            name = attrs.get("name") or body.strip()
            if not name:
                return "skill name is required"
            saved = await self._install_repo_skill(name)
            return f"Skill installed: {saved}"
        if tool_name == "skills.activate":
            query = attrs.get("query") or attrs.get("name") or body.strip()
            return self._activate_skill_text(query)
        if tool_name in {"skills.read", "skills.export_md"}:
            name = attrs.get("name") or body.strip()
            if not name:
                return "skill name is required"
            path = self._find_skill_path(name)
            if not path.exists():
                return "Skill not found"
            return path.read_text(encoding="utf-8", errors="replace")[:12000]
        if tool_name in {"skills.save_from_ai", "skills.import_md", "skill.save", "skill"}:
            name = attrs.get("name") or attrs.get("title") or "skill"
            if not body.strip():
                return "skill content is empty"
            saved = self._save_skill(name, body)
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
        await asyncio.sleep(0)
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

    async def _todo_registry_tool(self, tool_name: str, attrs_raw: str, body: str) -> str:
        await asyncio.sleep(0)
        attrs = self._parse_xml_attrs(attrs_raw)
        items = self._todo_items()

        if tool_name == "todo.add":
            text = (
                attrs.get("text")
                or attrs.get("task")
                or attrs.get("item")
                or attrs.get("title")
                or body.strip()
            )
            text = self._todo_parse_html_text(text)
            if not text:
                return "todo text is required"
            status = self._todo_normalize_status(attrs.get("status") or attrs.get("state") or "pending")
            items.append({"text": text[:500], "status": status})
            await self._save_todo_items(items)
            return "TODO item added\n" + self._format_todo_placeholder()

        if tool_name == "todo.closeall":
            if not items:
                return "TODO list is empty"
            for item in items:
                item["status"] = "closed"
            await self._save_todo_items(items)
            return "All TODO items closed\n" + self._format_todo_placeholder()

        if tool_name == "todo.clear":
            if not items:
                return "TODO list is already empty"
            await self._save_todo_items([])
            return "TODO list cleared"

        if tool_name == "todo.current":
            idx, error = self._todo_target_index(items, attrs, body)
            if idx is None:
                return error
            for i, item in enumerate(items):
                if item.get("status") == "open" and i != idx:
                    item["status"] = "pending"
            items[idx]["status"] = "open"
            await self._save_todo_items(items)
            return f"Current TODO: {items[idx]['text']}\n" + self._format_todo_placeholder()

        if tool_name == "todo.delete":
            idx, error = self._todo_target_index(items, attrs, body)
            if idx is None:
                return error
            removed = items.pop(idx)
            await self._save_todo_items(items)
            return f"TODO deleted: {removed['text']}\n" + self._format_todo_placeholder()

        if tool_name == "todo.close":
            idx, error = self._todo_target_index(items, attrs, body)
            if idx is None:
                return error
            items[idx]["status"] = "closed"
            await self._save_todo_items(items)
            return f"TODO closed: {items[idx]['text']}\n" + self._format_todo_placeholder()

        if tool_name == "todo.edit":
            target_body = body
            new_text = (
                attrs.get("new")
                or attrs.get("value")
                or attrs.get("text")
                or ""
            ).strip()
            if not attrs.get("index") and "|" in (body or ""):
                target_part, new_part = body.split("|", 1)
                target_body = target_part.strip()
                if not new_text:
                    new_text = new_part.strip()
            idx, error = self._todo_target_index(items, attrs, target_body)
            if idx is None:
                return error
            if not new_text:
                return "new todo text is required"
            parsed_text = self._todo_parse_html_text(new_text)
            if not parsed_text:
                return "new todo text is empty"
            items[idx]["text"] = parsed_text[:500]
            if attrs.get("status") or attrs.get("state"):
                items[idx]["status"] = self._todo_normalize_status(attrs.get("status") or attrs.get("state") or "")
            await self._save_todo_items(items)
            return f"TODO updated: {items[idx]['text']}\n" + self._format_todo_placeholder()

        return f"Unknown todo tool: {tool_name}"

    async def _thinking_note_tool(self, attrs_raw: str, body: str) -> str:
        await asyncio.sleep(0)
        # Detect when the model incorrectly put a real tool call inside the note body.
        # Surface an actionable error so the retry loop corrects the format.
        raw_body = (body or "").strip()
        embedded = self._extract_json_tool_calls(raw_body)
        real_embedded = [c for c in embedded if c[0] != "thinking.note"]
        if real_embedded:
            names = ", ".join(c[0] for c in real_embedded)
            return (
                f"[FORMAT ERROR] Tool call(s) found inside thinking.note body: {names}. "
                "The embedded tool(s) were NOT executed. "
                "Emit each tool as its own separate ```tool_call``` block. "
                "thinking.note must contain plain text only, never JSON tool calls."
            )
        note = self._thinking_note_text(attrs_raw, body)
        if not note:
            return "Thinking note recorded."
        return "Thinking note: " + note[:1200]

    def _thinking_note_text(self, attrs_raw: str, body: str) -> str:
        attrs = self._parse_xml_attrs(attrs_raw)
        text = (body or attrs.get("text") or attrs.get("note") or "").strip()
        text = html.unescape(text).strip()
        text = re.sub(r"^❔\s*", "", text).strip()
        text = re.sub(r"</?tool_call>", "", text, flags=re.I).strip()
        fenced = self.TOOL_CALL_JSON_RE.search(text)
        if fenced:
            text = fenced.group(1).strip()
        else:
            text = re.sub(r"^```(?:tool_call|json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()

        json_text = text
        if not json_text.startswith("{"):
            start = json_text.find("{")
            if start >= 0:
                json_text = json_text[start:]
        if json_text.startswith("{"):
            try:
                payload, _end = json.JSONDecoder().raw_decode(json_text)
                if isinstance(payload, dict):
                    args = payload.get("args") or {}
                    if isinstance(args, dict):
                        text = str(
                            args.get("note")
                            or args.get("text")
                            or payload.get("note")
                            or payload.get("text")
                            or text
                        ).strip()
                    else:
                        text = str(payload.get("note") or payload.get("text") or text).strip()
            except Exception:
                pass
        return text


    def _get_tool_map(self) -> dict[str, str]:
        """Unified mapping of tool tags to internal methods. Merges core + plugin maps.

        Cached after first build; invalidated by _register_plugin / _unregister_plugin.
        """
        if getattr(self, "_tool_map_cache", None) is not None:
            return self._tool_map_cache  # type: ignore[return-value]
        core = {
            # Core tools tightly coupled with module internals.
            "thinking.note": "_thinking_note_tool",
            "skill": "_save_skill",
            "skill.save": "_save_skill",
            "skills.list": "_skills_registry_tool",
            "skills.read": "_skills_registry_tool",
            "skills.activate": "_skills_registry_tool",
            "skills.import_md": "_skills_registry_tool",
            "skills.export_md": "_skills_registry_tool",
            "skills.save_from_ai": "_skills_registry_tool",
            "skills.install": "_skills_registry_tool",
            "skills.repo_list": "_skills_registry_tool",
            "code.generate_file": "_code_registry_tool",
            "code.generate_mcub_module": "_code_registry_tool",
            "code.choose_filename": "_code_registry_tool",
            "code.attach_result": "_code_registry_tool",
            "code.read_docs": "_fetch_mcub_docs",
            "context.remember": "_context_registry_tool",
            "context.clear": "_context_registry_tool",
            "context.regenerate": "_context_registry_tool",
            "context.reply_context": "_context_registry_tool",
            "context.media_context": "_context_registry_tool",
            "todo.add": "_todo_registry_tool",
            "todo.delete": "_todo_registry_tool",
            "todo.edit": "_todo_registry_tool",
            "todo.current": "_todo_registry_tool",
            "todo.close": "_todo_registry_tool",
            "todo.closeall": "_todo_registry_tool",
            "todo.clear": "_todo_registry_tool",
            "utility.token_usage": "_utility_registry_tool",
            "utility.placeholders": "_utility_registry_tool",
            "utility.random_template": "_utility_registry_tool",
            "utility.agent_log": "_utility_registry_tool",
            "utility.error_file": "_utility_registry_tool",
        }

        for plugin in self._plugins.values():
            for tname, handler in getattr(plugin, "tool_map", {}).items():
                if not tname or not handler:
                    continue
                core[str(tname).strip().lower()] = str(handler).strip()
        self._tool_map_cache: dict[str, str] = core
        return core

    async def _dispatch_tool(
        self,
        name: str,
        attrs_raw: str,
        body: str,
        source_event: Any,
        status_event: Any,
        agent_log: list[str],
        *,
        started_at: float | None = None,
        thinking_notes: list[str] | None = None,
    ) -> str:
        name = name.lower().strip()
        tmap = self._get_tool_map()
        # Plugin dispatch handles aliases via tool_map.
        
        # 1. Direct match or alias
        method_name = tmap.get(name)
        

        
        handler_method = None
        plugin_owner: "OpenAgentPlugin | None" = None
        
        # Check plugin handlers first. Exact tool_map ownership supports
        # legacy aliases like web_search/send_message/dialogs too.
        plugin_owner = self._get_plugin_for_tool(name)
        if plugin_owner:
            if method_name and hasattr(plugin_owner, method_name):
                handler_method = getattr(plugin_owner, method_name)
            else:
                pmap = getattr(plugin_owner, "tool_map", {})
                p_handler = pmap.get(name)
                if p_handler:
                    handler_method = getattr(plugin_owner, p_handler, None)
        if not handler_method and method_name:
            handler_method = getattr(self, method_name, None)
        if not handler_method:
            candidates = sorted(self._tool_names())
            nearest = ", ".join(difflib.get_close_matches(name, candidates, n=5, cutoff=0.45))
            suggestion = f" Closest matches: {nearest}." if nearest else ""
            return f"Error: Tool <{name}> not found in registry.{suggestion}"

        agent_log.append(name)
        if name == "thinking.note" and thinking_notes is not None:
            note = self._thinking_note_text(attrs_raw, body)
            if note:
                thinking_notes.append(note[:1200])
        display_value = "" if name == "thinking.note" else (attrs_raw or body)
        if self._requires_tool_confirmation(name, attrs_raw, body):
            if not status_event:
                return f"Tool <{name}> was not executed: user confirmation is required."
            elapsed = time.monotonic() - started_at if started_at is not None else None
            approved = await self._confirm_dangerous_tool(
                status_event,
                name,
                display_value,
                elapsed=elapsed,
            )
            if not approved:
                return f"Tool <{name}> was cancelled by the user. Do not retry it unless the user explicitly asks."
        if status_event:
            elapsed = time.monotonic() - started_at if started_at is not None else None
            await self._show_agent_action(
                status_event,
                f"Executing {name}...",
                display_value,
                agent_log,
                tool_name=name,
                elapsed=elapsed,
                thinking_notes=thinking_notes,
            )
            
        try:
            # Normalize arguments based on method signature
            sig = inspect.signature(handler_method)
            params = sig.parameters
            # Parse XML attrs once; reused for mode/target/mcub/skill branches below.
            attrs = self._parse_xml_attrs(attrs_raw)

            kwargs = {}
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
                    kwargs["mode"] = body.strip() or attrs.get("mode") or "private"
            if "target" in params: kwargs["target"] = body.strip() or attrs.get("target", "")
            
            if method_name == "_run_mcub_command" and not kwargs.get("command"):
                command_map = {
                    "mcub.modules": "modules",
                    "mcub.config": "cfg",
                    "mcub.install": "dlm",
                    "mcub.reload": "restart",
                }
                kwargs["command"] = (
                    command_map.get(name, "")
                    or attrs.get("command")
                    or attrs.get("cmd")
                    or attrs.get("text")
                    or attrs.get("query")
                    or ""
                )
                result = await handler_method(**kwargs)
            elif method_name == "_save_skill":
                result = await self._skills_registry_tool(name, attrs_raw, body or attrs.get("content", ""))
            else:
                result = await handler_method(**kwargs)

            if status_event and name.startswith("todo."):
                elapsed = time.monotonic() - started_at if started_at is not None else None
                await self._show_agent_action(
                    status_event,
                    f"Updated {name}",
                    result,
                    agent_log,
                    tool_name=name,
                    elapsed=elapsed,
                    thinking_notes=thinking_notes,
                )
            return result
        except Exception as e:
            err_type = type(e).__name__
            details = str(e).strip() or "no details"
            return (
                f"Tool <{name}> execution failed.\n"
                f"Error type: {err_type}\n"
                f"Details: {details[:1200]}\n"
                "Fix args and retry with a corrected tool call."
            )
