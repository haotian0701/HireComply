"""Compliance Report Generation Node.

Generates a structured EU AI Act compliance report from
the pipeline's audit trail. This is the final node.
"""

from __future__ import annotations

import yaml

from src.models.state import GraphState, PipelineStatus
from src.utils.audit_logger import format_audit_trail, log_node_action
from src.utils.llm_factory import get_llm

NODE_NAME = "generate_compliance_report"


def _load_prompts() -> dict:
    with open("configs/prompts.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["compliance_report"]


def generate_compliance_report(state: GraphState) -> dict:
    """Generate EU AI Act compliance report.

    Reads: pipeline_id, jd_title, audit_trail, candidate_scores
    Writes: compliance_report, status, audit_trail
    """
    prompts = _load_prompts()
    llm = get_llm()

    audit_entries = state.get("audit_trail", [])
    audit_text = format_audit_trail(audit_entries)

    num_candidates = len(state.get("resumes_raw", []))

    response = llm.invoke([
        {"role": "system", "content": prompts["system"]},
        {"role": "user", "content": prompts["user"].format(
            pipeline_id=state.get("pipeline_id", "unknown"),
            jd_title=state.get("jd_title", "Unknown Position"),
            num_candidates=num_candidates,
            audit_trail=audit_text,
        )},
    ])

    report = response.content

    audit_trail = log_node_action(
        state=state,
        node_name=NODE_NAME,
        action="Generated EU AI Act compliance report",
        input_summary=f"{len(audit_entries)} audit entries processed",
        output_summary=f"Compliance report generated ({len(report)} chars)",
        model_used=str(llm.model_name if hasattr(llm, 'model_name') else 'unknown'),
        reasoning="Report covers: process overview, human oversight, transparency, bias mitigation, data governance, risk assessment",
    )

    return {
        "compliance_report": report,
        "status": PipelineStatus.COMPLETED,
        "audit_trail": audit_trail,
    }
