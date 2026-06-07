from __future__ import annotations

from pathlib import Path

from docmd_graph.config import RunConfig
from docmd_graph.utils.subprocess import find_executable, run_command

from .base import AgentResult, AgentTask


class CodexAgent:
    name = "codex"

    def __init__(self, config: RunConfig):
        self.config = config

    def run(self, task: AgentTask) -> AgentResult:
        binary = find_executable(self.config.codex_bin)
        if not binary:
            return AgentResult(ok=False, stderr=f"Codex executable not found: {self.config.codex_bin}", returncode=127)

        sandbox = "workspace-write" if task.allow_edits else "read-only"
        output_file = task.output_file or (task.cwd / "_work" / "agent" / f"{task.role}-codex.txt")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            binary,
            "exec",
            "--cd",
            str(task.cwd),
            "--skip-git-repo-check",
            "--sandbox",
            sandbox,
            "--ask-for-approval",
            "never",
            "--color",
            "never",
            "--ephemeral",
            "--output-last-message",
            str(output_file),
        ]
        if self.config.model:
            cmd.extend(["--model", self.config.model])
        for image in task.images:
            if Path(image).exists():
                cmd.extend(["--image", str(image)])
        cmd.extend(self.config.codex_extra_args)
        cmd.append("-")

        try:
            result = run_command(cmd, cwd=task.cwd, input_text=task.prompt, timeout_s=task.timeout_s)
        except Exception as exc:  # noqa: BLE001
            return AgentResult(ok=False, stderr=str(exc), returncode=1, command=" ".join(cmd))

        stdout = result.stdout
        if output_file.exists():
            try:
                stdout = output_file.read_text(encoding="utf-8", errors="replace") or stdout
            except OSError:
                pass
        return AgentResult(
            ok=result.returncode == 0,
            stdout=stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            command=result.command_text,
        )
