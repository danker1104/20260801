/**
 * Utils - 유틸리티 함수
 */

/**
 * 거리를 km 단위로 포맷팅
 */
function formatDistance(meters) {
    if (meters < 1000) {
        return `${Math.round(meters)}m`;
    }
    return `${(meters / 1000).toFixed(1)}km`;
}

/**
 * 추천 점수를 0-5 범위로 포맷팅
 */
function formatScore(score) {
    if (score === null || score === undefined) {
        return '0.0';
    }
    return Math.min(5, Math.max(0, score)).toFixed(1);
}

/**
 * 평균 평점을 별모양으로 표시
 */
function formatStars(rating) {
    const fullStars = Math.floor(rating);
    const hasHalf = rating % 1 >= 0.5;
    let stars = '★'.repeat(fullStars);
    if (hasHalf) stars += '☆';
    return stars.padEnd(5, '☆');
}

/**
 * 날짜를 상대 시간으로 포맷팅 (예: 2시간 전)
 */
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return '방금 전';
    if (diffMin < 60) return `${diffMin}분 전`;
    if (diffHour < 24) return `${diffHour}시간 전`;
    if (diffDay < 7) return `${diffDay}일 전`;
    
    return date.toLocaleDateString('ko-KR');
}

/**
 * 에러 메시지 표시
 */
function showError(message) {
    const toast = document.getElementById('errorToast');
    toast.textContent = message;
    toast.style.display = 'block';
    
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

/**
 * 성공 메시지 표시
 */
function showSuccess(message) {
    const toast = document.getElementById('successToast');
    toast.textContent = message;
    toast.style.display = 'block';
    
    setTimeout(() => {
        toast.style.display = 'none';
    }, 2000);
}

/**
 * userId 생성 (테스트용, 실제는 인증 시스템에서)
 */
function getUserId() {
    let userId = localStorage.getItem('userId');
    if (!userId) {
        userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('userId', userId);
    }
    return userId;
}

/**
 * 현재 탭 상태 저장
 */
function saveTabState(tab) {
    localStorage.setItem('lastTab', tab);
}

/**
 * 저장된 탭 상태 불러오기
 */
function getLastTab() {
    return localStorage.getItem('lastTab') || 'map';
}

/**
 * Haversine 거리 계산 (미터 단위)
 */
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371000; // 지구 반지름 (미터)
    const toRad = Math.PI / 180;
    
    const dLat = (lat2 - lat1) * toRad;
    const dLon = (lon2 - lon1) * toRad;
    
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    
    const c = 2 * Math.asin(Math.sqrt(a));
    return R * c;
}

/**
 * 페이지 로드 시 위치 권한 요청
 */
async function requestLocationPermission() {
    return new Promise((resolve) => {
        if ('geolocation' in navigator) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    });
                },
                (error) => {
                    console.warn('위치 권한 거부:', error);
                    resolve({
                        latitude: 37.4979, // 기본값: 서울 강남역
                        longitude: 127.0276
                    });
                }
            );
        } else {
            resolve({
                latitude: 37.4979,
                longitude: 127.0276
            });
        }
    });
}

/**
 * 카테고리 이모지 반환
 */
function getCategoryEmoji(category) {
    const emojiMap = {
        '한식': '🥘',
        '일식': '🍣',
        '중식': '🥡',
        '양식': '🍝',
        '카페': '☕',
        '': '🍴'
    };
    return emojiMap[category] || '🍴';
}

/**
 * 카테고리 한글 텍스트 반환
 */
function getCategoryLabel(category) {
    if (!category) return '전체';
    return category;
}
