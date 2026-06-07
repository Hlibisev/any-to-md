from __future__ import annotations

from pathlib import Path

from docmd_graph.agents.workspace import (
    format_workspace_tree,
    sanitize_agent_audit,
    workspace_prompt_values,
)
from docmd_graph.models import AuditIssue, AuditReport


def test_workspace_prompt_values_use_relative_paths(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    media_dir = output_dir / "media"
    work_dir = output_dir / "_work"
    media_dir.mkdir(parents=True)
    work_dir.mkdir(parents=True)
    (output_dir / "blabla.md").write_text("# hi\n", encoding="utf-8")
    (media_dir / "page-01.png").write_bytes(b"png")
    (work_dir / "agent").mkdir()
    (work_dir / "agent" / "fix-round-0.txt").write_text("copied images", encoding="utf-8")

    values = workspace_prompt_values(
        output_dir=output_dir,
        output_md=output_dir / "blabla.md",
        media_dir=media_dir,
        work_dir=work_dir,
        screenshots_dir=work_dir / "screenshots",
    )

    assert values["workspace_root"] == "."
    assert values["output_md"] == "blabla.md"
    assert values["media_dir"] == "media"
    assert "media/page-01.png" in values["workspace_tree"]
    assert (work_dir / "workspace_manifest.txt").exists()


def test_sanitize_agent_audit_drops_false_missing_media(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    media_dir = output_dir / "media"
    output_md = output_dir / "blabla.md"
    media_dir.mkdir(parents=True)
    output_md.write_text("![p](media/page-01.png)\n", encoding="utf-8")
    (media_dir / "page-01.png").write_bytes(b"png")

    report = AuditReport(
        ok=False,
        score=0.5,
        summary="bad",
        issues=[
            AuditIssue(
                severity="blocker",
                location="media/",
                problem="The media/ directory is empty.",
                suggested_fix="copy files",
            )
        ],
        media_problems=["media/page-01.png"],
    )

    cleaned = sanitize_agent_audit(report, output_md, media_dir)
    assert cleaned.media_problems == []
    assert cleaned.issues == []


def test_format_workspace_tree_empty_dir(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    assert format_workspace_tree(root) == "(no files yet)"
