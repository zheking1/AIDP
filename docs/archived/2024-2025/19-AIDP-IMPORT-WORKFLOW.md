# AIDP 项目导入与创建规范

## 一、已有项目导入流程

### 前置条件
老项目代码需放在 NAS 上：
```bash
rsync -avz /local/project root@192.168.0.100:/home/docker/AI-Code/projects/project-name/
```

### Step 1: 创建项目
```
POST http://192.168.0.100:8883/api/projects/
{
    "name": "项目名",
    "description": "项目描述",
    "type": "python|java|vue|go|rust"
}
```
或 Web UI: http://192.168.0.100:8883/projects → Create Project

### Step 2: 索引代码（Code Index 18086）
```
POST http://192.168.0.100:18086/api/projects
{"name":"project-name","path":"/home/docker/AI-Code/projects/project-name"}

POST http://192.168.0.100:18086/api/index/directory
{"project_id":1,"dir_path":"/home/docker/AI-Code/projects/project-name"}
```
验证：`POST http://192.168.0.100:18086/api/explore {"project_id":1,"action":"summary"}`

### Step 3: 导入文档（Knowledge Tool 18081）
```python
# 自动扫描 README.md、docs/*.md
for doc in find_docs(project_path):
    POST http://192.168.0.100:18081/api/documents
    {
        "workspace_id": "default",
        "title": doc.filename,
        "content": doc.content,
        "doc_type": "markdown",
        "project_id": "1"
    }
```

### Step 4: 导入环境配置（Controller 8883）
```python
# 自动扫描 .env, application.yml, *.properties
for config in find_configs(project_path):
    POST http://192.168.0.100:8883/api/projects/{id}/configs
    {"env_type":"dev","config_key":config.key,"config_value":config.value}
```

### Step 5: 导入脚本/模板（Asset Tool 18082）
```python
# 自动扫描 scripts/*.sh, *.sql, Dockerfile
for script in find_scripts(project_path):
    POST http://192.168.0.100:18082/api/tools
    {"name":script.name,"content":script.content,"type":"script"}
```

### Step 6: 验证
- Dashboard: `http://192.168.0.100:8883/` 查看工具状态
- 搜索: `POST http://192.168.0.100:18081/api/documents/search/semantic?q=xxx`
- API 调试: `http://192.168.0.100:8883/docs`

---

## 二、新建项目创建规范

### 必须创建的文档
| 文档 | 内容 | 导入到 |
|------|------|--------|
| README.md | 项目概述、快速开始 | Knowledge Tool |
| ARCHITECTURE.md | 架构设计、模块说明 | Knowledge Tool |
| API.md | 接口文档 | Knowledge Tool |
| DEPLOY.md | 部署指南 | Knowledge Tool |
| .env.example | 环境变量模板 | Controller Configs |

### 必须创建的配置
```python
configs = {
    "dev": {
        "database_url": "postgresql://...",
        "redis_url": "redis://...",
        "port": "8080"
    }
}
```

### 必须创建的 Memory
```python
memories = [
    {"content":"项目技术栈：Python/FastAPI + PostgreSQL + Redis","tier":"semantic"},
    {"content":"端口分配：Controller 8883, Knowledge 18081,...","tier":"semantic"},
    {"content":"部署文档：NAS上使用docker-compose管理","tier":"episodic"},
]
```

### 必须注册的工具（SkillRouter 8788）
```python
skills = [
    {"name":"code-review","prompt":"Review code for...","rules":["xxx"]},
    {"name":"api-test","prompt":"Test API by...","rules":["xxx"]},
]
```

---

## 三、测试结果（2026-07-03）

| 工具 | 20 项通过 | 8 项待修复 |
|------|----------|-----------|
| Controller | 项目CRUD ✅ | Config写 ❌、审计 ❌ |
| Knowledge | 文档CRUD ✅、语义搜索 ✅ | FTS搜索 ❌ |
| Sandbox | 代码执行 ✅、历史 ✅ | - |
| Quality | Lint检查 ✅、安全检查 ✅ | - |
| Memory | 4级记忆 ✅、隐私过滤 ✅ | - |
| Code Index | 健康检查 ✅ | 列表 ❌ |
| Doc Index | 健康检查 ✅ | 列表 ❌ |
| Context Opt | 健康检查 ✅ | 分析/预算 ❌ |
| Evolution | 健康检查 ✅ | 事件收集 ❌ |

### 已知问题
1. **Context Optimizer / Evolution Engine / Code Index / Doc Index**: 4个工具的 SQLite 数据库在 Docker 容器重启后丢失（未挂载 volume）
2. **Config POST**: 缺少尾部斜杠返回 307 重定向（FastAPI 路由问题）
3. **Audit Logs**: 数据库表不存在（控制器 init_db 未创建）
4. **FTS Search**: API 路由注册问题