# 🍽️ SG-Food 카카오맵 JavaScript SDK 연동 가이드

## 📋 개요

카카오 Maps JavaScript API를 사용하여 실시간 위치 기반 식당 추천 서비스를 제공합니다.

- **지도**: 카카오맵
- **SDK 로드**: 동적 로드 (kakao-map-loader.js)
- **API 키 관리**: 환경변수 (.env)
- **반응형**: 데스크톱 및 모바일 지원

---

## 🚀 빠른 시작

### 1단계: 카카오 API 키 발급받기

1. **카카오디벨로퍼스 이동**
   - 사이트: https://developers.kakao.com
   - 로그인 또는 회원가입

2. **JavaScript 키 발급**
   - "애플리케이션" → "SG-Food" 앱 클릭
   - "키" 탭에서 JavaScript 키 복사

3. **⚠️ 중요: 지도(Maps) 서비스 활성화**
   - "서비스" 탭 클릭
   - "지도(Maps)" 서비스 우측의 **활성화** 클릭
   - ✅ 상태가 "활성"으로 변경되는지 확인
   - **이 단계를 빠뜨리면 "NotAuthorizedError" 오류가 발생합니다!**

4. **도메인 등록** (이미 완료됨)
   - "플랫폼" 탭 → "Web" 클릭
   - 도메인: `http://localhost:3000` 등록됨 ✅

### 2단계: 환경변수 설정

**파일: `.env`**

```env
# 기존 설정 유지...

# 카카오 Maps API 키 추가
KAKAO_MAPS_API_KEY=YOUR_KAKAO_JAVASCRIPT_API_KEY_HERE
```

### 3단계: 프론트엔드 설정

**파일: `frontend/js/config.js`**

```javascript
// .env의 KAKAO_MAPS_API_KEY 값을 복사하여 이 값을 설정
const KAKAO_MAPS_API_KEY = 'YOUR_KAKAO_JAVASCRIPT_API_KEY_HERE';
```

---

## 🔧 설정 파일 설명

### `frontend/js/config.js`
- **목적**: 프론트엔드 설정 중앙화
- **주요 변수**:
  - `KAKAO_MAPS_API_KEY`: 카카오 JavaScript API 키
  - `API_CONFIG`: 백엔드 API 기본 URL
  - `MAP_CONFIG`: 지도 기본 설정 (중심 좌표, 줌 레벨)

### `frontend/js/kakao-map-loader.js`
- **목적**: 카카오 Maps SDK 동적 로드
- **기능**:
  - SDK 로드 완료 대기
  - 오류 처리 및 화면 표시
  - `kakaoMapsReady` 이벤트 발생

### `frontend/js/map.js`
- **목적**: 지도 초기화 및 마커 관리 (Leaflet → 카카오맵 변환)
- **주요 함수**:
  - `initMapDesktop()`: 데스크톱 지도 초기화
  - `initMapMobile()`: 모바일 지도 초기화
  - `addRestaurantMarkers()`: 식당 마커 추가
  - `refreshMap()`: 지도 새로고침

---

## ✅ 테스트하기

### 테스트 페이지

브라우저에서 다음 URL로 이동:
```
http://localhost:3000/kakao-map-test.html
```

**테스트 항목**:
- ✅ 카카오 API 키 설정 여부
- ✅ SDK 로드 성공 여부
- ✅ 지도 초기화 성공 여부
- ✅ SDK 기능 테스트

### 브라우저 콘솔 확인

개발자도구 (F12) → Console 탭에서 다음 메시지 확인:
```
[KakaoMapLoader] 카카오 Maps API 로드 시작...
[KakaoMapLoader] ✅ 카카오 Maps API 로드 완료
[Map] 카카오맵 준비 완료
[Map Desktop] 지도 생성 완료
```

---

## 🐛 오류 해결

### 문제 1: "API 키가 설정되지 않았습니다" 오류

**원인**: `config.js`에서 `KAKAO_MAPS_API_KEY` 값이 설정되지 않음

**해결**:
```javascript
// ❌ 잘못된 설정
const KAKAO_MAPS_API_KEY = 'YOUR_KAKAO_JAVASCRIPT_API_KEY_HERE';

// ✅ 올바른 설정
const KAKAO_MAPS_API_KEY = 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'; // 실제 키
```

### 문제 2: "도메인이 등록되지 않았습니다" 오류

**원인**: 카카오디벨로퍼스에서 도메인이 등록되지 않음

**해결**:
1. https://developers.kakao.com 접속
2. 애플리케이션 선택 → "플랫폼" 탭
3. "Web" 추가 또는 수정
4. 도메인 입력: `http://localhost:3000`
5. 저장

### 문제 3: "NotAuthorizedError" 또는 "지도 서비스를 활성화하세요"

**원인**: 카카오 Developer Console에서 "지도(Maps)" 서비스가 비활성화됨

**해결**:
1. https://developers.kakao.com/console/app 접속
2. 앱 목록에서 "SG-Food" 앱 클릭
3. **"서비스" 탭** 클릭
4. "지도(Maps)" 항목의 **"활성화" 버튼 클릭**
5. ✅ 상태가 "활성"으로 변경되는지 확인
6. 페이지 새로고침 후 다시 테스트

**중요**: 이 단계를 빠뜨리면 모든 설정이 완료되어도 지도가 작동하지 않습니다!

### 문제 4: "Cannot read property 'maps' of undefined"

**원인**: kakao 객체가 로드되지 않음

**해결**:
- `kakaoMapsReady` 이벤트 대기 확인
- SDK 로드 상태 콘솔 로그 확인
- 네트워크 탭에서 SDK 스크립트 로드 상태 확인

---

## 📦 배포 시 주의사항

### 1. 환경변수 관리
- 프로덕션 환경에서는 안전한 환경변수 저장소 사용
- CI/CD 파이프라인에서 자동으로 주입

### 2. 도메인 등록
```
로컬 개발: http://localhost:3000
개발 서버: https://dev.example.com
프로덕션: https://www.example.com
```

### 3. API 키 보안
- JavaScript 키는 클라이언트에 노출되므로 안전함
- REST API 사용 시 Server 키 사용 (다른 보안 정책)

### 4. CORS 설정
- 백엔드 CORS 설정 확인 (main.py의 FRONTEND_URL)
- 프론트엔드는 이미 설정됨 (config.js의 API_CONFIG)

---

## 🗂️ 파일 구조

```
frontend/
├── js/
│   ├── config.js              # 설정 파일 (카카오 API 키)
│   ├── kakao-map-loader.js    # SDK 동적 로더
│   ├── map.js                 # 지도 관리 (카카오맵 기반)
│   ├── app.js                 # 애플리케이션 로직
│   ├── api.js                 # API 호출
│   └── utils.js               # 유틸리티
├── css/
│   └── styles.css             # 스타일
├── index.html                 # 메인 페이지
└── kakao-map-test.html        # 테스트 페이지
```

---

## 📚 참고자료

- **카카오 Maps API**: https://developers.kakao.com/docs/latest/ko/maps/common
- **카카오 API 키**: https://developers.kakao.com/console/app
- **기술 지원**: https://kakao-developers-asia.slack.com

---

## 🔄 다음 단계

현재 구현된 기능:
- ✅ 카카오맵 표시
- ✅ 지도 오류 처리
- ✅ 반응형 지도
- ✅ 현재 위치 기능 준비

향후 추가 예정:
- 🔄 식당 마커 표시 (현재 테스트 데이터 사용)
- 🔄 실시간 위치 추적
- 🔄 식당 검색 필터
- 🔄 리뷰 기능

---

**마지막 업데이트**: 2026-08-08  
**버전**: 1.0.0 (카카오맵 SDK 통합)
