from __future__ import annotations

from pathlib import Path

from docmd_graph.utils.filesystem import safe_relative, write_text
from docmd_graph.utils.markdown import find_image_refs


def format_workspace_tree(root: Path, *, max_entries: int = 200) -> str:
    if not root.exists():
        return "(empty)"
    lines: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = safe_relative(path, root)
        if rel.startswith("../"):
            continue
        lines.append(rel)
        if len(lines) >= max_entries:
            lines.append(f"... ({max_entries} entries shown)")
            break
    return "\n".join(lines) if lines else "(no files yet)"


def format_previous_agent_notes(agent_dir: Path, *, max_chars: int = 6000) -> str:
    if not agent_dir.exists():
        return "(no prior agent steps yet)"
    chunks: list[str] = []
    for path in sorted(agent_dir.glob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if not text:
            continue
        chunks.append(f"## {path.name}\n{text}")
    combined = "\n\n".join(chunks).strip()
    if not combined:
        return "(no prior agent steps yet)"
    if len(combined) > max_chars:
        return combined[:max_chars] + "\n... (truncated)"
    return combined


def refresh_workspace_manifest(output_dir: Path, work_dir: Path) -> Path:
    manifest_path = work_dir / "workspace_manifest.txt"
    tree = format_workspace_tree(output_dir)
    agent_notes = format_previous_agent_notes(work_dir / "agent")
    write_text(
        manifest_path,
        "\n".join(
            [
                "Conversion package root: .",
                "All agent paths below are relative to this root.",
                "",
                "Current files:",
                tree,
                "",
                "Previous agent steps:",
                agent_notes,
            ]
        ),
    )
    return manifest_path


def workspace_prompt_values(
    *,
    output_dir: Path,
    output_md: Path,
    media_dir: Path,
    work_dir: Path,
    screenshots_dir: Path,
    parser_results_path: Path | None = None,
) -> dict[str, str]:
    refresh_workspace_manifest(output_dir, work_dir)
    values = {
        "workspace_root": ".",
        "output_md": safe_relative(output_md, output_dir),
        "media_dir": safe_relative(media_dir, output_dir),
        "raw_md_path": safe_relative(work_dir / "raw.md", output_dir),
        "screenshots_dir": safe_relative(screenshots_dir, output_dir),
        "workspace_manifest": safe_relative(work_dir / "workspace_manifest.txt", output_dir),
        "agent_log_dir": safe_relative(work_dir / "agent", output_dir),
        "workspace_tree": format_workspace_tree(output_dir),
        "previous_agent_notes": format_previous_agent_notes(work_dir / "agent"),
    }
    if parser_results_path is not None:
        values["parser_results_path"] = safe_relative(parser_results_path, output_dir)
    return values


def sanitize_agent_audit(report, output_md: Path, media_dir: Path):
    """Drop agent claims about missing media that already exist on disk."""
    from docmd_graph.models import AuditReport

    if not isinstance(report, AuditReport):
        return report

    package_root = output_md.parent
    referenced = set(find_image_refs(output_md.read_text(encoding="utf-8", errors="replace")))
    existing_media = (
        {safe_relative(path, package_root) for path in media_dir.rglob("*") if path.is_file()}
        if media_dir.exists()
        else set()
    )
    has_media_files = bool(existing_media)

    def media_exists(token: str) -> bool:
        token = token.strip().strip("`\"'")
        if not token:
            return False
        if (package_root / token).exists():
            return True
        name = Path(token).name
        return any(Path(rel).name == name for rel in existing_media)

    cleaned_issues = []
    for issue in report.issues:
        problem = issue.problem.lower()
        location = issue.location.lower()
        if has_media_files and ("empty" in problem or "empty" in location) and "media" in problem + location:
            continue
        if (
            any(ref in issue.problem or ref in issue.location for ref in referenced if media_exists(ref))
            and ("missing" in problem or "does not exist" in problem or "broken" in problem)
        ):
            continue
        cleaned_issues.append(issue)

    cleaned_media = [item for item in report.media_problems if not media_exists(item)]
    cleaned_lost = [
        item
        for item in report.lost_information
        if not any(ref in item and media_exists(ref) for ref in referenced)
    ]

    blocking = any(issue.severity in {"blocker", "major"} for issue in cleaned_issues)
    return AuditReport(
        ok=report.ok and not blocking,
        score=report.score,
        summary=report.summary,
        issues=cleaned_issues,
        lost_information=cleaned_lost,
        encoding_problems=report.encoding_problems,
        media_problems=cleaned_media,
        raw_agent_output=report.raw_agent_output,
    )
