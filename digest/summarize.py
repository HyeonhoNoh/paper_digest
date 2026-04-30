"""
Claude API를 사용한 논문 요약.
"""

import logging
import os

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_KO = (
    "당신은 무선통신/신호처리 분야의 숙련된 연구자입니다. "
    "주어진 논문 초록을 정확하고 간결하게 한국어로 구조화하여 요약합니다. "
    "기술 용어는 영어 약어를 그대로 쓰고, 추측이나 일반론은 배제합니다."
)

SYSTEM_PROMPT_EN = (
    "You are an expert wireless communications and signal processing researcher. "
    "Summarize the given paper abstract precisely and concisely in a structured format. "
    "Keep technical acronyms in English. Avoid speculation."
)

PROMPT_TEMPLATE_KO = """다음 논문 초록을 4개 항목으로 요약하세요. 각 항목은 1-2문장, 전체 150자 내외.

제목: {title}
저자: {authors}
초록:
{abstract}

출력 형식 (마크다운, 굵은 라벨 그대로):
*문제*: ...
*방법*: ...
*핵심 결과*: ...
*의의*: ..."""

PROMPT_TEMPLATE_EN = """Summarize this paper abstract in 4 short bullets, each 1-2 sentences.

Title: {title}
Authors: {authors}
Abstract:
{abstract}

Output format (markdown, keep bold labels):
*Problem*: ...
*Method*: ...
*Key Result*: ...
*Significance*: ..."""


def summarize(paper: dict, model: str, language: str = "ko") -> str:
    """단일 논문 요약 → 마크다운 문자열."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    if language == "ko":
        system = SYSTEM_PROMPT_KO
        prompt = PROMPT_TEMPLATE_KO
    else:
        system = SYSTEM_PROMPT_EN
        prompt = PROMPT_TEMPLATE_EN

    user_content = prompt.format(
        title=paper["title"],
        authors=", ".join(paper["authors"][:5])
        + (" et al." if len(paper["authors"]) > 5 else ""),
        abstract=paper["abstract"][:4000],  # 초록은 사실 1500자 안팎이라 안전 cap
    )

    try:
        msg = client.messages.create(
            model=model,
            max_tokens=600,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        return msg.content[0].text.strip()
    except anthropic.APIError as e:
        logger.error("Claude API error for %s: %s", paper["arxiv_id"], e)
        return f"_요약 실패: {e}_"


def summarize_all(papers: list[dict], model: str, language: str = "ko") -> list[dict]:
    """모든 논문에 'summary' 필드 추가."""
    for i, p in enumerate(papers, 1):
        logger.info("[%d/%d] Summarizing %s", i, len(papers), p["arxiv_id"])
        p["summary"] = summarize(p, model=model, language=language)
    return papers
