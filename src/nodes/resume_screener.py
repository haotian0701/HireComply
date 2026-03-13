"""Resume Screener Node.

Evaluates candidates against structured JD requirements.
Every score includes an explicit reasoning chain for transparency.
"""

from __future__ import annotations

import yaml

from src.models.state import CandidateScore, GraphState, PipelineStatus
from src.utils.audit_logger import log_node_action
from src.utils.json_utils import parse_llm_json
from src.utils.llm_factory import get_llm

NODE_NAME = "screen_resumes"


def _load_prompts() -> dict:
    with open("configs/prompts.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["resume_screener"]


def _format_requirements(requirements) -> str:
    """Format requirements for the prompt."""
    lines = []
    for i, req in enumerate(requirements, 1):
        marker = "REQUIRED" if req.required else "PREFERRED"
        lines.append(f"{i}. [{marker}] [{req.category}] {req.description} (weight: {req.weight})")
    return "\n".join(lines)


def screen_resumes(state: GraphState) -> dict:
    """Screen all resumes against JD requirements.

    Reads: jd_requirements, resumes_raw
    Writes: candidate_scores, shortlist, status, audit_trail
    """
    requirements = state["jd_requirements"]
    resumes = state.get("resumes_raw", [])
    prompts = _load_prompts()
    llm = get_llm()

    req_text = _format_requirements(requirements)
    scores: list[CandidateScore] = []
    shortlist: list[str] = []

    for resume in resumes:
        response = llm.invoke([
            {"role": "system", "content": prompts["system"]},
            {"role": "user", "content": prompts["user"].format(
                requirements=req_text,
                resume_text=resume.get("text", ""),
            )},
        ])

        parsed = parse_llm_json(response.content)

        score = CandidateScore(
            candidate_id=resume["candidate_id"],
            name=resume.get("name", "Unknown"),
            overall_score=parsed.get("overall_score", 0.0),
            requirement_scores=parsed.get("requirement_scores", {}),
            reasoning=parsed.get("reasoning", ""),
            strengths=parsed.get("strengths", []),
            gaps=parsed.get("gaps", []),
        )
        scores.append(score)

        # TODO: make threshold configurable via settings
        if score.overall_score >= 0.5:
            shortlist.append(score.candidate_id)

    # Sort by score descending
    scores.sort(key=lambda s: s.overall_score, reverse=True)

    audit_trail = log_node_action(
        state=state,
        node_name=NODE_NAME,
        action="Screened resumes against job requirements",
        input_summary=f"{len(resumes)} resumes, {len(requirements)} requirements",
        output_summary=f"{len(shortlist)}/{len(resumes)} candidates shortlisted",
        model_used=str(llm.model_name if hasattr(llm, 'model_name') else 'unknown'),
        reasoning="Weighted scoring with per-requirement evidence chains",
    )

    return {
        "candidate_scores": scores,
        "shortlist": shortlist,
        "status": PipelineStatus.SCREENED,
        "audit_trail": audit_trail,
    }
