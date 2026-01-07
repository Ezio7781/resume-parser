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
            "You are a resume data extraction expert. Extract ONLY fields explicitly visible in the provided resume text.\n"
            "Return JSON array with one object containing all 10 fields.\n\n"
            "EXTRACTION RULES:\n\n"
            "full_name:\n"
            "  - The candidate's personal name (first + last, possibly middle)\n"
            "  - ALWAYS at the very top of the resume in contact section\n"
            "  - NEVER a company name, school name, institution, certification, or skill\n"
            "  - 2-4 capitalized words that form a person's name\n"
            "  - If you see 'University', 'Corporation', 'Inc', 'LLC' - that's NOT a name\n"
            "  - Example: Extract 'John Smith', NOT 'Stanford University'\n\n"
            "email:\n"
            "  - Valid email address in contact info (top of resume)\n"
            "  - Format: something@domain.ext\n\n"
            "phone_number:\n"
            "  - Primary phone, digits only, no formatting, no country code\n"
            "  - Must have 10+ digits to be valid\n\n"
            "alternate_phone_number:\n"
            "  - Secondary phone if listed, null otherwise\n\n"
            "highest_qualification:\n"
            "  - ONLY from Education section\n"
            "  - RETURN ONLY DEGREE TYPE: 'PhD', 'Masters', 'Bachelors', 'Diploma', 'Associate', or 'High School'\n"
            "  - NEVER return institution name, school, or full text like 'Masters in Computer Science'\n"
            "  - If multiple degrees: PhD (rank 6) > Masters (5) > Bachelors (4) > Diploma (2) > Associate (3) > High School (1)\n"
            "  - Return the HIGHEST ranked degree only\n"
            "  - Example: If 'Bachelors in Science from MIT' and 'Masters in Engineering', return 'Masters'\n\n"
            "years_of_experience:\n"
            "  - Total work experience years as NUMBER ONLY (5, 5.5, 10)\n"
            "  - Sum all jobs if multiple listed with date ranges\n"
            "  - NEVER include school/education years\n"
            "  - Format: numeric value only, no text like '5 years'\n\n"
            "current_company:\n"
            "  - Company name of the MOST RECENT job (marked 'Present', current year, or latest in list)\n"
            "  - NEVER include job title, location, or 'Technologies: Python, Java'\n"
            "  - Just the company name: 'Google', 'Microsoft', 'Acme Corp'\n\n"
            "current_designation:\n"
            "  - Job title of the MOST RECENT role only\n"
            "  - Must match the company from current_company field\n"
            "  - NEVER include company name, location, or responsibilities\n"
            "  - Examples: 'Senior Software Engineer', 'Product Manager', 'Data Scientist'\n\n"
            "city:\n"
            "  - City of residence (check location/address section)\n"
            "  - NOT company office location unless that's only location given\n\n"
            "state:\n"
            "  - State/region of residence\n\n"
            "CONFIDENCE & RETURN FORMAT:\n"
            "- Each field: null OR {\"value\": <value>, \"confidence\": <0.0-1.0>}\n"
            "- Confidence < 0.8: use null instead\n"
            "- Return JSON array ONLY with no explanation text\n"
            "- Example: [{\"full_name\": {\"value\": \"John Smith\", \"confidence\": 0.95}, \"email\": {\"value\": \"john@example.com\", \"confidence\": 0.99}, ...}]"
        )
    else:
        system = (
            "You are a strict resume parsing agent. Extract ONLY fields explicitly present in resume text.\n"
            "Return a JSON array with one object containing all 10 required fields.\n\n"
            "STRICT EXTRACTION RULES:\n\n"
            "full_name:\n"
            "  - Candidate's personal name (first + last, possibly middle)\n"
            "  - MUST be at the very top of resume in contact info\n"
            "  - KEYWORD BLOCKLIST: If text contains 'University', 'School', 'College', 'Inc', 'Corp', 'LLC', 'Ltd', 'Technologies', 'Institute', 'Academy' - it's NOT a name\n"
            "  - MUST be 2-4 words that look like a person's name\n"
            "  - High confidence (0.95+): clear personal name at top\n"
            "  - Low confidence or null: ambiguous or mixed with other content\n\n"
            "email:\n"
            "  - Standard email format: something@domain.extension\n"
            "  - Located in contact section\n"
            "  - High confidence (0.95+): valid format found in contact info\n\n"
            "phone_number:\n"
            "  - Digits only, no formatting (e.g., '5551234567' not '(555) 123-4567')\n"
            "  - No country codes or + prefix\n"
            "  - MUST be 10+ digits to be high confidence\n"
            "  - Low confidence or null: less than 10 digits or invalid format\n\n"
            "alternate_phone_number:\n"
            "  - Same format rules as phone_number\n"
            "  - Only if a second phone is explicitly listed\n"
            "  - null if not present\n\n"
            "highest_qualification:\n"
            "  - ONLY from Education/Academic section (MANDATORY)\n"
            "  - RETURN ONLY degree type: 'PhD', 'Masters', 'Bachelors', 'Diploma', 'Associate', 'High School'\n"
            "  - NEVER include institution name, school name, or subject (e.g., return 'Masters' NOT 'Masters of Computer Science from Stanford')\n"
            "  - Ranking system: PhD (6) > Masters (5) > Bachelors (4) > Diploma (2) > Associate (3) > High School (1)\n"
            "  - If multiple degrees: return the ONE with highest rank\n"
            "  - High confidence: clear degree in Education section\n"
            "  - null: if Education section not found or degree unclear\n\n"
            "years_of_experience:\n"
            "  - NUMERIC VALUE ONLY (5, 5.5, 10, 15) - NO TEXT\n"
            "  - From Experience section: sum all work experience years\n"
            "  - EXCLUDE education/school years, internships marked as 'internship'\n"
            "  - If date ranges given: calculate years between dates\n"
            "  - High confidence: multiple dated roles that clearly sum\n"
            "  - null: if no work history found or dates unclear\n\n"
            "current_company:\n"
            "  - Company name from MOST RECENT job only\n"
            "  - Identify as: has 'Present' label OR shows current year (2024-2025) OR is first/top entry\n"
            "  - Return ONLY company name: 'Google', 'Microsoft', 'IBM' (NOT 'Senior Engineer at Google')\n"
            "  - High confidence: 'Present' clearly marked\n"
            "  - null: if current role not identifiable\n\n"
            "current_designation:\n"
            "  - Job title from MOST RECENT role ONLY (same role as current_company)\n"
            "  - Return title only: 'Senior Software Engineer', 'Product Manager' (NOT company name or location)\n"
            "  - High confidence: clear job title in most recent role\n"
            "  - null: if current role or title unclear\n\n"
            "city:\n"
            "  - City name from residence/location info section\n"
            "  - NOT workplace or office location (unless no residence given)\n"
            "  - Plain city name only: 'New York', 'San Francisco'\n\n"
            "state:\n"
            "  - State or region from residence/location section\n"
            "  - Match with city field\n"
            "  - Plain state name or abbreviation\n\n"
            "RETURN FORMAT (MANDATORY):\n"
            "- JSON array with one object\n"
            "- Each field key: null OR {\"value\": <value>, \"confidence\": <0.0-1.0>}\n"
            "- Confidence < 0.8: always return null\n"
            "- NO explanations, NO extra keys, JSON ONLY\n"
            "- Example: [{\"full_name\": {\"value\": \"Jane Doe\", \"confidence\": 0.95}, \"email\": {\"value\": \"jane@example.com\", \"confidence\": 0.99}, ..., \"state\": null}]"
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
