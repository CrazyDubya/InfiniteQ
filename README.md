# InfiniteQ Planning Harness

An AI-powered project planning system that transforms rough ideas into detailed, actionable plans through an intelligent multi-model interview process.

**Latest: v0.2** adds profiles, threads, reflections, and execution bundles for immediate project kickoff!

## Overview

InfiniteQ uses multiple Vultr Serverless Inference models to conduct an adaptive interview that progressively refines a project concept into a comprehensive specification. The system maintains a compact plan state and tracks coverage across key dimensions (problem, users, features, architecture, etc.), ensuring thorough exploration without context overflow.

### Key Features

**Core (v0.1):**
- **Multi-Model Interview**: Leverages multiple LLMs (reasoning, coding, strategy, synthesis) to ask better questions
- **Infinite Questioning**: Maintains compact state to enable endless refinement without context limits
- **Coverage-Driven**: Automatically identifies and explores weak areas in your plan
- **Output for AI Agents**: Generates both JSON and Markdown formats ready for Cursor, ClaudeCode, Windsurf, etc.
- **Real-time Progress**: Visual coverage tracking shows planning completeness

**New in v0.2:**
- 🎯 **Project & Persona Profiles**: Context-aware questions based on project type, team size, budget, and your role
- 🧵 **Threads & Modes**: Parallel exploration threads (architecture, UX, risks, GTM, etc.) for multi-dimensional planning
- 💭 **Reflection Pulses**: Capture tacit knowledge with LLM-distilled semantic tagging (constraints, risks, preferences, decisions, insights)
- 📊 **Phase Coverage**: Track planning across lifecycle phases (prototype → v1 → scale-up → v2+)
- 👁️ **View Profiles**: Audience-specific plans (builder, stakeholder, investor, AI agent)
- ⚡ **Execution Bundles**: Ready-to-use repo scaffolds, task breakdowns, and AI coding tool prompts

## Architecture

### Backend (Python + FastAPI)

- **Session Manager**: Handles interview lifecycle and state persistence
- **Model Registry**: Discovers and categorizes Vultr models by capability
- **Question Engine**: Parallel multi-model question generation
- **Plan Reducer**: Incrementally updates plan state based on answers
- **Plan Synthesizer**: Generates final build-ready specifications

### Frontend (React + TypeScript + Vite)

- Clean, responsive UI for the interview process
- Real-time coverage visualization (thread + overall)
- Multiple-choice questions with an "Other" option
- Profile form, thread manager, reflection input and execution bundle viewer
- Final plan display with copy/download capabilities

## Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **Vultr Serverless Inference API Key** ([Get one here](https://www.vultr.com/))

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd InfiniteQ
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your VULTR_INFERENCE_API_KEY

# Run the server
python -m app.main
```

The backend will start on `http://localhost:8000`

### 3. Frontend Setup

In a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# (Optional) Configure API URL
cp .env.example .env

# Run the development server
npm run dev
```

The frontend will start on `http://localhost:3000`

### 4. Use the Application

1. Open `http://localhost:3000` in your browser
2. Enter your project idea (e.g., "A web app for NYC landlords to manage receiverships")
3. Answer the multiple-choice questions
4. Hit "Continue" to get more questions or "Finish" to generate your plan
5. Copy the plan and paste into your AI coding assistant!

From the session screen you can also open extra threads (architecture, risk, GTM, …),
switch between them, capture reflections, and pick the audience for the final plan
(builder, stakeholder, investor or agent spec) — including a ready-to-use execution
bundle.

## API Endpoints

### POST `/api/v1/session`

Create a new planning session.

**Request:**
```json
{
  "idea": "Your project idea",
  "mode": "kickoff" | "deep_dive" | "sanity_check",
  "project_profile": {
    "type": "saas",
    "sophistication": "mvp",
    "team_size": "solo",
    "tech_constraints": ["python", "react"],
    "timeline": "1-4_weeks",
    "budget_band": "<1k",
    "non_goals": ["mobile apps"]
  },
  "persona_profile": {
    "role": "founder_technical",
    "comfort_with_tech": "high",
    "comfort_with_business": "medium",
    "preferred_depth": "balanced"
  }
}
```

`mode` defaults to `kickoff`; both profiles are optional and every field inside them
has a default. See `backend/app/models/schema.py` for the allowed enum values.

**Response:**
```json
{
  "session_id": "uuid",
  "thread_id": "uuid",
  "first_questions": [...],
  "coverage": {...},
  "project_profile": {...},
  "persona_profile": {...}
}
```

The session starts with one thread (the kickoff thread); `thread_id` is the id of
that thread.

### POST `/api/v1/session/{id}/answer`

Submit answers and get next questions. The questions awaiting answers belong to the
session's active thread, so this is the single-thread shorthand for the thread answer
endpoint below; answers update that thread's coverage and the session's aggregated
coverage.

**Request:**
```json
{
  "answers": [
    {
      "question_id": "Q_001",
      "choice_id": "A",
      "free_text": "optional additional context"
    }
  ]
}
```

**Response:**
```json
{
  "next_questions": [...],
  "coverage": {...},
  "plan_preview": {...}
}
```

### POST `/api/v1/session/{id}/finish`

Finish the session and generate final plan.

**Response:**
```json
{
  "json_plan": {...},
  "markdown_brief": "# Project Plan\n..."
}
```

### Thread endpoints (v0.2)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/session/{id}/threads` | List threads and the active one |
| POST | `/api/v1/session/{id}/threads` | Create a thread (type, title, root_prompt) |
| PATCH | `/api/v1/session/{id}/threads/{tid}` | Rename a thread or park it (`active: false`) |
| POST | `/api/v1/session/{id}/threads/{tid}/activate` | Make a thread the active one |
| POST | `/api/v1/session/{id}/threads/{tid}/answer` | Answer questions in this thread |
| POST | `/api/v1/session/{id}/threads/{tid}/reflect` | Submit a freeform reflection — body is `{"text": "..."}` |
| GET | `/api/v1/session/{id}/threads/{tid}/insights` | Summarized reflections for a thread |

Answering in a thread returns `thread_coverage`, `phase_coverage` and
`global_coverage` (the session-level aggregate across all threads).

### GET `/api/v1/session/{id}/status`

Get session status and metadata (including a per-thread summary).

## Configuration

### Backend Environment Variables

Create `backend/.env`:

```env
# Required
VULTR_INFERENCE_API_KEY=your_api_key_here

# Optional
PORT=8000
DEBUG=false
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Session storage: file (default) | redis | memory
STORAGE_TYPE=file
SESSION_STORAGE_DIR=./data/sessions
REDIS_URL=redis://localhost:6379/0
SESSION_TTL_SECONDS=604800

# Rate limits, per client IP
RATE_LIMIT_LLM=30/minute       # routes that call inference models
RATE_LIMIT_SESSION=10/minute   # create/finish a session
RATE_LIMIT_READ=120/minute     # reads and metadata updates
```

`DEBUG=true` enables uvicorn auto-reload. Setting `SSL_CERTFILE` and `SSL_KEYFILE`
switches the server to HTTPS. Every API route is rate limited — see
`backend/app/api/rate_limit.py` for the policy.

### Frontend Environment Variables

Create `frontend/.env`:

```env
# Optional - defaults to /api/v1 (uses Vite proxy)
VITE_API_URL=http://localhost:8000/api/v1
```

## Model Selection Strategy

InfiniteQ discovers the available Vultr models and categorizes them by name pattern
(see `backend/app/services/model_registry.py`):

- **Reasoning**: `deepseek-r1-*`, `deepseek-reasoner`, `qwen*-think-*` for deep analysis
- **Code/Tech**: any `*coder*` model (`qwen2.5-coder-32b-instruct`, `deepseek-coder-*`, …)
- **Synthesis**: 70B-class models (`llama-3.3-70b-instruct-fp8`, `llama-3.1-70b-instruct`,
  `qwen2.5-72b`, `kimi-k2-*`) for final synthesis
- **Strategy**: `kimi`, `claude`, `gpt-4` and llama-instruct models for high-level planning

Roles are matched most-specific-first, so a 70B `kimi-k2-instruct` is treated as a
synthesis model rather than a strategy one.

The system rotates through models across interview rounds to leverage diverse perspectives.

If discovery fails, the app keeps running on a hardcoded model list and `/health` reports
`"status": "degraded"` together with `model_discovery_error`, so a bad key cannot look
like a healthy server.

## Coverage Dimensions

The system tracks coverage across 9 dimensions:

1. **Problem**: What are we solving and why?
2. **Users**: Who will use this and in what context?
3. **Constraints**: Time, budget, technical, compliance limits
4. **Features**: What functionality is needed?
5. **Architecture**: How should it be built?
6. **Data/ML**: Data sources, pipelines, models
7. **Operations**: Deployment, monitoring, maintenance
8. **Risks**: What could go wrong and how to mitigate?
9. **Go-to-market**: Positioning, pricing, launch

Questions automatically target the lowest-coverage areas to ensure comprehensive planning.

Coverage is tracked per thread and per lifecycle phase. Global (session-level) coverage
aggregates the threads: each dimension takes the highest score any thread reached, so
creating another (still empty) thread never lowers it.

## Development

### Backend Development

```bash
cd backend
source venv/bin/activate

# Run with auto-reload
uvicorn app.main:app --reload --port 8000

# Run tests (when available)
pytest tests/
```

### Frontend Development

```bash
cd frontend

# Development server with hot reload
npm run dev

# Type checking
npm run build

# Linting
npm run lint
```

## Project Structure

```
InfiniteQ/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── rate_limit.py      # Shared limiter + limit policy
│   │   │   └── routes.py          # FastAPI endpoints
│   │   ├── models/
│   │   │   └── schema.py          # Pydantic models
│   │   ├── services/
│   │   │   ├── vultr_client.py    # Vultr API wrapper (retries)
│   │   │   ├── model_registry.py  # Model discovery & selection
│   │   │   ├── session_manager.py # Session lifecycle, coverage aggregation, write locking
│   │   │   ├── session_storage.py # memory / file / redis backends
│   │   │   ├── question_engine.py # Question generation
│   │   │   ├── plan_reducer.py    # State + coverage updates
│   │   │   ├── plan_synthesizer.py # Final plan generation
│   │   │   ├── reflection_service.py # Reflection pulses & note distillation
│   │   │   ├── intelligent_bundle_generator.py # Model-generated bundles
│   │   │   └── coverage_assessor.py # Semantic coverage/trigger helpers
│   │   ├── prompts/
│   │   │   └── templates.py       # LLM prompts
│   │   └── main.py                # FastAPI app
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── IdeaInput.tsx      # Initial idea form
│   │   │   ├── QuestionCard.tsx   # MC question display
│   │   │   ├── CoverageDisplay.tsx # Coverage bars
│   │   │   ├── InterviewSession.tsx # Main interview flow
│   │   │   ├── FinalPlan.tsx      # Results display
│   │   │   └── v02/               # Profiles, threads, reflections, bundle viewer
│   │   ├── services/
│   │   │   └── api.ts             # Backend API client
│   │   ├── types/
│   │   │   └── index.ts           # TypeScript types
│   │   ├── App.tsx                # Main app component
│   │   ├── App.css                # Styles
│   │   └── main.tsx               # Entry point
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
└── README.md
```

## How It Works

### 1. Idea Normalization

When you submit an idea, the system uses a strategy model to extract:
- Normalized summary
- Project type (software, story, process, etc.)
- Key entities mentioned
- Initial scope hints

### 2. Question Generation

For each round:
1. Select 2-4 models based on round number and coverage gaps
2. Each model proposes 2-4 questions in parallel
3. An aggregator model deduplicates and selects the best questions
4. Questions target the lowest-coverage dimensions

### 3. Plan Updates

After each answer:
1. A reasoning model updates the canonical JSON plan
2. Coverage scores increase for addressed dimensions
3. The system stores a compact Q&A history (last 20 pairs)

### 4. Synthesis

On "Finish":
1. A large synthesis model (70B+) processes the final plan state
2. Generates two outputs:
   - **JSON Plan**: Structured data with all details
   - **Markdown Brief**: Human-readable spec for AI agents
3. Both are ready to paste into Cursor, ClaudeCode, etc.

## Use Cases

### Software Projects
- Web applications
- Mobile apps
- CLI tools
- APIs and microservices
- Data pipelines

### Other Project Types
- Story/narrative development
- Process documentation
- Research planning
- Content strategy
- Workflow automation

## Tips for Best Results

1. **Be Specific**: Start with concrete details rather than vague ideas
2. **Use "Other"**: Don't hesitate to provide custom answers when options don't fit
3. **Go Deep**: More rounds = more comprehensive plans (the system won't run out of memory)
4. **Finish Anytime**: You can generate a plan at any point; it will work with what it has
5. **Iterate**: Run multiple sessions to explore different approaches

## Troubleshooting

### Backend won't start
- Verify your `VULTR_INFERENCE_API_KEY` is set in `.env`
- Check that port 8000 is available
- Ensure Python 3.9+ is installed

### Frontend can't connect to backend
- Verify backend is running on port 8000
- Check Vite proxy configuration in `vite.config.ts`
- Try setting `VITE_API_URL` explicitly in `.env`

### Models not discovered
- Check your Vultr API key has access to Serverless Inference
- `GET /health` returns `"status": "degraded"` and `model_discovery_error` when discovery
  failed (the app is then running on fallback models)
- Review backend logs for API errors

### Questions seem repetitive
- This can happen if coverage isn't updating properly
- Check that answers are being submitted correctly
- Review plan state in `/session/{id}/status` endpoint

## Future Enhancements

- [x] Persistence for session recovery — Redis or file-based *(v0.2.1)*
- [x] Intelligent execution bundle generation *(v0.2.1)*
- [x] Deterministic reflection triggers *(v0.2.1)*
- [ ] Semantic coverage quality assessment — `CoverageQualityAssessor` exists in
      `backend/app/services/coverage_assessor.py` but is **not wired in**: it needs one
      extra model call per answer round, so coverage still uses the deterministic
      increment in `PlanReducer.update_coverage`
- [ ] WebSocket support for real-time updates
- [ ] Team collaboration features
- [ ] Plan comparison and versioning
- [ ] Export to project management tools
- [ ] Custom question templates
- [ ] Fine-tuned models for specific domains

## Recent Improvements (v0.2.1)

### Session Persistence
Sessions are persisted to disk (default) or Redis, so a planning session survives a
server restart. File writes are atomic, and every mutation is serialized per session.

```bash
# File storage (default)
export STORAGE_TYPE=file
export SESSION_STORAGE_DIR=./data/sessions

# Redis (falls back to file storage if Redis is unreachable)
export STORAGE_TYPE=redis
export REDIS_URL=redis://localhost:6379/0

# In-memory, no persistence (useful for tests)
export STORAGE_TYPE=memory
```

### Thread-Aware Planning Loop
Answers are persisted where they belong: thread coverage, phase coverage, the canonical
plan state and the session's aggregated coverage all survive the next request, so
questions keep targeting whatever is still weak instead of restarting from zero.

### Intelligent Execution Bundles
Bundles are generated by the models from the finished plan (project-specific scaffolds,
tasks and coding-tool prompts). If a model call fails, the built-in templates are used
so generating a bundle never fails the request.

### Deterministic Reflection Triggers
Reflection pulses are decided from the conversation so far rather than a random roll:

- At least 3 questions since the last reflection, forced at 12
- Two or more very short answers in the last three (possible confusion)
- A large coverage imbalance between dimensions

### Not wired in: semantic coverage assessment
`CoverageQualityAssessor` can score answers on specificity, completeness, novelty and
clarity, but wiring it in costs one extra model call per answer round, so it is left
unused for now.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

Built with ❤️ using Vultr Serverless Inference, FastAPI, and React

## v0.2 Quick Start

### Using Profiles

```python
import requests

# Create session with profiles
response = requests.post("http://localhost:8000/api/v1/session", json={
    "idea": "AI-powered fitness coaching app",
    "mode": "kickoff",
    "project_profile": {
        "type": "saas",
        "team_size": "solo",
        "tech_constraints": ["react native", "firebase"],
        "timeline": "1-3_months",
        "budget_band": "1k-10k"
    },
    "persona_profile": {
        "role": "founder_technical",
        "comfort_with_tech": "high",
        "comfort_with_business": "medium",
        "preferred_depth": "deep"
    }
})
```

### Creating Threads

```python
# Create specialized exploration threads
session_id = "your-session-id"

# Architecture thread
requests.post(f"http://localhost:8000/api/v1/session/{session_id}/threads", json={
    "type": "architecture",
    "title": "Backend & Infrastructure"
})

# Risk assessment thread
requests.post(f"http://localhost:8000/api/v1/session/{session_id}/threads", json={
    "type": "risk",
    "title": "Technical & Business Risks"
})
```

### Capturing Reflections

```python
# Submit freeform insights
thread_id = "your-thread-id"

requests.post(f"http://localhost:8000/api/v1/session/{session_id}/threads/{thread_id}/reflect", json={
    "text": "Budget constraint: Only $5k for v1. Must use free tiers."
})

# Returns tagged note:
# {
#   "note": {
#     "distilled": "Budget limited to $5k for v1",
#     "tags": ["constraint:budget", "decision:free_tier"]
#   }
# }
```

### Getting Execution Bundles

```python
# Generate ready-to-use artifacts
response = requests.post(f"http://localhost:8000/api/v1/session/{session_id}/finish", json={
    "view_profile": "builder",  # or "stakeholder", "investor", "agent_spec"
    "include_execution_bundle": True
})

bundle = response.json()["execution_bundle"]

# Contains:
# - repo_scaffold: Language, frameworks, folder structure
# - tasks: Phased breakdown (prototype → v1 → scale-up → v2+)
# - prompts: Ready-to-paste into ClaudeCode/Cursor
```

### Try the Examples

```bash
# Simple session
python examples/01_simple_session.py

# Complete v0.2 workflow
python examples/02_full_v02_workflow.py

# Execution bundle deep dive
python examples/03_execution_bundle_demo.py
```

## Documentation

- **v0.2 Architecture**: `docs/V0.2_ARCHITECTURE.md`
- **Migration Guide**: `docs/MIGRATION_V1_TO_V2.md`
- **Examples**: `examples/README.md`
- **Tests**: `backend/tests/README.md`

## Testing

```bash
# Run all tests
pytest

# Run integration tests
pytest backend/tests/test_v02_integration.py

# Run unit tests
pytest backend/tests/test_services_v02.py

# Planning loop regressions (thread persistence + coverage aggregation)
pytest backend/tests/test_planning_loop.py

# Execution bundles, rate limiting, retries, triggers, write locking
pytest backend/tests/test_execution_bundles.py backend/tests/test_hardening.py
```

