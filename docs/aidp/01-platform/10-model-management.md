# 统一模型管理

## 概述

AIDP 通过 Controller 统一管理所有 LLM 和 Embedding 模型配置。各工具不独立配置模型，而是通过 MCP 从 Controller 获取模型配置。这确保了平台内模型配置的一致性。

**源码**: `apps/controller/app/services/model_service.py`
**模型表**: `app/db/auth_models.py:395` (`AidpModel`)
**MCP 工具**: `manage_models` (in `app/mcp/server.py:167`)

## 数据模型 (AidpModel)

```python
# app/db/auth_models.py:395
class AidpModel(Base):
    __tablename__ = "aidp_models"
    id: int (PK, autoincrement)
    name: str            # 显示名称，如 "DeepSeek Chat"
    provider: str        # 提供商: "OpenAI" / "DeepSeek" / "Local"
    model_name: str      # 实际模型 ID: "deepseek-chat", "gpt-4"
    api_base: str        # API Base URL, null 则使用默认
    api_key: str         # API Key (加密存储)
    task_types: JSON     # 分配的任务类型: ["chat", "embedding", "code"]
    status: str          # "active" (default)
    priority: int        # 优先级，越高越优先 (default 0)
    max_tokens: int      # 最大输出 tokens (default 4096)
    temperature: float   # 0=精确, 1=创意 (default 0.7)
    created_at / updated_at: datetime
```

## 默认模型配置

系统启动时自动初始化 4 个默认模型 (`ModelService.seed_defaults()`):

| 名称 | 提供商 | model_name | api_base | task_types |
|------|--------|------------|----------|------------|
| DeepSeek Chat | DeepSeek | `deepseek-chat` | `https://api.deepseek.com/v1` | `["chat"]` |
| DeepSeek Coder | DeepSeek | `deepseek-coder` | `https://api.deepseek.com/v1` | `["chat", "code"]` |
| text-embedding-3-small | OpenAI | `text-embedding-3-small` | `https://api.openai.com/v1` | `["embedding"]` |
| all-MiniLM-L6-v2 | Local | `all-MiniLM-L6-v2` | null | `["embedding"]` |

种子数据只在 `aidp_models` 表为空时写入，不会重复创建。

## ModelService API

```python
class ModelService:

    # 初始化默认模型（仅当表为空时执行）
    seed_defaults()

    # 列出所有模型（按 priority DESC, id 排序）
    list_models() -> List[Dict]

    # 按任务类型获取模型列表（仅 status="active"，按 priority 排序）
    get_by_task(task_type: str) -> List[Dict]

    # 获取某任务类型的最佳模型（优先级最高、status active）
    get_best_for_task(task_type: str) -> Optional[Dict]

    # 单个模型 CRUD
    get_model(model_id: int) -> Optional[Dict]
    create_model(data: dict) -> Dict
    update_model(model_id: int, data: dict) -> Optional[Dict]
    delete_model(model_id: int) -> bool

    # 内部序列化
    _to_dict(model) -> Dict
```

## get_best_for_task 逻辑

```python
# app/services/model_service.py:84
@staticmethod
async def get_best_for_task(task_type: str) -> Optional[Dict]:
    models = await ModelService.get_by_task(task_type)
    return models[0] if models else None
```

**选择逻辑**:
1. 过滤 `status == "active"` 的模型
2. 过滤 `task_type in model.task_types` 的模型
3. 按 `priority DESC` 排序
4. 返回第一个

**结果**: 返回 `{"model_name", "api_base", "api_key", "provider", "task_types", "max_tokens", "temperature"}`

## 工具如何使用模型配置

工具通过 Controller 的 MCP 或 API 获取模型配置（不直接连接模型服务）:

### MCP 方式

```python
# MCP Client 调用:
invoke_tool_mcp("controller", "manage_models", {
    "action": "get_best",
    "task_type": "chat"
})

# 返回:
{
    "model": {
        "model_name": "deepseek-chat",
        "provider": "DeepSeek",
        "api_base": "https://api.deepseek.com/v1",
        "task_types": ["chat"],
        ...
    }
}
```

### API 方式

```python
# GET /api/models?task_type=chat
# 返回: [{"id": 1, "name": "DeepSeek Chat", "model_name": "deepseek-chat", ...}]
```

### 公开查询接口

```python
# app/services/model_service.py:156
async def get_model_for_task(task_type: str) -> Optional[Dict]:
    return await ModelService.get_best_for_task(task_type)

# app/services/model_service.py:161
async def get_all_models_for_task(task_type: str) -> List[Dict]:
    return await ModelService.get_by_task(task_type)
```

## MCP 模型管理 (manage_models)

`manage_models` MCP 工具提供完整的模型 CRUD:

```python
@mcp.tool()
async def manage_models(
    action: str,       # "list" | "get" | "get_best" | "create" | "update" | "delete"
    task_type: str,    # "chat" | "embedding" | "code"
    model_id: int,
    name: str,
    provider: str,
    model_name: str,
    api_base: str,
    task_types: str,   # JSON array
    priority: int,
)
```

| Action | 说明 | 必需参数 |
|--------|------|---------|
| `list` | 列出所有模型 | task_type (可选过滤) |
| `get_best` | 获取最佳模型 | task_type |
| `get` | 获取单个模型 | model_id |
| `create` | 创建模型 | name, provider, model_name, task_types |
| `update` | 更新模型 | model_id + 要更新的字段 |
| `delete` | 删除模型 | model_id |

## 使用场景

### 查看所有可用模型

```
manage_models(action="list")
```

### 按任务查看

```
manage_models(action="list", task_type="chat")
manage_models(action="list", task_type="embedding")
```

### 获取聊天模型

```
manage_models(action="get_best", task_type="chat")
# 返回优先级最高的 chat 模型
```

### 创建新模型

```
manage_models(
    action="create",
    name="GPT-4",
    provider="OpenAI",
    model_name="gpt-4",
    task_types='["chat"]'
)
```

## 架构优势

1. **集中配置**: 所有工具的模型配置统一在 Controller 中管理
2. **优先级控制**: 通过 priority 字段实现多模型自动切换
3. **动态切换**: 更新 `aidp_models` 表即可影响所有工具，无需重启
4. **统一 API Key 管理**: API Key 集中存储，避免在各工具中分散配置
5. **任务类型路由**: 不同任务自动选择最适合的模型 (chat/code/embedding)