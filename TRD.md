# TRD: GD-Food 기술 아키텍처

## 1. 문서 목적
이 문서는 GD-Food의 기술 아키텍처 단일 기준 문서다.
제품 요구사항, UX 요구사항, 운영 목표의 원문 기준은 PRD.md를 따른다.

## 2. 아키텍처 원칙
1. 아키텍처 스타일: 모놀리식 웹 애플리케이션
2. 지도 우선 진입 플로우를 지원하는 구조를 유지한다.
3. 권한/보안 경계(userId 서버 주입)는 계층 전반에서 강제한다.
4. 데이터 무결성 제약은 DB 레벨에서 보장한다.

## 3. 기술 스택
1. 프론트엔드: HTML, CSS, JavaScript
2. 백엔드: Python FastAPI
3. 데이터베이스: PostgreSQL (개발/테스트는 SQLite 허용)
4. 외부 연동: SK Open API

## 4. 시스템 구조
1. Web UI 계층
- 지도/리스트/필터/리뷰 화면 렌더링
- 위치 권한 요청 및 사용자 인터랙션 처리
2. API 서버 계층
- 주변 식당 조회, 리뷰 처리, 추천 계산
- 외부 API 응답 정규화 및 내부 모델 변환
3. 데이터 계층
- Restaurant, Review, ReviewStats 저장
- 제약조건/트랜잭션/인덱스 기반 정합성 유지

## 5. 요청 흐름 아키텍처
### 5.1 초기 진입
1. 지도 우선 렌더링
2. 위치 권한 요청
3. 허용 시 nearby API 호출
4. 미허용 시 nearby API 미호출, 안내 상태 유지

### 5.2 주변 조회
1. GET /api/restaurants/nearby
2. SK Open API 조회 및 응답 정규화
3. 리뷰 통계 결합 + 추천 점수 계산
4. 지도 핀/리스트 동기화 응답 반환

### 5.3 리뷰 쓰기
1. POST /api/restaurants/{restaurantId}/reviews
2. 서버 인증 컨텍스트에서 userId 추출
3. 리뷰 upsert
4. ReviewStats 트랜잭션 갱신

## 6. 인터페이스 아키텍처
### 6.1 API 엔드포인트
1. GET /api/restaurants/nearby
2. GET /api/restaurants/{restaurantId}/reviews
3. POST /api/restaurants/{restaurantId}/reviews

### 6.2 계약 원칙
1. Base Path: /api
2. Content-Type: application/json
3. 시간 형식: ISO-8601 UTC
4. 공통 에러 응답: code, message, traceId

## 7. 데이터베이스 아키텍처
### 7.1 핵심 엔터티
1. Restaurant
2. Review
3. ReviewStats

### 7.2 무결성 제약
1. Restaurant.externalId UNIQUE
2. Review.rating CHECK (1~5)
3. Review(restaurantId, userId) UNIQUE
4. 리뷰 upsert + 통계 갱신 단일 트랜잭션

### 7.3 인덱스 전략
1. Restaurant(lat, lng)
2. Restaurant(category)
3. Review(restaurantId, createdAt desc)

## 8. 보안 아키텍처
1. userId는 클라이언트 입력을 신뢰하지 않는다.
2. userId는 서버 세션/신뢰 가능한 내부 헤더에서 주입한다.
3. 외부 API 키는 서버 환경 변수로만 관리한다.
4. 입력값 타입/범위/길이 검증을 서버에서 강제한다.

## 9. 비기능 아키텍처
### 9.1 성능 목표
1. 첫 지도 표시 p95 1.5초 이내
2. nearby API 응답 p95 800ms 이내
3. 리뷰 저장 응답 p95 500ms 이내

### 9.2 안정성 목표
1. SK API 실패 시 최대 2회 재시도
2. 재시도 실패 시 fallback 응답
3. 5xx 에러율 1% 미만 목표

### 9.3 관측성
1. 필수 로그: traceId, endpoint, latencyMs, statusCode
2. 주요 메트릭: nearby 실패율, 권한 허용률, 리뷰 등록 성공률

## 10. UI/UX 아키텍처
### 10.1 디자인 원칙
1. 지도 우선 진입(first viewport 지도)
2. 지도/리스트 동시 탐색
3. 카드 기반 빠른 비교

### 10.2 레이아웃 구조
1. 데스크톱: 지도 60%, 리스트 40%
2. 모바일: 지도/리스트 토글
3. 모바일 첫 진입 기본 탭: 지도
4. 재방문/새로고침: 마지막 탭 상태 복원

### 10.3 상태/인터랙션 구조
1. Loading: 지도 선노출 + 리스트 스켈레톤
2. Empty: 반경 확장 CTA
3. Error: 재시도 버튼 + 안내 문구
4. 카테고리 변경: 핀/리스트 동기 갱신

### 10.4 접근성
1. 대비 4.5:1 이상
2. 터치 대상 44px 이상
3. 포커스 링 명확히 표시

## 11. 추천 계산 아키텍처
1. 추천 점수 공식
- recommendScore = 0.4 * distanceScore + 0.3 * externalScore + 0.3 * reviewScore
2. 정규화 규칙
- distanceScore: 가까울수록 높은 값
- externalScore: 외부 평점 기반 0~1 정규화
- reviewScore: 내부 리뷰 평점 기반 0~1 정규화

## 12. Agent Skills 운영 기준
이 절은 본 프로젝트 문서/구현 작업에서 사용하는 Skills의 적용 시점과 작성 대상을 정의한다.

### 12.1 기본 사용 Skills (Global)
1. find-skills
- 무엇을 작성/수행할 때: 신규 작업에 필요한 Skill 후보 조사, 설치 대상 선정 근거 정리
- 언제 사용할지: 새 작업 착수 전, 기존 Skill로 해결이 어려운 요구가 나온 시점

2. frontend-design
- 무엇을 작성/수행할 때: 지도 우선 UI 구조, 카드/필터/토글 레이아웃, 시각 방향 제안
- 언제 사용할지: 화면 구조 초안 수립 시, UI 개편안 작성 시

3. web-design-guidelines
- 무엇을 작성/수행할 때: 접근성, 반응형, 상호작용 규칙 점검 결과 작성
- 언제 사용할지: UI 스펙 리뷰, PR 전 점검, 릴리스 전 품질 확인 시

4. writing-guidelines
- 무엇을 작성/수행할 때: PRD/TRD/Design 문장 품질 개선, 용어 통일, 모호성 제거
- 언제 사용할지: 문서 수정 직후, 릴리스 노트/가이드 정리 시

### 12.2 추가 설치 Skills
1. fastapi-templates
- 무엇을 작성/수행할 때: FastAPI 프로젝트 구조, 라우터/서비스/스키마 분리, 예외 처리/DI 패턴 적용
- 언제 사용할지: 백엔드 API 구현 시작 시, 신규 엔드포인트 추가 시, 구조 리팩터링 시

2. accessibility
- 무엇을 작성/수행할 때: WCAG 2.2 기준 점검, 키보드 탐색/포커스/대비/대체 텍스트 개선안 작성
- 언제 사용할지: 화면 구현 후 QA 단계, 배포 전 접근성 점검 단계

### 12.3 단계별 사용 순서
1. 기획/문서 단계
- find-skills, writing-guidelines 우선 적용

2. UI 설계/구현 단계
- frontend-design으로 설계 후 web-design-guidelines와 accessibility로 검증

3. 백엔드 구현 단계
- fastapi-templates 우선 적용 후 writing-guidelines로 API 문서 품질 정리

4. 배포 전 검증 단계
- web-design-guidelines, accessibility, writing-guidelines 순으로 최종 점검

### 12.4 운영 원칙
1. 기능 구현 전에 어떤 Skill을 적용할지 먼저 선언한다.
2. Skill 적용 결과는 PR 설명 또는 변경 문서에 근거로 남긴다.
3. 동일 요구를 반복할 때는 검증된 Skill 조합을 재사용한다.