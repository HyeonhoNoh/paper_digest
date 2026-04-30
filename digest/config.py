"""
주제별 검색 쿼리 설정.
arXiv API는 Lucene 문법 사용: https://info.arxiv.org/help/api/user-manual.html#query_details
필드: ti(제목), abs(초록), au(저자), cat(카테고리), all(전체)
"""

TOPICS = {
    "RSMA": {
        "arxiv_query": (
            '(abs:"rate splitting" OR abs:RSMA OR ti:RSMA OR ti:"rate splitting") '
            'AND (cat:cs.IT OR cat:eess.SP OR cat:cs.NI)'
        ),
        "emoji": "📡",
    },
    "ISAC": {
        "arxiv_query": (
            '(abs:"integrated sensing and communication" '
            'OR abs:"integrated sensing and communications" '
            'OR abs:ISAC OR ti:ISAC '
            'OR abs:"joint communication and sensing" '
            'OR abs:"joint sensing and communication") '
            'AND (cat:cs.IT OR cat:eess.SP OR cat:cs.NI)'
        ),
        "emoji": "🛰️",
    },
    "LLM-Comm": {
        "arxiv_query": (
            '(abs:"large language model" OR abs:"large language models" OR abs:LLM '
            'OR abs:"large multimodal model" OR abs:LMM '
            'OR abs:"vision-language model" OR abs:VLM '
            'OR abs:"foundation model") '
            'AND (abs:wireless OR abs:6G OR abs:"semantic communication" '
            'OR abs:"network management" OR abs:"radio access" '
            'OR abs:"physical layer" OR abs:"resource allocation" '
            'OR abs:"beam selection" OR abs:beamforming) '
            'AND (cat:cs.NI OR cat:cs.IT OR cat:eess.SP)'
        ),
        "emoji": "🤖",
    },
    "Semantic-Comm": {
        "arxiv_query": (
            '(abs:"semantic communication" OR abs:"semantic communications" '
            'OR ti:"semantic communication" OR ti:"semantic communications") '
            'AND (cat:cs.IT OR cat:eess.SP OR cat:cs.NI)'
        ),
        "emoji": "💬",
    },
}

# 검색 범위
DAYS_BACK = 7
MAX_PAPERS_PER_TOPIC = 30  # 주제별 최대 가져올 논문 수 (안전장치)

# Claude 요약 설정
# 비용 효율: claude-haiku-4-5 ($1/$5 per 1M tokens)
# 더 자세한 요약 원하면: claude-sonnet-4-6 ($3/$15)
CLAUDE_MODEL = "claude-haiku-4-5"
SUMMARY_LANGUAGE = "ko"  # "ko" 한글, "en" 영어
