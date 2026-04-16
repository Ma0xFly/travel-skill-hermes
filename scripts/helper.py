from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from amap_client import geocode, plan_route
from weather_client import build_weather_summary
from web_search import search_web

DEFAULT_PROFILE: Dict[str, Any] = {
    "intent": "都要",
    "crowd_preference": "适中",
    "duration": "一天",
    "travel_type": "朋友",
    "budget": None,
    "first_time": None,
    "known_info": [],
}

ALLOWED_INTENTS = {"想玩", "想吃", "都要"}
ALLOWED_CROWD_PREFERENCES = {"热闹", "适中", "人少"}
ALLOWED_DURATIONS = {"半天", "一天", "晚上"}
ALLOWED_TRAVEL_TYPES = {"情侣", "朋友", "家庭", "独行"}
ALLOWED_ROUTE_MODES = {"walking", "driving", "transit"}

SUPPORTED_CITIES = {
    "上海", "杭州", "成都", "重庆", "广州", "深圳", "长沙", "郴州",
    "清远", "衡阳", "北京", "南京", "苏州", "武汉", "西安",
}

INTENT_PATTERNS = [
    ("都要", ["逛吃", "玩吃", "边玩边吃", "又想玩又想吃", "都要", "一起安排", "顺便吃饭"]),
    ("想吃", ["吃什么", "美食", "餐厅", "馆子", "饭店", "夜宵", "小吃", "想吃"]),
    ("想玩", ["玩什么", "去哪玩", "景点", "打卡", "逛逛", "游玩", "想玩"]),
]
CROWD_PATTERNS = [
    ("人少", ["人少", "避开人流", "别太挤", "不喜欢拥挤", "不想排队", "清净", "安静", "小众"]),
    ("热闹", ["热闹", "人多一点", "烟火气", "繁华", "热闹点", "越热闹越好"]),
    ("适中", ["适中", "别太冷清", "平衡一点"]),
]
DURATION_PATTERNS = [
    ("晚上", ["晚上", "夜里", "夜游", "晚饭后", "今晚"]),
    ("半天", ["半天", "半日", "下午", "上午"]),
    ("一天", ["一天", "一日", "全天"]),
]
TRAVEL_TYPE_PATTERNS = [
    ("情侣", ["情侣", "约会", "和对象", "和男朋友", "和女朋友", "两个人"]),
    ("家庭", ["家庭", "带娃", "亲子", "爸妈", "老人", "全家"]),
    ("独行", ["一个人", "独自", "独行", "solo"]),
    ("朋友", ["朋友", "同学", "闺蜜", "兄弟", "同事"]),
]
FIRST_TIME_TRUE_PATTERNS = ["第一次来", "初次来", "第一次去", "头一回来", "第一次到"]
FIRST_TIME_FALSE_PATTERNS = ["不是第一次", "来过很多次", "之前来过", "去过好几次", "熟一点"]
KNOWN_INFO_HINTS = {
    "夜景": ["夜景", "灯光", "江边", "江景", "citywalk夜景"],
    "拍照": ["拍照", "出片", "打卡", "好看", "氛围感"],
    "小吃": ["小吃", "路边摊", "夜宵", "街边吃的"],
    "本地菜": ["本地菜", "当地特色", "特色馆子", "地道"],
    "预算敏感": ["别太贵", "省钱", "预算有限", "穷游", "性价比"],
    "不想排队": ["不想排队", "别排太久", "少排队", "排队短一点"],
}
BUDGET_RANGE_PATTERNS = [
    re.compile(r"预算\s*(\d{2,5})\s*[到\-~至]\s*(\d{2,5})\s*元?"),
    re.compile(r"(\d{2,5})\s*[到\-~至]\s*(\d{2,5})\s*元\s*(预算|以内)?"),
]
BUDGET_SINGLE_PATTERNS = [
    re.compile(r"预算\s*(\d{2,5})\s*元"),
    re.compile(r"人均\s*(\d{2,5})\s*元"),
    re.compile(r"(\d{2,5})\s*元以内"),
]
WEATHER_HINTS = ["天气", "气温", "下雨", "适合出游", "适合旅游", "穿什么"]
ROUTE_HINTS = ["怎么走", "路线", "导航", "步行", "公交", "驾车"]
WEB_SEARCH_HINTS = ["最新", "实时", "最近", "官网", "开放时间", "营业时间", "票价", "门票", "政策"]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())


def extract_city(text: str) -> Optional[str]:
    for city in SUPPORTED_CITIES:
        if city in text:
            return city
    match = re.search(r"去([\u4e00-\u9fa5]{2,6})(玩|旅游|逛|吃)", text)
    return match.group(1) if match else None


def extract_by_patterns(text: str, mapping: List[tuple[str, List[str]]]) -> Optional[str]:
    for target, patterns in mapping:
        if any(keyword in text for keyword in patterns):
            return target
    return None


def extract_first_time(text: str) -> Optional[bool]:
    if any(keyword in text for keyword in FIRST_TIME_FALSE_PATTERNS):
        return False
    if any(keyword in text for keyword in FIRST_TIME_TRUE_PATTERNS):
        return True
    return None


def extract_budget(text: str) -> Optional[str]:
    for pattern in BUDGET_RANGE_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"{match.group(1)}-{match.group(2)}"
    for pattern in BUDGET_SINGLE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    if any(x in text for x in ["别太贵", "省钱", "穷游"]):
        return "预算敏感"
    return None


def extract_known_info(text: str) -> List[str]:
    clues: List[str] = []
    for label, keywords in KNOWN_INFO_HINTS.items():
        if any(keyword in text for keyword in keywords):
            clues.append(label)
    return clues


def infer_intent(text: str) -> str:
    return extract_by_patterns(text, INTENT_PATTERNS) or "都要"


def infer_route_mode(text: str) -> str:
    if "公交" in text or "地铁" in text:
        return "transit"
    if "驾车" in text or "开车" in text:
        return "driving"
    return "walking"


def infer_request_type(text: str) -> str:
    if any(keyword in text for keyword in WEATHER_HINTS):
        return "weather"
    if ("从" in text and "到" in text) or any(keyword in text for keyword in ROUTE_HINTS):
        return "route"
    if any(keyword in text for keyword in WEB_SEARCH_HINTS):
        return "web_search"
    return "recommendation"


def extract_route_points(text: str) -> Dict[str, Optional[str]]:
    match = re.search(r"从(.+?)到(.+?)(怎么走|路线|导航|最方便|最划算|步行|公交|驾车|$)", text)
    if not match:
        return {"origin": None, "destination": None}
    return {"origin": match.group(1).strip("，。！？； "), "destination": match.group(2).strip("，。！？； ")}


def build_web_search_query(raw_query: str, city: Optional[str], known_info: List[str]) -> str:
    parts: List[str] = [city] if city else []
    parts.extend(known_info[:2])
    parts.append(raw_query)
    return " ".join(part for part in parts if part)


def parse_query(query: str) -> Dict[str, Any]:
    text = normalize_text(query)
    route_points = extract_route_points(text)
    known_info = extract_known_info(text)
    city = extract_city(text)
    return {
        "city": city,
        "intent": infer_intent(text),
        "crowd_preference": extract_by_patterns(text, CROWD_PATTERNS),
        "duration": extract_by_patterns(text, DURATION_PATTERNS),
        "travel_type": extract_by_patterns(text, TRAVEL_TYPE_PATTERNS),
        "budget": extract_budget(text),
        "first_time": extract_first_time(text),
        "known_info": known_info,
        "request_type": infer_request_type(text),
        "route_mode": infer_route_mode(text),
        "origin": route_points["origin"],
        "destination": route_points["destination"],
        "search_query": build_web_search_query(query, city, known_info),
        "raw_query": query,
    }


def merge_known_info(explicit_value: Any, parsed_value: Any) -> List[str]:
    merged: List[str] = []
    for value in [explicit_value, parsed_value]:
        if not value:
            continue
        merged.extend([value] if isinstance(value, str) else value)
    deduped: List[str] = []
    for item in merged:
        if item and item not in deduped:
            deduped.append(item)
    return deduped


def build_profile(user_input: Dict[str, Any]) -> Dict[str, Any]:
    query = user_input.get("query") or user_input.get("text") or ""
    parsed = parse_query(query) if query else {}
    profile = dict(DEFAULT_PROFILE)
    profile.update({k: v for k, v in parsed.items() if v not in (None, "", [])})
    profile.update({k: v for k, v in user_input.items() if v not in (None, "", [])})
    profile["known_info"] = merge_known_info(user_input.get("known_info"), parsed.get("known_info"))
    return profile


def validate_profile(profile: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    request_type = profile.get("request_type", "recommendation")
    if request_type in {"weather", "recommendation"} and not profile.get("city"):
        errors.append("缺少 city，当前请求至少需要城市信息。")
    if request_type == "route":
        if not profile.get("origin"):
            errors.append("路线查询缺少 origin。")
        if not profile.get("destination"):
            errors.append("路线查询缺少 destination。")
        if profile.get("route_mode", "walking") not in ALLOWED_ROUTE_MODES:
            errors.append(f"route_mode 不合法：{profile.get('route_mode')}")
    if profile.get("intent") not in ALLOWED_INTENTS:
        errors.append(f"intent 不合法：{profile.get('intent')}")
    if profile.get("crowd_preference") and profile.get("crowd_preference") not in ALLOWED_CROWD_PREFERENCES:
        errors.append(f"crowd_preference 不合法：{profile.get('crowd_preference')}")
    if profile.get("duration") and profile.get("duration") not in ALLOWED_DURATIONS:
        errors.append(f"duration 不合法：{profile.get('duration')}")
    if profile.get("travel_type") and profile.get("travel_type") not in ALLOWED_TRAVEL_TYPES:
        errors.append(f"travel_type 不合法：{profile.get('travel_type')}")
    return errors


def summarize_known_info(known_info: Optional[List[str]]) -> str:
    return "未提供额外图片或文字线索，按常规偏好规划。" if not known_info else "已识别补充线索：" + "；".join(known_info)


def build_response_outline(profile: Dict[str, Any]) -> Dict[str, Any]:
    request_type = profile.get("request_type", "recommendation")
    intent = profile.get("intent", "都要")
    if request_type == "weather":
        sections = ["天气概览", "未来预报", "出行建议"]
    elif request_type == "route":
        sections = ["路线概览", "起终点", "时长和距离", "补充建议"]
    elif request_type == "web_search":
        sections = ["搜索结论", "结果列表", "使用建议"]
    elif intent == "想玩":
        sections = ["总判断", "景点推荐", "时间安排", "注意事项"]
    elif intent == "想吃":
        sections = ["总判断", "餐厅推荐", "推荐菜", "踩坑提醒"]
    else:
        sections = ["总判断", "主路线", "备选方案", "避坑提醒"]
    return {
        "city": profile.get("city"),
        "request_type": request_type,
        "intent": intent,
        "duration": profile.get("duration", "一天"),
        "crowd_preference": profile.get("crowd_preference", "适中"),
        "summary": summarize_known_info(profile.get("known_info")),
        "sections": sections,
    }


def handle_weather_request(profile: Dict[str, Any]) -> Dict[str, Any]:
    return build_weather_summary(profile["city"]).to_dict()


def handle_route_request(profile: Dict[str, Any]) -> Dict[str, Any]:
    city = profile.get("city")
    origin_result = geocode(profile["origin"], city)
    if not origin_result.ok:
        return origin_result.to_dict()
    destination_result = geocode(profile["destination"], city)
    if not destination_result.ok:
        return destination_result.to_dict()
    origin_location = origin_result.data.get("location", "")
    destination_location = destination_result.data.get("location", "")
    route_result = plan_route(origin_location, destination_location, city or "", profile.get("route_mode", "walking"))
    return {
        "ok": route_result.ok,
        "source": route_result.source,
        "origin": profile.get("origin"),
        "destination": profile.get("destination"),
        "origin_location": origin_location,
        "destination_location": destination_location,
        "data": route_result.data.to_dict() if route_result.ok and route_result.data else None,
        "error": route_result.error,
    }


def handle_web_search_request(profile: Dict[str, Any]) -> Dict[str, Any]:
    result = search_web(profile.get("search_query") or profile.get("raw_query") or "")
    return result.to_dict() if not result.ok else {"ok": True, "source": result.source, "data": result.data.to_dict()}


def handle_recommendation_request(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "source": "travel-skill", "data": {"profile": profile, "outline": build_response_outline(profile)}}


def route_request(user_input: Dict[str, Any]) -> Dict[str, Any]:
    profile = build_profile(user_input)
    errors = validate_profile(profile)
    if errors:
        return {"ok": False, "source": "travel-skill", "errors": errors, "profile": profile}
    request_type = profile.get("request_type", "recommendation")
    if request_type == "weather":
        return handle_weather_request(profile)
    if request_type == "route":
        return handle_route_request(profile)
    if request_type == "web_search":
        return handle_web_search_request(profile)
    return handle_recommendation_request(profile)


def to_pretty_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    sample_inputs = [
        {"query": "帮我看看杭州这两天天气怎么样，适不适合旅游？"},
        {"query": "从橘子洲到岳麓山怎么走，公交最划算吗？", "city": "长沙"},
        {"query": "帮我查一下上海博物馆最新开放时间和预约政策"},
        {"query": "我和对象第一次去杭州玩半天，想拍照，不想排长队，顺便吃点本地菜，预算300到500元。"},
    ]
    for sample in sample_inputs:
        print(to_pretty_json(route_request(sample)))
        print("-" * 60)
