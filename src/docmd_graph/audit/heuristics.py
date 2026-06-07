from __future__ import annotations

from pathlib import Path

from docmd_graph.models import AuditIssue, AuditReport
from docmd_graph.utils.markdown import find_image_refs, find_markdown_links

MOJIBAKE_PATTERNS = ["�", "Ð", "Ñ", "Рџ", "Р°", "Рµ", "â€™", "â€œ", "â€", "Ã"]


def audit_markdown(output_md: Path, media_dir: Path) -> AuditReport:
    issues: list[AuditIssue] = []
    media_problems: list[str] = []
    encoding_problems: list[str] = []
    lost_information: list[str] = []

    if not output_md.exists():
        return AuditReport(
            ok=False,
            score=0.0,
            summary="Markdown file does not exist.",
            issues=[
                AuditIssue(
                    severity="blocker",
                    location=str(output_md),
                    problem="Final Markdown file is missing.",
                    suggested_fix="Create the final Markdown file.",
                )
            ],
        )

    try:
        md = output_md.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return AuditReport(
            ok=False,
            score=0.0,
            summary="Markdown is not valid UTF-8.",
            issues=[
                AuditIssue(
                    severity="blocker",
                    location=str(output_md),
                    problem="Final Markdown cannot be decoded as UTF-8.",
                    suggested_fix="Rewrite the file as UTF-8.",
                )
            ],
        )

    stripped = md.strip()
    if len(stripped) < 40:
        issues.append(
            AuditIssue(
                severity="major",
                location=str(output_md),
                problem="Final Markdown is nearly empty.",
                suggested_fix="Restore extracted content from raw parser output.",
            )
        )

    replacement_count = md.count("�")
    suspicious_count = sum(md.count(pattern) for pattern in MOJIBAKE_PATTERNS)
    if replacement_count or suspicious_count >= 8:
        msg = f"Possible encoding corruption: replacement={replacement_count}, suspicious={suspicious_count}."
        encoding_problems.append(msg)
        issues.append(
            AuditIssue(
                severity="major",
                location=str(output_md),
                problem=msg,
                suggested_fix="Re-read source/raw Markdown as UTF-8 and repair mojibake text.",
            )
        )

    for ref in find_image_refs(md):
        target = (output_md.parent / ref).resolve()
        if not target.exists():
            media_problems.append(ref)
            issues.append(
                AuditIssue(
                    severity="major",
                    location=ref,
                    problem="Markdown image reference points to a missing file.",
                    suggested_fix="Copy the image into media/ or update the link to the correct relative path.",
                )
            )

    for ref in find_markdown_links(md):
        if ref.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif', '.tif', '.tiff', '.bmp')):
            target = (output_md.parent / ref).resolve()
            if not target.exists():
                media_problems.append(ref)
                issues.append(
                    AuditIssue(
                        severity="minor",
                        location=ref,
                        problem="Markdown link points to a missing local media file.",
                        suggested_fix="Update or remove the broken media link.",
                    )
                )

    long_lines = [idx + 1 for idx, line in enumerate(md.splitlines()) if len(line) > 500]
    if len(long_lines) > 5:
        issues.append(
            AuditIssue(
                severity="minor",
                location=f"lines {long_lines[:5]}",
                problem="Many very long lines reduce Markdown readability.",
                suggested_fix="Wrap prose lines and rebuild malformed tables if needed.",
            )
        )

    table_lines = [line for line in md.splitlines() if line.strip().startswith("|") and line.strip().endswith("|")]
    if table_lines:
        malformed = 0
        for line in table_lines:
            if line.count("|") < 3:
                malformed += 1
        if malformed > 3:
            issues.append(
                AuditIssue(
                    severity="minor",
                    location="tables",
                    problem="Some table-like lines have too few columns and may be malformed.",
                    suggested_fix="Repair table rows or convert them to bullet lists.",
                )
            )

    unreferenced_media = _unreferenced_media_files(output_md, media_dir, md)
    if len(unreferenced_media) >= 20:
        issues.append(
            AuditIssue(
                severity="minor",
                location=str(media_dir),
                problem=f"Many media files are not referenced from Markdown ({len(unreferenced_media)} files).",
                suggested_fix="Reference important figures or remove unused extracted parser noise.",
            )
        )

    blocking = any(issue.severity in {"blocker", "major"} for issue in issues)
    score = max(0.0, 1.0 - sum(_issue_penalty(issue.severity) for issue in issues))
    summary = "Audit passed." if not blocking else "Audit found blocking or major issues."
    return AuditReport(
        ok=not blocking,
        score=score,
        summary=summary,
        issues=issues,
        lost_information=lost_information,
        encoding_problems=encoding_problems,
        media_problems=media_problems,
    )


def _issue_penalty(severity: str) -> float:
    return {"blocker": 0.55, "major": 0.30, "minor": 0.08, "info": 0.02}.get(severity, 0.05)


def _unreferenced_media_files(output_md: Path, media_dir: Path, markdown: str) -> list[Path]:
    if not media_dir.exists():
        return []
    refs = set(find_image_refs(markdown)) | set(find_markdown_links(markdown))
    resolved_refs = {(output_md.parent / ref).resolve() for ref in refs if not ref.startswith("#")}
    media_files = [p.resolve() for p in media_dir.rglob("*") if p.is_file()]
    return [p for p in media_files if p not in resolved_refs]
