"""
대구푸드 공공 API 클라이언트

카카오 검색 결과를 대구푸드 데이터와 매칭해 상세 정보를 보강한다.
"""
import html
import json
import logging
import re
import time
from collections import Counter
from typing import Dict, List, Optional

import aiohttp

from config import (
    API_TIMEOUT_SECONDS,
    DAEGU_FOOD_API_URL,
    DAEGU_FOOD_CACHE_TTL_SECONDS,
    DAEGU_FOOD_DEFAULT_ADDR,
)

logger = logging.getLogger(__name__)


class DaeguFoodClient:
    """대구푸드 공공 API 클라이언트"""

    _cache: Dict[str, Dict[str, object]] = {}
    VALID_ADDRS = {
        "중구",
        "동구",
        "서구",
        "남구",
        "북구",
        "수성구",
        "달서구",
        "달성군",
    }

    @staticmethod
    def _clean_text(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = html.unescape(str(value))
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return None
        if text in {"없음", "없습니다.", "가능한 외국어가 없습니다."}:
            return None
        return text

    @staticmethod
    def _normalize(value: Optional[str]) -> str:
        if not value:
            return ""
        return re.sub(r"[^0-9a-zA-Z가-힣]", "", value).lower()

    @classmethod
    def extract_addr(cls, raw_text: Optional[str]) -> Optional[str]:
        """문자열에서 대구 구/군 값을 추출"""
        text = cls._clean_text(raw_text)
        if not text:
            return None

        match = re.search(r"(중구|동구|서구|남구|북구|수성구|달서구|달성군)", text)
        if not match:
            return None

        addr = match.group(1)
        return addr if addr in cls.VALID_ADDRS else None

    @classmethod
    def _normalize_addr(cls, addr: Optional[str]) -> Optional[str]:
        if not addr:
            return None
        cleaned = str(addr).strip()
        return cleaned if cleaned in cls.VALID_ADDRS else cls.extract_addr(cleaned)

    def _build_restaurant_addr_map(
        self,
        restaurants: List[dict],
        preferred_addr: Optional[str] = None,
        user_address: Optional[str] = None,
    ) -> List[str]:
        """
        식당별 대구 구/군을 계산한다.
        1) 식당 주소 추출값
        2) 사용자 주소/선호 addr
        3) 목록 다수결
        4) 기본값
        """
        detected = []
        for restaurant in restaurants:
            detected.append(self.extract_addr(restaurant.get("address")))

        fallback_candidates = [
            self._normalize_addr(preferred_addr),
            self.extract_addr(user_address),
        ]

        counts = Counter([x for x in detected if x])
        majority = counts.most_common(1)[0][0] if counts else None
        fallback_candidates.append(majority)
        fallback_candidates.append(self._normalize_addr(DAEGU_FOOD_DEFAULT_ADDR))

        fallback_addr = next((x for x in fallback_candidates if x), "중구")
        return [addr or fallback_addr for addr in detected]

    async def get_restaurants(self, addr: Optional[str] = None) -> List[dict]:
        """행정구역별 대구푸드 식당 목록 조회 (TTL 캐시)"""
        target_addr = self._normalize_addr(addr) or self._normalize_addr(DAEGU_FOOD_DEFAULT_ADDR) or "중구"

        cached = self._cache.get(target_addr)
        now = time.time()
        if cached and (now - float(cached.get("ts", 0))) < DAEGU_FOOD_CACHE_TTL_SECONDS:
            return list(cached.get("data", []))

        params = {
            "mode": "json",
            "addr": target_addr,
        }

        if not DAEGU_FOOD_API_URL.startswith("https://"):
            logger.error("대구푸드 API는 HTTPS URL이어야 합니다")
            return []

        api_urls = [DAEGU_FOOD_API_URL]

        payload = None
        last_error = None
        try:
            async with aiohttp.ClientSession() as session:
                for api_url in api_urls:
                    try:
                        async with session.get(
                            api_url,
                            params=params,
                            headers={
                                "User-Agent": "WhatToEat/1.0",
                                "Accept": "application/json,text/plain,*/*",
                            },
                            timeout=aiohttp.ClientTimeout(total=API_TIMEOUT_SECONDS),
                        ) as response:
                            if response.status != 200:
                                logger.warning("대구푸드 API 오류: status=%s, addr=%s", response.status, target_addr)
                                continue
                            raw_bytes = await response.read()
                            decoded = None
                            for enc in ("utf-8", "cp949", "euc-kr"):
                                try:
                                    decoded = raw_bytes.decode(enc)
                                    break
                                except Exception:
                                    continue

                            if decoded is None:
                                raise ValueError("대구푸드 응답 디코딩 실패")

                            payload = json.loads(decoded)
                            break
                    except Exception as inner_exc:
                        last_error = inner_exc
                        continue

            if payload is None:
                if last_error:
                    raise last_error
                return []

            data = payload.get("data", []) if isinstance(payload, dict) else []
            if not isinstance(data, list):
                data = []

            self._cache[target_addr] = {
                "ts": now,
                "data": data,
            }
            return data
        except Exception as exc:
            logger.warning("대구푸드 API 호출 실패: %s", str(exc))
            return []

    async def enrich_restaurants(
        self,
        restaurants: List[dict],
        preferred_addr: Optional[str] = None,
        user_address: Optional[str] = None,
    ) -> List[dict]:
        """식당 목록을 구/군별 API 1회 호출로 보강"""
        if not restaurants:
            return []

        addr_map = self._build_restaurant_addr_map(
            restaurants,
            preferred_addr=preferred_addr,
            user_address=user_address,
        )

        unique_addrs = sorted(set(addr_map))
        rows_by_addr: Dict[str, List[dict]] = {}
        for addr in unique_addrs:
            rows_by_addr[addr] = await self.get_restaurants(addr=addr)

        enriched = []
        for idx, restaurant in enumerate(restaurants):
            rows = rows_by_addr.get(addr_map[idx], [])
            enriched.append(self.enrich_restaurant(restaurant, rows))

        return enriched

    def find_best_match(self, restaurant: dict, daegu_rows: List[dict]) -> Optional[dict]:
        """카카오 식당 1건에 가장 가까운 대구푸드 레코드를 선택"""
        if not daegu_rows:
            return None

        name = self._normalize(restaurant.get("name"))
        address = self._normalize(restaurant.get("address"))
        category = self._normalize(restaurant.get("category"))
        if not name:
            return None

        best = None
        best_score = 0

        for row in daegu_rows:
            row_name_raw = self._clean_text(row.get("BZ_NM"))
            row_name = self._normalize(row_name_raw)
            if not row_name:
                continue

            score = 0
            if row_name == name:
                score += 4
            elif row_name in name or name in row_name:
                score += 2

            row_addr = self._normalize(self._clean_text(row.get("GNG_CS")))
            if address and row_addr and (row_addr in address or address in row_addr):
                score += 2

            row_category = self._normalize(self._clean_text(row.get("FD_CS")))
            if category and row_category and (row_category == category or row_category in category or category in row_category):
                score += 1

            if score > best_score:
                best_score = score
                best = row

        return best if best_score >= 3 else None

    def enrich_restaurant(self, restaurant: dict, daegu_rows: List[dict]) -> dict:
        """대구푸드 상세 필드를 식당 데이터에 병합"""
        matched = self.find_best_match(restaurant, daegu_rows)

        enriched = dict(restaurant)
        if matched:
            enriched["daeguFoodId"] = self._clean_text(matched.get("OPENDATA_ID"))
            enriched["daeguBusinessHours"] = self._clean_text(matched.get("MBZ_HR"))
            enriched["daeguPhone"] = self._clean_text(matched.get("TLNO"))
            enriched["daeguMenu"] = self._clean_text(matched.get("MNU"))
            enriched["daeguDescription"] = self._clean_text(matched.get("SMPL_DESC"))
            enriched["daeguParking"] = self._clean_text(matched.get("PKPL"))
            enriched["daeguReservation"] = self._clean_text(matched.get("BKN_YN"))
            enriched["daeguSubway"] = self._clean_text(matched.get("SBW"))
            enriched["daeguBus"] = self._clean_text(matched.get("BUS"))
            enriched["daeguHomepage"] = self._clean_text(matched.get("HP"))
            if not enriched.get("category"):
                enriched["category"] = self._clean_text(matched.get("FD_CS"))
            if not enriched.get("address"):
                enriched["address"] = self._clean_text(matched.get("GNG_CS"))
        else:
            enriched["daeguFoodId"] = None
            enriched["daeguBusinessHours"] = None
            enriched["daeguPhone"] = None
            enriched["daeguMenu"] = None
            enriched["daeguDescription"] = None
            enriched["daeguParking"] = None
            enriched["daeguReservation"] = None
            enriched["daeguSubway"] = None
            enriched["daeguBus"] = None
            enriched["daeguHomepage"] = None

        return enriched

