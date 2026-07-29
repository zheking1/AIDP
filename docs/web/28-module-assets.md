# Assets Module — 代码资产模块

## 1. 模块概述

Assets（代码资产）模块提供**代码片段、模板和配置的管理**能力。用户可以将常用的代码片段、项目模板和环境配置集中存储，支持标签分类、全文搜索和模板变量渲染。该模块是 AIDP 平台的知识库基础，帮助团队复用代码和标准化配置。

模块定义文件位于 `apps/controller/app/modules/assets/__init__.py`：

```python
@register_module(name='assets', enabled=True)
class AssetsModule(BaseModule):
    """
    代码资产模块
    提供代码片段、模板、配置等资产的存储、搜索和渲染
    """
    name = "assets"
    description = "代码资产管理，支持搜索和模板渲染"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as assets_router
        app.include_router(assets_router, prefix="/api/assets")

    def on_startup(self):
        print(f"[AssetsModule] 资产模块已启动")

    def on_shutdown(self):
        print(f"[AssetsModule] 资产模块已停止")
```

模块没有外部模块依赖（`dependencies = []`），但通过 `project_id` 外键关联项目。

## 2. 数据模型

模块包含 2 个数据模型，定义在 `apps/controller/app/modules/assets/models.py`：

### Asset — 资产主表

```python
class Asset(Base):
    __tablename__ = "aidp_assets"

    id           = Column(String(36), primary_key=True, default=gen_uuid)
    project_id   = Column(Integer, ForeignKey("aidp_projects.id"), nullable=True, index=True)
    user_id      = Column(String(100), nullable=True, index=True)
    title        = Column(String(200), nullable=False, index=True)
    description  = Column(Text, nullable=True)
    asset_type   = Column(String(50), nullable=False, index=True, default="snippet")
    # snippet / template / config / component / utility / documentation
    language     = Column(String(50), nullable=True, index=True)
    format       = Column(String(50), nullable=True, default="text")
    visibility   = Column(String(20), default="project", index=True)
    # project / workspace / global
    content      = Column(Text, nullable=False)
    variables    = Column(Text, default="{}")
    extra_data   = Column(Text, default="{}")
    created_by   = Column(String(100), nullable=True)
    updated_by   = Column(String(100), nullable=True)
    access_count = Column(Integer, default=0)
    created_at   = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at   = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at   = Column(DateTime(timezone=True), nullable=True)

    tags = relationship("AssetTag", back_populates="asset", cascade="all, delete-orphan")
```

**Asset 字段详解：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| project_id | Integer | 所属项目（外键） |
| user_id | String(100) | 所有者 |
| title | String(200) | 资产标题（必填） |
| description | Text | 资产描述 |
| asset_type | String(50) | 资产类型：snippet / template / config / component / utility / documentation |
| language | String(50) | 编程语言（如 python / javascript / yaml） |
| format | String(50) | 格式（text / json / yaml 等） |
| visibility | String(20) | 可见性：project / workspace / global |
| content | Text | 资产内容（必填） |
| variables | Text | JSON 格式的变量定义 |
| extra_data | Text | JSON 格式的额外数据 |
| created_by | String(100) | 创建者 |
| updated_by | String(100) | 最后修改者 |
| access_count | Integer | 访问次数 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| deleted_at | DateTime | 软删除时间 |

### AssetTag — 标签表

```python
class AssetTag(Base):
    __tablename__ = "aidp_asset_tags"

    id       = Column(String(36), primary_key=True, default=gen_uuid)
    asset_id = Column(String(36), ForeignKey("aidp_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    tag      = Column(String(100), nullable=False, index=True)

    asset = relationship("Asset", back_populates="tags")
```

**模型关系：**

```
Asset 1 ── N AssetTag    (通过 asset_id 关联，级联删除)
```

一个资产可以有多个标签（通过 `Asset.tags` relationship 访问），标签作为独立行存储在 `aidp_asset_tags` 表中。

## 3. API 端点

所有路由定义在 `apps/controller/app/modules/assets/routes.py` 中，前缀为 `/api/assets`。

### 端点列表

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/api/assets/list` | 资产列表（支持 type/language/search 筛选） | 登录用户 |
| GET | `/api/assets/stats` | 资产统计 | 登录用户 |
| POST | `/api/assets/create` | 创建资产 | asset:write |
| POST | `/api/assets/search` | 搜索资产（标题+内容搜索） | 登录用户 |
| GET | `/api/assets/{asset_id}` | 获取单个资产详情 | 登录用户 |
| PUT | `/api/assets/{asset_id}` | 更新资产 | asset:write |
| DELETE | `/api/assets/{asset_id}` | 软删除资产 | asset:delete |
| POST | `/api/assets/{asset_id}/render` | 模板渲染（替换变量） | 登录用户 |

### Pydantic 请求模型

```python
class AssetCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    asset_type: str = Field("snippet", description="snippet, template, config, ...")
    language: Optional[str] = None
    format: Optional[str] = "text"
    visibility: str = Field("project", description="project, workspace, global")
    content: str = Field(..., min_length=1)
    variables: Optional[dict] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    extra_data: Optional[dict] = Field(default_factory=dict)

class AssetUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    asset_type: Optional[str] = None
    language: Optional[str] = None
    format: Optional[str] = None
    visibility: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[dict] = None
    tags: Optional[List[str]] = None
    extra_data: Optional[dict] = None

class AssetSearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    asset_type: Optional[str] = None
    language: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    top_k: int = Field(20, ge=1, le=100)

class AssetRenderRequest(BaseModel):
    variables: dict = Field(default_factory=dict)
```

## 4. 资产类型

模块支持 6 种资产类型，通过 `asset_type` 字段区分：

| 类型 | 标识符 | 说明 | 示例 |
|------|--------|------|------|
| **代码片段** | `snippet` | 可复用的代码段 | 二分查找函数、SQL 查询 |
| **模板** | `template` | 可渲染变量的模板 | 项目脚手架、API 模板 |
| **配置** | `config` | 环境配置 | Dockerfile、nginx.conf |
| **组件** | `component` | UI 或逻辑组件 | 按钮组件、日志组件 |
| **工具** | `utility` | 工具函数集合 | 日期工具、字符串工具 |
| **文档** | `documentation` | 代码文档 | API 文档注释、README |

前端统计面板对 snippet / template / config 三种类型做了特化展示：

```html
<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
    <div class="bg-gray-800 rounded-lg border p-4">
        <div class="text-sm text-gray-400">总资产</div>
        <div class="text-2xl font-bold text-white" x-text="stats.total || 0"></div>
    </div>
    <div class="bg-gray-800 rounded-lg border p-4">
        <div class="text-sm text-gray-400">代码片段</div>
        <div class="text-2xl font-bold text-blue-600" x-text="stats.by_type?.snippet || 0"></div>
    </div>
    <div class="bg-gray-800 rounded-lg border p-4">
        <div class="text-sm text-gray-400">模板</div>
        <div class="text-2xl font-bold text-purple-600" x-text="stats.by_type?.template || 0"></div>
    </div>
    <div class="bg-gray-800 rounded-lg border p-4">
        <div class="text-sm text-gray-400">配置</div>
        <div class="text-2xl font-bold text-green-600" x-text="stats.by_type?.config || 0"></div>
    </div>
</div>
```

## 5. 模板渲染

模板渲染是 Assets 模块的核心功能之一，通过 `POST /api/assets/{asset_id}/render` 端点实现。

### 渲染逻辑

```python
@router.post("/{asset_id}/render")
async def render_asset(asset_id: str, data: AssetRenderRequest, ...):
    # 1. 查找资产
    result = await db.execute(
        select(Asset).where(and_(Asset.id == asset_id, Asset.deleted_at.is_(None))))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # 2. 合并变量：资产预定义变量 + 请求传入变量
    template_vars = json.loads(asset.variables) if asset.variables else {}
    template_vars.update(data.variables)

    # 3. 执行模板替换
    rendered = asset.content
    for key, value in template_vars.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))

    return {"rendered_content": rendered, "variables_used": list(template_vars.keys())}
```

### 渲染示例

假设有一个名为 "Python API 模板" 的资产（`asset_type: "template"`）：

**资产 content：**
```python
import {{module_name}}

client = {{client_name}}.Client(
    base_url="{{base_url}}",
    api_key="{{api_key}}"
)

response = client.{{method}}("{{endpoint}}")
return response.json()
```

**资产预定义 variables：**
```json
{
    "module_name": "requests",
    "method": "get"
}
```

**调用 render 接口传入变量：**
```json
{
    "variables": {
        "client_name": "MyApi",
        "base_url": "https://api.example.com/v1",
        "api_key": "${API_KEY}",
        "endpoint": "users"
    }
}
```

**渲染结果：**
```python
import requests

client = MyApi.Client(
    base_url="https://api.example.com/v1",
    api_key="${API_KEY}"
)

response = client.get("users")
return response.json()
```

### 变量替换规则

1. 模板中使用 `{{variable_name}}` 格式标记变量
2. 变量来源合并：资产本身的 `variables` 字段 → 请求中的 `variables` 字段（后者覆盖前者）
3. 替换使用 `str.replace()`，支持字符串变量值
4. 未匹配的 `{{...}}` 保留原样

## 6. 搜索功能

Assets 模块提供了搜索端点 `POST /api/assets/search`：

```python
@router.post("/search")
async def search_assets(query: AssetSearchQuery, ...):
    search_pattern = f"%{query.query}%"

    conditions = [
        Asset.deleted_at.is_(None),
        or_(Asset.title.ilike(search_pattern), Asset.content.ilike(search_pattern))
    ]
    if query.asset_type:
        conditions.append(Asset.asset_type == query.asset_type)
    if query.language:
        conditions.append(Asset.language == query.language)

    sql_query = select(Asset).options(selectinload(Asset.tags)) \
        .where(and_(*conditions)).limit(query.top_k)
    result = await db.execute(sql_query)
    assets = result.scalars().all()

    # 搜索结果打分：标题匹配 0.5，内容匹配 0.3
    results = []
    for asset in assets:
        score = 0.5 if query.query.lower() in asset.title.lower() else 0.3
        results.append({"asset": asset.to_dict(), "score": score})

    return {"query": query.query, "total": len(results), "results": results}
```

搜索支持维度：
- **全文搜索** — 同时搜索标题和内容（ILIKE）
- **类型筛选** — 按 asset_type 过滤
- **语言筛选** — 按 programming language 过滤
- **相关性打分** — 标题匹配优先（0.5 vs 0.3）

## 7. 前端

前端模板位于 `apps/controller/app/web/templates/modules/assets/list_content.html`，使用 Alpine.js 管理状态。

### 核心 Alpine 组件：`assetsPage()`

```javascript
window.assetsPage = function assetsPage() {
    return {
        assets: [],              // 资产列表
        searchQuery: '',         // 搜索关键词
        filterType: '',          // 类型筛选
        loading: false,
        showCreateModal: false,
        showDetailModal: false,
        selectedAsset: null,
        stats: { total: 0, by_type: {}, by_language: {} },
        newAsset: {
            title: '', description: '', asset_type: 'snippet',
            language: '', content: ''
        },

        async init() { await this.loadAssets(); await this.loadStats(); },

        async loadAssets() {
            this.loading = true;
            try {
                const params = new URLSearchParams({ limit: '50' });
                if (this.searchQuery) params.set('search', this.searchQuery);
                if (this.filterType) params.set('asset_type', this.filterType);
                const res = await fetch(`/api/assets/list?${params}`);
                if (res.ok) { const data = await res.json(); this.assets = data.items || []; }
            } finally { this.loading = false; }
        },

        async loadStats() {
            const res = await fetch('/api/assets/stats');
            if (res.ok) this.stats = await res.json();
        },

        async createAsset() {
            const res = await fetch('/api/assets/create', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.newAsset)
            });
            if (res.ok) {
                this.showCreateModal = false;
                this.newAsset = { title: '', description: '', asset_type: 'snippet',
                                  language: '', content: '' };
                await this.loadAssets(); await this.loadStats();
            }
        },

        async viewAsset(asset) {
            const res = await fetch(`/api/assets/${asset.id}`);
            if (res.ok) { this.selectedAsset = await res.json(); this.showDetailModal = true; }
        },

        async deleteAsset(asset) {
            if (!asset || !confirm('确定删除此资产？')) return;
            const res = await fetch(`/api/assets/${asset.id}`, { method: 'DELETE' });
            if (res.ok) {
                this.showDetailModal = false;
                await this.loadAssets(); await this.loadStats();
            }
        }
    };
};
```

### 关键 UI 元素

| UI 元素 | 说明 |
|---------|------|
| **统计面板** | 显示总资产数、代码片段数、模板数、配置数 |
| **搜索框** | 输入即搜索（300ms 防抖） |
| **类型筛选** | 下拉选择全部/代码片段/模板/配置/组件/工具 |
| **资产卡片** | 显示标题、类型标签、语言、描述、标签列表 |
| **创建模态框** | 表单包含标题、类型、语言、内容（等宽字体）、描述 |
| **详情模态框** | 显示类型标签、语言、代码内容（pre 格式）、标签列表 |
| **删除按钮** | 确认后执行软删除 |