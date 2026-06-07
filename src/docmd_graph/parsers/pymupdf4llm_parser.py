from __future__ import annotations

import importlib.util
from pathlib import Path

from docmd_graph.config import RunConfig
from docmd_graph.models import ParserResult
from docmd_graph.utils.filesystem import safe_relative, slugify
from docmd_graph.utils.markdown import normalize_markdown_text, rewrite_absolute_media_links

from .base import PDF_EXTS, DocumentParser, ParserError


class PyMuPDF4LLMParser(DocumentParser):
    name = "pymupdf4llm"

    @classmethod
    def available(cls) -> bool:
        return importlib.util.find_spec("pymupdf4llm") is not None

    @classmethod
    def can_parse(cls, path: Path) -> bool:
        return path.suffix.lower() in PDF_EXTS

    def parse(self, path: Path, media_dir: Path, work_dir: Path, config: RunConfig) -> ParserResult:
        del work_dir, config
        if not self.available():
            raise ParserError("pymupdf4llm is not installed. Install with `uv sync --extra pymupdf4llm`.")
        import pymupdf4llm  # type: ignore[import-not-found]

        asset_dir = media_dir / slugify(path.stem)
        asset_dir.mkdir(parents=True, exist_ok=True)
        try:
            markdown = pymupdf4llm.to_markdown(
                str(path),
                write_images=True,
                image_path=str(asset_dir),
                image_format="png",
            )
        except Exception as exc:  # noqa: BLE001
            raise ParserError(f"PyMuPDF4LLM failed: {exc}") from exc

        markdown = rewrite_absolute_media_links(str(markdown), media_dir.parent)
        media = [safe_relative(p, media_dir.parent) for p in sorted(asset_dir.rglob("*")) if p.is_file()]
        return ParserResult(
            source_path=str(path),
            parser=self.name,
            markdown=normalize_markdown_text(markdown),
            media=media,
        )
