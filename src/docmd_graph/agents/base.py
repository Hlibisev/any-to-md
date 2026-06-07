from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class AgentTask:
    role: str
    prompt: str
    cwd: Path
    timeout_s: int = 1200
    allow_edits: bool = False
    images: list[Path] = field(default_factory=list)
    output_file: Path | None = None


@dataclass
class AgentResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    command: str = ""


class AgentExecutor(Protocol):
    name: str

    def run(self, task: AgentTask) -> AgentResult:
        raise NotImplementedError
