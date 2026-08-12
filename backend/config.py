import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# ===== 데이터베이스 =====
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sg_food.db")

# ===== 카카오 맵 API =====
KAKAO_MAPS_API_KEY = os.getenv("KAKAO_MAPS_API_KEY")
KAKAO_MAPS_API_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

# ===== FastAPI 서버 =====
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "0.0.0.0")
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", 8000))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# ===== CORS =====
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ===== 비즈니스 로직 설정 =====
NEARBY_RADIUS_METERS = 1000  # 1km
MAX_NEARBY_COUNT = 20  # 한 번에 조회하는 최대 개수

# API 타임아웃 및 재시도 설정
API_TIMEOUT_SECONDS = 10
MAX_RETRY_COUNT = 3

# 추천 점수 가중치
RECOMMENDATION_WEIGHTS = {
    "distance": 0.4,
    "external_score": 0.3,
    "review_score": 0.3,
}

# ===== 성능 목표 =====
API_TIMEOUT_SECONDS = 10
SK_API_TIMEOUT_SECONDS = 5
MAX_RETRY_COUNT = 2
