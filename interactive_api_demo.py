"""
Real Estate Agent - Interactive HTTP API Demo
==============================================

Interactive script that tests the broker agent HTTP API.
Shows JSON responses at each step of the conversation.

Prerequisites:
  - FastAPI app running: uvicorn main:app --reload
  - Or add to main.py: app.include_router(router)

Run with: python interactive_api_demo.py
"""

import httpx
import json
import asyncio

# Configuration
BASE_URL = "http://localhost:8000/api/broker_agent"


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_json(data, label: str = ""):
    """Pretty print JSON data"""
    if label:
        print(f"\n📋 {label}:")
    print(json.dumps(data, indent=2, default=str))


def print_request(method: str, endpoint: str, body: dict = None):
    """Print request details"""
    print(f"\n📤 Request:")
    print(f"   {method} {endpoint}")
    if body:
        print(f"   Body: {json.dumps(body)}")


def print_response(response: httpx.Response):
    """Print response details"""
    print(f"\n📥 Response:")
    print(f"   Status: {response.status_code}")
    try:
        data = response.json()
        print_json(data, "Response JSON")
        return data
    except:
        print(f"   Body: {response.text}")
        return None


async def main():
    """Interactive demo of the HTTP API"""

    print_header("REAL ESTATE AGENT - INTERACTIVE HTTP API DEMO")

    async with httpx.AsyncClient() as client:
        # ====================================================================
        # STEP 1: CREATE SESSION
        # ====================================================================

        print("📍 STEP 1: Creating a new session...")
        print("-" * 80)

        print_request("POST", "/sessions", {})

        response = await client.post(f"{BASE_URL}/sessions", json={})
        data = print_response(response)

        if response.status_code != 200:
            print("❌ Failed to create session")
            return

        session_id = data["session_id"]
        print(f"\n✅ Session created: {session_id}")

        # ====================================================================
        # STEP 2: GET CURRENT QUESTION
        # ====================================================================

        print_header("STEP 2: Getting current question")

        print_request("GET", f"/sessions/{session_id}")

        response = await client.get(f"{BASE_URL}/sessions/{session_id}")
        data = print_response(response)

        print(f"\n💬 Agent: {data['message']}")

        # ====================================================================
        # STEP 3: ANSWER Q1 - TRANSACTION TYPE
        # ====================================================================

        print_header("STEP 3: Answer Q1 - Transaction Type")

        answer = "buy"
        body = {"answer": answer, "question_id": "transaction_type"}
        print_request("POST", f"/sessions/{session_id}/answer", body)
        print(f"\n👤 User answers: {answer}")

        response = await client.post(
            f"{BASE_URL}/sessions/{session_id}/answer",
            json=body,
        )
        data = print_response(response)

        print(f"\n💬 Agent: {data['message']}")
        print_json(data["user_summary"], "User Summary So Far")

        # ====================================================================
        # STEP 4: ANSWER Q2 - LOCATION
        # ====================================================================

        print_header("STEP 4: Answer Q2 - Location")

        answer = "Indiranagar"
        body = {"answer": answer, "question_id": "location"}
        print_request("POST", f"/sessions/{session_id}/answer", body)
        print(f"\n👤 User answers: {answer}")

        response = await client.post(
            f"{BASE_URL}/sessions/{session_id}/answer",
            json=body,
        )
        data = print_response(response)

        print(f"\n💬 Agent: {data['message']}")
        print_json(data["user_summary"], "User Summary So Far")

        # ====================================================================
        # STEP 5: ANSWER Q3 - PRICE RANGE
        # ====================================================================

        print_header("STEP 5: Answer Q3 - Price Range (in lakhs)")

        answer = {"min": 50.0, "max": 100.0}
        body = {"answer": answer, "question_id": "price_range"}
        print_request("POST", f"/sessions/{session_id}/answer", body)
        print(f"\n👤 User answers: {json.dumps(answer)}")

        response = await client.post(
            f"{BASE_URL}/sessions/{session_id}/answer",
            json=body,
        )
        data = print_response(response)

        print(f"\n💬 Agent: {data['message']}")
        print_json(data["user_summary"], "User Summary So Far")

        # ====================================================================
        # STEP 6: ANSWER Q4 - PROPERTY AREA
        # ====================================================================

        print_header("STEP 6: Answer Q4 - Property Area (in sq ft)")

        answer = {"min": 1000, "max": 2500}
        body = {"answer": answer, "question_id": "property_area"}
        print_request("POST", f"/sessions/{session_id}/answer", body)
        print(f"\n👤 User answers: {json.dumps(answer)}")

        response = await client.post(
            f"{BASE_URL}/sessions/{session_id}/answer",
            json=body,
        )
        data = print_response(response)

        print(f"\n💬 Agent: {data['message']}")
        print_json(data["user_summary"], "User Summary So Far")

        # ====================================================================
        # STEP 7: ANSWER Q5 - PROPERTY TYPE
        # ====================================================================

        print_header("STEP 7: Answer Q5 - Property Type")

        answer = "apartment"
        body = {"answer": answer, "question_id": "property_type"}
        print_request("POST", f"/sessions/{session_id}/answer", body)
        print(f"\n👤 User answers: {answer}")

        response = await client.post(
            f"{BASE_URL}/sessions/{session_id}/answer",
            json=body,
        )
        data = print_response(response)

        print(f"\n💬 Agent: {data['message']}")
        print_json(data["user_summary"], "User Summary So Far")

        # ====================================================================
        # STEP 8: ANSWER Q6 - SPECIAL FEATURES
        # ====================================================================

        print_header("STEP 8: Answer Q6 - Special Features")

        answer = ["gym", "pool", "parking", "security"]
        body = {"answer": answer, "question_id": "special_features"}
        print_request("POST", f"/sessions/{session_id}/answer", body)
        print(f"\n👤 User answers: {json.dumps(answer)}")

        response = await client.post(
            f"{BASE_URL}/sessions/{session_id}/answer",
            json=body,
        )
        data = print_response(response)

        print(f"\n💬 Agent: {data['message']}")
        print(f"\n✅ Conversation Completed: {data['completed']}")

        # ====================================================================
        # STEP 9: GET FINAL SUMMARY
        # ====================================================================

        print_header("STEP 9: Getting final summary")

        print_request("GET", f"/sessions/{session_id}/summary")

        response = await client.get(f"{BASE_URL}/sessions/{session_id}/summary")
        data = print_response(response)

        # ====================================================================
        # STEP 10: GET FINAL SESSION STATE
        # ====================================================================

        print_header("STEP 10: Getting final session state")

        print_request("GET", f"/sessions/{session_id}")

        response = await client.get(f"{BASE_URL}/sessions/{session_id}")
        data = print_response(response)

        print_json(data["messages"], "Full Conversation History")

        # ====================================================================
        # COMPLETION
        # ====================================================================

        print_header("✅ HTTP API DEMO COMPLETED")

        completion_info = {
            "status": "success",
            "session_id": session_id,
            "base_url": BASE_URL,
            "endpoints_tested": [
                "POST /sessions",
                "GET /sessions/{id}",
                "POST /sessions/{id}/answer",
                "GET /sessions/{id}/summary",
            ],
            "total_requests": 10,
        }

        print_json(completion_info, "Completion Info")

        print("\n" + "=" * 80)
        print("  ✅ ALL ENDPOINTS TESTED SUCCESSFULLY")
        print("=" * 80)
        print("\n📝 Available Endpoints:")
        print(f"   POST   {BASE_URL}/sessions")
        print(f"   GET    {BASE_URL}/sessions/{{session_id}}")
        print(f"   POST   {BASE_URL}/sessions/{{session_id}}/answer")
        print(f"   GET    {BASE_URL}/sessions/{{session_id}}/summary")
        print("\n")


if __name__ == "__main__":
    print("\n⚠️  Make sure your FastAPI server is running!")
    print("   Run: uvicorn main:app --reload")
    print("   Or add this to main.py: app.include_router(router)")
    print("\nPress Enter to continue...")
    input()

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. FastAPI server is running on http://localhost:8000")
        print("  2. Broker agent router is included in the app")
        print("  3. You have httpx installed: pip install httpx")
