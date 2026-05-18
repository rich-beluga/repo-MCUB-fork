# scop: inline
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any


class ContactsPlugin:
    name = "contacts"
    version = "0.1.0"
    author = "@dev_dolbaeb"
    description = "Telegram contacts tools"

    tool_registry = (
        "contacts.add",
        "contacts.delete",
        "contacts.block",
        "contacts.unblock",
        "contacts.entity",
    )

    tool_map = {
        "contacts.add": "cmd_misc",
        "contacts.delete": "cmd_misc",
        "contacts.block": "cmd_misc",
        "contacts.unblock": "cmd_misc",
        "contacts.entity": "cmd_misc",
    }

    _MISC = {
        "contacts.add": "add_contact",
        "contacts.delete": "delete_contact",
        "contacts.block": "block_user",
        "contacts.unblock": "unblock_user",
        "contacts.entity": "get_entity",
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def cmd_misc(self, tool_name: str, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._misc_tool(self._MISC.get(tool_name, tool_name), attrs_raw, body, source_event)
