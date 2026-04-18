import os
import httpx

# Removed global API key check, it's now checked per request in summarize_content

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL   = "anthropic/claude-sonnet-4.5"

# SYSTEM_PROMPT = """You are a competitive intelligence analyst. Be factual, dense, and neutral.
# State "Not found" for missing data. No filler — every sentence must add information."""

# INSTRUCTIONS = """Produce a structured intelligence report on the website and entity behind it.
#
# 1. EXECUTIVE SUMMARY
# 3–4 paragraphs: what it does, who it serves, its scale/maturity, what makes it distinctive, and any red flags or inconsistencies.
#
# 2. COMPANY PROFILE
# Legal name, trading name, aliases · Address and country · Registration/VAT/CoC numbers · Founded (or inferred age) · Headcount/office count · Leadership names and titles · Contact details and social handles
#
# 3. PRODUCTS & SERVICES
# For each offering: name, description, target segment, pricing model, specific prices if listed, key features, and any limitations or fair-use caveats.
#
# 4. MARKET POSITIONING
# B2B/B2C/B2G · Industry verticals · Geographic and language scope · Tone (formal/casual/technical) · Market tier: budget, mid-market, or premium
#
# 5. TECHNOLOGY & INFRASTRUCTURE
# Stack clues, integrations, third-party partnerships, APIs/SDKs, security and compliance claims (GDPR, ISO, SOC2, etc.)
#
# 6. CONTENT & SEO
# Topic clusters and target keywords · Content types present (blog, docs, case studies, etc.) · Freshness signals · Gated content or lead-gen mechanisms
#
# 7. TRUST & CREDIBILITY
# Named clients, logos, case studies · Testimonials or review scores · Awards, press, certifications · Guarantees, SLAs, refund policies
#
# 8. KEY FACTS TABLE
# | Field | Value |
# |---|---|
# | Legal name | |
# | Address | |
# | Founded | |
# | Headcount | |
# | Pricing from | |
# | Primary language | |
# | GDPR compliant | |
#
# 9. GAPS & CAVEATS
# What's missing, vague, evasive, or outdated? What needs a follow-up source to verify?
#
# 10. ANALYST CONCLUSIONS
# 2–3 paragraphs: entity type, credibility assessment, and the single most important takeaway."""

SYSTEM_PROMPT = """You are a competitive intelligence analyst. Be factual, dense, and neutral.
Write in tight prose paragraphs — no bullet points, no filler. Every sentence must add information.
Omit any field or section where data was genuinely not found rather than writing "Not found"."""

INSTRUCTIONS = """Produce a structured intelligence report on the entity behind this website.
Use the section headers below. Only include a section if you found relevant data for it.

EXECUTIVE SUMMARY
What the entity does, who it serves, its scale and maturity, what makes it distinctive, and any red flags or inconsistencies.

COMPANY PROFILE
Legal name, trading name, aliases, address, country, registration/VAT/CoC numbers, founding date or inferred age, headcount, office count, leadership names and titles, contact details, and social handles.

PRODUCTS & SERVICES
For each offering: name, description, target segment, pricing model, specific prices, key features, and any limitations or fair-use caveats.

MARKET POSITIONING
B2B/B2C/B2G classification, industry verticals, geographic and language scope, tone, and market tier (budget, mid-market, or premium).

TECHNOLOGY & INFRASTRUCTURE
Stack clues, integrations, third-party partnerships, APIs or SDKs, and security or compliance claims (GDPR, ISO, SOC2, etc.).

TRUST & CREDIBILITY
Named clients, logos, case studies, testimonials, review scores, awards, press mentions, certifications, guarantees, SLAs, and refund policies.

KEY FACTS
Present as a two-column table of every concrete data point found (names, numbers, dates, URLs).

GAPS & OPEN QUESTIONS
What is missing, vague, or evasive, and what would need a follow-up source to verify.

ANALYST CONCLUSIONS
Entity type, credibility assessment, and the single most important takeaway."""


async def summarize_content(
    content: str,
    title: str,
    model: str = DEFAULT_MODEL,
    instructions: str | None = None,
) -> str:
    """
    Call OpenRouter with the scraped content and return a markdown intelligence report.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")

    if not api_key or len(api_key.strip()) < 10:
        raise Exception(f"OPENROUTER_API_KEY is missing or too short (length: {len(api_key) if api_key else 0}). Please set it in your environment variables.")

    if instructions is None:
        instructions = INSTRUCTIONS
    
    user_message = f"{instructions}\n\n---\n\nPage title: {title}\n\n{content}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        "max_tokens": 4096,
        "temperature": 0.3,
        "top_p": 1,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://url-summarizer.app",
        "X-Title":       "URL Summarizer",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
        except httpx.ReadTimeout:
            print("OpenRouter Error: LLM request timed out (120s limit).")
            raise Exception("LLM request timed out (120s limit).")
        except Exception as e:
            print(f"OpenRouter Error: {e}")
            raise e

        if response.status_code != 200:
            print(f"OpenRouter Error: {response.status_code} - {response.text}")
            response.raise_for_status()

        data = response.json()

    return data["choices"][0]["message"]["content"].strip()