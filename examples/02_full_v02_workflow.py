"""
Example 2: Complete v0.2 Workflow

Demonstrates all v0.2 features:
- Custom profiles
- Multiple threads
- Reflection pulses
- Execution bundles
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def main():
    print_section("InfiniteQ v0.2: Complete Workflow Demo")

    # 1. Create session with detailed profiles
    print_section("1. Creating Session with Profiles")

    session_response = requests.post(f"{BASE_URL}/session", json={
        "idea": "Enterprise SaaS platform for team collaboration with AI-powered insights",
        "mode": "kickoff",
        "project_profile": {
            "type": "saas",
            "sophistication": "production",
            "team_size": "4-10",
            "tech_constraints": ["python", "typescript", "react", "postgresql"],
            "timeline": "6+_months",
            "budget_band": "100k+",
            "non_goals": ["mobile apps in v1", "blockchain integration"]
        },
        "persona_profile": {
            "role": "founder_team",
            "tech_comfort": 8,
            "business_comfort": 7,
            "preferred_depth": "deep"
        }
    })

    session = session_response.json()
    session_id = session["session_id"]
    kickoff_thread = session["thread_id"]

    print(f"Session ID: {session_id}")
    print(f"Project Type: {session['project_profile']['type']}")
    print(f"Team Size: {session['project_profile']['team_size']}")
    print(f"Timeline: {session['project_profile']['timeline']}")
    print(f"Persona: {session['persona_profile']['role']}")
    print(f"Tech Comfort: {session['persona_profile']['tech_comfort']}/10")

    # 2. Create specialized threads
    print_section("2. Creating Specialized Threads")

    threads_to_create = [
        {"type": "architecture", "title": "Backend & Infrastructure Architecture"},
        {"type": "product_ux", "title": "User Experience & Interface Design"},
        {"type": "risk", "title": "Technical & Business Risk Assessment"}
    ]

    thread_ids = {"kickoff": kickoff_thread}

    for thread_config in threads_to_create:
        response = requests.post(
            f"{BASE_URL}/session/{session_id}/threads",
            json=thread_config
        )
        thread = response.json()["thread"]
        thread_ids[thread_config["type"]] = thread["id"]
        print(f"✓ Created {thread_config['type']} thread: {thread['title']}")

    # 3. Work on architecture thread
    print_section("3. Architecture Thread Exploration")

    arch_thread_id = thread_ids["architecture"]

    # Activate architecture thread
    requests.post(f"{BASE_URL}/session/{session_id}/threads/{arch_thread_id}/activate")
    print(f"Activated architecture thread: {arch_thread_id}")

    # Simulate answering questions
    for i in range(3):
        # Get current questions
        status_response = requests.get(f"{BASE_URL}/session/{session_id}/status")
        # Answer them (simplified - would show real questions in UI)
        print(f"  Round {i+1}: Answered architecture questions")
        time.sleep(0.5)  # Simulate user thinking

    # 4. Submit reflection
    print_section("4. Submitting Reflection")

    reflection_response = requests.post(
        f"{BASE_URL}/session/{session_id}/threads/{arch_thread_id}/reflect",
        json={
            "reflection": """
            Critical insight: We need to handle 50k concurrent users from day 1.
            The backend must be horizontally scalable - thinking microservices with
            Kubernetes. Also, data consistency is crucial for real-time collaboration,
            so we might need event sourcing. Budget-wise, cloud costs could spiral
            if we're not careful about auto-scaling policies.
            """
        }
    )

    note = reflection_response.json()["note"]
    print(f"Reflection captured:")
    print(f"  Raw: {note['raw'][:80]}...")
    print(f"  Distilled: {note['distilled']}")
    print(f"  Tags: {', '.join(note['tags'])}")

    # 5. Get insights
    insights_response = requests.get(
        f"{BASE_URL}/session/{session_id}/threads/{arch_thread_id}/insights"
    )
    insights = insights_response.json()
    print(f"\nInsights extracted:")
    for category, items in insights["insights_by_type"].items():
        if items:
            print(f"  {category.capitalize()}: {len(items)} items")

    # 6. Work on risk thread
    print_section("5. Risk Assessment Thread")

    risk_thread_id = thread_ids["risk"]
    requests.post(f"{BASE_URL}/session/{session_id}/threads/{risk_thread_id}/activate")

    # Submit risk-focused reflection
    risk_reflection = requests.post(
        f"{BASE_URL}/session/{session_id}/threads/{risk_thread_id}/reflect",
        json={
            "reflection": """
            Main risks: 1) Competitive market - Slack, Teams already dominate.
            2) AI features might not be differentiated enough. 3) Enterprise sales
            cycle is long (6-12 months). 4) Need SOC 2 compliance which takes time.
            """
        }
    )

    risk_note = risk_reflection.json()["note"]
    print(f"Risk reflection:")
    print(f"  {risk_note['distilled']}")
    print(f"  Tags: {', '.join(risk_note['tags'])}")

    # 7. List all threads
    print_section("6. Thread Summary")

    threads_response = requests.get(f"{BASE_URL}/session/{session_id}/threads")
    all_threads = threads_response.json()

    print(f"Total threads: {len(all_threads['threads'])}")
    print(f"Active thread: {all_threads['active_thread_id']}")
    print("\nThread details:")
    for thread in all_threads["threads"]:
        print(f"  [{thread['type']}] {thread['title']}")
        print(f"    Questions asked: {thread['questions_asked']}")
        print(f"    Reflections: {len(thread['notes'])}")

    # 8. Synthesize with execution bundle
    print_section("7. Generating Final Plan with Execution Bundle")

    finish_response = requests.post(
        f"{BASE_URL}/session/{session_id}/finish",
        json={
            "view_profile": "builder",
            "include_execution_bundle": True
        }
    )

    final = finish_response.json()

    print(f"✓ Plan generated:")
    print(f"  Markdown: {len(final['markdown_brief'])} characters")
    print(f"  JSON plan: {len(json.dumps(final['json_plan']))} characters")

    # Execution bundle details
    if "execution_bundle" in final and final["execution_bundle"]:
        bundle = final["execution_bundle"]
        print(f"\n✓ Execution Bundle:")
        print(f"  Language: {bundle['repo_scaffold']['language']}")
        print(f"  Frameworks: {', '.join(bundle['repo_scaffold']['frameworks'])}")
        print(f"  Tasks: {len(bundle['tasks'])}")
        print(f"  AI Prompts: {len(bundle['prompts'])}")

        print(f"\n  Task Breakdown:")
        for task in bundle["tasks"][:5]:  # First 5 tasks
            print(f"    [{task['phase']}] {task['title']} ({task['estimate']})")

        print(f"\n  AI-Ready Prompts:")
        for prompt in bundle["prompts"]:
            print(f"    {prompt['title']} (for {prompt['target']})")

    # 9. Show different view profiles
    print_section("8. View Profiles Comparison")

    for view in ["builder", "stakeholder", "investor"]:
        view_response = requests.post(
            f"{BASE_URL}/session/{session_id}/finish",
            json={
                "view_profile": view,
                "include_execution_bundle": False
            }
        )
        view_plan = view_response.json()
        print(f"{view.capitalize()} view: {len(view_plan['markdown_brief'])} chars")

    print_section("✅ Complete v0.2 Workflow Finished!")

    print(f"""
Summary:
- Session ID: {session_id}
- Threads created: {len(all_threads['threads'])}
- Reflections captured: {sum(len(t['notes']) for t in all_threads['threads'])}
- Execution bundle generated: Yes
- View profiles tested: 3

Next steps:
1. Review the execution bundle tasks
2. Use the AI prompts with ClaudeCode/Cursor
3. Start implementation following the phase-based plan
    """)


if __name__ == "__main__":
    main()
