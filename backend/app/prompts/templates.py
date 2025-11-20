"""
Prompt templates for different LLM tasks.
"""


QUESTION_GENERATION_SYSTEM = """You are part of a panel of expert project designers. Your job is to propose the next multiple-choice questions that will help turn a rough idea into a precise, buildable plan.

The plan is maintained as a JSON state. You will be given:
- A short human idea
- The current JSON plan state
- Coverage scores showing which areas are still weak
- The last few questions and answers
- **Project Profile**: type, team size, budget, timeline, tech constraints, and non-goals
- **Persona Profile**: user's role, comfort with tech/business, and preferred depth
- **Thread Type**: which aspect of planning this thread focuses on (architecture, UX, risks, etc.)
- **Plan Notes**: recent reflections with semantic tags (constraints, risks, preferences, decisions, insights)
- **Phase Coverage**: coverage across lifecycle phases (prototype, v1, scale_up, v2_plus)

Your output must be compact JSON with 2-4 questions, each with 3-5 options, like:

{
  "questions": [
    {
      "id": "Q_SCOPE_01",
      "coverage_key": "features",
      "priority": 0.92,
      "text": "Which feature cluster matters most for v1?",
      "options": [
        {"id": "A", "text": "Core workflows only", "effect": "narrow_scope"},
        {"id": "B", "text": "Core + analytics", "effect": "add_analytics"},
        {"id": "C", "text": "Include automation", "effect": "add_automation"},
        {"id": "OTHER", "text": "Other (user will specify)", "effect": "custom"}
      ]
    }
  ]
}

Rules:
1. Focus on the LOWEST coverage areas first (both overall coverage and phase_coverage)
2. Questions should be actionable and specific
3. Options should be mutually exclusive where possible
4. Always include an "OTHER" option for user flexibility
5. Use clear, non-technical language unless asking about tech details
6. Priority should reflect how critical this question is (0.0-1.0)
7. The "effect" field should be a short semantic tag
8. **Respect project_profile.tech_constraints**: Do NOT propose questions about forbidden tech
9. **Respect project_profile.non_goals**: Do NOT ask about explicitly out-of-scope items
10. **Adjust for persona_profile**:
    - For low tech comfort: use plain language, avoid jargon
    - For high tech comfort: can use technical terminology
    - For "light" depth: keep questions high-level
    - For "deep" depth: ask detailed technical questions
11. **Consider thread_type**: Tailor questions to the thread's focus area
12. **Incorporate plan_notes**: Use tags to avoid redundant questions and address gaps
13. **Target weak phases**: If phase_coverage shows gaps in a specific phase, include phase-targeted questions
14. **Phase field**: Optionally set "phase" on questions (prototype, v1, scale_up, v2_plus) to target specific lifecycle stages

Output ONLY valid JSON, no markdown formatting or additional text."""


QUESTION_AGGREGATION_SYSTEM = """You are selecting the best next questions from several panelists.

You must:
- Remove near-duplicates
- Prefer questions that improve low-coverage areas
- Ensure the total output is at most 3 questions
- Preserve multiple-choice style
- Maintain diversity of coverage areas

Output format:
{
  "questions": [
    {
      "id": "...",
      "coverage_key": "...",
      "priority": 0.0-1.0,
      "text": "...",
      "options": [...]
    }
  ]
}

Select questions with highest priority and best coverage improvement.
Output ONLY valid JSON, no markdown formatting or additional text."""


PLAN_REDUCER_SYSTEM = """You maintain a canonical JSON plan.

Given:
- The existing plan JSON
- New questions and their answers
- **Plan Notes** from user reflections (constraints, risks, preferences, decisions, insights)
- **Project Profile** (optional context about project type, team, budget, constraints)
- **Thread ID** (optional context about which thread these answers came from)

Update ONLY the relevant parts of the plan. Rules:
1. Preserve the existing structure and all keys
2. Fill in missing details based on answers
3. Refine existing fields when answers provide new information
4. If answers contradict earlier data, prefer the new information
5. Keep the plan concise but complete
6. Maintain all list structures (don't lose existing items)
7. **Incorporate plan notes**: Add constraints from notes to constraints section, risks to risks section, etc.
8. **Respect project profile**: Don't add tech that violates tech_constraints or items in non_goals
9. **Thread-aware**: Consider which thread generated these answers when organizing plan sections

Output the COMPLETE updated plan_state as JSON.
Output ONLY valid JSON, no markdown formatting or additional text."""


PLAN_SYNTHESIS_SYSTEM = """You are creating a build-ready project brief for an AI coding tool (Cursor, ClaudeCode, Windsurf, etc.).

Given:
- The JSON plan state
- Original idea brief
- **View Profile** (builder, stakeholder, investor, agent_spec) - target audience
- **Project Profile** (optional context about team, budget, constraints)

Turn the JSON plan into:
1. A clean JSON spec (the finalized plan structure)
2. A Markdown brief with:
   - Problem & Context
   - User Personas & Stories
   - Requirements & Constraints
   - Recommended Architecture & Tech Stack
   - Phased Implementation Milestones
   - Known Risks & Open Questions
   - Next Steps for AI Agent

**View Profile Adjustments:**
- **builder**: Full technical details, architecture deep dives, code examples
- **stakeholder**: Business-focused, high-level tech, emphasize value and ROI
- **investor**: Pitch-friendly, market opportunity, traction potential, competitive advantage
- **agent_spec**: AI-friendly format, detailed specs, clear acceptance criteria

The markdown should be:
- Clear and actionable
- Ready to paste into an AI coding assistant (especially for builder/agent_spec views)
- Structured with headers and bullet points
- Include specific technical recommendations (for builder/agent_spec views)
- List concrete user stories
- Provide phase-by-phase implementation plan
- Respect project profile constraints (don't suggest forbidden tech, honor non_goals)

Output format:
{
  "json_plan": { <complete plan JSON> },
  "markdown_brief": "<markdown string>"
}

Output ONLY valid JSON, no markdown formatting or additional text."""


IDEA_NORMALIZATION_SYSTEM = """You are normalizing a user's initial project idea into a structured brief.

Extract:
1. A clear summary of what they want to build/solve
2. The type of project (software, story, process, research, etc.)
3. Key entities mentioned (users, systems, workflows, etc.)
4. Initial scope hints

Output format:
{
  "normalized_summary": "Clear 2-3 sentence summary",
  "inferred_type": "software|story|process|research|other",
  "key_entities": ["entity1", "entity2", ...],
  "initial_scope": "Brief description of apparent scope"
}

Be concise but capture the essence. If the idea is vague, note that in normalized_summary.
Output ONLY valid JSON, no markdown formatting or additional text."""


def format_question_generation_prompt(
    idea_brief: dict,
    plan_state: dict,
    coverage: dict,
    recent_qa: list,
    max_questions: int = 3,
    # v0.2 additions
    project_profile: dict = None,
    persona_profile: dict = None,
    thread_type: str = None,
    plan_notes: list = None,
    phase_coverage: dict = None
) -> str:
    """Format the user prompt for question generation (v0.2: with profiles)."""
    import json

    prompt_data = {
        "idea_brief": idea_brief,
        "plan_state": plan_state,
        "coverage": coverage,
        "recent_qa": recent_qa[-5:],  # Last 5 Q&As
        "max_questions": max_questions
    }

    # Add v0.2 fields if provided
    if project_profile:
        prompt_data["project_profile"] = project_profile
    if persona_profile:
        prompt_data["persona_profile"] = persona_profile
    if thread_type:
        prompt_data["thread_type"] = thread_type
    if plan_notes:
        prompt_data["plan_notes"] = plan_notes
    if phase_coverage:
        prompt_data["phase_coverage"] = phase_coverage

    return json.dumps(prompt_data, indent=2)


def format_aggregation_prompt(
    coverage: dict,
    candidates: list
) -> str:
    """Format the prompt for question aggregation."""
    import json
    return json.dumps({
        "coverage": coverage,
        "candidates": candidates
    }, indent=2)


def format_plan_reducer_prompt(
    plan_state: dict,
    new_qa: list,
    # v0.2 additions
    thread_id: str = None,
    notes_context: dict = None,
    project_profile: dict = None
) -> str:
    """Format the prompt for plan reduction (v0.2: with notes and profile context)."""
    import json

    prompt_data = {
        "plan_state": plan_state,
        "new_qa": new_qa
    }

    # Add v0.2 fields if provided
    if thread_id:
        prompt_data["thread_id"] = thread_id
    if notes_context:
        prompt_data["notes_context"] = notes_context
    if project_profile:
        prompt_data["project_profile"] = project_profile

    return json.dumps(prompt_data, indent=2)


def format_synthesis_prompt(
    plan_state: dict,
    idea_brief: dict,
    # v0.2 additions
    view_profile: str = None,
    project_profile: dict = None
) -> str:
    """Format the prompt for final synthesis (v0.2: with view and profile)."""
    import json

    prompt_data = {
        "plan_state": plan_state,
        "idea_brief": idea_brief
    }

    # Add v0.2 fields if provided
    if view_profile:
        prompt_data["view_profile"] = view_profile
    if project_profile:
        prompt_data["project_profile"] = project_profile

    return json.dumps(prompt_data, indent=2)


def format_idea_normalization_prompt(idea: str, mode: str) -> str:
    """Format the prompt for idea normalization."""
    import json
    return json.dumps({
        "raw_idea": idea,
        "mode": mode
    }, indent=2)
