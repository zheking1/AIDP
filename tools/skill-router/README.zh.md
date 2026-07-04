<div align="center">

  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-green.svg)](https://fastapi.tiangolo.com/)
  [![MCP](https://img.shields.io/badge/MCP-可用-brightgreen.svg)](https://modelcontextprotocol.io/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-blue.svg)](https://www.postgresql.org/)

</div>

<h1 align="center">SkillRouter</h1>

<div align="center">

  **AI Agent 动态技能路由服务** — 缩小上下文，消除幻觉，无限扩展你的技能库。

  [核心功能](#-核心功能) • [快速开始](#-快速开始) • [MCP 集成](#-mcp-集成) • [架构设计](#-架构设计) • [路线图](#-路线图)

  [English](README.md) | 中文

</div>

---

## 🌟 为什么选择 SkillRouter?

AI Agent 的上下文窗口消耗很快。每个工具描述、函数签名、提示词模板都在争抢 token。当 Agent 拥有 50+ 工具时，大模型会：

- 🚫 **浪费 Token** — 读取 50 个工具却只用 1 个
- 🎯 **注意力分散** — 被无关工具稀释注意力
- 💭 **产生幻觉** — 选错工具、编造参数、甚至忽略工具

**技能库越大，问题越严重。** 覆盖率和准确性不可兼得 — 直到现在。

SkillRouter 架在 Agent 和技能库之间。它接收用户任务，从你的技能库（无论多大）中找到 **2-6 个最相关的技能**，只返回这些。Agent 只把匹配的技能注入 LLM 上下文。

```
                      ┌──────────────────────┐
                      │     Agent            │
                      │  (Claude / Cursor /   │
                      │   自定义)             │
                      └──────┬───────▲───────┘
                             │       │
                       MCP   │       │ 2-6 个匹配
                     resolve │       │ 技能 (精炼!)
                      _task  │       │
                             │       │
                      ┌──────▼───────┴───────┐
                      │    SkillRouter        │
                      │  (FastAPI + FastMCP)  │
                      │                       │
                      │  ┌─────────────────┐  │
                      │  │   技能库         │  │
                      │  │ (1000+ 技能)    │  │
                      │  │                  │  │
                      │  │ ① 向量搜索      │  │
                      │  │ ② LLM 重排序    │  │
                      │  │ ③ 规则匹配      │  │
                      │  └─────────────────┘  │
                      └───────────────────────┘
```

**效果**：LLM 只看到 2-6 个工具，而非 50+。上下文完整保留，幻觉消除。技能库可扩展到 1000+ 而质量不下降。

---

## ✨ 核心功能

| | 功能 | 说明 |
|---|------|------|
| 🧠 | **语义路由** | pgvector 余弦相似度，毫秒级从 1000 个缩减到 20 个 |
| 🔄 | **LLM 重排序** | 意图感知重排，精选最佳 2-6 个技能 |
| 📋 | **规则引擎** | 优先级 if-then 规则，可覆盖或提升匹配结果 |
| 🏷️ | **自动分类** | LLM 自动生成标签、描述和分组 |
| 🔐 | **RBAC 权限** | 基于角色的访问控制，支持技能级允许/拒绝列表 |
| 💾 | **会话缓存** | 30 分钟语义缓存，加速重复查询 |
| 📝 | **多文件技能** | 主脚本 + 辅助文件 + 执行配置 + 参数定义 |
| 📜 | **进化追踪** | Diff 历史、回滚、完整审计日志 |
| 🔍 | **代码审查** | 自动化风险模式检测，审批后才能发布 |
| 💻 | **CLI 执行器** | `srcli run` 本地执行技能，与服务端隔离 |
| 🧩 | **MCP 原生** | 45+ 个工具，任意 MCP 客户端即用（Claude、Cursor、Cline 等） |
| 🎨 | **Web 控制台** | 内置管理面板，零构建步骤 |

---

## 📖 目录

- [快速开始](#-快速开始)
- [架构设计](#-架构设计)
- [MCP 集成](#-mcp-集成)
- [CLI 使用](#-cli-使用)
- [Web 控制台](#-web-控制台)
- [配置说明](#-配置说明)
- [项目结构](#-项目结构)
- [API 参考](#-api-参考)
- [路线图](#-路线图)
- [常见问题](#-常见问题)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

---

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- PostgreSQL 数据库（带 pgvector 扩展）
- LLM API 端点（OpenAI 兼容格式）
- Embedding API 端点

### 1. 克隆并配置

```bash
git clone https://github.com/yourusername/SkillRouter.git
cd SkillRouter

cp .env.example .env
# 编辑 .env，填入数据库、Redis 和 LLM 配置
```

### 2. 启动服务

```bash
docker compose up -d
```

### 3. 访问 Web 控制台

在浏览器中打开 **http://localhost:8788**。

- **默认账号**：`admin / admin123`
- **请立即修改密码**，在设置页面中修改

### 4. 添加第一个技能

1. 进入 **技能库** → **创建技能**
2. 填写名称、描述和内容
3. 添加标签以提升匹配效果
4. 点击 **保存**

### 5. 测试路由

进入 **测试台**，输入任务描述，看看 SkillRouter 如何匹配正确的技能！

---

## 🏗️ 架构设计

### 三阶段匹配

SkillRouter 采用三阶段方案，在最小延迟下实现最高准确率：

```
┌─────────────────────────────────────────────────────────────┐
│ 阶段 1: Embedding 向量搜索                                  │
│  ────────────────────────────────────────────────────────   │
│  "查询上个月订单" → 向量 (384维)                            │
│  pgvector 余弦相似度 → top 20 技能                          │
│  延迟: ~50ms                                                │
└──────────────────────────────────┬──────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 阶段 2: LLM 重排序（可选）                                   │
│  ────────────────────────────────────────────────────────   │
│  轻量级 LLM 分析意图                                         │
│  重排序 top 10 → 选出最佳 2-6 个                             │
│  延迟: ~200-500ms（超时自动降级）                            │
└──────────────────────────────────┬──────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 阶段 3: 规则匹配 + 权限过滤                                  │
│  ────────────────────────────────────────────────────────   │
│  规则: 标签含 "order" 且优先级 > 5 → 提升排名                │
│  规则: 标签含 "finance" → 需要审批                           │
│  角色权限: 按用户角色过滤                                     │
│  延迟: ~10ms                                                 │
└─────────────────────────────────────────────────────────────┘
```

### 执行流程示例

```
Agent 收到: "查一下 ABC Corp 上个月的订单"
        │
        ▼
Agent 通过 MCP 调用 resolve_task
        │
        ▼
SkillRouter 匹配: order_api (#1), invoice_api (#2)
        │
        ▼
Agent 只把 2 个技能注入 LLM 上下文（0.3K tokens，不是 7.5K）
        │
        ▼
LLM 选对工具 → 执行 → 返回结果
```

---

## 🔌 MCP 集成

### 从任意 MCP 客户端连接

SkillRouter 是 MCP 原生的。可以连接到 Claude Desktop、Cursor、Cline 或任何 MCP 兼容的 Agent。

**服务地址**：`http://your-server:8788/mcp`

**配置示例** (Claude Desktop):

```json
{
  "mcpServers": {
    "skillrouter": {
      "url": "http://localhost:8788/mcp",
      "headers": {
        "X-API-Key": "your-api-key-here"
      }
    }
  }
}
```

### 核心 MCP 工具

| 分类 | 工具 |
|------|------|
| **路由** | `resolve_task` — SkillRouter 的核心 |
| **技能** | `skill_register`, `skill_update`, `skill_delete`, `skill_get`, `skill_list` |
| **规则** | `rule_create`, `rule_update`, `rule_delete`, `rule_list` |
| **审查** | `skill_review`, `skill_approve`, `skill_reject`, `skill_pre_review` |
| **模型** | `model_create`, `model_update`, `model_delete`, `model_list` |
| **进化** | `evolution_submit`, `evolution_rollback`, `evolution_list` |
| **LLM** | `llm_completion` — 直接调用 LLM |

### 自动分类

通过 MCP 创建技能或规则时，SkillRouter 会自动：

- 🏷️ 生成相关标签
- 📝 创建简洁描述
- 📁 建议（并创建）合适的分组
- 🔒 设置默认权限

```python
# Agent 只需要名称 + 内容 — 其余自动填充
skill_register(
    name="CSV处理器",
    content="import pandas as pd\ndef process_csv(file_path):..."
)
# 返回: { tags: ["csv", "数据处理", "python"], 
#         description: "使用 pandas 处理 CSV 文件", 
#         group_name: "数据处理" }
```

---

## 💻 CLI 使用

`srcli` 工具让你可以在本地运行技能，与服务端隔离。

### 安装

```bash
curl -sSL http://your-server:8788/api/cli/install.sh | bash
```

### 常用命令

```bash
# 配置
srcli config set-server http://your-server:8788
srcli config set-api-key your-key

# 浏览技能
srcli list                    # 列出所有技能
srcli list --q "csv"          # 按关键词搜索
srcli list --tag "python"     # 按标签过滤

# 安装和运行
srcli install csv-processor   # 下载技能
srcli run csv-processor --file=data.csv  # 本地执行

# 管理
srcli info csv-processor      # 查看技能详情
srcli files csv-processor     # 列出技能文件
srcli update csv-processor    # 检查更新
srcli rollback csv-processor v2  # 回滚到旧版本
srcli diff csv-processor      # 比较本地与服务器版本
```

### 安全模型

- **服务端永不执行不可信代码** — 技能通过 CLI 在本地执行
- **客户端保留历史版本** — 秒级回滚
- **服务端无 CPU/内存尖峰** — 执行分布到各客户端
- **CLI 可离线工作** — 缓存的技能无需网络也能运行

---

## 🎨 Web 控制台

SkillRouter 附带功能完整的 Web 管理面板 — 零构建步骤即可使用。

### 功能

- 📋 **技能管理** — 创建、编辑、审查、版本控制
- 📋 **规则管理** — if-then 规则，用于提升/屏蔽技能
- 👥 **用户管理** — 多用户，基于角色的访问控制
- 🔑 **API 密钥** — 生成和管理 MCP API Key
- 📊 **统计中心** — 使用统计、缓存命中率、延迟指标
- 🔒 **权限管理** — 技能级别的角色访问控制
- 🧪 **测试台** — 用任意查询测试解析器

### 截图

| 技能库 | 测试台 | 统计中心 |
|--------|--------|----------|
| 浏览和管理所有技能 | 交互式测试技能匹配 | 监控使用情况和性能 |

---

## ⚙️ 配置说明

### 环境变量

```ini
# 服务端
PORT=8788
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# 数据库
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/skill-manager

# 缓存
REDIS_URL=redis://localhost:6379/0
SESSION_CACHE_TTL=1800

# 主 LLM
LLM_ENDPOINT=http://localhost:8000/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=deepseek-v3

# Embedding
EMBEDDING_ENDPOINT=http://localhost:8000/v1
EMBEDDING_API_KEY=sk-xxx
EMBEDDING_DIM=384

# 角色模型（可选 - 不同任务用不同模型）
RANKER_MODEL=deepseek-v3-flash   # 技能重排序
INTENT_MODEL=deepseek-v3-flash   # 意图分析
REVIEW_MODEL=deepseek-v3         # 代码审查
```

### 基于角色的访问控制

SkillRouter 支持 5 种用户角色：

| 角色 | 等级 | 权限 |
|------|------|------|
| `super_admin` | 5 | 完全系统访问 |
| `admin` | 4 | 管理用户、技能、规则 |
| `developer` | 3 | 创建/编辑技能，提交审查 |
| `user` | 2 | 使用技能，查看技能库 |
| `readonly` | 1 | 只读 |

---

## 📁 项目结构

```
SkillRouter/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置
│   ├── db/
│   │   ├── models.py        # SQLAlchemy 模型
│   │   ├── database.py      # 数据库连接
│   │   └── init_db.py       # 数据库迁移
│   ├── services/
│   │   ├── resolve_service.py    # 核心路由逻辑
│   │   ├── ranker_service.py     # LLM 重排序
│   │   ├── classification_service.py  # 自动分类
│   │   ├── cache_service.py      # 会话和请求缓存
│   │   ├── skill_service.py      # 技能 CRUD
│   │   ├── rule_service.py       # 规则 CRUD
│   │   ├── review_service.py     # 代码审查
│   │   ├── vector_service.py     # Embedding 向量
│   │   └── validation_service.py # 后置校验
│   ├── mcp/
│   │   └── tools.py         # MCP 工具定义 (45+ 工具)
│   └── web/
│       ├── routes.py        # Web UI 路由
│       ├── auth_utils.py    # 认证和权限
│       ├── settings_utils.py # 设置管理
│       ├── i18n/            # 国际化 (中/英)
│       └── templates/       # Jinja2 + Alpine.js 模板
├── cli/
│   └── srcli.py             # CLI 客户端
├── tests/                   # 集成测试
├── docker-compose.yml       # Docker 部署
├── Dockerfile
├── requirements.txt
├── README.md                # 英文文档
└── README.zh.md             # 中文文档
```

---

## 📚 API 参考

### REST API

所有端点都在 `/api/` 路径下。详情请参阅 [API 文档](docs/API.md)。

### MCP 工具

完整的工具列表请参阅 [MCP 工具文档](docs/MCP_TOOLS.md)。

### WebSocket (SSE)

实时更新通过 Server-Sent Events 提供，地址为 `/api/events`。

---

## 🛣️ 路线图

### ✅ 已完成

- [x] pgvector 向量搜索
- [x] LLM 重排序服务
- [x] 规则引擎
- [x] 会话语义缓存
- [x] 基于角色的访问控制
- [x] Web UI 管理面板
- [x] CLI 本地执行
- [x] 代码审查系统
- [x] 自动分类
- [x] MCP 服务器 (45+ 工具)

### 🔄 进行中

- [ ] 技能进化反馈循环
- [ ] Precision@k 指标
- [ ] 多语言支持 (中/英/日)

### 📅 计划中

- [ ] 技能市场 / 公共注册表
- [ ] 技能组合（链式调用多个技能）
- [ ] Agent 记忆集成
- [ ] 技能实时热重载
- [ ] 更多 CLI 功能

---

## ❓ 常见问题

### Q: 我需要单独的 LLM 来做重排序吗？

A: 不需要。如果不配置 ranker 模型，SkillRouter 会直接使用 embedding 分数。对于 < 50 个技能的库，这通常已经足够准确。

### Q: 可以和多个 Agent 一起使用吗？

A: 可以！为每个 Agent 创建独立的 API Key。每个 Agent 的会话缓存和活动都是独立追踪的。

### Q: SkillRouter 安全吗？

A: SkillRouter 从设计上考虑了安全性：
- 服务器从不执行技能代码 — 执行通过 CLI 在客户端进行
- 5 级 RBAC 角色控制
- 技能级权限控制
- API Key 认证
- 新技能的代码审查系统

### Q: 支持哪些 embedding 模型？

A: 任何 OpenAI 兼容的 embedding 端点。已测试：
- BGE-M3 (384/1024 维)
- text-embedding-3-small (1536 维)
- text-embedding-3-large (3072 维)

### Q: 如何从现有的工具系统迁移？

A: 使用 `skill_register` MCP 工具批量导入现有工具。每个工具都会变成一个技能，包含其描述、参数和实现。

---

## 🤝 贡献指南

欢迎贡献！以下是你可以帮助的方式：

### 贡献方式

- 🐛 **报告 Bug** — 提交 issue
- 💡 **建议功能** — 发起讨论
- 📝 **改进文档** — 编辑 README 或 wiki
- 🔧 **提交代码** — 欢迎 Pull Request

### 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/yourusername/SkillRouter.git
cd SkillRouter

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/

# 启动开发服务器
python -m app.main
```

### 代码规范

- Python 遵循 PEP 8
- 所有地方使用类型注解
- 公共 API 编写文档字符串
- 新功能添加测试

---

## 📄 许可证

本项目采用 **MIT 许可证** — 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) — 出色的 Python Web 框架
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP 服务器框架
- [pgvector](https://github.com/pgvector/pgvector) — PostgreSQL 向量搜索
- [Alpine.js](https://alpinejs.dev/) — 轻量级 JavaScript 框架
- [Tailwind CSS](https://tailwindcss.com/) — 实用优先的 CSS

---

<div align="center">

**用 ❤️ 为 AI Agent 社区打造**

[⬆ 返回顶部](#skillrouter)

</div>