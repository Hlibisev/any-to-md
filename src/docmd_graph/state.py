from __future__ import annotations

from typing import Any, TypedDict


class DocState(TypedDict, total=False):
    input_paths: list[str]
    output_dir: str
    output_md: str
    media_dir: str
    work_dir: str
    config: dict[str, Any]
    parser_results: list[dict[str, Any]]
    raw_md_path: str
    screenshots: list[str]
    diagnostics: list[str]
    audit_round: int
    audit_ok: bool
    audit_report: dict[str, Any]
    agent_outputs: list[dict[str, Any]]
