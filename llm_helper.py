import os
import json
from typing import Optional

import httpx

try:
    from secrets_store import get_api_key as get_stored_api_key
except Exception:
    get_stored_api_key = None


def call_llm_extract(text: str, api_key: str = None, api_url: str = None, model: str = 'gpt-4o-mini', mode: str = 'strict') -> Optional[list]:
    """
    Call an OpenAI-compatible chat completion endpoint (or Grok-like) to extract resume fields.

    Expects the model to return a JSON array of objects matching the exact field names and rules.
    The caller must provide `GROK_API_KEY` in env or pass api_key, and may override `GROK_API_URL`.
    """
    if not api_key:
        # prefer server-side stored key when available
        try:
            if get_stored_api_key:
                api_key = get_stored_api_key()
        except Exception:
            api_key = None
    if not api_key:
        api_key = os.getenv('GROK_API_KEY')
    if not api_key:
        return None

    api_url = api_url or os.getenv('GROK_API_URL') or 'https://api.openai.com/v1/chat/completions'

    if mode == 'human':
        system = (
            "You are a careful resume reader extracting candidate information. Extract ONLY information actually present in the resume. "
            "Be thorough but accurate - look carefully through the entire document for all required fields. "
            "For each field return either null or an object {\"value\": <string or number>, \"confidence\": <0.0-1.0>, \"source_excerpt\": <short text span from the resume>}.\n"
            "Extraction Guidelines:\n"
            "- full_name: Extract the candidate's complete name (usually at the top of resume)\n"
            "- email: Find the email address (usually in contact section)\n"
            "- phone_number: Primary phone number, normalize to digits only (remove formatting)\n"
            "- alternate_phone_number: Secondary phone if present, otherwise null\n"
            "- highest_qualification: Highest degree completed (PhD, Masters, Bachelors, Diploma). Return degree type, not institution name.\n"
            "- years_of_experience: Total years of work experience as a number. Sum if multiple roles given. Only numeric or null.\n"
            "- current_company: Company name from the MOST RECENT job position\n"
            "- current_designation: Job title from the MOST RECENT job position\n"
            "- city: City of residence/current location\n"
            "- state: State/region of residence/current location\n"
            "Return JSON array with objects containing exactly these keys. Include no extra keys or explanation; respond with JSON only."
        )
    else:
        system = (
            "You are a strict data extraction agent. Extract ONLY fields explicitly present in the resume text.\n"
            "CRITICAL RULES:\n"
            "1. Do NOT guess, infer, or hallucinate. If a field is missing or ambiguous, return null.\n"
            "2. Confidence must be 0.8 or higher for acceptance. If unsure, use lower confidence or null.\n"
            "3. For years_of_experience: MUST be numeric ONLY (e.g., 5, 5.5) or null. Never text.\n"
            "4. For highest_qualification: Return ONLY the highest COMPLETED degree type (PhD, Masters, Bachelors, Diploma, etc.), not the institution.\n"
            "5. For current_company and current_designation: Must come from the MOST RECENT job role only.\n"
            "6. For phone_number: Normalize to digits only (no formatting)\n"
            "7. Look for 'Present' or current year to identify current job role\n\n"
            "Return a JSON array where each element is an object with these exact keys: "
            "full_name, email, phone_number, alternate_phone_number, highest_qualification, years_of_experience, current_company, current_designation, city, state.\n"
            "For each key, provide either null or an object: {\"value\": <value>, \"confidence\": <0.0-1.0>}.\n"
            "Example: {\"full_name\": {\"value\": \"John Doe\", \"confidence\": 0.95}, \"email\": null, \"years_of_experience\": {\"value\": 5, \"confidence\": 0.9}, ...}.\n"
            "Do NOT include any extra keys or explanatory text. Respond with the JSON array only."
        )

    user = (
        "Here is the resume text delimited by triple backticks. Extract fields per the strict rules. "
        "Resume text:\n```\n" + text + "\n```"
    )

    # Build request payload for OpenAI Chat Completions API
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.0,
        "max_tokens": 1500,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(api_url, headers=headers, json=payload)
            r.raise_for_status()
            j = r.json()
            # Attempt to retrieve assistant content
            if 'choices' in j and len(j['choices']) > 0:
                content = j['choices'][0].get('message', {}).get('content') or j['choices'][0].get('text')
            else:
                content = j.get('text')
            if not content:
                return None
            # The model should return a JSON array where each field is either null or {"value":..., "confidence":...}
            content = content.strip()
            # strip possible code fences
            if content.startswith('```'):
                parts = content.split('```')
                if len(parts) >= 2:
                    content = parts[1].strip()
            parsed = json.loads(content)
            # normalize structure: ensure array of objects
            if isinstance(parsed, dict):
                return [parsed]
            return parsed
    except Exception:
        return None
