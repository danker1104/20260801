"""
뭐 먹을래? FastAPI Application with async support and proper lifecycle management.

Production-ready backend API with:
- Async/await patterns (FastAPI + asyncio)
- Database connection pooling (AsyncSession)
- Dependency injection (FastAPI Depends)
- Error handling (structured exceptions)
- Logging (structured logging)
- CORS middleware
"""
import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import AUTH_SECRET, FRONTEND_URL, DEBUG, FASTAPI_HOST, FASTAPI_PORT
from core.database import init_db, close_db
from routes import auth, restaurants, reviews

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
    logger.info("🚀 뭐 먹을래? 백엔드 서버 시작...")

    if not DEBUG and (not AUTH_SECRET or len(AUTH_SECRET) < 32):
        raise RuntimeError("운영 환경에서는 32자 이상의 AUTH_SECRET이 필요합니다")
    
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
    logger.info("🛑 뭐 먹을래? 백엔드 서버 종료 중...")
    
    try:
        await close_db()
        logger.info("✅ 데이터베이스 연결 종료")
    except Exception as e:
        logger.error(f"⚠️ 종료 중 오류: {str(e)}")
    
    logger.info("✅ 서버 종료 완료")


# ===== FastAPI 애플리케이션 초기화 =====
app = FastAPI(
    title="뭐 먹을래? API",
    description="위치 기반 식당 추천 서비스 백엔드 API (Async + Production Ready)",
    version="2.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


allowed_origins = [FRONTEND_URL]
if DEBUG:
    allowed_origins.extend([
        "http://localhost:3000",
        "http://localhost:5000",
        "http://127.0.0.1:3000",
    ])

# ===== CORS 미들웨어 설정 =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(self)"
    if request.url.path not in {"/docs", "/redoc"}:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if not DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ===== 라우터 등록 =====
app.include_router(restaurants.router)
app.include_router(reviews.router)
app.include_router(auth.router)


# ===== 헬스 체크 엔드포인트 =====
@app.get("/health")
async def health_check():
    """
    서버 상태 확인
    
    Returns:
        { "status": "healthy", "service": "뭐 먹을래? API" }
    """
    return {
        "status": "healthy",
        "service": "뭐 먹을래? API",
        "version": "2.0.0",
    }


# ===== 루트 엔드포인트 =====
@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "🍽️ 뭐 먹을래? API에 오신 것을 환영합니다",
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

