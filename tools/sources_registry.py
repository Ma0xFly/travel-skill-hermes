# -*- coding: utf-8 -*-
"""
sources_registry.py — travel-skill 信源注册表（声明式）

设计：
- 每个信源是一个 dict，声明 name/role/env_key/proxy/weight/enabled/callable
- _call_* 函数在 import 时不执行任何网络请求（惰性调用）
- 新增信源 = 在 ENGINES / TRAVEL_SOURCES 里加一个条目 + 一个 _call_* 函数，无需改调用方
- 优先级：weight 越大越靠前（Exa 中文内容密度实测优于 Tavily，故主力）
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
import urllib.request

REQUEST_TIMEOUT = 12
UA = {"User-Agent": "travel-skill/1.1 (sources-registry)"}

_EXA_PROXY = "http://127.0.0.1:7897"  # Clash Verge 混合端口；无代理环境自动跳过 exa


def _http_get_json(url: str, timeout: int = REQUEST_TIMEOUT, proxy: str | None = None) -> dict:
    req = urllib.request.Request(url, headers=UA)
    if proxy:
        handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        opener = urllib.request.build_opener(handler)
    else:
        opener = urllib.request.build_opener()
    with opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------- Exa
def _call_exa(query: str, limit: int) -> list[dict]:
    """mcporter call exa.web_search_exa —— 返回带正文高亮的网页结果"""
    import subprocess

    env = dict(os.environ)
    env.setdefault("https_proxy", _EXA_PROXY)
    env.setdefault("http_proxy", _EXA_PROXY)
    cmd = ["mcporter", "call", "exa.web_search_exa", f"query={query}", f"numResults={limit}"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
    if out.returncode != 0 or not out.stdout.strip():
        raise RuntimeError(f"exa exit={out.returncode}: {out.stderr[:200]}")
    return _parse_exa_stdout(out.stdout)


def _parse_exa_stdout(text: str) -> list[dict]:
    """mcporter 文本输出 → 结构化结果；解析失败返回空列表（交给下一个引擎）"""
    items: list[dict] = []
    blocks = text.split("Title:")
    for b in blocks[1:]:
        lines = b.strip().splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        url = highlight = ""
        for ln in lines[1:]:
            s = ln.strip()
            if s.startswith("URL:"):
                url = s[4:].strip()
            elif s.startswith("Highlights:"):
                highlight = " ".join(x.strip() for x in lines[lines.index(ln) + 1:] if x.strip())
                break
        if url:
            items.append({"title": title, "url": url, "snippet": highlight[:300]})
    return items


# ---------------------------------------------------------------- Tavily
def _call_tavily(query: str, limit: int) -> list[dict]:
    key = os.getenv("TAVILY_API_KEY", "")
    if not key:
        raise RuntimeError("TAVILY_API_KEY 未配置")
    body = json.dumps({"query": query, "max_results": limit, "search_depth": "basic"}).encode()
    req = urllib.request.Request(
        "https://api.tavily.com/search", data=body,
        headers={**UA, "Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        data = json.loads(resp.read().decode())
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": (r.get("content") or "")[:300]}
        for r in data.get("results", [])
    ]


# ---------------------------------------------------------------- DuckDuckGo
def _call_duckduckgo(query: str, limit: int) -> list[dict]:
    params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
    payload = _http_get_json(f"https://api.duckduckgo.com/?{urllib.parse.urlencode(params)}")
    items: list[dict] = []
    if payload.get("AbstractText"):
        items.append({"title": payload.get("Heading") or query,
                      "url": payload.get("AbstractURL", ""), "snippet": payload["AbstractText"]})

    def walk(entries: list):
        for e in entries:
            if len(items) >= limit:
                return
            if "Topics" in e:
                walk(e["Topics"])
            elif e.get("FirstURL"):
                items.append({"title": (e.get("Text") or "").split(" - ")[0],
                              "url": e["FirstURL"], "snippet": e.get("Text", "")})
    walk(payload.get("RelatedTopics", []))
    return items


# ---------------------------------------------------------------- 小红书
_XHS_API = os.path.expanduser("~/Projects/Spider_XHS/xhs_api.py")
_XHS_VENV_PY = os.path.expanduser("~/Projects/Spider_XHS/.venv/bin/python")


def _call_xiaohongshu(query: str, limit: int) -> list[dict]:
    """Spider_XHS 封装：真实笔记 + 点赞/收藏/评论（热度=质量信号）。

    ⚠️ 上游有 35s 风控节流（~/.cache/xhs_api.lock 跨进程锁），每次 query
    只发一次请求，禁止在循环里高频调用。
    """
    if not (os.path.exists(_XHS_API) and os.path.exists(_XHS_VENV_PY)):
        raise RuntimeError("Spider_XHS 不在 ~/Projects/Spider_XHS")
    out = subprocess.run(
        [_XHS_VENV_PY, _XHS_API, "search", query, str(limit)],
        capture_output=True, text=True, timeout=90,
    )
    if out.returncode != 0:
        raise RuntimeError(f"xhs exit={out.returncode}: {out.stderr[:200]}")
    data = json.loads(out.stdout)
    if not data.get("success"):
        raise RuntimeError(f"xhs: {data.get('msg', 'unknown')}")
    items = []
    for n in (data.get("notes") or [])[:limit]:
        stat = (f"❤{n.get('likes', '?')} ⭐{n.get('collects', '?')} "
                f"💬{n.get('comments', '?')} · @{n.get('nickname', '')}")
        items.append({"title": n.get("title") or "小红书笔记",
                      "url": n.get("url", ""), "snippet": stat})
    return items


# ---------------------------------------------------------------- B站
BILI_BIN = os.environ.get("BILI_BIN", "/home/myx/.hermes/hermes-agent/venv/bin/bili")


def _call_bilibili(query: str, limit: int) -> list[dict]:
    """bili-cli 视频搜索：播放量=热度信号，时长=深度信号。

    深度内容续接：bilibili_subtitle_text(bvid) 可把攻略视频字幕转全文。
    """
    if not os.path.exists(BILI_BIN):
        raise RuntimeError("bili-cli 未找到（可设 BILI_BIN 环境变量）")
    out = subprocess.run(
        [BILI_BIN, "search", query, "--type", "video", "-n", str(limit), "--json"],
        capture_output=True, text=True, timeout=30,
    )
    if out.returncode != 0:
        raise RuntimeError(f"bili exit={out.returncode}: {out.stderr[:200]}")
    data = json.loads(out.stdout)
    items = []
    for v in (data.get("data") or [])[:limit]:
        items.append({
            "title": v.get("title") or "B站视频",
            "url": f"https://www.bilibili.com/video/{v.get('bvid', '')}",
            "snippet": f"▶{v.get('play', '?')} · {v.get('duration', '?')} · UP:{v.get('author', '')}",
        })
    return items


def bilibili_subtitle_text(bvid: str) -> str:
    """拉取 B 站视频字幕全文（~/.local/bin/bilibili_subtitle.py，内含 cookies）。

    直连不走代理（脚本要求 HTTP_PROXY/HTTPS_PROXY 置空）；用 hermes venv
    python（依赖 requests）。失败抛异常，调用方自行降级到普通搜索。
    """
    script = os.path.expanduser("~/.local/bin/bilibili_subtitle.py")
    venv_py = "/home/myx/.hermes/hermes-agent/venv/bin/python"
    if not (os.path.exists(script) and os.path.exists(venv_py)):
        raise RuntimeError("字幕脚本或 hermes venv python 不存在")
    env = {k: v for k, v in os.environ.items()
           if k.lower() not in ("http_proxy", "https_proxy")}
    out = subprocess.run([venv_py, script, bvid],
                         capture_output=True, text=True, timeout=120, env=env)
    if out.returncode != 0:
        raise RuntimeError(f"subtitle exit={out.returncode}: {out.stderr[:200]}")
    return out.stdout


# ---------------------------------------------------------------- 高德 POI
def _call_amap_poi(query: str, limit: int) -> list[dict]:
    """高德 POI 搜索（tools/amap_client.py）：评分/地址/类型结构化数据。

    需 env AMAP_KEY（Web服务类型）。query 建议「城市 + 关键词」连写，
    如「杭州 灵隐寺 门票」。
    """
    if not os.getenv("AMAP_KEY"):
        raise RuntimeError("AMAP_KEY 未配置")
    import amap_client  # 同目录 tools/，延迟导入避免无 key 时阻塞

    parts = query.split(maxsplit=1)
    city, keyword = (parts + [""][:2])[:2] if len(parts) == 2 else (parts[0], parts[0])
    result = amap_client.search_poi(keyword, city)
    if not result.ok:
        raise RuntimeError(f"amap: {result.error}")
    pois = result.data.get("pois", []) if isinstance(result.data, dict) else result.data
    import dataclasses

    items = []
    for p in (pois or [])[:limit]:
        if isinstance(p, dict):
            d = p
        elif dataclasses.is_dataclass(p):
            d = dataclasses.asdict(p)  # amap_client 返回 PoiItem dataclass
        else:
            continue
        name = d.get("name", "")
        addr = d.get("address") or d.get("district") or ""
        ptype = d.get("poi_type") or d.get("type") or ""
        if name:
            items.append({"title": name, "url": "", "snippet": f"📍{addr} · {ptype}"})
    return items


# ---------------------------------------------------------------- 和风天气
def _call_qweather(query: str, limit: int) -> list[dict]:
    """和风天气（实况+3天预报）。Console V4 起需专属 API Host。

    env: QWEATHER_KEY + QWEATHER_API_HOST（控制台→设置→API Host，
    形如 abc123.qweatherapi.com）。query 为城市名（中文）。
    """
    key = os.getenv("QWEATHER_KEY", "")
    host = os.getenv("QWEATHER_API_HOST", "").replace("https://", "").strip("/")
    if not key or not host:
        raise RuntimeError("QWEATHER_KEY / QWEATHER_API_HOST 未配置（V4 控制台获取专属 Host）")

    def _get(path: str, params: dict) -> dict:
        url = f"https://{host}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                import gzip
                raw = gzip.decompress(raw)
            return json.loads(raw.decode("utf-8"))

    geo = _get("/geo/v2/city/lookup", {"location": query, "key": key, "number": 1})
    loc = geo.get("location", [{}])[0]
    city_id, city_name = loc.get("id"), loc.get("name", query)
    now = _get("/v7/weather/now", {"location": city_id, "key": key})
    daily = _get("/v7/weather/3d", {"location": city_id, "key": key})

    n = now.get("now", {})
    out = [{"title": f"{city_name} 实时天气",
            "url": "https://www.qweather.com/",
            "snippet": f"{n.get('temp')}°C {n.get('text')} 湿度{n.get('humidity')}% 风{n.get('windDir')}{n.get('windScale')}级"}]
    for d in daily.get("daily", [])[:limit - 1 if limit > 1 else 1]:
        out.append({"title": f"{city_name} {d.get('fxDate')}",
                    "url": "https://www.qweather.com/",
                    "snippet": f"{d.get('textDay')} {d.get('tempMin')}~{d.get('tempMax')}°C 降水{d.get('precip')}mm"})
    return out


# ---------------------------------------------------------------- 抖音
_MC_DIR = os.path.expanduser("~/Projects/MediaCrawler")
_MC_DY_DATA = os.path.join(_MC_DIR, "data", "douyin", "jsonl")


def _mc_env() -> dict:
    """MediaCrawler 走国内站直连，剔除全部代理变量（含 all_proxy）。"""
    return {k: v for k, v in os.environ.items()
            if k.lower() not in ("http_proxy", "https_proxy", "all_proxy")}


def _call_douyin(query: str, limit: int, max_notes: int = 10, comments: bool = False) -> list[dict]:
    """MediaCrawler 抖音搜索（登录态已缓存在 browser_data/，无需重复扫码）。

    ⚠️ 慢速信源：每次调用拉起浏览器跑完整搜索，约 1 分钟；按点赞降序返回。
    comments=True 时同时抓一级评论（更慢，按需开）。抖音风控最严，勿高频。
    """
    import glob

    if not os.path.isdir(_MC_DIR):
        raise RuntimeError("MediaCrawler 不在 ~/Projects/MediaCrawler")
    subprocess.run(
        ["uv", "run", "main.py", "--platform", "dy", "--lt", "qrcode", "--type", "search",
         "--keywords", query, "--crawler_max_notes_count", str(max_notes),
         "--save_data_option", "jsonl", "--get_comment", "true" if comments else "false"],
        cwd=_MC_DIR, capture_output=True, text=True, timeout=300, env=_mc_env(),
    )
    files = sorted(glob.glob(os.path.join(_MC_DY_DATA, "search_contents_*.jsonl")),
                   key=os.path.getmtime)
    if not files:
        raise RuntimeError("douyin: 无输出文件（登录态可能失效，重跑一次扫码）")
    rows = []
    with open(files[-1], "r", encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            # ⚠️ 只保留本次关键词产出的行（同一日期文件会追加多次搜索的结果，防止跨词污染）
            if str(d.get("source_keyword", "")).strip() != query.strip():
                continue
            rows.append(d)

    def _int(v):
        try:
            return int(str(v).replace("w", "0000").replace(".", ""))
        except (ValueError, TypeError):
            return 0

    # jsonl 跨次运行追加，按 aweme_id 去重（保留点赞最高的一条）
    best: dict[str, dict] = {}
    for d in rows:
        aid = str(d.get("aweme_id", ""))
        if aid and (aid not in best or _int(d.get("liked_count")) > _int(best[aid].get("liked_count"))):
            best[aid] = d
    rows = sorted(best.values(), key=lambda d: _int(d.get("liked_count")), reverse=True)
    items = []
    for d in rows[:limit]:
        text = (d.get("title") or d.get("desc") or "抖音视频").split("#")[0].strip()
        items.append({
            "title": text[:80] or "抖音视频",
            "url": d.get("aweme_url") or f"https://www.douyin.com/video/{d.get('aweme_id', '')}",
            "snippet": f"❤{d.get('liked_count', '?')} 💬{d.get('comment_count', '?')} · @{d.get('nickname', '')}",
        })
    return items


# ================================================================ 注册表
ENGINES: list[dict] = [
    # -- web_search: 快速事实（开放时间/门票/政策），按 weight 降序降级 --
    {"name": "exa",        "role": "web_search", "weight": 30, "enabled": True, "callable": _call_exa},
    {"name": "tavily",     "role": "web_search", "weight": 20, "enabled": True, "callable": _call_tavily},
    # -- travel_notes: 深度攻略（真人体验/踩坑/路线），调用方按 role 取用 --
    {"name": "xiaohongshu", "role": "travel_notes", "weight": 35, "enabled": True, "callable": _call_xiaohongshu},  # ⚠️ 35s 风控节流
    {"name": "bilibili",    "role": "travel_notes", "weight": 32, "enabled": True, "callable": _call_bilibili},   # 全文: bilibili_subtitle_text(bvid)
    {"name": "douyin",      "role": "travel_notes", "weight": 28, "enabled": True, "callable": _call_douyin},     # ⚠️ 慢速(~1min/次,MediaCrawler 拉起浏览器)；登录态已缓存
    {"name": "amap_poi",  "role": "poi_detail",   "weight": 28, "enabled": True, "callable": _call_amap_poi},  # 需 AMAP_KEY
    {"name": "qweather",  "role": "weather",      "weight": 15, "enabled": True, "callable": _call_qweather},  # 需 QWEATHER_KEY + QWEATHER_API_HOST（V4 专属 Host）
    # -- 预留位：接入 = 加条目 + _call_* 函数 --
    # -- 已评估、明确不接（防重复踩坑） --
    # duckduckgo: 2026-09-21 下线，中文旅游查询基本为空；_call_duckduckgo 保留可随时加回
    # searxng: 公共实例（searx.be）禁 JSON API 返回空，仅自建有意义
    # 马蜂窝/大众点评: 强风控且无现成工具；12306: 无稳定公开 API
]


def get_engine_chain(role: str = "web_search") -> list[dict]:
    """按 weight 降序返回启用的指定角色信源"""
    chain = sorted(
        (e for e in ENGINES if e["role"] == role and e["enabled"]),
        key=lambda e: e["weight"], reverse=True,
    )
    return chain


def search_with_chain(query: str, limit: int = 5, role: str = "web_search") -> tuple[list[dict], str]:
    """沿引擎链依次尝试，返回 (结果, 实际使用的引擎名)；全失败返回 ([], "none")"""
    for engine in get_engine_chain(role):
        try:
            items = engine["callable"](query, limit)
            if items:
                return items[:limit], engine["name"]
        except Exception:
            continue  # 静默降级到下一个引擎
    return [], "none"
