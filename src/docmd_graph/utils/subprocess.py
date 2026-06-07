from __future__ import annotations

import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def command_text(self) -> str:
        return " ".join(shlex.quote(arg) for arg in self.args)


def find_executable(name: str, fallback: str | None = None) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if fallback:
        return shutil.which(fallback)
    return None


def run_command(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
    timeout_s: int = 600,
    env: dict[str, str] | None = None,
) -> CommandResult:
    if not args:
        raise ValueError("args cannot be empty")
    executable = shutil.which(args[0]) if "/" not in args[0] else args[0]
    if not executable:
        raise FileNotFoundError(f"Executable not found: {args[0]}")

    completed = subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout_s,
        env=env,
        check=False,
    )
    return CommandResult(
        args=list(args),
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )
