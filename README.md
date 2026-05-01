# Paper Digest Agent

매주 평일 아침, **RSMA / ISAC / LLM-기반 통신 / Semantic Comm / Token Comm** 분야의 신규 arXiv 논문을 자동으로 검색하여 Claude로 요약하고 Slack에 보내주는 에이전트.

```
arXiv 검색 → Semantic Scholar 보강 → Claude 요약 → Slack 알림
```

## 동작 원리

- **소스**: arXiv API (메인) + Semantic Scholar API (인용 수, 학회 정보 보강)
- **대상 카테고리**: `cs.IT`, `eess.SP`, `cs.NI`
- **요약 모델**: Claude Haiku 4.5 (기본, 저렴) — `digest/config.py`에서 변경 가능
- **중복 방지**: `data/seen.json`에 처리한 arXiv ID 기록, 매번 자동 커밋
- **스케줄**: GitHub Actions cron으로 평일(월-금) 오전 9시(KST) 실행
- **신규 논문 0편인 날**: Slack 알림 생략 (조용히 종료)

## 셋업 (10분)

### 1. 이 레포지토리 fork 또는 복사

GitHub에 새 private repo를 만들고 이 디렉토리 전체를 push 하세요.

### 2. Slack Incoming Webhook 만들기

1. https://api.slack.com/apps → **Create New App** → From scratch
2. App 이름 (예: "Paper Digest"), 워크스페이스 선택
3. 좌측 **Incoming Webhooks** → On 으로 켜기
4. **Add New Webhook to Workspace** → 받을 채널 선택 (예: `#research-digest`)
5. 생성된 Webhook URL 복사 (`https://hooks.slack.com/services/...`)

### 3. Anthropic API 키 발급

https://console.anthropic.com/settings/keys 에서 키 발급.

### 4. GitHub Secrets 등록

레포지토리 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Name | Value |
|------|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `SLACK_WEBHOOK_URL` | Slack에서 받은 webhook URL |

### 5. 수동 테스트

레포지토리 → **Actions** → **Weekday Paper Digest** → **Run workflow** 버튼 클릭.

3-5분 정도 후에 Slack 채널에 다이제스트가 도착하면 성공.

## 로컬에서 실행 / 테스트

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env 파일 열어서 두 키 채우기

# .env 로드 (또는 export로 직접 설정)
set -a; source .env; set +a
python main.py
```

## 커스터마이징

### 검색 주제 추가/수정

`digest/config.py`의 `TOPICS` 딕셔너리 편집:

```python
TOPICS = {
    "Quantum-Comm": {
        "arxiv_query": '(abs:"quantum communication" OR abs:QKD) AND cat:quant-ph',
        "emoji": "⚛️",
    },
    # ...
}
```

arXiv 쿼리 문법: https://info.arxiv.org/help/api/user-manual.html#query_details
필드 prefix: `ti:` 제목, `abs:` 초록, `au:` 저자, `cat:` 카테고리, `all:` 전체.

### 요약 깊이 조절

`digest/config.py`:

```python
CLAUDE_MODEL = "claude-sonnet-4-6"  # 더 정교한 요약 (3배 비싸짐)
SUMMARY_LANGUAGE = "en"             # 영어 요약
```

### 실행 주기 변경

`.github/workflows/weekday-digest.yml`의 cron 변경:

```yaml
- cron: "0 0 * * 1-5"   # 평일 매일 09:00 KST (현재)
- cron: "0 0 * * 1"     # 매주 월요일만 09:00 KST
- cron: "0 0 * * *"     # 매일 09:00 KST (주말 포함)
- cron: "0 22 * * 0-4"  # 평일 매일 07:00 KST
```

cron은 UTC 기준. KST = UTC + 9.

### 검색 기간 / 최대 개수

```python
DAYS_BACK = 7               # 최근 7일치 (매일 돌려도 안전망 역할)
MAX_PAPERS_PER_TOPIC = 30   # 주제별 최대 30편
```

> 매일 실행해도 `seen.json`이 중복 검사하므로 같은 논문이 반복 요약되지 않습니다.

## 비용 추정

평일 매일 실행, 신규 논문 ~30-40편/주 가정. 같은 논문은 한 번만 요약됨.

| 모델 | 주간 비용 (USD) | 월간 비용 |
|------|---------------|----------|
| Haiku 4.5 ($1/$5 per 1M) | ~$0.15 | ~$0.65 |
| Sonnet 4.6 ($3/$15 per 1M) | ~$0.45 | ~$2.00 |

GitHub Actions 무료 한도(2000분/월) 안에서 충분히 돌아감 (월 약 25분 사용).

## 트러블슈팅

**Slack에 메시지가 안 온다**
→ Actions 탭에서 워크플로우 로그 확인. 특정 날 신규 논문이 없으면 정상적으로 알림 생략됨. 빨간 X면 로그의 `Run digest` 단계 확인.

**arXiv 검색 결과가 너무 적다 / 너무 많다**
→ `digest/config.py`의 쿼리 조정. `OR` 키워드를 늘리거나 줄이기.

**같은 논문이 다시 요약된다**
→ `data/seen.json`이 커밋되지 않았을 가능성. workflow의 `permissions: contents: write` 확인.

**새로 추가한 토픽이 안 보인다**
→ `seen.json`이 이미 해당 논문들을 "본 것"으로 처리했을 수 있음. 토픽 추가 후 누락이 의심되면 `data/seen.json`을 `[]`로 초기화하고 재실행.

**Semantic Scholar 429 에러**
→ 무시 가능. 보강 정보(인용 수)가 누락될 뿐 핵심 기능에는 영향 없음.

**Anthropic API 401 에러**
→ API 키 무효 또는 계정 크레딧 부족. https://console.anthropic.com 확인.

## 파일 구조

```
.
├── .github/workflows/weekday-digest.yml  # GitHub Actions 스케줄
├── digest/
│   ├── config.py        # 주제, 모델, 검색 설정 — 여기를 주로 편집
│   ├── sources.py       # arXiv + Semantic Scholar 검색
│   ├── summarize.py     # Claude API 요약
│   ├── slack.py         # Slack Block Kit 전송
│   └── state.py         # seen.json 관리
├── data/seen.json       # 처리한 arXiv ID (자동 생성/커밋)
├── main.py              # 엔트리 포인트
├── requirements.txt
└── .env.example
```
