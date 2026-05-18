# scop: inline
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path
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
        attrs = self.agent._parse_xml_attrs(attrs_raw)
        path_str = attrs.get("path") or attrs.get("file") or body.strip()
        caption = attrs.get("caption") or ""
        chat = await self.agent._resolve_tool_chat(attrs.get("chat") or attrs.get("to"), source_event)
        if not path_str:
            return "File path is required"
        fpath = Path(path_str).expanduser()
        if not fpath.is_absolute():
            fpath = Path.cwd() / fpath
        if not fpath.is_file():
            return f"File not found: {fpath}"
        try:
            await self.agent.client.send_file(chat, str(fpath), caption=caption or None)
            return f"File sent: {fpath.name}"
        except Exception as exc:
            return f"Send failed: {exc}"

    async def cmd_download(self, attrs_raw: str, body: str, source_event: Any) -> str:
        import io
        attrs = self.agent._parse_xml_attrs(attrs_raw)
        msg_id = attrs.get("message") or attrs.get("msg") or body.strip()
        chat = await self.agent._resolve_tool_chat(attrs.get("chat") or attrs.get("from"), source_event)
        try:
            if msg_id and msg_id.isdigit():
                msg = await self.agent.client.get_messages(chat, ids=int(msg_id))
            else:
                msg = await source_event.get_reply_message() if source_event else None
            if not msg or not msg.media:
                return "No media found"
            data = await msg.download_media(file=bytes)
            if data is None:
                return "Download returned no data"
            size_mb = len(data) / (1024 * 1024)
            return f"Downloaded: {size_mb:.2f} MB. Format: {type(data).__name__}"
        except Exception as exc:
            return f"Download failed: {exc}"

    async def cmd_read_text(self, attrs_raw: str, body: str) -> str:
        attrs = self.agent._parse_xml_attrs(attrs_raw)
        path_raw = body.strip() or attrs.get("path") or attrs.get("file") or attrs.get("name") or ""
        if not path_raw:
            return "File path is required"
        fpath = Path(path_raw).expanduser()
        if not fpath.is_absolute():
            fpath = Path.cwd() / fpath
        try:
            if not fpath.is_file():
                return f"File not found: {fpath}"
            return fpath.read_text(encoding="utf-8", errors="replace")[:12000]
        except Exception as exc:
            return f"Read failed: {exc}"
