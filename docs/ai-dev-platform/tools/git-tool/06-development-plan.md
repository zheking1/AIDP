# git-tool 开发计划

## 1. 里程碑

| 阶段 | 交付 |
|---|---|
| M1 | 工具协议、仓库登记、路径校验 |
| M2 | status、diff_summary |
| M3 | commit_history、show_commit、file_history |
| M4 | 可选 create_commit |
| M5 | 测试、示例、OpenAPI |

## 2. AI 编码任务

1. 实现 `RepoPathGuard`。
2. 实现安全 Git 命令执行器。
3. 实现 status parser。
4. 实现 diff parser。
5. 实现 history 查询。
6. 实现写操作开关和 create_commit。
7. 补齐集成测试。

## 3. 风险控制

- 不支持原始命令执行。
- 不支持破坏性命令。
- diff 超大时截断。
- 写操作默认关闭。
