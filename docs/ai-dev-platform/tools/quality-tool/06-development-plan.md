# quality-tool 开发计划

## 1. 总体策略

`quality-tool` 应先实现日志解析和 issue 归一化，再接入 sandbox 执行完整检查。这样即使 sandbox 未准备好，也可以先验证 TypeScript/Python 日志解析能力。

## 2. 里程碑

| 里程碑 | 目标 | 交付物 |
|---|---|---|
| M0 | 工程骨架 | TypeScript + Fastify、配置、统一错误 |
| M1 | 工具协议 | manifest、capabilities、invoke |
| M2 | 数据模型 | ruleset/result/issue 表 |
| M3 | 日志解析 | TypeScript、Python、测试日志解析 |
| M4 | 规则集 | 内置规则集和校验 |
| M5 | sandbox 联动 | 调用 sandbox-tool 执行检查 |
| M6 | 结果闭环 | 保存结果、OpenAPI、examples、联调 |

## 3. 开发任务

1. 创建工程骨架和统一响应。
2. 实现工具协议接口。
3. 创建 Drizzle/SQL migration。
4. 实现 RulesetService。
5. 实现 TypeScriptLogParser。
6. 实现 PythonLogParser。
7. 实现 TestLogParser。
8. 实现 IssueNormalizer。
9. 实现 parse_build_log API。
10. 实现 SandboxClient。
11. 实现 quality.check。
12. 保存 quality_result 和 issue。
13. 生成 OpenAPI、examples、Dockerfile。

## 4. 关键验收点

- TypeScript `TSxxxx` 能解析出 file/line/message。
- Python traceback 能解析出 file/line/message。
- pytest/Vitest 失败能解析测试文件和用例名。
- `quality.check` 能调用 sandbox mock。
- 结果可查询。

## 5. 风险控制

| 风险 | 控制方式 |
|---|---|
| 日志格式多变 | parser 独立模块，先覆盖高频格式 |
| sandbox 不可用 | 支持纯日志解析模式 |
| issue 重复 | fingerprint 去重 |
| 日志过大 | 限制大小，流式处理 |
| AI 难以修复 | suggested_fix 使用规则模板生成 |
