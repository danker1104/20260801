# 🍽️ 뭐 먹을래? Frontend

위치 기반 식당 추천 서비스의 프론트엔드 (HTML/CSS/JavaScript)

## 📋 기술 스택

- **HTML5**: 시맨틱 마크업
- **CSS3**: Glassmorphism 디자인, Flexbox/Grid 반응형 레이아웃
- **JavaScript (ES6+)**: 비동기 처리, 이벤트 핸들링
- **Leaflet v1.9+**: 지도 라이브러리
- **Leaflet Marker Cluster**: 마커 클러스터링

## 📁 프로젝트 구조

```
frontend/
├── index.html              # 메인 HTML 파일
├── css/
│   └── styles.css         # 전역 스타일 (Glassmorphism, 반응형)
├── js/
│   ├── utils.js           # 유틸리티 함수 (포맷팅, 거리 계산)
│   ├── api.js             # API 호출 래퍼 (fetch)
│   ├── map.js             # Leaflet 지도 관리
│   └── app.js             # 메인 애플리케이션 로직
└── README.md              # 이 파일
```

## 🎨 UI/UX 특징

### Glassmorphism 디자인
- 반투명 배경에 블러 효과 (backdrop-filter)
- 부드러운 색상 팔레트:
  - **Primary**: #3447AA (파란색)
  - **Soft Surface**: #FBEAEB (분홍색)
  - **Background**: #F8FAFC (밝은 회색)
  - **Text**: #1F2A44 (어두운 파란색)

### 반응형 레이아웃
- **데스크톱** (769px+):
  - 2열 레이아웃 (지도 60% | 리스트 40%)
  - 고정 네비게이션 바
  
- **모바일** (768px 이하):
  - 탭 기반 레이아웃 (지도 / 리스트)
  - 기본 탭: 지도 우선
  - 마지막 탭 상태 복원

### 접근성
- 대비 4.5:1 이상 (WCAG AA)
- 터치 대상 44px 이상
- 키보드 네비게이션 지원
- 시맨틱 HTML 구조

## 🚀 실행 방법

### 1단계: 백엔드 실행
```bash
cd backend
pip install -r requirements.txt
python main.py
# 서버 시작: http://localhost:8000
# API 문서: http://localhost:8000/docs
```

### 2단계: 프론트엔드 실행
```bash
# 간단한 HTTP 서버 실행 (Python 3)
cd frontend
python -m http.server 3000

# 또는 Node.js http-server
npx http-server -p 3000

# 브라우저에서 열기
# http://localhost:3000
```

## 📡 API 통신

### 백엔드 엔드포인트
- **기본 URL**: 로컬 개발은 `http://localhost:8000/api`, 배포는 프론트 origin의 `/api`
- **인증**: 서버가 발급한 익명 Bearer 토큰을 `Authorization` 헤더로 전달

### 주요 API
1. **주변 식당 검색**
   ```
   GET /restaurants/nearby?latitude=37.4979&longitude=127.0276&category=한식
   응답: { restaurants: [...] }
   ```

2. **식당 상세 조회**
   ```
   GET /restaurants/{id}
   ```

3. **리뷰 작성/업데이트**
   ```
   POST /restaurants/{id}/reviews
   Body: { rating: 5, content: "맛있습니다!" }
   Header: Authorization: Bearer {accessToken}
   ```

4. **리뷰 목록 조회**
   ```
   GET /restaurants/{id}/reviews?skip=0&limit=20
   ```

5. **리뷰 삭제**
   ```
   DELETE /restaurants/{id}/reviews/{reviewId}
   Header: Authorization: Bearer {accessToken}
   ```

## 🎯 주요 기능

### 1. 지도 기반 식당 검색
- 현위치를 기반으로 1km 내 식당 검색
- 마커 클러스터링으로 많은 마커 최적화
- 줌/팬 제어로 지도 탐색
- 마커 클릭 시 식당 상세 팝업

### 2. 카테고리 필터링
- 전체, 한식, 일식, 중식, 양식, 카페
- 실시간 리스트 업데이트
- 모바일/데스크톱 동기화

### 3. 정렬 옵션
- **추천순**: 거리(40%) + 외부평점(30%) + 리뷰평점(30%)
- **거리순**: 현위치에서의 거리

### 4. 식당 상세 정보
- 이름, 주소, 카테고리
- 평균 평점, 리뷰 수
- 추천 점수 및 거리

### 5. 리뷰 시스템
- 별점(1~5) + 텍스트 리뷰
- 사용자별 단일 리뷰 정책 (업데이트 지원)
- 리뷰 목록 조회 및 삭제
- 본인 리뷰만 삭제 가능

### 6. 상태 유지
- 서버 발급 익명 인증 토큰은 페이지 메모리에만 보관
- 마지막 탭 상태 복원 (모바일)
- 무한 스크롤 지원 (구현 예정)

## 🔧 환경 설정

### 필수 환경 변수 (백엔드 .env)
```
SK_TMAP_API_KEY=YOUR_KEY
DATABASE_URL=sqlite:///./sg_food.db
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
DEBUG=False
AUTH_SECRET=CHANGE_ME_TO_A_LONG_RANDOM_SECRET
FRONTEND_URL=http://localhost:3000
```

### 프론트엔드 설정 (js/api.js)
```javascript
const API_BASE_URL = window.APP_CONFIG.api.baseURL;
const API_TIMEOUT = 10000; // 10초
```

## 🎮 사용 시나리오

### 시나리오 1: 초기 진입
1. 페이지 로드
2. 위치 권한 요청
3. 지도 표시 (기본: 강남역)
4. 현위치 주변 식당 로드
5. 식당 마커 표시 및 리스트 렌더링

### 시나리오 2: 식당 검색 및 필터링
1. 카테고리 칩 클릭
2. 식당 목록 실시간 업데이트
3. 정렬 옵션 변경 (추천순/거리순)
4. 리스트에서 식당 선택 또는 지도 마커 클릭

### 시나리오 3: 리뷰 작성
1. 식당 상세 모달 열기
2. 별점 선택 (1~5)
3. 리뷰 텍스트 입력 (선택사항)
4. "리뷰 작성" 버튼 클릭
5. 성공 토스트 표시
6. 리뷰 목록 갱신

### 시나리오 4: 모바일 네비게이션
1. 초기: 지도 탭 활성화
2. 탭 버튼 또는 토글로 전환
3. 마지막 탭 상태 저장 (localStorage)
4. 페이지 재진입 시 마지막 탭 복원

## ⚙️ 개발자 도구

### 브라우저 콘솔 디버깅
```javascript
// 현위치 확인
console.log(currentLocation);

// 로드된 식당 목록
console.log(restaurants);

// 선택된 식당
console.log(selectedRestaurant);

// 사용자 ID
console.log(userId);
```

### Leaflet 지도 디버깅
```javascript
// 지도 줌 레벨 확인
console.log(mapDesktop.getZoom());

// 지도 중심 확인
console.log(mapDesktop.getCenter());

// 모든 마커 확인
console.log(currentMarkers);
```

## 🐛 알려진 제약사항

1. **위치 권한**: 거부 시 기본값(강남역)으로 설정
2. **API 타임아웃**: 10초 초과 시 오류
3. **마커 클러스터**: 많은 식당(500+)일 때 성능 저하 가능
4. **모바일 지도**: 초기 로드 시 크기 조정 필요 (invalidateSize)

## 📱 테스트 체크리스트

- [ ] 데스크톱 브라우저에서 지도 + 리스트 2열 표시
- [ ] 모바일 브라우저에서 탭 토글 동작
- [ ] 위치 권한 요청 및 지도 표시
- [ ] 카테고리 필터링 실시간 작동
- [ ] 정렬 옵션 변경 시 리스트 업데이트
- [ ] 식당 클릭 시 상세 모달 열림
- [ ] 별점 선택 및 리뷰 작성 동작
- [ ] 리뷰 삭제 권한 검증
- [ ] 토스트 알림 표시 (성공/오류)
- [ ] 모바일 탭 상태 복원 (새로고침 후)

## 🚀 성능 최적화 (향후)

- [ ] 무한 스크롤 구현 (가상 스크롤)
- [ ] 이미지 레이지 로드
- [ ] Service Worker 캐싱
- [ ] 웹팩 번들링
- [ ] gzip 압축
- [ ] CDN 배포

## 📚 참고 자료

- [Leaflet 공식 문서](https://leafletjs.com/)
- [OpenStreetMap](https://www.openstreetmap.org/)
- [Glassmorphism Design](https://www.uxdesigninstitute.com/blog/glassmorphism/)
- [WCAG 2.2 접근성 가이드](https://www.w3.org/WAI/WCAG22/quickref/)

