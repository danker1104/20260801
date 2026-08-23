"""
Gemini 기반 리뷰 분석 랭커

리뷰 텍스트를 분석해 식당별 추천 점수를 계산한다.
"""
import json
import logging
import re
from typing import Dict, List, Optional

import httpx

from config import GEMINI_API_KEY, GEMINI_API_URL, GEMINI_MODEL, API_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class GeminiReviewRanker:
    """Gemini를 사용해 리뷰 기반 추천 점수를 생성한다."""

    SCORE_MIN = 0.0
    SCORE_MAX = 5.0

    POSITIVE_HINTS = [
        "맛있", "훌륭", "친절", "깔끔", "추천", "재방문", "만족", "신선", "좋았", "좋아요", "최고", "쾌적",
    ]
    NEGATIVE_HINTS = [
        "별로", "불친절", "짜", "싱겁", "비싸", "불편", "시끄", "느리", "최악", "실망", "아쉽", "재방문 의사",
    ]

    @staticmethod
    def _has_review_signal(review_count: int, review_avg: float, reviews: List[dict]) -> bool:
        if review_count > 0 and review_avg > 0:
            return True

        for rv in reviews or []:
            content = str(rv.get("content") or "").strip()
            if content:
                return True

        return False

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

    @staticmethod
    def _fallback_rank(restaurants: List[dict], review_payloads: List[dict]) -> List[dict]:
        """Gemini 호출 실패 시 별점+댓글 감성 통합 점수 계산"""
        score_by_external_id: Dict[str, Optional[float]] = {}
        reason_by_external_id: Dict[str, str] = {}

        def _star_score(review_avg: float, review_count: int) -> float:
            # 리뷰 수가 적을 때 과대평가를 방지하는 완만한 스무딩
            confidence = min(1.0, review_count / 20.0)
            normalized_avg = max(0.0, min(1.0, review_avg / 5.0))
            return normalized_avg * (0.35 + 0.65 * confidence)

        def _text_sentiment(reviews: List[dict]) -> float:
            if not reviews:
                return 0.5

            pos = 0
            neg = 0
            for rv in reviews:
                content = str(rv.get("content") or "").strip().lower()
                if not content:
                    continue

                pos += sum(1 for hint in GeminiReviewRanker.POSITIVE_HINTS if hint in content)
                neg += sum(1 for hint in GeminiReviewRanker.NEGATIVE_HINTS if hint in content)

            if pos == 0 and neg == 0:
                return 0.5

            return max(0.0, min(1.0, (pos + 1) / (pos + neg + 2)))

        for item in review_payloads:
            ext_id = str(item.get("externalId") or "")
            review_count = int(item.get("reviewCount") or 0)
            review_avg = float(item.get("reviewAvg") or 0.0)
            reviews = item.get("reviews") or []

            has_signal = GeminiReviewRanker._has_review_signal(review_count, review_avg, reviews)
            if not has_signal:
                score_by_external_id[ext_id] = None
                reason_by_external_id[ext_id] = "리뷰 댓글과 별점 데이터가 없어 평가하지 않았습니다."
                continue

            star_component = _star_score(review_avg, review_count)
            text_component = _text_sentiment(reviews)

            normalized = min(1.0, max(0.0, star_component * 0.7 + text_component * 0.3))
            score = normalized * GeminiReviewRanker.SCORE_MAX
            reason = (
                f"별점({review_avg:.1f}/5, {review_count}건)과 리뷰 텍스트 감성을 함께 반영했습니다."
            )

            score_by_external_id[ext_id] = score
            reason_by_external_id[ext_id] = reason

        ranked = []
        for restaurant in restaurants:
            ext_id = str(restaurant.get("externalId") or "")
            ai_score = score_by_external_id.get(ext_id)
            if ai_score is None:
                enriched = dict(restaurant)
                enriched["aiRecommendedScore"] = None
                enriched["aiRecommendationReason"] = reason_by_external_id.get(
                    ext_id,
                    "리뷰 댓글과 별점 데이터가 없어 평가하지 않았습니다.",
                )
                enriched["recommendScore"] = None
                ranked.append(enriched)
                continue

            raw_base_score = restaurant.get("recommendScore")
            has_base_score = raw_base_score is not None
            base_score = 0.0
            if has_base_score:
                try:
                    base_score = float(raw_base_score)
                except Exception:
                    has_base_score = False

            if has_base_score:
                # 0~1 점수가 들어오는 하위호환 처리
                if 0.0 <= base_score <= 1.0:
                    base_score *= GeminiReviewRanker.SCORE_MAX
                blended = min(
                    GeminiReviewRanker.SCORE_MAX,
                    max(GeminiReviewRanker.SCORE_MIN, base_score * 0.2 + ai_score * 0.8),
                )
            else:
                # base 점수가 없으면 리뷰 기반 AI 점수를 그대로 사용한다.
                blended = min(GeminiReviewRanker.SCORE_MAX, max(GeminiReviewRanker.SCORE_MIN, ai_score))

            enriched = dict(restaurant)
            enriched["aiRecommendedScore"] = ai_score
            enriched["aiRecommendationReason"] = reason_by_external_id.get(ext_id, "기본 점수 적용")
            enriched["recommendScore"] = blended
            ranked.append(enriched)

        ranked.sort(
            key=lambda x: x.get("recommendScore") if isinstance(x.get("recommendScore"), (int, float)) else -1,
            reverse=True,
        )
        return ranked[:10]

    async def rank_restaurants(self, restaurants: List[dict], review_payloads: List[dict]) -> List[dict]:
        """리뷰 데이터 기반으로 식당 목록을 재정렬해 상위 10개 반환"""
        if not restaurants:
            return []

        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY가 없어 fallback 랭킹으로 대체합니다")
            return self._fallback_rank(restaurants, review_payloads)

        prompt_payload = {
            "restaurants": review_payloads,
            "instruction": (
                "각 식당의 추천 점수(score: 0~5)를 계산할 때 별점 정보와 리뷰 댓글 내용을 반드시 통합 평가하라. "
                "별점 평균(reviewAvg, reviewCount)만 보지 말고 reviews[].content의 감성(긍정/부정)과 구체성도 반영하라. "
                "긍정 댓글과 높은 별점이 함께 많은 식당은 더 높은 점수를 주고, "
                "별점은 높지만 댓글이 부정적인 경우는 과대평가하지 말고 감점하라. "
                "리뷰 수가 적으면 신뢰도를 낮게 보고 점수를 보수적으로 책정하라. "
                "반드시 JSON만 반환하고 형식은 {\"scores\":[{\"externalId\":\"...\",\"score\":0.0,\"reason\":\"...\"}]} 로 유지한다."
            ),
        }

        endpoint = f"{GEMINI_API_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": json.dumps(prompt_payload, ensure_ascii=False)
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
                response = await client.post(endpoint, json=body)
                response.raise_for_status()
                result = response.json()

            text = (
                result.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

            parsed = self._extract_json_block(text)
            if not parsed or "scores" not in parsed or not isinstance(parsed["scores"], list):
                logger.warning("Gemini 응답 파싱 실패, fallback 랭킹 사용")
                return self._fallback_rank(restaurants, review_payloads)

            score_map: Dict[str, float] = {}
            reason_map: Dict[str, str] = {}

            # Gemini 점수가 일부만 내려오더라도 전체를 안정적으로 정렬하기 위해
            # 로컬 통합 점수를 기본값으로 함께 유지한다.
            fallback_ranked = self._fallback_rank(restaurants, review_payloads)
            fallback_score_map = {
                str(item.get("externalId") or ""): item.get("aiRecommendedScore")
                for item in fallback_ranked
            }
            has_signal_map = {
                str(item.get("externalId") or ""): self._has_review_signal(
                    int(item.get("reviewCount") or 0),
                    float(item.get("reviewAvg") or 0.0),
                    item.get("reviews") or [],
                )
                for item in review_payloads
            }

            for item in parsed["scores"]:
                external_id = str(item.get("externalId") or "")
                if not external_id:
                    continue

                score_val = item.get("score", 1.8)
                try:
                    score_val = float(score_val)
                except Exception:
                    score_val = 1.8

                # Gemini가 0~1로 반환하는 경우 0~5 스케일로 자동 확장
                if 0.0 <= score_val <= 1.0:
                    score_val *= GeminiReviewRanker.SCORE_MAX

                score_map[external_id] = min(GeminiReviewRanker.SCORE_MAX, max(GeminiReviewRanker.SCORE_MIN, score_val))
                reason_map[external_id] = str(item.get("reason") or "리뷰 분석 결과")

            ranked = []
            for restaurant in restaurants:
                ext_id = str(restaurant.get("externalId") or "")
                has_signal = has_signal_map.get(ext_id, False)
                if not has_signal:
                    enriched = dict(restaurant)
                    enriched["aiRecommendedScore"] = None
                    enriched["aiRecommendationReason"] = "리뷰 댓글과 별점 데이터가 없어 평가하지 않았습니다."
                    enriched["recommendScore"] = None
                    ranked.append(enriched)
                    continue

                gemini_score = score_map.get(ext_id)
                local_score = fallback_score_map.get(ext_id)
                if local_score is None:
                    enriched = dict(restaurant)
                    enriched["aiRecommendedScore"] = None
                    enriched["aiRecommendationReason"] = "리뷰 댓글과 별점 데이터가 없어 평가하지 않았습니다."
                    enriched["recommendScore"] = None
                    ranked.append(enriched)
                    continue

                ai_score = (gemini_score * 0.75 + local_score * 0.25) if gemini_score is not None else local_score
                raw_base_score = restaurant.get("recommendScore")
                has_base_score = raw_base_score is not None
                base_score = 0.0
                if has_base_score:
                    try:
                        base_score = float(raw_base_score)
                    except Exception:
                        has_base_score = False

                if has_base_score:
                    # 0~1 점수가 들어오는 하위호환 처리
                    if 0.0 <= base_score <= 1.0:
                        base_score *= GeminiReviewRanker.SCORE_MAX
                    blended = min(
                        GeminiReviewRanker.SCORE_MAX,
                        max(GeminiReviewRanker.SCORE_MIN, base_score * 0.2 + ai_score * 0.8),
                    )
                else:
                    # base 점수가 없으면 리뷰 기반 AI 점수를 그대로 사용한다.
                    blended = min(GeminiReviewRanker.SCORE_MAX, max(GeminiReviewRanker.SCORE_MIN, ai_score))

                enriched = dict(restaurant)
                enriched["aiRecommendedScore"] = ai_score
                enriched["aiRecommendationReason"] = reason_map.get(
                    ext_id,
                    "별점과 댓글 감성을 통합해 기본 점수를 적용했습니다.",
                )
                enriched["recommendScore"] = blended
                ranked.append(enriched)

            ranked.sort(
                key=lambda x: x.get("recommendScore") if isinstance(x.get("recommendScore"), (int, float)) else -1,
                reverse=True,
            )
            return ranked[:10]
        except Exception as exc:
            logger.warning("Gemini 랭킹 실패, fallback 랭킹 사용: %s", str(exc))
            return self._fallback_rank(restaurants, review_payloads)
