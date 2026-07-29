# 权限系统设计

## 1. 三层权限架构

```
┌─────────────────────────────────────────────────────────────┐
│                        权限架构                              │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 项目级 (Project)                                   │
│  ├── 项目成员角色 (admin/editor/viewer)                      │
│  └── 项目资源权限 (knowledge:read, memory:write 等)         │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 用户级 (User)                                      │
│  ├── 个人资源 (skills:personal)                              │
│  └── 用户偏好设置                                            │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: 全局级 (Global)                                    │
│  ├── 系统管理员 (admin)                                      │
│  └── 全局资源 (skills:global)                                │
└─────────────────────────────────────────────────────────────┘
```

## 2. 角色定义

### 2.1 系统角色

| 角色 | 描述 | 权限 |
|------|------|------|
| **admin** | 系统管理员 | 所有权限 |
| **user** | 普通用户 | 创建项目、管理自己的资源 |
| **guest** | 访客 | 只读访问公开内容 |

### 2.2 项目角色

| 角色 | 描述 | 权限概览 |
|------|------|----------|
| **admin** | 项目管理员 | 管理成员、项目设置、所有内容操作 |
| **editor** | 编辑者 | 创建、编辑、删除内容 |
| **viewer** | 查看者 | 只读访问 |

## 3. 权限粒度

### 3.1 权限命名规范

```
{resource}:{action}:{scope}

Examples:
- knowledge:read              → 读取知识库
- knowledge:write             → 写入知识库
- knowledge:delete            → 删除知识库内容
- knowledge:admin             → 管理知识库设置
- memory:read:project         → 读取项目记忆
- skills:read:global          → 读取全局技能
- skills:write:personal       → 写入个人技能
- project:admin               → 项目管理权限
```

### 3.2 完整权限列表

```yaml
# permissions.yaml

permissions:
  # ====================
  # 项目权限
  # ====================
  project:
    view:
      description: "查看项目"
      default_roles: [admin, editor, viewer]
    
    admin:
      description: "管理项目"
      default_roles: [admin]
      includes: [project:view]
  
  # ====================
  # 知识库权限
  # ====================
  knowledge:
    read:
      description: "读取文档"
      default_roles: [admin, editor, viewer]
    
    write:
      description: "创建/编辑文档"
      default_roles: [admin, editor]
    
    delete:
      description: "删除文档"
      default_roles: [admin, editor]
    
    admin:
      description: "管理知识库设置"
      default_roles: [admin]
  
  # ====================
  # 记忆权限
  # ====================
  memory:
    read:
      description: "读取记忆"
      default_roles: [admin, editor, viewer]
    
    write:
      description: "创建/编辑记忆"
      default_roles: [admin, editor]
    
    delete:
      description: "删除记忆"
      default_roles: [admin, editor]
    
    admin:
      description: "管理记忆设置"
      default_roles: [admin]
  
  # ====================
  # 代码资产权限
  # ====================
  asset:
    read:
      description: "读取资产"
      default_roles: [admin, editor, viewer]
    
    write:
      description: "创建/编辑资产"
      default_roles: [admin, editor]
    
    delete:
      description: "删除资产"
      default_roles: [admin]
  
  # ====================
  # 技能权限
  # ====================
  skills:
    read:
      global:
        description: "读取全局技能"
        default_roles: [admin]  # 只有管理员可以管理全局技能
      
      personal:
        description: "读取个人技能"
        default_roles: [admin, editor, viewer]
      
      project:
        description: "读取项目技能"
        default_roles: [admin, editor, viewer]
    
    write:
      personal:
        description: "写入个人技能"
        default_roles: [admin, editor, viewer]
      
      project:
        description: "写入项目技能"
        default_roles: [admin, editor]
    
    admin:
      global:
        description: "管理全局技能"
        default_roles: [admin]
      
      project:
        description: "管理项目技能"
        default_roles: [admin]
  
  # ====================
  # 开发工具权限
  # ====================
  sandbox:
    execute:
      description: "执行沙箱代码"
      default_roles: [admin, editor]
  
  quality:
    check:
      description: "运行质量检查"
      default_roles: [admin, editor, viewer]
  
  # ====================
  # 管理员权限
  # ====================
  admin:
    users:
      description: "管理用户"
      default_roles: [admin]
    
    projects:
      description: "管理所有项目"
      default_roles: [admin]
    
    skills:
      description: "管理全局技能"
      default_roles: [admin]
    
    audit:
      description: "查看审计日志"
      default_roles: [admin]
    
    settings:
      description: "系统设置"
      default_roles: [admin]
```

## 4. 权限检查实现

### 4.1 装饰器实现

```python
# app/core/permissions.py

from functools import wraps
from fastapi import HTTPException, Request
from typing import List, Optional, Any

class PermissionChecker:
    def __init__(self, permissions: List[str]):
        self.permissions = permissions
    
    async def __call__(self, request: Request) -> Any:
        user = request.state.user
        # 检查系统管理员
        if user.role in ['admin', 'super_admin']:
            return user
        
        # 检查具体权限
        for permission in self.permissions:
            if not await self._check_permission(user, permission, None):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission}"
                )
        
        return user
    
    async def _check_permission(
        self, 
        user, 
        permission: str, 
        project_id: Optional[str] = None
    ) -> bool:
        # 解析权限
        parts = permission.split(":")
        resource = parts[0]
        action = parts[1] if len(parts) > 1 else "read"
        scope = parts[2] if len(parts) > 2 else None
        
        # 系统级权限检查
        if resource == "admin":
            return user.role in ['admin', 'super_admin']
        
        # 项目级权限检查（通过 project_id 参数传入）
        if project_id:
            # 实际检查由各模块的 route 层实现（如 _project_filter()）
            return True
        
        # 个人资源检查
        if scope == "personal":
            return True  # 用户可以管理自己的资源
        
        return False
    
    def _check_role_permission(self, role: str, resource: str, action: str) -> bool:
        # 管理员拥有所有权限
        if role == "admin":
            return True
        
        # 编辑者权限
        if role == "editor":
            if action in ["read", "write"]:
                return True
            if resource in ["knowledge", "memory"] and action == "delete":
                return True
            return False
        
        # 查看者权限
        if role == "viewer":
            return action == "read"
        
        return False

# 快捷函数
def require_permissions(*permissions: str):
    return Depends(PermissionChecker(list(permissions)))
```

### 4.2 使用示例

```python
# app/modules/knowledge/routes.py

from fastapi import APIRouter, Depends
from app.core.permissions import require_permissions

router = APIRouter()

@router.get("/projects/{project_id}/knowledge/documents")
async def list_documents(
    project_id: str,
    user=require_permissions("knowledge:read")
):
    """列出文档 - 需要 knowledge:read 权限"""
    pass

@router.post("/projects/{project_id}/knowledge/documents")
async def create_document(
    project_id: str,
    user=require_permissions("knowledge:write")
):
    """创建文档 - 需要 knowledge:write 权限"""
    pass

@router.delete("/projects/{project_id}/knowledge/documents/{doc_id}")
async def delete_document(
    project_id: str,
    doc_id: str,
    user=require_permissions("knowledge:delete")
):
    """删除文档 - 需要 knowledge:delete 权限"""
    pass

# 项目设置 - 仅管理员
@router.get("/projects/{project_id}/settings/instructions")
async def get_instructions(
    project_id: str,
    user=require_permissions("project:admin")
):
    """获取 Instructions - 需要 project:admin 权限"""
    pass
```

## 5. 前端权限控制

### 5.1 权限上下文

```javascript
// 前端权限检查
const usePermission = () => {
  const { user } = useAuth();
  const { currentProject } = useProject();
  
  const checkPermission = (permission) => {
    // 系统管理员
    if (user.role === 'admin') return true;
    
    // 解析权限
    const [resource, action, scope] = permission.split(':');
    
    // 项目级权限
    if (currentProject) {
      const member = currentProject.members.find(m => m.userId === user.id);
      if (!member) return false;
      
      return checkRolePermission(member.role, resource, action);
    }
    
    return false;
  };
  
  return { checkPermission };
};
```

### 5.2 权限组件

```jsx
// PermissionGuard 组件
const PermissionGuard = ({ 
  permissions, 
  children, 
  fallback = null 
}) => {
  const { checkPermission } = usePermission();
  
  const hasPermission = permissions.every(p => checkPermission(p));
  
  return hasPermission ? children : fallback;
};

// 使用示例
<PermissionGuard permissions={["knowledge:write"]}>
  <Button>创建文档</Button>
</PermissionGuard>
```

## 6. 数据库表

```sql
-- 用户表
CREATE TABLE app_users (
    id VARCHAR(128) PRIMARY KEY,
    email VARCHAR(256) UNIQUE NOT NULL,
    name VARCHAR(128),
    avatar_url VARCHAR(512),
    role VARCHAR(32) DEFAULT 'user',  -- admin, user, guest
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- 项目表
CREATE TABLE app_projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    description TEXT,
    owner_id VARCHAR(128) REFERENCES app_users(id),
    visibility VARCHAR(32) DEFAULT 'private',  -- private, internal, public
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 项目成员表
CREATE TABLE app_project_members (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES app_projects(id) ON DELETE CASCADE,
    user_id VARCHAR(128) REFERENCES app_users(id) ON DELETE CASCADE,
    role VARCHAR(32) DEFAULT 'editor',  -- admin, editor, viewer
    invited_by VARCHAR(128),
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, user_id)
);

-- 审计日志表
CREATE TABLE app_audit_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(128),
    project_id INTEGER,
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64),
    resource_id VARCHAR(128),
    details JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_audit_logs_user ON app_audit_logs(user_id);
CREATE INDEX idx_audit_logs_project ON app_audit_logs(project_id);
CREATE INDEX idx_audit_logs_created ON app_audit_logs(created_at);
```

## 7. 权限矩阵速查

| 功能 | ADMIN | EDITOR | VIEWER |
|------|:-----:|:------:|:------:|
| **项目** ||||
| 查看项目 | ✅ | ✅ | ✅ |
| 编辑项目信息 | ✅ | ❌ | ❌ |
| 管理成员 | ✅ | ❌ | ❌ |
| 删除项目 | ✅ | ❌ | ❌ |
| **知识库** ||||
| 查看文档 | ✅ | ✅ | ✅ |
| 创建文档 | ✅ | ✅ | ❌ |
| 编辑文档 | ✅ | ✅ | ❌ |
| 删除文档 | ✅ | ✅ | ❌ |
| 配置知识库 | ✅ | ❌ | ❌ |
| **记忆** ||||
| 查看记忆 | ✅ | ✅ | ✅ |
| 创建记忆 | ✅ | ✅ | ❌ |
| 编辑记忆 | ✅ | ✅ | ❌ |
| 删除记忆 | ✅ | ✅ | ❌ |
| **技能** ||||
| 查看项目技能 | ✅ | ✅ | ✅ |
| 创建项目技能 | ✅ | ✅ | ❌ |
| 使用全局技能 | ✅ | ✅ | ✅ |
| 管理全局技能 | ✅(sys) | ❌ | ❌ |
| **开发工具** ||||
| 执行沙箱 | ✅ | ✅ | ❌ |
| 运行质量检查 | ✅ | ✅ | ✅ |
