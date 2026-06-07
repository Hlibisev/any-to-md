from __future__ import annotations

from .base import AgentResult, AgentTask


class NoopAgent:
    name = "none"

    def run(self, task: AgentTask) -> AgentResult:
        del task
        return AgentResult(ok=True, stdout="Agent disabled; deterministic path only.")
