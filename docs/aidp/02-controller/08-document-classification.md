# Document Classification System

## Overview

The Document Classification system auto-analyzes imported documents and classifies them across multiple dimensions, then routes them to the appropriate storage backend (knowledge base, rules, skills, agents).

### Architecture

```
apps/controller/app/services/doc_classifier.py   -- LLM classifier + rule-based fallback (250 lines)
apps/controller/app/api/classification.py         -- REST API + import routing + storage logic (321 lines)
```

---

## LLM-Powered Classification

**Code location:** `doc_classifier.py:77-151`, `DocClassifier.classify()` + `_call_llm()`

### Entry Point

```python
DocClassifier.classify(title: str, content: str, filename: str = "") -> Dict[str, Any]
```
(line 81-96)

### Flow

1. **Get best chat model** — `ModelService.get_best_for_task("chat")` (`line 82`)
2. **If no model available** → Fall back to rule-based (`line 84-85`)
3. **Truncate content** — First 4000 characters sent to LLM (`line 87`)
4. **Call LLM** — `_call_llm(model, text_for_classify)` (`line 90`)
5. **Validate result** — Returns LLM result only if `"doc_type"` key present (`line 91-92`)
6. **On any error** → Fall back to rule-based (`line 93-96`)

### LLM Call Details

**`_call_llm()`** (line 98-151):

- **Model config required**: `api_base`, `api_key`, `model_name` — if incomplete, returns `None` triggering fallback
- **HTTP**: `POST {api_base}/chat/completions` via `httpx.AsyncClient` with 30s timeout
- **Payload**:
  ```json
  {
    "model": "<model_name>",
    "messages": [
      { "role": "system", "content": "<CLASSIFICATION_PROMPT>" },
      { "role": "user", "content": "文件名: ... 标题: ... 内容: <first 4000 chars>" }
    ],
    "temperature": 0.1,
    "max_tokens": 1024
  }
  ```
- **Response parsing**: Extracts JSON between first `{` and last `}` from LLM output (`line 141-144`)
- **Error handling**: Any non-200 status, JSON parse failure, or HTTP exception → returns `None` → triggers fallback

### Classification Prompt (CLASSIFICATION_PROMPT)

Full system prompt defined at `doc_classifier.py:14-74`. Instructs the LLM to analyze 7+ dimensions:

---

## Classification Dimensions

### 1. `doc_type` — Document Type (line 17)

| Value | Description |
|-------|-------------|
| `"document"` | Normal knowledge document (README, tutorial, architecture, user guide) |
| `"rule"` | Rule constraint (contains must/forbid/不得 clauses) |
| `"skill"` | Skill definition (instruction + content format) |
| `"agent"` | Agent definition (role, instructions, behavior) |
| `"standard"` | Standard/spec (coding, API, design — both doc and rule properties) |

### 2. `category` — Content Category (line 24)

| Value | Description |
|-------|-------------|
| `"architecture"` | Architecture design |
| `"api"` | API documentation |
| `"database"` | Database / SQL / schema |
| `"deployment"` | Deployment / ops |
| `"security"` | Security |
| `"testing"` | Testing |
| `"devops"` | DevOps / CI/CD |
| `"frontend"` | Frontend |
| `"backend"` | Backend |
| `"business"` | Business |
| `"planning"` | Planning / roadmap |
| `"code_style"` | Coding standards |
| `"uncategorized"` | Default |

### 3. `level` — Scope Level (line 39)

| Value | Description |
|-------|-------------|
| `"framework"` | Framework-level (tech-stack generic, e.g. Spring Boot) |
| `"project"` | Project-specific |
| `"template"` | Generic template |

### 4. `tech_stack` — Associated Technologies (line 44)

Array of tech stack names extracted from document content, e.g. `["Spring Boot", "React", "FastAPI"]`.

### 5. `tags` — Keyword Tags (line 46)

Array of keywords summarizing the document.

### 6. `summary` — One-Sentence Summary (line 48)

### 7. `confidence` — Classification Confidence (line 50)

| Value | Meaning |
|-------|---------|
| `"high"` | LLM confident |
| `"medium"` | LLM moderate; also used by fallback |
| `"low"` | Fallback only (no LLM or LLM failed) |

### Type-Specific Fields

**If `doc_type == "rule"`** (line 52):

| Field | Values |
|-------|--------|
| `severity` | `"critical"`, `"high"`, `"medium"`, `"low"` |
| `scope` | `"global"`, `"project"`, `"personal"` |

**If `doc_type == "agent"`** (line 56):

| Field | Description |
|-------|-------------|
| `role` | Agent role description string |
| `has_instructions` | `true`/`false` — whether contains specific instructions |

**If `doc_type == "standard"`** (line 60):

| Field | Description |
|-------|-------------|
| `has_rules` | `true`/`false` — whether contains extractable constraint rules |

---

## Rule-Based Fallback

**Code location:** `doc_classifier.py:153-250`, `DocClassifier._rule_based_fallback()`

Activated when: no chat model available, LLM call fails, or LLM returns no `doc_type`.

### Detection Order (first match wins)

```
1. RULE        ← constraint keywords (必须, 禁止, 不得, 应当, 严禁, severity:, constraint)
                  → severity: "critical" (必须/严禁), "high" (禁止), "low" (建议), "medium" (default)
                  → category: "code_style", scope: "project"

2. SKILL       ← "instruction:" + ("content:" or 执行) in content
                  → category: "uncategorized"

3. AGENT       ← keywords (agent, 角色, 扮演, 你是一个, "you are a", "role:")
                  → has_instructions: true if "instruction" or "指令" in content

4. STANDARD    ← keywords (规范, 标准, 规约, convention, standard, guideline)
                  → has_rules: true if any rule keyword also present

5. DOCUMENT    ← default fallback
                  → category: keyword-matched from cat_map (architecture/api/database/...)
```

### Category Detection for Documents (cat_map)

| Category | Keywords |
|----------|----------|
| `architecture` | 架构, architecture, 设计, design, component |
| `api` | api, 接口, endpoint, rest, graphql |
| `database` | 数据库, database, sql, schema, 表结构 |
| `deployment` | 部署, deploy, 运维, docker, kubernetes, k8s |
| `security` | 安全, security, 认证, 鉴权, oauth, jwt |
| `testing` | 测试, test, unit, integration, e2e |
| `devops` | ci/cd, devops, pipeline, "github action", jenkins |
| `frontend` | 前端, frontend, vue, react, angular, ui |
| `backend` | 后端, backend, server, service |
| `planning` | 计划, plan, 路线图, roadmap, milestone |

---

## REST API

**Code location:** `apps/controller/app/api/classification.py`

### `POST /api/classification/classify`

**Request** (`ClassifyRequest`, line 27-30):
```json
{
  "title": "string (1-500 chars, required)",
  "content": "string (min 1 char, required)",
  "filename": "string (optional)"
}
```

**Response** (`ClassifyResponse`, line 32-34):
```json
{
  "classification": { ... full classification dict ... },
  "source": "llm"  // or "fallback" if confidence == "low"
}
```

### `POST /api/classification/import`

**Request** (`ImportRequest`, line 42-48):
```json
{
  "project_id": 42,
  "kb_name": "optional custom KB name",
  "documents": [
    { "title": "...", "content": "...", "filename": "...", "source_uri": "..." },
    ...
  ],
  "auto_classify": true,
  "auto_create_kb": true
}
```

**Response** (`ImportResult`, line 49-53):
```json
{
  "total": 10,
  "classified": 9,
  "stored": {
    "knowledge": 7,
    "rule": 1,
    "skill": 0,
    "agent": 1
  },
  "errors": ["doc-name: error message..."]
}
```

### Import Routing Logic (line 84-121)

Each document is classified, then **routed to potentially multiple backends** based on `doc_type`:

| doc_type | Storage Backend | Can Co-Exist With |
|----------|----------------|-------------------|
| `"document"` | `_store_as_knowledge()` | — |
| `"standard"` | `_store_as_knowledge()` | `_store_as_rule()` if `has_rules` |
| `"rule"` | `_store_as_rule()` | — |
| `"skill"` | `_store_as_skill()` | — |
| `"agent"` | `_store_as_agent()` | — |

> **Note:** A `"standard"` document can be stored in both knowledge and rules if `has_rules` is true.

---

## Storage Functions

### `_store_as_knowledge()` (line 166-231)

- Auto-creates knowledge base via `_ensure_knowledge_base()` if `auto_create_kb` is set
- Inserts into `aidp_knowledge_documents` with raw SQL
- Generates embedding via `get_embedding()` (model: `"bge-m3"`) for semantic search
- Pushes to `doc-index` at `http://localhost:18087/api/docs` for wiki/code-linking features

### `_store_as_rule()` (line 258-274)

- Inserts into `app.modules.rules.models.Rule`
- Maps `severity` and `scope` from classification

### `_store_as_skill()` (line 277-301)

- Inserts into `app.modules.skills.models.Skill`
- Splits `instruction:` and `content:` parts if present in the document

### `_store_as_agent()` (line 304-321)

- Inserts into `app.modules.agents.models.Agent`
- Uses full document as `instructions` only if `has_instructions` is true
- Stores classification + source in `extra_data` JSON

### `_ensure_knowledge_base()` (line 126-163)

- Auto-creates a `KnowledgeBase` record named from `tech_stack[0] + " " + level + " docs"`
- Falls back to `"{level} knowledge base"` if no tech stack
- Generates slug from name with regex sanitization