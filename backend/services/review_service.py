"""
Review service with business logic and async patterns.
Repository 패턴 및 async/await를 활용한 개선된 구현.
"""
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from models import Review, ReviewStats
from repositories.review_repository import ReviewRepository

logger = logging.getLogger(__name__)


class ReviewService:
    """리뷰 관련 비즈니스 로직 - Async + Repository 패턴"""

    def __init__(self):
        self.review_repo = ReviewRepository(Review)

    async def create_or_update_review(
        self,
        db: AsyncSession,
        restaurant_id: int,
        user_id: str,
        rating: int,
        content: Optional[str] = None,
    ) -> Review:
        """
        리뷰 생성 또는 업데이트 (upsert)
        
        Args:
            db: AsyncSession
            restaurant_id: 식당 ID
            user_id: 사용자 ID (서버에서 주입)
            rating: 평점 (1~5)
            content: 리뷰 내용
        
        Returns:
            생성/업데이트된 Review 객체
        """
        try:
            review = await self.review_repo.upsert(
                db,
                restaurant_id=restaurant_id,
                user_id=user_id,
                rating=rating,
                content=content
            )
            logger.info(f"리뷰 생성/업데이트: restaurant_id={restaurant_id}, user_id={user_id}")
            return review
        
        except Exception as e:
            logger.error(f"리뷰 생성/업데이트 실패: {str(e)}")
            raise

    async def delete_review(
        self,
        db: AsyncSession,
        review_id: int,
        restaurant_id: int,
        user_id: str
    ) -> bool:
        """
        리뷰 삭제 (사용자의 리뷰만 삭제 가능)
        
        Args:
            db: AsyncSession
            review_id: 리뷰 ID
            user_id: 사용자 ID (권한 검증)
        
        Returns:
            삭제 성공 여부
        """
        try:
            deleted = await self.review_repo.delete_by_id_and_user(
                db,
                review_id=review_id,
                restaurant_id=restaurant_id,
                user_id=user_id
            )
            if deleted:
                logger.info(f"리뷰 삭제: review_id={review_id}, user_id={user_id}")
            return deleted
        
        except Exception as e:
            logger.error(f"리뷰 삭제 실패: {str(e)}")
            raise

    async def get_reviews_by_restaurant(
        self,
        db: AsyncSession,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[Review]:
        """
        식당의 리뷰 목록 조회 (최신순)
        
        Args:
            db: AsyncSession
            restaurant_id: 식당 ID
            skip: 페이지 오프셋
            limit: 페이지 크기
        
        Returns:
            Review 객체 리스트
        """
        return await self.review_repo.get_by_restaurant(
            db,
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit
        )

    async def get_reviews_count(
        self,
        db: AsyncSession,
        restaurant_id: int
    ) -> int:
        """식당의 총 리뷰 수 (async)"""
        return await self.review_repo.count_by_restaurant(db, restaurant_id)

    async def get_user_review(
        self,
        db: AsyncSession,
        restaurant_id: int,
        user_id: str,
    ) -> Optional[Review]:
        """
        사용자의 특정 식당 리뷰 조회
        
        Args:
            db: AsyncSession
            restaurant_id: 식당 ID
            user_id: 사용자 ID
        
        Returns:
            Review 객체 (없으면 None)
        """
        return await self.review_repo.get_by_restaurant_and_user(
            db,
            restaurant_id=restaurant_id,
            user_id=user_id
        )

    async def get_review_stats(
        self,
        db: AsyncSession,
        restaurant_id: int
    ) -> tuple:
        """
        식당의 리뷰 통계 (개수, 평균 평점)
        
        Args:
            db: AsyncSession
            restaurant_id: 식당 ID
        
        Returns:
            (count, avg_rating)
        """
        return await self.review_repo.get_rating_stats(db, restaurant_id)
