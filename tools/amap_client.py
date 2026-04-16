from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import List, Optional

from config import AMAP_BASE_URL, AMAP_KEY, DEFAULT_SEARCH_RADIUS, REQUEST_TIMEOUT
from tool_types import ApiResult, PoiItem, RouteResult


def _http_get(url: str) -> dict:
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def geocode(address: str, city: Optional[str] = None) -> ApiResult:
    if not AMAP_KEY:
        return ApiResult(ok=False, source="amap", error="缺少 AMAP_KEY 环境变量")

    params = {"key": AMAP_KEY, "address": address}
    if city:
        params["city"] = city

    url = f"{AMAP_BASE_URL}/geocode/geo?{urllib.parse.urlencode(params)}"

    try:
        payload = _http_get(url)
        geocodes = payload.get("geocodes", [])
        if not geocodes:
            return ApiResult(ok=False, source="amap", error="未找到地理编码结果")
        return ApiResult(ok=True, source="amap", data=geocodes[0])
    except Exception as exc:
        return ApiResult(ok=False, source="amap", error=str(exc))


def search_poi(keyword: str, city: str) -> ApiResult:
    if not AMAP_KEY:
        return ApiResult(ok=False, source="amap", error="缺少 AMAP_KEY 环境变量")

    params = {"key": AMAP_KEY, "keywords": keyword, "city": city, "output": "json"}
    url = f"{AMAP_BASE_URL}/place/text?{urllib.parse.urlencode(params)}"

    try:
        payload = _http_get(url)
        pois = [
            PoiItem(
                name=item.get("name", ""),
                address=item.get("address", ""),
                location=item.get("location", ""),
                district=item.get("district", ""),
                poi_type=item.get("type", ""),
            )
            for item in payload.get("pois", [])
        ]
        return ApiResult(ok=True, source="amap", data=pois)
    except Exception as exc:
        return ApiResult(ok=False, source="amap", error=str(exc))


def search_nearby(location: str, keyword: str, radius: int = DEFAULT_SEARCH_RADIUS) -> ApiResult:
    if not AMAP_KEY:
        return ApiResult(ok=False, source="amap", error="缺少 AMAP_KEY 环境变量")

    params = {
        "key": AMAP_KEY,
        "location": location,
        "keywords": keyword,
        "radius": radius,
        "output": "json",
    }
    url = f"{AMAP_BASE_URL}/place/around?{urllib.parse.urlencode(params)}"

    try:
        payload = _http_get(url)
        pois = [
            PoiItem(
                name=item.get("name", ""),
                address=item.get("address", ""),
                location=item.get("location", ""),
                district=item.get("district", ""),
                poi_type=item.get("type", ""),
            )
            for item in payload.get("pois", [])
        ]
        return ApiResult(ok=True, source="amap", data=pois)
    except Exception as exc:
        return ApiResult(ok=False, source="amap", error=str(exc))


def plan_route(origin: str, destination: str, city: str, mode: str = "walking") -> ApiResult:
    if not AMAP_KEY:
        return ApiResult(ok=False, source="amap", error="缺少 AMAP_KEY 环境变量")

    if mode == "walking":
        endpoint = "/direction/walking"
        params = {"key": AMAP_KEY, "origin": origin, "destination": destination}
    elif mode == "driving":
        endpoint = "/direction/driving"
        params = {"key": AMAP_KEY, "origin": origin, "destination": destination, "strategy": 0}
    elif mode == "transit":
        endpoint = "/direction/transit/integrated"
        params = {
            "key": AMAP_KEY,
            "origin": origin,
            "destination": destination,
            "city": city,
            "strategy": 0,
        }
    else:
        return ApiResult(ok=False, source="amap", error=f"不支持的路线模式: {mode}")

    url = f"{AMAP_BASE_URL}{endpoint}?{urllib.parse.urlencode(params)}"

    try:
        payload = _http_get(url)
        route = payload.get("route", {})

        if mode == "transit":
            transits = route.get("transits", [])
            if not transits:
                return ApiResult(ok=False, source="amap", error="未找到公交路线")
            best = transits[0]
            result = RouteResult(
                mode=mode,
                origin=origin,
                destination=destination,
                distance_m=0,
                duration_s=int(best.get("duration", 0)),
                summary=f"公交约 {int(best.get('duration', 0)) // 60} 分钟",
                cost=float(best.get("cost", 0) or 0),
            )
        else:
            paths = route.get("paths", [])
            if not paths:
                return ApiResult(ok=False, source="amap", error="未找到路线结果")
            best = paths[0]
            distance = int(best.get("distance", 0))
            duration = int(best.get("duration", 0))
            result = RouteResult(
                mode=mode,
                origin=origin,
                destination=destination,
                distance_m=distance,
                duration_s=duration,
                summary=f"{mode} 约 {duration // 60} 分钟，{distance // 1000:.1f} 公里",
            )
        return ApiResult(ok=True, source="amap", data=result)
    except Exception as exc:
        return ApiResult(ok=False, source="amap", error=str(exc))
