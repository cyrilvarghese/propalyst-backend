"""
LLM-Based Why Decision Tool
===========================

Uses Gemini LLM to intelligently decide whether a "why" follow-up question
makes sense based on the micro-interaction guidelines.

This tool complements the keyword-based approach in graph.py with more nuanced
decision-making using LLM analysis.
"""

import os
import json
from typing import Tuple, Optional, Dict, Any
from pathlib import Path
from google import genai
from dotenv import load_dotenv

load_dotenv()


class WhyDecisionLLM:
    """LLM-based tool for evaluating whether to ask 'why' follow-up questions"""

    # Shared Gemini client instance (singleton pattern)
    _client: Optional[genai.Client] = None
    _model: str = "gemini-2.5-flash"
    _prompt_cache: Optional[str] = None

    # Path to prompt template
    PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "why_decision_evaluation.txt"

    @classmethod
    def _get_client(cls) -> genai.Client:
        """Get or create shared Gemini client instance (singleton)"""
        if cls._client is None:
            api_key = os.getenv("GEMINI_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")

            if not api_key:
                raise ValueError("GEMINI_AI_API_KEY or GOOGLE_API_KEY must be set in environment")

            cls._client = genai.Client(api_key=api_key)

        return cls._client

    @classmethod
    def _load_prompt(cls) -> str:
        """Load prompt from file (with caching)"""
        if cls._prompt_cache is None:
            try:
                with open(cls.PROMPT_FILE, "r") as f:
                    cls._prompt_cache = f.read()
            except FileNotFoundError:
                raise FileNotFoundError(f"Prompt file not found: {cls.PROMPT_FILE}")

        return cls._prompt_cache

    @classmethod
    async def should_ask_why_llm(
        cls,
        question_id: str,
        question_label: str,
        user_answer: str,
    ) -> Tuple[bool, str, str, float]:
        """
        Use LLM to intelligently decide whether to ask a "why" follow-up question.

        Based on micro-interaction guidelines:
        "A why is needed when the answer could reasonably lead to multiple
        materially different paths forward."

        Args:
            question_id (str): Which question was answered (e.g., "proximity_location", "budget")
            question_label (str): Human-readable label (e.g., "Location", "Price Range")
            user_answer (str): The user's answer text

        Returns:
            Tuple[bool, str, str, float]: (should_ask_why, reason, why_question, confidence)
                - should_ask_why: Whether to ask a why question
                - reason: Explanation of the decision
                - why_question: The generated "why" question to ask (empty if ask_why=false)
                - confidence: Confidence level (0.0-1.0)

        Raises:
            Exception if LLM call fails or response is invalid
        """

        try:
            client = cls._get_client()
            prompt_template = cls._load_prompt()

            # Build prompt with context
            prompt = prompt_template.format(
                question_id=question_id,
                question_label=question_label,
                user_answer=user_answer,
            )

            # Call LLM with low temperature for consistent decisions
            response = client.models.generate_content(
                model=cls._model,
                contents=prompt,
                config={"temperature": 0.3},  # Low temperature for consistency
            )

            response_text = response.text.strip()

            # Clean up markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Parse JSON response
            decision_data = json.loads(response_text)

            # Extract decision components
            ask_why = decision_data.get("ask_why", False)
            reason = decision_data.get("reason", "")
            why_question = decision_data.get("why_question", "")
            confidence = float(decision_data.get("confidence", 0.5))

            # Ensure valid values
            ask_why = bool(ask_why)
            why_question = str(why_question) if why_question else ""
            confidence = max(0.0, min(1.0, confidence))  # Clamp to 0.0-1.0

            return ask_why, reason, why_question, confidence

        except json.JSONDecodeError as e:
            print(f"[WhyDecisionLLM] ✗ Failed to parse LLM JSON response: {e}")
            print(f"[WhyDecisionLLM] Raw response: {response_text[:500]}")
            raise Exception(f"Failed to parse LLM response as JSON: {str(e)}")

        except Exception as e:
            print(f"[WhyDecisionLLM] ✗ Error evaluating why decision: {e}")
            raise Exception(f"Failed to evaluate why decision: {str(e)}")


async def should_ask_why_llm(
    question_id: str,
    question_label: str,
    user_answer: str,
) -> Tuple[bool, str, str, float]:
    """
    Use LLM to intelligently decide whether to ask a "why" follow-up question.

    Wrapper function around WhyDecisionLLM class method for cleaner imports.

    Args:
        question_id (str): Which question was answered (e.g., "proximity_location")
        question_label (str): Human-readable label (e.g., "Location")
        user_answer (str): The user's answer text

    Returns:
        Tuple[bool, str, str, float]: (should_ask_why, reason, why_question, confidence)

    Example:
        >>> ask_why, reason, why_q, confidence = await should_ask_why_llm(
        ...     question_id="proximity_location",
        ...     question_label="Location",
        ...     user_answer="Indiranagar"
        ... )
        >>> print(ask_why, reason, why_q, confidence)
        True "Location name alone doesn't explain intent..." "What draws you to Indiranagar?" 0.85
    """
    return await WhyDecisionLLM.should_ask_why_llm(question_id, question_label, user_answer)


__all__ = ["should_ask_why_llm", "WhyDecisionLLM"]
