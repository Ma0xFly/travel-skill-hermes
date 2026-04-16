# 安装说明

本文档介绍如何安装和配置 `travel-skill`。

## 1. 环境要求

- Python 3.10+
- Git
- 可选：高德地图 API Key
- 可选：和风天气 API Key

## 2. 目录安装

### Cursor

```bash
mkdir -p .cursor/skills
git clone <your-repo-url> .cursor/skills/travel-skill
```

### Claude Code

```bash
mkdir -p .claude/skills
git clone <your-repo-url> .claude/skills/travel-skill
```

### OpenClaw

```bash
git clone <your-repo-url> ~/.openclaw/workspace/skills/travel-skill
```

## 3. 环境变量配置

建议配置以下环境变量：

```bash
AMAP_KEY=
WEATHER_KEY=
TRAVEL_SKILL_REQUEST_TIMEOUT=10
WEB_SEARCH_BASE_URL=https://api.duckduckgo.com/
```

说明：

- `AMAP_KEY`：用于地理编码、POI 搜索和路线规划
- `WEATHER_KEY`：用于天气查询
- `TRAVEL_SKILL_REQUEST_TIMEOUT`：工具请求超时时间，单位秒
- `WEB_SEARCH_BASE_URL`：联网搜索接口地址

## 4. 当前目录结构

```text
travel-skill/
├── SKILL.md
├── reference.md
├── examples.md
├── INSTALL.md
├── README.md
├── LICENSE
├── scripts/
│   └── helper.py
└── tools/
    ├── config.py
    ├── tool_types.py
    ├── weather_client.py
    ├── amap_client.py
    ├── web_search.py
    ├── snapshot_store.py
    └── version_manager.py
```

## 5. 工具能力说明

### 天气工具

用于：

- 查询实时天气
- 查询未来天气预报
- 生成出游建议

### 高德工具

用于：

- 地理编码
- 搜索 POI
- 路线规划

### 联网搜索工具

用于：

- 查询景点最新开放时间
- 查询门票与预约政策
- 查询官网与公告信息

### 版本管理工具

用于：

- 创建快照
- 查看历史版本
- 回滚指定版本

## 6. 使用建议

- 常规“去哪玩 / 去哪吃 / 怎么安排”问题，直接由 Skill 主流程处理
- 问天气时，自动调用天气工具
- 问路线时，自动调用高德工具
- 问最新开放时间、票价、政策时，自动调用联网搜索工具
- 重大改动前，建议先创建版本快照
