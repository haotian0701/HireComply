"""Bias Scanner Node.

Analyzes JD text for potential bias indicators.
Core component of EU AI Act Article 10 (bias mitigation) compliance.
"""

from __future__ import annotations

import yaml

from src.models.state import BiasFlag, BiasRiskLevel, GraphState, PipelineStatus
from src.utils.audit_logger import log_node_action
from src.utils.json_utils import parse_llm_json
from src.utils.llm_factory import get_llm

NODE_NAME = "scan_bias"


def _load_prompts() -> dict:
    with open("configs/prompts.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["bias_scanner"]


def _calculate_risk_level(flags: list[BiasFlag]) -> BiasRiskLevel:
    """Determine overall bias risk from individual flags."""
    if not flags:
        return BiasRiskLevel.LOW

    severities = [f.severity for f in flags]
    if BiasRiskLevel.HIGH in severities:
        return BiasRiskLevel.HIGH
    if len([s for s in severities if s == BiasRiskLevel.MEDIUM]) >= 2:
        return BiasRiskLevel.HIGH
    if BiasRiskLevel.MEDIUM in severities:
        return BiasRiskLevel.MEDIUM
    return BiasRiskLevel.LOW


def scan_bias(state: GraphState) -> dict:
    """Scan JD for bias indicators.

    Reads: jd_raw (or jd_debiased if exists)
    Writes: bias_flags, bias_risk_level, status, audit_trail
    """
    text = state.get("jd_debiased") or state["jd_raw"]
    prompts = _load_prompts()
    llm = get_llm()

    response = llm.invoke([
        {"role": "system", "content": prompts["system"]},
        {"role": "user", "content": prompts["user"].format(text=text)},
    ])

    parsed = parse_llm_json(response.content)

    bias_flags = [
        BiasFlag(
            source="jd",
            text=flag["text"],
            bias_type=flag["bias_type"],
            severity=BiasRiskLevel(flag.get("severity", "low")),
            suggestion=flag.get("suggestion", ""),
        )
        for flag in parsed.get("flags", [])
    ]

    risk_level = _calculate_risk_level(bias_flags)

    audit_trail = log_node_action(
        state=state,
        node_name=NODE_NAME,
        action="Scanned job description for bias indicators",
        input_summary=f"JD text ({len(text)} chars)",
        output_summary=f"Found {len(bias_flags)} bias flags, risk level: {risk_level.value}",
        model_used=str(llm.model_name if hasattr(llm, 'model_name') else 'unknown'),
        reasoning=f"LLM bias analysis covering gender, age, ethnicity, disability, socioeconomic dimensions",
    )

    return {
        "bias_flags": bias_flags,
        "bias_risk_level": risk_level,
        "status": PipelineStatus.BIAS_SCANNED,
        "audit_trail": audit_trail,
    }
