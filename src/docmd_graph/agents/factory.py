from __future__ import annotations

from docmd_graph.config import RunConfig

from .base import AgentExecutor
from .codex import CodexAgent
from .cursor import CursorAgent
from .noop import NoopAgent


def make_agent(config: RunConfig) -> AgentExecutor:
    if config.agent == "codex":
        return CodexAgent(config)
    if config.agent == "cursor":
        return CursorAgent(config)
    return NoopAgent()
