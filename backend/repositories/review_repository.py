"""
Review repository with custom queries.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from models import Review, ReviewStats
from schemas import ReviewCreate, ReviewUpdate
from repositories.base_repository import BaseRepository


class ReviewRepository(BaseRepository[Review, ReviewCreate, ReviewUpdate]):
    """Review-specific repository with custom queries."""

    async def get_by_restaurant_and_user(
        self,
        db: AsyncSession,
        restaurant_id: int,
        user_id: str
    ) -> Optional[Review]:
        """
        식당과 사용자로 리뷰 조회
        (한 사용자는 한 식당에 최대 1개 리뷰만 가능)
        
        Args:
            db: AsyncSession
            restaurant_id: Restaurant ID
            user_id: User ID
        
        Returns:
            Review or None
        """
        result = await db.execute(
            select(Review).where(
                and_(
                    Review.restaurantId == restaurant_id,
                    Review.userId == user_id
                )
            )
        )
        return result.scalars().first()

    async def get_by_restaurant(
        self,
        db: AsyncSession,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[Review]:
        """
        식당의 모든 리뷰 조회 (최신순)
        
        Args:
            db: AsyncSession
            restaurant_id: Restaurant ID
            skip: 페이지 오프셋
            limit: 페이지 크기
        
        Returns:
            List of reviews (newest first)
        """
        result = await db.execute(
            select(Review)
            .where(Review.restaurantId == restaurant_id)
            .order_by(Review.createdAt.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Review]:
        """
        사용자의 모든 리뷰 조회
        
        Args:
            db: AsyncSession
            user_id: User ID
            skip: 페이지 오프셋
            limit: 페이지 크기
        
        Returns:
            List of reviews
        """
        result = await db.execute(
            select(Review)
            .where(Review.userId == user_id)
            .order_by(Review.createdAt.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def count_by_restaurant(
        self,
        db: AsyncSession,
        restaurant_id: int
    ) -> int:
        """
        식당의 리뷰 개수
        
        Args:
            db: AsyncSession
            restaurant_id: Restaurant ID
        
        Returns:
            Review count
        """
        result = await db.execute(
            select(func.count(Review.id)).where(
                Review.restaurantId == restaurant_id
            )
        )
        return result.scalar() or 0

    async def get_rating_stats(
        self,
        db: AsyncSession,
        restaurant_id: int
    ) -> tuple:
        """
        식당의 리뷰 통계 (개수, 평균 평점)
        
        Args:
            db: AsyncSession
            restaurant_id: Restaurant ID
        
        Returns:
            (count, avg_rating)
        """
        result = await db.execute(
            select(
                func.count(Review.id),
                func.avg(Review.rating)
            ).where(Review.restaurantId == restaurant_id)
        )
        row = result.tuple()
        if row:
            count, avg_rating = row[0]
            return count or 0, float(avg_rating) if avg_rating else 0.0
        return 0, 0.0

    async def get_latest_review_date(
        self,
        db: AsyncSession,
        restaurant_id: int
    ):
        """
        식당의 가장 최근 리뷰 생성 날짜
        
        Args:
            db: AsyncSession
            restaurant_id: Restaurant ID
        
        Returns:
            datetime or None
        """
        result = await db.execute(
            select(func.max(Review.createdAt)).where(
                Review.restaurantId == restaurant_id
            )
        )
        return result.scalar()

    async def upsert(
        self,
        db: AsyncSession,
        restaurant_id: int,
        user_id: str,
        rating: int,
        content: Optional[str] = None
    ) -> Review:
        """
        리뷰 생성 또는 업데이트 (upsert)
        같은 사용자가 같은 식당에 리뷰를 여러 번 제출하면 마지막 것으로 업데이트
        
        Args:
            db: AsyncSession
            restaurant_id: Restaurant ID
            user_id: User ID
            rating: 평점 (1~5)
            content: 리뷰 내용
        
        Returns:
            Review (new or updated)
        """
        existing = await self.get_by_restaurant_and_user(
            db, restaurant_id, user_id
        )
        
        if existing:
            # 업데이트
            existing.rating = rating
            existing.content = content
            await db.flush()
            await db.refresh(existing)
            return existing
        else:
            # 신규 생성
            review = Review(
                restaurantId=restaurant_id,
                userId=user_id,
                rating=rating,
                content=content
            )
            db.add(review)
            await db.flush()
            await db.refresh(review)
            return review

    async def delete_by_id_and_user(
        self,
        db: AsyncSession,
        review_id: int,
        user_id: str
    ) -> bool:
        """
        본인의 리뷰만 삭제 가능 (보안)
        
        Args:
            db: AsyncSession
            review_id: Review ID
            user_id: User ID (권한 검증용)
        
        Returns:
            True if deleted, False if not found or unauthorized
        """
        result = await db.execute(
            select(Review).where(
                and_(
                    Review.id == review_id,
                    Review.userId == user_id
                )
            )
        )
        review = result.scalars().first()
        
        if review:
            await db.delete(review)
            return True
        return False
