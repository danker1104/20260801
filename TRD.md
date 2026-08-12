# TRD: SG-Food 기술 아키텍처

## 1. 문서 목적
이 문서는 SG-Food의 기술 아키텍처 단일 기준 문서다.
제품 요구사항, UX 요구사항, 운영 목표의 원문 기준은 PRD.md를 따른다.

## 2. 아키텍처 원칙
1. 아키텍처 스타일: 모놀리식 웹 애플리케이션
2. 지도 우선 진입 플로우를 지원하는 구조를 유지한다.
3. 권한/보안 경계(userId 서버 주입)는 계층 전반에서 강제한다.
4. 데이터 무결성 제약은 DB 레벨에서 보장한다.

## 3. 기술 스택
### 3.1 프론트엔드
1. 언어: HTML, CSS, JavaScript (ES6+)
2. 지도 라이브러리: Leaflet (v1.9+)
   - 설치: npm install leaflet leaflet.markercluster
   - 타일 서비스: OpenStreetMap (기본)
   - 마커 클러스터링: Leaflet.markercluster
3. HTTP 클라이언트: fetch API

### 3.2 백엔드
1. 프레임워크: Python FastAPI (v0.100+)
2. 외부 API 클라이언트: requests 라이브러리
3. 환경 변수: python-dotenv

### 3.3 데이터베이스
1. 프로덕션: PostgreSQL (v13+)
2. 개발/테스트: SQLite 허용

### 3.4 외부 연동
1. SK Open API (T-Map POI 검색)
   - 엔드포인트: https://apis.openapi.sk.com/tmap/pois
   - 인증: API 키 (환경 변수: SK_TMAP_API_KEY)

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
1. GET /api/restaurants/nearby (쿼리 파라미터: lat, lng, radius=1000)

2. 백엔드 처리 흐름:
   
   a) SK T-Map POI 검색 API 호출
      - 엔드포인트: https://apis.openapi.sk.com/tmap/pois
      - 메서드: GET
      - 인증: appKey (환경 변수 SK_TMAP_API_KEY)
      - 필수 요청 파라미터:
        ```
        version=1
        searchType=all (전체 검색)
        reqCoordType=WGS84GEO (요청 좌표계)
        resCoordType=WGS84GEO (응답 좌표계)
        searchKeyword=음식점 (또는 카테고리별 검색)
        page=1
        count=20 (기본값, 조정 가능)
        ```
      - 선택 파라미터:
        ```
        multiPoint=N
        searchtypCd=A
        poiGroupYn=N
        ```
   
   b) SK API 응답 파싱
      - 응답 형식 (JSON):
        ```json
        {
          "searchPoiInfo": {
            "totalCount": 총_식당_수,
            "count": 반환된_개수,
            "pois": {
              "poi": [
                {
                  "id": "SKT_POI_ID_12345",
                  "name": "식당명",
                  "noorLat": 위도,
                  "noorLon": 경도,
                  "frontLat": 입구_위도,
                  "frontLon": 입구_경도,
                  "lowerAddrName": "상세주소",
                  "middleAddrName": "시군구",
                  "upperAddrName": "시도",
                  "telNo": "전화번호",
                  "firstBuildYear": "건축연도"
                }
              ]
            }
          }
        }
        ```
   
   c) 내부 Restaurant 모델로 변환
      - 매핑 규칙:
        ```
        Restaurant {
          externalId: poi.id (외부 ID)
          name: poi.name (식당명)
          lat: poi.noorLat (건물 위도)
          lng: poi.noorLon (건물 경도)
          address: poi.lowerAddrName (주소)
          category: 카테고리 분류 로직 적용
          externalRating: null (T-Map에는 평점 없음)
          createdAt: 현재시각
          updatedAt: 현재시각
        }
        ```
   
   d) DB에 upsert (중복 제거)
      - Restaurant.externalId 기준으로 존재 여부 확인
      - 존재하면 updatedAt만 갱신
      - 없으면 신규 삽입
   
   e) 거리 계산 (Haversine 공식)
      - 사용자 좌표(lat, lng)와 Restaurant(lat, lng) 사이의 거리 계산
      - 결과: distanceScore 계산에 사용 (섹션 12 참고)
   
   f) 리뷰 통계 결합
      - 각 Restaurant마다 ReviewStats 조회
      - ReviewStats 없으면 기본값 (reviewCount=0, reviewAvg=0)
      - reviewScore 계산
   
   g) 추천 점수 계산 (섹션 12 참고)
      - recommendScore = 0.4 * distanceScore + 0.3 * externalScore + 0.3 * reviewScore
   
   h) 정렬 및 응답
      - 기본: 추천순 (recommendScore DESC)
      - 옵션: 거리순 (distance ASC)
      - 응답 포맷 (추천순으로 정렬된 리스트)

3. 성능 목표
   - SK API 응답: ~500ms (네트워크 지연 포함)
   - DB 처리/계산: ~200ms
   - 전체 p95: 800ms 이내
   - 실패 시: 최대 2회 재시도 (섹션 9.2 참고)

4. 지도 핀/리스트 동기화 응답 반환
   - 프론트엔드는 응답을 받아 지도 핀 표시 및 리스트 렌더링

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
2. Review.rating 범위: 1~5 정수 (소수점 불가)
   - CHECK (rating >= 1 AND rating <= 5 AND rating = CAST(rating AS INTEGER))
   - 예: 1점, 2점, 3점, 4점, 5점만 허용
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

## 11. 디자인 스펙
### 11.1 핵심 컬러 및 Glassmorphism 스타일
#### 컬러 팔레트
- Primary: #3447AA
- Soft Surface: #FBEAEB
- Text: #1F2A44
- Background: #F8FAFC
- Border: #D9E0EE

#### Glassmorphism 스타일 가이드
1. 기본 개념
   - 반투명 배경(backdrop-filter)과 흐릿한 효과로 유리잔 효과 구현
   - 계층감과 현대적 비주얼 제공

2. 적용 요소
   - 카드(식당 카드, 리뷰 카드): backdrop-filter blur(10px), opacity 0.8
   - 모달/오버레이: backdrop-filter blur(8px), opacity 0.85
   - 필터/정렬 바: backdrop-filter blur(12px), opacity 0.9
   - 상단 바(nav): backdrop-filter blur(12px), opacity 0.92

3. CSS 구현 예시
   ```css
   .glass-card {
     background: rgba(248, 250, 252, 0.8);
     backdrop-filter: blur(10px);
     border: 1px solid rgba(217, 224, 238, 0.5);
     border-radius: 16px;
     box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
   }
   ```

4. 대비 및 접근성
   - 텍스트 레이어 대비 유지: Text 색상(#1F2A44) on Glassmorphic surface
   - 최소 대비 4.5:1 확보
   - 포커스 상태 명확히 표시(어두운 테두리 또는 강조색)

### 11.2 첫 화면 규칙
1. 페이지 로드 후 first viewport 주요 영역은 지도여야 한다.
2. 데스크톱은 초기 상태에서 지도 패널 visible.
3. 모바일은 기본 탭을 지도(Map)로 시작.
4. 위치 권한 미허용이어도 기본 지도 + 권한 안내 오버레이 표시.
5. 첫 진입 이후에는 사용자의 마지막 탭 상태(지도/리스트)를 유지한다.

### 11.3 레이아웃 상세
#### 데스크톱
1. 상단 고정 바
2. 본문 2열: 지도 60%, 리스트 40%
3. 필터/정렬 sticky

#### 모바일
1. 상단 지도/리스트 토글
2. 기본 선택은 지도
3. 하단 내 주변 다시 검색 CTA
4. 재방문/새로고침 시 마지막 탭 상태를 우선 복원

### 11.4 핵심 화면 구성
1. 홈: 지도 먼저 렌더링, 이후 1km 리스트 로드
2. 카테고리: 칩 선택 시 지도 핀/리스트 동시 갱신
3. 상세: 요약 카드 + 리뷰 탭 + 리뷰 작성 박스 상단 배치

### 11.5 컴포넌트 최소 스펙
1. 식당 카드: 이름, 거리, 카테고리, 종합점수, 리뷰 수
2. 카테고리 칩: 높이 36px, radius 18px
3. 점수 배지: 숫자 강조
4. 리뷰 작성: 별점 + 텍스트 + 등록 버튼

### 11.6 상태 및 인터랙션
1. Loading: 지도 선표시 + 리스트 스켈레톤
2. Empty: 1.5km 확장 검색 CTA
3. Error: 재시도 및 안내 문구
4. 카테고리 변경: 리스트 crossfade + 선택 핀 강조

### 11.7 접근성 상세
1. 대비 4.5:1 이상
2. 터치 대상 44px 이상
3. 포커스 링 명확히 표시

### 11.8 콘텐츠 톤
- 짧고 선택 친화적 문장
- 예시: 가까운 순, 리뷰 좋은 순, 지금 이 동네 인기

## 12. 추천 계산 아키텍처
1. 추천 점수 공식
- recommendScore = 0.4 * distanceScore + 0.3 * externalScore + 0.3 * reviewScore
2. 정규화 규칙
- distanceScore: 가까울수록 높은 값
- externalScore: 외부 평점 기반 0~1 정규화
- reviewScore: 내부 리뷰 평점 기반 0~1 정규화

## 13. Agent Skills 운영 기준
이 절은 본 프로젝트 문서/구현 작업에서 사용하는 Skills의 적용 시점과 작성 대상을 정의한다.

### 13.1 기본 사용 Skills (Global)
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

### 13.2 추가 설치 Skills
1. fastapi-templates
- 무엇을 작성/수행할 때: FastAPI 프로젝트 구조, 라우터/서비스/스키마 분리, 예외 처리/DI 패턴 적용
- 언제 사용할지: 백엔드 API 구현 시작 시, 신규 엔드포인트 추가 시, 구조 리팩터링 시

2. accessibility
- 무엇을 작성/수행할 때: WCAG 2.2 기준 점검, 키보드 탐색/포커스/대비/대체 텍스트 개선안 작성
- 언제 사용할지: 화면 구현 후 QA 단계, 배포 전 접근성 점검 단계

### 13.3 단계별 사용 순서
1. 기획/문서 단계
- find-skills, writing-guidelines 우선 적용

2. UI 설계/구현 단계
- frontend-design으로 설계 후 web-design-guidelines와 accessibility로 검증

3. 백엔드 구현 단계
- fastapi-templates 우선 적용 후 writing-guidelines로 API 문서 품질 정리

4. 배포 전 검증 단계
- web-design-guidelines, accessibility, writing-guidelines 순으로 최종 점검

### 13.4 운영 원칙
1. 기능 구현 전에 어떤 Skill을 적용할지 먼저 선언한다.
2. Skill 적용 결과는 PR 설명 또는 변경 문서에 근거로 남긴다.
3. 동일 요구를 반복할 때는 검증된 Skill 조합을 재사용한다.