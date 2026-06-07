from __future__ import annotations

from pathlib import Path

from docmd_graph.utils.markdown import normalize_markdown_text, rewrite_absolute_media_links


def deterministic_repair(output_md: Path, output_dir: Path) -> list[str]:
    """Apply safe repairs that do not require an LLM/agent."""
    if not output_md.exists():
        return []
    text = output_md.read_text(encoding="utf-8", errors="replace")
    repaired = rewrite_absolute_media_links(text, output_dir)
    repaired = normalize_markdown_text(repaired)
    if repaired != text:
        output_md.write_text(repaired, encoding="utf-8", newline="\n")
        return ["Normalized UTF-8 Markdown, line endings, and absolute local media links."]
    return []
