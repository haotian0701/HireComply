# EU AI Act Compliance Mapping — HireComply

This document maps EU AI Act requirements for high-risk AI systems
(recruitment is classified under Annex III) to HireComply's implementation.

**Reference**: Regulation (EU) 2024/1689 (AI Act)
**Enforcement date**: August 2, 2026 (for high-risk system obligations)

---

## Article 9 — Risk Management System

| Requirement | Implementation |
|---|---|
| Identify and analyse known/foreseeable risks | `bias_scanner` node runs on every JD before screening |
| Estimate and evaluate risks from intended use | Rule-based `bias_detector` + LLM-based scanner (dual layer) |
| Adopt risk management measures | Conditional routing: HIGH bias → pipeline blocked until human review |
| Testing with appropriate metrics | Unit tests for bias detector, eval suite for screening accuracy |

## Article 10 — Data and Data Governance

| Requirement | Implementation |
|---|---|
| Training data quality | Not applicable (no fine-tuned model; uses foundation model APIs) |
| Bias examination of datasets | `bias_scanner` checks JD text; screening node checks for disparate scoring patterns |
| Data relevance and representativeness | Resume parsing extracts only job-relevant information |

## Article 12 — Record-keeping

| Requirement | Implementation |
|---|---|
| Automatic logging of events | `audit_logger` records every node execution with timestamps |
| Traceability of AI decisions | Each `CandidateScore` includes full `reasoning` chain |
| Log retention | PostgreSQL persistence via LangGraph checkpointer |
| Identify input data reference | `AuditEntry.input_summary` captures what data each node processed |

## Article 13 — Transparency

| Requirement | Implementation |
|---|---|
| Instructions for use | This documentation + README |
| Understandable output | Scoring includes per-requirement breakdown with evidence quotes |
| Human-interpretable explanations | `reasoning` field in CandidateScore; `compliance_report` node |
| Inform candidates about AI use | Compliance report includes candidate notification template |

## Article 14 — Human Oversight

| Requirement | Implementation |
|---|---|
| Human oversight during use | `human_review` node with LangGraph `interrupt()` |
| Ability to override AI decisions | Human can approve, reject, or modify shortlist |
| Understanding of AI capabilities/limitations | Review summary shows confidence scores and identified gaps |
| At least two qualified persons for oversight | Configurable; audit trail records reviewer identity |

## Article 26 — Deployer Obligations

| Requirement | Implementation |
|---|---|
| Use in accordance with instructions | Prompts externalized in `prompts.yaml`; configurable thresholds |
| Assign human oversight to competent persons | Reviewer identity captured in audit trail |
| Monitor operation for risks | LangSmith integration for production monitoring |
| Inform workers' representatives | Compliance report generation for stakeholder communication |

---

## Implementation Status

- [x] Risk management (bias detection + conditional routing)
- [x] Record-keeping (audit trail on every node)
- [x] Transparency (explainable scoring with reasoning chains)
- [x] Human oversight (interrupt-based review node)
- [ ] Candidate notification template generation
- [ ] GDPR Data Protection Impact Assessment template
- [ ] Multi-reviewer support (currently single reviewer)
- [ ] Bias monitoring dashboard for production use
- [ ] CE marking documentation package

---

## Relevant Regulations (Cross-reference)

- **GDPR Article 22**: Right not to be subject to solely automated decisions
  → HireComply enforces human-in-the-loop at screening stage
- **GDPR Article 35**: DPIA requirement for high-risk processing
  → Compliance report provides inputs for DPIA
- **NYC Local Law 144**: Annual bias audit for automated employment decision tools
  → Bias scanner + audit trail support annual audit requirements
- **Colorado AI Act (SB 24-205)**: Impact assessments for high-risk AI
  → Compliance report maps to impact assessment structure
