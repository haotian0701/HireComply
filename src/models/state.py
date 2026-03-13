"""Graph state schema for the HireComply recruitment pipeline.

This TypedDict defines the complete state that flows through
every node in the LangGraph. Every field change is automatically
tracked by the checkpointer for audit trail purposes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class PipelineStatus(str, Enum):
    """Overall pipeline status."""
    PENDING = "pending"
    JD_PARSED = "jd_parsed"
    BIAS_SCANNED = "bias_scanned"
    SCREENED = "screened"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    INTERVIEW_READY = "interview_ready"
    COMPLETED = "completed"


class BiasRiskLevel(str, Enum):
    """Bias risk classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ── Structured sub-models ──────────────────────────────────────


@dataclass
class JDRequirement:
    """A single extracted requirement from the job description."""
    category: str  # "hard_skill", "soft_skill", "experience", "education", "language"
    description: str
    required: bool  # True = must-have, False = nice-to-have
    weight: float = 1.0  # Scoring weight


@dataclass
class BiasFlag:
    """A detected bias issue."""
    source: str  # "jd" or "screening"
    text: str  # The problematic text
    bias_type: str  # "gender", "age", "ethnicity", "disability", etc.
    severity: BiasRiskLevel = BiasRiskLevel.LOW
    suggestion: str = ""  # Suggested fix


@dataclass
class CandidateScore:
    """Scoring result for a single candidate."""
    candidate_id: str
    name: str
    overall_score: float  # 0.0 - 1.0
    requirement_scores: dict[str, float] = field(default_factory=dict)
    reasoning: str = ""  # Explainable reason chain
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


@dataclass
class InterviewQuestion:
    """A generated structured interview question."""
    competency: str  # Which requirement/skill this tests
    question: str
    follow_ups: list[str] = field(default_factory=list)
    evaluation_criteria: str = ""


@dataclass
class AuditEntry:
    """A single audit trail entry for compliance."""
    node_name: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    action: str = ""
    input_summary: str = ""
    output_summary: str = ""
    human_involved: bool = False
    human_decision: str = ""  # What the human decided (if applicable)
    model_used: str = ""
    reasoning: str = ""


# ── Main Graph State ───────────────────────────────────────────


class GraphState(TypedDict, total=False):
    """Complete state for the HireComply recruitment graph.

    Every node reads from and writes to this state.
    LangGraph's checkpointer persists every state transition,
    giving us a built-in audit trail for EU AI Act compliance.
    """

    # ── Pipeline metadata ──
    pipeline_id: str
    status: PipelineStatus
    created_at: str
    updated_at: str

    # ── Job Description ──
    jd_raw: str  # Original JD text
    jd_title: str
    jd_requirements: list[JDRequirement]
    jd_structured: dict  # Full structured JD output

    # ── Bias Detection ──
    bias_flags: list[BiasFlag]
    bias_risk_level: BiasRiskLevel
    jd_debiased: str  # Cleaned JD text (if bias was found)

    # ── Resume Screening ──
    resumes_raw: list[dict]  # [{candidate_id, name, text, metadata}]
    candidate_scores: list[CandidateScore]
    shortlist: list[str]  # candidate_ids that passed screening

    # ── Human Review ──
    human_reviewer: str  # Who reviewed
    human_approved: bool
    human_notes: str
    human_overrides: dict  # Any changes the human made

    # ── Interview Generation ──
    interview_questions: list[InterviewQuestion]

    # ── Compliance ──
    audit_trail: list[AuditEntry]
    compliance_report: str  # Final generated report

    # ── Conversation (for interactive mode) ──
    messages: Annotated[list, add_messages]
