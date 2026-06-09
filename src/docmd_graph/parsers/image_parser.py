from __future__ import annotations

from pathlib import Path

from PIL import Image

from docmd_graph.config import RunConfig
from docmd_graph.models import ParserResult
from docmd_graph.utils.filesystem import copy_file_unique, safe_relative, slugify

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
            ocr_text = self._ocr_gcv(path, diagnostics)
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
            md_lines.append("> Image copied to media. Enable `--ocr` for Google Cloud Vision OCR.\n")

        return ParserResult(
            source_path=str(path),
            parser=self.name,
            markdown="\n".join(md_lines),
            media=[str(copied)],
            diagnostics=diagnostics,
        )

    def _ocr_gcv(self, path: Path, diagnostics: list[str]) -> str:
        try:
            from google.cloud import vision  # noqa: PLC0415
        except ImportError:
            diagnostics.append("google-cloud-vision not installed; OCR skipped. Install with: pip install google-cloud-vision")
            return ""

        try:
            client = vision.ImageAnnotatorClient()
            content = path.read_bytes()
            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)

            if response.error.message:
                diagnostics.append(f"GCV error: {response.error.message}")
                return ""

            return response.full_text_annotation.text or ""
        except Exception as exc:  # noqa: BLE001 - optional OCR
            diagnostics.append(f"GCV OCR failed: {exc}")
            return ""
