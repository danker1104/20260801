"""
Restaurant routes with async handlers and dependency injection.
"""
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas import (
    NearbyRestaurantsResponse,
    RestaurantResponse,
)
from services.restaurant_service import RestaurantService
from services.kakao_api_client import KakaoApiClient

router = APIRouter(prefix="/api/restaurants", tags=["restaurants"])
logger = logging.getLogger(__name__)


@router.get("/nearby", response_model=NearbyRestaurantsResponse)
async def get_nearby_restaurants(
    lat: float = Query(..., description="사용자 위도"),
    lng: float = Query(..., description="사용자 경도"),
    radius: int = Query(1000, ge=100, le=5000, description="검색 반경 (미터)"),
    category: str = Query(None, description="카테고리 필터"),
    sortBy: str = Query("recommend", pattern="^(recommend|distance)$", description="정렬 방식"),
    limit: int = Query(10, ge=1, le=50, description="최대 반환 식당 수"),
    db: AsyncSession = Depends(get_db),
):
    """
    주변 식당 조회 (실시간 위치 기반 - 카카오 맵 API 연동)
    
    사용자의 현재 위치에서 반경 내의 식당을 조회합니다.
    카카오 맵 장소 검색 API 기반으로 전국 모든 지역 지원.
    
    - **lat**: 사용자 위도
    - **lng**: 사용자 경도  
    - **radius**: 검색 반경 (기본값 1000m, 최대 5000m)
    - **category**: 카테고리 필터 (한식/일식/중식/양식/카페)
    - **sortBy**: 정렬 방식 ("recommend" 또는 "distance")
    
    성능 목표: p95 800ms 이내
    반경 내 실제 위치한 식당만 반환
    """
    trace_id = str(uuid.uuid4())
    
    try:
        # 빈 문자열을 None으로 변환
        category = category if category and category.strip() else None
        
        logger.info(f"[{trace_id}] 주변 식당 조회 시작 (카카오 API): lat={lat}, lng={lng}, radius={radius}, category={category}")
        
        
        # 입력값 검증
        if not (-90 <= lat <= 90):
            raise HTTPException(status_code=400, detail="위도는 -90 ~ 90 범위여야 합니다")
        if not (-180 <= lng <= 180):
            raise HTTPException(status_code=400, detail="경도는 -180 ~ 180 범위여야 합니다")
        
        # 카카오 API 클라이언트로 식당 데이터 조회
        kakao_client = KakaoApiClient()
        
        try:
            all_restaurants = await kakao_client.search_nearby(
                lat=lat,
                lng=lng,
                radius=radius,
                category=category,
            )
            logger.info(f"[{trace_id}] 카카오 API 조회 완료: {len(all_restaurants)}개 식당")
        except Exception as e:
            logger.warning(f"[{trace_id}] 카카오 API 호출 실패 ({str(e)})")
            all_restaurants = []
        
        # 정렬
        if sortBy == "distance":
            all_restaurants.sort(key=lambda x: x.get("distance", 0))
        else:
            # 추천순: 거리와 평점을 고려한 점수
            for r in all_restaurants:
                distance = r.get("distance", 0)
                rating = r.get("externalRating", 0.75)
                distance_score = max(0, 1 - (distance / radius)) if radius > 0 else 1
                r["recommendScore"] = distance_score * 0.4 + rating * 0.6
            all_restaurants.sort(key=lambda x: x.get("recommendScore", 0), reverse=True)
        
        # 최대 개수 제한
        limited_restaurants = all_restaurants[:limit]
        
        logger.info(f"[{trace_id}] 주변 식당 조회 완료: total={len(limited_restaurants)}/{len(all_restaurants)}, category={category}, sortBy={sortBy}, limit={limit}")
        
        return NearbyRestaurantsResponse(
            total=len(limited_restaurants),
            restaurants=[RestaurantResponse(**r) for r in limited_restaurants],
            userLat=lat,
            userLng=lng,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] 주변 식당 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "RESTAURANT_SEARCH_FAILED",
                "message": "주변 식당 조회에 실패했습니다",
                "traceId": trace_id,
            }
        )


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant_detail(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    식당 상세 정보 조회 (Async)
    
    - **restaurant_id**: 식당 ID
    """
    trace_id = str(uuid.uuid4())
    
    try:
        service = RestaurantService()
        restaurant = await service.get_restaurant_by_id(db, restaurant_id)
        
        if not restaurant:
            raise HTTPException(status_code=404, detail="식당을 찾을 수 없습니다")
        
        # 리뷰 통계 포함
        from services.review_service import ReviewService
        review_service = ReviewService()
        review_count, review_avg = await review_service.get_review_stats(db, restaurant_id)
        
        return RestaurantResponse(
            id=restaurant.id,
            externalId=restaurant.externalId,
            name=restaurant.name,
            category=restaurant.category,
            lat=restaurant.lat,
            lng=restaurant.lng,
            address=restaurant.address,
            externalRating=restaurant.externalRating,
            reviewCount=review_count,
            reviewAvg=review_avg,
            createdAt=restaurant.createdAt,
            updatedAt=restaurant.updatedAt,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] 식당 상세 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="식당 상세 조회에 실패했습니다")
