import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import markdownify


class ScrapeResult:
    def __init__(self, title: str, content: str, url: str, markdown: str = ""):
        self.title = title
        self.content = content
        self.url = url
        self.markdown = markdown


async def scrape_url(url: str, extract_links: bool = False) -> dict:
    """
    Fetch a URL and extract clean text content and markdown.
    Optional: extract top 10 internal links for crawling.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, verify=False) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return {"title": "Error", "content": "", "url": url, "markdown": "", "links": []}

    try:
        soup = BeautifulSoup(response.text, "lxml")
    except Exception as e:
        print(f"lxml parser failed, falling back to html.parser: {e}")
        soup = BeautifulSoup(response.text, "html.parser")

    # Extract Title
    title = soup.title.string.strip() if soup.title and soup.title.string else url

    # Extract Links (if requested)
    links = []
    if extract_links:
        domain = urlparse(url).netloc
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(url, href)
            parsed_full = urlparse(full_url)
            # Only keep internal links, ignore fragments
            if parsed_full.netloc == domain and "#" not in full_url:
                if full_url not in links and full_url != url:
                    links.append(full_url)
            if len(links) >= 10:
                break

    # Clean HTML for Content/Markdown
    # Remove noise elements
    for tag in soup(["script", "style", "nav", "footer", "aside", "header",
                     "form", "iframe", "noscript", "svg", "img"]):
        tag.decompose()

    # Try to get the main content block first, fall back to body
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(class_="content")
        or soup.find("body")
    )

    if not main:
        return {"title": title, "content": "", "url": url, "markdown": "", "links": links}

    # Convert to Markdown
    md_content = markdownify.markdownify(str(main), heading_style="ATX").strip()

    # Get Raw Text
    raw_text = main.get_text(strip=True)

    # Cap content length to prevent token overflow (~8k chars per page for multi-page)
    md_content = md_content[:8000]
    raw_text = raw_text[:8000]

    return {
        "title": title,
        "content": raw_text,
        "url": url,
        "markdown": md_content,
        "links": links
    }
