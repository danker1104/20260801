/**
 * kakao-map-loader.js - 카카오 Maps API SDK 동적 로드
 * 
 * 카카오 Maps JavaScript API를 동적으로 로드하고,
 * 로드 완료 후 전역 이벤트를 발생시켜
 * 다른 스크립트에서 지도를 초기화할 수 있도록 합니다.
 */

(function() {
    'use strict';

    // 설정 가져오기 (config.js에서 설정됨)
    function getKakaoApiKey() {
        if (typeof window.APP_CONFIG !== 'undefined' && window.APP_CONFIG.kakao) {
            return window.APP_CONFIG.kakao.apiKey;
        }
        // 폴백: 전역 변수에서 찾기
        return typeof KAKAO_MAPS_API_KEY !== 'undefined' ? KAKAO_MAPS_API_KEY : null;
    }

    /**
     * 카카오 Maps SDK 로드
     */
    function loadKakaoMapsSDK() {
        return new Promise((resolve, reject) => {
            const apiKey = getKakaoApiKey();

            // API 키 검증
            if (!apiKey || apiKey === 'YOUR_KAKAO_JAVASCRIPT_API_KEY_HERE') {
                const errorMsg = 
                    '❌ 카카오 Maps API 키를 설정해주세요.\n' +
                    '1. 카카오디벨로퍼스(https://developers.kakao.com)에서 JavaScript 키를 발급받으세요.\n' +
                    '2. frontend/js/config.js의 KAKAO_MAPS_API_KEY에 설정하세요.\n' +
                    '3. 도메인은 http://localhost:3000 으로 등록해야 합니다.';
                
                console.error(errorMsg);
                console.warn('[KakaoMapLoader] 카카오 Maps API 키가 없어 지도를 로드할 수 없습니다.');
                reject(new Error(errorMsg));
                return;
            }

            // 이미 로드되었는지 확인
            if (window.kakao && window.kakao.maps) {
                console.log('[KakaoMapLoader] 카카오 Maps API가 이미 로드되었습니다.');
                // 이벤트가 아직 발생하지 않았을 수 있으니 발생시킴
                dispatchKakaoMapsReadyEvent();
                resolve(window.kakao.maps);
                return;
            }

            // SDK 로드 URL 생성
            // autoload=false 사용 후 kakao.maps.load()에서 초기화 완료 시점을 보장한다.
            const scriptUrl = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(apiKey)}&autoload=false&libraries=services`;

            // 디버깅: SDK URL 출력
            console.log('[KakaoMapLoader] SDK URL:', scriptUrl);
            console.log('[KakaoMapLoader] API 키 (처음 8글자):', apiKey.substring(0, 8) + '***');

            // 스크립트 엘리먼트 생성
            const script = document.createElement('script');
            script.src = scriptUrl;
            script.async = false;  // ← 동기 로드로 변경 (카카오 SDK 권장)
            script.defer = false;

            // 로드 타임아웃 설정 (10초)
            const timeout = setTimeout(() => {
                console.error('[KakaoMapLoader] ❌ SDK 로드 타임아웃 (10초 초과)');
                console.error('[KakaoMapLoader] 🔍 카카오 Developer Console 확인 필수:');
                console.error('  1. https://developers.kakao.com/console/app 접속');
                console.error('  2. "SG-Food" 앱 클릭');
                console.error('  3. "서비스" 탭 클릭');
                console.error('  4. "지도(Maps)" 서비스 "활성화" 버튼 클릭 (중요!)');
                console.error('  5. 페이지 새로고침 (Ctrl+Shift+R)');
                reject(new Error('SDK 로드 타임아웃 - 지도 서비스 활성화 필요'));
            }, 10000);

            // 오류 처리
            script.onerror = (error) => {
                clearTimeout(timeout);
                const errorDetails = error?.message || String(error);
                const errorMsg = `❌ 카카오 Maps API 로드 실패: ${errorDetails}`;
                console.error('[KakaoMapLoader]', errorMsg);
                console.error('[KakaoMapLoader] 🔍 카카오 Developer Console 확인:');
                console.error('  1. ⚠️ "서비스" 탭 → "지도(Maps)" 서비스 활성화 필수!');
                console.error('  2. API 키 재확인: ' + scriptUrl);
                console.error('  3. "플랫폼" 탭 → http://localhost:3000 도메인 등록 확인');
                console.error('  4. Network 탭: 404/403 상태 코드 확인');
                reject(error);
            };

            // 성공 이벤트
            script.onload = () => {
                console.log('[KakaoMapLoader] 스크립트 로드 완료, kakao.maps.load 실행...');

                if (window.kakao?.maps?.load) {
                    window.kakao.maps.load(() => {
                        clearTimeout(timeout);
                        console.log('[KakaoMapLoader] ✅ 카카오 Maps API 로드 완료');
                        resolve(window.kakao.maps);
                        dispatchKakaoMapsReadyEvent();
                    });
                } else if (window.kakao?.maps) {
                    // 예외적 환경에서 load 함수가 없더라도 maps 객체가 있으면 진행
                    clearTimeout(timeout);
                    console.log('[KakaoMapLoader] ✅ 카카오 Maps API 로드 완료 (fallback)');
                    resolve(window.kakao.maps);
                    dispatchKakaoMapsReadyEvent();
                } else {
                    clearTimeout(timeout);
                    reject(new Error('카카오 Maps 객체를 찾을 수 없습니다'));
                }
            };

            // DOM에 추가
            document.head.appendChild(script);
            console.log('[KakaoMapLoader] 카카오 Maps API 로드 시작...');
        });
    }

    /**
     * 카카오 Maps 준비 완료 이벤트 발생
     */
    function dispatchKakaoMapsReadyEvent() {
        const event = new CustomEvent('kakaoMapsReady', {
            detail: {
                kakao: window.kakao,
                maps: window.kakao.maps,
                timestamp: new Date().toISOString(),
            }
        });
        document.dispatchEvent(event);
        console.log('[KakaoMapLoader] kakaoMapsReady 이벤트 발생');
    }

    /**
     * 로드 시작 (DOM이 준비된 후)
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadKakaoMapsSDK);
    } else {
        // DOM이 이미 준비된 경우
        loadKakaoMapsSDK().catch((error) => {
            console.error('[KakaoMapLoader] SDK 로드 중 오류:', error);
            // 에러를 화면에도 표시
            showMapError(error);
        });
    }

    /**
     * 지도 로딩 오류 화면에 표시
     */
    function showMapError(error) {
        const mapContainer = document.getElementById('map');
        if (mapContainer) {
            mapContainer.innerHTML = `
                <div style="
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100%;
                    background: #f5f5f5;
                    color: #d32f2f;
                    padding: 20px;
                    text-align: center;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                ">
                    <div style="font-size: 48px; margin-bottom: 16px;">❌</div>
                    <h3 style="margin: 0 0 8px 0; font-size: 18px;">지도를 로드할 수 없습니다</h3>
                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #666;">
                        ${error.message || '카카오 Maps API 로드 실패'}
                    </p>
                    <p style="margin: 0; font-size: 12px; color: #999;">
                        브라우저의 개발자도구(F12) 콘솔을 확인하세요.
                    </p>
                </div>
            `;
        }
    }

    // 전역에 로더 함수 노출
    window.loadKakaoMapsSDK = loadKakaoMapsSDK;
    window.KakaoMapLoader = {
        load: loadKakaoMapsSDK,
    };

    console.log('[KakaoMapLoader] 카카오맵 로더 초기화됨');
})();
