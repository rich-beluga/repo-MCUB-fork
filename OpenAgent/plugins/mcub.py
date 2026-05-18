# scop: inline
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any


class McubPlugin:
    name = "mcub"
    version = "0.1.0"
    author = "@dev_dolbaeb"
    description = "MCUB kernel command tools"

    tool_registry = (
        "mcub.command",
        "mcub.config",
        "mcub.modules",
        "mcub.install",
        "mcub.reload",
    )

    tool_map = {
        "mcub": "cmd_mcub",
        "mcub.command": "cmd_mcub",
        "mcub.config": "cmd_mcub",
        "mcub.modules": "cmd_mcub",
        "mcub.install": "cmd_mcub",
        "mcub.reload": "cmd_mcub",
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def cmd_mcub(self, tool_name: str, attrs_raw: str, body: str, source_event: Any) -> str:
        attrs = self.agent._parse_xml_attrs(attrs_raw)
        command_map = {
            "mcub.modules": "modules",
            "mcub.config": "cfg",
            "mcub.install": "dlm",
            "mcub.reload": "restart",
        }
        command = (
            command_map.get(tool_name, "")
            or attrs.get("command")
            or attrs.get("cmd")
            or attrs.get("text")
            or attrs.get("query")
            or body.strip()
        )
        return await self.agent._run_mcub_command(command, source_event)
