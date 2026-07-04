# aidp-controller 测试与验收

## 1. 单元测试

| 模块 | 测试点 |
|---|---|
| config | 环境变量、YAML、默认值 |
| ToolManifestValidator | tool.yaml 合法/非法 |
| ToolCapabilitySyncService | capability 同步和禁用 |
| CapabilityRouter | 权限、schema、超时、错误包装 |
| ApprovalPolicy | 高风险动作识别 |
| SecretRedactor | 日志和响应脱敏 |
| WorkflowRunner | step 顺序、失败、等待审批 |

## 2. 集成测试

- 启动 controller + PostgreSQL。
- 安装 mock-tool。
- 同步 mock capability。
- 调用 `/api/tools/invoke`。
- 停用工具后调用失败。
- 创建 approval 并 approve。
- 创建 secret 后列表不返回明文。

## 3. 端到端测试

流程：

1. 初始化默认 workspace/project。
2. 安装 mock-tool、memory-tool、knowledge-tool。
3. 创建 coding-basic workflow run。
4. workflow 调用多个 capability。
5. 高风险 step 进入 approval。
6. approve 后继续执行。
7. 最终生成 run summary。

## 4. 性能验收

| 操作 | 指标 |
|---|---:|
| tool invoke controller 额外开销 P95 | < 100ms |
| tool list P95 | < 300ms |
| workflow step 调度 P95 | < 200ms |

## 5. 安全验收

- 跨 project 调用被拒绝。
- 未授权 capability 被拒绝。
- secret value 不进入日志。
- approval required 的动作不能绕过。
- disabled tool 不能被 MCP 或 API 调用。

## 6. 完成标准

- 所有 API 有 OpenAPI。
- 所有错误符合统一错误模型。
- 所有调用有 trace_id。
- mock-tool 可完整安装、调用、卸载。
- CLI 可完成最小操作。
