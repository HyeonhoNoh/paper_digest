"""
이미 본 arXiv ID 추적. data/seen.json에 저장.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_FILE = Path("data/seen.json")
MAX_TRACKED = 5000  # 무한정 커지지 않게 cap


def load_seen() -> set[str]:
    if not STATE_FILE.exists():
        return set()
    try:
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("seen.json 로드 실패, 빈 set으로 시작: %s", e)
        return set()


def save_seen(seen: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # 너무 커지면 가장 옛날 것부터 truncate (단순 정렬 — arXiv ID는 YYMM.NNNNN 형식이라 시간순)
    if len(seen) > MAX_TRACKED:
        kept = sorted(seen)[-MAX_TRACKED:]
        seen = set(kept)
    STATE_FILE.write_text(
        json.dumps(sorted(seen), indent=2, ensure_ascii=False), encoding="utf-8"
    )
