"""
Restaurant service with business logic and async patterns.
Repository 패턴 및 async/await를 활용한 개선된 구현.
"""
import math
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from models import Restaurant
from repositories.restaurant_repository import RestaurantRepository
from repositories.review_repository import ReviewRepository
from config import RECOMMENDATION_WEIGHTS

logger = logging.getLogger(__name__)


class RestaurantService:
    """식당 관련 비즈니스 로직 - Async + Repository 패턴"""

    def __init__(self):
        self.restaurant_repo = RestaurantRepository(Restaurant)

    @staticmethod
    def _calculate_distance(
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float
    ) -> float:
        """
        Haversine 공식으로 두 점 사이의 거리 계산 (미터 단위)
        
        Args:
            lat1, lng1: 점1 (사용자)
            lat2, lng2: 점2 (식당)
        
        Returns:
            거리 (미터)
        """
        EARTH_RADIUS = 6371000  # 지구 반지름 (미터)
        
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = EARTH_RADIUS * c
        return distance

    @staticmethod
    def _calculate_recommend_score(
        distance: float,
        external_score: float,
        review_score: float,
        max_distance: float = 1000,
    ) -> float:
        """
        추천 점수 계산 (0~1)
        
        공식: score = 0.4 * distanceScore + 0.3 * externalScore + 0.3 * reviewScore
        
        Args:
            distance: 거리 (미터)
            external_score: 외부 평점 (0~1)
            review_score: 내부 리뷰 평점 (1~5, 정규화됨)
            max_distance: 최대 거리 (이 이상은 distanceScore=0)
        
        Returns:
            추천 점수 (0~1)
        """
        # distanceScore: 가까울수록 높음
        distance_score = max(0, 1 - (distance / max_distance)) if distance <= max_distance else 0
        
        # externalScore: 0~1
        ext_score = min(1, max(0, external_score))
        
        # reviewScore: 평점을 0~1로 정규화 (1~5 → 0~1)
        review_normalized = (review_score - 1) / 4 if review_score > 0 else 0
        review_score_normalized = min(1, max(0, review_normalized))
        
        weights = RECOMMENDATION_WEIGHTS
        recommend_score = (
            weights["distance"] * distance_score +
            weights["external_score"] * ext_score +
            weights["review_score"] * review_score_normalized
        )
        
        return min(1, max(0, recommend_score))

    async def get_restaurant_by_id(
        self,
        db: AsyncSession,
        restaurant_id: int
    ) -> Optional[Restaurant]:
        """ID로 식당 조회 (async)"""
        return await self.restaurant_repo.get(db, restaurant_id)

    async def get_restaurant_by_external_id(
        self,
        db: AsyncSession,
        external_id: str
    ) -> Optional[Restaurant]:
        """외부 ID로 식당 조회 (async)"""
        return await self.restaurant_repo.get_by_external_id(db, external_id)

    async def get_all_restaurants(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20
    ) -> List[Restaurant]:
        """모든 식당 조회 (async)"""
        return await self.restaurant_repo.get_all(db, skip, limit)

    async def create_or_get(
        self,
        db: AsyncSession,
        external_id: str,
        name: str,
        lat: float,
        lng: float,
        address: str,
        category: Optional[str] = None,
        external_rating: Optional[float] = None
    ) -> Restaurant:
        """
        외부 ID로 식당이 있으면 조회, 없으면 생성 (async)
        
        Args:
            db: AsyncSession
            external_id: SK T-Map POI ID
            name: 식당 이름
            lat, lng: 좌표
            address: 주소
            category: 카테고리
            external_rating: 외부 평점
        
        Returns:
            Restaurant (new or existing)
        """
        return await self.restaurant_repo.create_or_get(
            db,
            external_id=external_id,
            name=name,
            lat=lat,
            lng=lng,
            address=address,
            category=category,
            externalRating=external_rating
        )

    @staticmethod
    async def normalize_poi(
        db: AsyncSession,
        poi: dict,
        user_lat: float,
        user_lng: float,
        review_repo: ReviewRepository,
    ) -> Optional[dict]:
        """
        SK T-Map POI 응답을 내부 Restaurant 모델로 정규화
        
        Args:
            db: AsyncSession
            poi: SK T-Map POI 데이터
            user_lat, user_lng: 사용자 위치
            review_repo: ReviewRepository (통계 조회용)
        
        Returns:
            정규화된 식당 정보 딕셔너리 또는 None
        """
        try:
            # POI 데이터 추출
            poi_id = str(poi.get("id", poi.get("poiId", "")))
            name = poi.get("name", "미분류")
            address = poi.get("fullAddress", "")
            lat = float(poi.get("lat", 0))
            lng = float(poi.get("lon", 0))
            category = poi.get("category", "")
            external_rating = float(poi.get("naver_score", 0)) / 5.0 if poi.get("naver_score") else 0.5
            
            if not poi_id or not name:
                return None
            
            # 거리 계산
            distance = RestaurantService._calculate_distance(user_lat, user_lng, lat, lng)
            
            # 추천 점수 계산 (간단하게)
            recommend_score = RestaurantService._calculate_recommend_score(
                distance=distance,
                external_score=external_rating,
                review_score=3.0,  # 테스트용 기본값
                max_distance=1000
            )
            
            return {
                "id": abs(hash(poi_id)) % (10 ** 8),  # 임시 ID (테스트용)
                "externalId": poi_id,
                "name": name,
                "category": category,
                "lat": lat,
                "lng": lng,
                "address": address,
                "externalRating": float(external_rating),
                "distance": float(distance),
                "reviewCount": 0,
                "reviewAvg": 0,
                "recommendScore": float(recommend_score),
                "createdAt": None,
                "updatedAt": None,
            }
        except Exception as e:
            logger.error(f"POI 정규화 실패: {str(e)}, poi={poi}")
            return None
