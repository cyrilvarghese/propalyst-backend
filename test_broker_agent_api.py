"""
Real Estate Agent - API Endpoint Tests
========================================

Tests for FastAPI router endpoints using TestClient.

Run with: pytest test_broker_agent_api.py -v
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from broker_agent.router import router


# ============================================================================
# SETUP
# ============================================================================

# Create test app
app = FastAPI()
app.include_router(router)

# Create test client
client = TestClient(app)


# ============================================================================
# SESSION CREATION TESTS
# ============================================================================

class TestCreateSession:
    """Test POST /api/broker_agent/sessions"""

    def test_create_session_success(self):
        """Test successful session creation"""
        response = client.post("/api/broker_agent/sessions", json={})

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "message" in data
        assert len(data["session_id"]) > 0
        assert "Welcome" in data["message"]

    def test_create_session_returns_valid_uuid(self):
        """Test session ID is valid UUID format"""
        response = client.post("/api/broker_agent/sessions", json={})
        data = response.json()
        session_id = data["session_id"]

        # UUID format check (basic)
        parts = session_id.split("-")
        assert len(parts) == 5

    def test_create_session_unique_ids(self):
        """Test each session gets unique ID"""
        response1 = client.post("/api/broker_agent/sessions", json={})
        response2 = client.post("/api/broker_agent/sessions", json={})

        session_id_1 = response1.json()["session_id"]
        session_id_2 = response2.json()["session_id"]

        assert session_id_1 != session_id_2


# ============================================================================
# GET SESSION TESTS
# ============================================================================

class TestGetSession:
    """Test GET /api/broker_agent/sessions/{session_id}"""

    def test_get_session_success(self):
        """Test getting session returns current question"""
        # Create session
        create_response = client.post("/api/broker_agent/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Get session
        response = client.get(f"/api/broker_agent/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "current_question" in data
        assert data["current_question"]["id"] == "transaction_type"
        assert "message" in data
        assert data["completed"] is False
        assert "user_summary" in data
        assert "messages" in data

    def test_get_session_not_found(self):
        """Test getting non-existent session returns 404"""
        response = client.get("/api/broker_agent/sessions/invalid-session-id")
        assert response.status_code == 404

    def test_get_session_user_summary_empty_initially(self):
        """Test user summary is empty for new session"""
        create_response = client.post("/api/broker_agent/sessions", json={})
        session_id = create_response.json()["session_id"]

        response = client.get(f"/api/broker_agent/sessions/{session_id}")
        data = response.json()
        summary = data["user_summary"]

        assert summary["transaction_type"] is None
        assert summary["location"] is None
        assert summary["property_type"] is None


# ============================================================================
# SUBMIT ANSWER TESTS
# ============================================================================

class TestSubmitAnswer:
    """Test POST /api/broker_agent/sessions/{session_id}/answer"""

    def test_submit_answer_transaction_type(self):
        """Test submitting answer to transaction type"""
        # Create session
        create_response = client.post("/api/broker_agent/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Submit answer
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "buy", "question_id": "transaction_type"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_summary"]["transaction_type"] == "buy"
        assert data["current_question"]["id"] == "location"

    def test_submit_answer_location(self):
        """Test submitting answer to location"""
        # Create session and answer Q1
        create_response = client.post("/api/broker_agent/sessions", json={})
        session_id = create_response.json()["session_id"]

        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "buy", "question_id": "transaction_type"},
        )

        # Answer Q2
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "Indiranagar", "question_id": "location"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_summary"]["location"] == "Indiranagar"
        assert data["current_question"]["id"] == "price_range"

    def test_submit_answer_price_range(self):
        """Test submitting answer to price range"""
        # Setup: Create session and answer Q1, Q2
        create_response = client.post("/api/broker_agent/sessions", json={})
        session_id = create_response.json()["session_id"]

        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "buy", "question_id": "transaction_type"},
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "Indiranagar", "question_id": "location"},
        )

        # Answer Q3
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": {"min": 50.0, "max": 100.0},
                "question_id": "price_range",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_summary"]["price_range"]["min"] == 50.0
        assert data["user_summary"]["price_range"]["max"] == 100.0
        assert data["current_question"]["id"] == "property_area"

    def test_submit_answer_property_area(self):
        """Test submitting answer to property area"""
        # Setup: Create session and answer Q1-Q3
        create_response = client.post("/api/broker_agent/sessions", json={})
        session_id = create_response.json()["session_id"]

        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "buy", "question_id": "transaction_type"},
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "Indiranagar", "question_id": "location"},
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": {"min": 50.0, "max": 100.0},
                "question_id": "price_range",
            },
        )

        # Answer Q4
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": {"min": 1000, "max": 2500},
                "question_id": "property_area",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_summary"]["area_range"]["min"] == 1000
        assert data["user_summary"]["area_range"]["max"] == 2500
        assert data["current_question"]["id"] == "property_type"

    def test_submit_answer_property_type(self):
        """Test submitting answer to property type"""
        # Setup: Create session and answer Q1-Q4
        create_response = client.post("/api/broker_agent/sessions", json={})
        session_id = create_response.json()["session_id"]

        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "buy", "question_id": "transaction_type"},
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "Indiranagar", "question_id": "location"},
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": {"min": 50.0, "max": 100.0},
                "question_id": "price_range",
            },
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": {"min": 1000, "max": 2500},
                "question_id": "property_area",
            },
        )

        # Answer Q5
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "apartment", "question_id": "property_type"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_summary"]["property_type"] == "apartment"
        assert data["current_question"]["id"] == "special_features"

    def test_submit_answer_special_features(self):
        """Test submitting answer to special features"""
        # Setup: Create session and answer Q1-Q5
        create_response = client.post("/api/broker_agent/sessions", json={})
        session_id = create_response.json()["session_id"]

        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "buy", "question_id": "transaction_type"},
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "Indiranagar", "question_id": "location"},
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": {"min": 50.0, "max": 100.0},
                "question_id": "price_range",
            },
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": {"min": 1000, "max": 2500},
                "question_id": "property_area",
            },
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "apartment", "question_id": "property_type"},
        )

        # Answer Q6
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": ["gym", "pool", "parking"],
                "question_id": "special_features",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert set(data["user_summary"]["special_features"]) == {
            "gym",
            "pool",
            "parking",
        }
        assert data["completed"] is True

    def test_submit_answer_not_found(self):
        """Test submitting answer to non-existent session"""
        response = client.post(
            "/api/broker_agent/sessions/invalid-session/answer",
            json={"answer": "buy", "question_id": "transaction_type"},
        )
        assert response.status_code == 404

    def test_submit_answer_updates_history(self):
        """Test conversation history is updated"""
        create_response = client.post("/api/broker_agent/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Submit first answer
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "buy", "question_id": "transaction_type"},
        )

        data = response.json()
        messages = data["messages"]

        # Should have user and agent messages
        assert len(messages) >= 2
        assert any(m["role"] == "user" for m in messages)
        assert any(m["role"] == "agent" for m in messages)


# ============================================================================
# GET SUMMARY TESTS
# ============================================================================

class TestGetUserSummary:
    """Test GET /api/broker_agent/sessions/{session_id}/summary"""

    def test_get_summary_success(self):
        """Test getting user summary"""
        # Create session and complete conversation
        create_response = client.post("/api/broker_agent/sessions", json={})
        session_id = create_response.json()["session_id"]

        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "buy", "question_id": "transaction_type"},
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "Indiranagar", "question_id": "location"},
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": {"min": 50.0, "max": 100.0},
                "question_id": "price_range",
            },
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": {"min": 1000, "max": 2500},
                "question_id": "property_area",
            },
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "apartment", "question_id": "property_type"},
        )
        client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": ["gym", "pool"],
                "question_id": "special_features",
            },
        )

        # Get summary
        response = client.get(f"/api/broker_agent/sessions/{session_id}/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["transaction_type"] == "buy"
        assert data["location"] == "Indiranagar"
        assert data["price_range"]["min"] == 50.0
        assert data["price_range"]["max"] == 100.0
        assert data["area_range"]["min"] == 1000
        assert data["area_range"]["max"] == 2500
        assert data["property_type"] == "apartment"
        assert set(data["special_features"]) == {"gym", "pool"}

    def test_get_summary_not_found(self):
        """Test getting summary for non-existent session"""
        response = client.get("/api/broker_agent/sessions/invalid-session/summary")
        assert response.status_code == 404

    def test_get_summary_empty_session(self):
        """Test summary for new session with no answers"""
        create_response = client.post("/api/broker_agent/sessions", json={})
        session_id = create_response.json()["session_id"]

        response = client.get(f"/api/broker_agent/sessions/{session_id}/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["transaction_type"] is None
        assert data["location"] is None
        assert data["property_type"] is None
        assert data["special_features"] == []


# ============================================================================
# CONVERSATION FLOW TESTS
# ============================================================================

class TestConversationFlow:
    """Test complete conversation flow through API"""

    def test_full_api_conversation(self):
        """Test complete conversation via API"""
        # 1. Create session
        response = client.post("/api/broker_agent/sessions", json={})
        session_id = response.json()["session_id"]
        assert response.status_code == 200

        # 2. Get first question (transaction type)
        response = client.get(f"/api/broker_agent/sessions/{session_id}")
        assert response.json()["current_question"]["id"] == "transaction_type"

        # 3. Answer Q1
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "sell", "question_id": "transaction_type"},
        )
        assert response.json()["user_summary"]["transaction_type"] == "sell"

        # 4. Answer Q2
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "Whitefield", "question_id": "location"},
        )
        assert response.json()["user_summary"]["location"] == "Whitefield"

        # 5. Answer Q3
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": {"min": 100.0, "max": 200.0},
                "question_id": "price_range",
            },
        )
        assert (
            response.json()["user_summary"]["price_range"]["min"] == 100.0
        )

        # 6. Answer Q4
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": {"min": 2000, "max": 4000},
                "question_id": "property_area",
            },
        )
        assert response.json()["user_summary"]["area_range"]["min"] == 2000

        # 7. Answer Q5
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={"answer": "villa", "question_id": "property_type"},
        )
        assert response.json()["user_summary"]["property_type"] == "villa"

        # 8. Answer Q6
        response = client.post(
            f"/api/broker_agent/sessions/{session_id}/answer",
            json={
                "answer": ["garden", "security", "north_facing"],
                "question_id": "special_features",
            },
        )
        assert response.json()["completed"] is True
        assert len(response.json()["user_summary"]["special_features"]) == 3


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    # Run with: pytest test_broker_agent_api.py -v
    pytest.main([__file__, "-v"])
