/**
 * API - 백엔드 API 호출 래퍼
 */

const API_BASE_URL = 'http://localhost:8000/api';
const API_TIMEOUT = 10000; // 10초

/**
 * API 호출 기본 함수
 */
async function apiCall(endpoint, options = {}) {
    const {
        method = 'GET',
        body = null,
        headers = {},
        userId = null,
    } = options;

    const url = `${API_BASE_URL}${endpoint}`;
    const fetchOptions = {
        method,
        headers: {
            'Content-Type': 'application/json',
            ...headers,
        },
    };

    // userId 추가
    if (userId) {
        fetchOptions.headers['X-User-Id'] = userId;
    }

    if (body) {
        fetchOptions.body = JSON.stringify(body);
    }

    try {
        console.log(`[apiCall] ${method} ${url}`);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

        const response = await fetch(url, {
            ...fetchOptions,
            signal: controller.signal,
        });

        clearTimeout(timeoutId);
        console.log(`[apiCall] Response: ${response.status} ${response.statusText}`);

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`[apiCall] Error [${method} ${endpoint}]:`, error);
        throw error;
    }
}

/**
 * 주변 식당 검색 (카카오 맵 API 사용)
 */
async function searchNearbyRestaurants(latitude, longitude, category = '', radius = 1000, limit = 10) {
    try {
        // 카카오 맵 API 초기화 확인
        if (!window.kakao || !window.kakao.maps || !window.kakao.maps.services) {
            console.error('Kakao Maps API not initialized');
            return { total: 0, restaurants: [], userLat: latitude, userLng: longitude };
        }

        const places = new window.kakao.maps.services.Places();
        
        // 카테고리별 검색어 매핑
        const categoryKeywords = {
            '한식': '한식당',
            '일식': '일식당',
            '중식': '중국음식',
            '양식': '양식당',
            '카페': '카페'
        };
        
        const query = categoryKeywords[category] || '음식점';
        
        // 카카오 API 호출
        const result = await new Promise((resolve) => {
            places.keywordSearch(query, (data, status) => {
                if (status === window.kakao.maps.services.Status.OK) {
                    // 현재 위치 주변 반경 내 식당만 필터링
                    const filtered = data.filter(place => {
                        const distance = calculateDistance(
                            latitude, longitude,
                            parseFloat(place.y), parseFloat(place.x)
                        );
                        return distance <= radius;
                    }).slice(0, limit);
                    
                    resolve(filtered);
                } else if (status === window.kakao.maps.services.Status.ZERO_RESULT) {
                    console.log('No results found:', query);
                    resolve([]);
                } else {
                    console.error('Kakao Places search error:', status);
                    resolve([]);
                }
            }, {
                location: new window.kakao.maps.LatLng(latitude, longitude),
                radius: radius
            });
        });

        // 결과 변환
        const restaurants = result.map((place, index) => ({
            id: place.id || `kakao_${index}`,
            externalId: place.id || `kakao_${index}`,
            name: place.place_name,
            category: category || '음식점',
            lat: parseFloat(place.y),
            lng: parseFloat(place.x),
            address: place.address_name || place.road_address_name || '',
            externalRating: 0.8,
            reviewCount: 0,
            reviewAvg: 0.0,
            distance: calculateDistance(latitude, longitude, parseFloat(place.y), parseFloat(place.x)),
            createdAt: null,
            updatedAt: null
        }));

        console.log('Kakao Places Search Result:', {
            query,
            found: restaurants.length,
            category
        });

        return {
            total: restaurants.length,
            restaurants: restaurants,
            userLat: latitude,
            userLng: longitude
        };

    } catch (error) {
        console.error('Kakao Places search error:', error);
        return {
            total: 0,
            restaurants: [],
            userLat: latitude,
            userLng: longitude
        };
    }
}

/**
 * 식당 상세 정보 조회
 */
async function getRestaurantDetail(restaurantId) {
    return apiCall(`/restaurants/${restaurantId}`);
}

/**
 * 리뷰 작성/업데이트
 */
async function createReview(restaurantId, rating, content, userId) {
    return apiCall(`/restaurants/${restaurantId}/reviews`, {
        method: 'POST',
        body: {
            rating,
            content: content || null,
        },
        userId,
    });
}

/**
 * 식당의 리뷰 목록 조회
 */
async function getRestaurantReviews(restaurantId, skip = 0, limit = 20) {
    const params = new URLSearchParams();
    params.append('skip', skip);
    params.append('limit', limit);

    return apiCall(`/restaurants/${restaurantId}/reviews?${params.toString()}`);
}

/**
 * 현재 사용자의 리뷰 조회
 */
async function getMyReview(restaurantId, userId) {
    return apiCall(`/restaurants/${restaurantId}/reviews/me`, {
        userId,
    });
}

/**
 * 리뷰 삭제
 */
async function deleteReview(restaurantId, reviewId, userId) {
    return apiCall(`/restaurants/${restaurantId}/reviews/${reviewId}`, {
        method: 'DELETE',
        userId,
    });
}

/**
 * 식당 통계 조회 (평점, 리뷰 수)
 */
async function getRestaurantStats(restaurantId) {
    return apiCall(`/restaurants/${restaurantId}/stats`);
}

/**
 * API 상태 확인 (헬스 체크)
 */
async function healthCheck() {
    try {
        const response = await fetch(`${API_BASE_URL.replace('/api', '')}/health`);
        return response.ok;
    } catch {
        return false;
    }
}
