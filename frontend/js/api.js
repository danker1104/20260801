/**
 * API - 백엔드 API 호출 래퍼
 */

const API_BASE_URL = window.APP_CONFIG?.api?.baseURL || '/api';
const API_TIMEOUT = 10000; // 10초
let authToken = null;
const DAEGU_DISTRICTS = ['중구', '동구', '서구', '남구', '북구', '수성구', '달서구', '달성군'];

function extractDaeguDistrict(addressText) {
    if (!addressText) return null;
    const text = String(addressText);
    const match = text.match(/(중구|동구|서구|남구|북구|수성구|달서구|달성군)/);
    if (!match) return null;
    return DAEGU_DISTRICTS.includes(match[1]) ? match[1] : null;
}

async function resolveUserDaeguDistrict(latitude, longitude) {
    try {
        if (!window.kakao || !window.kakao.maps || !window.kakao.maps.services) {
            return null;
        }

        const geocoder = new window.kakao.maps.services.Geocoder();
        return await new Promise((resolve) => {
            geocoder.coord2Address(longitude, latitude, (result, status) => {
                if (status !== window.kakao.maps.services.Status.OK || !Array.isArray(result) || result.length === 0) {
                    resolve(null);
                    return;
                }

                const roadAddress = result[0]?.road_address?.address_name || '';
                const lotAddress = result[0]?.address?.address_name || '';
                resolve(extractDaeguDistrict(roadAddress) || extractDaeguDistrict(lotAddress));
            });
        });
    } catch (error) {
        console.warn('Failed to resolve user district:', error);
        return null;
    }
}

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

    if (authToken) {
        fetchOptions.headers.Authorization = `Bearer ${authToken}`;
    }

    if (body) {
        fetchOptions.body = JSON.stringify(body);
    }

    try {
        debugLog(`[apiCall] ${method} ${url}`);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

        const response = await fetch(url, {
            ...fetchOptions,
            signal: controller.signal,
        });

        clearTimeout(timeoutId);
        debugLog(`[apiCall] Response: ${response.status} ${response.statusText}`);

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

async function initializeAuth() {
    const response = await apiCall('/auth/anonymous', { method: 'POST' });
    authToken = response.accessToken;
    return response.userId;
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
        
        const categories = Array.isArray(category)
            ? category.filter((item) => categoryKeywords[item])
            : [category];
        const searchCategories = categories.length > 0 ? categories : [''];

        // 카카오 API 호출: 설문 결과가 복수 카테고리이면 결과를 합친다.
        const resultsByCategory = await Promise.all(searchCategories.map((selectedCategory) => {
            const query = categoryKeywords[selectedCategory] || '음식점';
            return new Promise((resolve) => {
                places.keywordSearch(query, (data, status) => {
                    if (status === window.kakao.maps.services.Status.OK) {
                        const filtered = data.filter(place => {
                            const distance = calculateDistance(
                                latitude, longitude,
                                parseFloat(place.y), parseFloat(place.x)
                            );
                            return distance <= radius;
                        }).slice(0, limit);
                        resolve(filtered.map((place) => ({ place, selectedCategory })));
                    } else if (status === window.kakao.maps.services.Status.ZERO_RESULT) {
                        debugLog('No results found:', query);
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
        }));
        const result = resultsByCategory.flat();
        const uniqueResult = result.filter(({ place }, index, allPlaces) => (
            allPlaces.findIndex((item) => item.place.id === place.id) === index
        )).slice(0, limit);

        // 결과 변환
        const restaurants = uniqueResult.map(({ place, selectedCategory }, index) => ({
            id: place.id || `kakao_${index}`,
            externalId: place.id || `kakao_${index}`,
            name: place.place_name,
            category: selectedCategory || '음식점',
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

        const userDistrict = await resolveUserDaeguDistrict(latitude, longitude);

        // 대구푸드 데이터 보강
        let enrichedRestaurants = restaurants;
        try {
            const enrichResponse = await apiCall('/restaurants/daegu/enrich', {
                method: 'POST',
                body: {
                    addr: userDistrict || undefined,
                    restaurants,
                },
            });
            if (Array.isArray(enrichResponse?.restaurants)) {
                enrichedRestaurants = enrichResponse.restaurants;
            }
        } catch (enrichError) {
            console.warn('Daegu food enrichment skipped:', enrichError);
        }

        debugLog('Kakao Places Search Result:', {
            categories: searchCategories,
            found: enrichedRestaurants.length,
            category
        });

        return {
            total: enrichedRestaurants.length,
            restaurants: enrichedRestaurants,
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
async function createReview(restaurantId, rating, content, userId, restaurant = null) {
    return apiCall(`/restaurants/${restaurantId}/reviews`, {
        method: 'POST',
        body: {
            rating,
            content: content || null,
            externalId: restaurant?.externalId || String(restaurantId),
            restaurantName: restaurant?.name || null,
            category: restaurant?.category || null,
            lat: typeof restaurant?.lat === 'number' ? restaurant.lat : null,
            lng: typeof restaurant?.lng === 'number' ? restaurant.lng : null,
            address: restaurant?.address || null,
            externalRating: typeof restaurant?.externalRating === 'number' ? restaurant.externalRating : null,
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
