from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from docmd_graph.agents.base import AgentTask
from docmd_graph.agents.factory import make_agent
from docmd_graph.audit.heuristics import audit_markdown
from docmd_graph.audit.screenshots import render_reference_images
from docmd_graph.config import RunConfig
from docmd_graph.models import AuditIssue, AuditReport, ParserResult
from docmd_graph.parsers import parse_inputs
from docmd_graph.repair import deterministic_repair
from docmd_graph.state import DocState
from docmd_graph.utils.filesystem import ensure_dir, reset_dir, walk_inputs, write_text
from docmd_graph.utils.json_tools import extract_json_object
from docmd_graph.utils.markdown import compose_raw_markdown, write_markdown


def build_graph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError(
            "langgraph is required. Install with `uv sync` or `uv add langgraph`."
        ) from exc

    builder = StateGraph(DocState)
    builder.add_node("parse", parse_node)
    builder.add_node("enhance", enhance_node)
    builder.add_node("audit", audit_node)
    builder.add_node("fix", fix_node)
    builder.add_edge(START, "parse")
    builder.add_edge("parse", "enhance")
    builder.add_edge("enhance", "audit")
    builder.add_conditional_edges("audit", route_after_audit, {"fix": "fix", "end": END})
    builder.add_edge("fix", "audit")
    return builder.compile()


def parse_node(state: DocState) -> DocState:
    config = RunConfig.model_validate(state["config"])
    output_dir = Path(state["output_dir"])
    output_md = Path(state["output_md"])
    media_dir = Path(state["media_dir"])
    work_dir = Path(state["work_dir"])
    ensure_dir(output_dir)
    ensure_dir(media_dir)
    ensure_dir(work_dir)

    input_paths = walk_inputs([Path(p) for p in state["input_paths"]])
    screenshots, screenshot_diagnostics = render_reference_images(input_paths, work_dir, config)
    parser_results = parse_inputs(
        input_paths,
        media_dir=media_dir,
        work_dir=work_dir,
        output_dir=output_dir,
        config=config,
    )
    parser_result_dicts = [result.model_dump() for result in parser_results]
    raw_md = compose_raw_markdown(parser_result_dicts, include_source_comments=config.include_source_comments)
    raw_md_path = work_dir / "raw.md"
    write_markdown(raw_md_path, raw_md)
    write_text(work_dir / "parser_results.json", json.dumps(parser_result_dicts, ensure_ascii=False, indent=2))

    # Create the initial final Markdown before the enhancer runs.
    if not output_md.exists():
        write_markdown(output_md, raw_md)

    diagnostics = list(state.get("diagnostics", []))
    diagnostics.extend(screenshot_diagnostics)
    for result in parser_results:
        diagnostics.extend([f"{Path(result.source_path).name}: {d}" for d in result.diagnostics])

    return {
        **state,
        "input_paths": [str(p) for p in input_paths],
        "parser_results": parser_result_dicts,
        "raw_md_path": str(raw_md_path),
        "screenshots": [str(p) for p in screenshots],
        "diagnostics": diagnostics,
        "audit_round": 0,
    }


def enhance_node(state: DocState) -> DocState:
    config = RunConfig.model_validate(state["config"])
    output_md = Path(state["output_md"])
    output_dir = Path(state["output_dir"])
    deterministic_repair(output_md, output_dir)

    if config.agent == "none":
        return state

    prompt = _format_prompt(
        "enhancer.md",
        state,
        extra={
            "parser_results_path": str(Path(state["work_dir"]) / "parser_results.json"),
            "screenshots_dir": str(Path(state["work_dir"]) / "screenshots"),
        },
    )
    agent = make_agent(config)
    result = agent.run(
        AgentTask(
            role="enhance",
            prompt=prompt,
            cwd=Path(state["output_dir"]),
            timeout_s=config.agent_timeout_s,
            allow_edits=True,
            images=[Path(p) for p in state.get("screenshots", [])],
            output_file=Path(state["work_dir"]) / "agent" / "enhance.txt",
        )
    )
    outputs = list(state.get("agent_outputs", []))
    outputs.append(result.__dict__)
    deterministic_repair(output_md, output_dir)
    return {**state, "agent_outputs": outputs}


def audit_node(state: DocState) -> DocState:
    config = RunConfig.model_validate(state["config"])
    output_md = Path(state["output_md"])
    media_dir = Path(state["media_dir"])
    raw_md_path = Path(state["raw_md_path"])

    heuristic_report = audit_markdown(output_md, media_dir, raw_md_path)
    final_report = heuristic_report

    if config.agent != "none":
        prompt = _format_prompt(
            "auditor.md",
            state,
            extra={
                "screenshots_dir": str(Path(state["work_dir"]) / "screenshots"),
                "heuristic_report_json": json.dumps(heuristic_report.model_dump(), ensure_ascii=False, indent=2),
            },
        )
        agent = make_agent(config)
        result = agent.run(
            AgentTask(
                role=f"audit-round-{state.get('audit_round', 0)}",
                prompt=prompt,
                cwd=Path(state["output_dir"]),
                timeout_s=config.agent_timeout_s,
                allow_edits=False,
                images=[Path(p) for p in state.get("screenshots", [])],
                output_file=Path(state["work_dir"]) / "agent" / f"audit-round-{state.get('audit_round', 0)}.txt",
            )
        )
        outputs = list(state.get("agent_outputs", []))
        outputs.append(result.__dict__)
        state = {**state, "agent_outputs": outputs}
        agent_report = _parse_agent_audit(result.stdout)
        if agent_report:
            final_report = _merge_reports(heuristic_report, agent_report, result.stdout)
        elif not result.ok:
            final_report.issues.append(
                AuditIssue(
                    severity="minor",
                    location="agent-audit",
                    problem=f"Agent audit failed or returned non-JSON output: {result.stderr[:300]}",
                    suggested_fix="Check agent authentication and rerun with --keep-workdir for logs.",
                )
            )

    round_no = int(state.get("audit_round", 0))
    audit_path = Path(state["work_dir"]) / f"audit_round_{round_no}.json"
    write_text(audit_path, json.dumps(final_report.model_dump(), ensure_ascii=False, indent=2))
    return {
        **state,
        "audit_report": final_report.model_dump(),
        "audit_ok": final_report.ok,
    }


def fix_node(state: DocState) -> DocState:
    config = RunConfig.model_validate(state["config"])
    output_md = Path(state["output_md"])
    output_dir = Path(state["output_dir"])
    changes = deterministic_repair(output_md, output_dir)

    if config.agent != "none":
        prompt = _format_prompt(
            "fixer.md",
            state,
            extra={
                "screenshots_dir": str(Path(state["work_dir"]) / "screenshots"),
                "audit_report_json": json.dumps(state.get("audit_report", {}), ensure_ascii=False, indent=2),
            },
        )
        agent = make_agent(config)
        result = agent.run(
            AgentTask(
                role=f"fix-round-{state.get('audit_round', 0)}",
                prompt=prompt,
                cwd=Path(state["output_dir"]),
                timeout_s=config.agent_timeout_s,
                allow_edits=True,
                images=[Path(p) for p in state.get("screenshots", [])],
                output_file=Path(state["work_dir"]) / "agent" / f"fix-round-{state.get('audit_round', 0)}.txt",
            )
        )
        outputs = list(state.get("agent_outputs", []))
        outputs.append(result.__dict__)
        state = {**state, "agent_outputs": outputs}
        changes.extend(["Agent fixer executed." if result.ok else f"Agent fixer failed: {result.stderr[:200]}"])

    deterministic_repair(output_md, output_dir)
    diagnostics = list(state.get("diagnostics", []))
    diagnostics.extend(changes)
    return {
        **state,
        "audit_round": int(state.get("audit_round", 0)) + 1,
        "diagnostics": diagnostics,
    }


def route_after_audit(state: DocState) -> str:
    config = RunConfig.model_validate(state["config"])
    if state.get("audit_ok", False):
        return "end"
    if int(state.get("audit_round", 0)) >= config.max_fix_rounds:
        return "end"
    return "fix"


def prepare_initial_state(inputs: list[Path], output_dir: Path, config: RunConfig) -> DocState:
    if config.clean_existing_output and output_dir.exists():
        # Keep this conservative: delete only known output structure.
        for name in [config.output_name, "media", "_work"]:
            target = output_dir / name
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
    ensure_dir(output_dir)
    media_dir = ensure_dir(output_dir / "media")
    work_dir = ensure_dir(output_dir / "_work")
    output_md = output_dir / config.output_name
    return {
        "input_paths": [str(p) for p in inputs],
        "output_dir": str(output_dir),
        "output_md": str(output_md),
        "media_dir": str(media_dir),
        "work_dir": str(work_dir),
        "config": config.model_dump(),
        "parser_results": [],
        "screenshots": [],
        "diagnostics": [],
        "audit_round": 0,
        "audit_ok": False,
        "agent_outputs": [],
    }


def cleanup_workdir(state: DocState) -> None:
    config = RunConfig.model_validate(state["config"])
    if not config.keep_workdir:
        work_dir = Path(state["work_dir"])
        if work_dir.exists():
            shutil.rmtree(work_dir)


def _format_prompt(name: str, state: DocState, extra: dict[str, Any] | None = None) -> str:
    from docmd_graph.prompts import load_prompt

    values: dict[str, Any] = {
        "output_md": state.get("output_md", ""),
        "media_dir": state.get("media_dir", ""),
        "raw_md_path": state.get("raw_md_path", ""),
    }
    if extra:
        values.update(extra)
    return load_prompt(name).format(**values)


def _parse_agent_audit(text: str) -> AuditReport | None:
    data = extract_json_object(text)
    if not data:
        return None
    try:
        return AuditReport.model_validate(data)
    except ValidationError:
        return None


def _merge_reports(heuristic: AuditReport, agent: AuditReport, raw_agent_output: str) -> AuditReport:
    issues = [*heuristic.issues, *agent.issues]
    lost = [*heuristic.lost_information, *agent.lost_information]
    enc = [*heuristic.encoding_problems, *agent.encoding_problems]
    media = [*heuristic.media_problems, *agent.media_problems]
    blocking = any(issue.severity in {"blocker", "major"} for issue in issues)
    return AuditReport(
        ok=(heuristic.ok and agent.ok and not blocking),
        score=min(heuristic.score, agent.score),
        summary=f"Heuristic: {heuristic.summary} Agent: {agent.summary}",
        issues=issues,
        lost_information=lost,
        encoding_problems=enc,
        media_problems=media,
        raw_agent_output=raw_agent_output,
    )
