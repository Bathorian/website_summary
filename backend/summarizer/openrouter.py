import os
import httpx

# Removed global API key check, it's now checked per request in summarize_content

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "anthropic/claude-sonnet-4.5"

SYSTEM_PROMPT = """You are a competitive intelligence analyst.
Produce a factual, neutral report grounded only in the provided page content.
Do not use external knowledge. Do not guess missing facts.

Rules:
- Every claim must be supported by evidence from the provided text.
- If a claim is inferred (not explicitly stated), label it as "Inference" with lower confidence.
- Never fabricate names, numbers, dates, legal identifiers, customers, certifications, or prices.
- Do not output placeholders like "Not found", "N/A", or empty templates.
- Keep writing concise, information-dense, and non-promotional."""

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
        raise Exception(
            f"OPENROUTER_API_KEY is missing or too short (length: {len(api_key) if api_key else 0}). Please set it in your environment variables.")

    if instructions is None:
        instructions = INSTRUCTIONS

    user_message = f"{instructions}\n\n---\n\nPage title: {title}\n\n{content}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 4096,
        "temperature": 0.3,
        "top_p": 1,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://url-summarizer.app",
        "X-Title": "URL Summarizer",
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
