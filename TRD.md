# TRD: GD-Food 기술 요구사항

## 1. 문서 목적
이 문서는 GD-Food의 구현 기준을 정의한다.
PRD, 아키텍처, 디자인 문서를 기술 관점에서 통합한다.
핵심 UX는 앱 진입 즉시 지도 노출이다.
## 2. 제품 요약
1. 서비스명: GD-Food
2. 문제: 위치 맥락 없는 목록 탐색은 의사결정이 느리다.
3. 목표: 지도 우선 탐색, 1km 추천, 카테고리 필터, 리뷰 기반 보정
4. 핵심 경험: 앱 오픈 즉시 주변 맥락 파악 후 빠르게 식당 선택
## 3. 범위
### 3.1 포함 범위 (MVP)
1. 첫 진입 지도 우선 렌더링
2. 위치 기반 주변 식당 조회
3. 카테고리/정렬 필터
4. 리뷰 작성/조회
5. 리뷰 통계 기반 추천 점수 반영
### 3.2 제외 범위
1. 로그인/회원가입
2. 결제/예약
3. 실시간 혼잡도
4. 관리자 화면
## 4. 전제 조건
1. 사용자는 로그인 완료 상태다.
2. 인증 UI/로직은 본 범위에서 제외한다.
3. userId는 서버 세션 또는 신뢰 가능한 내부 헤더에서 주입한다.
4. 외부 식당 데이터는 SK Open API를 사용한다.
## 5. 기술 스택
1. 프론트엔드: HTML, CSS, JavaScript
2. 백엔드: Python FastAPI
3. DB: PostgreSQL (개발/테스트는 SQLite 허용)
4. 아키텍처: 모놀리식 웹 애플리케이션
## 6. 시스템 구성
1. Web UI: 지도/리스트/필터/리뷰 화면
2. API 서버: 조회, 리뷰 처리, 추천 점수 계산
3. 데이터 계층: Restaurant, Review, ReviewStats 저장
4. 외부 연동 계층: SK Open API 호출 및 응답 변환
## 7. 핵심 플로우
### 7.1 첫 진입
1. 앱 진입 시 지도 먼저 렌더링
2. 위치 권한 요청
3. 권한 허용 시 nearby API 호출
4. 권한 미허용 시 nearby API 미호출
5. 미허용 시 기본 지도 + 안내 메시지 + 재시도 버튼 제공
### 7.2 모바일 상태 규칙
1. 첫 진입 기본 탭은 지도
2. 이후에는 마지막 탭 상태(지도/리스트) 유지
## 8. 기능 요구사항
### FR-01 지도 우선 초기 화면
1. 첫 viewport에 지도 노출
2. 지도 로드 실패 시 오류 배너와 재시도 제공
### FR-02 주변 식당 추천
1. 기본 반경 1000m
2. 정렬: recommend(기본), distance
3. 지도 핀과 리스트 데이터는 항상 동일 집합 유지
### FR-03 카테고리 필터
1. 카테고리: 한식, 중식, 일식, 양식, 카페, 기타
2. 필터 변경 시 재조회
3. 필터 변경 시 페이지 초기화
### FR-04 리뷰
1. 식당당 사용자 1리뷰 정책
2. 재작성 시 upsert 처리
3. rating은 1~5 정수
4. 저장 후 통계 즉시 갱신
## 9. API 계약
### 9.1 공통
1. Base Path: /api
2. Content-Type: application/json
3. 시간 형식: ISO-8601 UTC
4. 공통 에러 응답: code, message, traceId
### 9.2 GET /api/restaurants/nearby
1. 설명: 좌표 중심 주변 식당 조회
2. Query
- lat, lng: 필수
- radius: 선택, 기본 1000
- category: 선택
- sort: 선택, recommend | distance
- page: 선택, 기본 1
- size: 선택, 기본 20, 최대 50
3. 성공(200): items, page, size, total
4. 실패 코드
- 400: 파라미터 검증 실패
- 429: 외부 API 한도 초과
- 502: 외부 API 장애
### 9.3 GET /api/restaurants/{restaurantId}/reviews
1. Query: page(기본 1), size(기본 10, 최대 30)
2. 성공(200): items, page, size, total
3. 실패 코드: 400, 404
### 9.4 POST /api/restaurants/{restaurantId}/reviews
1. Body: rating, content
2. userId는 body에서 받지 않는다.
3. 성공 코드
- 201: 신규 생성
- 200: 기존 수정
4. 실패 코드
- 400: 입력 검증 실패
- 404: 대상 식당 없음
- 409: 동시성 충돌
## 10. 데이터 모델
### 10.1 Restaurant
1. id: PK
2. externalId: UNIQUE, NOT NULL
3. name, category: NOT NULL
4. lat, lng: NOT NULL
5. address, externalRating
6. createdAt, updatedAt
### 10.2 Review
1. id: PK
2. restaurantId: FK
3. userId: NOT NULL
4. rating: CHECK (1~5)
5. content: NOT NULL
6. createdAt, updatedAt
7. UNIQUE(restaurantId, userId)
### 10.3 ReviewStats
1. restaurantId: PK/FK
2. reviewCount
3. reviewAvg
4. lastReviewAt
### 10.4 트랜잭션/인덱스
1. 리뷰 upsert + 통계 갱신은 단일 트랜잭션
2. 실패 시 전체 롤백
3. 인덱스
- Restaurant(lat, lng)
- Restaurant(category)
- Review(restaurantId, createdAt desc)
## 11. 추천 로직
1. 공식
- recommendScore = 0.4 * distanceScore + 0.3 * externalScore + 0.3 * reviewScore
2. 정규화
- distanceScore: 가까울수록 높음
- externalScore: 외부 평점 기반 0~1
- reviewScore: 내부 평균 평점 기반 0~1
3. 동점 처리: 거리 오름차순 우선
## 12. UI/UX 요구사항
### 12.1 레이아웃
1. 데스크톱: 지도 60%, 리스트 40%
2. 모바일: 지도/리스트 토글
3. 핵심 컬러: #3447AA, #FBEAEB
### 12.2 상태 처리
1. Loading: 지도 우선 노출, 리스트 스켈레톤
2. Empty: 반경 확장 CTA 제공
3. Error: 원인별 메시지 + 재시도 버튼
### 12.3 접근성
1. 텍스트 대비 4.5:1 이상
2. 터치 타깃 최소 44x44px
3. 키보드 포커스 표시
## 13. 보안 요구사항
1. 클라이언트 userId 입력은 신뢰하지 않는다.
2. userId는 서버 인증 컨텍스트로 강제 주입한다.
3. 외부 API 키는 서버 환경 변수로만 관리한다.
4. 입력값은 타입/범위/길이 검증을 적용한다.
5. 로그는 개인정보를 마스킹한다.
## 14. 비기능 요구사항
### 14.1 성능
1. 첫 지도 표시 p95 1.5초 이내
2. nearby API 응답 p95 800ms 이내
3. 리뷰 저장 응답 p95 500ms 이내
### 14.2 안정성
1. SK API 실패 시 최대 2회 재시도
2. 재시도 실패 시 사용자 재시도 경로 제공
3. 5xx 에러율 1% 미만 목표
### 14.3 관측성
1. 필수 로그: traceId, endpoint, latencyMs, statusCode
2. 주요 메트릭
- nearby 호출/실패율
- 권한 허용률
- 리뷰 등록 성공률
## 15. 테스트 전략
### 15.1 단위 테스트
1. 추천 점수 계산
2. rating/content 검증
3. 권한 상태별 nearby 호출 여부
### 15.2 통합 테스트
1. nearby 필터/정렬/페이지네이션
2. 리뷰 upsert 트랜잭션
3. 에러 코드/응답 포맷
### 15.3 E2E 테스트
1. 권한 허용 첫 진입 흐름
2. 권한 미허용 첫 진입 흐름
3. 모바일 탭 상태 복원
4. 리뷰 재작성 반영
## 16. 구현 순서
1. 지도 우선 진입 + 권한 분기
2. nearby API + 추천 정렬
3. 카테고리/페이지네이션
4. 리뷰 upsert + 통계 반영
5. 상태/접근성/오류 처리
6. 계측 로그/메트릭 연결
## 17. 배포 체크리스트
1. 환경 변수(SK API Key, DB URL) 확인
2. DB 마이그레이션 적용
3. OpenAPI 문서 최신화
4. 주요 E2E 통과 확인
## 18. 수용 기준
1. 첫 진입 시 지도 우선 노출 100%
2. 권한 미허용 상태 nearby API 호출 0건
3. 지도/리스트 데이터 불일치 0건
4. 리뷰 중복 생성 0건
5. 통계 반영 불일치 0건
6. 실패 상황에서 재시도 경로 제공 100%