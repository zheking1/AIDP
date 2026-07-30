# AIDP 代码清理计划

## 目标
统一所有工具的 LLM 配置来源、消除内部 HTTP 调用、移除硬编码值。

---

## 1. LLM 配置统一到 Controller ModelService

所有工具通过 `from app.services.model_service import get_model_for_task` 获取模型配置。

### 1.1 context_optimizer/services/llm_client.py
- 移除 HTTP 调用 `localhost:8883/api/models/for-task/chat`
- 改为 `get_model_for_task("chat")` 直接读数据库

### 1.2 evolution_engine/services/llm_client.py
- 同 1.1

### 1.3 knowledge_tool/services/two_step_ingest.py
- 移除 `os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")` 硬编码
- 移除 `os.getenv("LLM_API_KEY", "sk-xxx")` 硬编码
- 改为 `get_model_for_task("chat")` 和 `get_model_for_task("embedding")`

### 1.4 code_index/services/embedding_service.py
- 移除 HTTP 调用 `CONTROLLER_URL/api/models/for-task/embedding`
- 改为 `get_model_for_task("embedding")` 直接读数据库

### 1.5 各工具 config.py 默认值清理
- `skill_router/config.py`: `llm_api_key` / `embedding_api_key` 默认值改为空字符串
- `context_optimizer/config.py`: `LLM_API_KEY` 默认值改为空字符串
- `evolution_engine/config.py`: `LLM_API_KEY` 默认值改为空字符串

---

## 2. 内部 HTTP 调用改本地调用

### 2.1 context_optimizer/services/staged_retriever.py
- 移除 `TOOL_ENDPOINTS` 硬编码端口
- 移除 HTTP 调用，改为本地 import 各工具服务函数
- 涉及: memory.search, knowledge.search, code.search, asset.search, sandbox.execute, quality.check

---

## 3. 硬编码端口清理

### 3.1 tool_invoker.py:206
- skill-router 默认端口 `localhost:8788` 改为 `localhost:8883`
- 或改为 None（仅 HTTP fallback 时使用，本地优先）

---

## 验证
每个文件改完后运行 `python -m py_compile` 验证语法。
