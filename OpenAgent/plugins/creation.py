# scop: inline
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any


class CreationPlugin:
    name = "creation"
    version = "0.1.0"
    author = "@dev_dolbaeb"
    description = "Telegram channel/group/bot creation tools"

    tool_registry = (
        "creation.channel",
        "creation.group",
        "creation.bot",
        "creation.private_invite",
    )

    tool_map = {
        "create_channel": "cmd_channel_or_group",
        "creation.channel": "cmd_channel_or_group",
        "create_group": "cmd_channel_or_group",
        "creation.group": "cmd_channel_or_group",
        "create_bot": "cmd_bot",
        "creation.bot": "cmd_bot",
        "join_chat": "cmd_join",
        "creation.private_invite": "cmd_join",
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def cmd_channel_or_group(self, tool_name: str, attrs_raw: str, body: str) -> str:
        kind = "group" if tool_name.endswith("group") else "channel"
        return await self.agent._create_channel_or_group(kind, attrs_raw, body)

    async def cmd_bot(self, attrs_raw: str, body: str) -> str:
        return await self.agent._create_bot_via_botfather(attrs_raw, body)

    async def cmd_join(self, attrs_raw: str, body: str) -> str:
        return await self.agent._join_chat_tool(attrs_raw, body)
