# quality-tool 需求说明

## 1. 背景

AI 编码闭环不能只停留在“生成代码”和“编译运行”，还需要把构建失败、测试失败、Lint 失败转换成结构化、可定位、可修复的问题列表。`quality-tool` 负责这一层质量网关：它读取规则集，调用 `sandbox-tool` 执行检查，解析日志，输出标准化 issue。

## 2. 产品目标

- 支持项目规则集管理。
- 支持 build、test、lint、format、custom check。
- 支持 TypeScript/Node 构建日志解析。
- 支持 pytest/Vitest 等测试失败解析。
- 支持 issue 归一化。
- 支持质量结果持久化。
- 支持 controller managed 和 standalone 模式。

## 3. 非目标

MVP 不做：

- 不直接在宿主机执行命令。
- 不替代 `sandbox-tool`。
- 不实现所有语言的 Lint 解析。
- 不做复杂代码静态分析引擎。
- 不自动修改代码，只输出修复反馈。

## 4. 检查类型

| check_type | 说明 | MVP |
|---|---|---|
| `build` | 编译和打包 | 是 |
| `test` | 单元测试和集成测试 | 是 |
| `lint` | 静态规则检查 | 是，基础 |
| `format` | 格式检查 | 增强 |
| `security` | 安全扫描 | 增强 |
| `sql` | SQL 风险检查 | 增强 |
| `custom` | 自定义命令 | 增强 |

## 5. 使用场景

### 5.1 TypeScript 构建错误反馈

AI 修改 TypeScript/Fastify 代码后，调用 `quality.check`。工具通过 sandbox 执行 `pnpm test` 或 `pnpm build`，解析 `TSxxxx`、ESLint、Vitest 等错误，返回 file/line/message。

### 5.2 测试失败反馈

解析 pytest/Vitest 输出，把失败测试文件、用例名、断言错误、堆栈位置转换为 issue。

### 5.3 Lint 失败反馈

解析 ESLint、ruff、mypy 等输出，归一化为 issue，供 AI 按文件行号修复。

### 5.4 仅解析已有日志

用户或其它工具已经有构建日志时，可直接调用 `quality.parse_build_log`，不需要重新执行 sandbox。

## 6. 功能需求

### 6.1 规则集管理

规则集必须包含：

- ruleset_id。
- project_type。
- checks。
- command。
- required。
- parser。
- timeout。
- sandbox profile。

示例：

```yaml
id: typescript-node-default
projectType: typescript-node
checks:
  - type: build
    command: ["pnpm", "test"]
    parser: typescript
    required: true
```

### 6.2 质量检查

流程：

```text
读取 ruleset
  -> 创建 sandbox job
  -> 等待结果
  -> 获取日志
  -> 解析日志
  -> 归一化 issue
  -> 保存 quality_result
  -> 返回结果
```

### 6.3 日志解析

MVP 必须支持：

- TypeScript compilation failure。
- Vitest test failure。
- Python exception。
- pytest failure。

增强支持：

- eslint。
- ruff。
- mypy。
- SQL explain 风险。

### 6.4 Issue 输出

issue 必须包含：

- severity。
- check_type。
- rule_id。
- file。
- line。
- column。
- message。
- raw_message。
- suggested_fix。
- source。

## 7. 权限和隔离

- 所有结果必须带 `workspace_id`。
- 项目结果必须带 `project_id`。
- 不能读取其它项目 sandbox job。
- 规则集可见性支持 global/workspace/project。

## 8. 非功能需求

- 解析 10MB 日志不应 OOM。
- 质量结果查询 P95 小于 300ms。
- 解析器失败不能导致原始日志丢失。
- 所有调用必须携带 trace_id。

## 9. MVP 验收范围

- 工具协议接口可用。
- 规则集 CRUD 或内置规则集可用。
- `quality.check` 可调用 sandbox-tool。
- 可解析 TypeScript 构建错误。
- 可解析 Python 测试错误。
- 可保存 quality_result。
- issue 可直接作为 AI 修复输入。
