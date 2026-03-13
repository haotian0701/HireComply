"""JD Parser Node.

Extracts structured requirements from a raw job description.
"""

from __future__ import annotations

import yaml

from src.models.state import AuditEntry, GraphState, JDRequirement, PipelineStatus
from src.utils.audit_logger import log_node_action
from src.utils.json_utils import parse_llm_json
from src.utils.llm_factory import get_llm

NODE_NAME = "parse_jd"


def _infer_category(description: str) -> str:
    """Infer requirement category from description text."""
    text = (description or "").lower()
    if any(token in text for token in ["python", "fastapi", "django", "postgres", "redis", "docker", "kubernetes", "skill", "tool"]):
        return "hard_skill"
    if any(token in text for token in ["communication", "teamwork", "leadership", "collaboration", "soft"]):
        return "soft_skill"
    if any(token in text for token in ["year", "experience", "senior", "junior"]):
        return "experience"
    if any(token in text for token in ["degree", "bachelor", "master", "phd", "certification", "education"]):
        return "education"
    if any(token in text for token in ["english", "german", "language", "fluent", "proficiency"]):
        return "language"
    return "hard_skill"


def _normalize_requirements(parsed: dict) -> list[JDRequirement]:
    """Normalize various LLM output schemas into JDRequirement list."""
    raw_requirements = (
        parsed.get("requirements")
        or parsed.get("job_requirements")
        or parsed.get("criteria")
        or parsed.get("must_have")
        or []
    )

    # Some models may return a single object
    if isinstance(raw_requirements, dict):
        raw_requirements = [raw_requirements]

    # Some models may return list[str]
    normalized: list[JDRequirement] = []
    for req in raw_requirements:
        if isinstance(req, str):
            description = req.strip()
            if not description:
                continue
            normalized.append(
                JDRequirement(
                    category=_infer_category(description),
                    description=description,
                    required=True,
                    weight=1.0,
                )
            )
            continue

        if not isinstance(req, dict):
            continue

        description = (
            req.get("description")
            or req.get("text")
            or req.get("requirement")
            or req.get("name")
            or ""
        ).strip()
        if not description:
            continue

        category = (
            req.get("category")
            or req.get("type")
            or req.get("kind")
            or _infer_category(description)
        )

        required = req.get("required")
        if required is None:
            required = req.get("must_have")
        if required is None:
            required = req.get("is_required")
        if isinstance(required, str):
            required = required.strip().lower() in {"true", "yes", "required", "must", "must-have"}
        if required is None:
            required = True

        weight = req.get("weight", 1.0)
        try:
            weight = float(weight)
        except (TypeError, ValueError):
            weight = 1.0

        normalized.append(
            JDRequirement(
                category=str(category),
                description=description,
                required=bool(required),
                weight=weight,
            )
        )

    return normalized


def _load_prompts() -> dict:
    with open("configs/prompts.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["jd_parser"]


def parse_jd(state: GraphState) -> dict:
    """Parse raw JD text into structured requirements.

    Reads: jd_raw
    Writes: jd_title, jd_requirements, jd_structured, status, audit_trail
    """
    jd_raw = state["jd_raw"]
    prompts = _load_prompts()
    llm = get_llm()

    # Call LLM to parse
    response = llm.invoke([
        {"role": "system", "content": prompts["system"]},
        {"role": "user", "content": prompts["user"].format(jd_text=jd_raw)},
    ])

    # Parse structured output
    parsed = parse_llm_json(response.content)

    requirements = _normalize_requirements(parsed)

    # Audit
    audit_trail = log_node_action(
        state=state,
        node_name=NODE_NAME,
        action="Parsed job description into structured requirements",
        input_summary=f"JD text ({len(jd_raw)} chars)",
        output_summary=f"Extracted {len(requirements)} requirements",
        model_used=str(llm.model_name if hasattr(llm, 'model_name') else 'unknown'),
        reasoning="LLM-based extraction with structured JSON output",
    )

    return {
        "jd_title": parsed.get("title", "Untitled Position"),
        "jd_requirements": requirements,
        "jd_structured": parsed,
        "status": PipelineStatus.JD_PARSED,
        "audit_trail": audit_trail,
    }
