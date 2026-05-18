# scop: inline
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any


class WebPlugin:
    name = "web"
    version = "0.1.0"
    author = "@dev_dolbaeb"
    description = "Web search and URL fetch tools"

    tool_registry = (
        "web.search",
        "web.fetch_url",
        "web.read_html",
        "web.extract_links",
        "web.summarize_page",
    )

    tool_map = {
        "web_search": "cmd_web",
        "web.search": "cmd_web",
        "web.fetch_url": "cmd_web",
        "web.read_html": "cmd_web",
        "web.extract_links": "cmd_web",
        "web.summarize_page": "cmd_web",
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def cmd_web(self, tool_name: str, attrs_raw: str, body: str) -> str:
        attrs = self.agent._parse_xml_attrs(attrs_raw)
        query = (
            body.strip()
            or attrs.get("url")
            or attrs.get("query")
            or attrs.get("q")
            or attrs.get("text")
            or ""
        )
        if not query:
            return "query or url is required"
        return await self.agent._web_search(query)
