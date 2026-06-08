# ROADMAP

> 이 로드맵은 `docs/PRD.md`를 기반으로 생성되었습니다. (작성일: 2026-06-05)

---

## 프로젝트 개요

Notion을 CMS로 활용하여 AI·IT 관련 이슈를 정리하고 공유하는 웹 서비스입니다.
별도의 백엔드 없이 Notion API로 콘텐츠를 관리하며, Next.js 15 기반의 SSG + ISR 렌더링 전략으로 빠른 초기 로드를 목표로 합니다.

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 프레임워크 | Next.js 15 (App Router) |
| 언어 | TypeScript |
| CMS | Notion API (`@notionhq/client`) |
| 스타일링 | Tailwind CSS, shadcn/ui |
| 아이콘 | Lucide React |
| 렌더링 전략 | SSG + ISR (revalidate: 3600초) |
| 배포 | Vercel |

---

## 개발 단계

### Phase 0: 프로젝트 초기 설정 (예상 소요: 1일)

**목표**
개발을 시작하기 위한 뼈대를 구축합니다. 환경 변수, 패키지, 디렉토리 구조를 먼저 잡아야 이후 모든 단계에서 일관된 환경을 유지할 수 있습니다.

**왜 이 순서인가**
초기 설정이 잘못되면 이후 모든 작업에서 수정 비용이 발생합니다. 골격을 먼저 확립해야 공통 모듈과 핵심 기능 개발이 충돌 없이 진행됩니다.

**작업 항목**

- [ ] Next.js 15 프로젝트 생성 (`create-next-app`, App Router, TypeScript 옵션 선택)
- [ ] 필수 패키지 설치
  - `@notionhq/client`
  - `tailwindcss`, `postcss`, `autoprefixer`
  - `shadcn/ui` 초기화 (`npx shadcn-ui@latest init`)
  - `lucide-react`
- [ ] 디렉토리 구조 생성
  - `app/`, `components/layout/`, `components/`, `lib/`, `types/`
- [ ] `.env.local` 파일 생성 및 환경 변수 설정
  - `NOTION_API_KEY`
  - `NOTION_DATABASE_ID`
- [ ] `.env.local`을 `.gitignore`에 등록
- [ ] `tailwind.config.ts` 설정 (폰트, 컬러 팔레트, 브레이크포인트 확인)
- [ ] `app/layout.tsx` 기본 구조 작성 (메타데이터, `<html>`, `<body>` 태그)
- [ ] ESLint, Prettier 설정 (팀 컨벤션 통일)

**완료 기준**

- [ ] `npm run dev` 실행 시 로컬 서버가 정상 기동됨
- [ ] 환경 변수가 `process.env`로 정상 참조됨
- [ ] Tailwind CSS 클래스가 페이지에 적용됨
- [ ] shadcn/ui 기본 컴포넌트(`Button` 등) import 가능

---

### Phase 1: 공통 모듈 및 레이아웃 개발 (예상 소요: 2일)

**목표**
Notion API 연동 레이어와 공통 레이아웃 컴포넌트를 만듭니다. 이 모듈들은 모든 페이지에서 사용되므로 핵심 기능 개발보다 먼저 완성되어야 합니다.

**왜 이 순서인가**
`lib/notion.ts`가 없으면 어떤 페이지도 데이터를 가져올 수 없습니다. 공통 레이아웃(`Header`, `Footer`)도 이 단계에서 만들어야 이후 페이지 개발 시 중복 작업이 발생하지 않습니다.

**작업 항목**

**타입 정의 (`types/notion.ts`)**
- [ ] `NotionPost` 타입 정의 (id, title, category, tags, publishedDate, status, slug, important)
- [ ] `NotionBlock` 타입 정의 (Notion 페이지 블록 구조)

**Notion API 모듈 (`lib/notion.ts`)**
- [ ] Notion 클라이언트 초기화 (`new Client({ auth: NOTION_API_KEY })`)
- [ ] `getPosts()`: Status=`발행됨` 필터, 발행일 내림차순 정렬로 글 목록 조회
- [ ] `getImportantPosts()`: Notion checkbox `중요=true`인 현재 중요 글 3~5개 조회
- [ ] `getPostBySlug(slug)`: slug(페이지 ID 또는 고유값)로 단일 글 조회
- [ ] `getPostBlocks(pageId)`: 페이지의 블록 콘텐츠 조회
- [ ] `getCategories()`: 카테고리 목록 추출
- [ ] Notion API 응답을 `NotionPost` 타입으로 변환하는 매핑 함수 작성 (`중요` checkbox → `important: boolean`)

**공통 레이아웃 컴포넌트**
- [ ] `components/layout/Header.tsx`: 사이트명, 네비게이션 링크
- [ ] `components/layout/Footer.tsx`: 저작권 정보, 링크
- [ ] `app/layout.tsx`에 `Header`, `Footer` 연결

**완료 기준**

- [ ] `getPosts()` 호출 시 Notion DB에서 발행된 글 목록이 반환됨
- [ ] `getImportantPosts()` 호출 시 `중요=true` 글이 3~5개 범위로 반환됨
- [ ] `getPostBlocks()` 호출 시 페이지 블록 배열이 반환됨
- [ ] `Header`, `Footer`가 모든 페이지에 렌더링됨
- [ ] TypeScript 컴파일 오류 없음

---

### Phase 2: 핵심 기능 개발 (예상 소요: 4일)

**목표**
서비스의 핵심인 글 목록 페이지, 글 상세 페이지, Notion 블록 렌더러를 구현합니다. MVP의 핵심 가치를 제공하는 단계입니다.

**왜 이 순서인가**
Phase 1에서 완성된 API 모듈과 레이아웃을 기반으로, 사용자가 실제로 콘텐츠를 볼 수 있는 페이지를 만듭니다. 검색·필터 기능(Phase 3)보다 먼저 콘텐츠 표시가 완성되어야 합니다.

**작업 항목**

**글 목록 페이지 (`app/page.tsx`)**
- [ ] `getPosts()` 호출 후 ISR 설정 (`revalidate: 3600`)
- [ ] `PostCard` 컴포넌트 작성 (`components/PostCard.tsx`)
  - 제목, 카테고리 배지, 태그, 발행일, 중요 배지 표시
  - 글 상세 페이지 링크 연결
- [ ] `중요=true` 글을 홈 최상단 중요 섹션에 먼저 표시
- [ ] 글 목록 그리드 레이아웃 구성 (반응형: 1열 → 2열 → 3열)
- [ ] 빈 상태(글이 없을 때) UI 처리
- [ ] 페이지네이션 구현 (또는 무한 스크롤 선택)

**글 상세 페이지 (`app/posts/[slug]/page.tsx`)**
- [ ] `generateStaticParams()`: 빌드 시 모든 발행된 글의 slug 생성
- [ ] `generateMetadata()`: 글 제목·설명 기반 OG 메타데이터 생성
- [ ] `getPostBySlug()`, `getPostBlocks()` 호출 후 ISR 설정
- [ ] 이전 글 / 다음 글 네비게이션 구현
- [ ] 글 헤더: 제목, 카테고리, 태그, 발행일 표시

**Notion 블록 렌더러 (`components/NotionRenderer.tsx`)**
- [ ] 지원 블록 타입별 렌더링 구현
  - `paragraph`: 일반 텍스트
  - `heading_1`, `heading_2`, `heading_3`: 제목
  - `bulleted_list_item`, `numbered_list_item`: 목록
  - `code`: 코드 블록 (언어 구문 강조)
  - `image`: 이미지 (`next/image` 사용, WebP 변환)
  - `quote`: 인용문
  - `divider`: 구분선
  - `callout`: 콜아웃 박스
- [ ] 지원하지 않는 블록 타입 fallback 처리

**완료 기준**

- [ ] 홈 페이지에서 `중요=true` 섹션과 발행된 글 목록이 정상 표시됨
- [ ] 글 카드 클릭 시 상세 페이지로 이동됨
- [ ] Notion 페이지 블록이 웹에서 올바르게 렌더링됨
- [ ] 이미지가 `next/image`로 최적화되어 표시됨
- [ ] 이전/다음 글 네비게이션이 동작함
- [ ] sm/md/lg 브레이크포인트에서 레이아웃이 올바르게 반응함

---

### Phase 3: 추가 기능 개발 (예상 소요: 3일)

**목표**
검색과 카테고리 필터링 기능을 추가하여 사용자가 원하는 콘텐츠를 빠르게 찾을 수 있게 합니다.

**왜 이 순서인가**
핵심 기능(콘텐츠 표시)이 완성된 후에 탐색 기능을 올려야 합니다. 데이터가 없는 상태에서 검색·필터 UI를 먼저 만들면 검증이 불가능합니다.

**작업 항목**

**검색 기능 (`components/SearchBar.tsx`)**
- [ ] 검색 입력 UI 컴포넌트 작성
- [ ] 제목 기반 키워드 실시간 필터링 구현 (클라이언트 사이드)
- [ ] 디바운스 처리 (입력 후 300ms 지연)
- [ ] 검색 결과 없을 때 안내 메시지 표시
- [ ] URL 쿼리 파라미터(`?q=keyword`)와 검색 상태 동기화

**카테고리 필터링 (`components/CategoryFilter.tsx`)**
- [ ] 카테고리 탭/버튼 UI 컴포넌트 작성
- [ ] URL 파라미터(`?category=AI`)로 선택 상태 유지
- [ ] 선택된 카테고리 강조 스타일
- [ ] `전체` 선택 시 모든 글 표시

**카테고리별 글 목록 페이지 (`app/category/[category]/page.tsx`)**
- [ ] `generateStaticParams()`: 카테고리 목록으로 정적 경로 생성
- [ ] 해당 카테고리 글만 필터링하여 목록 표시
- [ ] 페이지 제목에 카테고리명 표시
- [ ] ISR 설정 (`revalidate: 3600`)

**완료 기준**

- [ ] 검색어 입력 시 제목 기반으로 글 목록이 즉시 필터링됨
- [ ] 카테고리 선택 시 URL이 변경되고 해당 글만 표시됨
- [ ] 페이지 새로고침 후에도 카테고리/검색 상태가 URL로 유지됨
- [ ] `/category/AI` 접근 시 AI 카테고리 글만 표시됨

---

### Phase 4: 최적화 및 배포 (예상 소요: 2일)

**목표**
성능 요구사항(LCP 2.5초 이하)을 충족하고, Vercel에 배포하여 실제 서비스를 운영합니다.

**왜 이 순서인가**
기능이 모두 완성된 후 최적화를 진행해야 병목 지점을 정확히 파악할 수 있습니다. 배포는 최적화 검증 후 진행하는 것이 안전합니다.

**작업 항목**

**성능 최적화**
- [ ] `next/image`로 모든 이미지 최적화 (WebP 변환, lazy loading)
- [ ] Lighthouse 성능 측정 및 LCP 2.5초 이하 확인
- [ ] ISR `revalidate: 3600` 설정 전체 페이지 적용 확인
- [ ] 불필요한 클라이언트 컴포넌트 서버 컴포넌트로 전환 검토
- [ ] `next/font`로 웹폰트 최적화 (레이아웃 시프트 방지)

**SEO 및 메타데이터**
- [ ] `app/layout.tsx`에 기본 OG 메타데이터 설정
- [ ] 각 글 상세 페이지 `generateMetadata()` 완성
- [ ] `robots.txt`, `sitemap.xml` 생성 (`app/robots.ts`, `app/sitemap.ts`)

**배포**
- [ ] GitHub 저장소에 코드 push
- [ ] Vercel 프로젝트 생성 및 GitHub 연동
- [ ] Vercel 환경 변수 설정 (`NOTION_API_KEY`, `NOTION_DATABASE_ID`)
- [ ] 프로덕션 빌드 성공 확인 (`npm run build`)
- [ ] 배포된 URL에서 전체 기능 동작 검증

**완료 기준**

- [ ] Lighthouse LCP 2.5초 이하
- [ ] Vercel 프로덕션 배포 성공
- [ ] 모든 페이지(`/`, `/posts/[slug]`, `/category/[category]`)가 실제 URL에서 정상 동작
- [ ] 환경 변수가 프로덕션에서 올바르게 참조됨
- [ ] `sitemap.xml`이 정상 생성됨

---

## 마일스톤

| 마일스톤 | 완료 기준 | 예상 완료 시점 |
|---------|----------|--------------|
| M0: 개발 환경 구축 | 로컬 서버 기동 및 Tailwind 동작 확인 | Phase 0 완료 후 |
| M1: Notion 연동 완료 | API 호출로 글 목록 데이터 수신 확인 | Phase 1 완료 후 |
| M2: MVP 완성 | 글 목록 및 상세 페이지 정상 동작 | Phase 2 완료 후 |
| M3: 전체 기능 완성 | 검색·카테고리 필터 포함 모든 기능 동작 | Phase 3 완료 후 |
| M4: 프로덕션 배포 | Vercel 배포 및 성능 기준 충족 | Phase 4 완료 후 |

---

## 전체 예상 일정 요약

| Phase | 내용 | 예상 소요 |
|-------|------|----------|
| Phase 0 | 프로젝트 초기 설정 | 1일 |
| Phase 1 | 공통 모듈 및 레이아웃 | 2일 |
| Phase 2 | 핵심 기능 개발 | 4일 |
| Phase 3 | 추가 기능 개발 | 3일 |
| Phase 4 | 최적화 및 배포 | 2일 |
| **합계** | | **약 12일** |

---

## 리스크 및 고려사항

**Notion API 제한**
- Notion API는 분당 3회 요청 제한이 있습니다. ISR과 SSG를 적극 활용하여 런타임 API 호출을 최소화합니다.
- 블록 콘텐츠가 많은 글은 페이지 빌드 시간이 길어질 수 있으므로, `generateStaticParams`에서 조회할 글 수를 제한할 수 있습니다.

**Notion 블록 타입 다양성**
- Notion은 30개 이상의 블록 타입을 지원합니다. MVP에서는 주요 블록 타입만 지원하고, 지원하지 않는 블록은 명확한 fallback UI를 제공합니다.

**이미지 도메인 설정**
- Notion의 이미지 URL은 `prod-files-secure.s3.us-west-2.amazonaws.com` 등 외부 도메인을 사용합니다. `next.config.ts`의 `images.remotePatterns`에 해당 도메인을 등록해야 합니다.

**Slug 전략**
- Notion 페이지 ID를 slug로 사용하면 URL이 가독성이 낮습니다. `Title` 필드를 slug로 변환하거나, 별도 `Slug` 프로퍼티를 Notion DB에 추가하는 것을 권장합니다.

**환경 변수 보안**
- `NOTION_API_KEY`는 서버 사이드에서만 참조해야 합니다. `NEXT_PUBLIC_` 접두사 없이 유지하여 클라이언트에 노출되지 않도록 합니다.

---

## MVP 제외 항목 (추후 개발)

| 기능 | 이유 |
|------|------|
| 댓글 기능 | 별도 백엔드 또는 외부 서비스 연동 필요 |
| 다크 모드 | shadcn/ui 테마 설정 후 추가 가능 |
| RSS 피드 | `app/feed.xml/route.ts`로 추후 구현 |

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-06-05 | v1.0 | PRD.md 기반 초기 로드맵 생성 |
