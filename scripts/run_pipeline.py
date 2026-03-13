"""CLI entry point for running the HireComply pipeline.

Usage:
    python -m scripts.run_pipeline
    python -m scripts.run_pipeline --jd data/sample_jds/backend_engineer.json
    python scripts/run_pipeline.py --jd data/sample_jds/backend_engineer.json
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
import uuid
from datetime import datetime
from pathlib import Path

# Ensure project root is importable when running as a script:
#   python scripts/run_pipeline.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.recruitment_graph import get_default_graph
from src.models.state import PipelineStatus


SAMPLE_JD = """
Senior Backend Engineer - Stuttgart, Germany

We are looking for a young and dynamic software engineer to join our
fast-paced team. The ideal candidate is a digital native who thrives
in a high-energy startup environment.

Requirements:
- 5+ years of Python experience
- Strong knowledge of FastAPI or Django
- Experience with PostgreSQL and Redis
- Familiarity with Docker and Kubernetes
- Excellent English communication skills
- Bachelor's degree from a top-tier university

Nice to have:
- Experience with LLMs and AI/ML
- German language skills
- Contributions to open-source projects
"""

SAMPLE_RESUMES = [
    {
        "candidate_id": "c001",
        "name": "Alice Zhang",
        "text": """
        Alice Zhang — Senior Software Engineer
        7 years Python experience. Expert in FastAPI, PostgreSQL, Redis.
        Built microservices serving 10M+ requests/day. Docker/K8s daily user.
        MSc Computer Science, TU Munich. Fluent English and German.
        Active open-source contributor (500+ GitHub stars).
        Recently exploring LangChain and LLM integration.
        """,
    },
    {
        "candidate_id": "c002",
        "name": "Bob Mueller",
        "text": """
        Bob Mueller — Software Developer
        3 years experience with Python and Django.
        Basic PostgreSQL knowledge. Learning Docker.
        BSc from local university. Good English skills.
        Interested in AI but no hands-on experience.
        """,
    },
]


def _save_markdown_output(pipeline_id: str, result: dict, approved: bool) -> Path:
    """Save pipeline results to a markdown file in the repository."""
    output_dir = PROJECT_ROOT / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"{pipeline_id}_{timestamp}_report.md"

    status = result.get("status", "unknown")
    bias_flags = result.get("bias_flags", [])
    scores = result.get("candidate_scores", [])
    questions = result.get("interview_questions", [])
    audit = result.get("audit_trail", [])
    compliance_report = result.get("compliance_report", "No report generated")

    lines: list[str] = []
    lines.append(f"# HireComply Run Report — {pipeline_id}")
    lines.append("")
    lines.append(f"- Generated at: {datetime.utcnow().isoformat()}")
    lines.append(f"- Final status: {status}")
    lines.append(f"- Human decision: {'approved' if approved else 'rejected'}")
    lines.append(f"- Bias flags: {len(bias_flags)}")
    lines.append(f"- Candidates screened: {len(scores)}")
    lines.append(f"- Interview questions: {len(questions)}")
    lines.append(f"- Audit entries: {len(audit)}")
    lines.append("")

    if scores:
        lines.append("## Candidate Scores")
        lines.append("")
        shortlist = set(result.get("shortlist", []))
        for score in scores:
            marker = "✅" if score.candidate_id in shortlist else "❌"
            lines.append(f"- {marker} {score.name} ({score.candidate_id}): {score.overall_score:.2f}")
        lines.append("")

    if questions:
        lines.append("## Interview Questions")
        lines.append("")
        for index, question in enumerate(questions, 1):
            lines.append(f"### Q{index} — {question.competency}")
            lines.append(question.question)
            if question.follow_ups:
                lines.append("")
                lines.append("Follow-ups:")
                for follow_up in question.follow_ups:
                    lines.append(f"- {follow_up}")
            if question.evaluation_criteria:
                lines.append("")
                lines.append(f"Evaluation: {question.evaluation_criteria}")
            lines.append("")

    lines.append("## Compliance Report")
    lines.append("")
    lines.append(str(compliance_report))
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Run HireComply pipeline")
    parser.add_argument("--jd", type=str, help="Path to JD JSON file")
    args = parser.parse_args()

    # Load JD
    if args.jd:
        with open(args.jd) as f:
            jd_data = json.load(f)
            jd_text = jd_data.get("text", jd_data.get("jd_raw", ""))
    else:
        print("Using sample JD (note: it contains intentional bias for testing)")
        jd_text = SAMPLE_JD

    # Build initial state
    initial_state = {
        "pipeline_id": str(uuid.uuid4())[:8],
        "status": PipelineStatus.PENDING,
        "created_at": datetime.utcnow().isoformat(),
        "jd_raw": jd_text,
        "resumes_raw": SAMPLE_RESUMES,
        "audit_trail": [],
    }

    # Config for checkpointer thread
    config = {"configurable": {"thread_id": initial_state["pipeline_id"]}}

    graph = get_default_graph()

    print(f"{'='*60}")
    print(f"  HireComply Pipeline — {initial_state['pipeline_id']}")
    print(f"{'='*60}\n")

    # Run until interrupt (human review)
    print("[1/6] Starting pipeline...\n")
    try:
        result = graph.invoke(initial_state, config)
    except Exception as error:
        error_result = {
            "status": "failed",
            "audit_trail": initial_state.get("audit_trail", []),
            "compliance_report": (
                "## Pipeline Execution Error\n\n"
                "The pipeline failed before human review.\n\n"
                "```text\n"
                f"{traceback.format_exc()}"
                "```"
            ),
        }
        saved_path = _save_markdown_output(initial_state["pipeline_id"], error_result, approved=False)
        print(f"\n  ✗ Pipeline failed: {error}")
        print(f"  Saved markdown report: {saved_path.relative_to(PROJECT_ROOT)}")
        return

    print(f"\n  Status: {result.get('status', 'unknown')}")
    print(f"  Bias flags: {len(result.get('bias_flags', []))}")
    for flag in result.get("bias_flags", []):
        print(f"    ⚠ [{flag.severity.value}] {flag.bias_type}: {flag.text}")
        if flag.suggestion:
            print(f"      → Suggestion: {flag.suggestion}")

    print(f"\n  Candidates screened: {len(result.get('candidate_scores', []))}")
    for score in result.get("candidate_scores", []):
        marker = "✓" if score.candidate_id in result.get("shortlist", []) else "✗"
        print(f"    {marker} {score.name}: {score.overall_score:.2f}")

    # ── Human review interrupt ──
    print(f"\n{'─'*60}")
    print("  PIPELINE PAUSED — Human Review Required")
    print(f"{'─'*60}")
    print("\n  [Press Enter to approve, or type 'reject' to reject]")

    user_input = input("  > ").strip().lower()
    approved = user_input != "reject"

    from langgraph.types import Command

    # Resume with human decision
    try:
        result = graph.invoke(
            Command(resume={"approved": approved, "reviewer": "cli_user", "notes": user_input or "Approved via CLI"}),
            config,
        )
    except Exception as error:
        error_result = {
            **result,
            "status": "failed",
            "compliance_report": (
                "## Pipeline Execution Error\n\n"
                "The pipeline failed after human review during final stages.\n\n"
                "```text\n"
                f"{traceback.format_exc()}"
                "```"
            ),
        }
        saved_path = _save_markdown_output(initial_state["pipeline_id"], error_result, approved=approved)
        print(f"\n  ✗ Pipeline failed: {error}")
        print(f"  Saved markdown report: {saved_path.relative_to(PROJECT_ROOT)}")
        return

    if approved:
        print(f"\n  ✓ Approved — generating interview questions...")
        questions = result.get("interview_questions", [])
        print(f"  Generated {len(questions)} questions\n")
        for i, q in enumerate(questions, 1):
            print(f"  Q{i} [{q.competency}]: {q.question}")

        print(f"\n{'─'*60}")
        print("  COMPLIANCE REPORT")
        print(f"{'─'*60}")
        print(result.get("compliance_report", "No report generated"))
    else:
        print("\n  ✗ Pipeline rejected by reviewer")

    # Print audit summary
    audit = result.get("audit_trail", [])
    print(f"\n{'='*60}")
    print(f"  Audit trail: {len(audit)} entries recorded")
    print(f"{'='*60}")

    saved_path = _save_markdown_output(initial_state["pipeline_id"], result, approved)
    print(f"\n  Saved markdown report: {saved_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
