/**
 * App - 메인 애플리케이션 로직
 * 실시간 위치 기반 식당 추천
 */

let currentLocation = { latitude: 37.4979, longitude: 127.0276 }; // 기본값: 서울 강남역
let restaurants = [];
let selectedRestaurant = null;
let currentCategory = '';
let currentSort = 'recommend';
let userId = null;
let locationWatchId = null;  // Geolocation watch ID
let detailModalTrigger = null;

function infoOrNone(value) {
    if (value === null || value === undefined) {
        return '정보 없음';
    }

    const text = String(value).trim();
    if (!text || text === '없음' || text === '없습니다.' || text === 'null' || text === 'undefined') {
        return '정보 없음';
    }

    return text;
}

function formatRecommendDisplay(score) {
    if (score === null || score === undefined || Number.isNaN(Number(score))) {
        return '평가 없음';
    }
    return formatScore(score);
}

/**
 * 페이지 로드 시 초기화
 */
document.addEventListener('DOMContentLoaded', async () => {
    try {
        userId = await initializeAuth();
    } catch (error) {
        console.error('인증 초기화 실패:', error);
        showError('서비스 인증을 초기화할 수 없습니다');
        return;
    }
    
    debugLog('🍽️ 뭐 먹을래? 애플리케이션 시작');
    debugLog('기본 위치(권한 거부 시 fallback):', currentLocation);
    debugLog('📺 뷰포트 크기:', window.innerWidth, 'x', window.innerHeight);
    
    // 위치 권한 요청 및 실시간 추적 시작
    debugLog('📍 위치 정보 요청 중...');
    try {
        await requestLocationPermission();
        debugLog('Location permission resolved');
    } catch (err) {
        console.error('Location permission error:', err);
    }
    
    debugLog('최종 위치:', currentLocation);

    // 반응형 레이아웃 확인
    debugLog('🔄 반응형 레이아웃 업데이트 시작');
    updateResponsiveLayout();
    debugLog('✅ 반응형 레이아웃 업데이트 완료');

    // 지도 초기화 (async 함수이므로 await 필요)
    try {
        await initMapDesktop(currentLocation.latitude, currentLocation.longitude);
        await initMapMobile(currentLocation.latitude, currentLocation.longitude);
        // 초기 렌더 시점의 레이아웃 계산이 늦는 브라우저를 위해 한 번 더 리사이즈 적용
        setTimeout(() => resizeMap(), 150);
        debugLog('✅ 지도 초기화 완료');
    } catch (err) {
        console.error('❌ 지도 초기화 실패:', err);
    }

    // 이벤트 리스너 등록
    setupEventListeners();

    // 초기 데이터 로드
    debugLog('Starting loadRestaurants...');
    await loadRestaurants();
    debugLog('loadRestaurants completed');
});

/**
 * Geolocation 권한 요청 및 실시간 위치 추적
 */
async function requestLocationPermission() {
    return new Promise((resolve) => {
        // 보안 컨텍스트 검사 (HTTP 접속 환경 등에서 브라우저 Geolocation API 차단 감지)
        if (window.isSecureContext === false) {
            console.warn('⚠️ 보안 연결(HTTPS 또는 localhost)이 아니므로 브라우저 정책상 위치 정보(Geolocation)가 제한됩니다.');
            debugLog('⚠️ 비보안 환경(HTTP): 기본 위치(강남역)로 Fallback 진행합니다.');
            resolve(currentLocation);
            return;
        }

        if (!('geolocation' in navigator)) {
            console.warn('⚠️  브라우저에서 Geolocation을 지원하지 않습니다');
            resolve(currentLocation);
            return;
        }

        const optionsHigh = {
            enableHighAccuracy: true,
            timeout: 10000, // 10초로 타임아웃 확장
            maximumAge: 0,
        };

        const optionsLow = {
            enableHighAccuracy: false, // GPS 수신 불량 시 Wi-Fi/네트워크 기반 시도
            timeout: 10000,
            maximumAge: 30000,
        };

        const handleSuccess = (position) => {
            currentLocation = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                accuracy: position.coords.accuracy,
            };
            debugLog('✅ 현재 위치 감지 성공:', currentLocation);
            
            // 실시간 위치 추적 시작
            startLocationTracking();
            resolve(currentLocation);
        };

        // 1차 고정밀 위치 요청
        navigator.geolocation.getCurrentPosition(
            handleSuccess,
            (error) => {
                console.warn('⚠️ 1차 고정밀 위치 조회 실패:', error.message, `(code: ${error.code})`);
                
                // 권한 거부가 아닌 타임아웃/수신 불가 시, 2차 네트워크 기반 시도
                if (error.code !== error.PERMISSION_DENIED) {
                    debugLog('🔄 네트워크/Wi-Fi 기반 2차 위치 조회 시도...');
                    navigator.geolocation.getCurrentPosition(
                        handleSuccess,
                        (fallbackErr) => {
                            console.warn('⚠️ 2차 위치 조회도 실패:', fallbackErr.message);
                            debugLog('⚠️ 기본 위치(강남역)로 Fallback 진행합니다.');
                            resolve(currentLocation);
                        },
                        optionsLow
                    );
                } else {
                    debugLog('⚠️ 위치 권한 거부됨. 기본 위치(강남역)로 Fallback 진행합니다.');
                    resolve(currentLocation);
                }
            },
            optionsHigh
        );
    });
}

/**
 * 현위치 1회 재조회 (새로고침 버튼 전용)
 * - 실내/저전력 환경에서 위치 타임아웃이 잦아 타임아웃을 늘리고 캐시 사용을 허용한다.
 */
async function requestCurrentLocationOnce() {
    return new Promise((resolve, reject) => {
        if (window.isSecureContext === false) {
            reject(new Error('보안 연결(HTTPS 또는 localhost)에서만 위치 정보 재조회가 가능합니다'));
            return;
        }

        if (!('geolocation' in navigator)) {
            reject(new Error('Geolocation을 지원하지 않는 브라우저입니다'));
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                });
            },
            (error) => reject(error),
            {
                // 버튼 클릭 재검색은 성공률이 중요하므로 캐시 허용 + 타임아웃 확장
                enableHighAccuracy: false,
                timeout: 15000,
                maximumAge: 60000,
            }
        );
    });
}

/**
 * 실시간 위치 추적 시작
 */
function startLocationTracking() {
    if (locationWatchId) {
        navigator.geolocation.clearWatch(locationWatchId);
    }

    debugLog('🎯 실시간 위치 추적 시작');

    locationWatchId = navigator.geolocation.watchPosition(
        (position) => {
            const newLocation = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                accuracy: position.coords.accuracy,
            };

            // 위치 변화 감지 (20m 이상 이동 시)
            const distance = calculateDistance(
                currentLocation.latitude,
                currentLocation.longitude,
                newLocation.latitude,
                newLocation.longitude
            );

            if (distance > 20) {
                debugLog(`📍 위치 변경 감지 (${distance.toFixed(0)}m)`);
                currentLocation = newLocation;

                // 지도 중심 및 내 위치 마커 갱신
                if (typeof window.updateUserLocation === 'function') {
                    window.updateUserLocation(currentLocation.latitude, currentLocation.longitude);
                } else {
                    if (window.mapDesktop) {
                        const moveLatLng = new kakao.maps.LatLng(currentLocation.latitude, currentLocation.longitude);
                        window.mapDesktop.setCenter(moveLatLng);
                    }
                    if (window.mapMobile) {
                        const moveLatLng = new kakao.maps.LatLng(currentLocation.latitude, currentLocation.longitude);
                        window.mapMobile.setCenter(moveLatLng);
                    }
                }

                // 식당 정보 자동 갱신 (1km 반경, 최대 10개)
                loadRestaurants(1000, 10);
            }
        },
        (error) => {
            console.warn('⚠️  위치 추적 오류:', error.message);
        },
        {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 1000,  // 1초 이내 캐시된 위치 사용
        }
    );
}

/**
 * 반응형 레이아웃 업데이트
 */
function updateResponsiveLayout() {
    const isMobile = window.innerWidth <= 768;
    const desktopLayout = document.querySelector('.desktop-layout');
    const mobileLayout = document.querySelector('.mobile-layout');

    if (isMobile) {
        if (desktopLayout) desktopLayout.style.setProperty('display', 'none', 'important');
        if (mobileLayout) mobileLayout.style.setProperty('display', 'block', 'important');
        debugLog('📱 모바일 바텀시트 레이아웃 활성화 (', window.innerWidth, 'px)');
    } else {
        if (desktopLayout) desktopLayout.style.setProperty('display', 'flex', 'important');
        if (mobileLayout) mobileLayout.style.setProperty('display', 'none', 'important');
        debugLog('🖥️ 데스크톱 레이아웃 활성화 (', window.innerWidth, 'px)');
    }
}

let currentSheetState = 'half'; // 'collapsed' | 'half' | 'full'

/**
 * 바텀시트 상태 변경 (collapsed / half / full)
 */
function setBottomSheetState(state) {
    const sheet = document.getElementById('bottomSheet');
    const fabGroup = document.querySelector('.mobile-fab-group');
    const bottomNavItems = document.querySelectorAll('.bottom-nav-item');

    if (!sheet) return;

    sheet.classList.remove('sheet-collapsed', 'sheet-half', 'sheet-full');
    sheet.classList.add(`sheet-${state}`);
    currentSheetState = state;

    // FAB 위치 조정
    if (fabGroup) {
        if (state === 'full') {
            fabGroup.style.bottom = '85vh';
        } else if (state === 'half') {
            fabGroup.style.bottom = '54vh';
        } else {
            fabGroup.style.bottom = '90px';
        }
    }

    // 하단 네비게이션 활성화 표시
    bottomNavItems.forEach(item => {
        const itemState = item.getAttribute('data-state');
        if (itemState) {
            item.classList.toggle('active', itemState === state);
        }
    });

    setTimeout(() => resizeMap(), 150);
}

/**
 * 바텀시트 드래그 제스처 초기화
 */
function initBottomSheetGestures() {
    const handle = document.getElementById('sheetHandle');
    const sheet = document.getElementById('bottomSheet');
    if (!handle || !sheet) return;

    let startY = 0;
    let initialHeight = 0;
    let isDragging = false;

    handle.addEventListener('touchstart', (e) => {
        startY = e.touches[0].clientY;
        initialHeight = sheet.offsetHeight;
        isDragging = true;
        sheet.style.transition = 'none';
    }, { passive: true });

    handle.addEventListener('touchmove', (e) => {
        if (!isDragging) return;
        const deltaY = startY - e.touches[0].clientY;
        const newHeight = initialHeight + deltaY;
        const maxHeight = window.innerHeight - 120;
        if (newHeight >= 70 && newHeight <= maxHeight) {
            sheet.style.height = `${newHeight}px`;
        }
    }, { passive: true });

    handle.addEventListener('touchend', () => {
        if (!isDragging) return;
        isDragging = false;
        sheet.style.transition = '';

        const currentHeight = sheet.offsetHeight;
        const windowH = window.innerHeight;

        if (currentHeight < windowH * 0.25) {
            setBottomSheetState('collapsed');
        } else if (currentHeight > windowH * 0.70) {
            setBottomSheetState('full');
        } else {
            setBottomSheetState('half');
        }
    });

    // 핸들 터치/클릭 시 시트 토글
    handle.addEventListener('click', (e) => {
        if (e.target.tagName === 'SELECT' || e.target.closest('.sort-section')) return;
        if (currentSheetState === 'half') {
            setBottomSheetState('full');
        } else {
            setBottomSheetState('half');
        }
    });
}

/**
 * 이벤트 리스너 등록
 */
function setupEventListeners() {
    // 바텀시트 제스처 초기화
    initBottomSheetGestures();

    // 윈도우 리사이즈
    window.addEventListener('resize', () => {
        updateResponsiveLayout();
        resizeMap();
    });

    // 데스크톱 카테고리 칩
    document.querySelectorAll('.panel-list .chip').forEach((chip) => {
        chip.addEventListener('click', (e) => {
            document.querySelectorAll('.panel-list .chip').forEach((c) => c.classList.remove('chip-active'));
            e.target.classList.add('chip-active');
            currentCategory = e.target.getAttribute('data-category');
            loadRestaurants();
        });
    });

    // 모바일 오버레이 카테고리 칩
    document.querySelectorAll('.mobile-category-chips .chip').forEach((chip) => {
        chip.addEventListener('click', (e) => {
            document.querySelectorAll('.mobile-category-chips .chip').forEach((c) => c.classList.remove('chip-active'));
            e.target.classList.add('chip-active');
            currentCategory = e.target.getAttribute('data-category');
            loadRestaurants();
        });
    });

    // 정렬 선택
    const sortSelect = document.getElementById('sortSelect');
    const sortSelectMobile = document.getElementById('sortSelectMobile');
    
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            currentSort = e.target.value;
            sortRestaurants();
            renderRestaurantList('desktop');
        });
    }

    if (sortSelectMobile) {
        sortSelectMobile.addEventListener('change', (e) => {
            currentSort = e.target.value;
            sortRestaurants();
            renderRestaurantList('mobile');
        });
    }

    // 새로고침 버튼
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshBtnMobile = document.getElementById('refreshBtnMobile');

    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshNearbyRestaurants);
    }
    if (refreshBtnMobile) {
        refreshBtnMobile.addEventListener('click', refreshNearbyRestaurants);
    }

    // 모바일 FAB 버튼 이벤트
    const mobileLocationFab = document.getElementById('mobileLocationFab');
    if (mobileLocationFab) {
        mobileLocationFab.addEventListener('click', refreshNearbyRestaurants);
    }

    const mobileSurveyFab = document.getElementById('mobileSurveyFab');
    const bottomNavSurveyBtn = document.getElementById('bottomNavSurveyBtn');

    const openSurvey = () => {
        if (typeof window.openFoodSurvey === 'function') {
            window.openFoodSurvey();
        } else {
            const surveyModal = document.getElementById('surveyModal');
            if (surveyModal) surveyModal.style.display = 'flex';
        }
    };

    if (mobileSurveyFab) {
        mobileSurveyFab.addEventListener('click', openSurvey);
    }
    if (bottomNavSurveyBtn) {
        bottomNavSurveyBtn.addEventListener('click', openSurvey);
    }

    // 모바일 하단 네비게이션 버튼
    document.querySelectorAll('.bottom-nav-item[data-state]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const state = btn.getAttribute('data-state');
            setBottomSheetState(state);
        });
    });

    // 모달 닫기
    const modalOverlay = document.getElementById('modalOverlay');
    const modalClose = document.querySelector('.modal-close');
    const detailModal = document.getElementById('detailModal');

    const closeDetailModal = () => {
        detailModal.style.display = 'none';
        detailModalTrigger?.focus();
    };

    if (modalOverlay) {
        modalOverlay.addEventListener('click', closeDetailModal);
    }

    if (modalClose) {
        modalClose.addEventListener('click', closeDetailModal);
    }

    // 마커 클릭 이벤트
    window.addEventListener('markerClick', (e) => {
        loadRestaurantDetail(e.detail.restaurantId);
        // 마커 클릭 시 모바일이면 시트를 half로 조절하여 지도와 카드를 함께 감상하도록 지원
        if (window.innerWidth <= 768 && currentSheetState === 'full') {
            setBottomSheetState('half');
        }
    });
}

/**
 * 설문 결과를 기존 카테고리 검색으로 연결한다.
 */
window.applySurveyRecommendations = function applySurveyRecommendations(categories) {
    currentCategory = categories;
    document.querySelectorAll('.chip').forEach((chip) => {
        const chipCategory = chip.getAttribute('data-category');
        chip.classList.toggle('chip-active', categories.includes(chipCategory));
    });
    loadRestaurants();
};

/**
 * 현위치 다시 검색
 * 1) 현재 위치를 다시 요청하고
 * 2) 지도를 최신 위치로 이동한 뒤
 * 3) 주변 식당을 재조회한다.
 */
async function refreshNearbyRestaurants() {
    try {
        debugLog('↻ 현위치 다시 검색 시작');

        // 최신 위치를 강제로 다시 확인
        const latestLocation = await requestCurrentLocationOnce();
        currentLocation = latestLocation;
        debugLog('📍 새 위치 수신:', currentLocation);

        // 실시간 추적도 최신 좌표 기준으로 재시작
        startLocationTracking();

        // 지도 중심을 최신 위치로 재설정
        await initMapDesktop(currentLocation.latitude, currentLocation.longitude);
        await initMapMobile(currentLocation.latitude, currentLocation.longitude);
        setTimeout(() => resizeMap(), 100);

        // 주변 식당 재조회
        await loadRestaurants();
        debugLog('✅ 현위치 다시 검색 완료:', currentLocation);
    } catch (error) {
        console.error('❌ 현위치 다시 검색 실패:', error);
        showError('현재 위치를 다시 가져오지 못했습니다. 위치 권한과 GPS 상태를 확인해주세요.');
    }
}

/**
 * 탭 전환
 */
function switchTab(tab) {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabBtns.forEach((btn) => {
        if (btn.getAttribute('data-tab') === tab) {
            btn.classList.add('tab-btn-active');
        } else {
            btn.classList.remove('tab-btn-active');
        }
    });

    tabPanes.forEach((pane) => {
        if (pane.id === `${tab}Tab`) {
            pane.classList.add('tab-pane-active');
        } else {
            pane.classList.remove('tab-pane-active');
        }
    });

    // 탭 상태 저장
    saveTabState(tab);

    // 지도 리사이즈
    setTimeout(() => resizeMap(), 100);
}

/**
 * 식당 목록 로드
 */
async function loadRestaurants(radius = 1000, limit = 10) {
    try {
        // 로딩 표시
        showLoading('desktop', true);
        showLoading('mobile', true);

        debugLog('Calling searchNearbyRestaurants with:', {
            lat: currentLocation.latitude,
            lng: currentLocation.longitude,
            category: currentCategory,
            radius: radius,
            limit: limit
        });

        // API 호출 (기본값: 반경 1km, 최대 10개)
        const response = await searchNearbyRestaurants(
            currentLocation.latitude,
            currentLocation.longitude,
            currentCategory,
            radius,
            limit
        );

        debugLog('API response:', response);
        restaurants = response.restaurants || [];
        debugLog(`${restaurants.length}개의 식당 로드됨`);

        // 정렬
        sortRestaurants();

        // 렌더링
        renderRestaurantList('desktop');
        renderRestaurantList('mobile');

        // 지도 갱신
        refreshMap(currentLocation.latitude, currentLocation.longitude, restaurants);

        showLoading('desktop', false);
        showLoading('mobile', false);

        if (restaurants.length === 0) {
            showError('주변에 식당을 찾을 수 없습니다');
        }
    } catch (error) {
        console.error('식당 로드 실패:', error);
        showError('식당 정보를 불러올 수 없습니다');
        showLoading('desktop', false);
        showLoading('mobile', false);
    }
}

/**
 * 식당 정렬
 */
function sortRestaurants() {
    if (currentSort === 'distance') {
        restaurants.sort((a, b) => a.distance - b.distance);
    } else {
        // 추천순 (점수 내림차순)
        restaurants.sort((a, b) => (b.recommendScore || 0) - (a.recommendScore || 0));
    }
}

/**
 * 식당 목록 렌더링
 */
function renderRestaurantList(platform) {
    const containerId = platform === 'desktop' ? 'restaurantList' : 'restaurantListMobile';
    const container = document.getElementById(containerId);

    if (platform === 'mobile') {
        const countBadge = document.getElementById('sheetRestaurantCount');
        if (countBadge) {
            countBadge.textContent = `${restaurants.length}개`;
        }
    }

    if (restaurants.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>주변에 식당이 없습니다</p>
                <p style="font-size: 12px; margin-top: 8px;">위치를 다시 확인해주세요</p>
            </div>
        `;
        return;
    }

    container.innerHTML = restaurants.map((restaurant) => `
        <div class="restaurant-card" data-restaurant-id="${escapeHtml(restaurant.id)}" role="button" tabindex="0">
            <div class="card-header">
                <h3 class="card-name">${escapeHtml(restaurant.name)}</h3>
                <div class="card-score">${formatRecommendDisplay(restaurant.recommendScore)}</div>
            </div>
            
            <div class="card-meta">
                <span>📍 ${formatDistance(restaurant.distance)}</span>
                <span class="card-category">${getCategoryEmoji(restaurant.category)} ${escapeHtml(restaurant.category || '기타')}</span>
            </div>
            
            <div class="card-footer">
                <span>⭐ ${restaurant.reviewAvg ? `${formatAverageRating(restaurant.reviewAvg)} (${formatStars(restaurant.reviewAvg)})` : '평가 없음'}</span>
                <span>📝 ${restaurant.reviewCount || 0}개 리뷰</span>
            </div>
        </div>
    `).join('');

    container.querySelectorAll('.restaurant-card').forEach((card) => {
        const openDetail = () => loadRestaurantDetail(card.dataset.restaurantId);
        card.addEventListener('click', openDetail);
        card.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                openDetail();
            }
        });
    });
}

/**
 * 식당 상세 정보 로드 및 모달 표시
 */
async function loadRestaurantDetail(restaurantId) {
    try {
        const normalizedRestaurantId = String(restaurantId);
        const restaurant = restaurants.find((r) => String(r.id) === normalizedRestaurantId);
        if (!restaurant) {
            showError('식당 정보를 찾을 수 없습니다');
            return;
        }

        selectedRestaurant = restaurant;
        detailModalTrigger = document.activeElement;

        // 지도 중심 이동
        centerMapOnRestaurant(restaurant, mapDesktop);
        centerMapOnRestaurant(restaurant, mapMobile);

        // 모달 콘텐츠 렌더링
        const modal = document.getElementById('detailModal');
        const content = document.getElementById('detailContent');

        content.innerHTML = `
            <div class="detail-header">
                <h2 id="detailModalTitle" class="detail-name">${escapeHtml(restaurant.name)}</h2>
                <div class="detail-meta">
                    <span>📍 ${formatDistance(restaurant.distance)}</span>
                    <span>⭐ ${restaurant.reviewAvg ? formatAverageRating(restaurant.reviewAvg) : '0.0'}</span>
                    <span>📝 ${restaurant.reviewCount || 0}개</span>
                </div>
            </div>

            <div class="detail-body">
                <div class="detail-section">
                    <h3 class="detail-section-title">기본 정보</h3>
                    <p><strong>카테고리:</strong> ${getCategoryEmoji(restaurant.category)} ${restaurant.category || '미분류'}</p>
                    <p><strong>주소:</strong> ${escapeHtml(restaurant.address)}</p>
                    <p><strong>추천 점수:</strong> ${restaurant.recommendScore === null || restaurant.recommendScore === undefined ? '평가 없음' : `${formatScore(restaurant.recommendScore)}/5.0`}</p>
                </div>

                <div class="detail-section">
                    <h3 class="detail-section-title">대구 공공데이터 정보</h3>
                    <p><strong>영업시간:</strong> ${escapeHtml(infoOrNone(restaurant.daeguBusinessHours))}</p>
                    <p><strong>전화번호:</strong> ${escapeHtml(infoOrNone(restaurant.daeguPhone))}</p>
                    <p><strong>대표메뉴:</strong> ${escapeHtml(infoOrNone(restaurant.daeguMenu))}</p>
                    <p><strong>주차:</strong> ${escapeHtml(infoOrNone(restaurant.daeguParking))}</p>
                    <p><strong>예약:</strong> ${escapeHtml(infoOrNone(restaurant.daeguReservation))}</p>
                    <p><strong>지하철:</strong> ${escapeHtml(infoOrNone(restaurant.daeguSubway))}</p>
                    <p><strong>버스:</strong> ${escapeHtml(infoOrNone(restaurant.daeguBus))}</p>
                    <p><strong>홈페이지:</strong> ${escapeHtml(infoOrNone(restaurant.daeguHomepage))}</p>
                    <p><strong>설명:</strong> ${escapeHtml(infoOrNone(restaurant.daeguDescription))}</p>
                </div>

                <div class="detail-section">
                    <h3 class="detail-section-title">리뷰 작성</h3>
                    <div class="review-form" id="reviewForm">
                        <div class="rating-input" id="ratingInput">
                            ${[1, 2, 3, 4, 5].map((star) => `
                                <span class="star" data-rating="${star}">★</span>
                            `).join('')}
                        </div>
                        <textarea id="reviewContent" 
                                  placeholder="이 식당에 대한 의견을 공유해주세요" 
                                  style="width: 100%; padding: 8px; border: 1px solid #D9E0EE; border-radius: 8px; font-family: inherit; resize: vertical; min-height: 60px;"></textarea>
                        <button id="submitReviewBtn" class="btn btn-primary" style="margin-top: 8px; width: 100%;" type="button">
                            ✓ 리뷰 작성
                        </button>
                    </div>
                </div>

                <div class="detail-section" id="reviewsSection">
                    <h3 class="detail-section-title">리뷰 (${restaurant.reviewCount || 0})</h3>
                    <div id="reviewsList" style="display: flex; flex-direction: column; gap: 16px;"></div>
                </div>
            </div>
        `;

        // 별점 클릭 이벤트
        setupRatingInput();
        document.getElementById('submitReviewBtn').addEventListener('click', () => submitReview(restaurant.id));

        // 리뷰 목록 로드
        await loadReviews(restaurantId);

        // 모달 표시
        modal.style.display = 'flex';
        modal.querySelector('.modal-close')?.focus();
    } catch (error) {
        console.error('상세 정보 로드 실패:', error);
        showError('상세 정보를 불러올 수 없습니다');
    }
}

/**
 * 별점 입력 설정
 */
function setupRatingInput() {
    const stars = document.querySelectorAll('#ratingInput .star');
    let selectedRating = 0;

    stars.forEach((star) => {
        star.addEventListener('click', () => {
            selectedRating = parseInt(star.getAttribute('data-rating'));
            stars.forEach((s) => {
                const rating = parseInt(s.getAttribute('data-rating'));
                if (rating <= selectedRating) {
                    s.classList.add('active');
                } else {
                    s.classList.remove('active');
                }
            });
        });
    });
}

/**
 * 리뷰 목록 로드
 */
async function loadReviews(restaurantId) {
    try {
        const response = await getRestaurantReviews(restaurantId, 0, 10);
        const reviews = response.reviews || [];

        const reviewsList = document.getElementById('reviewsList');
        const reviewsTitle = document.querySelector('#reviewsSection .detail-section-title');
        if (reviewsTitle) {
            reviewsTitle.textContent = `리뷰 (${reviews.length})`;
        }

        if (reviews.length === 0) {
            reviewsList.innerHTML = '<p style="text-align: center; color: #999;">아직 리뷰가 없습니다</p>';
            return;
        }

        reviewsList.innerHTML = reviews.map((review) => `
            <div class="review-item">
                <div class="review-header">
                    <div>
                        <div class="review-user">${escapeHtml(review.userId)}</div>
                        <div class="review-rating">${formatStars(review.rating)}</div>
                    </div>
                    ${review.userId === userId ? `
                        <button class="delete-review-btn" data-review-id="${escapeHtml(review.id)}"
                                style="background: #E63946; color: white; border: none; padding: 4px 8px; border-radius: 4px; font-size: 12px; cursor: pointer;">
                            삭제
                        </button>
                    ` : ''}
                </div>
                <p class="review-content">${escapeHtml(review.content || '(내용 없음)')}</p>
                <p style="font-size: 12px; color: #999; margin-top: 8px;">${formatRelativeTime(review.createdAt)}</p>
            </div>
        `).join('');
        reviewsList.querySelectorAll('.delete-review-btn').forEach((button) => {
            button.addEventListener('click', () => deleteReviewItem(restaurantId, button.dataset.reviewId));
        });
    } catch (error) {
        console.error('리뷰 로드 실패:', error);
        document.getElementById('reviewsList').innerHTML = '<p style="text-align: center; color: #999;">리뷰를 불러올 수 없습니다</p>';
    }
}

/**
 * 리뷰 작성 제출
 */
async function submitReview(restaurantId) {
    const stars = document.querySelectorAll('#ratingInput .star.active');
    const rating = stars.length;
    const content = document.getElementById('reviewContent').value;

    if (rating === 0) {
        showError('별점을 선택해주세요');
        return;
    }

    try {
        await createReview(restaurantId, rating, content, userId, selectedRestaurant);
        showSuccess('리뷰가 작성되었습니다');
        
        // 모달 재로드
        loadRestaurantDetail(restaurantId);
    } catch (error) {
        console.error('리뷰 작성 실패:', error);
        showError(error.message || '리뷰 작성에 실패했습니다');
    }
}

/**
 * 리뷰 삭제
 */
async function deleteReviewItem(restaurantId, reviewId) {
    if (!confirm('정말 삭제하시겠습니까?')) return;

    try {
        await deleteReview(restaurantId, reviewId, userId);
        showSuccess('리뷰가 삭제되었습니다');
        
        // 모달 재로드
        loadRestaurantDetail(restaurantId);
    } catch (error) {
        console.error('리뷰 삭제 실패:', error);
        showError('리뷰 삭제에 실패했습니다');
    }
}

/**
 * 로딩 표시
 */
function showLoading(platform, show) {
    if (platform === 'desktop') {
        const mapLoading = document.getElementById('mapLoading');
        const listLoading = document.getElementById('listLoading');
        if (mapLoading) mapLoading.style.display = show ? 'flex' : 'none';
        if (listLoading) listLoading.style.display = show ? 'flex' : 'none';
    } else {
        const mapLoading = document.getElementById('mapLoadingMobile');
        const listLoading = document.getElementById('listLoadingMobile');
        if (mapLoading) mapLoading.style.display = show ? 'flex' : 'none';
        if (listLoading) listLoading.style.display = show ? 'flex' : 'none';
    }
}

/**
 * 초기 탭 복원
 */
window.addEventListener('load', () => {
    const lastTab = getLastTab();
    if (lastTab && window.innerWidth <= 768) {
        switchTab(lastTab);
    }
});

