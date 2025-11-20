# Migration Guide: v0.1 → v0.2

This guide helps you upgrade from InfiniteQ v0.1 to v0.2.

## Overview of Changes

InfiniteQ v0.2 introduces **6 major features** while maintaining backwards compatibility with v0.1:

1. **Threads & Modes** - Multiple parallel exploration threads
2. **Project & Persona Profiles** - Context-aware questioning
3. **Phase Coverage** - Lifecycle-specific planning (prototype → v1 → scale-up → v2+)
4. **Reflection Pulses** - Capture tacit knowledge
5. **Views & Sealed Sections** - Audience-specific plan filtering
6. **Execution Bundles** - Ready-to-use repo scaffolds, tasks, and AI prompts

## Backwards Compatibility

**Good news:** All v0.1 endpoints still work!

```python
# v0.1 code continues to work unchanged
response = requests.post("/session", json={"idea": "My app idea"})
```

v0.2 simply adds optional parameters with sensible defaults.

---

## API Changes

### 1. Session Creation

**v0.1:**
```python
POST /session
{
  "idea": "Your project idea",
  "mode": "software"  # or "story", "process", "other"
}
```

**v0.2 (Enhanced):**
```python
POST /session
{
  "idea": "Your project idea",
  "mode": "kickoff",  # or "deep_dive", "sanity_check"
  "project_profile": {
    "type": "saas",
    "sophistication": "mvp",
    "team_size": "solo",
    "tech_constraints": ["python", "react", "no PHP"],
    "timeline": "1-3_months",
    "budget_band": "1k-10k",
    "non_goals": ["mobile apps", "blockchain"]
  },
  "persona_profile": {
    "role": "founder_solo",
    "tech_comfort": 7,        # 1-10
    "business_comfort": 5,    # 1-10
    "preferred_depth": "deep" # "light", "medium", "deep"
  }
}
```

**Migration:**
- Add profiles to get better questions
- Or omit profiles to use defaults (works like v0.1)

---

### 2. Answering Questions

**v0.1:**
```python
POST /session/{id}/answer
{
  "answers": [
    {"question_id": "Q1", "choice_id": "A", "free_text": "Details..."}
  ]
}
```

**v0.2 (Thread-Aware):**
```python
# Option A: Use v0.1 endpoint (still works)
POST /session/{id}/answer
{
  "answers": [...]
}

# Option B: Use thread-specific endpoint (recommended)
POST /session/{id}/threads/{thread_id}/answer
{
  "answers": [...]
}
```

**Migration:**
- v0.1 endpoint works on the active thread
- v0.2 endpoint allows explicit thread targeting
- Use v0.2 when working with multiple threads

---

### 3. Finishing Sessions

**v0.1:**
```python
POST /session/{id}/finish
{}

# Returns:
{
  "json_plan": {...},
  "markdown_brief": "..."
}
```

**v0.2 (Views & Execution Bundles):**
```python
POST /session/{id}/finish
{
  "view_profile": "builder",  # or "stakeholder", "investor", "agent_spec"
  "include_execution_bundle": true
}

# Returns:
{
  "json_plan": {...},
  "markdown_brief": "...",
  "execution_bundle": {
    "repo_scaffold": {...},
    "tasks": [...],
    "prompts": [...]
  }
}
```

**Migration:**
- Add `view_profile` for audience-specific plans
- Set `include_execution_bundle: true` for immediate actionability

---

## New Endpoints (v0.2 Only)

### Thread Management

```python
# Create new thread
POST /session/{id}/threads
{
  "type": "architecture",  # or product_ux, risk, gtm, etc.
  "title": "Backend architecture planning",
  "root_prompt": "Focus on scalability..."  # optional
}

# List all threads
GET /session/{id}/threads

# Activate a thread
POST /session/{id}/threads/{thread_id}/activate

# Answer in specific thread
POST /session/{id}/threads/{thread_id}/answer
{
  "answers": [...]
}
```

### Reflection System

```python
# Submit reflection
POST /session/{id}/threads/{thread_id}/reflect
{
  "reflection": "I'm worried about scalability..."
}

# Returns:
{
  "note": {
    "id": "...",
    "raw": "I'm worried about scalability...",
    "distilled": "Scalability concerns for high traffic",
    "tags": ["risk:scalability", "constraint:performance"]
  }
}

# Get insights
GET /session/{id}/threads/{thread_id}/insights

# Returns:
{
  "insights_by_type": {
    "constraints": [...],
    "risks": [...],
    "preferences": [...],
    "decisions": [...],
    "insights": [...]
  }
}
```

---

## Data Model Changes

### New Types

```typescript
// Profiles
interface ProjectProfile {
  type?: "saas" | "mobile_app" | "web_app" | ...
  sophistication?: "toy" | "mvp" | "production"
  team_size?: "solo" | "2-3" | "4-10" | "10+"
  tech_constraints?: string[]
  timeline?: "weekend" | "1-4_weeks" | "1-3_months" | "6+_months"
  budget_band?: "<1k" | "1k-10k" | "10k-100k" | "100k+"
  non_goals?: string[]
}

interface PersonaProfile {
  role?: "founder_solo" | "tech_lead" | "product_manager" | ...
  tech_comfort?: number  // 1-10
  business_comfort?: number  // 1-10
  preferred_depth?: "light" | "medium" | "deep"
}

// Threads
interface ThreadState {
  id: string
  type: "kickoff" | "architecture" | "product_ux" | ...
  title: string
  questions_asked: number
  notes: PlanNote[]
}

// Reflections
interface PlanNote {
  id: string
  raw: string
  distilled: string
  tags: string[]  // e.g., ["constraint:budget", "risk:scalability"]
}

// Execution Bundle
interface ExecutionBundle {
  repo_scaffold: RepoScaffold
  tasks: Task[]
  prompts: LLMPromptTemplate[]
}
```

### Extended Types

```typescript
// Questions now have optional phase
interface Question {
  ...existing fields...
  phase?: "prototype" | "v1" | "scale_up" | "v2_plus"
}

// SessionData now has profiles and threads
interface SessionData {
  ...existing fields...
  project_profile?: ProjectProfile
  persona_profile?: PersonaProfile
  threads: Record<string, ThreadState>
  active_thread_id: string
}
```

---

## Migration Strategies

### Strategy 1: Gradual Adoption (Recommended)

Keep v0.1 code working, add v0.2 features incrementally:

**Phase 1: Add Profiles**
```python
# Before (v0.1)
create_session(idea="My app")

# After (v0.2)
create_session(
    idea="My app",
    project_profile={"type": "saas", "team_size": "solo"}
)
```

**Phase 2: Add Threads**
```python
# Create specialized threads
create_thread(session_id, type="architecture", title="Tech Stack")
create_thread(session_id, type="risk", title="Risk Assessment")
```

**Phase 3: Add Reflections**
```python
# Capture insights
submit_reflection(session_id, thread_id, "Budget constraint: $5k max")
```

**Phase 4: Use Execution Bundles**
```python
# Get ready-to-use artifacts
bundle = finish_session(
    session_id,
    view_profile="builder",
    include_execution_bundle=True
)
```

### Strategy 2: Clean Break

Rewrite for v0.2 from scratch:

```python
# v0.2-first approach
def create_planning_session(idea, profiles):
    # Create with profiles
    session = create_session(idea=idea, **profiles)

    # Create specialized threads
    for thread_type in ["architecture", "product_ux", "risk"]:
        create_thread(session.id, type=thread_type)

    return session

def capture_insights_during_planning(session_id, thread_id):
    # Automatically inject reflections
    if should_reflect():
        reflection = get_user_reflection()
        submit_reflection(session_id, thread_id, reflection)

def generate_execution_ready_plan(session_id):
    # Get complete bundle
    return finish_session(
        session_id,
        view_profile="agent_spec",
        include_execution_bundle=True
    )
```

---

## Frontend Migration

### v0.1 Components

Keep existing:
- `IdeaInput.tsx`
- `QuestionCard.tsx`
- `CoverageDisplay.tsx`
- `FinalPlan.tsx`

### New v0.2 Components

Add from `frontend/src/components/v02/`:

```typescript
import {
  ProfileForms,
  ThreadManager,
  ReflectionInput,
  ExecutionBundleViewer,
} from "./components/v02";

// Use in your app
<ProfileForms onProfilesChange={handleProfiles} />
<ThreadManager
  threads={threads}
  activeThreadId={activeThreadId}
  onCreateThread={handleCreateThread}
  onActivateThread={handleActivateThread}
/>
<ReflectionInput
  reflectionPrompt={reflectionPrompt}
  onSubmitReflection={handleReflection}
/>
<ExecutionBundleViewer bundle={executionBundle} />
```

---

## Testing Migration

### Update Tests

**v0.1 tests continue to work:**
```python
def test_create_session_v1():
    # Still works!
    response = client.post("/session", json={"idea": "Test"})
    assert response.status_code == 200
```

**Add v0.2 tests:**
```python
def test_create_session_with_profiles():
    response = client.post("/session", json={
        "idea": "Test",
        "project_profile": {"type": "saas"},
        "persona_profile": {"role": "founder_solo"}
    })
    assert "project_profile" in response.json()
    assert "persona_profile" in response.json()

def test_thread_creation():
    session = create_session("Test")
    response = client.post(f"/session/{session.id}/threads", json={
        "type": "architecture",
        "title": "Tech stack"
    })
    assert response.status_code == 200

def test_execution_bundle():
    session = create_session("Test")
    response = client.post(f"/session/{session.id}/finish", json={
        "view_profile": "builder",
        "include_execution_bundle": True
    })
    bundle = response.json()["execution_bundle"]
    assert "repo_scaffold" in bundle
    assert "tasks" in bundle
    assert "prompts" in bundle
```

---

## Common Migration Issues

### Issue 1: Profile Defaults

**Problem:** Not providing profiles gives unexpected results.

**Solution:** Always provide at least basic profiles:
```python
project_profile = {"type": "saas"}  # Minimal
persona_profile = {"role": "founder_solo"}
```

### Issue 2: Thread Confusion

**Problem:** Multiple threads but unclear which is active.

**Solution:** Always check `active_thread_id`:
```python
status = get_session_status(session_id)
active_thread = status["active_thread_id"]
```

### Issue 3: Missing Execution Bundle

**Problem:** `finish()` doesn't return execution bundle.

**Solution:** Explicitly request it:
```python
finish_session(
    session_id,
    include_execution_bundle=True  # Required!
)
```

---

## Performance Considerations

v0.2 is slightly heavier due to:
- Profile processing
- Thread state management
- Reflection distillation (LLM calls)

**Optimization tips:**
1. **Batch thread creation** - Create all threads at session start
2. **Limit reflections** - They're auto-triggered every 5-10 questions
3. **Cache profiles** - Reuse profiles for similar projects
4. **Lazy-load bundles** - Only generate when needed

---

## Rollback Plan

If you need to rollback to v0.1:

1. **Backend:** Revert to commit before v0.2
2. **Frontend:** Remove v0.2 components
3. **Database:** No schema changes needed (v0.2 is additive)

v0.1 data will still work in v0.2 (just without v0.2 features).

---

## Getting Help

- **Examples:** See `examples/` directory for complete workflows
- **Tests:** See `backend/tests/test_v02_integration.py`
- **Docs:** Read `docs/V0.2_ARCHITECTURE.md`
- **Issues:** Report at GitHub repository

---

## Checklist

Use this checklist for migration:

### Backend
- [ ] Update API calls to include profiles (optional)
- [ ] Add thread management if needed
- [ ] Implement reflection capture (optional)
- [ ] Request execution bundles on finish
- [ ] Update tests with v0.2 scenarios

### Frontend
- [ ] Import v0.2 types
- [ ] Add ProfileForms to session creation
- [ ] Add ThreadManager for thread UI
- [ ] Add ReflectionInput for insights
- [ ] Add ExecutionBundleViewer for final output
- [ ] Update API calls to v0.2 endpoints

### Testing
- [ ] Run v0.1 tests (should still pass)
- [ ] Add v0.2 integration tests
- [ ] Test profiles
- [ ] Test threads
- [ ] Test reflections
- [ ] Test execution bundles

### Deployment
- [ ] Update environment variables (if any)
- [ ] No database migrations needed
- [ ] Deploy backend
- [ ] Deploy frontend
- [ ] Monitor for issues

---

## Next Steps

1. Read `examples/02_full_v02_workflow.py` for complete example
2. Try `examples/03_execution_bundle_demo.py` to see bundles
3. Review new components in `frontend/src/components/v02/`
4. Check out test coverage in `backend/tests/`

Happy migrating! 🚀
