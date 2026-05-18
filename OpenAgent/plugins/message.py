# scop: inline
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any


class MessagePlugin:
    name = "message"
    version = "0.1.0"
    author = "@dev_dolbaeb"
    description = "Telegram message tools"

    tool_registry = (
        "message.send_current", "message.send_target", "message.reply", "message.edit", "message.forward",
        "message.delete", "message.pin", "message.react", "message.get", "message.search",
        "message.history", "message.mark_read", "message.typing", "message.schedule", "message.draft",
    )

    tool_map = {
        "send_message": "cmd_send",
        "message.send": "cmd_send",
        "message.send_current": "cmd_send",
        "message.send_target": "cmd_send",
        "history": "cmd_history",
        "message.history": "cmd_history",
        "search_messages": "cmd_search",
        "message.search": "cmd_search",
        "message.delete": "cmd_delete",
        "delete_messages": "cmd_delete",
        "message.forward": "cmd_forward",
        "forward_message": "cmd_forward",
        "message.pin": "cmd_pin",
        "pin_message": "cmd_pin",
        "message.edit": "cmd_misc",
        "message.reply": "cmd_misc",
        "message.react": "cmd_misc",
        "message.get": "cmd_misc",
        "message.mark_read": "cmd_misc",
        "message.typing": "cmd_misc",
        "message.schedule": "cmd_misc",
        "message.draft": "cmd_misc",
    }

    _MISC = {
        "message.edit": "edit_message",
        "message.reply": "reply_message",
        "message.react": "react_message",
        "message.get": "get_message",
        "message.mark_read": "mark_read",
        "message.typing": "typing",
        "message.schedule": "schedule_message",
        "message.draft": "save_draft",
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def cmd_send(self, tool_name: str, attrs_raw: str, body: str, source_event: Any) -> str:
        attrs = self.agent._parse_xml_attrs(attrs_raw)
        chat = attrs.get("chat") or attrs.get("to") or attrs.get("target")
        if tool_name == "message.send_current":
            chat = None
        message = body.strip() or attrs.get("message") or attrs.get("text") or ""
        return await self.agent._send_userbot_message(message, source_event, chat=chat)

    async def cmd_history(self, attrs_raw: str, source_event: Any) -> str:
        return await self.agent._history_tool(attrs_raw, source_event)

    async def cmd_search(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._search_messages_tool(attrs_raw, body, source_event)

    async def cmd_delete(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._delete_messages_tool(attrs_raw, body, source_event)

    async def cmd_forward(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._forward_message_tool(attrs_raw, body, source_event)

    async def cmd_pin(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._pin_message_tool(attrs_raw, body, source_event)

    async def cmd_misc(self, tool_name: str, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._misc_tool(self._MISC.get(tool_name, tool_name), attrs_raw, body, source_event)
