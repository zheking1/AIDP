# Memory Tool - Overview

## Purpose

Memory Tool 是 AIDP 平台的记忆管理组件，提供分层记忆存储、语义搜索、矛盾检测和记忆整合能力。

## Configuration (`app/config.py`)

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `APP_NAME` | `memory-tool` | 应用名称 |
| `APP_VERSION` | `0.1.0` | 版本号 |
| `HOST` / `PORT` | `0.0.0.0:18085` | 服务监听地址 |
| `DATABASE_URL` | `""` | 数据库连接串 |
| `DATABASE_ECHO` | `false` | SQL 日志开关 |
| `SECRET_KEY` | `""` | 密钥 |
| `MEMORY_DEFAULT_LIMIT` | `50` | 默认查询限制 |
| `MEMORY_MAX_LIMIT` | `200` | 最大查询限制 |

## Core Concepts

### 记忆层级 (Memory Tiers)

| Tier | 说明 |
|------|------|
| `episodic` | 事件记忆 — 特定时刻的交互记录 |
| `semantic` | 语义记忆 — 结构化的知识事实 |
| `procedural` | 程序记忆 — 操作流程和方法论 |

### 记忆类别 (Categories)

| Category | 说明 |
|----------|------|
| `architecture` | 架构决策 |
| `decision` | 技术选型 |
| `pattern` | 设计模式 |
| `issue` | 问题记录 |
| `bug` | Bug 修复经验 |
| `other` | 其他 |

### AI 记忆生命周期

```mermaid
AI生成 → pending → 人工审核 → approved/rejected
                              ↓
                        合并相似记忆 (consolidate)
```

## Embedding

嵌入生成通过 **Controller** 协调：
1. 查询 `GET {CONTROLLER_URL}/api/models/for-task/embedding` 获取模型配置
2. 默认回退: `BAAI/bge-m3`（1024 维，截断至 384 维适配存储）
3. 调用远程嵌入 API 生成向量
4. 结果缓存于进程内 `_embedding_model_cache`

## Capabilities

| # | Capability | 说明 | 权限 |
|---|------------|------|------|
| 1 | `memory.create` | 创建记忆条目 | `memory:write` |
| 2 | `memory.search` | 搜索记忆条目 | `memory:read` |
| 3 | `memory.search.hybrid` | BM25 + TFIDF + Vector 混合搜索 | `memory:read` |
| 4 | `memory.contradiction.check` | 创建前检查矛盾 | `memory:write` |
| 5 | `memory.consolidate` | 整合相似记忆 | `memory:write` |
| 6 | `memory.context` | 获取上下文包 | `memory:read` |
| 7 | `memory.update` | 更新记忆条目 | `memory:write` |
| 8 | `memory.delete` | 删除记忆条目 | `memory:delete` |