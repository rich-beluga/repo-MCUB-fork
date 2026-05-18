# scop: inline
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any


class ChatPlugin:
    name = "chat"
    version = "0.1.0"
    author = "@dev_dolbaeb"
    description = "Telegram chat information and settings tools"

    tool_registry = (
        "chat.info", "chat.participants", "chat.admins", "chat.permissions", "chat.common_with_user",
        "chat.set_title", "chat.set_about", "chat.set_username", "chat.slowmode", "chat.invite_link",
    )

    tool_map = {
        "chat": "cmd_chat",
        "chat.info": "cmd_chat",
        "chat.participants": "cmd_chat",
        "chat.search": "cmd_search",
        "chat.admins": "cmd_misc",
        "chat.permissions": "cmd_misc",
        "chat.common_with_user": "cmd_misc",
        "chat.set_username": "cmd_misc",
        "chat.invite_link": "cmd_misc",
        "set_slowmode": "cmd_slowmode",
        "chat.slowmode": "cmd_slowmode",
        "set_chat_title": "cmd_title",
        "chat.set_title": "cmd_title",
        "set_chat_about": "cmd_about",
        "chat.set_about": "cmd_about",
        "join_chat": "cmd_join",
    }

    _MISC = {
        "chat.admins": "get_admins",
        "chat.permissions": "get_permissions",
        "chat.common_with_user": "get_common_chats",
        "chat.set_username": "set_chat_username",
        "chat.invite_link": "export_invite",
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def cmd_chat(self, attrs_raw: str, body: str, source_event: Any) -> str:
        attrs = self.agent._parse_xml_attrs(attrs_raw)
        query = body.strip() or attrs.get("chat") or attrs.get("query") or ""
        return await self.agent._chat_tool(query, source_event)

    async def cmd_search(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._search_messages_tool(attrs_raw, body, source_event)

    async def cmd_slowmode(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._set_slowmode_tool(attrs_raw, body, source_event)

    async def cmd_title(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._set_chat_title_tool(attrs_raw, body, source_event)

    async def cmd_about(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._set_chat_about_tool(attrs_raw, body, source_event)

    async def cmd_join(self, attrs_raw: str, body: str) -> str:
        return await self.agent._join_chat_tool(attrs_raw, body)

    async def cmd_misc(self, tool_name: str, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._misc_tool(self._MISC.get(tool_name, tool_name), attrs_raw, body, source_event)
