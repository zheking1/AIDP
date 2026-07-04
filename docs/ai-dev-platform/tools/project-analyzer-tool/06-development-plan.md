# project-analyzer-tool 开发计划

## 1. 里程碑

| 里程碑 | 周期 | 交付 |
|---|---:|---|
| M1 工具骨架 | 1 天 | 协议、capability、配置 |
| M2 文件扫描 | 2 天 | 安全路径、ignore、文件索引 |
| M3 构建和框架识别 | 2 天 | Node/Python/Fastify/Flutter 分析 |
| M4 符号和 API 摘要 | 2-3 天 | symbol、route、config、SQL |
| M5 摘要和导出 | 1-2 天 | markdown summary、memory export |
| M6 测试 | 1-2 天 | 示例项目和集成测试 |

## 2. AI 编码任务

1. 实现工具协议。
2. 实现数据库迁移。
3. 实现 WorkspaceReader 和 IgnoreRuleService。
4. 实现文件索引和增量 hash。
5. 实现 Node/Python/Dart/Config 分析器。
6. 实现 Fastify route 和 TypeScript symbol 粗解析。
7. 实现 SummaryService。
8. 实现 find_symbol/find_files/dependency_graph。
9. 实现 memory-tool client。

## 3. 风险控制

| 风险 | 控制 |
|---|---|
| 扫描过慢 | 默认 ignore、文件大小限制、增量缓存 |
| 解析器脆弱 | 单文件失败不影响整体扫描 |
| 泄露源码 | 默认只保存摘要和符号，不保存完整源码 |
| 路径越界 | canonical path 校验 |

## 4. 交付物

- `tool.yaml`
- `openapi.yaml`
- `config.example.yaml`
- 示例 TypeScript/Fastify 项目扫描结果
- 示例 Flutter 项目扫描结果
- 单元测试和集成测试
