from __future__ import annotations

import importlib.util
from pathlib import Path

from docmd_graph.config import RunConfig
from docmd_graph.models import ParserResult
from docmd_graph.utils.filesystem import safe_relative, slugify
from docmd_graph.utils.markdown import normalize_markdown_text, rewrite_absolute_media_links

from .base import DocumentParser, ParserError

SUPPORTED_EXTS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".webp",
    ".bmp",
}


class DoclingParser(DocumentParser):
    name = "docling"

    @classmethod
    def available(cls) -> bool:
        return importlib.util.find_spec("docling") is not None

    @classmethod
    def can_parse(cls, path: Path) -> bool:
        return path.suffix.lower() in SUPPORTED_EXTS

    def parse(self, path: Path, media_dir: Path, work_dir: Path, config: RunConfig) -> ParserResult:
        del config
        if not self.available():
            raise ParserError("docling is not installed. Install with `uv sync --extra docling`.")
        try:
            from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001
            raise ParserError(f"Could not import Docling: {exc}") from exc

        asset_dir = media_dir / slugify(path.stem)
        asset_dir.mkdir(parents=True, exist_ok=True)
        tmp_md = work_dir / f"docling-{slugify(path.stem)}.md"
        try:
            converter = DocumentConverter()
            result = converter.convert(str(path))
            document = result.document
            try:
                from docling.datamodel.base_models import ImageRefMode  # type: ignore[import-not-found]

                document.save_as_markdown(
                    tmp_md,
                    artifacts_dir=asset_dir,
                    image_mode=ImageRefMode.REFERENCED,
                )
                markdown = tmp_md.read_text(encoding="utf-8", errors="replace")
            except Exception:
                markdown = document.export_to_markdown()
                tmp_md.write_text(markdown, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            raise ParserError(f"Docling failed: {exc}") from exc

        markdown = rewrite_absolute_media_links(markdown, media_dir.parent)
        media = [safe_relative(p, media_dir.parent) for p in sorted(asset_dir.rglob("*")) if p.is_file()]
        return ParserResult(
            source_path=str(path),
            parser=self.name,
            markdown=normalize_markdown_text(markdown),
            markdown_path=str(tmp_md),
            media=media,
        )
