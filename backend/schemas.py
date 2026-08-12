from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# ===== Restaurant Schemas =====

class RestaurantBase(BaseModel):
    """식당 기본 정보"""
    name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = None
    lat: float
    lng: float
    address: str = Field(..., min_length=1, max_length=500)
    externalRating: Optional[float] = None


class RestaurantCreate(RestaurantBase):
    """식당 생성 요청"""
    externalId: str = Field(..., min_length=1, max_length=255)


class RestaurantUpdate(BaseModel):
    """식당 업데이트 요청"""
    name: Optional[str] = None
    category: Optional[str] = None
    address: Optional[str] = None
    externalRating: Optional[float] = None


class RestaurantResponse(RestaurantBase):
    """식당 응답"""
    id: int
    externalId: str
    distance: Optional[float] = Field(None, description="사용자로부터의 거리 (미터)")
    recommendScore: Optional[float] = Field(None, description="추천 점수 (0~1)")
    reviewCount: int = 0
    reviewAvg: float = 0.0
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class NearbyRestaurantsResponse(BaseModel):
    """주변 식당 조회 응답"""
    total: int = Field(..., description="총 식당 수")
    restaurants: List[RestaurantResponse]
    userLat: float
    userLng: float


# ===== Review Schemas =====

class ReviewBase(BaseModel):
    """리뷰 기본 정보"""
    rating: int = Field(..., ge=1, le=5, description="1~5 정수")
    content: Optional[str] = Field(None, max_length=1000)


class ReviewCreate(ReviewBase):
    """리뷰 생성 요청 (userId는 서버에서 주입)"""
    pass


class ReviewUpdate(BaseModel):
    """리뷰 업데이트 요청"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    content: Optional[str] = Field(None, max_length=1000)


class ReviewResponse(ReviewBase):
    """리뷰 응답"""
    id: int
    restaurantId: int
    userId: str
    createdAt: datetime
    updatedAt: datetime
    
    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    """리뷰 목록 응답"""
    total: int
    reviews: List[ReviewResponse]


class ReviewStatsResponse(BaseModel):
    """리뷰 통계 응답"""
    reviewCount: int
    reviewAvg: float
    lastReviewAt: Optional[datetime] = None


# ===== Error Schemas =====

class ErrorResponse(BaseModel):
    """에러 응답"""
    code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    traceId: Optional[str] = Field(None, description="추적 ID")


# ===== Request Schemas =====

class NearbyRestaurantsRequest(BaseModel):
    """주변 식당 조회 요청"""
    lat: float = Field(..., description="사용자 위도")
    lng: float = Field(..., description="사용자 경도")
    radius: int = Field(1000, ge=100, le=5000, description="검색 반경 (미터)")
    category: Optional[str] = Field(None, description="카테고리 필터")
    sortBy: str = Field("recommend", pattern="^(recommend|distance)$", description="정렬 방식")
