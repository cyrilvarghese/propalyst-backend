"""
Simple API tester for Broker Agent
Shows raw JSON responses from the API

Run: python test_broker_api.py
"""

import httpx
import asyncio
import json
from typing import Optional

API_URL = "http://localhost:8000/api/broker"


async def test_broker_flow():
    """Test the complete broker conversation flow"""

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Create new session
        print("\n" + "="*80)
        print("STEP 1: Create New Session")
        print("="*80)
        response = await client.get(f"{API_URL}/new-session")
        session_data = response.json()
        print(json.dumps(session_data, indent=2))
        session_id = session_data["session_id"]

        # Step 2-9: Answer questions
        answers = [
            ("transaction_type", "buy", "Q1: Transaction Type"),
            ("location", "Indiranagar", "Q2: Location"),
            ("bhk", "3", "Q3: BHK"),
            ("property_type", "apartment", "Q4: Property Type"),
            ("budget_min", "1.5", "Q5a: Budget Min"),
            ("budget_max", "2.5", "Q5b: Budget Max"),
            ("open_to_nearby", "yes", "Q6: Open to Nearby"),
            ("customer_phone", "9876543210", "Q8: Contact Info"),
        ]

        for i, (field_name, user_input, description) in enumerate(answers, 2):
            print("\n" + "="*80)
            print(f"STEP {i}: {description}")
            print(f"Input: {user_input}")
            print("="*80)

            response = await client.post(
                f"{API_URL}/chat",
                json={
                    "session_id": session_id,
                    "user_input": user_input,
                    "field_name": field_name
                }
            )

            result = response.json()
            print(json.dumps(result, indent=2))

            if result.get("error"):
                print(f"\n⚠️  ERROR: {result['error']}")

            if result.get("completed"):
                print(f"\n✅ CONVERSATION COMPLETED!")

            if result.get("lead_stored"):
                print(f"\n💾 LEAD STORED!")


async def test_invalid_input():
    """Test validation with invalid input"""

    async with httpx.AsyncClient(timeout=30) as client:
        # Create session
        response = await client.get(f"{API_URL}/new-session")
        session_id = response.json()["session_id"]

        print("\n" + "="*80)
        print("TEST: Invalid Input - Bad Location")
        print("="*80)

        # Answer transaction type
        await client.post(
            f"{API_URL}/chat",
            json={
                "session_id": session_id,
                "user_input": "buy",
                "field_name": "transaction_type"
            }
        )

        # Try invalid location
        response = await client.post(
            f"{API_URL}/chat",
            json={
                "session_id": session_id,
                "user_input": "xyz123invalidlocation",
                "field_name": "location"
            }
        )

        result = response.json()
        print(json.dumps(result, indent=2))

        if result.get("error"):
            print(f"\n✅ Validation correctly caught invalid input!")


async def main():
    """Run all tests"""

    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "🚀 BROKER AGENT API TESTER 🚀" + " "*31 + "║")
    print("╚" + "="*78 + "╝")

    try:
        # Test 1: Full conversation flow
        await test_broker_flow()

        # Test 2: Invalid input handling
        await test_invalid_input()

        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nMake sure the server is running:")
        print("  python -m uvicorn main:app --reload --port 8000")


if __name__ == "__main__":
    asyncio.run(main())
