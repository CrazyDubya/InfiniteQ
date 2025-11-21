"""
Example 3: Execution Bundle Demo

Shows how to generate and use execution bundles for immediate project kickoff.
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def main():
    print("=== InfiniteQ v0.2: Execution Bundle Demo ===\n")

    # Create session
    print("Creating session for a fintech app...")
    session_response = requests.post(f"{BASE_URL}/session", json={
        "idea": "Mobile app for personal finance management with AI budgeting assistant",
        "project_profile": {
            "type": "mobile_app",
            "team_size": "solo",
            "tech_constraints": ["react native", "firebase", "openai api"],
            "timeline": "1-3_months",
            "budget_band": "1k-10k"
        },
        "persona_profile": {
            "role": "founder_solo",
            "tech_comfort": 7,
            "business_comfort": 5,
            "preferred_depth": "medium"
        }
    })

    session_id = session_response.json()["session_id"]
    print(f"✓ Session: {session_id}\n")

    # Answer a few questions (simplified for demo)
    # In real usage, you'd go through the full interview
    print("Going through planning interview...\n")

    # Finish with execution bundle
    print("Generating execution bundle...")
    finish_response = requests.post(
        f"{BASE_URL}/session/{session_id}/finish",
        json={
            "view_profile": "agent_spec",
            "include_execution_bundle": True
        }
    )

    result = finish_response.json()
    bundle = result["execution_bundle"]

    # Display execution bundle
    print("\n" + "="*70)
    print("  EXECUTION BUNDLE")
    print("="*70 + "\n")

    # 1. Repository Scaffold
    print("1. REPOSITORY SCAFFOLD")
    print("-" * 70)
    scaffold = bundle["repo_scaffold"]
    print(f"Language: {scaffold['language']}")
    print(f"Frameworks: {', '.join(scaffold['frameworks'])}\n")
    print("Suggested Structure:")
    for path, items in scaffold["structure"].items():
        if path:
            print(f"  {path}")
            for item in items:
                print(f"    - {item}")
        else:
            print("  Root:")
            for item in items:
                print(f"    - {item}")
    print()

    # 2. Task Breakdown
    print("2. TASK BREAKDOWN (Phased Implementation)")
    print("-" * 70)
    tasks_by_phase = {}
    for task in bundle["tasks"]:
        phase = task["phase"]
        if phase not in tasks_by_phase:
            tasks_by_phase[phase] = []
        tasks_by_phase[phase].append(task)

    for phase in ["prototype", "v1", "scale_up", "v2_plus"]:
        if phase in tasks_by_phase:
            print(f"\n📋 {phase.upper().replace('_', ' ')}:")
            for task in tasks_by_phase[phase]:
                print(f"\n   [{task['estimate']}] {task['title']}")
                print(f"   {task['description']}")
                print(f"   Acceptance Criteria:")
                for criterion in task["acceptance_criteria"]:
                    print(f"     ✓ {criterion}")
                if task["dependencies"]:
                    print(f"   Dependencies: {', '.join(task['dependencies'])}")
    print()

    # 3. AI-Ready Prompts
    print("3. AI-READY PROMPTS")
    print("-" * 70)
    for prompt in bundle["prompts"]:
        print(f"\n🤖 {prompt['title']} (for {prompt['target'].upper()})")
        print("-" * 70)
        print(prompt["prompt"])
        print()

    # 4. Save to files
    print("4. SAVING TO FILES")
    print("-" * 70)

    # Save scaffold as JSON
    with open("scaffold.json", "w") as f:
        json.dump(scaffold, f, indent=2)
    print("✓ Saved scaffold.json")

    # Save tasks as JSON
    with open("tasks.json", "w") as f:
        json.dump(bundle["tasks"], f, indent=2)
    print("✓ Saved tasks.json")

    # Save prompts as text files
    for i, prompt in enumerate(bundle["prompts"], 1):
        filename = f"prompt_{i}_{prompt['target']}.txt"
        with open(filename, "w") as f:
            f.write(f"# {prompt['title']}\n")
            f.write(f"# Target: {prompt['target']}\n\n")
            f.write(prompt["prompt"])
        print(f"✓ Saved {filename}")

    # Save full markdown plan
    with open("plan.md", "w") as f:
        f.write(result["markdown_brief"])
    print("✓ Saved plan.md")

    print("\n" + "="*70)
    print("  NEXT STEPS")
    print("="*70 + "\n")

    print("""
1. Review the generated files:
   - scaffold.json: Repository structure
   - tasks.json: Phased task breakdown
   - prompt_*.txt: AI coding tool prompts
   - plan.md: Complete project plan

2. Initialize your project:
   - Create the repo structure from scaffold.json
   - Set up version control (git init)
   - Install dependencies

3. Start with AI coding assistant:
   - Open prompt_1_claudecode.txt
   - Paste into ClaudeCode/Cursor/Windsurf
   - Let AI set up your project

4. Work through tasks:
   - Follow the phased breakdown in tasks.json
   - Start with PROTOTYPE phase
   - Complete acceptance criteria before moving on

5. Iterate:
   - Come back to InfiniteQ for specific threads (architecture, UX, etc.)
   - Use reflection pulses to capture new insights
   - Generate updated execution bundles as plan evolves
    """)

    print("✅ Execution bundle ready for immediate action!")


if __name__ == "__main__":
    main()
