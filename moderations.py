import os
import json
import logging
import re
from typing import Dict

import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)


def _strip_markdown(text: str) -> str:
    """
    Removes markdown code blocks and trims whitespace.
    Handles ```json ... ``` and ``` ... ```
    """
    if not text:
        return text

    # Remove fenced code blocks
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")

    return text.strip()


def check_message(message_content: str) -> Dict:
    """
    Classifies a message using Gemini moderation.

    Returns:
    {
        is_allowed: bool,
        category: str,
        confidence: float (0-1),
        reason: str
    }

    Fail-open: if Gemini API fails, message is allowed.
    """
    # Default fail-open response
    fail_open_response = {
        "is_allowed": True,
        "category": "unknown",
        "confidence": 0.0,
        "reason": "Moderation service unavailable, allowing message"
    }

    if not GEMINI_API_KEY:
        logging.warning("GEMINI_API_KEY not configured")
        return fail_open_response

    prompt = f"""
You are a content moderation system.

Classify the following message into ONE of these categories:
- clean
- toxic
- spam
- harassment

Return ONLY valid JSON in this exact format:
{{
  "category": "<clean|toxic|spam|harassment>",
  "confidence": <number between 0 and 1>,
  "reason": "<short explanation>"
}}

Message:
"{message_content}"
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=5
        )
        response.raise_for_status()

        data = response.json()

        # Gemini text extraction
        text_response = (
            data["candidates"][0]["content"]["parts"][0]["text"]
        )

        cleaned = _strip_markdown(text_response)

        parsed = json.loads(cleaned)

        category = parsed.get("category", "unknown")
        confidence = float(parsed.get("confidence", 0.0))
        reason = parsed.get("reason", "")

        is_allowed = category == "clean"

        return {
            "is_allowed": is_allowed,
            "category": category,
            "confidence": max(0.0, min(confidence, 1.0)),
            "reason": reason
        }

    except Exception as e:
        logging.warning(f"Gemini moderation failed: {e}")
        return fail_open_response
