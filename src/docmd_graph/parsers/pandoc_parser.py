from __future__ import annotations

import shutil
from pathlib import Path

from docmd_graph.config import RunConfig
from docmd_graph.models import ParserResult
from docmd_graph.utils.filesystem import safe_relative, slugify
from docmd_graph.utils.markdown import normalize_markdown_text, rewrite_absolute_media_links
from docmd_graph.utils.subprocess import run_command

from .base import OFFICE_EXTS, DocumentParser, ParserError


class PandocParser(DocumentParser):
    name = "pandoc"

    @classmethod
    def available(cls) -> bool:
        return shutil.which("pandoc") is not None

    @classmethod
    def can_parse(cls, path: Path) -> bool:
        return path.suffix.lower() in OFFICE_EXTS or path.suffix.lower() in {".md", ".html", ".htm"}

    def parse(self, path: Path, media_dir: Path, work_dir: Path, config: RunConfig) -> ParserResult:
        del config
        if not self.available():
            raise ParserError("pandoc executable not found.")
        asset_dir = media_dir / slugify(path.stem)
        asset_dir.mkdir(parents=True, exist_ok=True)
        tmp_md = work_dir / f"pandoc-{slugify(path.stem)}.md"
        result = run_command(
            [
                "pandoc",
                str(path),
                "-t",
                "gfm",
                "--wrap=none",
                f"--extract-media={asset_dir}",
                "-o",
                str(tmp_md),
            ],
            timeout_s=600,
        )
        if result.returncode != 0:
            raise ParserError(f"pandoc failed: {result.stderr.strip() or result.stdout.strip()}")
        markdown = tmp_md.read_text(encoding="utf-8", errors="replace")
        markdown = rewrite_absolute_media_links(markdown, media_dir.parent)
        media = [safe_relative(p, media_dir.parent) for p in sorted(asset_dir.rglob("*")) if p.is_file()]
        diagnostics = [result.stderr.strip()] if result.stderr.strip() else []
        return ParserResult(
            source_path=str(path),
            parser=self.name,
            markdown=normalize_markdown_text(markdown),
            markdown_path=str(tmp_md),
            media=media,
            diagnostics=diagnostics,
        )
