"""
Database connection and session management with async support.
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import select

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Async SQLAlchemy 엔진 생성
engine = create_async_engine(
    DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///") if "sqlite" in DATABASE_URL else DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Async 세션 팩토리
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Declarative base for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    FastAPI 의존성: DB 세션 주입
    
    Usage:
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()


async def init_db():
    """
    애플리케이션 시작 시 데이터베이스 초기화
    - 모든 테이블 생성
    - 마이그레이션 실행 (필요시)
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database initialized successfully")


async def close_db():
    """
    애플리케이션 종료 시 데이터베이스 연결 종료
    """
    await engine.dispose()
    logger.info("✅ Database connections closed")
