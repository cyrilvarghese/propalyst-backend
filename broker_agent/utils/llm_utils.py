"""LLM response utilities for cleaning and processing responses."""

import re


def clean_llm_response(response_text: str, format_type: str = "json") -> str:
    """
    Clean LLM response by removing markdown code blocks.

    LLMs often wrap JSON, text, and other structured responses in markdown
    code blocks (```json ... ```). This utility removes those wrappers to
    extract the clean content.

    Args:
        response_text (str): Raw response from LLM API
        format_type (str): Type of content ('json', 'text', 'markdown', etc.)
                          Used for documentation; function handles all types

    Returns:
        str: Cleaned response text without markdown wrappers

    Examples:
        >>> clean_llm_response('```json\\n{"answer": "buy"}\\n```')
        '{"answer": "buy"}'

        >>> clean_llm_response('```\\nSome text here\\n```', 'text')
        'Some text here'

        >>> clean_llm_response('Plain text without blocks')
        'Plain text without blocks'
    """
    text = response_text.strip()

    # Check if response is wrapped in markdown code blocks
    if text.startswith("```"):
        # Remove opening backticks and optional language identifier
        # Matches: ``` or ```json or ```text or ```markdown, etc.
        text = re.sub(r'^```(?:json|text|markdown|python)?\n?', '', text)

        # Remove closing backticks
        text = re.sub(r'\n?```$', '', text)

        # Clean up any extra whitespace
        text = text.strip()

    return text


__all__ = ["clean_llm_response"]
