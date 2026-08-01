# PRD: GD-Food

## 1. 제품 개요
- 목적: 앱 진입 즉시 지도 기반 탐색을 제공하고, 1km 추천으로 빠르게 식당을 선택하게 한다.
- 아키텍처: 단일 웹 아키텍처(모놀리식)

## 2. 문제 정의
낯선 지역에서 텍스트 목록 중심 탐색은 위치 감각이 부족해 선택까지 시간이 길어진다.

## 3. 제품 목표
1. 앱 진입 즉시 지도 노출
2. 현재 위치 1km 식당 추천
3. 카테고리 기반 맞춤 추천
4. 자체 리뷰 기반 추천 품질 향상

## 4. 전제 조건
1. 로그인 완료 상태를 가정한다.
2. 인증 UI/인증 로직은 범위에서 제외한다.
3. userId는 클라이언트 입력으로 받지 않고, 서버 세션 또는 신뢰 가능한 내부 헤더에서 주입한다.

## 5. 기술 및 연동
1. 프론트엔드: HTML, CSS, JavaScript
2. 백엔드: Python FastAPI
3. 데이터베이스: PostgreSQL (개발/테스트 SQLite 가능)
4. 외부 API: SK Open API

## 6. 기능 요구사항
### FR-01 진입 즉시 지도 노출
1. 앱 접속 후 첫 렌더링에서 지도를 먼저 보여준다.
2. 위치 권한 미승인 상태에서도 기본 중심 지도를 표시한다.
3. 위치 권한 미허용 시 nearby API는 호출하지 않는다.
4. 위치 권한 허용 후에만 nearby API를 호출한다.

### FR-02 위치 기반 추천
1. lat/lng 기준 반경 1km 식당 조회
2. 거리순/추천순 정렬

### FR-03 카테고리 추천
1. 카테고리 선택 시 지도 핀/리스트 동시 갱신

### FR-04 자체 리뷰
1. 리뷰 작성/조회
2. 리뷰 통계 추천 점수 반영

## 7. 핵심 API
1. GET /api/restaurants/nearby
- query: lat, lng, radius=1000, category(optional), sort(optional)

2. GET /api/restaurants/{restaurantId}/reviews
- query: page(optional), size(optional)

3. POST /api/restaurants/{restaurantId}/reviews
- body: rating(1~5), content
- userId는 서버 세션 또는 신뢰 가능한 내부 헤더에서 주입

## 8. 추천 로직
- recommendScore = 0.4 x distanceScore + 0.3 x externalScore + 0.3 x reviewScore

## 9. MVP 범위
포함:
1. 첫 진입 지도 노출
2. 1km 식당 조회
3. 카테고리 필터
4. 리뷰 작성/조회

제외:
1. 로그인 구현
2. 예약/결제
3. 실시간 혼잡도

## 10. 성공 기준
1. 첫 화면 지도 노출 성공률 100%
2. 1km 필터 정확 동작
3. 카테고리 필터 결과 일관성
4. 리뷰 반영 정상 동작

## 11. 디자인 핵심 요구사항
1. 콘셉트: Modern Card Map
2. 핵심 컬러: #3447AA, #FBEAEB
3. 레이아웃: 데스크톱 지도 60%/리스트 40%
4. 모바일: 첫 진입 기본 탭은 지도이며, 지도/리스트 토글을 제공한다.
5. 모바일 상태 규칙: 첫 진입은 지도 탭, 이후에는 마지막 사용 탭 상태 유지

## 12. 데이터 무결성 및 보안 제약
1. Review.rating은 1~5 범위 체크 제약을 둔다.
2. Restaurant.externalId는 유니크 제약을 둔다.
3. Review는 restaurantId+userId 기준 중복 정책(단일 리뷰 후 수정) 적용한다.
4. 리뷰 저장과 ReviewStats 갱신은 단일 트랜잭션으로 처리한다.
5. 클라이언트가 userId를 임의 지정할 수 없도록 서버에서 사용자 식별을 강제한다.