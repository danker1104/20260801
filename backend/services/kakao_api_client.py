"""
카카오 맵 API 클라이언트
장소 검색 API를 사용하여 주변 식당 정보 조회
"""
import logging
import math
from typing import Optional, List
import aiohttp

from config import KAKAO_MAPS_API_KEY, KAKAO_MAPS_API_URL, API_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

# 카테고리별 검색어 매핑
CATEGORY_KEYWORDS = {
    "한식": "한식당",
    "일식": "일식당",
    "중식": "중국음식",
    "양식": "양식당",
    "카페": "카페",
}


class KakaoApiClient:
    """카카오 맵 API 클라이언트"""
    
    def __init__(self):
        self.api_key = KAKAO_MAPS_API_KEY
        self.api_url = KAKAO_MAPS_API_URL
        self.timeout = API_TIMEOUT_SECONDS
    
    async def search_nearby(
        self,
        lat: float,
        lng: float,
        radius: int = 1000,
        category: Optional[str] = None,
    ) -> List[dict]:
        """
        주변 식당 검색
        
        Args:
            lat: 사용자 위도
            lng: 사용자 경도
            radius: 검색 반경 (미터, 기본값 1000)
            category: 카테고리 필터 (한식/일식/중식/양식/카페)
        
        Returns:
            식당 정보 리스트
        """
        try:
            # 카테고리별 검색어 결정
            query = CATEGORY_KEYWORDS.get(category, "식당")
            
            logger.info(f"카카오 API 검색 시작: query={query}, lat={lat}, lng={lng}, radius={radius}")
            
            # 카카오 API 호출
            headers = {
                "Authorization": f"KakaoAK {self.api_key}"
            }
            params = {
                "query": query,
                "x": lng,  # 카카오 API는 경도를 x로 사용
                "y": lat,  # 카카오 API는 위도를 y로 사용
                "radius": radius,
                "size": 15,  # 최대 15개 조회 (기본값)
                "sort": "distance",  # 거리순 정렬
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        logger.error(f"카카오 API 오류: status={response.status}")
                        return []
                    
                    data = await response.json()
                    
                    # 응답 파싱
                    documents = data.get("documents", [])
                    logger.info(f"카카오 API 응답: {len(documents)}개 식당")
                    
                    # 결과 변환
                    restaurants = []
                    for doc in documents:
                        # 거리 계산 (카카오 API가 제공하는 거리 사용)
                        distance = float(doc.get("distance", 0))
                        
                        # 반경 필터링
                        if distance > radius:
                            continue
                        
                        restaurant = {
                            "id": doc.get("id", doc.get("place_name", "")),
                            "externalId": doc.get("id", ""),
                            "name": doc.get("place_name", ""),
                            "category": category or doc.get("category_group_name", "음식점"),
                            "lat": float(doc.get("y", 0)),
                            "lng": float(doc.get("x", 0)),
                            "address": doc.get("address_name", ""),
                            "externalRating": 0.8,  # 카카오 API는 평점 미제공
                            "reviewCount": 0,
                            "reviewAvg": 0.0,
                            "distance": distance,
                        }
                        restaurants.append(restaurant)
                    
                    return restaurants
        
        except Exception as e:
            logger.error(f"카카오 API 호출 실패: {str(e)}")
            return []
    
    @staticmethod
    def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Haversine 공식으로 두 지점 간 거리 계산 (미터)
        
        Args:
            lat1, lng1: 첫 번째 지점 좌표
            lat2, lng2: 두 번째 지점 좌표
        
        Returns:
            거리 (미터)
        """
        R = 6371000  # 지구 반경 (미터)
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
