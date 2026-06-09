from __future__ import annotations

from pathlib import Path

from docmd_graph.config import RunConfig
from docmd_graph.models import ParserResult
from docmd_graph.utils.filesystem import safe_relative

from .base import IMAGE_EXTS, OFFICE_EXTS, PDF_EXTS, TEXT_EXTS, DocumentParser, ParserError
from .image_parser import ImageParser
from .markitdown_parser import MarkItDownParser
from .pandoc_parser import PandocParser
from .pymupdf4llm_parser import PyMuPDF4LLMParser
from .text_parser import TextParser

PARSERS: dict[str, type[DocumentParser]] = {
    "pymupdf4llm": PyMuPDF4LLMParser,
    "pandoc": PandocParser,
    "markitdown": MarkItDownParser,
    "image": ImageParser,
    "text": TextParser,
}


def parser_order(path: Path) -> list[str]:
    ext = path.suffix.lower()
    if ext in PDF_EXTS:
        return ["pymupdf4llm", "markitdown"]
    if ext in OFFICE_EXTS:
        if ext in {".docx", ".doc", ".odt", ".rtf"}:
            return ["pandoc", "markitdown"]
        return ["markitdown", "pandoc"]
    if ext in IMAGE_EXTS:
        return ["image", "markitdown"]
    if ext in TEXT_EXTS:
        return ["text", "markitdown"]
    return ["markitdown", "pandoc", "text"]


def parse_inputs(
    paths: list[Path],
    *,
    media_dir: Path,
    work_dir: Path,
    output_dir: Path,
    config: RunConfig,
) -> list[ParserResult]:
    results: list[ParserResult] = []
    for path in paths:
        results.append(parse_one(path, media_dir=media_dir, work_dir=work_dir, output_dir=output_dir, config=config))
    return results


def parse_one(
    path: Path,
    *,
    media_dir: Path,
    work_dir: Path,
    output_dir: Path,
    config: RunConfig,
) -> ParserResult:
    del output_dir
    candidates = [config.parser] if config.parser != "auto" else parser_order(path)
    diagnostics: list[str] = []
    for name in candidates:
        parser_cls = PARSERS.get(str(name))
        if parser_cls is None:
            diagnostics.append(f"Unknown parser: {name}")
            continue
        if not parser_cls.can_parse(path):
            diagnostics.append(f"{name}: parser does not support {path.suffix or 'extensionless file'}")
            continue
        if not parser_cls.available():
            diagnostics.append(f"{name}: parser not available")
            continue
        parser = parser_cls()
        try:
            result = parser.parse(path, media_dir, work_dir, config)
            result.diagnostics.extend(diagnostics)
            return result
        except ParserError as exc:
            diagnostics.append(f"{name}: {exc}")
        except Exception as exc:  # noqa: BLE001
            diagnostics.append(f"{name}: unexpected error: {exc}")

    rel = safe_relative(path, path.parent)
    return ParserResult(
        source_path=str(path),
        parser="failed",
        markdown=f"### {rel}\n\n[Parsing failed for this file.]\n",
        ok=False,
        diagnostics=diagnostics or ["No parser candidates were available."],
    )


def get_available_parsers() -> dict[str, bool]:
    return {name: parser.available() for name, parser in PARSERS.items()}
