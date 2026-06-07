from __future__ import annotations

from pathlib import Path

from docmd_graph.config import RunConfig
from docmd_graph.utils.filesystem import safe_relative, write_text
from docmd_graph.utils.subprocess import find_executable, run_command

from .base import AgentResult, AgentTask


class CursorAgent:
    name = "cursor"

    def __init__(self, config: RunConfig):
        self.config = config

    def run(self, task: AgentTask) -> AgentResult:
        binary = find_executable(self.config.cursor_bin, self.config.cursor_fallback_bin)
        if not binary:
            return AgentResult(
                ok=False,
                stderr=f"Cursor executable not found: {self.config.cursor_bin} or {self.config.cursor_fallback_bin}",
                returncode=127,
            )

        prompt_dir = task.cwd / "_work" / "prompts"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = write_text(prompt_dir / f"{task.role}-cursor.md", task.prompt)
        rel_prompt = safe_relative(prompt_path, task.cwd)
        rel_images = [safe_relative(Path(p), task.cwd) for p in task.images if Path(p).exists()]
        image_note = ""
        if rel_images:
            image_note = " Reference images are available at: " + ", ".join(rel_images) + "."
        short_prompt = f"Read and follow the instructions in {rel_prompt}.{image_note} Complete the task exactly."

        cmd = [
            binary,
            "--print",
            "--output-format",
            "text",
            "--workspace",
            str(task.cwd),
            "--trust",
        ]
        if task.allow_edits:
            cmd.append("--force")
        if self.config.model:
            cmd.extend(["--model", self.config.model])
        cmd.extend(self.config.cursor_extra_args)
        cmd.append(short_prompt)

        try:
            result = run_command(cmd, cwd=task.cwd, timeout_s=task.timeout_s)
        except Exception as exc:  # noqa: BLE001
            return AgentResult(ok=False, stderr=str(exc), returncode=1, command=" ".join(cmd))

        if task.output_file:
            try:
                task.output_file.parent.mkdir(parents=True, exist_ok=True)
                task.output_file.write_text(result.stdout, encoding="utf-8")
            except OSError:
                pass
        return AgentResult(
            ok=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            command=result.command_text,
        )
