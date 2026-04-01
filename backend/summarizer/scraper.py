import httpx
from bs4 import BeautifulSoup


class ScrapeResult:
    def __init__(self, title: str, content: str, url: str):
        self.title = title
        self.content = content
        self.url = url


async def scrape_url(url: str) -> ScrapeResult:
    """
    Fetch a URL and extract clean text content using BeautifulSoup.
    Strips scripts, styles, nav elements, and other noise.
    Caps content at ~8 000 chars to stay within LLM context limits.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; URLSummarizer/1.0; "
            "+https://github.com/your-org/url-summarizer)"
        )
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "footer", "aside", "header",
                     "form", "iframe", "noscript", "svg", "img"]):
        tag.decompose()

    # Extract title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Try to get the main content block first, fall back to body
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(class_="content")
        or soup.find("body")
    )

    raw_text = main.get_text(separator="\n", strip=True) if main else ""

    # Collapse blank lines and cap length
    lines = [ln for ln in raw_text.splitlines() if ln.strip()]
    content = "\n".join(lines)[:8_000]

    return ScrapeResult(title=title, content=content, url=url)
