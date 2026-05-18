# scop: inline
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any


class FilePlugin:
    name = "file"
    version = "0.1.0"
    author = "@dev_dolbaeb"
    description = "File send/read/download tools"

    tool_registry = (
        "file.send",
        "file.download_media",
        "file.read_text",
    )

    tool_map = {
        "send_file": "cmd_send",
        "file.send": "cmd_send",
        "download_media": "cmd_download",
        "file.download": "cmd_download",
        "file.download_media": "cmd_download",
        "file.read_text": "cmd_read_text",
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def cmd_send(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._send_file_tool(attrs_raw, body, source_event)

    async def cmd_download(self, attrs_raw: str, body: str, source_event: Any) -> str:
        return await self.agent._download_media_tool(attrs_raw, body, source_event)

    async def cmd_read_text(self, attrs_raw: str, body: str) -> str:
        return await self.agent._file_read_text_tool(attrs_raw, body)
