# AIDP 统一 Web UI 平台开发计划

## 1. 项目概述

### 1.1 目标
将 AIDP 现有的 7 个独立工具 Web UI 整合为统一的配置驱动平台，实现：
- ✅ 单点登录、统一布局
- ✅ 项目级数据隔离
- ✅ 配置驱动菜单系统
- ✅ RBAC 权限控制
- ✅ 7个工具完整集成

### 1.2 当前状态
| 组件 | 状态 | 备注 |
|------|------|------|
| 统一登录 | ✅ 已完成 | Controller 已实现 |
| Workspace 框架 | ✅ 已完成 | Tab 标签页系统 |
| 用户/角色管理 | ✅ 已完成 | Admin 功能 |
| Knowledge Tool | ⚠️ iframe 嵌入 | 需真正集成 |
| Memory Tool | ❌ 未集成 | 独立运行 |
| Asset Tool | ❌ 未集成 | 独立运行 |
| Sandbox Tool | ❌ 未集成 | 独立运行 |
| Quality Tool | ❌ 未集成 | 独立运行 |
| SkillRouter | ❌ 未集成 | 独立运行 |
| Evolution Engine | ❌ 未集成 | 独立运行 |

**当前完成度：约 20%**

### 1.3 参考文档
- `docs/web/01-architecture-design.md` - 架构设计
- `docs/web/02-menu-configuration.md` - 菜单配置
- `docs/web/03-permission-system.md` - 权限系统
- `docs/web/04-implementation-plan.md` - 实施计划

---

## 2. 开发阶段

### 📅 Phase 1: 基础架构 (Week 1)
**目标**：建立配置驱动的基础框架

#### Day 1: 配置系统搭建
**上午 (4h)**:
- [ ] 创建 `app/config/menu.yaml` 菜单配置
  - 8个菜单组定义
  - 权限绑定
  - 动态参数支持 (`{project_id}`)
- [ ] 创建 `app/config/permissions.yaml` 权限配置
  - 所有工具的 CRUD 权限
  - 三层权限架构

**下午 (4h)**:
- [ ] 实现 `app/core/config_loader.py`
  - YAML 加载和验证
  - 热重载支持
  - 配置缓存
- [ ] 编写配置验证单元测试

**验收标准**:
```python
# 测试代码
from app.core.config_loader import ConfigLoader

loader = ConfigLoader()
menu = loader.load_menu()
assert len(menu['sidebar']) == 8
assert 'knowledge' in [g['group'] for g in menu['sidebar']]
```

#### Day 2: 菜单引擎实现
**上午 (4h)**:
- [ ] 实现 `app/core/menu.py` 菜单引擎
  - `MenuEngine` 类
  - `get_sidebar_menu(user, project_id)` 方法
  - 权限过滤逻辑
  - 动态路由生成

**下午 (4h)**:
- [ ] 实现 `app/core/context.py` 项目上下文
  - `ProjectContext` 类
  - 上下文依赖注入
  - 项目验证中间件
- [ ] 菜单渲染 API 端点
  - `GET /api/menu` - 获取当前用户菜单

**验收标准**:
```python
# 测试代码
engine = MenuEngine()
menu = engine.get_sidebar_menu(user, project_id="123")
assert all('route' in item for group in menu for item in group['items'])
```

#### Day 3: 权限系统实现
**上午 (4h)**:
- [ ] 实现 `app/core/permissions.py`
  - `PermissionChecker` 类
  - 装饰器 `require_permissions()`
  - 三层权限检查逻辑

**下午 (4h)**:
- [ ] 权限检查中间件
  - 自动注入到所有路由
  - 权限缓存
- [ ] 编写权限测试用例
  - 管理员权限
  - 编辑者权限
  - 查看者权限

**验收标准**:
```python
# 测试代码
@router.get("/test")
async def test_route(
    user=require_permissions("knowledge:read")
):
    return {"ok": True}
```

#### Day 4: 模块注册机制
**上午 (4h)**:
- [ ] 创建 `app/modules/__init__.py`
  - 模块基类 `Module`
  - 注册装饰器 `@register_module`
  - 模块自动发现

**下午 (4h)**:
- [ ] 动态路由加载
  - 从模块自动注册路由
  - 前缀自动添加
- [ ] 创建示例模块结构

**验收标准**:
```python
# 测试代码
from app.modules import register_module, Module

@register_module(name='test')
class TestModule(Module):
    pass

# 验证模块已注册
assert 'test' in get_registered_modules()
```

#### Day 5: 统一布局模板
**上午 (4h)**:
- [ ] 重构 `templates/base.html`
  - 动态侧边栏渲染
  - 项目切换器
  - 用户信息展示

**下午 (4h)**:
- [ ] 创建共享组件
  - `components/sidebar.html`
  - `components/header.html`
  - `components/project_switcher.html`
- [ ] 静态资源整理

**验收标准**:
- 侧边栏根据配置动态渲染
- 项目切换器正常工作
- 移动端适配

---

### 📅 Phase 2: 项目系统 (Week 2)
**目标**：实现项目管理和数据隔离

#### Day 1-2: 数据库迁移
**任务**:
- [ ] 创建迁移脚本 `migrations/001_create_projects.sql`
  - `app_projects` 表
  - `app_project_members` 表
  - `app_project_settings` 表
  
- [ ] 修改现有表
  - `kt_document` 添加 `project_id` 字段
  - `memories` 添加 `project_id` 字段
  - `skills` 添加 `scope` 字段（global/personal/project）
  
- [ ] 创建 Alembic 迁移
  ```bash
  alembic revision -m "add project isolation"
  alembic upgrade head
  ```

**验收标准**:
- 所有迁移成功执行
- 数据完整性约束正确
- 回滚脚本可正常工作

#### Day 3-4: 项目 API 实现
**任务**:
- [ ] `GET /api/projects` - 项目列表
- [ ] `POST /api/projects` - 创建项目
- [ ] `GET /api/projects/{id}` - 项目详情
- [ ] `PUT /api/projects/{id}` - 更新项目
- [ ] `DELETE /api/projects/{id}` - 删除项目
- [ ] `POST /api/projects/{id}/members` - 添加成员
- [ ] `DELETE /api/projects/{id}/members/{user_id}` - 移除成员
- [ ] `PUT /api/projects/{id}/members/{user_id}/role` - 修改角色

**验收标准**:
```python
# API 测试
response = client.get("/api/projects")
assert response.status_code == 200
assert "items" in response.json()
```

#### Day 5: 项目前端页面
**任务**:
- [ ] 项目列表页 `/projects`
  - 卡片式布局
  - 创建项目按钮
  - 搜索过滤
  
- [ ] 项目创建弹窗
  - 项目名称
  - 描述
  - 技术栈标签
  - 可见性设置

**验收标准**:
- 可创建新项目
- 可查看项目列表
- 可进入项目

---

### 📅 Phase 3: 工具集成 - Knowledge Tool (Week 3)
**目标**：完成 Knowledge Tool 模块迁移

#### Day 1: 模块结构搭建
**任务**:
- [ ] 创建 `app/modules/knowledge/` 目录结构
  ```
  knowledge/
  ├── __init__.py      # 模块注册
  ├── routes.py        # API 路由
  ├── models.py        # 数据模型
  ├── services.py      # 业务逻辑
  └── templates/       # 页面模板
      ├── list.html
      ├── detail.html
      └── search.html
  ```

- [ ] 注册 Knowledge 模块
  ```python
  @register_module(name='knowledge')
  class KnowledgeModule(Module):
      name = "knowledge"
      description = "文档知识库管理"
  ```

#### Day 2-3: API 路由迁移
**任务**:
- [ ] 迁移现有 API
  - `GET /api/projects/{id}/knowledge/documents`
  - `POST /api/projects/{id}/knowledge/documents`
  - `GET /api/projects/{id}/knowledge/documents/{doc_id}`
  - `PUT /api/projects/{id}/knowledge/documents/{doc_id}`
  - `DELETE /api/projects/{id}/knowledge/documents/{doc_id}`
  - `POST /api/projects/{id}/knowledge/upload`
  - `GET /api/projects/{id}/knowledge/search`

- [ ] 添加项目上下文过滤
  ```python
  async def get_documents(
      project_id: int,
      context=Depends(get_project_context)
  ):
      if context.current_project.id != project_id:
          raise HTTPException(403, "Access denied")
      return await query_documents(project_id=project_id)
  ```

#### Day 4-5: 前端模板迁移
**任务**:
- [ ] 迁移文档列表页
  - 项目上下文显示
  - 权限控制（只显示有权限的操作按钮）
  
- [ ] 迁移文档详情页
  - 预览功能
  - 编辑功能
  
- [ ] 迁移搜索页
  - 语义搜索
  - 过滤器

**验收标准**:
- 所有原有功能正常工作
- 数据按项目隔离
- 权限检查生效

---

### 📅 Phase 4: 工具集成 - Memory & Skills (Week 4)
**目标**：完成 Memory Tool 和 Skills 模块

#### Day 1-2: Memory Tool 集成
**任务**:
- [ ] 创建 `app/modules/memory/` 模块
- [ ] 迁移 API 路由
  - `/api/projects/{id}/memory/memories`
  - `/api/projects/{id}/memory/graph`
  - `/api/projects/{id}/memory/search`
- [ ] 迁移前端页面
  - 记忆列表
  - 记忆图谱（D3.js）
  - 向量搜索

#### Day 3-4: Skills 模块统一
**任务**:
- [ ] 创建 `app/modules/skills/` 模块
- [ ] 实现三层技能 API
  - `GET /skills/global` (管理员)
  - `GET /skills/personal` (当前用户)
  - `GET /skills/project/{project_id}` (项目技能)
- [ ] 迁移前端页面
  - 全局技能管理（管理员）
  - 个人技能管理
  - 项目技能管理

#### Day 5: Asset & Sandbox & Quality 集成
**任务**:
- [ ] Asset Tool 集成（基础功能）
- [ ] Sandbox Tool 集成
- [ ] Quality Tool 集成

---

### 📅 Phase 5: 功能完善 (Week 5)
**目标**：通知中心、审计日志、性能优化

#### Day 1-2: 通知中心
**任务**:
- [ ] 创建 `app/modules/notifications/`
- [ ] 实现通知模型
- [ ] WebSocket 实时推送
- [ ] 通知列表页面
- [ ] 未读计数 API

#### Day 3: 审计日志
**任务**:
- [ ] 审计日志中间件
- [ ] 日志查询 API
- [ ] 管理员审计日志页面

#### Day 4-5: 性能优化
**任务**:
- [ ] 菜单配置缓存
- [ ] API 响应缓存
- [ ] 数据库查询优化
- [ ] 前端资源压缩

---

## 3. 任务依赖图

```
Week 1: 基础架构
├── Day 1: 配置系统 [BLOCKS: Day 2, Day 3, Day 4]
├── Day 2: 菜单引擎 [BLOCKS: Day 5]
├── Day 3: 权限系统 [BLOCKS: Week 2, Week 3, Week 4]
├── Day 4: 模块注册 [BLOCKS: Week 3, Week 4]
└── Day 5: 统一布局 [BLOCKS: Week 2]

Week 2: 项目系统
├── Day 1-2: 数据库 [BLOCKS: Day 3-4]
├── Day 3-4: 项目 API [BLOCKS: Day 5, Week 3]
└── Day 5: 项目页面 [BLOCKS: Week 3]

Week 3: Knowledge Tool
├── Day 1: 模块结构 [BLOCKS: Day 2-3]
├── Day 2-3: API 迁移 [BLOCKS: Day 4-5]
└── Day 4-5: 前端迁移

Week 4: Memory & Skills
├── Day 1-2: Memory Tool
├── Day 3-4: Skills 模块
└── Day 5: 其他工具

Week 5: 功能完善
├── Day 1-2: 通知中心
├── Day 3: 审计日志
└── Day 4-5: 性能优化
```

---

## 4. 每日检查清单

### 开始工作前
- [ ] 查看昨日完成状态
- [ ] 确认依赖任务已完成
- [ ] 拉取最新代码
- [ ] 创建功能分支

### 开发过程中
- [ ] 编写单元测试
- [ ] 遵循代码规范
- [ ] 定期提交代码
- [ ] 更新文档

### 完成任务后
- [ ] 通过所有单元测试
- [ ] 代码审查（自我）
- [ ] 更新进度文档
- [ ] 提交 Pull Request

---

## 5. 验收标准

### 功能验收
- [ ] 菜单配置驱动，修改 YAML 立即生效
- [ ] 项目上下文正确传递，数据隔离生效
- [ ] 权限检查正常工作，未授权访问被拒绝
- [ ] 7个工具全部集成完成
- [ ] 单点登录正常工作

### 性能验收
- [ ] 页面加载时间 < 1s
- [ ] API 响应时间 < 300ms (95% 请求)
- [ ] 菜单渲染时间 < 100ms
- [ ] 支持 100+ 并发用户

### 代码验收
- [ ] 单元测试覆盖率 > 80%
- [ ] 无严重代码异味
- [ ] 文档完整
- [ ] 通过安全扫描

---

## 6. 风险预案

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 数据迁移失败 | 中 | 高 | 提前备份，分批次迁移，保留回滚方案 |
| 权限系统复杂 | 中 | 中 | 先实现基础 RBAC，后期扩展细粒度权限 |
| 性能瓶颈 | 低 | 中 | 提前规划缓存策略，使用 Redis |
| 工具 API 不兼容 | 低 | 高 | 创建适配层，保持向后兼容 |
| 开发延期 | 中 | 中 | 预留缓冲时间，优先完成核心功能 |

---

## 7. 资源需求

### 开发环境
- [ ] PostgreSQL 13+ (带 pgvector)
- [ ] Redis 6+
- [ ] Python 3.11+
- [ ] Node.js 18+ (前端构建)

### 测试数据
- [ ] 3-5 个测试项目
- [ ] 每项目 50+ 文档
- [ ] 多角色测试账号

---

## 8. 里程碑

| 里程碑 | 日期 | 交付物 |
|--------|------|--------|
| M1: 基础架构完成 | Week 1 结束 | 配置系统、菜单引擎、权限系统 |
| M2: 项目系统完成 | Week 2 结束 | 项目管理、数据隔离 |
| M3: Knowledge 集成 | Week 3 结束 | Knowledge Tool 完全集成 |
| M4: 全部工具集成 | Week 4 结束 | 7个工具全部集成 |
| M5: 生产就绪 | Week 5 结束 | 通知中心、审计日志、性能优化 |

---

## 9. 附录

### 9.1 分支命名规范
```
feature/web-ui-menu-config      # 新功能
feature/web-ui-project-system   # 项目系统
feature/web-ui-knowledge        # Knowledge 集成
feature/web-ui-memory           # Memory 集成
fix/web-ui-permission-bug       # Bug 修复
```

### 9.2 提交信息规范
```
feat: add menu configuration system
feat: implement permission checker
test: add unit tests for menu engine
docs: update architecture design
fix: resolve project context injection issue
```

### 9.3 关键文件清单
```
apps/controller/
├── app/
│   ├── config/
│   │   ├── menu.yaml              # 菜单配置
│   │   └── permissions.yaml       # 权限配置
│   ├── core/
│   │   ├── config_loader.py       # 配置加载
│   │   ├── menu.py                # 菜单引擎
│   │   ├── permissions.py         # 权限系统
│   │   └── context.py             # 项目上下文
│   ├── modules/                   # 工具模块
│   │   ├── knowledge/
│   │   ├── memory/
│   │   ├── skills/
│   │   ├── assets/
│   │   └── sandbox/
│   └── web/templates/
│       └── base.html              # 统一布局
```

---

**计划版本**: 1.0  
**制定日期**: 2026-07-09  
**预计工期**: 5 周  
**文档状态**: 待开始执行
