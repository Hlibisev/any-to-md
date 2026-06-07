from __future__ import annotations

import importlib.util
from pathlib import Path

from docmd_graph.config import RunConfig
from docmd_graph.models import ParserResult
from docmd_graph.utils.markdown import normalize_markdown_text, rewrite_absolute_media_links

from .base import DocumentParser, ParserError

SUPPORTED_EXTS = {
    ".pdf",
    ".docx",
    ".doc",
    ".pptx",
    ".xlsx",
    ".xls",
    ".html",
    ".htm",
    ".csv",
    ".json",
    ".xml",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".tif",
    ".webp",
    ".bmp",
}


class MarkItDownParser(DocumentParser):
    name = "markitdown"

    @classmethod
    def available(cls) -> bool:
        return importlib.util.find_spec("markitdown") is not None

    @classmethod
    def can_parse(cls, path: Path) -> bool:
        return path.suffix.lower() in SUPPORTED_EXTS

    def parse(self, path: Path, media_dir: Path, work_dir: Path, config: RunConfig) -> ParserResult:
        del work_dir, config
        if not self.available():
            raise ParserError("markitdown is not installed. Install with `uv sync --extra markitdown`.")
        try:
            from markitdown import MarkItDown  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001
            raise ParserError(f"Could not import MarkItDown: {exc}") from exc

        try:
            converter = MarkItDown()
            converted = converter.convert(str(path))
            markdown = getattr(converted, "text_content", None) or str(converted)
        except Exception as exc:  # noqa: BLE001
            raise ParserError(f"MarkItDown failed: {exc}") from exc

        markdown = rewrite_absolute_media_links(markdown, media_dir.parent)
        return ParserResult(
            source_path=str(path),
            parser=self.name,
            markdown=normalize_markdown_text(markdown),
            diagnostics=["MarkItDown generally optimizes for LLM-readable text, not high-fidelity layout."],
        )
