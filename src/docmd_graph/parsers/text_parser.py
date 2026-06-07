from __future__ import annotations

from pathlib import Path

from docmd_graph.config import RunConfig
from docmd_graph.models import ParserResult
from docmd_graph.utils.markdown import normalize_markdown_text

from .base import TEXT_EXTS, DocumentParser


class TextParser(DocumentParser):
    name = "text"

    @classmethod
    def can_parse(cls, path: Path) -> bool:
        return path.suffix.lower() in TEXT_EXTS

    def parse(self, path: Path, media_dir: Path, work_dir: Path, config: RunConfig) -> ParserResult:
        del media_dir, work_dir, config
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")
        return ParserResult(
            source_path=str(path),
            parser=self.name,
            markdown=normalize_markdown_text(text),
            diagnostics=[],
        )
