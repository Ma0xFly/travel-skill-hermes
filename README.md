<p align="center">
  <h1 align="center">travel-skill</h1>
</p>

<p align="center">
  <em>"让 AI 不只是告诉你去哪玩，而是真的帮你把旅行安排明白。"</em>
</p>

<p align="center">
  <a href="https://claude.ai/code"><img src="https://img.shields.io/badge/Claude%20Code-Skill-blueviolet" alt="Claude Code"></a>
  <a href="https://cursor.com"><img src="https://img.shields.io/badge/Cursor-Skill-blue" alt="Cursor"></a>
  <a href="https://agentskills.io"><img src="https://img.shields.io/badge/AgentSkills-Standard-green" alt="AgentSkills"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

<br/>

<p align="center">
你想让 AI 推荐旅游攻略，它给你一堆没有顺序的热门榜单？<br/>
你想问 AI 半天去哪玩，它给你塞 10 个景点让你自己选？<br/>
你想看天气、路线和开放时间，它却把静态知识当实时信息讲给你？<br/>
你上传图片和文字想让它帮你规划，它却只能泛泛而谈？<br/>
</p>

<p align="center">
<strong>装上这个 Skill，AI 不只是“会推荐”，<br/>而是能按你的偏好、时间和场景，把旅行建议组织成可执行方案。</strong>
</p>

<br/>

<p align="center">
  <a href="#效果演示">效果演示</a> · <a href="#安装">安装</a> · <a href="#skill-结构">Skill 结构</a> · <a href="#核心能力">核心能力</a> · <a href="#后续规划">后续规划</a>
</p>

<br/>

---

## 这个 Skill 有什么不一样？

不是简单的“景点推荐提示词”，而是一个面向旅行规划的 **轻量工具型 Skill**：

| 维度 | 普通 AI 回答 | 装了 travel-skill 的 AI |
|------|-------------|-------------------------|
| 城市游玩推荐 | 给你一堆景点清单 | 根据半天 / 一天、人流偏好和出行类型，给你更适合执行的组合方案 |
| 美食推荐 | 罗列热门餐厅 | 结合景点区域、时间段和排队情况，安排顺路吃什么 |
| 天气问题 | 泛泛讲天气常识 | 调天气工具，返回天气概览 + 未来预报 + 出游建议 |
| 路线问题 | 模糊说“可以坐地铁” | 调高德工具，给出起终点路线、时长和距离 |
| 最新开放时间 | 容易把旧知识当新消息 | 联网搜索最新开放时间、门票和预约政策 |
| Skill 开发维护 | 改文件全靠手动备份 | 内置版本快照和回滚能力，方便持续迭代 |

---

## 效果演示

### 🗺 旅游推荐

```text
用户  ❯  杭州半天，情侣出行，想要人少一点，顺便安排吃饭。

AI    ❯  你这个场景更适合做成一条轻松、能拍照、不过分赶路的半日路线。
         我会避开最拥挤的核心时段，把重点放在“氛围感 + 顺路吃饭”。

         推荐主路线：
         1. 先去西湖周边相对安静的步行段
         2. 再找一个适合停留的茶馆或街区点
         3. 晚餐安排杭州本地菜馆
```

### 🌦 天气查询

```text
用户  ❯  帮我看看杭州这两天天气怎么样，适不适合旅游？

AI    ❯  当前天气整体适合常规出游，可优先安排户外景点。
         如果未来几天有明显降雨，我会提醒你准备室内备选点。
```

### 🚶 路线规划

```text
用户  ❯  从橘子洲到岳麓山怎么走，公交最划算吗？

AI    ❯  我会先解析橘子洲和岳麓山的位置，再调用路线工具。
         返回内容会包括：公交 / 步行 / 驾车的时长、距离，以及更适合当前场景的建议。
```

### 🔎 最新信息检索

```text
用户  ❯  帮我查一下上海博物馆最新开放时间和预约政策。

AI    ❯  我会优先走联网搜索工具，补充静态知识库之外的最新信息。
         返回结果会包含：搜索结论、结果列表、可进一步核验的官网链接。
```

---

## 核心能力

### 1）常规旅游规划

- 景点推荐
- 美食推荐
- 玩 + 吃组合路线
- 热闹 / 适中 / 人少差异化输出
- 半天 / 一天 / 晚上逛吃场景化规划

### 2）工具增强能力

- 天气查询
- 高德路线规划
- 联网搜索最新旅游信息
- 版本快照与回滚

### 3）输入理解能力

- 从自然语言中提取城市、时长、预算、人流偏好
- 识别情侣 / 朋友 / 家庭 / 独行场景
- 识别用户图片 / 文字补充线索
- 自动判断当前请求应走推荐、天气、路线还是联网搜索

---

## 安装

详细安装步骤见 [`INSTALL.md`](INSTALL.md)。

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

---

## Skill 结构

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

### 文件说明

- `SKILL.md`：Skill 入口、触发条件、工作流和回答要求
- `reference.md`：规则、数据模型、工具能力和路由说明
- `examples.md`：典型问法与输出示例
- `scripts/helper.py`：输入解析、意图判断、工具路由主入口
- `tools/`：天气、高德、联网搜索和版本管理工具层

---

## 当前实现思路

当前版本采用 **轻量规则版 MVP + 工具增强** 思路：

1. 先解析用户输入
2. 判断请求类型
3. 决定走推荐 / 天气 / 路线 / 联网搜索哪条链路
4. 统一返回结构化结果

这样做的好处是：

- 一开始就能用
- 复杂度可控
- 后续可以逐步叠加城市数据和推荐算法

---

## 后续规划

接下来适合继续演进的方向：

1. 补第一批城市样例数据
2. 完善推荐结果生成能力
3. 增加预算模式和天气联动
4. 增加动态热度与节假日拥挤提醒
5. 优化工具调用结果和自然语言输出衔接

---

## License

本项目使用 [MIT License](LICENSE)。
