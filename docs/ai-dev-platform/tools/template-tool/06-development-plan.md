# template-tool 开发计划

## 1. 里程碑

| 里程碑 | 周期 | 交付 |
|---|---:|---|
| M1 工具骨架 | 1 天 | tool.yaml、基础 API |
| M2 模板注册 | 2 天 | Zip 校验、template.yaml 解析、元数据入库 |
| M3 变量校验 | 1 天 | schema 校验、默认值、错误提示 |
| M4 预览和渲染 | 2-3 天 | render engine、preview、artifact zip |
| M5 安全和测试 | 1-2 天 | 路径安全、集成测试、示例 |

## 2. AI 编码任务

1. 实现工具协议和 capability 路由。
2. 实现数据库迁移和实体。
3. 实现 Zip 安全解压与 `template.yaml` 解析。
4. 实现变量 schema 校验。
5. 实现文件路径和文本内容渲染。
6. 实现 preview。
7. 实现 render job 和产物存储。
8. 补齐 API 测试和 examples。

## 3. 风险控制

| 风险 | 控制 |
|---|---|
| Zip Slip | 解压前规范化路径并校验根目录 |
| 覆盖用户文件 | 默认 artifact_zip，不直接写 workspace |
| 模板执行恶意脚本 | MVP 不执行任何模板脚本 |
| secret 泄露 | secret 变量不进入日志和 preview |

## 4. 交付清单

- `tool.yaml`
- `openapi.yaml`
- `config.example.yaml`
- 示例模板 Zip
- `examples/create.json`
- `examples/preview.json`
- `examples/render.json`
- 单元测试和集成测试
