# Daily AI Digest Web

Next.js 16 App Router 기반 AI/IT 다이제스트 프론트엔드. Notion DB를 CMS로 사용하며 서버 컴포넌트 + ISR로 렌더링.

## 빠른 시작

```bash
npm install
npm run dev   # http://localhost:3000
```

## 환경변수 (`.env.local`)

| 변수 | 설명 | 기본값 |
|---|---|---|
| `NOTION_API_KEY` | Notion 통합 키 ([발급](https://www.notion.so/my-integrations)) | — |
| `NOTION_DATABASE_ID` | Notion DB ID | `376d18a9-aa84-80f6-8a9b-e26f880dd0aa` |
| `ADMIN_PASSWORD` | `/admin` 대시보드 접근 비밀번호 | — |

## 기능

### 홈 (`/`)

- **중요 항목 섹션**: Notion `중요` checkbox가 `true`인 항목(매 sync마다 백엔드가 3~5개 마킹)을 페이지 최상단 강조 섹션으로 분리. 노란 테두리 + "중요" 배지.
- **검색**: 제목 · 요약 · 출처 · 태그 대상 실시간 부분일치 검색 (200ms 디바운스). `?q=` URL 동기화.
- **정렬 7종** (`?sort=` URL 동기화):

  | 키 | 기준 |
  |---|---|
  | `recent` (기본) | 수집일 최신순 |
  | `oldest` | 수집일 오래된순 |
  | `importance` | Notion `중요도`(number) 내림차순 → 수집일 tiebreak |
  | `relevance` | 검색어 매치 가중치순 (없으면 최신순) |
  | `title` | 제목 가나다순 |
  | `source` | 출처 가나다순 |
  | `topic` | 토픽 가나다순 → 수집일 tiebreak |

- **토픽 필터**: 탭 방식, `?topic=` URL 동기화.

### 상세 페이지 (`/posts/[slug]`)

Notion 페이지 블록을 렌더링. 이전/다음 글 네비게이션, 원문 링크.

### 다크모드

헤더 우측 Sun/Moon 토글. OS 설정 자동 감지(`defaultTheme="system"`). localStorage 저장.

### 관리자 대시보드 (`/admin`)

`ADMIN_PASSWORD` env 비번 인증(httpOnly 쿠키, 8시간 유효). 읽기 전용 — Notion 쓰기 없음.

- 요약 통계: 전체 / 수집완료 / 번역필요 / 중요 표시 수
- 토픽 · 출처별 분포 막대
- 중요 항목 목록 (3~5개 정상 여부 표시)
- 번역 필요 항목 목록

## Notion 프로퍼티 매핑

| Notion 프로퍼티 | 타입 | 프론트 필드 | 용도 |
|---|---|---|---|
| `제목` | title | `title` | 카드 제목 |
| `한줄요약` | rich_text | `summary` | 카드 본문 요약 |
| `토픽` | select | `topic` | 토픽 필터 탭 |
| `태그` | multi_select | `tags[]` | 카드 배지 |
| `출처` | select | `source` | 카드 메타 / 정렬 |
| `링크` | url | `link` | 원문 이동 |
| `수집일` | date | `collectedDate` | 날짜 표시 / 정렬 |
| `상태` | select | `status` | 관리자 집계 |
| `중요` | checkbox | `important` | 상단 강조 섹션 여부 |
| `중요도` | number | `importance` | 중요도순 정렬 점수 |
| `Canonical Key` | rich_text | `canonicalKey` | 안정적 upsert 키 |

> `중요도` 프로퍼티가 Notion DB에 없으면 `importance=0` 폴백 — 빌드/런타임 무오류.

## 아키텍처

```
app/
  page.tsx              홈 (ISR 60s, 서버 컴포넌트)
  layout.tsx            루트 레이아웃 + ThemeProvider
  posts/[slug]/         상세 페이지 (ISR 60s)
  admin/
    page.tsx            관리자 대시보드 (동적, 쿠키 인증)
    login/page.tsx      로그인 폼
  api/admin/login/      POST 인증 핸들러 (쿠키 발급)

components/
  PostsSection.tsx      중요 섹션 + 검색/정렬/토픽 필터 (client)
  PostCard.tsx          카드 컴포넌트 (highlighted 강조 지원)
  NotionRenderer.tsx    Notion 블록 → JSX
  theme-provider.tsx    next-themes 래퍼 (client)
  layout/
    Header.tsx          헤더 + 다크모드 토글
    theme-toggle.tsx    Sun/Moon 버튼 (client)

lib/
  notion.ts             Notion API 클라이언트 레이어
  sort.ts               정렬 순수 함수 (sortPosts, SORT_OPTIONS)
  utils.ts              cn() 헬퍼
```

## 데이터 흐름 참고

- `중요` checkbox는 `scripts/notion_digest_sync.py`가 매 sync마다 3~5개 범위로 자동 정규화.
- 5개 초과 시 → `notion_digest_sync.py` 재실행 또는 다음 sync 대기.
- 프론트는 Notion 쓰기 없음. CMS 변경은 백엔드 파이프라인을 통해.
