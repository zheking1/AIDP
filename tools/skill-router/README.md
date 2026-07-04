<div align="center">

  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-green.svg)](https://fastapi.tiangolo.com/)
  [![MCP](https://img.shields.io/badge/MCP-Ready-brightgreen.svg)](https://modelcontextprotocol.io/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-blue.svg)](https://www.postgresql.org/)

</div>

<h1 align="center">SkillRouter</h1>

<div align="center">

  **Dynamic skill routing for AI agents** — keep context small, cut hallucinations, grow your skill library without limits.

  [Key Features](#-key-features) • [Quick Start](#-quick-start) • [MCP Integration](#-mcp-integration) • [Architecture](#-architecture) • [Roadmap](#-roadmap)

</div>

---

## 🌟 Why SkillRouter?

An AI agent's context window fills up fast. Every tool description, function schema, and prompt template competes for tokens. When an agent has 50+ tools, the LLM:

- 🚫 **Wastes tokens** — reading 50 tools when only 1 is needed
- 🎯 **Loses focus** — attention diluted across irrelevant tools
- 💭 **Hallucinates** — picks wrong tool, invents parameters, ignores tools entirely

**The bigger your skill library grows, the worse this gets.** You can't have both coverage and accuracy — until now.

SkillRouter sits between your agent and your skill library. It receives the user's task, finds the **2-6 relevant skills** from your library (however large), and returns only those. Your agent injects only matched skills into the LLM context.

```
                      ┌──────────────────────┐
                      │    Agent              │
                      │  (Claude / Cursor /   │
                      │   Custom)             │
                      └──────┬───────▲───────┘
                             │       │
                       MCP   │       │ 2-6 matched
                     resolve │       │ skills
                      _task  │       │ (compact!)
                             │       │
                      ┌──────▼───────┴───────┐
                      │    SkillRouter        │
                      │  (FastAPI + FastMCP)  │
                      │                       │
                      │  ┌─────────────────┐  │
                      │  │ Skill Library    │  │
                      │  │ (1000+ skills)   │  │
                      │  │                  │  │
                      │  │ ① vector search  │  │
                      │  │ ② LLM reranking  │  │
                      │  │ ③ rule matching  │  │
                      │  └─────────────────┘  │
                      └───────────────────────┘
```

**Result**: LLM sees 2-6 tools, not 50+. Context preserved. Hallucination eliminated. Library can grow to 1000+ skills without degrading quality.

---

## ✨ Key Features

| | Feature | Description |
|---|---------|-------------|
| 🧠 | **Semantic Routing** | pgvector cosine similarity narrows 1000→20 in milliseconds |
| 🔄 | **LLM Reranking** | Intent-aware reordering picks the best 2-6 skills |
| 📋 | **Rule Engine** | Priority if-then rules override or boost matches |
| 🏷️ | **Auto-Classification** | LLM auto-generates tags, descriptions, and groups |
| 🔐 | **RBAC Permissions** | Role-based access control with per-skill allow/deny lists |
| 💾 | **Session Cache** | 30-minute semantic cache for repeated queries |
| 📝 | **Multi-File Skills** | Main script + helpers + exec config + param schema |
| 📜 | **Evolution Tracking** | Diff history, rollback, full audit trail |
| 🔍 | **Code Review** | Automated risk pattern detection before approval |
| 💻 | **CLI Executor** | `srcli run` executes skills locally, isolated from server |
| 🧩 | **MCP-Native** | 45+ tools, works with any MCP client (Claude, Cursor, Cline, etc.) |
| 🎨 | **Web UI** | Built-in management dashboard — zero build step needed |

---

## 📖 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [MCP Integration](#-mcp-integration)
- [CLI Usage](#-cli-usage)
- [Web UI](#-web-ui)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [API Reference](#-api-reference)
- [Roadmap](#-roadmap)
- [FAQ](#-faq)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- A PostgreSQL database with pgvector extension
- An LLM API endpoint (OpenAI-compatible)
- An embedding API endpoint

### 1. Clone & Configure

```bash
git clone https://github.com/yourusername/SkillRouter.git
cd SkillRouter

cp .env.example .env
# Edit .env with your database, Redis, and LLM credentials
```

### 2. Start the Server

```bash
docker compose up -d
```

### 3. Access the Web UI

Open **http://localhost:8788** in your browser.

- **Default login**: `admin / admin123`
- **Change the password immediately** in the settings page

### 4. Add Your First Skill

1. Go to **Skills** → **Create Skill**
2. Fill in name, description, and content
3. Add tags for better matching
4. Click **Save**

### 5. Test the Router

Go to **Test Bench** and enter a task description. See how SkillRouter matches the right skills!

---

## 🏗️ Architecture

### Three-Phase Matching

SkillRouter uses a three-phase approach for maximum accuracy with minimum latency:

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Embedding Vector Search                            │
│  ────────────────────────────────────────────────────────   │
│  "query last month orders" → vector (384d)                  │
│  pgvector cosine similarity → top 20 skills                 │
│  Latency: ~50ms                                             │
└──────────────────────────────────┬──────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: LLM Reranking (optional)                           │
│  ────────────────────────────────────────────────────────   │
│  Lightweight LLM analyzes intent                            │
│  Reranks top 10 → picks best 2-6                            │
│  Latency: ~200-500ms (auto-degrades on timeout)             │
└──────────────────────────────────┬──────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Rule Matching + Permission Filter                  │
│  ────────────────────────────────────────────────────────   │
│  Rule: tag "order" + priority > 5 → promote                 │
│  Rule: tag "finance" → requires approval                    │
│  Role-based access: filter by user role                     │
│  Latency: ~10ms                                             │
└─────────────────────────────────────────────────────────────┘
```

### Execution Flow Example

```
Agent receives: "query last month orders for customer ABC Corp"
        │
        ▼
Agent calls resolve_task via MCP
        │
        ▼
SkillRouter matches: order_api (#1), invoice_api (#2)
        │
        ▼
Agent injects only 2 skills into LLM context (0.3K tokens, not 7.5K)
        │
        ▼
LLM picks correct tool → executes → returns result
```

---

## 🔌 MCP Integration

### Connect from Any MCP Client

SkillRouter is MCP-native. Connect it to Claude Desktop, Cursor, Cline, or any MCP-compatible agent.

**Server URL**: `http://your-server:8788/mcp`

**Configuration example** (Claude Desktop):

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

### Core MCP Tools

| Category | Tools |
|----------|-------|
| **Routing** | `resolve_task` — the heart of SkillRouter |
| **Skills** | `skill_register`, `skill_update`, `skill_delete`, `skill_get`, `skill_list` |
| **Rules** | `rule_create`, `rule_update`, `rule_delete`, `rule_list` |
| **Review** | `skill_review`, `skill_approve`, `skill_reject`, `skill_pre_review` |
| **Models** | `model_create`, `model_update`, `model_delete`, `model_list` |
| **Evolution** | `evolution_submit`, `evolution_rollback`, `evolution_list` |
| **LLM** | `llm_completion` — direct LLM access |

### Auto-Classification

When creating skills or rules via MCP, SkillRouter automatically:

- 🏷️ Generates relevant tags
- 📝 Creates a concise description
- 📁 Suggests (and creates) appropriate groups
- 🔒 Sets default permissions

```python
# Agent just needs name + content — rest is auto-filled
skill_register(
    name="CSV Processor",
    content="import pandas as pd\ndef process_csv(file_path):..."
)
# Returns: { tags: ["csv", "data-processing", "python"], 
#           description: "Process CSV files with pandas", 
#           group_name: "Data Processing" }
```

---

## 💻 CLI Usage

The `srcli` tool lets you run skills locally, isolated from the server.

### Installation

```bash
curl -sSL http://your-server:8788/api/cli/install.sh | bash
```

### Basic Commands

```bash
# Configure
srcli config set-server http://your-server:8788
srcli config set-api-key your-key

# Browse skills
srcli list                    # list all skills
srcli list --q "csv"          # search by keyword
srcli list --tag "python"     # filter by tag

# Install & run
srcli install csv-processor   # download skill
srcli run csv-processor --file=data.csv  # execute locally

# Manage
srcli info csv-processor      # view skill details
srcli files csv-processor     # list skill files
srcli update csv-processor    # check for updates
srcli rollback csv-processor v2  # rollback to old version
srcli diff csv-processor      # compare local vs server
```

### Security Model

- **Server never runs untrusted code** — skills execute locally via CLI
- **Client keeps historical versions** — instant rollback
- **No server CPU/memory spikes** — execution is distributed
- **CLI works offline** — cached skills run without network

---

## 🎨 Web UI

SkillRouter comes with a full-featured web dashboard — zero build step required.

### Features

- 📋 **Skill Management** — create, edit, review, version control
- 📋 **Rule Management** — if-then rules for boosting/blocking skills
- 👥 **User Management** — multi-user with role-based access
- 🔑 **API Keys** — generate and manage MCP API keys
- 📊 **Statistics** — usage stats, cache hit rates, latency metrics
- 🔒 **Permissions** — per-skill role-based access control
- 🧪 **Test Bench** — test the resolver with any query

### Screenshots

| Skill Library | Test Bench | Statistics |
|--------------|------------|------------|
| Browse and manage all your skills | Test skill matching interactively | Monitor usage and performance |

---

## ⚙️ Configuration

### Environment Variables

```ini
# Server
PORT=8788
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/skill-manager

# Cache
REDIS_URL=redis://localhost:6379/0
SESSION_CACHE_TTL=1800

# LLM (main model)
LLM_ENDPOINT=http://localhost:8000/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=deepseek-v3

# Embedding
EMBEDDING_ENDPOINT=http://localhost:8000/v1
EMBEDDING_API_KEY=sk-xxx
EMBEDDING_DIM=384

# Roles (optional - separate models for different tasks)
RANKER_MODEL=deepseek-v3-flash   # for skill reranking
INTENT_MODEL=deepseek-v3-flash   # for intent analysis
REVIEW_MODEL=deepseek-v3         # for code review
```

### Role-Based Access Control

SkillRouter supports 5 user roles:

| Role | Level | Permissions |
|------|-------|-------------|
| `super_admin` | 5 | Full system access |
| `admin` | 4 | Manage users, skills, rules |
| `developer` | 3 | Create/edit skills, submit for review |
| `user` | 2 | Use skills, view library |
| `readonly` | 1 | View only |

---

## 📁 Project Structure

```
SkillRouter/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration
│   ├── db/
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── database.py      # DB connection
│   │   └── init_db.py       # Database migrations
│   ├── services/
│   │   ├── resolve_service.py    # Core routing logic
│   │   ├── ranker_service.py     # LLM reranking
│   │   ├── classification_service.py  # Auto-classification
│   │   ├── cache_service.py      # Session & request caching
│   │   ├── skill_service.py      # Skill CRUD
│   │   ├── rule_service.py       # Rule CRUD
│   │   ├── review_service.py     # Code review
│   │   ├── vector_service.py     # Embedding vectors
│   │   └── validation_service.py # Post-validation
│   ├── mcp/
│   │   └── tools.py         # MCP tool definitions (45+ tools)
│   └── web/
│       ├── routes.py        # Web UI routes
│       ├── auth_utils.py    # Auth & permissions
│       ├── settings_utils.py # Settings management
│       ├── i18n/            # Internationalization (EN/ZH)
│       └── templates/       # Jinja2 + Alpine.js templates
├── cli/
│   └── srcli.py             # CLI client
├── tests/                   # Integration tests
├── docker-compose.yml       # Docker deployment
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 📚 API Reference

### REST API

All endpoints are available at `/api/`. See the [API documentation](docs/API.md) for details.

### MCP Tools

See the [MCP Tools documentation](docs/MCP_TOOLS.md) for a complete reference.

### WebSocket (SSE)

Real-time updates via Server-Sent Events at `/api/events`.

---

## 🛣️ Roadmap

### ✅ Completed

- [x] Vector search with pgvector
- [x] LLM reranking service
- [x] Rule engine
- [x] Session semantic cache
- [x] Role-based access control
- [x] Web UI management dashboard
- [x] CLI local execution
- [x] Code review system
- [x] Auto-classification
- [x] MCP server (45+ tools)

### 🔄 In Progress

- [ ] Skill evolution feedback loop
- [ ] Precision@k metrics
- [ ] Multi-language support (EN/ZH/JA)

### 📅 Planned

- [ ] Skill marketplace / public registry
- [ ] Skill composition (chaining multiple skills)
- [ ] Agent memory integration
- [ ] Real-time skill hot-reload
- [ ] More CLI features

---

## ❓ FAQ

### Q: Do I need a separate LLM for reranking?

A: No. If you don't configure a ranker model, SkillRouter uses embedding scores directly. For skill libraries < 50, this is usually accurate enough.

### Q: Can I use SkillRouter with multiple agents?

A: Yes! Create separate API keys for each agent. Each agent's session cache and activity are tracked independently.

### Q: Is SkillRouter secure?

A: SkillRouter is designed with security in mind:
- The server never executes skill code — execution happens client-side via CLI
- RBAC with 5 role levels
- Per-skill permission controls
- API key authentication
- Code review system for new skills

### Q: What embedding models are supported?

A: Any OpenAI-compatible embedding endpoint. Tested with:
- BGE-M3 (384/1024 dim)
- text-embedding-3-small (1536 dim)
- text-embedding-3-large (3072 dim)

### Q: How do I migrate from an existing tool system?

A: Use the `skill_register` MCP tool to batch-import your existing tools. Each tool becomes a skill with its description, parameters, and implementation.

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Ways to Contribute

- 🐛 **Report bugs** — open an issue
- 💡 **Suggest features** — start a discussion
- 📝 **Improve docs** — edit README or wiki
- 🔧 **Submit code** — pull requests welcome

### Development Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/SkillRouter.git
cd SkillRouter

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Start dev server
python -m app.main
```

### Code Style

- Follow PEP 8 for Python
- Use type hints everywhere
- Write docstrings for public APIs
- Add tests for new features

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) — amazing Python web framework
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP server framework
- [pgvector](https://github.com/pgvector/pgvector) — vector search for PostgreSQL
- [Alpine.js](https://alpinejs.dev/) — lightweight JavaScript framework
- [Tailwind CSS](https://tailwindcss.com/) — utility-first CSS

---

<div align="center">

**Made with ❤️ for the AI agent community**

[⬆ Back to Top](#skillrouter)

</div>