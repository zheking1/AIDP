# Assets Module (代码资产管理)

## 概述

代码资产管理模块提供可复用的代码片段、模板、配置、组件、工具函数和文档的存储和检索功能。支持标签系统、变量模板渲染。

**源码**: `apps/controller/app/modules/assets/`
**路由前缀**: `/api/assets`
**模型表**: `aidp_assets`, `aidp_asset_tags`

## 数据模型

### Asset (代码资产)

**表**: `aidp_assets`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| project_id | Integer FK | 关联项目 |
| user_id | String(100) | 创建者 |
| title | String(200) | 标题 (可索引) |
| description | Text | 描述 |
| asset_type | String(50) | 类型: `"snippet"` / `"template"` / `"config"` / `"component"` / `"utility"` / `"documentation"` |
| language | String(50) | 语言 (可索引) |
| format | String(50) | 格式，默认 `"text"` |
| visibility | String(20) | `"project"` / `"workspace"` / `"global"` |
| content | Text | 资产内容 |
| variables | Text (JSON) | 模板变量定义 |
| extra_data | Text (JSON) | 扩展数据 |
| created_by | String(100) | 创建者 ID |
| updated_by | String(100) | 更新者 ID |
| access_count | Integer | 访问计数 |
| deleted_at | DateTime | 软删除时间 |

### AssetTag (资产标签)

**表**: `aidp_asset_tags`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| asset_id | String(36) FK | 关联资产 (CASCADE) |
| tag | String(100) | 标签名 (可索引) |

## API 端点

### 资产 CRUD

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/assets/list` | GET | - | 列出资产 (project_id, asset_type, language, search) |
| `/api/assets/create` | POST | `asset:write` | 创建资产 (含 tags) |
| `/api/assets/search` | POST | - | 搜索资产 (title + content 全文匹配) |
| `/api/assets/stats` | GET | - | 统计 (total, by_type, by_language) |
| `/api/assets/{asset_id}` | GET | - | 获取资产 (access_count++) |
| `/api/assets/{asset_id}` | PUT | `asset:write` | 更新资产 (含 tags 全量替换) |
| `/api/assets/{asset_id}` | DELETE | `asset:delete` | 软删除资产 |

### 模板渲染

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/assets/{asset_id}/render` | POST | - | 渲染资产模板 (`{{key}}` 替换) |

## 资产类型

| asset_type | 说明 |
|------------|------|
| `snippet` | 代码片段 |
| `template` | 模板 |
| `config` | 配置文件 |
| `component` | 组件 |
| `utility` | 工具函数 |
| `documentation` | 文档 |

## 可见性

| visibility | 说明 |
|------------|------|
| `project` | 项目内可见 |
| `workspace` | 工作区内可见 |
| `global` | 全局可见 |

## 模板渲染

当 asset 包含 `{{variable}}` 占位符时，`render` 端点支持变量替换:

```
POST /api/assets/{asset_id}/render
{"variables": {"name": "MyApp", "port": "8883"}}

content: "app = {{name}}(port={{port}})"
→ rendered: "app = MyApp(port=8883)"
```

渲染优先级:
1. asset 自身定义的 `variables` 中查找 key
2. 请求参数中的 `variables` 覆盖

## Tags 更新逻辑

更新 Asset 时，tags 采用全量替换:
1. 删除该 asset 的所有现有 AssetTag
2. 根据新 tags 列表重新插入

## 数据关系图

```
aidp_projects (1) ----< aidp_assets (N)
aidp_assets (1) ----< aidp_asset_tags (N, CASCADE)
```