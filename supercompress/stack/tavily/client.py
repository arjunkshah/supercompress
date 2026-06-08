"""Tavily integration — search, extract, research for agent retrieval."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from supercompress.stack._paths import FIXTURES
from supercompress.stack.config import Settings, get_settings


@dataclass
class SearchHit:
    title: str
    url: str
    content: str
    score: float = 0.0


@dataclass
class TavilyBundle:
    query: str
    hits: List[SearchHit] = field(default_factory=list)
    extracted: List[Dict[str, Any]] = field(default_factory=list)
    answer: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_context_block(self) -> str:
        lines = [f"## Tavily research: {self.query}"]
        if self.answer:
            lines.append(f"**Synthesis:** {self.answer}")
        for i, hit in enumerate(self.hits[:8], 1):
            lines.append(f"\n### [{i}] {hit.title}\nURL: {hit.url}\n{hit.content[:1200]}")
        for ext in self.extracted[:5]:
            lines.append(
                f"\n### Extract: {ext.get('url', 'unknown')}\n{ext.get('content', '')[:1500]}"
            )
        return "\n".join(lines)


class TavilyClient:
    """Multi-surface Tavily client: search → extract → synthesize."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from tavily import TavilyClient as _Tavily

            self._client = _Tavily(api_key=self.settings.tavily_api_key)
        return self._client

    def search(
        self,
        query: str,
        *,
        max_results: int = 8,
        search_depth: str = "advanced",
        topic: str = "general",
        time_range: Optional[str] = "week",
        include_domains: Optional[List[str]] = None,
    ) -> TavilyBundle:
        kwargs: Dict[str, Any] = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "topic": topic,
        }
        if time_range:
            kwargs["time_range"] = time_range
        if include_domains:
            kwargs["include_domains"] = include_domains

        resp = self.client.search(**kwargs)
        hits = [
            SearchHit(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                score=float(r.get("score", 0)),
            )
            for r in resp.get("results", [])
        ]
        return TavilyBundle(query=query, hits=hits, raw=resp)

    def search_multi(self, queries: List[str], **kwargs) -> TavilyBundle:
        """Parallel-style multi-query research with deduped URLs."""
        seen: set[str] = set()
        all_hits: List[SearchHit] = []
        for q in queries:
            bundle = self.search(q, **kwargs)
            for hit in bundle.hits:
                if hit.url not in seen:
                    seen.add(hit.url)
                    all_hits.append(hit)
        return TavilyBundle(
            query=" | ".join(queries),
            hits=sorted(all_hits, key=lambda h: h.score, reverse=True),
        )

    def extract_urls(self, urls: List[str], query: Optional[str] = None) -> List[Dict[str, Any]]:
        if not urls:
            return []
        resp = self.client.extract(urls=urls[:20], query=query)
        results = resp.get("results", [])
        return [
            {"url": r.get("url", ""), "content": r.get("raw_content", r.get("content", ""))}
            for r in results
        ]

    def search_and_answer(self, query: str, **kwargs) -> TavilyBundle:
        """Full research pass: search with answer synthesis + top URL extract."""
        kwargs.setdefault("search_depth", "advanced")
        resp = self.client.search(query=query, include_answer=True, max_results=kwargs.pop("max_results", 8), **kwargs)
        hits = [
            SearchHit(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                score=float(r.get("score", 0)),
            )
            for r in resp.get("results", [])
        ]
        bundle = TavilyBundle(query=query, hits=hits, answer=resp.get("answer"), raw=resp)
        top_urls = [h.url for h in bundle.hits[:5] if h.url]
        bundle.extracted = self.extract_urls(top_urls, query=query)
        return bundle

    def company_intel(self, company: str, website: Optional[str] = None) -> TavilyBundle:
        queries = [
            f"{company} funding news 2026",
            f"{company} product launch agent AI",
            f"{company} competitors market position",
        ]
        bundle = self.search_multi(queries, topic="news", time_range="month")
        if website:
            bundle.extracted = self.extract_urls([website], query=f"{company} overview")
        bundle.answer = f"Competitive intel gathered for {company} across {len(bundle.hits)} sources."
        return bundle

    def social_pulse(self, topic: str) -> TavilyBundle:
        return self.search(
            f"{topic} site:reddit.com OR site:news.ycombinator.com OR site:twitter.com",
            topic="general",
            time_range="week",
            max_results=10,
        )


class DemoTavilyClient(TavilyClient):
    """Fixture-backed Tavily for `supercompress doctor` and CI."""

    def search(self, query: str, **kwargs) -> TavilyBundle:
        data = json.loads((FIXTURES / "tavily_search.json").read_text())
        hits = [SearchHit(**h) for h in data.get("hits", [])]
        return TavilyBundle(query=query, hits=hits, answer=data.get("answer"))

    def extract_urls(self, urls: List[str], query: Optional[str] = None) -> List[Dict[str, Any]]:
        data = json.loads((FIXTURES / "tavily_extract.json").read_text())
        return data.get("results", [])

    def search_and_answer(self, query: str, **kwargs) -> TavilyBundle:
        bundle = self.search(query)
        bundle.extracted = self.extract_urls([h.url for h in bundle.hits[:3]])
        return bundle

    def company_intel(self, company: str, website: Optional[str] = None) -> TavilyBundle:
        return self.search_and_answer(f"{company} AI agent competitive landscape")

    def social_pulse(self, topic: str) -> TavilyBundle:
        return self.search(f"developer sentiment {topic}")


def get_tavily(settings: Optional[Settings] = None) -> TavilyClient:
    s = settings or get_settings()
    if s.demo_mode or not s.has_tavily():
        return DemoTavilyClient(s)
    return TavilyClient(s)
