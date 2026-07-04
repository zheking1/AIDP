# quality-tool AI 实施包

## 1. 开发输入

开发前必须阅读：

- `docs/ai-dev-platform/common/tool-contract.md`
- `docs/ai-dev-platform/common/engineering-standards.md`
- `docs/ai-dev-platform/tools/sandbox-tool/README.md`
- `docs/ai-dev-platform/tools/quality-tool/README.md`
- `docs/ai-dev-platform/tools/quality-tool/01-requirements.md`
- `docs/ai-dev-platform/tools/quality-tool/02-architecture.md`
- `docs/ai-dev-platform/tools/quality-tool/03-module-design.md`
- `docs/ai-dev-platform/tools/quality-tool/04-api-capabilities.md`
- `docs/ai-dev-platform/tools/quality-tool/05-data-model.md`
- `docs/ai-dev-platform/tools/quality-tool/06-development-plan.md`
- `docs/ai-dev-platform/tools/quality-tool/07-testing-acceptance.md`

## 2. 目标交付

实现一个可独立运行、可被 controller 安装的质量校验工具。

必须交付：

```text
tool.yaml
openapi.yaml
config.example.yaml
Dockerfile
migrations/
src/
tests/
examples/
rulesets/
```

## 3. 实施重点

- 不直接执行宿主机命令。
- 完整检查必须通过 sandbox-tool。
- parser 和 normalizer 保持可单测。
- issue 必须包含 file/line/message。
- 原始日志必须保留引用。

## 4. Definition of Done

- 工具可 standalone 启动。
- controller 可安装。
- 可解析 TypeScript/Python 错误。
- `quality.check` 可调用 sandbox-tool。
- issue 可直接作为 AI 修复输入。
