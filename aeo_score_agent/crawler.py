from __future__ import annotations

from collections import deque
from time import perf_counter
from urllib.parse import urljoin, urlparse

import extruct
import requests
from bs4 import BeautifulSoup
from w3lib.html import get_base_url

from aeo_score_agent.models import PageData


USER_AGENT = "AEO-Score-Agent/1.0 (+https://github.com/araman1-dev/AEO-Score-Agent)"


class SiteCrawler:
    def __init__(self, max_pages: int = 10, timeout: int = 15):
        self.max_pages = max_pages
        self.timeout = timeout

    def crawl(self, start_url: str) -> list[PageData]:
        parsed_start = urlparse(start_url)
        if not parsed_start.scheme:
            start_url = f"https://{start_url}"
            parsed_start = urlparse(start_url)

        domain = parsed_start.netloc
        visited: set[str] = set()
        queue = deque([start_url])
        pages: list[PageData] = []

        while queue and len(pages) < self.max_pages:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            page = self._fetch_page(url)
            if page is None:
                continue

            pages.append(page)
            for link in page.links:
                parsed_link = urlparse(link)
                if parsed_link.netloc == domain and link not in visited:
                    queue.append(link)

        return pages

    def _fetch_page(self, url: str) -> PageData | None:
        headers = {"User-Agent": USER_AGENT}
        start = perf_counter()
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            elapsed = perf_counter() - start
            if "text/html" not in response.headers.get("Content-Type", ""):
                return None
        except requests.RequestException:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        extracted = extruct.extract(
            response.text,
            base_url=get_base_url(response.text, response.url),
            syntaxes=["json-ld", "microdata", "opengraph", "rdfa"],
        )

        schema_payloads: list[dict] = []
        schema_types: set[str] = set()

        for syntax in ("json-ld", "microdata", "rdfa"):
            for item in extracted.get(syntax, []):
                if isinstance(item, dict):
                    schema_payloads.append(item)
                    item_type = item.get("@type") or item.get("type")
                    if isinstance(item_type, str):
                        schema_types.add(item_type)
                    elif isinstance(item_type, list):
                        schema_types.update([t for t in item_type if isinstance(t, str)])

        headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"]) if h.get_text(strip=True)]
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
        list_items = [li.get_text(" ", strip=True) for li in soup.find_all("li") if li.get_text(strip=True)]
        img_alts = [img.get("alt", "").strip() for img in soup.find_all("img") if img.get("alt")]

        links: list[str] = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            full_url = urljoin(response.url, href)
            if full_url.startswith("http"):
                links.append(full_url.split("#")[0])

        body_text = soup.get_text(" ", strip=True).lower()
        has_author_bio_hint = any(k in body_text for k in ["author", "written by", "about the author", "bio"])
        has_pub_date = any(k in body_text for k in ["published", "publication date", "posted on"])
        has_last_updated = any(k in body_text for k in ["last updated", "updated on", "modified"])
        has_faq_hint = "faq" in body_text or any("?" in h for h in headings)
        has_about_hint = any(k in body_text for k in ["about us", "our story", "mission"])
        has_trust_signals = any(
            k in body_text
            for k in ["certified", "award", "trusted by", "partnership", "accredited", "testimonial"]
        )

        return PageData(
            url=response.url,
            status_code=response.status_code,
            load_time_seconds=elapsed,
            html=response.text,
            title=(soup.title.get_text(strip=True) if soup.title else ""),
            meta_description=(soup.find("meta", attrs={"name": "description"}) or {}).get("content", "")
            if soup.find("meta", attrs={"name": "description"})
            else "",
            canonical=(soup.find("link", attrs={"rel": "canonical"}) or {}).get("href")
            if soup.find("link", attrs={"rel": "canonical"})
            else None,
            headings=headings,
            paragraphs=paragraphs,
            list_items=list_items,
            image_alt_texts=img_alts,
            links=links,
            schema_types=schema_types,
            schema_payloads=schema_payloads,
            has_author_bio_hint=has_author_bio_hint,
            has_pub_date=has_pub_date,
            has_last_updated=has_last_updated,
            has_faq_section_hint=has_faq_hint,
            has_about_hint=has_about_hint,
            has_trust_signals_hint=has_trust_signals,
        )
