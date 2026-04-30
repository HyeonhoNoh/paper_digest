"""
주간 논문 다이제스트 메인 엔트리 포인트.

실행 흐름:
1. 주제별 arXiv 검색 (최근 N일)
2. Semantic Scholar로 메타데이터 보강
3. 이미 본 논문 필터링
4. Claude API로 요약
5. Slack으로 전송
6. seen.json 업데이트
"""

import logging
import os
import sys

from digest import config
from digest.slack import send_digest
from digest.sources import fetch_topic
from digest.state import load_seen, save_seen
from digest.summarize import summarize_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("digest")


def main() -> int:
    # 환경변수 체크
    for var in ("ANTHROPIC_API_KEY", "SLACK_WEBHOOK_URL"):
        if not os.environ.get(var):
            logger.error("환경변수 %s 누락", var)
            return 1

    seen = load_seen()
    logger.info("이미 본 논문: %d개", len(seen))

    topic_summaries: dict[str, list[dict]] = {}
    new_ids: set[str] = set()

    # 1. 주제별 수집
    for topic, cfg in config.TOPICS.items():
        logger.info("=== %s ===", topic)
        try:
            papers = fetch_topic(
                cfg["arxiv_query"],
                days_back=config.DAYS_BACK,
                max_results=config.MAX_PAPERS_PER_TOPIC,
            )
        except Exception as e:
            logger.exception("[%s] 검색 실패: %s", topic, e)
            topic_summaries[topic] = []
            continue

        # 이미 본 것 제외
        fresh = [p for p in papers if p["arxiv_id"] not in seen]
        logger.info("[%s] %d개 검색됨, %d개 신규", topic, len(papers), len(fresh))

        topic_summaries[topic] = fresh
        new_ids.update(p["arxiv_id"] for p in fresh)

    # 신규 논문이 하나도 없으면 종료
    total_new = sum(len(ps) for ps in topic_summaries.values())
    if total_new == 0:
        logger.info("이번 주 새 논문 없음. Slack 알림 생략.")
        return 0

    # 2. 요약
    for topic, papers in topic_summaries.items():
        if papers:
            logger.info("=== Summarizing %s (%d papers) ===", topic, len(papers))
            summarize_all(
                papers, model=config.CLAUDE_MODEL, language=config.SUMMARY_LANGUAGE
            )

    # 3. Slack 전송
    try:
        send_digest(
            topic_summaries,
            topic_meta=config.TOPICS,
            webhook_url=os.environ["SLACK_WEBHOOK_URL"],
        )
        logger.info("Slack 전송 완료")
    except Exception as e:
        logger.exception("Slack 전송 실패: %s", e)
        return 2

    # 4. seen 업데이트 (Slack 성공 후에만)
    seen.update(new_ids)
    save_seen(seen)
    logger.info("seen.json 업데이트 완료 (%d개)", len(seen))

    return 0


if __name__ == "__main__":
    sys.exit(main())
