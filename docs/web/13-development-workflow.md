# 开发工作流文档

## 1. 概述

本文档描述如何在 AIDP 系统中开发新工具、修改现有模块、添加新功能。

## 2. 开发新工具

### 2.1 工具目录结构

```
tools/my-tool/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置
│   ├── models.py            # 数据模型
│   ├── services/            # 业务逻辑
│   │   ├── __init__.py
│   │   └── my_service.py
│   └── api/
│       ├── __init__.py
│       ├── tool.py          # 标准工具 API
│       └── routes.py        # 额外 API 路由
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── tool.yaml                # 工具清单
└── README.md
```

### 2.2 实现标准 API 契约

每个工具必须实现以下端点：

```python
# app/api/tool.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ToolInvokeRequest(BaseModel):
    trace_id: str
    capability: str
    context: dict = {}
    input: dict = {}

class ToolInvokeResponse(BaseModel):
    trace_id: str
    tool: str
    capability: str
    success: bool
    output: dict = None
    error: dict = None
    elapsed_ms: int

@router.get("/health")
async def health():
    return {"status": "ok", "tool": "my-tool", "version": "0.1.0"}

@router.get("/tool/manifest")
async def manifest():
    return {
        "name": "my-tool",
        "version": "0.1.0",
        "description": "我的工具",
        "capabilities": [...]
    }

@router.get("/tool/capabilities")
async def capabilities():
    return [
        {
            "name": "my-tool.do_something",
            "description": "执行某操作",
            "input_schema": {...},
            "output_schema": {...}
        }
    ]

@router.post("/tool/invoke")
async def invoke(req: ToolInvokeRequest):
    # 路由到具体处理函数
    if req.capability == "my-tool.do_something":
        result = await do_something(req.input)
        return ToolInvokeResponse(
            trace_id=req.trace_id,
            tool="my-tool",
            capability=req.capability,
            success=True,
            output=result
        )
```

### 2.3 注册到 Controller

```python
# 工具启动后，通过 REST API 注册
POST http://localhost:8883/api/tools
{
    "name": "my-tool",
    "endpoint": "http://127.0.0.1:18086",
    "displayName": "我的工具",
    "description": "工具描述",
    "version": "0.1.0"
}
```

### 2.4 实现 MCP 能力（可选）

如果工具需要被 AI Agent 直接调用，在 Controller MCP Server 中添加工具函数：

```python
# apps/controller/app/mcp/server.py
@mcp.tool()
async def my_tool_do_something(arguments: str) -> str:
    """执行某操作"""
    import json
    args = json.loads(arguments)
    result = await invoke_tool("my-tool", "my-tool.do_something", args)
    return json.dumps(result)
```

## 3. 修改 Controller 模块

### 3.1 模块目录结构

```
apps/controller/app/modules/my_module/
├── __init__.py
├── models.py           # SQLAlchemy 模型
├── routes.py           # API 路由
├── services.py         # 业务逻辑
├── templates_routes.py # 模板路由（可选）
└── templates/          # 页面模板（可选）
    ├── my_page.html
    └── my_page_content.html
```

### 3.2 创建模块

```python
# apps/controller/app/modules/my_module/__init__.py
from app.core.module_registry import register_module

@register_module(name='my_module', dependencies=['knowledge'])
class MyModule:
    name = 'my_module'
    description = '我的模块'
    version = '1.0.0'
    
    def register_routes(self, app):
        from .routes import router
        app.include_router(router, prefix="/api/my-module")
    
    def register_models(self):
        from . import models
        return models
```

### 3.3 添加 API 路由

```python
# apps/controller/app/modules/my_module/routes.py
from fastapi import APIRouter, Depends
from app.core.permissions import PermissionChecker

router = APIRouter()

@router.get("/items")
async def list_items(user=Depends(PermissionChecker(["my_module:read"]))):
    # 业务逻辑
    return {"items": [...]}

@router.post("/items")
async def create_item(data: dict, user=Depends(PermissionChecker(["my_module:write"]))):
    # 业务逻辑
    return {"id": "new_item_id"}
```

### 3.4 添加数据模型

```python
# apps/controller/app/modules/my_module/models.py
from sqlalchemy import Column, String, Integer, DateTime
from app.db.database import Base

class MyItem(Base):
    __tablename__ = "aidp_my_items"
    
    id = Column(String(32), primary_key=True)
    name = Column(String(256), nullable=False)
    owner_id = Column(String(128), nullable=False)
    created_at = Column(DateTime, server_default="now()")
```

### 3.5 添加前端页面

```html
<!-- apps/controller/app/modules/my_module/templates/my_page_content.html -->
<div x-data="myPage()" x-init="init()">
    <div class="flex items-center justify-between">
        <div>
            <h1 class="text-xl font-bold text-white tracking-tight">我的页面</h1>
            <p class="text-sm text-gray-400 mt-0.5">页面描述</p>
        </div>
        <button @click="showCreateModal = true"
                class="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 ...">
            创建
        </button>
    </div>
    
    <!-- 内容 -->
    <div class="pt-5">
        <!-- 列表等 -->
    </div>
</div>

<script>
window.myPage = function() {
    return {
        items: [],
        loading: false,
        
        async init() {
            await this.loadItems();
        },
        
        async loadItems() {
            this.loading = true;
            try {
                var r = await fetch('/api/my-module/items');
                if (r.ok) {
                    var d = await r.json();
                    this.items = d.items || [];
                }
            } finally { this.loading = false; }
        }
    };
};
</script>
```

## 4. 添加菜单项

### 4.1 编辑菜单配置

**文件**: `apps/controller/app/config/menu.yaml`

```yaml
groups:
  - group: "my-module"
    title: "我的模块"
    icon: "fas fa-cube"
    order: 50
    items:
      - id: "my-module-items"
        label: "项目列表"
        icon: "fas fa-list"
        route: "/my-module/items"
        description: "管理我的项目"
```

### 4.2 添加路由

```python
# apps/controller/app/web/routes.py
@router.get("/my-module/items", response_class=HTMLResponse)
async def my_module_items_page(request: Request):
    user = await get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return render_template(request, "modules/my_module/my_page_content.html", {
        "current_user": user.to_dict()
    })
```

## 5. 测试流程

### 5.1 单元测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_health.py -v

# 运行带覆盖率的测试
pytest tests/ --cov=app --cov-report=html
```

### 5.2 集成测试

```bash
# 启动本地开发服务器
uvicorn app.main:app --reload --port 8883

# 测试 API
curl http://localhost:8883/health
curl http://localhost:8883/api/tools
```

### 5.3 MCP 测试

```bash
# 测试 MCP 端点
curl -X POST http://localhost:8883/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## 6. 部署流程

### 6.1 开发环境

```bash
# 本地开发
uvicorn app.main:app --reload --port 8883

# 或使用 Docker
docker-compose up -d
```

### 6.2 生产部署

```bash
# 1. 上传代码到 NAS
scp -r apps/controller/ root@192.168.0.100:/home/docker/AI-Code/controller/

# 2. 构建镜像
ssh root@192.168.0.100 "cd /home/docker/AI-Code/controller && docker build --no-cache -t aidp/controller:0.1.0 ."

# 3. 重启容器
ssh root@192.168.0.100 "docker stop aidp-controller && docker rm aidp-controller && docker run -d --name aidp-controller --network host -v /home/docker/AI-Code/controller/data:/app/data -e DATABASE_URL=... --restart unless-stopped aidp/controller:0.1.0"
```

## 7. 代码规范

### 7.1 Python 代码规范

- 使用 type hints
- 遵循 PEP 8
- 函数和类添加 docstring
- 使用 async/await 处理异步操作
- 错误处理使用 HTTPException

### 7.2 前端代码规范

- 使用 Alpine.js 组件模式
- 组件函数注册到 window 对象
- 不要在 `_content.html` 中使用 `<html><head><body>`
- 布局样式由 Workspace 自动注入

### 7.3 数据库规范

- 表名使用 `aidp_` 前缀
- 使用 VARCHAR(32) 作为主键（UUID）
- 使用 DateTime 作为时间戳
- 所有表包含 `created_at` 字段

## 8. 关键文件索引

| 文件 | 用途 |
|------|------|
| `apps/controller/app/core/module_registry.py` | 模块注册表 |
| `apps/controller/app/core/permissions.py` | 权限检查 |
| `apps/controller/app/config/menu.yaml` | 菜单配置 |
| `apps/controller/app/config/permissions.yaml` | 权限配置 |
| `apps/controller/app/db/database.py` | 数据库连接 |
| `apps/controller/app/db/models.py` | 数据模型 |
| `apps/controller/app/main.py` | 应用入口 |
| `apps/controller/app/web/routes.py` | Web 路由 |
| `tools/*/app/api/tool.py` | 工具标准 API |
