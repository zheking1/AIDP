# AIDP 工程化规范手册

> **版本**: v1.1  
> **适用范围**: 所有 AIDP 组件开发  
> **生效日期**: 2026-07-29  

---

## 目录

1. [开发规范](#1-开发规范)
2. [部署流程](#2-部署流程)
3. [测试规范](#3-测试规范)
4. [项目管理](#4-项目管理)
5. [质量控制](#5-质量控制)

---

## 1. 开发规范

### 1.1 代码规范

#### Python 代码规范 (PEP8 + 项目扩展)

**必须遵守:**
- 使用 **Black** 格式化代码 (line-length: 100)
- 使用 **isort** 排序 import (profile: black)
- 使用 **Type Hints** 标注所有函数参数和返回值
- 最大函数行数: 50 行
- 最大类行数: 300 行
- 最大文件行数: 500 行
- 复杂度限制: McCabe < 10

**代码模板:**

```python
"""Module docstring with one-line summary.

Detailed description of the module's purpose and functionality.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

# Standard library imports
import json
from pathlib import Path

# Third-party imports
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

# Local imports
from app.db.models import MemoryEntry
from app.schemas.common import ApiResponse

logger = logging.getLogger(__name__)


async def create_memory_entry(
    db: AsyncSession,
    title: str,
    content: str,
    category: str,
    project: Optional[str] = None,
) -> MemoryEntry:
    """Create a new memory entry.
    
    Args:
        db: Database session
        title: Memory title (max 200 chars)
        content: Memory content
        category: Category (architecture|decision|pattern|issue|bug)
        project: Optional project identifier
    
    Returns:
        Created MemoryEntry instance
    
    Raises:
        ValueError: If category is invalid
        DatabaseError: If database operation fails
    
    Example:
        >>> entry = await create_memory_entry(
        ...     db=session,
        ...     title="API Design Pattern",
        ...     content="Use FastAPI for async APIs",
        ...     category="pattern",
        ...     project="my-project"
        ... )
    """
    if category not in ["architecture", "decision", "pattern", "issue", "bug"]:
        raise ValueError(f"Invalid category: {category}")
    
    entry = MemoryEntry(
        title=title,
        content=content,
        category=category,
        project=project,
        created_at=datetime.utcnow(),
    )
    
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    logger.info(f"Created memory entry: {entry.id}")
    
    return entry
```

**检查命令:**
```bash
# 格式化
black --line-length 100 app/
isort --profile black app/

# 检查
flake8 app/ --max-line-length 100 --max-complexity 10
mypy app/ --strict
pylint app/ --max-line-length=100
```

#### JavaScript/前端代码规范

**必须遵守:**
- 使用 **Prettier** 格式化
- 使用 **ESLint** 检查
- 使用 **JSDoc** 注释函数
- 最大函数行数: 30 行
- 使用可选链操作符 (`?.`) 和空值合并 (`??`)
- 禁止使用 `var`, 使用 `let`/`const`

**代码模板:**

```javascript
/**
 * Calculate estimated token count for text
 * 
 * @param {string} text - Input text to analyze
 * @param {Object} options - Configuration options
 * @param {boolean} [options.includeWhitespace=true] - Whether to count whitespace
 * @returns {number} Estimated token count
 * @throws {TypeError} If text is not a string
 * 
 * @example
 * const tokens = estimateTokens("Hello world", { includeWhitespace: false });
 * console.log(tokens); // 2
 */
function estimateTokens(text, options = {}) {
  if (typeof text !== 'string') {
    throw new TypeError('text must be a string');
  }
  
  const { includeWhitespace = true } = options;
  
  // Chinese characters: ~2 tokens each
  const chineseChars = (text.match(/[\u4e00-\u9fff]/g) ?? []).length;
  
  // Other chars: ~4 chars per token
  const otherChars = text.length - chineseChars;
  
  let tokens = chineseChars * 2 + Math.ceil(otherChars / 4);
  
  if (!includeWhitespace) {
    tokens -= (text.match(/\s/g) ?? []).length / 4;
  }
  
  return Math.max(1, Math.floor(tokens));
}

// Alpine.js Component Pattern
function memoryGraph() {
  return {
    /** @type {Array<Object>} */
    nodes: [],
    
    /** @type {Array<Object>} */
    links: [],
    
    /** @type {Object|null} */
    selectedNode: null,
    
    /** @type {boolean} */
    loading: false,
    
    /**
     * Initialize the graph
     * @returns {Promise<void>}
     */
    async init() {
      await this.loadGraphData();
      this.renderGraph();
    },
    
    /**
     * Load graph data from API
     * @returns {Promise<void>}
     */
    async loadGraphData() {
      this.loading = true;
      
      try {
        const response = await fetch('/api/memories/graph/data');
        const data = await response.json();
        
        this.nodes = data?.nodes ?? [];
        this.links = data?.links ?? [];
      } catch (error) {
        console.error('Failed to load graph:', error);
        this.showError('加载图谱失败');
      } finally {
        this.loading = false;
      }
    },
  };
}
```

### 1.2 Git 工作流程

#### 分支模型 (Git Flow 简化版)

```
main (production)
  ↑
develop (integration)
  ↑
feature/T-123-description
```

**分支命名规范:**
- 功能分支: `feature/T-{ticket}-{description}`
  - 示例: `feature/T-456-add-memory-graph`
- 修复分支: `fix/T-{ticket}-{description}`
  - 示例: `fix/T-789-fix-token-calculation`
- 热修复: `hotfix/{description}`
  - 示例: `hotfix/fix-database-connection`

#### Commit 规范 (Conventional Commits)

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 列表:**
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具变动

**示例:**
```bash
# Good
feat(memory): add vector search API

Implement semantic search using pgvector with cosine similarity.
Supports filtering by project and category.

Closes #123

# Good
fix(api): correct token calculation for Chinese text

Previous algorithm underestimated Chinese tokens by 50%.
Now using 2 tokens per Chinese character.

Fixes #456

# Bad
update code
fix bug
add feature
```

#### 提交前检查清单

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running pre-commit checks..."

# 1. Run linter
flake8 app/ --max-line-length 100 || exit 1

# 2. Run type checker
mypy app/ --strict || exit 1

# 3. Run tests
pytest tests/ -x -q || exit 1

# 4. Check for debug code
if grep -r "print(" app/ --include="*.py" | grep -v "logger"; then
    echo "ERROR: Found print statements, use logger instead"
    exit 1
fi

# 5. Check for TODO/FIXME without ticket
if grep -r "TODO:" app/ --include="*.py" | grep -v "TODO: T-"; then
    echo "WARNING: TODO without ticket number"
fi

echo "All checks passed!"
```

### 1.3 代码审查 (Code Review)

#### 审查清单

**架构层面:**
- [ ] 是否符合 SOLID 原则
- [ ] 是否有重复代码 (DRY)
- [ ] 错误处理是否完善
- [ ] 性能是否合理

**代码层面:**
- [ ] 变量命名清晰
- [ ] 函数单一职责
- [ ] 注释完整
- [ ] Type hints 完整

**安全层面:**
- [ ] 无硬编码密码
- [ ] SQL 注入防护
- [ ] XSS 防护
- [ ] 输入验证

**测试层面:**
- [ ] 单元测试覆盖
- [ ] 边界条件测试
- [ ] 错误路径测试

#### 审查流程

1. **创建 PR** → 填写模板
2. **自动化检查** → CI 通过
3. **人工审查** → 至少 1 人批准
4. **解决评论** → 所有评论 resolved
5. **合并** → Squash & Merge

**PR 模板:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No new warnings

## Testing
How to test this change:
1. Step 1
2. Step 2
3. Expected result

## Related Issues
Fixes #123
```

---

## 2. 部署流程

### 2.1 环境管理

#### 环境定义

| 环境 | 用途 | 数据 | 部署频率 |
|------|------|------|----------|
| Local | 开发 | 测试数据 | 按需 |
| Dev | 集成测试 | 模拟数据 | 每次 PR 合并 |
| Staging | 预发布 | 生产镜像 | 发布前 |
| Production | 生产 | 真实数据 | 每周一次 |

#### 环境配置管理

**12-Factor App 原则:**
- 配置存储在环境变量
- 不使用配置文件存储敏感信息
- 每个环境独立配置

**配置模板:**
```bash
# .env.template (提交到 Git)
DATABASE_URL=postgresql://user:password@host:port/db
REDIS_URL=redis://host:port/0
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=<generate-random-key>

# .env.local (本地开发, 不提交)
DATABASE_URL=postgresql://localhost:5432/aidp_dev
DEBUG=true
LOG_LEVEL=DEBUG
```

### 2.2 CI/CD 流程

#### GitHub Actions 工作流

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ develop, main ]
  pull_request:
    branches: [ develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: ankane/pgvector:latest
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'
    
    - name: Install dependencies
      run: |
        pip install -r requirements-dev.txt
    
    - name: Run linter
      run: |
        flake8 app/ --max-line-length 100
        mypy app/ --strict
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
      run: |
        pytest tests/ -v --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t aidp/${{ github.event.repository.name }}:${{ github.sha }} .
        docker tag aidp/${{ github.event.repository.name }}:${{ github.sha }} aidp/${{ github.event.repository.name }}:latest
    
    - name: Push to registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker push aidp/${{ github.event.repository.name }}:${{ github.sha }}
        docker push aidp/${{ github.event.repository.name }}:latest
```

### 2.3 部署步骤

#### 手动部署流程 (NAS 环境)

```bash
#!/bin/bash
# deploy.sh

set -e  # Exit on error

SERVICE_NAME=$1
VERSION=$2
ENV=${3:-production}

if [ -z "$SERVICE_NAME" ] || [ -z "$VERSION" ]; then
    echo "Usage: ./deploy.sh <service-name> <version> [environment]"
    exit 1
fi

echo "🚀 Deploying $SERVICE_NAME:$VERSION to $ENV"

# 1. Pre-deployment checks
echo "📋 Running pre-deployment checks..."
ssh nas "docker pull aidp/$SERVICE_NAME:$VERSION" || exit 1

# 2. Database migrations
echo "🗄️ Running database migrations..."
ssh nas "cd /home/docker/$SERVICE_NAME && docker-compose run --rm app alembic upgrade head" || exit 1

# 3. Health check current version
echo "🏥 Health checking current version..."
CURRENT_HEALTH=$(ssh nas "curl -s http://localhost:${SERVICE_PORT}/health | jq -r '.status'")
if [ "$CURRENT_HEALTH" != "ok" ]; then
    echo "⚠️ Warning: Current version is not healthy"
fi

# 4. Deploy new version
echo "🔄 Deploying new version..."
ssh nas "cd /home/docker/$SERVICE_NAME && docker-compose up -d" || exit 1

# 5. Wait for startup
echo "⏳ Waiting for startup..."
sleep 10

# 6. Post-deployment health check
echo "🏥 Running health checks..."
for i in {1..5}; do
    HEALTH=$(ssh nas "curl -s http://localhost:${SERVICE_PORT}/health | jq -r '.status'")
    if [ "$HEALTH" == "ok" ]; then
        echo "✅ Health check passed!"
        break
    fi
    echo "Attempt $i: Health check failed, retrying..."
    sleep 5
done

if [ "$HEALTH" != "ok" ]; then
    echo "❌ Health check failed, rolling back..."
    ssh nas "cd /home/docker/$SERVICE_NAME && docker-compose rollback"
    exit 1
fi

# 7. Smoke tests
echo "🧪 Running smoke tests..."
ssh nas "cd /home/docker/$SERVICE_NAME && docker-compose run --rm app pytest tests/smoke/ -v" || exit 1

echo "✅ Deployment successful!"

# 8. Cleanup
echo "🧹 Cleaning up old images..."
ssh nas "docker system prune -f"
```

### 2.3.1 禁止使用 `docker cp` 部署（强制规则）

> **严禁在任何环境下使用 `docker cp` 进行代码部署。必须通过重新构建 Docker 镜像完成。**

#### 为什么禁止

| `docker cp` 的问题 | 后果 |
|---|---|
| Python 字节码缓存不更新 | `.pyc` 文件未重新编译，代码改动不生效 |
| 应用内配置缓存未失效 | `config_loader.py` 等模块的 `_cache` 字典不清空 |
| Jinja2 模板缓存未失效 | 前端 HTML 改动不可见 |
| 重启不解决问题 | `docker restart` 只是重启进程，不重建文件系统层 |
| 状态不可追溯 | 无法确定容器内实际运行的是哪个版本 |

#### 正确做法

```bash
# 1. 上传完整源码到 NAS
tar czf controller-src.tar.gz -C apps/controller .
scp controller-src.tar.gz root@192.168.0.100:/tmp/

# 2. 解压到部署目录
ssh nas "cd /home/docker/AI-Code/controller && tar xzf /tmp/controller-src.tar.gz"

# 3. 重新构建镜像
ssh nas "cd /home/docker/AI-Code/controller && docker build -t aidp/controller:0.1.0 ."

# 4. 删除旧容器 + 重建新容器（不是 restart）
ssh nas "docker stop aidp-controller && docker rm aidp-controller"
ssh nas "cd /home/docker/AI-Code && docker compose up -d controller"

# 5. 验证
ssh nas "curl -sf http://127.0.0.1:8883/health"
```

#### 检查清单

- [ ] 使用 `docker build` 重建了镜像（非 `docker cp`）
- [ ] 使用 `docker rm` + `docker compose up` 重建了容器（非 `docker restart`）
- [ ] 验证新代码在容器内生效（`docker exec {container} grep {new_code_pattern} {file}`）

#### 部署检查清单

**部署前:**
- [ ] 版本号已更新
- [ ] CHANGELOG.md 已更新
- [ ] 数据库迁移已测试
- [ ] 配置变量已设置
- [ ] 回滚计划已准备

**部署中:**
- [ ] 健康检查通过
- [ ] 日志无错误
- [ ] 关键功能测试通过
- [ ] 性能指标正常

**部署后:**
- [ ] 监控无告警
- [ ] 用户反馈正常
- [ ] 文档已更新

---

## 3. 测试规范

### 3.1 测试金字塔

```
       /\
      /  \
     / E2E\      (10%)  - 用户场景
    /______\
   /        \
  /Integration\  (30%)  - API/集成
 /____________\
/              \
/   Unit Tests   \ (60%)  - 函数/类
/________________\
```

### 3.2 单元测试规范

**要求:**
- 覆盖率 ≥ 80%
- 核心业务逻辑覆盖率 ≥ 95%
- 每个函数至少一个测试
- 边界条件必须测试
- 错误路径必须测试

**测试结构:**

```python
# tests/test_memory_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.services.memory_service import MemoryService
from app.db.models import MemoryEntry


class TestMemoryService:
    """Test suite for MemoryService."""
    
    @pytest.fixture
    def service(self):
        return MemoryService()
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_create_memory_success(self, service, mock_db):
        """Test creating a memory entry successfully."""
        # Arrange
        data = {
            "title": "Test Memory",
            "content": "Test content",
            "category": "pattern",
        }
        
        # Act
        result = await service.create_memory(mock_db, data)
        
        # Assert
        assert result.title == "Test Memory"
        assert result.category == "pattern"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_memory_invalid_category(self, service, mock_db):
        """Test creating memory with invalid category raises error."""
        # Arrange
        data = {
            "title": "Test",
            "content": "Content",
            "category": "invalid",
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid category"):
            await service.create_memory(mock_db, data)
    
    @pytest.mark.asyncio
    async def test_search_memories_empty_query(self, service, mock_db):
        """Test searching with empty query returns empty results."""
        # Act
        results = await service.search_memories(mock_db, query="")
        
        # Assert
        assert results == []
    
    @pytest.mark.parametrize("category,expected", [
        ("architecture", True),
        ("decision", True),
        ("invalid", False),
    ])
    def test_validate_category(self, service, category, expected):
        """Test category validation with multiple inputs."""
        result = service.validate_category(category)
        assert result == expected
```

**运行命令:**
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Run specific test
pytest tests/test_memory_service.py::TestMemoryService::test_create_memory_success -v

# Run with debugger
pytest tests/ --pdb
```

### 3.3 集成测试规范

**API 集成测试:**

```python
# tests/integration/test_memory_api.py
import pytest
from httpx import AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client):
    """Get authentication headers."""
    response = await client.post("/api/auth/login", json={
        "username": "test@example.com",
        "password": "testpassword"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestMemoryAPI:
    """Integration tests for Memory API."""
    
    @pytest.mark.asyncio
    async def test_create_memory_api(self, client, auth_headers):
        """Test POST /api/memories endpoint."""
        # Arrange
        payload = {
            "title": "API Test Memory",
            "content": "Content from API test",
            "category": "pattern",
        }
        
        # Act
        response = await client.post(
            "/api/memories",
            json=payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "API Test Memory"
        assert data["category"] == "pattern"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, client, auth_headers):
        """Test GET /api/memories/{id} with non-existent ID."""
        # Act
        response = await client.get(
            "/api/memories/00000000-0000-0000-0000-000000000000",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
```

### 3.4 E2E 测试规范

**使用 Playwright:**

```python
# tests/e2e/test_memory_graph.py
import pytest
from playwright.async_api import async_playwright


@pytest.fixture
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


class TestMemoryGraph:
    """E2E tests for Memory Graph visualization."""
    
    @pytest.mark.asyncio
    async def test_graph_loads_successfully(self, browser):
        """Test that the memory graph page loads and displays nodes."""
        # Arrange
        page = await browser.new_page()
        await page.goto("http://localhost:18085/memory-graph")
        
        # Act
        await page.wait_for_selector("#graph-svg", timeout=10000)
        await page.wait_for_load_state("networkidle")
        
        # Assert
        nodes = await page.query_selector_all(".graph-node")
        assert len(nodes) > 0, "Graph should display nodes"
        
        await page.close()
    
    @pytest.mark.asyncio
    async def test_node_click_shows_details(self, browser):
        """Test clicking a node shows detail panel."""
        # Arrange
        page = await browser.new_page()
        await page.goto("http://localhost:18085/memory-graph")
        await page.wait_for_selector(".graph-node")
        
        # Act
        await page.click(".graph-node:first-child")
        
        # Assert
        detail_panel = await page.query_selector(".node-details")
        assert detail_panel is not None
        
        title = await page.inner_text(".node-details .title")
        assert len(title) > 0
        
        await page.close()
```

### 3.4.1 交互元素全面测试（按钮 / 超链接 / 点击事件）

> **核心原则：页面上每一个可点击的元素都必须经过测试，不能遗漏任何一个按钮或链接。**

**按钮分类测试矩阵：**

| 按钮类型 | 测试重点 | 预期结果 |
|----------|----------|----------|
| 创建类 | 打开表单 → 填写 → 保存 | API 200 + 列表刷新 + 数据可见 |
| 编辑类 | 数据回显 → 修改 → 保存 | 原始值正确 + 更新后可见 |
| 删除类 | 确认对话框 → 确认删除 | API 200 + 列表项减少 |
| 查看类 | 弹窗展示详情 | 字段与数据库一致 |
| 导航类 | 跳转/加载目标页面 | 无 404，页面正常渲染 |
| 搜索/筛选 | 输入/选择 → 列表过滤 | 结果正确，数量匹配 |
| 分页类 | 上下页/页码跳转 | 数据变化，高亮正确 |
| 状态切换 | 启用/禁用/锁定 | 状态变更反映在列表中 |
| 取消/关闭 | 弹窗关闭 | 数据未保存，列表不变 |

**每个按钮点击后必须验证 4 项：**
1. **视觉反馈** — 按钮有响应，无卡死
2. **行为触发** — 弹窗打开 / 页面跳转 / API 调用 / 数据变化
3. **无控制台错误** — 无 `ReferenceError` / `TypeError`
4. **结果正确** — API 200 + 数据变更 + UI 更新

**超链接测试：**
- [ ] 所有 `<a href>` 可点击，无死链
- [ ] 内部路由跳转正确（无 404）
- [ ] 外部链接新窗口打开
- [ ] 锚点链接正确滚动

**CRUD 完整链路验证（Create / Read / Update / Delete）：**
- Create: 按钮 → 弹窗 → 填写 → 保存 → 列表增加 → 数据可见 → 数据库存在
- Read: 列表加载 → 详情展示 → 字段一致 → 空状态友好
- Update: 编辑按钮 → 数据回显 → 修改 → 保存 → 列表更新 → 数据库变更
- Delete: 删除按钮 → 确认 → 删除 → 列表减少 → 数据消失 → 数据库删除

### 3.5 性能测试

**使用 Locust:**

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between


class MemoryUser(HttpUser):
    """Simulate user interactions with Memory Tool."""
    
    wait_time = between(1, 5)
    
    def on_start(self):
        """Login before starting tasks."""
        response = self.client.post("/api/auth/login", json={
            "username": "test@example.com",
            "password": "testpassword"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def search_memories(self):
        """Search memories - common operation."""
        self.client.post(
            "/api/memories/search/vector",
            json={"query": "API design pattern", "top_k": 10},
            headers=self.headers
        )
    
    @task(2)
    def get_graph_data(self):
        """Load graph data - heavy operation."""
        self.client.get(
            "/api/memories/graph/data",
            headers=self.headers
        )
    
    @task(1)
    def create_memory(self):
        """Create memory - write operation."""
        self.client.post(
            "/api/memories",
            json={
                "title": "Performance Test Memory",
                "content": "Test content",
                "category": "pattern"
            },
            headers=self.headers
        )
```

**运行性能测试:**
```bash
locust -f tests/performance/locustfile.py --host=http://localhost:18085
```

---

## 4. 项目管理

### 4.1 任务管理

#### 任务拆分原则

**INVEST 原则:**
- **I**ndependent: 独立
- **N**egotiable: 可协商
- **V**aluable: 有价值
- **E**stimable: 可估算
- **S**mall: 小粒度
- **T**estable: 可测试

**任务粒度:**
- 每个任务应在 1-3 天内完成
- 超过 3 天的任务必须拆分
- 每个任务必须有验收标准

**任务模板:**
```markdown
## Description
As a [role], I want [feature] so that [benefit].

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Notes
- API endpoint: POST /api/memories
- Database changes: Add embedding column
- Dependencies: pgvector extension

## Estimation
- Story Points: 5
- Estimated Hours: 16

## Subtasks
- [ ] Database migration (2h)
- [ ] API implementation (6h)
- [ ] Frontend integration (4h)
- [ ] Testing (4h)
```

### 4.2 进度跟踪

#### 每日站会 (Daily Standup)

**时间**: 每天 9:30, 15 分钟
**参与者**: 所有开发人员
**问题**:
1. 昨天完成了什么？
2. 今天计划做什么？
3. 有什么阻碍？

#### 进度报告模板

```markdown
# Weekly Progress Report

## Week: 2026-07-01 to 2026-07-07

### Completed
- ✅ T-123: Implement vector search API (8h / 8h)
- ✅ T-124: Add D3.js graph visualization (12h / 10h)

### In Progress
- 🔄 T-125: Context package builder (6h / 12h, 50%)
  - Blocker: Waiting for token calculation API

### Planned
- 📋 T-126: Review queue implementation
- 📋 T-127: Performance optimization

### Risks
- **HIGH**: Database migration may take longer than expected
- **MEDIUM**: Token calculation accuracy needs validation

### Metrics
- Velocity: 20 story points/week
- Bug count: 3 (2 fixed, 1 in progress)
- Test coverage: 82% (+5%)
```

### 4.3 风险管理

#### 风险登记册

| ID | 风险描述 | 可能性 | 影响 | 缓解措施 | 负责人 |
|----|---------|-------|------|---------|-------|
| R1 | pgvector 性能不佳 | 中 | 高 | 准备 Qdrant 备选方案 | 架构组 |
| R2 | D3.js 大数据量卡顿 | 中 | 中 | 实现分页加载 + 虚拟化 | 前端组 |
| R3 | Token 计算不准确 | 高 | 中 | 多模型验证 + 用户反馈 | 算法组 |
| R4 | 第三方 API 限流 | 低 | 高 | 实现缓存 + 降级策略 | 后端组 |

#### 升级机制

```
Level 1: 团队成员解决 (日常技术问题)
    ↓ 30分钟未解决
Level 2: Tech Lead 介入 (架构/设计问题)
    ↓ 2小时未解决
Level 3: 架构师介入 (系统级问题)
    ↓ 4小时未解决
Level 4: 管理层决策 (资源/范围变更)
```

---

## 5. 质量控制

### 5.1 质量门禁

#### 代码合并门禁

```yaml
# 必须通过以下检查才能合并
merge_requirements:
  - lint_passed: true
  - type_check_passed: true
  - unit_test_coverage: ">= 80%"
  - integration_tests_passed: true
  - code_review_approved: ">= 1"
  - security_scan_passed: true
  - documentation_updated: true
```

#### 发布门禁

```yaml
# 必须通过以下检查才能发布
release_requirements:
  - all_tests_passed: true
  - e2e_tests_passed: true
  - performance_benchmark_met: true
  - security_audit_passed: true
  - changelog_updated: true
  - version_tagged: true
  - rollback_tested: true
```

### 5.2 监控与告警

#### 关键指标

| 指标 | 警告阈值 | 严重阈值 | 响应时间 |
|------|---------|---------|---------|
| API 错误率 | > 1% | > 5% | 5min |
| API 响应时间 (P95) | > 500ms | > 1000ms | 10min |
| 数据库连接池 | > 70% | > 90% | 5min |
| 内存使用 | > 80% | > 95% | 5min |
| 磁盘使用 | > 80% | > 90% | 30min |

#### 告警模板

```json
{
  "alert": "HighErrorRate",
  "severity": "critical",
  "service": "memory-tool",
  "message": "Error rate is 8% (>5% threshold)",
  "timestamp": "2026-07-07T10:30:00Z",
  "runbook": "https://wiki/runbooks/high-error-rate",
  "dashboard": "http://grafana/d/memory-tool"
}
```

### 5.3 故障响应

#### 故障等级

| 等级 | 描述 | 响应时间 | 解决时间 | 通知方式 |
|------|------|---------|---------|---------|
| P0 | 系统完全不可用 | 5分钟 | 1小时 | 电话 + 短信 + 邮件 |
| P1 | 核心功能不可用 | 15分钟 | 4小时 | 短信 + 邮件 |
| P2 | 部分功能受影响 | 1小时 | 24小时 | 邮件 |
| P3 | 轻微问题 | 4小时 | 1周 | 邮件 |

#### 故障响应流程

```
1. Detect (监控/用户反馈)
   ↓
2. Triage (定级 + 指派)
   ↓
3. Communicate (通知相关方)
   ↓
4. Mitigate (止血: 降级/限流/重启)
   ↓
5. Fix (修复)
   ↓
6. Verify (验证)
   ↓
7. Postmortem (复盘)
```

---

## 附录

### A. 工具清单

| 类别 | 工具 | 用途 |
|------|------|------|
| 代码质量 | Black, isort, flake8, mypy | 代码格式化与检查 |
| 测试 | pytest, playwright, locust | 单元/E2E/性能测试 |
| CI/CD | GitHub Actions | 自动化流程 |
| 监控 | Prometheus, Grafana | 指标收集与可视化 |
| 日志 | ELK Stack | 日志收集与分析 |
| 文档 | Markdown, Swagger | 技术文档与 API 文档 |

### B. 参考资料

- [PEP 8 - Style Guide for Python Code](https://pep8.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [12-Factor App](https://12factor.net/)
- [Google Testing Blog](https://testing.googleblog.com/)

---

**文档版本**: v1.0  
**最后更新**: 2026-07-07  
**维护者**: AIDP Engineering Team
