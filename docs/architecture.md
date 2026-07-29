# AIDP Controller - 技术架构文档

## 一、技术栈

### 后端
- **框架**: FastAPI (Python 3.13+)
- **ORM**: SQLAlchemy 2.0 (async)
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **模板引擎**: Jinja2
- **认证**: Session + Cookie (`aidp_session`)
- **启动**: `uvicorn app.main:app --host 0.0.0.0 --port 8883`

### 前端
- **框架**: Alpine.js 3.15 (CDN, 无构建步骤)
- **样式**: Tailwind CSS v4 (CDN `@tailwindcss/browser@4`)
- **图标**: Font Awesome 6 (CDN)
- **图表**: D3.js v7 (CDN, 仅记忆图谱)
- **状态管理**: Alpine `x-data` 组件内状态 + 全局默认值

### 部署
- **容器化**: Docker, `network_mode: host`
- **NAS**: `192.168.0.100`, SSH key `~/.ssh/nas_temp`
- **容器名**: `aidp-controller`
- **代码路径**: NAS `/home/docker/AI-Code/controller/`, 容器 `/app/`

---

## 二、页面加载原理

### 双文件模式
每个功能页面有两个模板文件：
```
modules/{module}/{name}.html           # 完整页面，继承布局
modules/{module}/{name}_content.html   # 内容片段，无布局（供 workspace partial 加载）
```

### Workspace 布局 (`layouts/workspace.html`)
- 主入口 `/` → 渲染 workspace → 侧边栏菜单加载自 `/api/menu`
- 点击菜单项 → `openTab(id, name, icon, url)`:
  1. 请求 `{url}?partial=1`
  2. 服务端 `render_template()` 自动切换到 `{name}_content.html`
  3. 提取 `<script>` 内容 → `eval` 注册到 `window`
  4. `replaceChildren` 插入 DOM
  5. `Alpine.initTree()` 初始化组件
- 菜单数据源: `config/menu.yaml` → 按角色过滤后由 `/api/menu` 返回

### Hub 设计
- 知识中心 / 技能库 / 记忆中心 是 Hub 菜单组
- 点击 Hub 标题在侧边栏展开子菜单（`toggleHub`），不再跳转独立页面
- 子菜单项点击后通过 partial 加载对应页面

### 全局 Alpine 默认值
`workspace.html` 中定义所有组件的变量默认值，防止 `ReferenceError`：
```javascript
function _(name, val) { if (window[name] === undefined) window[name] = val; }
_('showCreateModal', false);
_('showDetailModal', false);
// ... 40+ 变量
```

---

## 三、核心模块

### 1. 知识库 (`modules/knowledge/`)

**模型**:
| 表 | 关键字段 |
|---|---|
| `aidp_knowledge_bases` | id, name, slug, kb_level, parent_id, domains, keywords, tech_stack, visibility, chunk_size |
| `aidp_knowledge_documents` | id, base_id, title, content, category, tags, version, index_status, summary |
| `aidp_document_chunks` | id, document_id, content, chunk_index, embedding |
| `aidp_project_knowledge_bindings` | project_id, knowledge_base_id, binding_type |

**页面**:
| 路由 | 模板 | 功能 |
|---|---|---|
| `/knowledge/bases` | `bases_content.html` | KB 层级树、创建/编辑/删除、网页导入 |
| `/knowledge/documents` | `documents_content.html` | 文档列表、新建/上传/编辑/删除、分类筛选 |
| `/knowledge/search` | `search_content.html` | 全文搜索、评分排序、高亮 |
| `/knowledge/templates` | `templates_content.html` | 文档模板 CRUD |

**API 端点**: `/api/knowledge/bases`, `/api/knowledge/documents`, `/api/knowledge/search` 等

### 2. 技能 (`modules/skills/`)

**模型**:
| 表 | 关键字段 |
|---|---|
| `aidp_skills` | id, name, description, instruction, content, tags, version, exec_config, review_status, review_report, review_log, source_id |
| `aidp_skill_groups` | id, name, parent_id, scope |
| `aidp_skill_files` | id, skill_id, path, content, language |
| `aidp_skill_evolutions` | id, skill_id, old_version, diff_summary, trigger_reason |

**页面**:
| 路由 | 模板 | 功能 |
|---|---|---|
| `/skills/global` | `global_content.html` | 全局技能浏览（admin 可创建/删除）、分组管理 |
| `/skills/personal` | `personal_content.html` | 个人技能 CRUD、导入(GitHub/URL)、审核、exec_config 编辑、版本历史 |

**API**: `/api/skills/create`, `/api/skills/{id}/review`, `/api/skills/{id}/exec-config`, `/api/skills/{id}/evolutions`, `/api/skills/{id}/package`

### 3. 规则 (`modules/rules/`)

**模型**:
| 表 | 关键字段 |
|---|---|
| `aidp_rules` | id, name, content, category, severity, priority, version, pattern, scope |
| `aidp_rule_groups` | id, name, parent_id, scope |

**页面**:
| 路由 | 模板 | 功能 |
|---|---|---|
| `/rules/global` | `global_content.html` | 全局规则（admin 可创建/删除）、优先级显示 |
| `/rules/personal` | `personal_content.html` | 个人规则 CRUD、分组管理、移到分组 |

**API**: `/api/rules/create`, `/api/rules/{id}/move`, `/api/rules/groups/create` 等

### 4. 记忆 (`modules/memory/`)

**模型**:
| 表 | 关键字段 |
|---|---|
| `aidp_memory_entries` | id, title, content, category, memory_tier, embedding, parent_id |
| `aidp_memory_relations` | id, source_id, target_id, relation_type, strength |
| `aidp_context_packages` | id, name, memory_ids, generated_context |
| `aidp_memory_access_logs` | id, memory_id, action |

**页面**:
| 路由 | 模板 | 功能 |
|---|---|---|
| `/memory/memories` | `memories_content.html` | 记忆条目 CRUD、搜索 |
| `/memory/graph` | `graph_content.html` | D3.js 知识图谱可视化 |

### 5. 资产 (`modules/assets/`)

**模型**: `aidp_assets` (title, asset_type, language, content, tags), `aidp_asset_tags`

**页面**: `/assets` → `list_content.html` → 资产列表、创建、详情

**API**: `/api/assets/list`, `/api/assets/create`, `/api/assets/{id}` 等

### 6. 代码沙箱 (`modules/sandbox/`)

**模型**: `aidp_sandbox_executions` (language, code, stdout, stderr, exit_code)

**页面**: `/sandbox` → `index_content.html` → 在线代码编辑器 + 执行结果 + 历史

**API**: `POST /api/sandbox/execute`, `GET /api/sandbox/history`

### 7. 质量检查 (`modules/quality/`)

**模型**: `aidp_quality_checks` (filename, check_type, issues JSON, issue_count)

**页面**: `/quality` → `index_content.html` → 代码检查 + 安全扫描 + 历史

**API**: `POST /api/quality/check`, `GET /api/quality/history`

### 8. 其他模块

| 模块 | 模型 | 页面 | 功能 |
|---|---|---|---|
| Agents | `aidp_agents` | `list_content.html` | Agent 配置管理 |
| Workflows | `aidp_workflows`, `aidp_workflow_steps`, `aidp_workflow_execution` | `list_content.html` | 流程引擎、步骤管理 |
| 认证 | `users`, `user_sessions` (auth_models.py) | `auth/login.html` | Session 认证 |

### 9. 系统管理 (`admin/`)

**页面**: 用户管理、项目管理、指令管理、模型管理、工具注册、NAS 文件、环境配置、审计日志、系统设置

所有 admin 页面通过 `/admin/{name}` 路由渲染，对应 `admin/{name}_content.html` 模板。

---

## 四、设计原则

### 1. Partial 加载优先
- workspace 内所有页面使用 `?partial=1` 加载内容片段
- 不 iframe（所有 hub 已改为 inline 展开）
- 服务端 `render_template()` 自动切换 `_content.html`

### 2. 单文件组件
- 每个 Alpine 组件定义在 `window.{name} = function() { return {...} }` 
- 通过 `eval('window.' + name + ' = ' + code)` 注册
- 函数名必须与 `x-data="{name}()"` 完全匹配

### 3. 菜单驱动
- `config/menu.yaml` 定义全部菜单结构
- 支持 hub / 直接 / 项目分区 / admin 四种类型
- `requires_role` 控制 admin 权限
- `requires_project` 控制项目可见性

### 4. 权限分层
- 后端: `require_permissions()` 装饰器
- 前端: `{% if is_admin %}` Jinja2 条件 + Alpine 全局默认值
- 角色: admin / super_admin / user

### 5. 错误预防
- 所有 Alpine 变量在 `workspace.html` 有全局默认值（`_()` 函数）
- `console.warn` 过滤 "is not defined" 消息
- `window.onerror` + `addEventListener` 双重错误捕获

---

## 五、API 前缀

| 模块 | 前缀 |
|---|---|
| 知识库 | `/api/knowledge` |
| 技能 | `/api/skills` |
| 规则 | `/api/rules` |
| 记忆 | `/api/memory` |
| 资产 | `/api/assets` |
| 沙箱 | `/api/sandbox` |
| 质量 | `/api/quality` |
| Agent | `/api/agents` |
| 工作流 | `/api/workflows` |
| 认证 | `/api/auth` |
| 菜单 | `/api/menu` |
| 项目 | `/api/projects` |

---

## 六、常用部署命令

```bash
# 部署单个文件
scp -i ~/.ssh/nas_temp "local_path" root@192.168.0.100:"nas_path"
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker cp nas_path aidp-controller:container_path && docker exec aidp-controller find /app -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null && docker restart aidp-controller"

# 运行 Python 脚本（迁移/清理）
docker exec -e PYTHONPATH=/app aidp-controller python3 /tmp/script.py

# 查看日志
docker logs aidp-controller --tail 20
```