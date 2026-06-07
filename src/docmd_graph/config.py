from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ParserName = Literal["auto", "pymupdf4llm", "pandoc", "markitdown", "docling", "image", "text"]
AgentName = Literal["none", "codex", "cursor"]


class RunConfig(BaseModel):
    """Configuration for one conversion run."""

    parser: ParserName = "auto"
    agent: AgentName = "none"
    output_name: str = "blabla.md"
    max_fix_rounds: int = Field(default=2, ge=0, le=10)
    keep_workdir: bool = False
    fail_on_audit: bool = False

    # OCR and reference rendering.
    enable_ocr: bool = False
    ocr_languages: str = "eng+rus"
    render_dpi: int = Field(default=160, ge=72, le=300)
    render_max_pages: int = Field(default=24, ge=1, le=200)

    # Agent runtime.
    agent_timeout_s: int = Field(default=1200, ge=30)
    model: str | None = None
    codex_bin: str = "codex"
    cursor_bin: str = "cursor-agent"
    cursor_fallback_bin: str = "agent"
    codex_extra_args: list[str] = Field(default_factory=list)
    cursor_extra_args: list[str] = Field(default_factory=list)

    # Output control.
    clean_existing_output: bool = True
    include_source_comments: bool = False

    @field_validator("output_name")
    @classmethod
    def validate_output_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("output_name cannot be empty")
        if Path(value).name != value:
            raise ValueError("output_name must be a filename, not a path")
        if not value.lower().endswith(".md"):
            raise ValueError("output_name must end with .md")
        return value
