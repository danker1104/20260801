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

/** 외부 데이터의 HTML 삽입을 방지한다. */
function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * 평균 평점을 별모양으로 표시
 */
function formatStars(rating) {
    const normalized = roundToHalf(rating);
    const fullStars = Math.floor(normalized);
    const hasHalf = normalized % 1 === 0.5;

    let html = `<span class="star-rating" aria-label="${normalized.toFixed(1)}점">`;
    for (let i = 1; i <= 5; i++) {
        let cls = 'is-empty';
        if (i <= fullStars) {
            cls = 'is-full';
        } else if (hasHalf && i === fullStars + 1) {
            cls = 'is-half';
        }
        html += `<span class="rating-star ${cls}">★</span>`;
    }
    html += '</span>';
    return html;
}

/**
 * 평점을 0.5 단위로 반올림
 */
function roundToHalf(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) {
        return 0;
    }
    return Math.min(5, Math.max(0, Math.round(num * 2) / 2));
}

/**
 * 평균 평점을 0.5 단위 숫자로 표시 (예: 1.5, 2.0, 2.5)
 */
function formatAverageRating(value) {
    return roundToHalf(value).toFixed(1);
}

/**
 * 날짜를 상대 시간으로 포맷팅 (예: 2시간 전)
 */
function formatRelativeTime(dateString) {
    if (!dateString) return '';

    // 백엔드가 타임존 없는 ISO 문자열(예: 2026-08-15T02:13:06.597017)을 주면 UTC로 간주한다.
    let normalized = String(dateString).trim();
    const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(normalized);

    if (!hasTimezone) {
        // 초과 마이크로초(6자리)는 Date 파싱 호환성을 위해 밀리초(3자리)로 축약
        normalized = normalized.replace(/\.(\d{3})\d+$/, '.$1');
        normalized += 'Z';
    }

    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) return '';

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
 * 서버 인증으로 발급된 현재 익명 사용자 ID를 표시할 때 사용
 */
function getUserId() {
    return null;
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
