# travel-skill · Hermes 适配版

> 基于 [Leon-KTlan/travel-skill](https://github.com/Leon-KTlan/travel-skill)（MVP 规则版）的深度改造：
> 把「单引擎联网搜索」重写为**声明式信源注册表 + 多链路降级采集**，并经真实行程全流程验证。
> 详细适配记录见 [README-HERMES.md](README-HERMES.md)。

![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue) ![License](https://img.shields.io/badge/License-MIT-yellow)

## 与上游的差异

| 维度 | 上游 MVP | 本版 |
|---|---|---|
| 联网搜索 | 单引擎（DDG，中文查询基本为空） | **Exa → Tavily** 降级链，中文旅游查询实测可用 |
| 深度攻略 | 无 | **小红书 → B站 → 抖音** 真人攻略链（点赞/播放量=热度信号） |
| 结构化事实 | 仅路线 | + **高德 POI**（评分/地址/类型）、**和风天气**（实况+3天预报） |
| 行程时长 | 封顶「一天」（多日请求被静默降级或报错） | **days 字段（2–15 天）**，多日输出骨架：总览表+逐日明细+避坑+预算 |
| 工程化 | 手动备份 | .gitignore、版本快照、跨进程风控锁 |

## 架构

```text
请求 → helper.py 解析（city/intent/days/travel_type/crowd...）
     → 路由四类：recommendation / weather / route / web_search
     → 信源注册表（sources_registry.py）按 role + weight 降序调用，失败静默降级
```

**信源注册表**（核心）：每条链是声明式条目，接入新信源 = 加一个条目 + 一个 `_call_*` 函数，调用方零改动。

| 链 (role) | 信源（权重降序） | 用途 |
|---|---|---|
| `web_search` | Exa(30) → Tavily(20) | 开放时间/门票/政策/官方通知 |
| `travel_notes` | 小红书(35) → B站(32) → 抖音(28) | 真人体验/踩坑/路线（⚠️ 各有风控节流） |
| `poi_detail` | 高德 POI(28) | 结构化：评分/地址/类型 |
| `weather` | 和风天气(15) | 实况 + 3 天预报 |

已评估不接：DDG（中文空结果）、SearXNG（公共实例禁 JSON）、马蜂窝/大众点评（强风控）。

## 地图产出（配套 travelmapify）

行程 POI 可一键生成**离线单文件地图**（Leaflet + 高德栅格瓦片，GCJ-02 天然对齐，双击打开、无 key、无 HTTP 服务），三步：

```bash
echo '[{"name": "虹桥天地"}, {"name": "朱家角古镇-放生桥"}]' > pois.json
python3 ~/.hermes/skills/travelmapify/scripts/geocode_locations.py pois.json -o geo.json --city 上海
python3 ~/.hermes/skills/travelmapify/scripts/generate_leaflet_map.py geo.json trip.html
```

真实产出示例见 [`examples/shanghai-7d-map.html`](examples/shanghai-7d-map.html)（上海中秋+国庆 7 日行程 21 个点位，含市区/青浦/迪士尼全标注）。选型依据：高德 JS API 与 DomRender/key 授权三重耦合，栅格标点场景 Leaflet 更稳（详见 README-HERMES）。

## 环境变量

| 变量 | 必需 | 说明 |
|---|---|---|
| `AMAP_KEY` | ✅ | 高德 Web 服务 key（geocode/POI/路线） |
| `TAVILY_API_KEY` | ✅ | 搜索链第 2 顺位 |
| `QWEATHER_KEY` + `QWEATHER_API_HOST` | 可选 | 和风 V4 专属 Host |
| `EXA_API_KEY` | 可选 | 走 mcporter（`exa.web_search_exa`），需代理 |

travel_notes 链依赖本地工具（缺失自动降级到下一信源）：[Spider_XHS](https://github.com/...)（小红书，venv + cookie）、bili-cli（B站，可拉字幕全文）、[MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)（抖音，扫码登录态缓存）。

## 安装（Hermes）

```bash
git clone https://github.com/Ma0xFly/travel-skill-hermes.git ~/.hermes/skills/travel-skill
# 在 ~/.hermes/.env 配置上表变量；travel_notes 链按需部署本地工具
```

## 实战验证（2026-09，上海 7 天中秋+国庆行程）

全链路跑通一次真实规划：国务院放假通知 / 光影节档期（政府源）→ 朱家角国庆限流（景区官网）→ 地铁末班车（官方时刻）→ 小红书 4.2 万赞 citywalk 路线抓详情 → 高德 POI 评分选餐厅 → 和风天气。多源交叉验证 + 避坑清单产出，期间修复小红书 cookie 多行解析回归（见 README-HERMES）。

## License

MIT（继承上游），感谢 [Leon-KTlan](https://github.com/Leon-KTlan) 的原始设计。
