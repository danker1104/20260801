"""
Review routes with async handlers and dependency injection.
"""
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas import (
    ReviewCreate,
    ReviewResponse,
    ReviewListResponse,
)
from services.review_service import ReviewService
from services.restaurant_service import RestaurantService
from auth import get_current_user

router = APIRouter(prefix="/api/restaurants", tags=["reviews"])
logger = logging.getLogger(__name__)


async def resolve_restaurant_for_review(
    db: AsyncSession,
    restaurant_service: RestaurantService,
    restaurant_id: str,
    review: Optional[ReviewCreate] = None,
):
    """
    리뷰 관련 API에서 사용할 식당 엔티티를 조회/생성한다.

    - 숫자 ID면 내부 PK로 조회
    - 문자열 ID면 externalId로 조회
    - review 메타데이터가 있으면 없는 식당을 자동 생성
    """
    normalized_restaurant_id = str(restaurant_id)

    if normalized_restaurant_id.isdigit():
        restaurant = await restaurant_service.get_restaurant_by_id(db, int(normalized_restaurant_id))
        if restaurant:
            return restaurant

    restaurant = await restaurant_service.get_restaurant_by_external_id(db, normalized_restaurant_id)
    if restaurant:
        return restaurant

    if not review:
        return None

    # 외부 ID 기반 리뷰 작성 시 식당 메타데이터가 포함되면 식당을 자동 생성한다.
    if not review.restaurantName or review.lat is None or review.lng is None or not review.address:
        raise HTTPException(
            status_code=400,
            detail="식당 정보가 없어 리뷰를 저장할 수 없습니다. 식당명/좌표/주소를 함께 전송하세요",
        )

    created = await restaurant_service.create_or_get(
        db=db,
        external_id=review.externalId or normalized_restaurant_id,
        name=review.restaurantName,
        lat=review.lat,
        lng=review.lng,
        address=review.address,
        category=review.category,
        external_rating=review.externalRating,
    )
    return created


@router.post("/{restaurant_id}/reviews", response_model=ReviewResponse)
async def create_review(
    restaurant_id: str,
    review: ReviewCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    리뷰 작성 또는 업데이트 (Async)
    
    같은 사용자가 같은 식당에 리뷰를 여러 번 작성하면 마지막 리뷰로 자동 업데이트됩니다.
    
    Args:
        restaurant_id: 식당 ID
        review: 리뷰 정보
            - rating: 1~5 정수
            - content: 리뷰 내용 (선택사항, 최대 1000자)
        user_id: 사용자 ID (X-User-Id 헤더에서 추출)
        db: AsyncSession
    
    Returns:
        ReviewResponse: 생성/업데이트된 리뷰
    
    주의:
        userId는 요청 본문에서 입력받지 않음 (보안: 서버에서 주입)
    """
    trace_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{trace_id}] 리뷰 작성 시작 (async): restaurant_id={restaurant_id}, user_id={user_id}")
        
        # 식당 조회/자동 생성
        service = RestaurantService()
        restaurant = await resolve_restaurant_for_review(
            db=db,
            restaurant_service=service,
            restaurant_id=restaurant_id,
            review=review,
        )

        if not restaurant:
            raise HTTPException(status_code=404, detail="식당을 찾을 수 없습니다")
        
        # 리뷰 생성/업데이트
        review_service = ReviewService()
        db_review = await review_service.create_or_update_review(
            db=db,
            restaurant_id=restaurant.id,
            user_id=user_id,
            rating=review.rating,
            content=review.content,
        )
        
        logger.info(f"[{trace_id}] 리뷰 작성 완료: review_id={db_review.id}")
        
        return ReviewResponse(
            id=db_review.id,
            restaurantId=db_review.restaurantId,
            userId=db_review.userId,
            rating=db_review.rating,
            content=db_review.content,
            createdAt=db_review.createdAt,
            updatedAt=db_review.updatedAt,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] 리뷰 작성 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "REVIEW_CREATE_FAILED",
                "message": "리뷰 작성에 실패했습니다",
                "traceId": trace_id,
            }
        )


@router.get("/{restaurant_id}/reviews", response_model=ReviewListResponse)
async def get_reviews(
    restaurant_id: str,
    skip: int = Query(0, ge=0, description="페이지 오프셋"),
    limit: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db: AsyncSession = Depends(get_db),
):
    """
    식당의 리뷰 목록 조회 (Async)
    
    최신 리뷰순으로 정렬하여 반환합니다.
    
    Args:
        restaurant_id: 식당 ID
        skip: 페이지 오프셋 (기본값 0)
        limit: 페이지 크기 (기본값 20, 최대 100)
        db: AsyncSession
    
    Returns:
        ReviewListResponse: 리뷰 목록 (total, reviews)
    """
    trace_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{trace_id}] 리뷰 목록 조회 (async): restaurant_id={restaurant_id}, skip={skip}, limit={limit}")
        
        # 식당 존재 여부 확인
        service = RestaurantService()
        restaurant = await resolve_restaurant_for_review(
            db=db,
            restaurant_service=service,
            restaurant_id=restaurant_id,
            review=None,
        )

        if not restaurant:
            # 외부 ID 식당은 아직 리뷰가 한 건도 없을 수 있으므로 빈 목록을 반환한다.
            return ReviewListResponse(total=0, reviews=[])
        
        # 리뷰 조회
        review_service = ReviewService()
        reviews = await review_service.get_reviews_by_restaurant(
            db=db,
            restaurant_id=restaurant.id,
            skip=skip,
            limit=limit,
        )
        
        total = await review_service.get_reviews_count(db, restaurant.id)
        
        return ReviewListResponse(
            total=total,
            reviews=[
                ReviewResponse(
                    id=r.id,
                    restaurantId=r.restaurantId,
                    userId=r.userId,
                    rating=r.rating,
                    content=r.content,
                    createdAt=r.createdAt,
                    updatedAt=r.updatedAt,
                )
                for r in reviews
            ],
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] 리뷰 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="리뷰 목록 조회에 실패했습니다")


@router.get("/{restaurant_id}/reviews/me", response_model=ReviewResponse)
async def get_my_review(
    restaurant_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    현재 사용자의 특정 식당 리뷰 조회 (Async)
    
    Args:
        restaurant_id: 식당 ID
        user_id: 사용자 ID (X-User-Id 헤더에서 추출)
        db: AsyncSession
    
    Returns:
        ReviewResponse: 사용자의 리뷰
    
    Raises:
        HTTPException: 리뷰를 찾을 수 없을 시 404
    """
    trace_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{trace_id}] 내 리뷰 조회 (async): restaurant_id={restaurant_id}, user_id={user_id}")
        
        service = RestaurantService()
        restaurant = await resolve_restaurant_for_review(
            db=db,
            restaurant_service=service,
            restaurant_id=restaurant_id,
            review=None,
        )

        if not restaurant:
            raise HTTPException(status_code=404, detail="식당을 찾을 수 없습니다")

        # 리뷰 조회
        review_service = ReviewService()
        review = await review_service.get_user_review(
            db=db,
            restaurant_id=restaurant.id,
            user_id=user_id,
        )
        
        if not review:
            raise HTTPException(status_code=404, detail="작성한 리뷰가 없습니다")
        
        return ReviewResponse(
            id=review.id,
            restaurantId=review.restaurantId,
            userId=review.userId,
            rating=review.rating,
            content=review.content,
            createdAt=review.createdAt,
            updatedAt=review.updatedAt,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] 내 리뷰 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="내 리뷰 조회에 실패했습니다")


@router.delete("/{restaurant_id}/reviews/{review_id}")
async def delete_review(
    restaurant_id: str,
    review_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    리뷰 삭제 (본인의 리뷰만 삭제 가능) (Async)
    
    보안: userId 검증을 통해 본인의 리뷰만 삭제 가능합니다.
    
    Args:
        restaurant_id: 식당 ID
        review_id: 리뷰 ID
        user_id: 사용자 ID (X-User-Id 헤더에서 추출)
        db: AsyncSession
    
    Returns:
        { "message": "리뷰가 삭제되었습니다" }
    
    Raises:
        HTTPException: 리뷰를 찾을 수 없거나 삭제 권한 없을 시 404
    """
    trace_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{trace_id}] 리뷰 삭제 시작 (async): restaurant_id={restaurant_id}, review_id={review_id}, user_id={user_id}")

        service = RestaurantService()
        restaurant = await resolve_restaurant_for_review(
            db=db,
            restaurant_service=service,
            restaurant_id=restaurant_id,
            review=None,
        )

        if not restaurant:
            raise HTTPException(status_code=404, detail="식당을 찾을 수 없습니다")
        
        # 리뷰 삭제
        review_service = ReviewService()
        deleted = await review_service.delete_review(
            db=db,
            review_id=review_id,
            restaurant_id=restaurant.id,
            user_id=user_id,
        )
        
        if not deleted:
            raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없거나 삭제 권한이 없습니다")
        
        logger.info(f"[{trace_id}] 리뷰 삭제 완료")
        
        return {"message": "리뷰가 삭제되었습니다"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] 리뷰 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="리뷰 삭제에 실패했습니다")
