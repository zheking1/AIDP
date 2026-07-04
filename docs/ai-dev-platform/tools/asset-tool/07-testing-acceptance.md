# asset-tool 测试和验收标准

## 1. 单元测试

### 1.1 Repository 测试

- 创建资产 → 数据库有记录。
- 查询资产 → 返回正确数据。
- 更新资产 → 数据库更新。
- 删除资产 → 软删除标记。
- 关键词检索 → 返回匹配结果。
- scope 过滤 → 不同项目数据隔离。

### 1.2 Service 测试

- 创建资产 → 调用 repository。
- 权限检查 → 不同 visibility 返回正确结果。
- trace_id 透传 → 日志包含 trace_id。

### 1.3 Template Engine 测试

- 简单变量替换 → 正确渲染。
- 缺少变量 → 返回错误。
- 无变量 → 原样返回。

## 2. API 测试

### 2.1 工具协议测试

- `GET /health` → 返回 UP。
- `GET /tool/manifest` → 返回 tool.yaml 内容。
- `GET /tool/capabilities` → 返回 capability 列表。
- `POST /tool/invoke` → 调用 capability。

### 2.2 资产 API 测试

- `POST /api/assets` → 创建资产。
- `GET /api/assets/{id}` → 查询资产。
- `PUT /api/assets/{id}` → 更新资产。
- `DELETE /api/assets/{id}` → 删除资产。
- `GET /api/assets` → 列出资产。

### 2.3 检索测试

- 关键词检索 → 返回匹配结果。
- 类型过滤 → 只返回指定类型。
- 语言过滤 → 只返回指定语言。
- 标签过滤 → 只返回指定标签。
- scope 过滤 → 不同项目数据隔离。

### 2.4 模板渲染测试

- 渲染模板 → 返回渲染结果。
- 渲染不存在的模板 → 返回 404。
- 渲染无权限的模板 → 返回 403。

## 3. 集成测试

### 3.1 Controller 调用测试

- controller 安装工具 → 健康检查通过。
- controller 调用 `/tool/invoke` → 返回结果。
- controller 调用不存在的 capability → 返回错误。

### 3.2 跨项目隔离测试

- 项目 A 创建资产 → 项目 B 不能检索。
- 工作区公共资产 → 同一工作区可检索。
- 全局资产 → 所有工作区可检索。

## 4. 性能验收

- 1000 条资产，P95 检索延迟小于 500ms。
- `top_k <= 20` 时响应体默认小于 128KB。

## 5. 安全验收

- 跨项目访问返回 FORBIDDEN。
- 错误响应不泄露敏感信息。
- 日志不包含完整资产内容。
