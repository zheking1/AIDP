# error-tool 测试与验收

## 1. 单元测试

| 模块 | 用例 |
|---|---|
| `SecretRedactor` | password、token、secret、Authorization 脱敏 |
| `TypeScriptCompileNormalizer` | 提取 TS 错误码、file、line、symbol |
| `PythonExceptionNormalizer` | 提取 exception class、file、line |
| `NodeRuntimeNormalizer` | 提取 root cause 和 stack_top |
| `TestFailureNormalizer` | 提取 test_name、expected、actual |
| `FingerprintService` | 绝对路径、时间戳变化不影响 fingerprint |
| `ErrorSearchRanker` | resolved 且高相似案例排序靠前 |

## 2. 集成测试

### 2.1 record

输入 TypeScript 编译失败日志。

期望：

- 返回 `error_type=typescript_compile`。
- `normalized.symbol` 不为空。
- raw log 被保存到配置路径。
- 敏感字段已脱敏。

### 2.2 search

准备两个项目的相似错误。

期望：

- 当前 project 只返回本项目错误。
- `include_workspace=true` 返回同 workspace 共享错误。
- 不返回其他 workspace 错误。

### 2.3 solution

步骤：

1. record error。
2. link solution。
3. resolve。
4. search 同类错误。

期望：

- search 结果包含 root_cause 和 fix_steps。
- resolved 案例比 open 案例排序更高。

## 3. 端到端验收

模拟流程：

1. `sandbox-tool` 构建或测试失败。
2. controller 调用 `error.record`。
3. controller 调用 `error.search`。
4. AI 根据解决方案修复。
5. `sandbox-tool` 重新构建或测试成功。
6. controller 调用 `error.link_solution` 和 `error.resolve`。

验收：

- 全流程 trace_id 可串联。
- 错误案例状态变为 resolved。
- 再次搜索能召回该方案。

## 4. 性能指标

| 操作 | 指标 |
|---|---:|
| record 1MB 日志 P95 | < 800ms |
| search 10 万案例 P95 | < 1000ms |
| normalizer 单条日志 | < 100ms |

## 5. 安全验收

- 响应不返回 raw log 全文。
- 日志脱敏后才落盘。
- 跨 workspace 查询返回空而不是暴露存在性。
- `error.export_pattern` 必须去除敏感路径和凭据。
