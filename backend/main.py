"""
SG-Food FastAPI Application with async support and proper lifecycle management.

Production-ready backend API with:
- Async/await patterns (FastAPI + asyncio)
- Database connection pooling (AsyncSession)
- Dependency injection (FastAPI Depends)
- Error handling (structured exceptions)
- Logging (structured logging)
- CORS middleware
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import FRONTEND_URL, DEBUG, FASTAPI_HOST, FASTAPI_PORT
from core.database import init_db, close_db
from routes import restaurants, reviews

# ===== 로깅 설정 =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ===== 앱 생명주기 (Lifespan Context) =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 애플리케이션 생명주기 관리
    
    시작 이벤트: 데이터베이스 초기화, 리소스 할당
    종료 이벤트: 리소스 정리, 연결 해제
    """
    # ========== 시작 이벤트 ==========
    logger.info("🚀 SG-Food 백엔드 서버 시작...")
    
    try:
        # DB 초기화
        await init_db()
        logger.info("✅ 데이터베이스 초기화 완료")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {str(e)}")
        raise
    
    logger.info("✅ 서버 준비 완료")
    
    yield  # 서버 실행 중
    
    # ========== 종료 이벤트 ==========
    logger.info("🛑 SG-Food 백엔드 서버 종료 중...")
    
    try:
        await close_db()
        logger.info("✅ 데이터베이스 연결 종료")
    except Exception as e:
        logger.error(f"⚠️ 종료 중 오류: {str(e)}")
    
    logger.info("✅ 서버 종료 완료")


# ===== FastAPI 애플리케이션 초기화 =====
app = FastAPI(
    title="SG-Food API",
    description="위치 기반 식당 추천 서비스 백엔드 API (Async + Production Ready)",
    version="2.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ===== CORS 미들웨어 설정 =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)


# ===== 라우터 등록 =====
app.include_router(restaurants.router)
app.include_router(reviews.router)


# ===== 헬스 체크 엔드포인트 =====
@app.get("/health")
async def health_check():
    """
    서버 상태 확인
    
    Returns:
        { "status": "healthy", "service": "SG-Food API" }
    """
    return {
        "status": "healthy",
        "service": "SG-Food API",
        "version": "2.0.0",
    }


# ===== 루트 엔드포인트 =====
@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "🍽️ SG-Food API에 오신 것을 환영합니다",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "status": "operational",
    }


# ===== 메인 진입점 =====
if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"🌐 서버 시작: {FASTAPI_HOST}:{FASTAPI_PORT}")
    logger.info(f"📖 API 문서: http://{FASTAPI_HOST}:{FASTAPI_PORT}/docs")
    logger.info(f"🔧 디버그 모드: {DEBUG}")
    
    uvicorn.run(
        "main:app",
        host=FASTAPI_HOST,
        port=FASTAPI_PORT,
        reload=DEBUG,
        log_level="info",
    )
