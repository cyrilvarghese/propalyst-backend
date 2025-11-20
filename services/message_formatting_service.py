"""
Message Formatting Service
==========================

Formats raw property listing messages into friendly WhatsApp broker outreach messages
using Google Gemini LLM.
"""

import os
from typing import Optional
from google import genai
from dotenv import load_dotenv

load_dotenv()


class MessageFormattingService:
    """Service for formatting property messages using Gemini LLM"""

    # Shared Gemini client instance (singleton pattern)
    _client: Optional[genai.Client] = None
    _model: str = "gemini-2.0-flash-exp"

    @classmethod
    def _get_client(cls) -> genai.Client:
        """Get or create shared Gemini client instance (singleton)"""
        if cls._client is None:
            # Try both possible environment variable names
            api_key = os.getenv("GEMINI_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")

            if not api_key:
                raise ValueError("GEMINI_AI_API_KEY or GOOGLE_API_KEY must be set in environment")

            cls._client = genai.Client(api_key=api_key)
            print("[MessageFormatting] ✓ Created shared Gemini client instance")

        return cls._client

    @classmethod
    async def format_message(
        cls,
        raw_message: str,
        agent_name: str = "Naresh",
        tone: str = "professional_friendly",
        include_emojis: bool = True
    ) -> str:
        """
        Format a raw property listing into a friendly WhatsApp broker outreach message

        Args:
            raw_message: Raw WhatsApp property listing message
            tone: Tone of the message (professional_friendly, casual, formal)
            include_emojis: Whether to include emojis in formatted message

        Returns:
            Formatted WhatsApp message optimized for broker outreach
        """
        try:
            client = cls._get_client()

            # Build prompt based on tone and emoji preference
            emoji_instruction = "Use relevant emojis (👋🏢💰✨📞) to make it friendly" if include_emojis else "Do not use emojis"

            tone_map = {
                "professional_friendly": "professional yet warm and approachable",
                "casual": "casual and conversational",
                "formal": "formal and business-like"
            }
            tone_description = tone_map.get(tone, "professional yet warm and approachable")

            prompt = f"""You are drafting a WhatsApp message for Naresh, a broker from Real Broker. He has a CLIENT who is interested in the property listing shown below.

CONTEXT:
- Naresh is reaching OUT to the broker who posted this listing
- The broker's name is: {agent_name}
- He wants to express interest on behalf of his client
- Goal: Request more details or schedule a viewing

REQUIREMENTS:
- Keep it VERY SHORT (under 100 words)
- Start with "Hi {agent_name}!" to address the broker
- {emoji_instruction}
- Tone: {tone_description}
- Format for WhatsApp (short and direct)

TEMPLATE STRUCTURE:
[Greeting with broker's name: "Hi {agent_name}!"]
[Express interest in their property - reference 2-3 key details from listing]
[Mention having a matching client]
[Request next steps - viewing/details]
[Signature: Naresh, Real Broker]

EXAMPLE OUTPUT:
```
Hi {agent_name}! 👋

I came across your 4 BHK apartment listing in Brunton Road, MG Road cross. The property looks like a great fit for one of my clients!

They're specifically looking for:
✅ Semi-furnished 4 BHK in that area
✅ Budget around ₹1.5L/month
✅ Parking for 2 cars

Could we schedule a viewing? I'd love to discuss this further.

Thanks!
Naresh
Real Broker
```

BROKER'S PROPERTY LISTING:
{raw_message}

OUTPUT (your interest message to the broker):"""

            print(f"[MessageFormatting] Formatting message with tone: {tone}, emojis: {include_emojis}")

            # Generate formatted message
            response = client.models.generate_content(
                model=cls._model,
                contents=prompt
            )

            formatted_message = response.text.strip()

            # Clean up any markdown code blocks if present
            if formatted_message.startswith("```"):
                # Remove code block markers
                formatted_message = formatted_message.split("```")[1]
                if formatted_message.startswith("\n"):
                    formatted_message = formatted_message[1:]

            print(f"[MessageFormatting] ✓ Message formatted successfully ({len(formatted_message)} chars)")

            return formatted_message

        except Exception as e:
            print(f"[MessageFormatting] ✗ Error formatting message: {e}")
            raise Exception(f"Failed to format message: {str(e)}")
