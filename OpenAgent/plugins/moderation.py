# scop: inline
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any


class ModerationPlugin:
    name = "moderation"
    version = "0.1.0"
    author = "@dev_dolbaeb"
    description = "Telegram moderation tools"

    tool_registry = (
        "moderation.mute", "moderation.unmute", "moderation.ban", "moderation.unban", "moderation.kick",
        "moderation.promote", "moderation.demote", "moderation.pin", "moderation.delete_messages", "moderation.get_admins",
    )

    tool_map = {
        "mute_user": "cmd_mute",
        "chat.mute": "cmd_mute",
        "moderation.mute": "cmd_mute",
        "unmute_user": "cmd_unmute",
        "chat.unmute": "cmd_unmute",
        "moderation.unmute": "cmd_unmute",
        "ban_user": "cmd_ban",
        "chat.ban": "cmd_ban",
        "moderation.ban": "cmd_ban",
        "unban_user": "cmd_unban",
        "chat.unban": "cmd_unban",
        "moderation.unban": "cmd_unban",
        "kick_user": "cmd_kick",
        "chat.kick": "cmd_kick",
        "moderation.kick": "cmd_kick",
        "promote_user": "cmd_promote",
        "chat.promote": "cmd_promote",
        "moderation.promote": "cmd_promote",
        "demote_user": "cmd_demote",
        "chat.demote": "cmd_demote",
        "moderation.demote": "cmd_demote",
        "moderation.pin": "cmd_pin",
        "moderation.delete_messages": "cmd_delete",
        "moderation.get_admins": "cmd_admins",
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def cmd_mute(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._mute_user_tool(attrs_raw, body, source_event)

    async def cmd_unmute(self, attrs_raw: str, source_event: Any) -> str:
        return await self.agent._unmute_user_tool(attrs_raw, source_event)

    async def cmd_ban(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._ban_user_tool(attrs_raw, body, source_event)

    async def cmd_unban(self, attrs_raw: str, source_event: Any) -> str:
        return await self.agent._unban_user_tool(attrs_raw, source_event)

    async def cmd_kick(self, attrs_raw: str, source_event: Any) -> str:
        return await self.agent._kick_user_tool(attrs_raw, source_event)

    async def cmd_promote(self, attrs_raw: str, source_event: Any) -> str:
        return await self.agent._promote_user_tool(attrs_raw, source_event)

    async def cmd_demote(self, attrs_raw: str, source_event: Any) -> str:
        return await self.agent._demote_user_tool(attrs_raw, source_event)

    async def cmd_pin(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._pin_message_tool(attrs_raw, body, source_event)

    async def cmd_delete(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._delete_messages_tool(attrs_raw, body, source_event)

    async def cmd_admins(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._misc_tool("get_admins", attrs_raw, body, source_event)
