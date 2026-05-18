# scop: inline
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any


class DialogPlugin:
    name = "dialog"
    version = "0.1.0"
    author = "@dev_dolbaeb"
    description = "Telegram dialog listing and management tools"

    tool_registry = (
        "dialog.list_private", "dialog.list_groups", "dialog.list_all", "dialog.search", "dialog.archive",
        "dialog.unarchive", "dialog.leave", "dialog.export_invite", "dialog.get_photo", "dialog.set_photo",
    )

    tool_map = {
        "dialogs": "cmd_list",
        "dialog.list": "cmd_list",
        "dialog.list_private": "cmd_list",
        "dialog.list_groups": "cmd_list",
        "dialog.list_all": "cmd_list",
        "dialog.search": "cmd_misc",
        "dialog.archive": "cmd_misc",
        "dialog.unarchive": "cmd_misc",
        "dialog.leave": "cmd_misc",
        "dialog.export_invite": "cmd_misc",
        "dialog.get_photo": "cmd_misc",
        "dialog.set_photo": "cmd_misc",
    }

    _MISC = {
        "dialog.search": "search_dialogs",
        "dialog.archive": "archive_dialog",
        "dialog.unarchive": "unarchive_dialog",
        "dialog.leave": "leave_chat",
        "dialog.export_invite": "export_invite",
        "dialog.get_photo": "get_chat_photo",
        "dialog.set_photo": "set_chat_photo",
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def cmd_list(self, tool_name: str, attrs_raw: str, body: str) -> str:
        attrs = self.agent._parse_xml_attrs(attrs_raw)
        if tool_name == "dialog.list_groups":
            mode = "groups"
        elif tool_name == "dialog.list_all":
            mode = "all"
        else:
            mode = body.strip() or attrs.get("mode") or "private"
        return await self.agent._dialogs_tool(mode)

    async def cmd_misc(self, tool_name: str, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._misc_tool(self._MISC.get(tool_name, tool_name), attrs_raw, body, source_event)
