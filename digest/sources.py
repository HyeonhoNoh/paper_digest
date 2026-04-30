"""
논문 검색 및 메타데이터 수집.
- arXiv API: 주 소스 (제목, 초록, 저자, 발표일)
- Semantic Scholar API: 인용 수, TLDR 등으로 보강 (best-effort)
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Iterable

import arxiv
import requests

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"


def fetch_arxiv(query: str, days_back: int, max_results: int) -> list[dict]:
    """
    arXiv에서 최근 days_back일간 게시된 논문 검색.
    SubmittedDate 내림차순 정렬, 컷오프보다 오래된 논문 만나면 중단.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    search = arxiv.Search(
        query=query,
        max_results=max_results * 2,  # 컷오프 필터링 여유분
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    client = arxiv.Client(page_size=50, delay_seconds=3.0, num_retries=3)

    papers = []
    for result in client.results(search):
        if result.published < cutoff:
            break  # 정렬되어 있으니 더 볼 필요 없음
        # arxiv_id에서 버전(v1, v2 등) 제거 → 안정적인 dedup 키
        raw_id = result.entry_id.rsplit("/", 1)[-1]
        arxiv_id = raw_id.split("v")[0]

        papers.append(
            {
                "arxiv_id": arxiv_id,
                "title": " ".join(result.title.split()),  # 줄바꿈 정규화
                "authors": [a.name for a in result.authors],
                "abstract": " ".join(result.summary.split()),
                "published": result.published.isoformat(),
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "pdf_url": result.pdf_url,
                "categories": result.categories,
            }
        )
        if len(papers) >= max_results:
            break

    logger.info("arXiv: %d papers found for query", len(papers))
    return papers


def enrich_with_semantic_scholar(papers: list[dict]) -> list[dict]:
    """
    Semantic Scholar로 인용 수, TLDR 등 보강. 실패해도 원본 그대로 반환.
    Rate limit: 익명 1 req/sec.
    """
    for p in papers:
        try:
            r = requests.get(
                f"{SEMANTIC_SCHOLAR_BASE}/paper/arXiv:{p['arxiv_id']}",
                params={"fields": "citationCount,influentialCitationCount,venue,tldr"},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                p["citations"] = data.get("citationCount", 0)
                p["tldr"] = (data.get("tldr") or {}).get("text")
                p["venue"] = data.get("venue") or None
            elif r.status_code == 429:
                logger.warning("Semantic Scholar rate limited, sleeping 5s")
                time.sleep(5)
        except Exception as e:
            logger.debug("Semantic Scholar enrichment failed for %s: %s", p["arxiv_id"], e)
        time.sleep(1.1)  # rate limit 보수적으로
    return papers


def fetch_topic(query: str, days_back: int, max_results: int) -> list[dict]:
    """주어진 쿼리에 대해 arXiv 검색 + Semantic Scholar 보강."""
    papers = fetch_arxiv(query, days_back, max_results)
    if papers:
        papers = enrich_with_semantic_scholar(papers)
    return papers
