from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class Restaurant(Base):
    """
    식당 정보 모델
    - externalId: SK T-Map POI ID (외부 시스템 ID)
    - name: 식당 이름
    - category: 카테고리
    - lat, lng: 위치 좌표
    - address: 주소
    - externalRating: 외부 평점 (T-Map에는 없으므로 null)
    """
    __tablename__ = "restaurants"
    
    id = Column(Integer, primary_key=True, index=True)
    externalId = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True, index=True)
    lat = Column(Float, nullable=False, index=True)
    lng = Column(Float, nullable=False, index=True)
    address = Column(String(500), nullable=False)
    externalRating = Column(Float, nullable=True)
    
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 관계
    reviews = relationship("Review", back_populates="restaurant", cascade="all, delete-orphan")
    stats = relationship("ReviewStats", back_populates="restaurant", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('externalId', name='uq_restaurant_externalid'),
    )


class Review(Base):
    """
    리뷰 모델
    - rating: 1~5 정수 (부분 점수 불가)
    - userId: 서버에서 주입 (클라이언트 입력 신뢰 금지)
    - content: 리뷰 텍스트
    """
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    restaurantId = Column(Integer, ForeignKey("restaurants.id"), nullable=False, index=True)
    userId = Column(String(255), nullable=False)
    rating = Column(Integer, nullable=False)
    content = Column(String(1000), nullable=True)
    
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 관계
    restaurant = relationship("Restaurant", back_populates="reviews")
    
    __table_args__ = (
        UniqueConstraint('restaurantId', 'userId', name='uq_review_restaurant_user'),
        CheckConstraint('rating >= 1 AND rating <= 5', name='ck_review_rating'),
    )


class ReviewStats(Base):
    """
    식당별 리뷰 통계
    - reviewCount: 총 리뷰 수
    - reviewAvg: 평균 평점
    - lastReviewAt: 마지막 리뷰 작성 시간
    """
    __tablename__ = "review_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    restaurantId = Column(Integer, ForeignKey("restaurants.id"), unique=True, nullable=False, index=True)
    reviewCount = Column(Integer, default=0, nullable=False)
    reviewAvg = Column(Float, default=0.0, nullable=False)
    lastReviewAt = Column(DateTime, nullable=True)
    
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 관계
    restaurant = relationship("Restaurant", back_populates="stats")
    
    __table_args__ = (
        UniqueConstraint('restaurantId', name='uq_stats_restaurant'),
    )
