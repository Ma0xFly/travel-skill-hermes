from __future__ import annotations

from typing import List

from config import DEFAULT_WEB_SEARCH_LIMIT
from sources_registry import search_with_chain
from tool_types import ApiResult, SearchResultBundle, SearchResultItem


def search_web(query: str, limit: int = DEFAULT_WEB_SEARCH_LIMIT) -> ApiResult:
    """联网搜索：走信源注册表引擎链（Exa → Tavily → DuckDuckGo，见 sources_registry.ENGINES）。

    返回的 source 字段 = 实际命中的引擎名，便于诊断信源质量。
    """
    items_raw, engine_used = search_with_chain(query, limit=limit)

    if not items_raw:
        return ApiResult(
            ok=False,
            source="engine-chain",
            error="全部搜索引擎无结果或不可用（exa/tavily/duckduckgo），可换更具体关键词重试。",
        )

    items: List[SearchResultItem] = [
        SearchResultItem(
            title=it.get("title") or query,
            snippet=it.get("snippet") or it.get("title") or "",
            url=it.get("url", ""),
        )
        for it in items_raw
        if it.get("url")
    ]
    items = items[:limit]

    summary = items[0].snippet if items else "未检索到直接结果，可换更具体关键词重试。"
    bundle = SearchResultBundle(query=query, items=items, summary=summary)
    return ApiResult(ok=True, source=engine_used, data=bundle)
