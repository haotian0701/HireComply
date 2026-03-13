"""Interview Question Generation Node.

Generates structured, competency-based interview questions
tailored to each candidate's profile and identified gaps.
Questions are standardized across candidates for fairness.
"""

from __future__ import annotations

import yaml

from src.models.state import GraphState, InterviewQuestion, PipelineStatus
from src.utils.audit_logger import log_node_action
from src.utils.json_utils import parse_llm_json
from src.utils.llm_factory import get_llm

NODE_NAME = "generate_interview_questions"


def _load_prompts() -> dict:
    with open("configs/prompts.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["interview_gen"]


def _to_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [text]


def _normalize_questions(parsed: dict) -> list[InterviewQuestion]:
    raw_questions = (
        parsed.get("questions")
        or parsed.get("interview_questions")
        or parsed.get("items")
        or parsed.get("output")
        or []
    )

    if isinstance(raw_questions, dict):
        raw_questions = [raw_questions]

    questions: list[InterviewQuestion] = []
    for item in raw_questions:
        if isinstance(item, str):
            text = item.strip()
            if not text:
                continue
            questions.append(
                InterviewQuestion(
                    competency="general",
                    question=text,
                    follow_ups=[
                        "What specific actions did you take?",
                        "What was the measurable result?",
                    ],
                    evaluation_criteria="Clarity of actions, relevance, and impact.",
                )
            )
            continue

        if not isinstance(item, dict):
            continue

        competency = (
            item.get("competency")
            or item.get("skill")
            or item.get("requirement")
            or item.get("gap")
            or item.get("topic")
            or "general"
        )
        question_text = (
            item.get("question")
            or item.get("prompt")
            or item.get("text")
            or ""
        ).strip()
        if not question_text:
            continue

        follow_ups = _to_list(
            item.get("follow_ups")
            or item.get("followups")
            or item.get("probes")
        )
        evaluation_criteria = (
            item.get("evaluation_criteria")
            or item.get("rubric")
            or item.get("scoring_criteria")
            or item.get("what_good_looks_like")
            or ""
        )

        questions.append(
            InterviewQuestion(
                competency=str(competency),
                question=question_text,
                follow_ups=follow_ups,
                evaluation_criteria=str(evaluation_criteria),
            )
        )

    return questions


def _fallback_questions(requirements, gaps: list[str]) -> list[InterviewQuestion]:
    seeds: list[tuple[str, str]] = []

    for gap in gaps:
        if gap and gap != "No specific gaps identified":
            seeds.append(("gap", gap))

    for requirement in requirements:
        seeds.append((requirement.category, requirement.description))

    if not seeds:
        seeds = [("general", "role-relevant problem solving")]

    target_count = 5
    generated: list[InterviewQuestion] = []
    for index in range(target_count):
        category, topic = seeds[index % len(seeds)]
        generated.append(
            InterviewQuestion(
                competency=topic,
                question=(
                    f"Describe a situation where you had to demonstrate {topic}. "
                    "What was the context, what actions did you take, and what was the result?"
                ),
                follow_ups=[
                    "What trade-offs did you consider when choosing your approach?",
                    "What would you do differently next time and why?",
                ],
                evaluation_criteria=(
                    f"Assesses evidence of {category} competency, structured STAR storytelling, "
                    "and measurable impact."
                ),
            )
        )

    return generated


def generate_interview_questions(state: GraphState) -> dict:
    """Generate structured interview questions for shortlisted candidates.

    Reads: jd_requirements, candidate_scores, shortlist
    Writes: interview_questions, status, audit_trail
    """
    requirements = state["jd_requirements"]
    scores = state.get("candidate_scores", [])
    shortlist = state.get("shortlist", [])
    prompts = _load_prompts()
    llm = get_llm()

    req_text = "\n".join(
        f"- [{r.category}] {r.description}" for r in requirements
    )

    # Aggregate common gaps across shortlisted candidates
    all_gaps = []
    for s in scores:
        if s.candidate_id in shortlist:
            all_gaps.extend(s.gaps)

    # Deduplicate gaps
    unique_gaps = list(set(all_gaps)) if all_gaps else ["No specific gaps identified"]

    candidate_summary = f"{len(shortlist)} candidates shortlisted"

    response = llm.invoke([
        {"role": "system", "content": prompts["system"]},
        {"role": "user", "content": prompts["user"].format(
            requirements=req_text,
            candidate_summary=candidate_summary,
            gaps="\n".join(f"- {g}" for g in unique_gaps),
        )},
    ])

    parsed = parse_llm_json(response.content)
    questions = _normalize_questions(parsed)
    used_fallback = False
    if not questions:
        questions = _fallback_questions(requirements, unique_gaps)
        used_fallback = True

    audit_trail = log_node_action(
        state=state,
        node_name=NODE_NAME,
        action="Generated structured interview questions",
        input_summary=f"{len(requirements)} requirements, {len(unique_gaps)} gaps identified",
        output_summary=(
            f"Generated {len(questions)} interview questions"
            + (" (fallback template used)" if used_fallback else "")
        ),
        model_used=str(llm.model_name if hasattr(llm, 'model_name') else 'unknown'),
        reasoning="Competency-based STAR format questions, standardized across candidates",
    )

    return {
        "interview_questions": questions,
        "status": PipelineStatus.INTERVIEW_READY,
        "audit_trail": audit_trail,
    }
