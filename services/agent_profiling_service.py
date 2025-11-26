"""
Agent Profiling Service
========================

Profiles real estate agents based on their WhatsApp message history using LLM analysis.
Reads from crea_top_agents_3m_msgs_grouped view and stores results in agent_profiles_clean table.
"""

import os
import json
from typing import List, Dict, Any, Optional
from google import genai
from dotenv import load_dotenv
from models.agent_profile import (
    TopAgentGrouped,
    AgentProfileLLMInput,
    AgentProfileLLMOutput,
    AgentProfileClean
)
from services.agent_profiling_progress_service import AgentProfilingProgressService

load_dotenv()


class AgentProfilingService:
    """Service for profiling agents using LLM analysis of their WhatsApp messages"""

    # Shared Gemini client instance (singleton pattern)
    _client: Optional[genai.Client] = None
    _model: str = "gemini-2.0-flash-exp"

    # LLM Prompt for agent profiling
    PROFILING_PROMPT = """You are analyzing WhatsApp messages from a real estate agent to create a structured profile of their specialization.

PROPERTY TYPE VOCABULARY (use these exact values):
- residential_apartment
- residential_villa
- plot_land
- commercial_office
- commercial_retail
- industrial_warehouse
- agri_land

ANALYSIS RULES:

1. **Primary Locations**: Identify 3-5 key areas or micro-markets mentioned across messages

2. **Property Types**: Use only the vocabulary above

3. **Price Ranges**:
   - Convert all prices to rupees (Cr → ×10000000, Lakh → ×100000, k → ×1000)
   - Ignore junk prices or investigate messages for any meaningfullness
   - Ignore "Price on request" or similar
   - Set to null if no reliable prices found

4. **BHK Range**:
   - Infer from patterns like "2 BHK", "3.5 BHK", "4 bed"
   - Use bhk_min and bhk_max for typical range
   - Set to null if no BHK info

5. **Supply vs Demand Counts**:
   - **Supply**: "for sale", "for rent", "available", "keys with me", "inventory"
   - **Demand**: "requirement", "looking for", "need a", "client wants", "seeking"
   - Count messages in each category:
     * supply_sale_count: supply listings for sale
     * supply_rent_count: supply listings for rent
     * demand_buy_count: demand/requirements to buy
     * demand_rent_count: demand/requirements to rent

6. **Summary**: 1-2 sentences describing agent's specialization focus

7. **Uncertainty**: Use null for any field you're unsure about (prefer null over guessing)

RESPOND WITH ONLY VALID JSON, NO EXTRA TEXT.

Agent Data:
{agent_data}

Required JSON structure:
{{
  "agent_contact": "{agent_contact}",
  "primary_locations": ["Area1", "Area2"],
  "primary_property_types": ["residential_apartment"],
  "sale_price_min": 20000000,
  "sale_price_max": 60000000,
  "rent_price_min": 60000,
  "rent_price_max": 180000,
  "bhk_min": 2,
  "bhk_max": 4,
  "supply_sale_count": 15,
  "supply_rent_count": 6,
  "demand_buy_count": 2,
  "demand_rent_count": 1,
  "summary_text": "Brief summary of agent's focus and specialization, mention any peculiarities (like price on request, etc., or high priced properties) or unique selling points"
}}"""

    @classmethod
    def _get_client(cls) -> genai.Client:
        """Get or create shared Gemini client instance (singleton)"""
        if cls._client is None:
            api_key = os.getenv("GEMINI_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")

            if not api_key:
                raise ValueError("GEMINI_AI_API_KEY or GOOGLE_API_KEY must be set in environment")

            cls._client = genai.Client(api_key=api_key)
            print("[AgentProfiling] ✓ Created shared Gemini client instance")

        return cls._client

    @classmethod
    async def profile_agent_with_llm(cls, agent_data: Dict[str, Any]) -> AgentProfileLLMOutput:
        """
        Profile a single agent using LLM analysis

        Args:
            agent_data: Dictionary with agent_contact, agent_name, company_name,
                       total_posts_last_3_months, and sample_messages

        Returns:
            AgentProfileLLMOutput with structured profile data

        Raises:
            Exception if LLM call fails or response is invalid
        """
        try:
            client = cls._get_client()

            # Build prompt with agent data
            agent_contact = agent_data.get("agent_contact", "")
            prompt = cls.PROFILING_PROMPT.format(
                agent_data=json.dumps(agent_data, indent=2),
                agent_contact=agent_contact
            )

            print(f"[AgentProfiling] Profiling agent {agent_contact} with {len(agent_data.get('sample_messages', []))} messages")

            # Call LLM
            response = client.models.generate_content(
                model=cls._model,
                contents=prompt
            )

            response_text = response.text.strip()

            # Log first 200 chars of LLM output for debugging
            print(f"[AgentProfiling] LLM response preview (first 200 chars): {response_text[:200]}")

            # Clean up markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Parse JSON response
            profile_data = json.loads(response_text)

            # Validate and create Pydantic model
            profile = AgentProfileLLMOutput(**profile_data)

            print(f"[AgentProfiling] ✓ Successfully profiled agent {agent_contact}")

            return profile

        except json.JSONDecodeError as e:
            print(f"[AgentProfiling] ✗ Failed to parse LLM JSON response: {e}")
            print(f"[AgentProfiling] Raw response: {response_text[:500]}")
            raise Exception(f"Failed to parse LLM response as JSON: {str(e)}")

        except Exception as e:
            print(f"[AgentProfiling] ✗ Error profiling agent: {e}")
            raise Exception(f"Failed to profile agent: {str(e)}")

    @classmethod
    def build_llm_input(cls, agent_row: Dict[str, Any]) -> AgentProfileLLMInput:
        """
        Build LLM input payload from grouped agent data

        Args:
            agent_row: Row from crea_top_agents_3m_msgs_grouped view

        Returns:
            AgentProfileLLMInput ready for LLM processing
        """
        # Extract raw messages from the messages array
        messages = agent_row.get("messages", [])
        sample_messages = [msg.get("raw_message", "") for msg in messages if msg.get("raw_message")]

        return AgentProfileLLMInput(
            agent_contact=agent_row.get("agent_contact", ""),
            agent_name=agent_row.get("agent_name", ""),
            company_name=agent_row.get("company_name"),
            total_posts_last_3_months=agent_row.get("total_posts", 0),
            sample_messages=sample_messages
        )

    @classmethod
    async def process_all_agents(cls, from_supabase_service, skip_completed: bool = True) -> Dict[str, Any]:
        """
        Main orchestration method: Process all top agents and generate profiles

        Args:
            from_supabase_service: SupabaseService class for database operations
            skip_completed: If True, skip agents already completed in current session (default: True)

        Returns:
            Dictionary with processing results and statistics
        """
        try:
            print("[AgentProfiling] Starting agent profiling pipeline...")

            # Step 1: Fetch agents from view
            all_agents = await from_supabase_service.get_top_agents_grouped()

            if not all_agents:
                return {
                    "success": True,
                    "profiles_processed": 0,
                    "profiles_created": 0,
                    "profiles_updated": 0,
                    "errors": [],
                    "message": "No agents found to profile"
                }

            # Start progress tracking session
            session_id = AgentProfilingProgressService.start_session(len(all_agents))

            # Filter out already completed agents if requested
            if skip_completed:
                agents = AgentProfilingProgressService.get_agents_to_process(all_agents)
            else:
                agents = all_agents

            if not agents:
                return {
                    "success": True,
                    "profiles_processed": 0,
                    "profiles_created": 0,
                    "profiles_updated": 0,
                    "errors": [],
                    "message": f"All {len(all_agents)} agents already processed in session {session_id}",
                    "session_id": session_id
                }

            profiles_processed = 0
            profiles_created = 0
            profiles_updated = 0
            errors = []

            print(f"[AgentProfiling] Found {len(agents)} agents to profile (total: {len(all_agents)})")

            # Step 2: Process each agent
            for agent_row in agents:
                try:
                    agent_contact = agent_row.get("agent_contact")

                    # Build LLM input
                    llm_input = cls.build_llm_input(agent_row)

                    # Call LLM for profiling
                    llm_output = await cls.profile_agent_with_llm(llm_input.model_dump())

                    # Prepare data for upsert
                    profile_data = {
                        "agent_contact": llm_output.agent_contact,
                        "agent_name": agent_row.get("agent_name"),
                        "company_name": agent_row.get("company_name"),
                        "sale_price_min": llm_output.sale_price_min,
                        "sale_price_max": llm_output.sale_price_max,
                        "rent_price_min": llm_output.rent_price_min,
                        "rent_price_max": llm_output.rent_price_max,
                        "bhk_min": llm_output.bhk_min,
                        "bhk_max": llm_output.bhk_max,
                        "supply_sale_count": llm_output.supply_sale_count,
                        "supply_rent_count": llm_output.supply_rent_count,
                        "demand_buy_count": llm_output.demand_buy_count,
                        "demand_rent_count": llm_output.demand_rent_count,
                        "primary_locations": llm_output.primary_locations,
                        "primary_property_types": llm_output.primary_property_types,
                        "profile_json": llm_output.model_dump(),
                        "summary_text": llm_output.summary_text,
                        "total_posts": agent_row.get("total_posts", 0),
                        "lookback_months": 3,
                        "messages_sampled": len(llm_input.sample_messages)
                    }

                    # Check if profile already exists
                    existing_profile = await from_supabase_service.get_agent_profile(agent_contact)

                    # Upsert to database
                    result = await from_supabase_service.upsert_agent_profile(profile_data)

                    if result.get("success"):
                        profiles_processed += 1
                        if existing_profile:
                            profiles_updated += 1
                        else:
                            profiles_created += 1

                        # Mark as completed in progress tracker
                        AgentProfilingProgressService.mark_completed(agent_contact)
                    else:
                        error_msg = result.get('message', 'Unknown error')
                        errors.append(f"{agent_contact}: {error_msg}")
                        AgentProfilingProgressService.mark_failed(agent_contact, error_msg)

                except Exception as e:
                    error_msg = f"{agent_row.get('agent_contact', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    print(f"[AgentProfiling] ✗ Error processing agent: {error_msg}")

                    # Mark as failed in progress tracker
                    agent_contact = agent_row.get('agent_contact', 'unknown')
                    AgentProfilingProgressService.mark_failed(agent_contact, str(e))

            success_rate = (profiles_processed / len(agents) * 100) if agents else 0

            print(f"[AgentProfiling] ✓ Completed: {profiles_processed}/{len(agents)} agents ({success_rate:.1f}%)")
            print(f"[AgentProfiling]   Created: {profiles_created}, Updated: {profiles_updated}, Errors: {len(errors)}")

            # Get final progress summary
            progress_summary = AgentProfilingProgressService.get_progress_summary()

            return {
                "success": True,
                "profiles_processed": profiles_processed,
                "profiles_created": profiles_created,
                "profiles_updated": profiles_updated,
                "total_agents": len(all_agents),
                "agents_in_batch": len(agents),
                "success_rate": f"{success_rate:.1f}%",
                "errors": errors,
                "message": f"Processed {profiles_processed} out of {len(agents)} agents",
                "session_id": session_id,
                "progress_summary": progress_summary
            }

        except Exception as e:
            print(f"[AgentProfiling] ✗ Pipeline error: {e}")
            return {
                "success": False,
                "profiles_processed": 0,
                "profiles_created": 0,
                "profiles_updated": 0,
                "errors": [str(e)],
                "message": f"Pipeline failed: {str(e)}"
            }

    @classmethod
    async def process_single_agent(cls, agent_contact: str, from_supabase_service) -> Dict[str, Any]:
        """
        Process a single agent by contact number

        Args:
            agent_contact: Agent phone number to profile
            from_supabase_service: SupabaseService class for database operations

        Returns:
            Dictionary with processing result
        """
        try:
            print(f"[AgentProfiling] Processing single agent: {agent_contact}")

            # Fetch all agents and find the specific one
            agents = await from_supabase_service.get_top_agents_grouped()
            agent_row = next((a for a in agents if a.get("agent_contact") == agent_contact), None)

            if not agent_row:
                return {
                    "success": False,
                    "message": f"Agent {agent_contact} not found in top agents view",
                    "data": None
                }

            # Build LLM input
            llm_input = cls.build_llm_input(agent_row)

            # Call LLM for profiling
            llm_output = await cls.profile_agent_with_llm(llm_input.model_dump())

            # Prepare data for upsert
            profile_data = {
                "agent_contact": llm_output.agent_contact,
                "agent_name": agent_row.get("agent_name"),
                "company_name": agent_row.get("company_name"),
                "sale_price_min": llm_output.sale_price_min,
                "sale_price_max": llm_output.sale_price_max,
                "rent_price_min": llm_output.rent_price_min,
                "rent_price_max": llm_output.rent_price_max,
                "bhk_min": llm_output.bhk_min,
                "bhk_max": llm_output.bhk_max,
                "supply_sale_count": llm_output.supply_sale_count,
                "supply_rent_count": llm_output.supply_rent_count,
                "demand_buy_count": llm_output.demand_buy_count,
                "demand_rent_count": llm_output.demand_rent_count,
                "primary_locations": llm_output.primary_locations,
                "primary_property_types": llm_output.primary_property_types,
                "profile_json": llm_output.model_dump(),
                "summary_text": llm_output.summary_text,
                "total_posts": agent_row.get("total_posts", 0),
                "lookback_months": 3,
                "messages_sampled": len(llm_input.sample_messages)
            }

            # Upsert to database
            result = await from_supabase_service.upsert_agent_profile(profile_data)

            if result.get("success"):
                print(f"[AgentProfiling] ✓ Successfully profiled agent {agent_contact}")
                return {
                    "success": True,
                    "message": f"Successfully profiled agent {agent_contact}",
                    "data": result.get("data")
                }
            else:
                return {
                    "success": False,
                    "message": result.get("message"),
                    "data": None
                }

        except Exception as e:
            print(f"[AgentProfiling] ✗ Error processing agent {agent_contact}: {e}")
            return {
                "success": False,
                "message": f"Error processing agent: {str(e)}",
                "data": None
            }
