"""Human Review Node.

This node triggers a LangGraph interrupt, pausing the pipeline
until a human reviewer approves, rejects, or modifies the shortlist.

This is the core of EU AI Act Article 14 (Human Oversight) compliance.
"""

from __future__ import annotations

from langgraph.types import interrupt

from src.models.state import GraphState, PipelineStatus
from src.utils.audit_logger import log_node_action

NODE_NAME = "human_review"


def human_review(state: GraphState) -> dict:
    """Pause pipeline for human review.

    The interrupt() call suspends execution. When the pipeline is
    resumed (via graph.invoke with updated state or Command), the
    human's decision is captured in the state.

    Reads: candidate_scores, shortlist, bias_flags
    Writes: human_approved, human_reviewer, human_notes, status, audit_trail
    """
    # Prepare review summary for the human
    scores = state.get("candidate_scores", [])
    shortlist = state.get("shortlist", [])
    bias_flags = state.get("bias_flags", [])

    review_summary = {
        "shortlisted_candidates": [
            {
                "id": s.candidate_id,
                "name": s.name,
                "score": s.overall_score,
                "strengths": s.strengths,
                "gaps": s.gaps,
            }
            for s in scores
            if s.candidate_id in shortlist
        ],
        "rejected_candidates": [
            {
                "id": s.candidate_id,
                "name": s.name,
                "score": s.overall_score,
                "reasoning": s.reasoning,
            }
            for s in scores
            if s.candidate_id not in shortlist
        ],
        "bias_flags": [
            {"type": f.bias_type, "text": f.text, "severity": f.severity.value}
            for f in bias_flags
        ],
    }

    # ── Interrupt: wait for human input ──
    human_input = interrupt(review_summary)

    # After resume, human_input contains the reviewer's decision
    approved = human_input.get("approved", False)
    reviewer = human_input.get("reviewer", "unknown")
    notes = human_input.get("notes", "")
    overrides = human_input.get("overrides", {})

    audit_trail = log_node_action(
        state=state,
        node_name=NODE_NAME,
        action="Human review completed",
        input_summary=f"{len(shortlist)} candidates presented for review",
        output_summary=f"{'Approved' if approved else 'Rejected'} by {reviewer}",
        human_involved=True,
        human_decision=f"{'Approved' if approved else 'Rejected'}. Notes: {notes}",
    )

    return {
        "human_approved": approved,
        "human_reviewer": reviewer,
        "human_notes": notes,
        "human_overrides": overrides,
        "status": PipelineStatus.APPROVED if approved else PipelineStatus.REJECTED,
        "audit_trail": audit_trail,
    }
