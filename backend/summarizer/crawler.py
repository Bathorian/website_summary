import asyncio
from typing import List, Dict, Set
from .scraper import scrape_url

async def crawl_website(start_url: str, max_pages: int = 11, max_depth: int = 1) -> Dict:
    """
    Crawls a website starting from start_url.
    Returns a combined dictionary containing the main title and concatenated markdown of all visited pages.
    """
    visited: Set[str] = set()
    to_visit: List[Dict] = [{"url": start_url, "depth": 0}]
    results: List[Dict] = []
    
    main_title = "Unknown"

    while to_visit and len(visited) < max_pages:
        current = to_visit.pop(0)
        url = current["url"]
        depth = current["depth"]

        if url in visited:
            continue
        
        print(f"Crawler: Visiting {url} (depth {depth})")
        visited.add(url)
        
        try:
            # For the first page, we always extract links.
            # For subsequent pages, only if we haven't reached max_depth yet.
            should_extract_links = (depth < max_depth)
            scraped = await scrape_url(url, extract_links=should_extract_links)
            
            if not scraped or scraped.get("title") == "Error":
                print(f"Crawler: Failed to scrape {url}")
                if url == start_url:
                    return scraped
                continue

            if url == start_url:
                main_title = scraped["title"]
            
            results.append(scraped)

            # Add internal links to the queue
            if should_extract_links:
                for link in scraped.get("links", []):
                    if link not in visited:
                        to_visit.append({"url": link, "depth": depth + 1})
        
        except Exception as e:
            print(f"Crawler: Error scraping {url}: {e}")
            if url == start_url:
                return {"title": "Error", "markdown": str(e), "url": url}
            continue

    # Combine all results into a single context
    combined_markdown = ""
    for idx, res in enumerate(results):
        combined_markdown += f"\n\n--- Page {idx+1}: {res['url']} ---\n\n"
        combined_markdown += res["markdown"]

    return {
        "title": main_title,
        "markdown": combined_markdown.strip(),
        "visited_urls": list(visited)
    }
