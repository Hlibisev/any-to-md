from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .filesystem import safe_relative, write_text

_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def normalize_markdown_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    # Collapse extreme vertical whitespace while preserving paragraph breaks.
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"


def find_image_refs(markdown: str) -> list[str]:
    refs: list[str] = []
    for match in _IMAGE_RE.finditer(markdown):
        ref = match.group(1).strip().strip('"').strip("'")
        if ref and not ref.startswith(("http://", "https://", "data:")):
            refs.append(ref)
    return refs


def find_markdown_links(markdown: str) -> list[str]:
    refs: list[str] = []
    for match in _LINK_RE.finditer(markdown):
        ref = match.group(1).strip().strip('"').strip("'")
        if ref and not ref.startswith(("http://", "https://", "mailto:", "#")):
            refs.append(ref)
    return refs


def make_source_section(source_path: str, markdown: str, include_comment: bool = False) -> str:
    title = Path(source_path).name
    comment = f"<!-- source: {source_path} -->\n\n" if include_comment else ""
    body = normalize_markdown_text(markdown) if markdown.strip() else "[No text extracted.]\n"
    return f"## {title}\n\n{comment}{body}".strip() + "\n"


def compose_raw_markdown(parser_results: list[dict], include_source_comments: bool = False) -> str:
    parts = ["# Converted document", ""]
    for result in parser_results:
        parts.append(
            make_source_section(
                str(result.get("source_path", "unknown")),
                str(result.get("markdown", "")),
                include_comment=include_source_comments,
            )
        )
    return normalize_markdown_text("\n\n".join(parts))


def rewrite_absolute_media_links(markdown: str, output_dir: Path) -> str:
    """Convert absolute local image links under output_dir to relative links."""

    def replace(match: re.Match[str]) -> str:
        full = match.group(0)
        ref = match.group(1).strip().strip('"').strip("'")
        if ref.startswith(("http://", "https://", "data:")):
            return full
        path = Path(ref)
        if path.is_absolute():
            rel = safe_relative(path, output_dir)
            return full.replace(match.group(1), rel)
        # Normalize accidental ./ prefixes.
        clean = ref[2:] if ref.startswith("./") else ref
        return full.replace(match.group(1), clean)

    return _IMAGE_RE.sub(replace, markdown)


def write_markdown(path: Path, markdown: str) -> Path:
    return write_text(path, normalize_markdown_text(markdown))
