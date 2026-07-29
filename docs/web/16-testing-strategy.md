# 测试策略文档

## 1. 概述

AIDP 系统采用分层测试策略：
1. **单元测试** — 测试单个函数/类
2. **集成测试** — 测试模块间交互
3. **端到端测试** — 测试完整用户流程
4. **性能测试** — 测试系统性能指标

## 2. 测试框架

| 组件 | 框架 | 说明 |
|------|------|------|
| 后端 | pytest | Python 测试框架 |
| 异步测试 | pytest-asyncio | 支持 async/await |
| HTTP 测试 | httpx | 异步 HTTP 客户端 |
| 覆盖率 | pytest-cov | 代码覆盖率 |
| Mock | unittest.mock | Mock 和 patch |

## 3. 单元测试

### 3.1 测试目录结构

```
tests/
├── __init__.py
├── conftest.py           # 共享 fixtures
├── test_health.py        # 健康检查测试
├── test_auth.py          # 认证测试
├── test_tools.py         # 工具管理测试
├── test_projects.py      # 项目管理测试
├── test_knowledge.py     # 知识库测试
├── test_memory.py        # 记忆系统测试
├── test_permissions.py   # 权限测试
└── test_mcp.py           # MCP 测试
```

### 3.2 编写单元测试

```python
# tests/test_health.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "UP"
    assert data["service"] == "AIDP Controller"
```

### 3.3 测试工具调用

```python
# tests/test_tools.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.anyio
async def test_invoke_tool():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 先登录获取 session
        login_resp = await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        
        # 调用工具
        resp = await client.post("/api/tools/sandbox-tool/invoke", json={
            "capability": "sandbox.execute",
            "arguments": {"code": "print(1)", "language": "python"}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
```

### 3.4 测试权限

```python
# tests/test_permissions.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.anyio
async def test_unauthorized_access():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 未登录访问受保护的 API
        resp = await client.get("/api/tools")
        assert resp.status_code == 401

@pytest.mark.anyio
async def test_authorized_access():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 登录
        await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        # 访问受保护的 API
        resp = await client.get("/api/tools")
        assert resp.status_code == 200
```

## 4. 集成测试

### 4.1 测试工具注册流程

```python
# tests/test_tool_registration.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.anyio
async def test_tool_registration_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 登录
        await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        # 注册工具
        resp = await client.post("/api/tools", json={
            "name": "test-tool",
            "endpoint": "http://localhost:18099",
            "displayName": "测试工具"
        })
        assert resp.status_code == 201
        tool_id = resp.json()["id"]
        
        # 验证工具已注册
        resp = await client.get("/api/tools")
        tools = resp.json()["tools"]
        assert any(t["name"] == "test-tool" for t in tools)
```

### 4.2 测试 MCP 上下文管道

```python
# tests/test_mcp_context.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.anyio
async def test_mcp_context_pipeline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 调用 aidp_context
        resp = await client.post("/mcp/", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "aidp_context",
                "arguments": {
                    "project_name": "test-project",
                    "task": "测试任务"
                }
            },
            "id": 1
        })
        assert resp.status_code == 200
        result = resp.json()
        assert "result" in result
```

## 5. 端到端测试

### 5.1 测试用户注册流程

```python
# tests/e2e/test_user_flow.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.anyio
async def test_user_registration_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. 访问登录页面
        resp = await client.get("/login")
        assert resp.status_code == 200
        
        # 2. 登录
        resp = await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert resp.status_code == 200
        
        # 3. 访问工作台
        resp = await client.get("/")
        assert resp.status_code == 200
        
        # 4. 获取菜单
        resp = await client.get("/api/menu")
        assert resp.status_code == 200
        
        # 5. 创建项目
        resp = await client.post("/api/projects", json={
            "name": "e2e-test-project",
            "description": "端到端测试项目"
        })
        assert resp.status_code == 201
```

## 6. 性能测试

### 6.1 API 响应时间测试

```python
# tests/perf/test_api_performance.py
import pytest
import time
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.anyio
async def test_api_response_time():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 登录
        await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        # 测试 API 响应时间
        start = time.time()
        resp = await client.get("/api/tools")
        elapsed = time.time() - start
        
        assert resp.status_code == 200
        assert elapsed < 0.2  # 200ms 内响应
```

### 6.2 并发测试

```python
# tests/perf/test_concurrent.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.anyio
async def test_concurrent_requests():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 登录
        await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        # 并发请求
        async def make_request():
            return await client.get("/api/tools")
        
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # 所有请求都应该成功
        for resp in responses:
            assert resp.status_code == 200
```

## 7. 测试配置

### 7.1 conftest.py

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.fixture
async def authenticated_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 登录
        await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        yield client
```

### 7.2 pytest.ini

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    e2e: marks tests as end-to-end tests
```

## 8. 运行测试

### 8.1 运行所有测试

```bash
pytest tests/ -v
```

### 8.2 运行特定测试

```bash
# 运行单个文件
pytest tests/test_health.py -v

# 运行单个测试
pytest tests/test_health.py::test_health -v

# 运行标记的测试
pytest -m "not slow" -v
```

### 8.3 生成覆盖率报告

```bash
pytest tests/ --cov=app --cov-report=html
```

## 9. 测试数据管理

### 9.1 测试数据库

```python
# 使用独立的测试数据库
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/aidp_test"
```

### 9.2 测试 Fixtures

```python
@pytest.fixture
async def test_project():
    """创建测试项目"""
    # 创建项目
    # 返回项目 ID
    yield project_id
    # 清理测试数据
```

## 10. 持续集成

### 10.1 CI 配置示例

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-asyncio httpx pytest-cov
      - run: pytest tests/ --cov=app --cov-report=xml
```

## 11. 关键文件索引

| 文件 | 用途 |
|------|------|
| `tests/conftest.py` | 共享 fixtures |
| `tests/test_health.py` | 健康检查测试 |
| `tests/test_phase1.py` | 第一阶段功能测试 |
| `pytest.ini` | pytest 配置 |
| `.github/workflows/test.yml` | CI 配置 |
