# Hermes 本地适配说明（2026-09-21）

本目录两个 skill 已针对 Hermes Agent 工作站适配并实测。改动与用法如下。

## 环境变量（~/.hermes/.env）

| 变量 | 状态 | 用途 |
|---|---|---|
| `AMAP_KEY` | ✅ 已配 | Web服务 key：REST geocode/POI/路线/搜索（travel-skill + travelmapify 直连） |
| `TAVILY_API_KEY` | ✅ 已有 | 搜索引擎链第 2 顺位 |
| `AMAP_JS_KEY` | ⬜ 建议补 | Web端(JS API) key：生成地图用自己的 key（现回退模板公开 key）。注意 JS key 和 REST key 是两种类型，[控制台](https://console.amap.com/dev/key/app) 创建时选「Web端(JS API)」 |
| `WEATHER_KEY` | ⬜ 可选 | 和风天气，缺省时天气查询优雅降级 |

## 改动清单

### travel-skill
- **tools/sources_registry.py（新增）**：声明式信源注册表。搜索引擎链 **Exa(30) → Tavily(20) → DuckDuckGo(10)**，按 weight 降序、失败静默降级；`ENGINES` 列表末尾留有注释好的预留位（xiaohongshu / amap_poi / 12306 / qweather），接入 = 加条目 + `_call_*` 函数。
- **tools/web_search.py（重写）**：改走 `search_with_chain()`；返回的 `source` 字段 = 实际命中引擎名。原 DDG-only 逻辑废弃（中文旅游查询基本返回空）。

### travelmapify（v3 重构）
- **scripts/generate_leaflet_map.py（新增，推荐）**：Leaflet + 高德栅格瓦片（style=7 底图 + style=8 路网）自包含单文件 HTML 生成器，库内联自 `assets/vendor/`，**零 JS key 依赖、可离线双击打开**。选型依据 `AI开发工具.md` 场景⑩：栅格标点场景 Leaflet 优先于 AMap JS（后者 DomRender 模块链/WebGL/key 授权三重耦合，实测本机渲染进程曾整体失效）。
- **scripts/geocode_locations.py**：新增直连路径——有 `AMAP_KEY` 走高德 REST `place/text`（结果带 `via: amap-direct`），无 key 回退原 FlyAI 本地代理（8769）。
- **scripts/generate_from_optimized_template.py（AMap JS 旧版，保留）**：`inject_amap_key()` 仅在显式配置 `AMAP_JS_KEY` 时替换模板 JS key，绝不回退 `AMAP_KEY`（REST key 进 JS 槽位实测 0 瓦片）。⚠️ 已知坑：模板默认图层+`detectRetina:true` 在本机不出瓦片（scale=2 瓦片 404），改用 Leaflet 版。

## 已验证

- ✅ `AMAP_KEY` REST geocode 实测通过（上海外滩 → 121.497,31.238）
- ✅ Exa 中文旅游查询实测（西湖音乐喷泉开放时间 → 命中官方新闻）
- ✅ 模板地图渲染：161 张高德瓦片 + POI 标记 + 控件齐全（AMap JS 2.0）
- ⚠️ `AMAP_KEY`（REST 类型）**不能**驱动 JS 地图瓦片（实测 0 瓦片），JS key 需另建

## 调用速记

```bash
# 推荐链路：POI 名单 → 地理编码 → Leaflet 自包含地图（一行一个文件）
python3 ~/.hermes/skills/travelmapify/scripts/geocode_locations.py pois.json -o geo.json --city 杭州
python3 ~/.hermes/skills/travelmapify/scripts/generate_leaflet_map.py geo.json trip.html
# 产物 trip.html 双击即可打开，无需 HTTP 服务、无需任何 key
```

## 信源注册表（sources_registry.py，双链设计）

- **web_search 链**（快速事实：开放时间/门票/政策）：**Exa(30) → Tavily(20)**；秒级响应
  - 主题型逐日信源（不进 ENGINES，由 SKILL.md 硬规则按需调用）：**Magic Tips 客流月历**——迪士尼逐日客流+降水预测，URL 模式 `magic-tips.app/zh/renliu-rili/shanghai-disney-resort/{年}/{月}`，页面内嵌全月 JSON（date/percentage/weather_precip_sum），curl 直取无需 key；近 30 天平均误差 ±10。教训（2026-09-21）：单日客流禁止按「假期=高峰」外推，中秋末日 9/27 实为窗口内最低（33%）
- **travel_notes 链**（深度攻略：真人体验/踩坑/路线）：**小红书(35) → B站(32) → 抖音(28)**
  - 小红书：Spider_XHS 封装，带点赞/收藏热度；⚠️ 35s 风控节流（跨进程锁），勿循环高频调用
    - ⚠️ 2026-09-21 修复回归：config.yaml 的 xhs_cookie 为多行续行式（2空格缩进），旧正则 `\s*(.+?)(?=^\w+:|\Z)` 会把后续中文注释段一起吞进 cookie → httpx header latin-1 编码炸（UnicodeEncodeError）。xhs_api.py load_cookie 已改为「主行+缩进续行，遇非缩进行即停」。往 config.yaml 加新平台段（如抖音）时务必让注释行顶格。
  - B站：bili-cli 搜索（播放量/时长=热度深度信号）；`bilibili_subtitle_text(bvid)` 可续接字幕全文（22min 攻略视频实测 13.8K 字符）
  - 抖音：MediaCrawler（~/Projects/MediaCrawler，Playwright 扫码登录态已缓存）；⚠️ 慢速 ~1min/次（每次拉起浏览器）；实测命中 57 万赞西湖避坑攻略；按 aweme_id 去重、按点赞降序；抖音官方开放平台关键词搜索不向个人开放，此为唯一可行路径
- **poi_detail 链**（结构化事实）：**高德 POI(28)** ✅ 实测：`灵隐寺 | 法云弄1号 · 国家级景点`
- **weather 链**（行前天气检查）：**和风天气(15)** ✅ 实测：实况+3天预报；⚠️ Console V4 需专属 API Host（`QWEATHER_API_HOST`）

### 平台注册/控制台链接汇总

| 平台 | 链接 | 免费额度 | 备注 |
|---|---|---|---|
| 高德开放平台 | https://console.amap.com/dev/key/app | 个人认证足够 | 本场景需「Web服务」类型 key；JS 地图另建「Web端(JS API)」key |
| 和风天气 | https://console.qweather.com | 个人认证 5万次/月 | V4 控制台：设置→API Host 复制专属域名；devapi.qweather.com 对新账号已关闭 |
| 抖音开放平台 | https://open.douyin.com | — | 关键词搜索不向个人开放；数据获取走 MediaCrawler（~/Projects/MediaCrawler） |
| MediaCrawler | https://github.com/NanmiCoder/MediaCrawler | 开源免费 | Playwright+扫码登录；抖音/小红书/快手/B站/微博/知乎六平台 |
- **已评估不接**（注释留档防重复踩坑）：DDG（中文查询为空，2026-09-21 下线）、SearXNG（公共实例禁 JSON）、马蜂窝/大众点评（强风控无现成工具）、12306（无稳定公开 API）
- **扩展位**：`ENGINES` 列表注释区（amap_poi / qweather 等），接入 = 加条目 + `_call_*` 函数
