# quality-tool 测试与验收

## 1. 测试目标

测试必须证明：

- 规则集可校验。
- TypeScript/Python/test 日志可解析。
- issue 字段完整。
- `quality.check` 可联动 sandbox-tool。
- 结果可保存和查询。

## 2. 单元测试

### 2.1 TypeScriptLogParser

用例：

- `TS2339 Property does not exist`。
- `TS2307 Cannot find module`。
- ESLint error。
- Vitest failure。

期望：

- file_path 正确。
- line 正确。
- message 可读。

### 2.2 PythonLogParser

用例：

- Python traceback。
- pytest assertion failure。
- ruff error。
- mypy type error。

### 2.3 IssueNormalizer

用例：

- severity 映射。
- fingerprint 稳定。
- 重复 issue 去重。
- suggested_fix 生成。

### 2.4 RulesetService

用例：

- 合法 ruleset 通过。
- 缺少 command 失败。
- 不支持 parser 失败。

## 3. API 测试

- `POST /api/quality/parse-build-log` 返回 issues。
- `POST /api/quality/check` sandbox 不可用时返回结构化错误。
- `GET /api/quality/results/{id}` 权限隔离生效。
- `POST /api/quality/rulesets/validate` 可校验 YAML/JSON。

## 4. 集成测试

### 4.1 解析 TypeScript 构建错误

步骤：

1. 提供 TypeScript 错误日志。
2. 调用 parse_build_log。

期望：

- 至少返回 1 个 issue。
- issue 包含 severity、file、line、message。

### 4.2 quality.check 调用 sandbox mock

步骤：

1. 配置 sandbox mock 返回失败日志。
2. 调用 quality.check。

期望：

- passed=false。
- 保存 quality_result。
- 保存 issue。

## 5. 端到端测试

步骤：

1. 准备有 TypeScript 类型错误的示例项目。
2. 调用 `quality.check`。
3. quality-tool 调用 sandbox-tool。
4. 解析日志。
5. 查询结果。

期望：

- 返回 file/line/message。
- raw_log_object_key 存在。
- issue 可作为 AI 修复输入。

## 6. 性能验收

| 指标 | 目标 |
|---|---:|
| 10MB 日志解析 | 不 OOM |
| 质量结果查询 P95 | < 300ms |
| 1000 issues 归一化 | < 2s |

## 7. 最终验收清单

- [ ] `tool.yaml` 合法。
- [ ] `openapi.yaml` 覆盖全部 API。
- [ ] `/tool/capabilities` 包含 `quality.check`。
- [ ] TypeScript 错误可解析。
- [ ] Python 错误可解析。
- [ ] issue 字段完整。
- [ ] quality.check 可调用 sandbox-tool。
- [ ] 结果可查询。
- [ ] controller managed 联调通过。
