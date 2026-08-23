"""
Gemini 기반 이벤트성 리뷰 스파이크 필터.

특정 기간에 리뷰가 급증하면 Gemini로 이벤트/캠페인성 여부를 판정하고,
이벤트성으로 판단되면 해당 기간의 리뷰를 자동 삭제한다.
"""
from datetime import datetime, timedelta
import json
import logging
import re
from typing import Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    API_TIMEOUT_SECONDS,
    GEMINI_API_KEY,
    GEMINI_API_URL,
    GEMINI_MODEL,
    REVIEW_EVENT_AI_CONFIDENCE_THRESHOLD,
    REVIEW_EVENT_FILTER_ENABLED,
    REVIEW_SPIKE_MIN_COUNT,
    REVIEW_SPIKE_MULTIPLIER,
    REVIEW_SPIKE_WINDOW_HOURS,
)
from repositories.review_repository import ReviewRepository
from models import Review

logger = logging.getLogger(__name__)


class ReviewEventFilterService:
    """리뷰 폭증 구간의 이벤트성 리뷰를 탐지/삭제한다."""

    def __init__(self):
        self.review_repo = ReviewRepository(Review)

    @staticmethod
    def _extract_json_block(text: str) -> Optional[dict]:
        if not text:
            return None

        stripped = text.strip()
        try:
            return json.loads(stripped)
        except Exception:
            pass

        block_match = re.search(r"```json\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
        if block_match:
            try:
                return json.loads(block_match.group(1))
            except Exception:
                return None

        raw_match = re.search(r"(\{.*\})", stripped, flags=re.DOTALL)
        if raw_match:
            try:
                return json.loads(raw_match.group(1))
            except Exception:
                return None

        return None

    async def _is_event_campaign_by_gemini(
        self,
        restaurant_name: str,
        reviews: List[Review],
    ) -> Dict[str, object]:
        """Gemini로 이벤트성 리뷰 폭증 여부를 판정한다."""
        if not GEMINI_API_KEY:
            return {
                "isEventCampaign": False,
                "confidence": 0.0,
                "reason": "GEMINI_API_KEY 미설정",
            }

        sample = [
            {
                "id": r.id,
                "rating": r.rating,
                "content": (r.content or "")[:400],
                "createdAt": r.createdAt.isoformat() if r.createdAt else None,
                "userId": r.userId,
            }
            for r in reviews[:60]
        ]

        prompt = {
            "restaurantName": restaurant_name,
            "instruction": (
                "아래 리뷰 묶음이 자연스러운 일반 방문 후기인지, "
                "이벤트/체험단/리워드성 캠페인으로 단기간 집중 생성된 후기인지 판정하라. "
                "판정 기준은 문체 반복, 과도한 긍정 편향, 유사 패턴, 짧은 시간 밀집도, "
                "광고성 표현 여부를 종합한다. "
                "반드시 JSON만 반환하라: "
                "{\"isEventCampaign\": true|false, \"confidence\": 0~1, \"reason\": \"...\"}"
            ),
            "reviews": sample,
        }

        endpoint = f"{GEMINI_API_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        body = {
            "contents": [{"parts": [{"text": json.dumps(prompt, ensure_ascii=False)}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
                response = await client.post(endpoint, json=body)
                response.raise_for_status()
                payload = response.json()

            text = (
                payload.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            parsed = self._extract_json_block(text) or {}

            is_event = bool(parsed.get("isEventCampaign", False))
            confidence = parsed.get("confidence", 0.0)
            try:
                confidence = float(confidence)
            except Exception:
                confidence = 0.0

            reason = str(parsed.get("reason") or "Gemini 판정 결과")
            return {
                "isEventCampaign": is_event,
                "confidence": max(0.0, min(1.0, confidence)),
                "reason": reason,
            }
        except Exception as exc:
            logger.warning("이벤트성 리뷰 Gemini 판정 실패: %s", str(exc))
            return {
                "isEventCampaign": False,
                "confidence": 0.0,
                "reason": f"Gemini 판정 실패: {str(exc)}",
            }

    async def detect_and_purge_spike_reviews(
        self,
        db: AsyncSession,
        restaurant_id: int,
        restaurant_name: str,
    ) -> Dict[str, object]:
        """
        리뷰 급증 구간을 감지하고 이벤트성으로 판정되면 해당 구간 리뷰를 삭제한다.
        """
        if not REVIEW_EVENT_FILTER_ENABLED:
            return {
                "deleted": 0,
                "spike": False,
                "reason": "리뷰 이벤트 필터 비활성화",
            }

        now = datetime.utcnow()
        window = timedelta(hours=max(1, REVIEW_SPIKE_WINDOW_HOURS))
        current_start = now - window
        previous_start = current_start - window

        current_reviews = await self.review_repo.get_in_period(
            db,
            restaurant_id=restaurant_id,
            start_at=current_start,
            end_at=now,
            limit=500,
        )
        current_count = len(current_reviews)

        if current_count < REVIEW_SPIKE_MIN_COUNT:
            return {
                "deleted": 0,
                "spike": False,
                "reason": "리뷰 수가 최소 임계치 미만",
            }

        previous_count = await self.review_repo.count_in_period(
            db,
            restaurant_id=restaurant_id,
            start_at=previous_start,
            end_at=current_start,
        )

        baseline = max(1, previous_count)
        spike_ratio = current_count / baseline
        is_spike = spike_ratio >= REVIEW_SPIKE_MULTIPLIER

        if not is_spike:
            return {
                "deleted": 0,
                "spike": False,
                "reason": f"스파이크 미충족 (ratio={spike_ratio:.2f})",
            }

        ai_judgement = await self._is_event_campaign_by_gemini(
            restaurant_name=restaurant_name,
            reviews=current_reviews,
        )
        is_event = bool(ai_judgement.get("isEventCampaign", False))
        confidence = float(ai_judgement.get("confidence", 0.0) or 0.0)

        if not is_event or confidence < REVIEW_EVENT_AI_CONFIDENCE_THRESHOLD:
            return {
                "deleted": 0,
                "spike": True,
                "reason": f"Gemini 비이벤트 판정 또는 신뢰도 부족(confidence={confidence:.2f})",
            }

        review_ids = [r.id for r in current_reviews]
        deleted_count = await self.review_repo.delete_by_ids(db, review_ids)

        logger.warning(
            "이벤트성 리뷰 삭제: restaurant_id=%s, deleted=%s, window_hours=%s, reason=%s",
            restaurant_id,
            deleted_count,
            REVIEW_SPIKE_WINDOW_HOURS,
            ai_judgement.get("reason", ""),
        )

        return {
            "deleted": deleted_count,
            "spike": True,
            "reason": str(ai_judgement.get("reason") or "이벤트성 리뷰로 판정되어 삭제"),
        }
