"""Structured audit trail logger.

Every node in the graph calls this to record its actions.
This is the core of EU AI Act Article 12 (record-keeping) compliance.
Logs are appended to the graph state AND can be persisted to PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime

import structlog

from src.models.state import AuditEntry, GraphState

logger = structlog.get_logger()


def log_node_action(
    state: GraphState,
    node_name: str,
    action: str,
    input_summary: str = "",
    output_summary: str = "",
    human_involved: bool = False,
    human_decision: str = "",
    model_used: str = "",
    reasoning: str = "",
) -> list[AuditEntry]:
    """Create an audit entry and append to the state's audit trail.

    Returns the updated audit_trail list (LangGraph reducer pattern).
    """
    entry = AuditEntry(
        node_name=node_name,
        timestamp=datetime.utcnow().isoformat(),
        action=action,
        input_summary=input_summary,
        output_summary=output_summary,
        human_involved=human_involved,
        human_decision=human_decision,
        model_used=model_used,
        reasoning=reasoning,
    )

    # Also emit a structured log for observability
    logger.info(
        "audit_entry",
        pipeline_id=state.get("pipeline_id", "unknown"),
        node=node_name,
        action=action,
        human_involved=human_involved,
    )

    existing = state.get("audit_trail", [])
    return existing + [entry]


def format_audit_trail(entries: list[AuditEntry]) -> str:
    """Format audit trail as a human-readable markdown report."""
    if not entries:
        return "No audit entries recorded."

    lines = ["# Audit Trail Report\n"]
    lines.append(f"Generated: {datetime.utcnow().isoformat()}\n")
    lines.append(f"Total entries: {len(entries)}\n")

    for i, entry in enumerate(entries, 1):
        lines.append(f"## Step {i}: {entry.node_name}")
        lines.append(f"- **Timestamp**: {entry.timestamp}")
        lines.append(f"- **Action**: {entry.action}")
        if entry.model_used:
            lines.append(f"- **Model**: {entry.model_used}")
        if entry.input_summary:
            lines.append(f"- **Input**: {entry.input_summary}")
        if entry.output_summary:
            lines.append(f"- **Output**: {entry.output_summary}")
        if entry.human_involved:
            lines.append(f"- **Human Review**: Yes")
            lines.append(f"- **Human Decision**: {entry.human_decision}")
        if entry.reasoning:
            lines.append(f"- **Reasoning**: {entry.reasoning}")
        lines.append("")

    return "\n".join(lines)
