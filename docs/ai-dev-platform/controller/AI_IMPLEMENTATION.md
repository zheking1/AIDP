# aidp-controller AI 实施指南

## 1. 默认技术栈

必须使用：

- TypeScript
- Node.js LTS
- Fastify
- PostgreSQL
- Drizzle ORM 或轻量 SQL migration
- Vitest
- pino

不要默认使用重型企业框架、Nacos、Kubernetes。

## 2. 推荐目录

```text
apps/controller/
  src/
    config/
    db/
    modules/
      workspace/
      auth/
      tool-manager/
      capability-router/
      mcp-adapter/
      workflow-runner/
      approval-center/
      secrets-manager/
      audit-log/
    shared/
    server.ts
  tests/
  openapi.yaml
  config.example.yaml
```

## 3. 第一阶段实现顺序

1. Fastify 基础服务。
2. `/health`。
3. 数据库连接和 migration。
4. tool.yaml schema。
5. tool install。
6. `/api/tools`。
7. `/api/tools/invoke`。
8. mock-tool 联调。

## 4. 编码注意事项

- 所有输入用 schema 校验。
- 所有外部工具调用必须设置 timeout。
- 所有日志包含 trace_id。
- secret value 不得打印。
- 不允许直接拼接 SQL。
- 不允许把工具 base_url 暴露给普通 MCP 客户端。

## 5. 最小验收命令

```text
npm install
npm run test
npm run dev
aidp tool install ./tools/mock-tool
aidp invoke mock.echo '{"text":"hello"}'
```
