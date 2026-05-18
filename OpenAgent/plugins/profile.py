# scop: inline
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any


class ProfilePlugin:
    name = "profile"
    version = "0.1.0"
    author = "@dev_dolbaeb"
    description = "Telegram profile tools"

    tool_registry = (
        "profile.get", "profile.get_full", "profile.get_me", "profile.update_name", "profile.update_bio",
        "profile.update_username", "profile.set_photo", "profile.download_photo", "profile.get_photos", "profile.common_chats",
    )

    tool_map = {
        "profile": "cmd_profile",
        "profile.get": "cmd_profile",
        "profile.get_full": "cmd_profile",
        "profile.get_me": "cmd_misc",
        "profile.get_photos": "cmd_misc",
        "profile.common_chats": "cmd_misc",
        "profile.download_photo": "cmd_misc",
        "update_profile": "cmd_update",
        "profile.update": "cmd_update",
        "profile.update_name": "cmd_update",
        "profile.update_bio": "cmd_update",
        "profile.update_username": "cmd_update",
        "set_profile_photo": "cmd_set_photo",
        "profile.set_photo": "cmd_set_photo",
    }

    _MISC = {
        "profile.get_me": "get_me",
        "profile.get_photos": "get_profile_photos",
        "profile.common_chats": "get_common_chats",
        "profile.download_photo": "get_profile_photos",
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def cmd_profile(self, attrs_raw: str, body: str, source_event: Any) -> str:
        attrs = self.agent._parse_xml_attrs(attrs_raw)
        target = body.strip() or attrs.get("target") or attrs.get("user") or ""
        return await self.agent._profile_tool(target, source_event)

    async def cmd_update(self, attrs_raw: str, body: str) -> str:
        return await self.agent._update_profile_tool(attrs_raw, body)

    async def cmd_set_photo(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._set_profile_photo_tool(attrs_raw, body, source_event)

    async def cmd_misc(self, tool_name: str, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._misc_tool(self._MISC.get(tool_name, tool_name), attrs_raw, body, source_event)
