"""HireComply Recruitment Graph.

The main LangGraph state graph that orchestrates the entire
compliance-first recruitment pipeline.

Graph flow:
    parse_jd → scan_bias → [route_bias] → screen_resumes
    → human_review (interrupt) → [route_review]
    → generate_interview_questions → generate_compliance_report
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.models.state import BiasRiskLevel, GraphState, PipelineStatus
from src.nodes.bias_scanner import scan_bias
from src.nodes.compliance_report import generate_compliance_report
from src.nodes.human_review import human_review
from src.nodes.interview_gen import generate_interview_questions
from src.nodes.jd_parser import parse_jd
from src.nodes.resume_screener import screen_resumes


# ── Routing functions ──────────────────────────────────────────


def route_after_bias(state: GraphState) -> str:
    """Route based on bias scan results.

    If HIGH bias risk → loop back for JD revision (future: auto-debias node)
    Otherwise → proceed to screening
    """
    if state.get("bias_risk_level") == BiasRiskLevel.HIGH:
        # For v0.1: high bias = stop and require human fix
        # For v0.2: auto-debias node that rewrites the JD
        return "human_review"
    return "screen_resumes"


def route_after_review(state: GraphState) -> str:
    """Route based on human review decision."""
    if state.get("human_approved"):
        return "generate_interview_questions"
    return END  # Rejected — pipeline ends


# ── Graph definition ───────────────────────────────────────────


def build_graph(checkpointer=None) -> StateGraph:
    """Build and compile the recruitment pipeline graph.

    Args:
        checkpointer: LangGraph checkpointer for state persistence.
                      Use MemorySaver for dev, PostgresSaver for prod.
    """
    graph = StateGraph(GraphState)

    # ── Add nodes ──
    graph.add_node("parse_jd", parse_jd)
    graph.add_node("scan_bias", scan_bias)
    graph.add_node("screen_resumes", screen_resumes)
    graph.add_node("human_review", human_review)
    graph.add_node("generate_interview_questions", generate_interview_questions)
    graph.add_node("generate_compliance_report", generate_compliance_report)

    # ── Define edges ──
    graph.set_entry_point("parse_jd")

    graph.add_edge("parse_jd", "scan_bias")

    graph.add_conditional_edges(
        "scan_bias",
        route_after_bias,
        {
            "screen_resumes": "screen_resumes",
            "human_review": "human_review",  # HIGH bias → immediate review
        },
    )

    graph.add_edge("screen_resumes", "human_review")

    graph.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            "generate_interview_questions": "generate_interview_questions",
            END: END,
        },
    )

    graph.add_edge("generate_interview_questions", "generate_compliance_report")
    graph.add_edge("generate_compliance_report", END)

    # ── Compile ──
    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],  # Pause for human input
    )


# Convenience: default compiled graph for quick testing
def get_default_graph():
    """Get a compiled graph with in-memory checkpointer."""
    return build_graph()
