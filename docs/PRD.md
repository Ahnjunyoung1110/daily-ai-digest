# PRD: 하루하루의 IT 이슈

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 프로젝트명 | 하루하루의 IT 이슈 |
| 목적 | Notion을 CMS로 활용한 AI·IT 관련 이슈 정리 및 공유 웹 서비스 |
| CMS 선택 이유 | Notion API를 통해 별도 백엔드 없이 콘텐츠 관리 가능 |

---

## 2. 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Next.js 15, TypeScript |
| CMS | Notion API (`@notionhq/client`) |
| Styling | Tailwind CSS, shadcn/ui |
| Icons | Lucide React |
| 배포 | Vercel (예정) |

---

## 3. Notion 데이터베이스 구조

| 필드명 | Notion 타입 | 설명 |
|--------|-------------|------|
| `Title` | title | 글 제목 |
| `Category` | select | 카테고리 (AI, 보안, 클라우드 등) |
| `Tags` | multi_select | 태그 (복수 선택) |
| `Published` | date | 발행일 |
| `Status` | select | 상태: `초안` / `발행됨` |
| `Content` | page content | 본문 (Notion 페이지 블록) |
| `중요` | checkbox | 프론트 상단 노출용 중요 AI/IT 이슈 여부. 수집/동기화 때 현재 item 중 3~5개만 체크되며 stale 체크는 sync에서 해제 |
| `중요도` | number | 수집기 `score_item()` 원본 점수 (0~100+). source_authority + popularity + topic_relevance + freshness + penalty 합산 |

---

## 4. 주요 기능

### 4.1 글 목록 (홈)
- 최근 발행된 글 목록 표시 (`Status = 발행됨` 필터)
- `중요=true` 글을 별도 섹션이나 상단 카드로 우선 표시
- 제목, 카테고리, 태그, 발행일, 중요 여부 표시
- 페이지네이션 또는 무한 스크롤

### 4.2 검색 기능
- 제목 기반 키워드 검색
- 검색 결과 실시간 필터링

### 4.3 카테고리별 필터링
- 카테고리 선택 시 해당 글만 표시
- URL 파라미터(`?category=AI`)로 상태 유지

### 4.4 글 상세 페이지
- Notion 페이지 블록 렌더링
- 제목, 카테고리, 태그, 발행일 메타 정보 표시
- 이전/다음 글 네비게이션

### 4.5 반응형 디자인
- 모바일 / 태블릿 / 데스크탑 레이아웃 지원
- Tailwind CSS 브레이크포인트 기준: `sm(640)` / `md(768)` / `lg(1024)`

---

## 5. 화면 구성

```
/                       → 홈: 최근 글 목록
/posts/[slug]           → 글 상세 페이지
/category/[category]    → 카테고리별 글 목록
```

### 공통 레이아웃
- 헤더: 사이트명, 검색바
- 푸터: 저작권 표기

### 홈 (`/`)
- 히어로 섹션: 사이트 소개 문구
- 중요 섹션: Notion `중요=true` 글 3~5개를 최상단 노출
- 글 카드 그리드: 최신순 정렬
- 카테고리 필터 탭

### 글 상세 (`/posts/[slug]`)
- 제목, 메타 정보 (카테고리, 태그, 발행일)
- Notion 블록 렌더링 영역
- 관련 글 추천 (같은 카테고리)

### 카테고리 (`/category/[category]`)
- 선택된 카테고리 표시
- 해당 카테고리 글 목록

---

## 6. MVP 범위

| 기능 | MVP 포함 | 비고 |
|------|----------|------|
| Notion API 연동 | ✅ | `중요` checkbox 매핑 포함 |
| 글 목록 페이지 | ✅ | |
| 글 상세 페이지 | ✅ | |
| 기본 스타일링 | ✅ | |
| 반응형 디자인 | ✅ | |
| 검색 기능 | ✅ | 클라이언트 사이드 |
| 카테고리 필터링 | ✅ | |
| 댓글 기능 | ❌ | 추후 고려 |
| 다크 모드 | ❌ | 추후 고려 |
| RSS 피드 | ❌ | 추후 고려 |

---

## 7. 구현 단계

### 1단계: 환경 설정
- `@notionhq/client` 패키지 설치
- `.env.local`에 `NOTION_API_KEY`, `NOTION_DATABASE_ID` 설정
- Notion 데이터베이스 생성 및 통합(Integration) 연결

### 2단계: Notion API 연동
- `lib/notion.ts`: Notion 클라이언트 초기화
- 데이터베이스 쿼리 함수 구현 (`getPosts`, `getImportantPosts`, `getPostBySlug`)
- 블록 컨텐츠 조회 함수 구현 (`getPostContent`)

### 3단계: 글 목록 페이지 구현
- `app/page.tsx`: 홈 페이지 (SSG), `중요=true` 상단 섹션 포함
- `components/PostCard.tsx`: 글 카드 컴포넌트
- `components/CategoryFilter.tsx`: 카테고리 필터 컴포넌트

### 4단계: 글 상세 페이지 구현
- `app/posts/[slug]/page.tsx`: 상세 페이지 (SSG + ISR)
- `components/NotionRenderer.tsx`: Notion 블록 렌더러
- 정적 경로 생성 (`generateStaticParams`)

### 5단계: 스타일링 및 최적화
- shadcn/ui 컴포넌트 적용
- 반응형 레이아웃 완성
- 이미지 최적화 (`next/image`)
- 메타데이터 설정 (`generateMetadata`)

---

## 8. 디렉토리 구조 (예정)

```
notion-cms-it/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                    # 홈
│   ├── posts/
│   │   └── [slug]/
│   │       └── page.tsx            # 글 상세
│   └── category/
│       └── [category]/
│           └── page.tsx            # 카테고리
├── components/
│   ├── layout/
│   │   ├── Header.tsx
│   │   └── Footer.tsx
│   ├── PostCard.tsx
│   ├── CategoryFilter.tsx
│   ├── SearchBar.tsx
│   └── NotionRenderer.tsx
├── lib/
│   └── notion.ts                   # Notion API 클라이언트
├── types/
│   └── notion.ts                   # 타입 정의
├── docs/
│   └── PRD.md
└── .env.local
```

---

## 9. 환경 변수

```env
NOTION_API_KEY=secret_xxxx
NOTION_DATABASE_ID=xxxx
```

---

## 10. 성능 요구사항

| 항목 | 목표 |
|------|------|
| 초기 로드 (LCP) | 2.5초 이하 |
| 렌더링 전략 | SSG + ISR (revalidate: 3600초) |
| 이미지 최적화 | next/image WebP 변환 |
