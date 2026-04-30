"""
Slack Incoming Webhook으로 다이제스트 전송.
Block Kit 사용. 메시지당 50블록 제한 → 주제별로 분할 전송.
"""

import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

SLACK_BLOCK_LIMIT = 45  # 50이지만 안전 마진
SLACK_TEXT_LIMIT = 2900  # 3000이지만 안전 마진


def _truncate(text: str, limit: int = SLACK_TEXT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n_…(truncated)_"


def _paper_block(paper: dict, topic_emoji: str) -> dict:
    """단일 논문을 Block Kit section으로 변환."""
    authors = paper.get("authors", [])
    author_str = ", ".join(authors[:3])
    if len(authors) > 3:
        author_str += f" 외 {len(authors) - 3}명"

    citations = paper.get("citations")
    venue = paper.get("venue")
    meta_parts = []
    if venue:
        meta_parts.append(f"📍 {venue}")
    if citations is not None and citations > 0:
        meta_parts.append(f"📈 {citations} citations")
    meta_str = " · ".join(meta_parts)

    text = (
        f"*<{paper['url']}|{paper['title']}>*\n"
        f"_{author_str}_"
    )
    if meta_str:
        text += f"\n{meta_str}"
    text += f"\n\n{paper.get('summary', '_요약 없음_')}"

    return {
        "type": "section",
        "text": {"type": "mrkdwn", "text": _truncate(text)},
    }


def _send(webhook_url: str, blocks: list[dict], fallback_text: str) -> None:
    """Slack에 한 메시지 전송."""
    payload = {"text": fallback_text, "blocks": blocks}
    r = requests.post(webhook_url, json=payload, timeout=15)
    if r.status_code != 200:
        logger.error("Slack post failed (%d): %s", r.status_code, r.text)
    r.raise_for_status()


def send_digest(
    topic_summaries: dict[str, list[dict]],
    topic_meta: dict[str, dict],
    webhook_url: str,
) -> None:
    """
    주제별로 묶어 Slack 메시지 전송.

    topic_summaries: {topic_name: [paper_dict, ...]}
    topic_meta: config.TOPICS (이모지 등)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    total_papers = sum(len(ps) for ps in topic_summaries.values())

    # 헤더 메시지
    header_blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📚 주간 논문 다이제스트 — {today}"},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"이번 주 신규 논문 *{total_papers}편* | 주제 {len(topic_summaries)}개",
                }
            ],
        },
        {"type": "divider"},
    ]
    _send(webhook_url, header_blocks, f"주간 논문 다이제스트 ({total_papers}편)")

    # 주제별로 메시지 분할 전송
    for topic, papers in topic_summaries.items():
        emoji = topic_meta.get(topic, {}).get("emoji", "🔹")
        if not papers:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{emoji} {topic}* — 이번 주 새 논문 없음",
                    },
                }
            ]
            _send(webhook_url, blocks, f"{topic}: 신규 논문 없음")
            continue

        # 주제 헤더
        topic_blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} {topic} ({len(papers)}편)"},
            }
        ]

        # 논문들을 블록으로 변환, chunk로 분할
        chunks = [topic_blocks]
        current = chunks[0]

        for p in papers:
            paper_blocks = [_paper_block(p, emoji), {"type": "divider"}]
            if len(current) + len(paper_blocks) > SLACK_BLOCK_LIMIT:
                # 새 chunk 시작
                current = []
                chunks.append(current)
            current.extend(paper_blocks)

        for chunk in chunks:
            if chunk:
                _send(webhook_url, chunk, f"{topic} 논문 요약")
