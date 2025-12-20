"""
Interactive API tester for Broker Agent
Prompts you to enter responses and shows JSON

Run: python test_broker_interactive.py
"""

import httpx
import asyncio
import json

API_URL = "http://localhost:8000/api/broker"


def print_response(response_data):
    """Pretty print the API response"""
    print("\n" + "="*80)
    print("API Response:")
    print("="*80)
    print(json.dumps(response_data, indent=2))
    print()


async def interactive_test():
    """Interactive conversation with the broker agent"""

    async with httpx.AsyncClient(timeout=30) as client:
        # Create session
        print("\n" + "="*80)
        print("Creating new session...")
        print("="*80)
        response = await client.get(f"{API_URL}/new-session")
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"✅ Session ID: {session_id}")

        # Start conversation
        print("\n" + "="*80)
        print("Starting conversation...")
        print("="*80)
        response = await client.post(
            f"{API_URL}/chat",
            json={"session_id": session_id}
        )
        result = response.json()
        print_response(result)

        # Main conversation loop
        question_count = 1
        while not result.get("completed"):
            current_question = result.get("current_question")

            if not current_question:
                print("No more questions!")
                break

            question_id = current_question.get("id")
            question_text = current_question.get("question")
            control_type = current_question.get("controlType")
            data = current_question.get("data", {})

            # Display question and options
            print("\n" + "="*80)
            print(f"Question #{question_count}: {question_text}")
            print("="*80)

            user_input = None

            if control_type == "radio":
                options = data.get("options", [])
                print("\nOptions:")
                for i, opt in enumerate(options, 1):
                    print(f"  {i}. {opt['label']}")
                choice = input("Enter your choice (number or value): ").strip()

                # Try to match by number or value
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(options):
                        user_input = options[idx]["value"]
                except ValueError:
                    # Try to match by value
                    user_input = choice

            elif control_type == "toggle-group":
                options = data.get("options", [])
                print("\nOptions:")
                for i, opt in enumerate(options, 1):
                    label = f"{opt['label']}"
                    if "count" in opt:
                        label += f" ({opt['count']} available)"
                    print(f"  {i}. {label}")
                choice = input("Enter your choice (number or value): ").strip()

                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(options):
                        user_input = options[idx]["value"]
                except ValueError:
                    user_input = choice

            elif control_type == "range-slider":
                min_val = data.get("min", 0)
                max_val = data.get("max", 100)
                unit = data.get("unit", "")
                print(f"\nEnter range in {unit} (min: {min_val}, max: {max_val})")
                print("Examples: '1.5-2.5' or '1.5 to 2.5'")
                user_input = input("Enter range: ").strip()

            elif control_type == "text":
                placeholder = data.get("placeholder", "")
                suggestions = data.get("suggestions", [])
                if suggestions:
                    print(f"\nSuggestions: {', '.join(suggestions[:5])}")
                print(f"Placeholder: {placeholder}")
                user_input = input("Enter your answer: ").strip()

            elif control_type == "tags":
                suggestions = data.get("suggestions", [])
                if suggestions:
                    print(f"\nSuggestions: {', '.join(suggestions[:10])}")
                print("Enter tags separated by commas (or skip)")
                user_input = input("Enter tags: ").strip()

            # If no input, skip
            if not user_input:
                print("⏭️  Skipping question...")
                continue

            # Send answer to API
            print(f"\n📤 Sending: {user_input}")
            response = await client.post(
                f"{API_URL}/chat",
                json={
                    "session_id": session_id,
                    "user_input": user_input,
                    "field_name": question_id
                }
            )

            result = response.json()
            print_response(result)

            if result.get("error"):
                print(f"⚠️  Error: {result['error']}")
                print("Try again with different input...")
                continue

            question_count += 1

            if result.get("completed"):
                print("\n" + "="*80)
                print("✅ CONVERSATION COMPLETED!")
                print("="*80)
                if result.get("lead_stored"):
                    print("💾 Lead has been stored!")


async def main():
    """Run interactive test"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*10 + "🚀 BROKER AGENT INTERACTIVE TESTER 🚀" + " "*32 + "║")
    print("╚" + "="*78 + "╝")

    try:
        await interactive_test()
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nMake sure the server is running:")
        print("  python -m uvicorn main:app --reload --port 8000")


if __name__ == "__main__":
    asyncio.run(main())
