"""
Review routes with async handlers and dependency injection.
"""
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas import (
    ReviewCreate,
    ReviewResponse,
    ReviewListResponse,
)
from services.review_service import ReviewService
from services.restaurant_service import RestaurantService

router = APIRouter(prefix="/api/restaurants", tags=["reviews"])
logger = logging.getLogger(__name__)


def get_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    """
    요청 헤더에서 userId 추출 (의존성 주입)
    
    실제 운영 환경에서는:
    - JWT 토큰 검증
    - 세션에서 userId 조회
    등의 보안 검증을 수행합니다.
    
    지금은 테스트를 위해 헤더에서 직접 받습니다.
    
    Args:
        x_user_id: X-User-Id 헤더값
    
    Returns:
        사용자 ID
    
    Raises:
        HTTPException: 인증 정보 없을 시
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="인증이 필요합니다")
    return x_user_id


@router.post("/{restaurant_id}/reviews", response_model=ReviewResponse)
async def create_review(
    restaurant_id: str,
    review: ReviewCreate,
    user_id: str = Depends(get_user_id),
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
        
        # 식당 존재 여부 확인
        service = RestaurantService()
        normalized_restaurant_id = str(restaurant_id)
        if normalized_restaurant_id.isdigit():
            restaurant = await service.get_restaurant_by_id(db, int(normalized_restaurant_id))
        else:
            restaurant = await service.get_restaurant_by_external_id(db, normalized_restaurant_id)

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
        normalized_restaurant_id = str(restaurant_id)
        if normalized_restaurant_id.isdigit():
            restaurant = await service.get_restaurant_by_id(db, int(normalized_restaurant_id))
        else:
            restaurant = await service.get_restaurant_by_external_id(db, normalized_restaurant_id)

        if not restaurant:
            raise HTTPException(status_code=404, detail="식당을 찾을 수 없습니다")
        
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
    user_id: str = Depends(get_user_id),
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
        normalized_restaurant_id = str(restaurant_id)
        if normalized_restaurant_id.isdigit():
            restaurant = await service.get_restaurant_by_id(db, int(normalized_restaurant_id))
        else:
            restaurant = await service.get_restaurant_by_external_id(db, normalized_restaurant_id)

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
    restaurant_id: int,
    review_id: int,
    user_id: str = Depends(get_user_id),
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
        logger.info(f"[{trace_id}] 리뷰 삭제 시작 (async): review_id={review_id}, user_id={user_id}")
        
        # 리뷰 삭제
        review_service = ReviewService()
        deleted = await review_service.delete_review(
            db=db,
            review_id=review_id,
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
