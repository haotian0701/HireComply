"""Rule-based Bias Detector Tool.

A deterministic, keyword-based bias detector that runs alongside
the LLM-based bias scanner. Having both ensures:
1. Speed: rule-based check is instant
2. Reliability: doesn't depend on LLM availability
3. Auditability: rules are explicit and verifiable
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class BiasMatch:
    """A single bias detection match."""
    text: str
    bias_type: str
    severity: str  # "low", "medium", "high"
    suggestion: str
    rule_id: str


# ── Bias detection rules ───────────────────────────────────────
# Each rule: (pattern, bias_type, severity, suggestion, rule_id)
# Patterns are case-insensitive regex

BIAS_RULES: list[tuple[str, str, str, str, str]] = [
    # Gender bias
    (r"\b(he|his|him)\b(?!\s+(or she|/her))", "gender", "medium",
     "Use gender-neutral pronouns (they/them) or 'the candidate'", "G001"),
    (r"\b(she|her|hers)\b(?!\s+(or he|/him))", "gender", "medium",
     "Use gender-neutral pronouns (they/them) or 'the candidate'", "G002"),
    (r"\b(aggressive|dominant|assertive)\b", "gender", "low",
     "Consider 'driven', 'proactive', or 'results-oriented'", "G003"),
    (r"\b(nurturing|supportive|collaborative)\b", "gender", "low",
     "Consider 'team-oriented' or 'empathetic leadership'", "G004"),
    (r"\bman(power|hours|ned)\b", "gender", "low",
     "Use 'workforce', 'work hours', 'staffed'", "G005"),

    # Age bias
    (r"\b(young|youthful)\b", "age", "high",
     "Remove age-related descriptors; focus on skills and experience", "A001"),
    (r"\bdigital native\b", "age", "high",
     "Specify required digital skills instead (e.g., 'proficient in X')", "A002"),
    (r"\b(junior|senior)\b(?!\s+(engineer|developer|manager|analyst|designer))", "age", "low",
     "Clarify this refers to experience level, not age", "A003"),
    (r"\b(energetic|dynamic)\b", "age", "medium",
     "Describe the work environment or pace instead", "A004"),
    (r"\brecent graduate\b", "age", "medium",
     "Specify '0-2 years experience' instead", "A005"),
    (r"\b(mature|seasoned)\b", "age", "low",
     "Specify years of experience instead", "A006"),

    # Ethnicity / nationality bias
    (r"\bnative (english|german|french) speaker\b", "ethnicity", "high",
     "Use 'fluent in X' or 'C1/C2 proficiency in X'", "E001"),
    (r"\bcultural fit\b", "ethnicity", "medium",
     "Define specific values or working styles instead", "E002"),

    # Disability bias
    (r"\bphysically fit\b", "disability", "high",
     "Specify actual physical requirements of the role if any", "D001"),
    (r"\bable-bodied\b", "disability", "high",
     "Remove unless a bona fide occupational qualification", "D002"),
    (r"\bstanding for long periods\b", "disability", "medium",
     "Clarify if this is truly essential or if accommodations are possible", "D003"),

    # Socioeconomic bias
    (r"\btop[- ]tier university\b", "socioeconomic", "high",
     "Focus on skills and knowledge rather than institution prestige", "S001"),
    (r"\belite (school|university|college)\b", "socioeconomic", "high",
     "Focus on relevant qualifications and competencies", "S002"),
    (r"\b(ivy league|oxbridge|russell group)\b", "socioeconomic", "high",
     "Specify required degree level and field instead", "S003"),
]


def detect_bias(text: str) -> list[BiasMatch]:
    """Run all bias rules against the given text.

    Returns a list of BiasMatch objects, sorted by severity (high first).
    """
    matches: list[BiasMatch] = []

    for pattern, bias_type, severity, suggestion, rule_id in BIAS_RULES:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append(BiasMatch(
                text=match.group(0),
                bias_type=bias_type,
                severity=severity,
                suggestion=suggestion,
                rule_id=rule_id,
            ))

    # Sort: high > medium > low
    severity_order = {"high": 0, "medium": 1, "low": 2}
    matches.sort(key=lambda m: severity_order.get(m.severity, 3))

    return matches


def get_bias_summary(matches: list[BiasMatch]) -> dict:
    """Summarize bias detection results."""
    if not matches:
        return {
            "total_flags": 0,
            "risk_level": "low",
            "by_type": {},
            "by_severity": {},
        }

    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}

    for m in matches:
        by_type[m.bias_type] = by_type.get(m.bias_type, 0) + 1
        by_severity[m.severity] = by_severity.get(m.severity, 0) + 1

    # Risk level
    if by_severity.get("high", 0) > 0:
        risk_level = "high"
    elif by_severity.get("medium", 0) >= 2:
        risk_level = "high"
    elif by_severity.get("medium", 0) > 0:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "total_flags": len(matches),
        "risk_level": risk_level,
        "by_type": by_type,
        "by_severity": by_severity,
    }
