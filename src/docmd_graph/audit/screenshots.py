from __future__ import annotations

import shutil
from pathlib import Path

from docmd_graph.config import RunConfig
from docmd_graph.parsers.base import IMAGE_EXTS
from docmd_graph.utils.filesystem import copy_file_unique, ensure_dir, slugify
from docmd_graph.utils.subprocess import run_command


def render_reference_images(input_paths: list[Path], work_dir: Path, config: RunConfig) -> tuple[list[Path], list[str]]:
    screenshots_dir = ensure_dir(work_dir / "screenshots")
    screenshots: list[Path] = []
    diagnostics: list[str] = []
    remaining_pages = config.render_max_pages

    for path in input_paths:
        if remaining_pages <= 0:
            diagnostics.append(f"Screenshot rendering stopped after {config.render_max_pages} pages/images.")
            break
        ext = path.suffix.lower()
        try:
            if ext == ".pdf":
                made = _render_pdf(path, screenshots_dir, config.render_dpi, remaining_pages)
                screenshots.extend(made)
                remaining_pages -= len(made)
            elif ext in IMAGE_EXTS:
                copied = copy_file_unique(path, screenshots_dir, name=f"source-{slugify(path.stem)}{path.suffix.lower()}")
                screenshots.append(copied)
                remaining_pages -= 1
            elif ext in {".docx", ".doc", ".odt", ".rtf", ".pptx"}:
                pdf = _office_to_pdf(path, screenshots_dir, diagnostics)
                if pdf:
                    made = _render_pdf(pdf, screenshots_dir, config.render_dpi, remaining_pages)
                    screenshots.extend(made)
                    remaining_pages -= len(made)
        except Exception as exc:  # noqa: BLE001
            diagnostics.append(f"Could not render reference for {path}: {exc}")

    return screenshots, diagnostics


def _render_pdf(path: Path, output_dir: Path, dpi: int, max_pages: int) -> list[Path]:
    import fitz  # type: ignore[import-not-found]

    made: list[Path] = []
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    doc = fitz.open(str(path))
    try:
        for page_index in range(min(len(doc), max_pages)):
            page = doc[page_index]
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            out = output_dir / f"{slugify(path.stem)}-page-{page_index + 1:03d}.png"
            pix.save(str(out))
            made.append(out)
    finally:
        doc.close()
    return made


def _office_to_pdf(path: Path, output_dir: Path, diagnostics: list[str]) -> Path | None:
    binary = shutil.which("soffice") or shutil.which("libreoffice")
    if not binary:
        diagnostics.append(f"LibreOffice/soffice not found; cannot render screenshots for {path.name}.")
        return None
    result = run_command(
        [binary, "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(path)],
        timeout_s=180,
    )
    if result.returncode != 0:
        diagnostics.append(f"LibreOffice failed for {path.name}: {result.stderr.strip() or result.stdout.strip()}")
        return None
    candidate = output_dir / f"{path.stem}.pdf"
    if candidate.exists():
        return candidate
    matches = list(output_dir.glob(f"{path.stem}*.pdf"))
    return matches[0] if matches else None
