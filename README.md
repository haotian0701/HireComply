# HireComply 🛡️

**Compliance-first AI Recruitment Agent powered by LangGraph**

An open-source recruitment pipeline that bakes EU AI Act compliance into every decision node — not as an afterthought, but as architecture.

## Why This Exists

Most AI recruitment tools optimize for speed. HireComply optimizes for **auditability**.

With the EU AI Act classifying recruitment AI as "high-risk" (enforcement begins August 2026), companies need hiring pipelines where every AI decision is explainable, every screening is bias-tested, and every step has a human-in-the-loop checkpoint. HireComply is a reference implementation of exactly that.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   HireComply Graph                   │
│                                                      │
│  ┌──────────┐    ┌──────────┐    ┌───────────────┐  │
│  │ JD Parser │───▶│  Bias    │───▶│  Resume       │  │
│  │ & Struct  │    │  Scanner │    │  Screener     │  │
│  └──────────┘    └──────────┘    └───────┬───────┘  │
│                                          │           │
│                       ┌──────────────────┘           │
│                       ▼                              │
│              ┌─────────────────┐                     │
│              │  Human Review   │ ◄── interrupt()     │
│              │  (Approve/Edit) │                     │
│              └────────┬────────┘                     │
│                       │                              │
│           ┌───────────┴───────────┐                  │
│           ▼                       ▼                  │
│  ┌─────────────────┐    ┌─────────────────┐         │
│  │ Interview Q Gen │    │  Reject with    │         │
│  │ (Structured)    │    │  Explanation    │         │
│  └────────┬────────┘    └─────────────────┘         │
│           │                                          │
│           ▼                                          │
│  ┌─────────────────┐                                 │
│  │ Compliance       │                                │
│  │ Report Generator │                                │
│  └─────────────────┘                                 │
│                                                      │
│  ── All nodes log to AuditTrail (PostgreSQL) ──      │
└─────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer         | Choice              | Why                                         |
|---------------|---------------------|---------------------------------------------|
| Orchestration | LangGraph           | State graph, interrupt/resume, checkpointer |
| LLM Interface | LangChain           | Model-agnostic, easy provider switching     |
| Backend API   | FastAPI             | Async, lightweight, OpenAPI docs             |
| Database      | PostgreSQL          | LangGraph checkpointer + audit logs         |
| Vector Store  | ChromaDB (optional) | Local, zero-cost semantic matching          |
| Observability | LangSmith           | Tracing, eval, debugging                    |
| Frontend      | Streamlit (v1)      | Fast demo UI, upgrade to React later        |

## Project Structure

```
hire-comply/
├── src/
│   ├── agents/
│   │   └── recruitment_graph.py    # Main LangGraph definition
│   ├── nodes/
│   │   ├── jd_parser.py            # JD parsing & structuring
│   │   ├── bias_scanner.py         # Bias detection in JD & screening
│   │   ├── resume_screener.py      # Resume-JD matching with explanations
│   │   ├── human_review.py         # Human-in-the-loop interrupt node
│   │   ├── interview_gen.py        # Structured interview question generation
│   │   └── compliance_report.py    # EU AI Act audit report generation
│   ├── tools/
│   │   ├── resume_parser.py        # PDF/DOCX resume extraction
│   │   └── bias_detector.py        # Bias keyword & pattern detection
│   ├── models/
│   │   └── state.py                # Graph state schema (TypedDict)
│   └── utils/
│       ├── audit_logger.py         # Structured audit trail logging
│       └── llm_factory.py          # LLM provider factory
├── configs/
│   ├── settings.py                 # App configuration (pydantic-settings)
│   └── prompts.yaml                # All LLM prompts (externalized)
├── tests/
│   ├── test_graph.py               # End-to-end graph tests
│   ├── test_bias_scanner.py        # Bias detection unit tests
│   └── test_resume_screener.py     # Screening logic tests
├── data/
│   ├── sample_resumes/             # Example resumes for testing
│   └── sample_jds/                 # Example job descriptions
├── docs/
│   └── COMPLIANCE.md               # EU AI Act mapping documentation
├── scripts/
│   └── run_pipeline.py             # CLI entry point for quick testing
├── pyproject.toml                  # Project metadata & dependencies
├── .env.example                    # Environment variable template
├── .gitignore
└── README.md
```

## Quick Start

```bash
# Clone & setup
git clone https://github.com/YOUR_USERNAME/hire-comply.git
cd hire-comply
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your API keys
# For Gemini free API:
#   LLM_PROVIDER=gemini
#   LLM_MODEL=gemini-2.5-flash
#   GOOGLE_API_KEY=your-key

# Run the pipeline
python -m scripts.run_pipeline --jd data/sample_jds/backend_engineer.json
```

## EU AI Act Compliance Mapping

| AI Act Requirement        | HireComply Implementation                        |
|---------------------------|--------------------------------------------------|
| Human oversight (Art. 14) | `human_review` interrupt node                    |
| Transparency (Art. 13)    | Explainable scoring with reason chains           |
| Record-keeping (Art. 12)  | PostgreSQL audit logger on every node            |
| Bias mitigation (Art. 10) | `bias_scanner` node + structured interview gen   |
| Risk management (Art. 9)  | Conditional routing on bias detection triggers   |

## Roadmap

- [ ] **v0.1** — Core graph: JD parse → screen → human review → interview gen
- [ ] **v0.2** — Bias scanner + audit logging + compliance report
- [ ] **v0.3** — FastAPI backend + Streamlit dashboard
- [ ] **v0.4** — Multi-model support (OpenAI / Anthropic / local)
- [ ] **v0.5** — Vector store for semantic resume matching
- [ ] **v1.0** — Full EU AI Act compliance report generation

## License

MIT
