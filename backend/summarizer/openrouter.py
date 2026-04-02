import os
import httpx

# Removed global API key check, it's now checked per request in summarize_content

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL   = "anthropic/claude-sonnet-4.5"

SYSTEM_PROMPT = """You are a senior research analyst specializing in competitive intelligence and business analysis.
Be factual, neutral, and thorough. Do not pad with filler — every sentence must add information.
If data for a section is not available, explicitly state "Not found" rather than skipping it."""

INSTRUCTIONS = """Your task is to produce an exhaustive, publication-quality intelligence report on this website and the entity behind it.

---

## 1. Executive Summary
Write 3–4 dense paragraphs covering:
- What the company/site does, who it serves, and its apparent positioning
- Its scale, reach, and maturity (inferred from tone, breadth, and available data)
- What makes it distinctive or noteworthy vs. generic alternatives
- Any red flags, gaps, or inconsistencies observed across the site

## 2. Company Profile
Extract and infer everything available:
- Full legal name, trading name, and any brand aliases
- Country, city, and full address (from imprint/contact/footer)
- Registration number, VAT/tax ID, chamber of commerce references
- Year founded or inferred age of the business
- Company size (headcount ranges, office count, team page data)
- Leadership names and titles (from About/Team pages)
- Contact details: email, phone, support channels, social media handles

## 3. Products & Services — Deep Breakdown
For each distinct product, service, or offering found:
- Name and one-line description
- Target user/customer segment
- Pricing model (free/paid/freemium/enterprise/quote-based)
- Specific pricing figures if listed
- Key features or differentiators mentioned
- Any limitations, caveats, or fair-use policies stated

## 4. Target Audience & Market Positioning
- Primary and secondary customer segments (B2B/B2C/B2G, industry verticals)
- Geographic focus (local, national, EU, global)
- Language(s) the site serves
- Tone and communication style (formal/casual/technical/sales-heavy)
- Where they appear to sit in the market: budget, mid-market, or premium?

## 5. Technology & Infrastructure Signals
- Tech stack clues visible in the content (platforms, frameworks, tools mentioned)
- Integrations or third-party partnerships referenced
- APIs, developer docs, or SDKs advertised
- Security or compliance claims (ISO, GDPR, SOC2, etc.)

## 6. Content & SEO Signals
- Main topic clusters and keywords the site appears to target
- Types of content present (blog, docs, case studies, whitepapers, videos)
- Apparent content freshness (dates, version numbers, references to recent events)
- Any gated content or lead-gen mechanisms described

## 7. Trust, Social Proof & Credibility Signals
- Client logos, named customers, or case studies mentioned
- Testimonials or review scores cited
- Awards, certifications, press mentions, or partnerships listed
- Guarantees, SLAs, or refund policies stated

## 8. Key Facts — Rapid-Reference Table
Produce a compact table of the most extractable hard facts:
| Field | Value |
|---|---|
| Legal name | |
| Address | |
| Founded | |
| Headcount | |
| Pricing from | |
| Primary language | |
| GDPR compliant | |

## 9. Gaps & Caveats
- What important information was missing or vague?
- Where does the site appear evasive, outdated, or inconsistent?
- What would require a follow-up source to verify?

## 10. Analyst Conclusions
2–3 paragraphs of synthesis: what kind of entity is this, how credible does it appear,
and what is the single most important thing to know about it?"""


async def summarize_content(
    content: str,
    title: str,
    model: str = DEFAULT_MODEL,
    instructions: str | None = None,  # ← default to None
) -> str:
    # Get the latest API key from environment
    api_key = os.environ.get("OPENROUTER_API_KEY")


    if not api_key:
        print("DEBUG: API Key not found in os.environ. Searching for alternative keys...")
        # Check if it was accidentally prefixed with spaces or quotes
        for k, v in os.environ.items():
            if "OPENROUTER" in k:
                print(f"DEBUG: Found similar key: '{k}' with length {len(v)}")

    if not api_key or len(api_key.strip()) < 10:
        print("CRITICAL: OPENROUTER_API_KEY is missing or too short!")
        print(f"DEBUG: Key length: {len(api_key) if api_key else 0}")
        print(f"DEBUG: All Environment Keys: {sorted(list(os.environ.keys()))}")
        raise Exception(f"OPENROUTER_API_KEY is missing (current length: {len(api_key) if api_key else 0}). Please set it in your PyCharm environment variables or .env file.")

    if instructions is None:
        instructions = INSTRUCTIONS
    """
    Call OpenRouter with the scraped content and return a markdown intelligence report.

    Args:
        content:      The scraped text of the website pages.
        title:        The page or site title, used as context.
        model:        The OpenRouter model string to use.
        instructions: The report template/instructions injected into the user turn.
                      Defaults to the standard 10-section INSTRUCTIONS constant.

    Returns:
        A markdown-formatted intelligence report as a string.
    """
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