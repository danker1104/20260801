# 뭐 먹을래? 웹 앱 기획서

## 1. 프로젝트 개요
- 웹 앱 이름: 뭐 먹을래?
- 한줄 소개: 앱 진입 즉시 지도를 보여주고, 현재 위치 1km 내 식당을 리뷰 기반으로 추천하는 서비스

## 2. 문제 정의
타지역에서는 식당 정보가 낯설어 빠르게 결정하기 어렵고, 텍스트 목록만으로는 위치 감각이 떨어진다.

## 3. 프로젝트 목적
지도 중심 첫 화면으로 위치 감각을 즉시 제공하고, 1km 추천과 카테고리 필터로 선택 시간을 줄인다.

## 4. 핵심 기능
1. 진입 즉시 지도 노출
- 앱 접속 직후 지도를 먼저 렌더링한다.
- 위치 권한 전에도 기본 중심 좌표 지도는 표시한다.
- 위치 권한 미허용 시 nearby API는 호출하지 않고, 지도+안내 문구만 노출한다.

2. 위치 기반 식당 추천
- 현재 위치 수집 후 반경 1km 식당 목록을 조회한다.
- 거리순/추천순 정렬을 지원한다.

3. 카테고리 맞춤 추천
- 카테고리 선택 시 지도 핀과 리스트를 동시에 갱신한다.

4. 앱 내 자체 리뷰
- 로그인 사용자 기준 리뷰 작성/조회
- 리뷰 통계를 추천 점수에 반영

## 5. 전제 조건
- 로그인은 완료된 상태를 가정한다.
- 인증 UI/인증 로직은 제외한다.
- userId는 클라이언트 입력으로 받지 않고, 서버 세션 또는 신뢰 가능한 내부 헤더에서 주입한다.

## 6. 기술 및 외부 연동

### 프론트엔드
- 언어: HTML, CSS, JavaScript (ES6+)
- 지도 라이브러리: Leaflet (v1.9+)
  - 설치: npm install leaflet leaflet.markercluster
  - 타일: OpenStreetMap
- 위치 수집: Geolocation API

### 백엔드
- 프레임워크: Python FastAPI (v0.100+)
- 외부 API 클라이언트: requests 라이브러리

### 데이터베이스
- 프로덕션: PostgreSQL (v13+)
- 개발/테스트: SQLite 허용

### 외부 API 연동
- **SK Open API (T-Map POI 검색)**
  - 엔드포인트: `https://apis.openapi.sk.com/tmap/pois?version=1`
  - 메서드: GET
  - 인증: API 키 (환경 변수 `SK_TMAP_API_KEY`)
  - 용도: 현재 위치 주변 음식점 POI 검색
  - 응답 형식: JSON (totalCount, pois.poi[] 배열)
  - 핵심 필드:
    - `poi.id`: 외부 식당 ID (externalId)
    - `poi.name`: 식당 이름
    - `poi.noorLat, poi.noorLon`: 위치 좌표
    - `poi.lowerAddrName`: 주소
  - 성능 목표: p95 500ms 이내
  - 재시도: 실패 시 최대 2회

## 7. 추천 로직 초안
- 종합점수 = 0.4 x 거리점수 + 0.3 x 외부평점점수 + 0.3 x 자체리뷰점수
- 거리점수: 가까울수록 높음
- 외부평점점수: SK Open API 평점 또는 대체 지표 정규화
- 자체리뷰점수: 평균 평점 + 리뷰 수 보정

## 8. 데이터 모델(초안)
1. Restaurant: id, externalId, name, category, lat, lng, address, externalRating
2. Review: id, restaurantId, userId, rating, content, createdAt
3. ReviewStats: restaurantId, reviewCount, reviewAvg, lastReviewAt

## 9. MVP 범위
포함:
- 앱 진입 즉시 지도 노출
- 1km 식당 조회
- 카테고리 필터 추천
- 리뷰 작성/조회

제외:
- 예약/결제
- 로그인 구현
- 실시간 혼잡도
- 이미지 리뷰 업로드

## 10. 사용자 흐름
1. 앱 접속 즉시 지도 확인
2. 위치 권한 허용 또는 미허용 상태 안내 확인
3. 1km 추천 목록/핀 확인
4. 카테고리 선택 후 결과 갱신
5. 상세에서 리뷰 조회/작성

## 11. 기대 효과
- 첫 화면 지도 노출로 즉시 위치 맥락 확보
- 추천/필터로 탐색 시간 단축
- 리뷰 축적으로 추천 품질 개선

## 12. 데이터 무결성/신뢰 경계
- 리뷰 작성 시 userId는 클라이언트 body에서 받지 않는다.
- userId는 서버 세션 또는 신뢰 가능한 내부 헤더에서만 주입한다.
- 리뷰 데이터는 식당별/사용자별 중복 정책과 평점 제약을 적용한다.
