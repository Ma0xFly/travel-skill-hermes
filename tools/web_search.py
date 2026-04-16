from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import List

from config import DEFAULT_WEB_SEARCH_LIMIT, REQUEST_TIMEOUT, WEB_SEARCH_BASE_URL
from tool_types import ApiResult, SearchResultBundle, SearchResultItem


def _http_get(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "travel-skill/1.0"})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _collect_related_topics(topics: List[dict], limit: int) -> List[SearchResultItem]:
    results: List[SearchResultItem] = []

    def visit(entries: List[dict]) -> None:
        for entry in entries:
            if len(results) >= limit:
                return
            if "Topics" in entry:
                visit(entry.get("Topics", []))
                continue

            text = entry.get("Text", "")
            url = entry.get("FirstURL", "")
            if not text or not url:
                continue

            title = text.split(" - ", 1)[0].strip()
            results.append(
                SearchResultItem(
                    title=title,
                    snippet=text,
                    url=url,
                )
            )

    visit(topics)
    return results


def search_web(query: str, limit: int = DEFAULT_WEB_SEARCH_LIMIT) -> ApiResult:
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1,
    }
    url = f"{WEB_SEARCH_BASE_URL}?{urllib.parse.urlencode(params)}"

    try:
        payload = _http_get(url)
        items: List[SearchResultItem] = []

        abstract = payload.get("AbstractText", "")
        abstract_url = payload.get("AbstractURL", "")
        heading = payload.get("Heading", "")
        if abstract and abstract_url:
            items.append(SearchResultItem(title=heading or query, snippet=abstract, url=abstract_url))

        related = _collect_related_topics(payload.get("RelatedTopics", []), limit=max(limit - len(items), 0))
        items.extend(related)
        items = items[:limit]

        summary = items[0].snippet if items else "未检索到直接结果，可换更具体关键词重试。"
        bundle = SearchResultBundle(query=query, items=items, summary=summary)
        return ApiResult(ok=True, source="duckduckgo", data=bundle)
    except Exception as exc:
        return ApiResult(ok=False, source="duckduckgo", error=str(exc))
