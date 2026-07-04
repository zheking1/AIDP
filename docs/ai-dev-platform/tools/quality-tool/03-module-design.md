# quality-tool 模块设计

## 1. 推荐代码结构

```text
quality-tool/
  tool.yaml
  openapi.yaml
  config.example.yaml
  migrations/
  src/
    server.ts
    api/
      health.routes.ts
      tool-protocol.routes.ts
      quality.routes.ts
      ruleset.routes.ts
    services/
      quality-check.service.ts
      quality-result.service.ts
      ruleset.service.ts
      sandbox.client.ts
    parser/
      log-parser.ts
      log-parser-registry.ts
      typescript-log-parser.ts
      python-log-parser.ts
      test-log-parser.ts
      node-stacktrace-parser.ts
      issue-normalizer.ts
    domain/
      models.ts
      enums.ts
    repository/
      quality-ruleset.repository.ts
      quality-result.repository.ts
```

## 2. 模块职责

### 2.1 QualityCheckService

流程：

1. 校验 workspace/project。
2. 加载 ruleset。
3. 按 checks 创建 sandbox job。
4. 获取 sandbox 日志。
5. 选择 parser。
6. 归一化 issue。
7. 保存结果。
8. 返回 passed 和 issues。

### 2.2 RulesetService

- 内置默认规则集。
- 支持项目自定义规则集。
- 校验 YAML/JSON 规则集 schema。
- 合并 global/workspace/project 规则。

### 2.3 SandboxClient

- 调用 `sandbox.run`、`sandbox.build.node`、`sandbox.test.python`。
- 透传 trace_id。
- 处理 sandbox 结构化错误。
- 拉取 stdout/stderr。

### 2.4 LogParserRegistry

根据 parser 名称或日志特征选择解析器：

- typescript。
- python。
- vitest。
- pytest。
- node_stacktrace。

### 2.5 IssueNormalizer

统一字段：

- severity。
- check_type。
- file。
- line。
- column。
- message。
- raw_message。
- suggested_fix。
- fingerprint。

## 3. Parser 接口

```ts
export interface LogParser {
  supports(context: ParseContext): boolean;
  parse(context: ParseContext): ParsedIssue[];
}
```

`ParseContext`：

- check_type。
- parser。
- raw_log。
- log_uri。
- project_root。
- metadata。

## 4. 规则集模型

```yaml
id: typescript-node-default
projectType: typescript-node
checks:
  - type: build
    command: ["pnpm", "test"]
    parser: typescript
    required: true
    timeoutSeconds: 600
```

规则：

- required check 失败则 `passed=false`。
- 非 required check 失败可返回 warning。
- command 必须交给 sandbox 执行。

## 5. Issue Severity

```text
blocker
error
warning
info
```

映射：

- 编译失败：error。
- 测试失败：error。
- Lint 严重规则：warning 或 error，取决于 ruleset。
- 格式问题：warning。

## 6. 错误码

| 错误码 | 场景 |
|---|---|
| `RULESET_NOT_FOUND` | 规则集不存在 |
| `RULESET_INVALID` | 规则集 schema 错误 |
| `PARSER_NOT_FOUND` | 找不到解析器 |
| `PARSE_FAILED` | 日志解析失败 |
| `SANDBOX_UNAVAILABLE` | sandbox-tool 不可用 |
| `QUALITY_CHECK_FAILED` | 检查执行失败 |
