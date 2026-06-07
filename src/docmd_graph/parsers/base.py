from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from docmd_graph.config import RunConfig
from docmd_graph.models import ParserResult

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}
TEXT_EXTS = {".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml"}
OFFICE_EXTS = {".docx", ".doc", ".odt", ".rtf", ".pptx", ".xlsx", ".xls", ".html", ".htm"}
PDF_EXTS = {".pdf"}


class ParserError(RuntimeError):
    pass


class DocumentParser(ABC):
    name: str

    @classmethod
    def available(cls) -> bool:
        return True

    @classmethod
    @abstractmethod
    def can_parse(cls, path: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, path: Path, media_dir: Path, work_dir: Path, config: RunConfig) -> ParserResult:
        raise NotImplementedError
