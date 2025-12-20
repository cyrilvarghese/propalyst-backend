"""
Streamlit UI for testing the Broker Agent

Run with: streamlit run test_broker_streamlit.py
"""

import streamlit as st
import httpx
import json
from typing import Optional, Dict, Any

# Page configuration
st.set_page_config(
    page_title="Broker Agent Tester",
    page_icon="🏠",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .broker-message {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid #4CAF50;
    }

    .user-message {
        background-color: #e3f2fd;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        text-align: right;
        border-right: 4px solid #2196F3;
    }

    .question-box {
        background-color: #fff3e0;
        padding: 15px;
        border-radius: 8px;
        border: 2px solid #FF9800;
    }

    .market-insight {
        background-color: #f3e5f5;
        padding: 10px;
        border-radius: 5px;
        font-size: 0.9em;
        margin: 10px 0;
        border-left: 3px solid #9C27B0;
    }

    .status-bar {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
        font-weight: bold;
    }

    .status-completed {
        background-color: #c8e6c9;
        color: #2e7d32;
    }

    .status-lead-stored {
        background-color: #bbdefb;
        color: #1565c0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "state_data" not in st.session_state:
    st.session_state.state_data = {}
if "completed" not in st.session_state:
    st.session_state.completed = False
if "lead_stored" not in st.session_state:
    st.session_state.lead_stored = False

# API base URL
API_URL = "http://localhost:8000/api/broker"

async def create_session() -> str:
    """Create a new broker session"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/new-session")
        data = response.json()
        return data["session_id"]

async def send_message(session_id: str, user_input: Optional[str] = None, field_name: Optional[str] = None) -> Dict[str, Any]:
    """Send a message to the broker agent"""
    payload = {"session_id": session_id}
    if user_input and field_name:
        payload["user_input"] = user_input
        payload["field_name"] = field_name

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{API_URL}/chat", json=payload)
        return response.json()

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🏠 Broker Agent Tester")
with col2:
    st.caption("LangGraph Demo")

st.markdown("---")

# Sidebar for session management
with st.sidebar:
    st.header("Session Management")

    if st.button("🆕 New Session", use_container_width=True):
        try:
            with st.spinner("Creating new session..."):
                import asyncio
                new_session_id = asyncio.run(create_session())
                st.session_state.session_id = new_session_id
                st.session_state.conversation = []
                st.session_state.state_data = {}
                st.session_state.completed = False
                st.session_state.lead_stored = False

                # Fetch the first question
                result = asyncio.run(send_message(new_session_id))
                st.session_state.current_question = result.get("current_question")

                st.success("✅ New session created!")
                st.rerun()
        except Exception as e:
            st.error(f"Failed to create session: {str(e)}")

    if st.session_state.session_id:
        st.success(f"Session: `{st.session_state.session_id[:8]}...`")
    else:
        st.info("No active session")

    st.markdown("---")
    st.subheader("Progress")

    # Show progress of questions
    questions = [
        "Transaction Type",
        "Location",
        "BHK",
        "Property Type",
        "Budget",
        "Open to Nearby",
        "Special Features",
        "Contact Info"
    ]

    answered = len(st.session_state.conversation) // 2  # User + Broker pairs
    progress = min(answered / len(questions), 1.0)
    st.progress(progress, text=f"{answered}/{len(questions)} questions answered")

    if st.session_state.completed:
        st.success("✅ Conversation Completed!")
    if st.session_state.lead_stored:
        st.info("💾 Lead Stored")

    st.markdown("---")
    st.markdown("### About")
    st.caption("""
    This is a test interface for the LangGraph Broker Agent.

    It demonstrates:
    - Conversational Q&A flow
    - State persistence
    - LLM-based validation
    - Rich UI components
    """)

# Main content area
if not st.session_state.session_id:
    st.info("👈 Click 'New Session' in the sidebar to start", icon="ℹ️")

    if st.button("Start Testing", use_container_width=True, type="primary"):
        try:
            with st.spinner("Creating session..."):
                import asyncio
                new_session_id = asyncio.run(create_session())
                st.session_state.session_id = new_session_id

                # Fetch the first question
                result = asyncio.run(send_message(new_session_id))
                st.session_state.current_question = result.get("current_question")

                st.rerun()
        except Exception as e:
            st.error(f"Failed to create session: {str(e)}")

else:
    # Display conversation history
    if st.session_state.conversation:
        st.subheader("Conversation")
        for msg in st.session_state.conversation:
            if msg["role"] == "broker":
                st.markdown(f'<div class="broker-message">**Broker:** {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="user-message">**You:** {msg["content"]}</div>', unsafe_allow_html=True)

    # Show current question
    if st.session_state.current_question and not st.session_state.completed:
        st.markdown("---")
        question = st.session_state.current_question

        st.markdown(f'<div class="question-box"><strong>Current Question:</strong> {question["question"]}</div>',
                   unsafe_allow_html=True)

        # Show market insight if available
        if question.get("data", {}).get("marketInsights"):
            st.markdown(f'<div class="market-insight">💡 {question["data"]["marketInsights"]}</div>',
                       unsafe_allow_html=True)

        # Show appropriate input control based on controlType
        control_type = question.get("controlType", "text")
        field_id = question.get("id", "")
        data = question.get("data", {})

        user_input = None

        if control_type == "radio":
            options = data.get("options", [])
            labels = [opt["label"] for opt in options]
            values = [opt["value"] for opt in options]

            selected_label = st.radio(
                "Select an option:",
                labels,
                key=f"radio_{field_id}"
            )
            user_input = values[labels.index(selected_label)]

        elif control_type == "toggle-group":
            options = data.get("options", [])
            cols = st.columns(len(options))

            for i, (col, opt) in enumerate(zip(cols, options)):
                with col:
                    button_key = f"toggle_{field_id}_{i}"
                    if st.button(opt["label"], use_container_width=True, key=button_key):
                        st.session_state[f"selected_{field_id}"] = opt["value"]
                        st.rerun()

            # Show previously selected value and set user_input
            if f"selected_{field_id}" in st.session_state:
                selected = st.session_state[f"selected_{field_id}"]
                label = next((opt['label'] for opt in options if opt['value'] == selected), selected)
                st.info(f"✅ Selected: {label}")
                user_input = selected

        elif control_type == "range-slider":
            histogram = data.get("histogram", [])
            min_val = data.get("min", 0)
            max_val = data.get("max", 100)

            st.write("Select your budget range (in Crores):")
            selected_range = st.slider(
                "Budget Range",
                min_value=min_val,
                max_value=max_val,
                value=(min_val, max_val),
                step=data.get("step", 0.1),
                label_visibility="collapsed",
                key=f"slider_{field_id}"
            )

            # Display selected range
            st.metric("Your Budget Range", f"₹{selected_range[0]:.2f} Cr - ₹{selected_range[1]:.2f} Cr")

            # Show histogram
            if histogram:
                st.bar_chart({item["range"]: item["count"] for item in histogram})

            # Format as "X-Y crore" for the LLM to parse
            user_input = f"{selected_range[0]}-{selected_range[1]} crore"

        elif control_type == "text":
            placeholder = data.get("placeholder", "Enter your response...")
            suggestions = data.get("suggestions", [])

            if suggestions:
                st.write("💡 Suggestions:", ", ".join(suggestions[:5]))

            user_input = st.text_input(
                "Your answer:",
                placeholder=placeholder,
                key=f"text_{field_id}"
            )

        elif control_type == "tags":
            st.write("Add tags (optional):")
            suggestions = data.get("suggestions", [])

            # Simple tag input
            tags_input = st.text_input(
                "Type tags separated by commas:",
                placeholder="e.g., north-facing, pet-friendly",
                key=f"tags_{field_id}"
            )

            if tags_input:
                user_input = tags_input

        # Submit button
        if user_input is not None:
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("✅ Submit", use_container_width=True, type="primary"):
                    try:
                        with st.spinner("Processing..."):
                            import asyncio
                            result = asyncio.run(
                                send_message(
                                    st.session_state.session_id,
                                    str(user_input),
                                    field_id
                                )
                            )

                        # Update state
                        st.session_state.completed = result.get("completed", False)
                        st.session_state.lead_stored = result.get("lead_stored", False)

                        # Add to conversation
                        st.session_state.conversation.append({
                            "role": "user",
                            "content": str(user_input)
                        })
                        st.session_state.conversation.append({
                            "role": "broker",
                            "content": result.get("conversational_message", "")
                        })

                        # Update current question
                        st.session_state.current_question = result.get("current_question")
                        st.session_state.state_data = result

                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        else:
            st.info("👆 Select or enter a value above, then click Submit")

    elif st.session_state.completed:
        st.markdown("---")
        st.success("🎉 Conversation Complete!", icon="✅")

        if st.session_state.lead_stored:
            st.info("✅ Lead has been stored and broker team will contact you soon!")

        # Show summary
        st.subheader("Lead Summary")
        if st.session_state.state_data:
            data = st.session_state.state_data

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Transaction", data.get("state_data", {}).get("transaction_type", "N/A"))
                st.metric("Location", data.get("state_data", {}).get("location", "N/A"))
                st.metric("BHK", data.get("state_data", {}).get("bhk", "N/A"))

            with col2:
                st.metric("Property Type", data.get("state_data", {}).get("property_type", "N/A"))
                st.metric("Budget", data.get("state_data", {}).get("budget_max", "N/A"))
                st.metric("Phone", data.get("state_data", {}).get("customer_phone", "N/A"))

        if st.button("Start New Conversation", use_container_width=True):
            st.session_state.session_id = None
            st.session_state.conversation = []
            st.session_state.current_question = None
            st.session_state.state_data = {}
            st.session_state.completed = False
            st.session_state.lead_stored = False
            st.rerun()

# Footer
st.markdown("---")
st.caption("🚀 Built with LangGraph | Testing the Broker Agent")
