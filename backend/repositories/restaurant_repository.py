"""
Restaurant repository with custom queries.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from models import Restaurant, ReviewStats
from schemas import RestaurantCreate, RestaurantUpdate
from repositories.base_repository import BaseRepository


class RestaurantRepository(BaseRepository[Restaurant, RestaurantCreate, RestaurantUpdate]):
    """Restaurant-specific repository with custom queries."""

    async def get_by_external_id(
        self,
        db: AsyncSession,
        external_id: str
    ) -> Optional[Restaurant]:
        """
        외부 API ID로 식당 조회
        
        Args:
            db: AsyncSession
            external_id: SK T-Map POI ID
        
        Returns:
            Restaurant or None
        """
        result = await db.execute(
            select(Restaurant).where(Restaurant.externalId == external_id)
        )
        return result.scalars().first()

    async def get_with_stats(
        self,
        db: AsyncSession,
        id: int
    ) -> Optional[Restaurant]:
        """
        식당을 리뷰 통계와 함께 조회
        
        Args:
            db: AsyncSession
            id: Restaurant ID
        
        Returns:
            Restaurant with loaded stats
        """
        result = await db.execute(
            select(Restaurant)
            .options(selectinload(Restaurant.stats))
            .where(Restaurant.id == id)
        )
        return result.scalars().first()

    async def get_all_with_stats(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Restaurant]:
        """
        모든 식당을 통계와 함께 조회
        
        Args:
            db: AsyncSession
            skip: 페이지 오프셋
            limit: 페이지 크기
        
        Returns:
            List of restaurants with stats
        """
        result = await db.execute(
            select(Restaurant)
            .options(selectinload(Restaurant.stats))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create_or_get(
        self,
        db: AsyncSession,
        external_id: str,
        **kwargs
    ) -> Restaurant:
        """
        외부 ID로 식당이 있으면 조회, 없으면 생성
        
        Args:
            db: AsyncSession
            external_id: SK T-Map POI ID
            **kwargs: Restaurant fields
        
        Returns:
            Restaurant (new or existing)
        """
        existing = await self.get_by_external_id(db, external_id)
        if existing:
            return existing

        # 신규 생성
        restaurant = Restaurant(
            externalId=external_id,
            **kwargs
        )
        db.add(restaurant)
        await db.flush()
        await db.refresh(restaurant)
        return restaurant

    async def search_nearby(
        self,
        db: AsyncSession,
        user_lat: float,
        user_lng: float,
        radius: int = 1000,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Restaurant]:
        """
        주변 식당 검색 (DB에 저장된 식당만)
        
        주의: 실제 주변 검색은 SK API를 통해 수행됨.
        이 메서드는 이미 저장된 식당들을 거리 필터링하는 용도.
        
        Args:
            db: AsyncSession
            user_lat: 사용자 위도
            user_lng: 사용자 경도
            radius: 검색 반경 (미터)
            category: 카테고리 필터
            skip: 페이지 오프셋
            limit: 페이지 크기
        
        Returns:
            List of nearby restaurants
        """
        # 간단한 구현: category 필터링만 수행
        # 실제 거리 기반 검색은 서비스 계층에서 수행
        query = select(Restaurant)
        
        if category:
            query = query.where(Restaurant.category == category)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def bulk_create(
        self,
        db: AsyncSession,
        restaurants: List[dict]
    ) -> List[Restaurant]:
        """
        여러 식당 한 번에 생성 (bulk insert)
        
        Args:
            db: AsyncSession
            restaurants: List of restaurant data dicts
        
        Returns:
            List of created restaurants
        """
        db_objects = [Restaurant(**data) for data in restaurants]
        db.add_all(db_objects)
        await db.flush()
        
        # ID 할당을 위해 refresh
        for obj in db_objects:
            await db.refresh(obj)
        
        return db_objects
