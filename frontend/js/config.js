/**
 * config.js - 프론트엔드 설정
 * 
 * .env 파일의 환경변수를 프론트엔드에서 사용하기 위한 설정 파일
 * 주의: 정적 파일 서버 환경에서 .env를 직접 읽을 수 없으므로,
 *       개발 시작 전에 아래 값들을 직접 설정하거나
 *       빌드 스크립트를 통해 자동으로 생성되어야 합니다.
 */

// ===== 개발 환경에서는 여기에 카카오 API 키를 직접 설정합니다 =====
// .env 파일의 KAKAO_MAPS_API_KEY 값을 여기에 복사하세요
const KAKAO_MAPS_API_KEY = 'YOUR_KAKAO_JAVASCRIPT_API_KEY_HERE';

// API 기본 설정
const API_CONFIG = {
    baseURL: 'http://localhost:8000/api',
    timeout: 10000,
};

// 지도 기본 설정
const MAP_CONFIG = {
    // 카카오맵 기본 중심 좌표 (서울 강남역)
    // 프론트엔드에서 사용자 위치로 자동 갱신됨
    center: {
        lat: 37.4979,
        lng: 127.0276,
    },
    // 기본 줌 레벨
    zoom: 13,
    // 최대/최소 줌 레벨
    maxZoom: 20,
    minZoom: 6,
};

/**
 * 설정 검증
 */
function validateConfig() {
    if (KAKAO_MAPS_API_KEY === 'YOUR_KAKAO_JAVASCRIPT_API_KEY_HERE') {
        console.warn(
            '⚠️  주의: 카카오 Maps API 키가 설정되지 않았습니다.\n' +
            '다음 방법으로 설정하세요:\n' +
            '1. frontend/js/config.js에서 KAKAO_MAPS_API_KEY를 설정하거나\n' +
            '2. .env 파일의 KAKAO_MAPS_API_KEY를 설정하고 build를 실행하세요.\n' +
            'https://developers.kakao.com 에서 JavaScript 키를 발급받을 수 있습니다.'
        );
        return false;
    }
    return true;
}

// 페이지 로드 시 설정 검증
window.addEventListener('DOMContentLoaded', () => {
    validateConfig();
});

// 글로벌 설정 객체 노출
window.APP_CONFIG = {
    kakao: {
        apiKey: KAKAO_MAPS_API_KEY,
    },
    api: API_CONFIG,
    map: MAP_CONFIG,
};
