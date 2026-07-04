# sandbox-tool AI 实施包

## 1. 开发输入

开发前必须阅读：

- `docs/ai-dev-platform/common/tool-contract.md`
- `docs/ai-dev-platform/common/engineering-standards.md`
- `docs/ai-dev-platform/tools/sandbox-tool/README.md`
- `docs/ai-dev-platform/tools/sandbox-tool/01-requirements.md`
- `docs/ai-dev-platform/tools/sandbox-tool/02-architecture.md`
- `docs/ai-dev-platform/tools/sandbox-tool/03-module-design.md`
- `docs/ai-dev-platform/tools/sandbox-tool/04-api-capabilities.md`
- `docs/ai-dev-platform/tools/sandbox-tool/05-data-model.md`
- `docs/ai-dev-platform/tools/sandbox-tool/06-development-plan.md`
- `docs/ai-dev-platform/tools/sandbox-tool/07-testing-acceptance.md`

## 2. 目标交付

实现一个可独立运行、可被 controller 安装的安全执行沙箱工具。

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
```

## 3. 实施重点

- controller 不能直接执行命令。
- 所有任务必须经过策略校验。
- 默认 `network=none`。
- 镜像必须在白名单。
- 禁止 privileged、host network、任意 hostPath。
- 超时必须强制终止。
- 任务结束必须清理容器和临时目录。

## 4. 推荐任务顺序

1. 工程骨架和工具协议。
2. job/log/artifact 数据模型。
3. 策略服务。
4. DockerExecutionService。
5. 日志和产物采集。
6. shell/python runner。
7. node/python project runner。
8. sql validate runner。
9. 安全测试和 controller 联调。

## 5. Definition of Done

- 工具可 standalone 启动。
- controller 可安装。
- 默认无网络。
- Python hello world 可执行。
- Node/TypeScript 示例项目可测试。
- 超时强杀。
- 容器和临时目录清理。
- 日志和产物可查询。
