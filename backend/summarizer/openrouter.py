import httpx
from encore.runtime import secret

# Encore secrets — set with: encore secret set --type local OpenRouterAPIKey
openrouter_api_key = secret("OpenRouterAPIKey")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL   = "openai/gpt-4o-mini"

SYSTEM_PROMPT = """You are a concise content analyst.
Given the text of a webpage, produce a structured summary with:
1. A one-sentence TL;DR
2. Key points (3-5 bullet points)
3. Main takeaway

Keep the total response under 300 words. Be factual and neutral."""


async def summarize_content(content: str, title: str, model: str = DEFAULT_MODEL) -> str:
    """
    Call OpenRouter with the scraped content and return a markdown summary.
    """
    user_message = f"Page title: {title}\n\n---\n\n{content}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        "max_tokens": 512,
        "temperature": 0.3,
    }

    headers = {
        "Authorization": f"Bearer {openrouter_api_key()}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://url-summarizer.app",
        "X-Title":       "URL Summarizer",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"].strip()
