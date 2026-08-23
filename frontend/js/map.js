/**
 * map.js - 카카오 Maps 지도 초기화 및 관리
 * 
 * 기존 Leaflet API와 유사한 인터페이스를 유지하면서
 * 카카오맵 SDK를 사용하도록 구현되었습니다.
 */

let mapDesktop = null;
let mapMobile = null;
let desktopMarkers = [];
let mobileMarkers = [];
let selectedMarker = null;

// 카카오맵 준비 완료 대기
let kakaoMapsReady = false;
let kakaoMaps = null;
let kakaoSdk = null;

/**
 * 카카오맵 로드 완료 대기
 */
document.addEventListener('kakaoMapsReady', (event) => {
    kakaoSdk = event.detail.kakao;
    kakaoMaps = event.detail.maps;
    kakaoMapsReady = true;
    debugLog('[Map] 카카오맵 준비 완료');
    debugLog('[Map] window.kakao:', typeof window.kakao);
    debugLog('[Map] window.kakao.maps:', typeof window.kakao?.maps);
}, { once: false }); // once: false로 변경하여 여러 번 발생할 수 있음

// SDK가 이미 로드되었는지 즉시 확인
setTimeout(() => {
    if (window.kakao && window.kakao.maps && !kakaoMapsReady) {
        debugLog('[Map] SDK가 이미 로드됨 (이벤트 발생 전)');
        kakaoSdk = window.kakao;
        kakaoMaps = window.kakao.maps;
        kakaoMapsReady = true;
        // 다른 리스너들을 위해 이벤트 발생
        document.dispatchEvent(new CustomEvent('kakaoMapsReady', {
            detail: { kakao: window.kakao, maps: window.kakao.maps }
        }));
    }
}, 100);

/**
 * 카카오맵이 준비될 때까지 대기
 */
function waitForKakaoMaps() {
    return new Promise((resolve, reject) => {
        // 이미 준비되었으면 즉시 반환
        if (kakaoMapsReady && kakaoMaps) {
            debugLog('[Map] 카카오맵이 이미 준비됨');
            resolve();
            return;
        }

        // 타임아웃 설정 (최대 10초)
        const timeout = setTimeout(() => {
            console.error('[Map] 카카오맵 로드 타임아웃 (10초 초과)');
            reject(new Error('카카오맵 로드 타임아웃'));
        }, 10000);

        // 이벤트 리스너 추가
        const handleKakaoReady = () => {
            clearTimeout(timeout);
            debugLog('[Map] kakaoMapsReady 이벤트 수신');
            resolve();
        };

        document.addEventListener('kakaoMapsReady', handleKakaoReady, { once: true });

        // SDK가 이미 로드되었는지 한 번 더 확인
        setTimeout(() => {
            if (kakaoMapsReady && kakaoMaps) {
                clearTimeout(timeout);
                document.removeEventListener('kakaoMapsReady', handleKakaoReady);
                resolve();
            }
        }, 100);
    });
}

/**
 * 지도 초기화 (데스크톱)
 */
async function initMapDesktop(latitude, longitude) {
    try {
        debugLog('[Map Desktop] 초기화 시작:', latitude, longitude);
        
        // 카카오맵이 준비될 때까지 대기
        debugLog('[Map Desktop] kakaoMapsReady 대기 중... kakaoMapsReady=', kakaoMapsReady);
        await waitForKakaoMaps();
        debugLog('[Map Desktop] waitForKakaoMaps() 완료');

        // 이미 초기화되었으면 중심만 변경
        if (mapDesktop) {
            const moveLatLng = new kakao.maps.LatLng(latitude, longitude);
            mapDesktop.setCenter(moveLatLng);
            debugLog('[Map Desktop] 지도 중심 이동:', latitude, longitude);
            return;
        }

        const mapContainer = document.getElementById('map');
        debugLog('[Map Desktop] 지도 컨테이너:', mapContainer ? 'found' : 'NOT FOUND');
        if (!mapContainer) {
            console.error('[Map Desktop] 지도 컨테이너를 찾을 수 없습니다: #map');
            return;
        }
        
        debugLog('[Map Desktop] 컨테이너 크기:', mapContainer.offsetWidth, 'x', mapContainer.offsetHeight);

        // 지도 옵션
        const mapOption = {
            center: new kakao.maps.LatLng(latitude, longitude),
            level: 5, // 카카오맵 줌 레벨 (1-14, 숫자가 작을수록 줌 in)
            mapTypeId: kakao.maps.MapTypeId.ROADMAP,
        };

        debugLog('[Map Desktop] kakao.maps:', typeof kakao?.maps, 'kakao.maps.Map:', typeof kakao?.maps?.Map);
        
        // 지도 생성
        mapDesktop = new kakao.maps.Map(mapContainer, mapOption);
        debugLog('[Map Desktop] 지도 생성 완료:', latitude, longitude);

        // 현재 위치 마커 추가
        addUserLocationMarker(mapDesktop, latitude, longitude);

        // 지도 로딩 표시 숨기기
        const mapLoading = document.getElementById('mapLoading');
        if (mapLoading) {
            mapLoading.style.display = 'none';
        }
    } catch (error) {
        console.error('[Map Desktop] 초기화 실패:', error);
        console.error('[Map Desktop] 스택:', error.stack);
        showMapError('데스크톱 지도 초기화 실패', error);
    }
}

/**
 * 지도 초기화 (모바일)
 */
async function initMapMobile(latitude, longitude) {
    try {
        // 카카오맵이 준비될 때까지 대기
        await waitForKakaoMaps();

        // 이미 초기화되었으면 중심만 변경
        if (mapMobile) {
            const moveLatLng = new kakao.maps.LatLng(latitude, longitude);
            mapMobile.setCenter(moveLatLng);
            debugLog('[Map Mobile] 지도 중심 이동:', latitude, longitude);
            return;
        }

        const mapContainer = document.getElementById('mapMobile');
        if (!mapContainer) {
            console.warn('[Map Mobile] 모바일 지도 컨테이너를 찾을 수 없습니다: #mapMobile');
            return;
        }

        // 지도 옵션
        const mapOption = {
            center: new kakao.maps.LatLng(latitude, longitude),
            level: 5,
            mapTypeId: kakao.maps.MapTypeId.ROADMAP,
        };

        // 지도 생성
        mapMobile = new kakao.maps.Map(mapContainer, mapOption);
        debugLog('[Map Mobile] 지도 생성 완료:', latitude, longitude);

        // 현재 위치 마커 추가
        addUserLocationMarker(mapMobile, latitude, longitude);

        // 지도 로딩 표시 숨기기
        const mapLoadingMobile = document.getElementById('mapLoadingMobile');
        if (mapLoadingMobile) {
            mapLoadingMobile.style.display = 'none';
        }
    } catch (error) {
        console.error('[Map Mobile] 초기화 실패:', error);
        showMapError('모바일 지도 초기화 실패', error);
    }
}

/**
 * 사용자 현위치 마커 추가
 */
function addUserLocationMarker(map, latitude, longitude) {
    try {
        // 커스텀 마커 오버레이
        const markerPosition = new kakao.maps.LatLng(latitude, longitude);

        const markerImageUrl = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSI4IiBmaWxsPSIjMzQ0N0FBIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiLz48L3N2Zz4=';

        const imageSize = new kakao.maps.Size(24, 24);
        const imageOption = { offset: new kakao.maps.Point(12, 12) };
        const markerImage = new kakao.maps.MarkerImage(markerImageUrl, imageSize, imageOption);

        const marker = new kakao.maps.Marker({
            position: markerPosition,
            image: markerImage,
            title: '현재 위치',
            zIndex: 3,
        });

        marker.setMap(map);
        debugLog('[Map] 현재 위치 마커 추가:', latitude, longitude);
    } catch (error) {
        console.error('[Map] 사용자 마커 추가 실패:', error);
    }
}

/**
 * 식당 마커 추가
 */
async function addRestaurantMarkers(map, restaurants) {
    try {
        if (!map) {
            console.warn('[Map] 지도 객체가 없습니다');
            return;
        }

        // 기존 마커 제거
        const markerArray = map === mapDesktop ? desktopMarkers : mobileMarkers;
        markerArray.forEach((marker) => marker.setMap(null));
        markerArray.length = 0;

        // 새 마커 추가
        restaurants.forEach((restaurant) => {
            const marker = createRestaurantMarker(restaurant);
            marker.setMap(map);
            markerArray.push(marker);
        });

        debugLog(`[Map] ${restaurants.length}개 식당 마커 추가 완료`);
    } catch (error) {
        console.error('[Map] 식당 마커 추가 실패:', error);
    }
}

/**
 * 식당 마커 생성
 */
function createRestaurantMarker(restaurant) {
    try {
        const reviewCount = Number(restaurant.reviewCount || 0);
        const markerLabel = reviewCount >= 10 ? '10+' : String(reviewCount);
        const scoreColor = '#E63946';

        // SVG 기반 마커 이미지
        const svgMarker = `
            <svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
                <circle cx="20" cy="20" r="18" fill="${scoreColor}" stroke="white" stroke-width="2"/>
                <text x="20" y="26" font-size="12" font-weight="bold" fill="white" text-anchor="middle">${markerLabel}</text>
            </svg>
        `;

        const imageUrl = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgMarker)));
        const imageSize = new kakao.maps.Size(40, 40);
        const imageOption = { offset: new kakao.maps.Point(20, 20) };
        const markerImage = new kakao.maps.MarkerImage(imageUrl, imageSize, imageOption);

        const position = new kakao.maps.LatLng(restaurant.lat, restaurant.lng);

        const marker = new kakao.maps.Marker({
            position: position,
            image: markerImage,
            title: restaurant.name,
            zIndex: 2,
        });

        // 마커 클릭 이벤트
        kakao.maps.event.addListener(marker, 'click', () => {
            selectedMarker = marker;
            handleMarkerClick(restaurant.id);
        });

        return marker;
    } catch (error) {
        console.error('[Map] 마커 생성 실패:', error);
        return null;
    }
}

/**
 * 마커 클릭 이벤트 핸들러
 */
function handleMarkerClick(restaurantId) {
    // 앱에서 처리하도록 이벤트 발생
    window.dispatchEvent(new CustomEvent('markerClick', { detail: { restaurantId } }));
}

/**
 * 특정 마커 하이라이트
 */
function highlightMarker(restaurantId) {
    // 카카오맵에서는 마커 스타일 변경 시 새 마커 이미지로 교체
    // 현재 구현: 정보 표시로 대체
    debugLog('[Map] 마커 하이라이트:', restaurantId);
}

/**
 * 지도 중심을 특정 식당으로 이동
 */
function centerMapOnRestaurant(restaurant, map) {
    try {
        if (!map) {
            console.warn('[Map] 지도 객체가 없습니다');
            return;
        }

        const centerPosition = new kakao.maps.LatLng(restaurant.lat, restaurant.lng);
        map.setCenter(centerPosition);
        map.setLevel(3); // 줌 인

        debugLog('[Map] 식당으로 중심 이동:', restaurant.name);
    } catch (error) {
        console.error('[Map] 중심 이동 실패:', error);
    }
}

/**
 * 지도 새로 고침 (마커 재로드)
 */
async function refreshMap(latitude, longitude, restaurants) {
    try {
        debugLog('[Map] 지도 새로고침:', latitude, longitude, restaurants.length, '개 식당');

        if (mapDesktop) {
            const moveLatLng = new kakao.maps.LatLng(latitude, longitude);
            mapDesktop.setCenter(moveLatLng);
            await addRestaurantMarkers(mapDesktop, restaurants);
        }

        if (mapMobile) {
            const moveLatLng = new kakao.maps.LatLng(latitude, longitude);
            mapMobile.setCenter(moveLatLng);
            await addRestaurantMarkers(mapMobile, restaurants);
        }
    } catch (error) {
        console.error('[Map] 지도 새로고침 실패:', error);
    }
}

/**
 * 지도 리사이즈 (윈도우 리사이즈 시)
 */
function resizeMap() {
    try {
        if (mapDesktop) {
            mapDesktop.relayout();
        }
        if (mapMobile) {
            mapMobile.relayout();
        }
        debugLog('[Map] 지도 리사이즈 완료');
    } catch (error) {
        console.error('[Map] 지도 리사이즈 실패:', error);
    }
}

/**
 * 지도 오류 표시
 */
function showMapError(title, error) {
    try {
        const errorDiv = document.querySelector('.map-error');
        if (errorDiv) {
            errorDiv.innerHTML = `<div>${title}</div><small>${error.message}</small>`;
            errorDiv.style.display = 'block';
        }
        console.error('[Map] 오류:', title, error);
    } catch (e) {
        console.error('[Map] 오류 표시 실패:', e);
    }
}

// 전역에 함수 노출
window.initMapDesktop = initMapDesktop;
window.initMapMobile = initMapMobile;
window.refreshMap = refreshMap;
window.resizeMap = resizeMap;
window.handleMarkerClick = handleMarkerClick;
window.centerMapOnRestaurant = centerMapOnRestaurant;

debugLog('[Map] 카카오맵 모듈 로드됨');
