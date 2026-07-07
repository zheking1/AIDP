# Evolution Engine 重构计划 - 两级进化系统

## 1. 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Evolution Architecture                    │
├─────────────────────────┬───────────────────────────────────┤
│      项目级进化          │          系统级进化                │
│    (Project Level)      │       (System Level)              │
├─────────────────────────┼───────────────────────────────────┤
│ • 用户私有的经验积累     │ • 全平台共享的最佳实践             │
│ • 项目特定的模式         │ • 经过审核的标准模板               │
│ • 个人工作流优化         │ • 跨项目的通用规则                 │
├─────────────────────────┴───────────────────────────────────┤
│                    管理员审核流程                            │
│  项目级优秀进化 ──提案──▶ 管理员审核 ──通过──▶ 系统级进化    │
└─────────────────────────────────────────────────────────────┘
```

## 2. 核心功能

### 2.1 版本管理
```
Evolution v1.2.3
├── 创建者: user@example.com
├── 来源项目: Project A
├── 审核状态: pending → approved → system
├── 影响范围: 项目级 → 系统级
├── 变更内容:
│   ├── 新增: error_handling pattern
│   ├── 修改: api_route template
│   └── 删除: outdated_config
├── 版本历史:
│   ├── v1.2.2 (回退点)
│   ├── v1.2.1
│   └── v1.0.0
└── 回退操作: [回退到此版本]
```

### 2.2 管理员审核工作流
```python
# 状态机
pending_review → admin_reviewing → approved/rejected → published
                    ↓
               needs_modification
```

### 2.3 多级回退机制
1. **全局回退**（管理员）- 系统级进化有严重 bug
2. **项目回退**（项目所有者）- 系统级进化不适合本项目
3. **个人回退**（用户）- 个人记忆/模板升级后不好用

## 3. 数据模型

```python
class EvolutionVersion(Base):
    __tablename__ = "evolution_versions"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    version = Column(String(20), nullable=False)  # semver
    level = Column(String(20))  # project / system
    source_project_id = Column(UUID, ForeignKey("projects.id"))
    created_by = Column(UUID, ForeignKey("users.id"))
    
    # 审核
    review_status = Column(String(20), default='pending')
    reviewed_by = Column(UUID, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    review_comment = Column(Text)
    
    # 变更内容
    changes = Column(JSONB)  # {added: [], modified: [], deleted: []}
    
    # 影响范围
    affected_tools = Column(JSONB)
    affected_projects = Column(JSONB)
    
    # 回退
    is_rollback_point = Column(Boolean, default=False)
    rollback_to_version = Column(String(20))
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

## 4. 开发计划（2 周）

### Week 1: 核心重构
- Day 1-2: 数据库迁移
- Day 3-4: 版本管理系统
- Day 5: 审核工作流

### Week 2: 高级功能
- Day 1-2: 回退机制
- Day 3: 影响分析
- Day 4: 管理员界面
- Day 5: 测试与优化

## 5. Web UI 界面

### 5.1 管理员控制台
```
┌────────────────────────────────────────┐
│         Evolution Management           │
├────────────────────────────────────────┤
│  待审核 (12)                           │
│  ├── Pattern: FastAPI Error Handler    │
│  │   来自: Project X | 影响: 5个项目   │
│  │   [查看详情] [批准] [拒绝] [修改]   │
│  │                                      │
│  └── Template: Docker Compose V3       │
│      来自: Project Y | 影响: 12个项目  │
│      [查看详情] [批准] [拒绝] [修改]   │
│                                         │
│  系统级进化 (156)                       │
│  ├── v2.1.0 (当前)                     │
│  ├── v2.0.3                            │
│  └── v1.9.8                            │
│                                         │
│  [发布新版本] [全局回退]                 │
└────────────────────────────────────────┘
```

---

**详细文档开发中补充**
