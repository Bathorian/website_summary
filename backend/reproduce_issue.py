import asyncio
from summarizer.scraper import scrape_url

async def main():
    url = "https://example.com"
    print(f"Testing scraper for {url} with lxml...")
    result = await scrape_url(url, extract_links=True)
    if result["title"] == "Error":
        print(f"Scrape failed: {result['markdown']}")
    else:
        print(f"Scrape successful: {result['title']}")
        print(f"Links found: {len(result['links'])}")
        print(f"Markdown snippet: {result['markdown'][:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
