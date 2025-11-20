# InfiniteQ v0.2 Examples

Interactive examples demonstrating InfiniteQ's AI-powered project planning capabilities.

## Prerequisites

```bash
# Install dependencies
pip install requests

# Start the InfiniteQ server
cd backend
uvicorn app.main:app --reload
```

## Examples

### 1. Simple Session (`01_simple_session.py`)

**What it shows:**
- Basic session creation
- Answering questions
- Getting a final plan

**Run it:**
```bash
python examples/01_simple_session.py
```

**Best for:**
- First-time users
- Quick project planning (< 10 minutes)
- Understanding the basic flow

---

### 2. Complete v0.2 Workflow (`02_full_v02_workflow.py`)

**What it shows:**
- Custom project and persona profiles
- Multiple specialized threads
- Reflection pulse system
- Execution bundle generation
- View profile comparison

**Run it:**
```bash
python examples/02_full_v02_workflow.py
```

**Best for:**
- Complex projects
- Teams wanting deep exploration
- Understanding all v0.2 features

**Demonstrates:**
- ✅ Profile-driven planning
- ✅ Thread-based exploration (architecture, UX, risks, etc.)
- ✅ Reflection capture with semantic tagging
- ✅ Phase-based task breakdown
- ✅ AI-ready prompts for coding tools

---

### 3. Execution Bundle Demo (`03_execution_bundle_demo.py`)

**What it shows:**
- Generating complete execution bundles
- Repository scaffolds
- Phased task breakdowns
- AI coding tool prompts
- Exporting to files

**Run it:**
```bash
python examples/03_execution_bundle_demo.py
```

**Outputs:**
- `scaffold.json` - Repository structure
- `tasks.json` - Phased task list
- `prompt_*.txt` - Ready-to-use AI prompts
- `plan.md` - Complete markdown plan

**Best for:**
- Immediate project kickoff
- AI-assisted development
- Solo developers and small teams

---

## Typical Workflows

### Solo Founder (Weekend Project)

```python
# Quick kickoff
session = create_session(
    idea="Your idea here",
    project_profile={
        "team_size": "solo",
        "timeline": "weekend",
        "budget_band": "<1k"
    }
)

# Get execution bundle
bundle = finish_session(
    session_id,
    view_profile="builder",
    include_execution_bundle=True
)

# Start coding with AI
# Paste bundle.prompts[0] into ClaudeCode
```

### Startup Team (3-6 Months)

```python
# Detailed planning
session = create_session(
    idea="Your SaaS idea",
    project_profile={
        "team_size": "4-10",
        "timeline": "6+_months",
        "sophistication": "production"
    }
)

# Parallel exploration
create_thread("architecture")
create_thread("product_ux")
create_thread("gtm")
create_thread("risk")

# Capture insights
submit_reflection("Critical constraints...")

# Get investor-ready plan
finish_session(
    view_profile="investor",
    include_execution_bundle=False
)
```

### Enterprise Project

```python
# Stakeholder-focused
session = create_session(
    idea="Enterprise platform",
    project_profile={
        "type": "enterprise",
        "team_size": "10+",
        "budget_band": "100k+"
    },
    persona_profile={
        "role": "business_leader",
        "tech_comfort": 3,
        "preferred_depth": "light"
    }
)

# Get business-friendly plan
finish_session(view_profile="stakeholder")
```

---

## API Endpoints Reference

### Core Flow

```python
# 1. Create session
POST /session
{
  "idea": "Your project idea",
  "mode": "kickoff",  # or "deep_dive", "sanity_check"
  "project_profile": {...},
  "persona_profile": {...}
}

# 2. Create threads
POST /session/{id}/threads
{
  "type": "architecture",  # or product_ux, risk, gtm, etc.
  "title": "Thread title"
}

# 3. Answer questions
POST /session/{id}/threads/{tid}/answer
{
  "answers": [...]
}

# 4. Submit reflections
POST /session/{id}/threads/{tid}/reflect
{
  "reflection": "Your freeform insights"
}

# 5. Finish
POST /session/{id}/finish
{
  "view_profile": "builder",  # or stakeholder, investor, agent_spec
  "include_execution_bundle": true
}
```

---

## Tips for Best Results

### 1. Profile Configuration

**Project Profile:**
- Be honest about team_size and timeline
- List all tech_constraints (forbidden technologies)
- Specify non_goals to keep scope tight

**Persona Profile:**
- Set tech_comfort honestly (1-10)
- Choose preferred_depth based on time available
- Select role that matches your position

### 2. Thread Strategy

**Use threads for:**
- Deep dives into specific areas
- Parallel exploration by team members
- Separating technical vs. business concerns

**Thread types:**
- `kickoff` - Initial brainstorming
- `architecture` - Technical deep dive
- `product_ux` - User experience focus
- `risk` - Risk assessment
- `gtm` - Go-to-market strategy
- `sanity_check` - Quick validation

### 3. Reflections

**When to reflect:**
- After every 5-10 questions
- When you have a realization
- To capture constraints or preferences

**Good reflections:**
- "Budget constraint: Only $5k for v1"
- "User insight: Our users are non-technical"
- "Risk: Competitor just launched similar feature"

### 4. View Profiles

Choose based on audience:

- **builder** → Technical team members
- **stakeholder** → Business stakeholders, PMs
- **investor** → Fundraising, pitches
- **agent_spec** → AI coding tools (most detailed)

### 5. Execution Bundles

**Include when:**
- Ready to start coding
- Using AI coding assistants
- Need task breakdown
- Want repo structure

**Use the prompts with:**
- ClaudeCode
- Cursor
- GitHub Copilot
- Windsurf
- Any AI coding tool

---

## Troubleshooting

### Server not responding
```bash
# Make sure server is running
cd backend
uvicorn app.main:app --reload --port 8000
```

### Import errors
```bash
# Make sure you're in the right directory
cd /path/to/InfiniteQ
python examples/01_simple_session.py
```

### Connection refused
```bash
# Check if port 8000 is available
lsof -i :8000

# Or use different port
BASE_URL = "http://localhost:8001"
```

---

## Next Steps

1. **Try the examples** in order (01 → 02 → 03)
2. **Modify for your project** - Edit the `idea` and profiles
3. **Explore the API** - Use the full workflow example as template
4. **Integrate with your tools** - Use execution bundles with AI coding assistants

## Questions?

- Check the API docs: `/docs` endpoint (FastAPI auto-docs)
- Read the v0.2 architecture: `docs/V0.2_ARCHITECTURE.md`
- Review test examples: `backend/tests/test_v02_integration.py`
