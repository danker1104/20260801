"""
Base repository pattern for generic CRUD operations.
"""
from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic base repository for CRUD operations.
    
    Provides async methods for:
    - Create (POST)
    - Read (GET by ID, GET all)
    - Update (PATCH)
    - Delete (DELETE)
    """

    def __init__(self, model: Type[ModelType]):
        """Initialize repository with model class."""
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """
        ID로 단일 레코드 조회
        
        Args:
            db: AsyncSession
            id: Primary key value
        
        Returns:
            Model instance or None
        """
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalars().first()

    async def get_all(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        모든 레코드 조회 (페이지네이션)
        
        Args:
            db: AsyncSession
            skip: 페이지 오프셋
            limit: 페이지 크기
        
        Returns:
            List of model instances
        """
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_count(self, db: AsyncSession) -> int:
        """전체 레코드 수"""
        result = await db.execute(
            select(func.count(self.model.id))
        )
        return result.scalar() or 0

    async def create(
        self,
        db: AsyncSession,
        obj_in: CreateSchemaType
    ) -> ModelType:
        """
        새 레코드 생성
        
        Args:
            db: AsyncSession
            obj_in: Pydantic schema
        
        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_in.dict(exclude_unset=True))
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: ModelType,
        obj_in: UpdateSchemaType
    ) -> ModelType:
        """
        기존 레코드 업데이트
        
        Args:
            db: AsyncSession
            db_obj: Model instance to update
            obj_in: Pydantic schema with updated fields
        
        Returns:
            Updated model instance
        """
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, id: Any) -> bool:
        """
        ID로 레코드 삭제
        
        Args:
            db: AsyncSession
            id: Primary key value
        
        Returns:
            True if deleted, False if not found
        """
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            return True
        return False

    async def delete_obj(self, db: AsyncSession, obj: ModelType) -> bool:
        """
        Model instance 직접 삭제
        
        Args:
            db: AsyncSession
            obj: Model instance
        
        Returns:
            True if successful
        """
        await db.delete(obj)
        return True
