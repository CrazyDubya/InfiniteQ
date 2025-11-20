"""
Example 1: Simple Planning Session

Demonstrates basic v0.2 usage with minimal configuration.
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def main():
    print("=== InfiniteQ v0.2: Simple Planning Session ===\n")

    # 1. Create session with a simple idea
    print("1. Creating session...")
    create_response = requests.post(f"{BASE_URL}/session", json={
        "idea": "A mobile app that helps people track their daily water intake"
    })

    session_data = create_response.json()
    session_id = session_data["session_id"]
    thread_id = session_data["thread_id"]

    print(f"   ✓ Session created: {session_id}")
    print(f"   ✓ Initial thread: {thread_id}")
    print(f"   ✓ Project type: {session_data['project_profile']['type']}")
    print()

    # 2. View first questions
    print("2. First questions:")
    for i, q in enumerate(session_data["first_questions"], 1):
        print(f"   Q{i}: {q['text']}")
        for opt in q["options"]:
            print(f"      {opt['id']}. {opt['text']}")
    print()

    # 3. Answer first question
    print("3. Submitting answer...")
    first_q = session_data["first_questions"][0]
    answer_response = requests.post(
        f"{BASE_URL}/session/{session_id}/threads/{thread_id}/answer",
        json={
            "answers": [
                {
                    "question_id": first_q["id"],
                    "choice_id": first_q["options"][0]["id"],
                    "free_text": "Focus on iOS first, Android later"
                }
            ]
        }
    )

    answer_data = answer_response.json()
    print(f"   ✓ Answer submitted")
    print(f"   ✓ Next questions: {len(answer_data['next_questions'])}")
    print()

    # 4. Check session status
    print("4. Session status:")
    status_response = requests.get(f"{BASE_URL}/session/{session_id}/status")
    status = status_response.json()

    print(f"   Total questions: {status['total_questions']}")
    print(f"   Active thread: {status['active_thread_id']}")
    print(f"   Coverage: {status['coverage']['features']:.0f}% features, {status['coverage']['architecture']:.0f}% architecture")
    print()

    # 5. Finish and get plan
    print("5. Generating final plan...")
    finish_response = requests.post(
        f"{BASE_URL}/session/{session_id}/finish",
        json={
            "view_profile": "builder",
            "include_execution_bundle": False
        }
    )

    plan = finish_response.json()
    print(f"   ✓ Plan generated ({len(plan['markdown_brief'])} characters)")
    print(f"\n--- Plan Preview ---")
    print(plan["markdown_brief"][:500] + "...\n")

    print("✅ Simple session complete!")


if __name__ == "__main__":
    main()
