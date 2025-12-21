#!/usr/bin/env python3
"""
Simple test for response cleaning utility - no dependencies.

Tests the clean_llm_response function directly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from broker_agent.utils.llm_utils import clean_llm_response


def test_response_cleaning():
    """Test response cleaning utility with various markdown formats."""
    print("\n" + "=" * 60)
    print("Testing Response Cleaning Utility")
    print("=" * 60)

    test_cases = [
        {
            "input": '```json\n{"answer": "buy", "question_id": "req_type", "confidence": 0.95}\n```',
            "expected": '{"answer": "buy", "question_id": "req_type", "confidence": 0.95}',
            "description": "JSON with markdown wrapper"
        },
        {
            "input": '```json\n{\n  "answer": "buy",\n  "question_id": "req_type"\n}\n```',
            "expected": '{\n  "answer": "buy",\n  "question_id": "req_type"\n}',
            "description": "Multiline JSON with markdown wrapper"
        },
        {
            "input": '```\nHello world, this is a test\n```',
            "expected": 'Hello world, this is a test',
            "description": "Plain text with markdown wrapper"
        },
        {
            "input": '```text\nGenerated acknowledgment text\n```',
            "expected": 'Generated acknowledgment text',
            "description": "Text with markdown wrapper"
        },
        {
            "input": '```python\nprint("hello")\nprint("world")\n```',
            "expected": 'print("hello")\nprint("world")',
            "description": "Python code with markdown wrapper"
        },
        {
            "input": '```markdown\n# Heading\nSome text\n```',
            "expected": '# Heading\nSome text',
            "description": "Markdown with markdown wrapper"
        },
        {
            "input": '{"answer": "buy", "confidence": 0.9}',
            "expected": '{"answer": "buy", "confidence": 0.9}',
            "description": "JSON without markdown wrapper"
        },
        {
            "input": 'Plain text without markup',
            "expected": 'Plain text without markup',
            "description": "Plain text without wrapper"
        },
        {
            "input": '```\n```',
            "expected": '',
            "description": "Empty markdown block"
        },
        {
            "input": '   ```json\n{"test": true}\n```   ',
            "expected": '{"test": true}',
            "description": "Markdown with surrounding whitespace"
        },
    ]

    passed = 0
    failed = 0

    for i, test_case in enumerate(test_cases, 1):
        result = clean_llm_response(test_case["input"])
        success = result == test_case["expected"]

        if success:
            print(f"\n✓ Test {i}: {test_case['description']}")
            passed += 1
        else:
            print(f"\n✗ Test {i}: {test_case['description']}")
            print(f"  Input:    {repr(test_case['input'][:80])}")
            print(f"  Expected: {repr(test_case['expected'][:80])}")
            print(f"  Got:      {repr(result[:80])}")
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 60)

    if failed == 0:
        print("\n✨ All response cleaning tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(test_response_cleaning())
