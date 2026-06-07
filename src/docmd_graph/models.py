from __future__ import annotations

from pydantic import BaseModel, Field


class ParserResult(BaseModel):
    source_path: str
    parser: str
    markdown: str = ""
    markdown_path: str | None = None
    media: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    ok: bool = True


class AuditIssue(BaseModel):
    severity: str = Field(description="blocker, major, minor, or info")
    location: str = ""
    problem: str
    suggested_fix: str = ""


class AuditReport(BaseModel):
    ok: bool = True
    score: float = 1.0
    summary: str = ""
    issues: list[AuditIssue] = Field(default_factory=list)
    lost_information: list[str] = Field(default_factory=list)
    encoding_problems: list[str] = Field(default_factory=list)
    media_problems: list[str] = Field(default_factory=list)
    raw_agent_output: str | None = None

    def has_blocking_issues(self) -> bool:
        return any(issue.severity in {"blocker", "major"} for issue in self.issues)


class ConversionResult(BaseModel):
    output_dir: str
    markdown_path: str
    media_dir: str
    parser_results: list[ParserResult]
    audit_report: AuditReport
    fix_rounds: int
    work_dir: str | None = None
