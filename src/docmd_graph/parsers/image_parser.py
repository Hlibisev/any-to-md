from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

from docmd_graph.config import RunConfig
from docmd_graph.models import ParserResult
from docmd_graph.utils.filesystem import copy_file_unique, safe_relative, slugify
from docmd_graph.utils.subprocess import run_command

from .base import IMAGE_EXTS, DocumentParser


class ImageParser(DocumentParser):
    name = "image"

    @classmethod
    def can_parse(cls, path: Path) -> bool:
        return path.suffix.lower() in IMAGE_EXTS

    def parse(self, path: Path, media_dir: Path, work_dir: Path, config: RunConfig) -> ParserResult:
        del work_dir
        diagnostics: list[str] = []
        asset_dir = media_dir / slugify(path.stem)
        copied = copy_file_unique(path, asset_dir)

        width = height = None
        try:
            with Image.open(path) as img:
                width, height = img.size
        except Exception as exc:  # noqa: BLE001 - metadata only
            diagnostics.append(f"Could not read image dimensions: {exc}")

        rel = safe_relative(copied, media_dir.parent)
        md_lines = [f"### Image: {path.name}", "", f"![{path.name}]({rel})", ""]
        if width and height:
            md_lines.extend([f"- Dimensions: {width} x {height}px", ""])

        if config.enable_ocr:
            ocr_text = self._ocr(path, config.ocr_languages, diagnostics)
            if ocr_text.strip():
                md_lines.extend([
                    "#### OCR transcript",
                    "",
                    "```text",
                    ocr_text.strip(),
                    "```",
                    "",
                ])
            else:
                md_lines.append("> OCR was enabled, but no text was extracted.\n")
        else:
            md_lines.append("> Image copied to media. Enable `--ocr` for best-effort local Tesseract transcription.\n")

        return ParserResult(
            source_path=str(path),
            parser=self.name,
            markdown="\n".join(md_lines),
            media=[str(copied)],
            diagnostics=diagnostics,
        )

    def _ocr(self, path: Path, languages: str, diagnostics: list[str]) -> str:
        if not shutil.which("tesseract"):
            diagnostics.append("Tesseract executable not found; image OCR skipped.")
            return ""
        try:
            result = run_command(
                ["tesseract", str(path), "stdout", "-l", languages],
                timeout_s=180,
            )
        except Exception as exc:  # noqa: BLE001 - optional OCR
            diagnostics.append(f"Tesseract failed: {exc}")
            return ""
        if result.returncode != 0:
            diagnostics.append(f"Tesseract returned {result.returncode}: {result.stderr.strip()}")
            return ""
        return result.stdout
