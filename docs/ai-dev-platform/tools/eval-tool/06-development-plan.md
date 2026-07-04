# eval-tool 开发计划

## 1. 里程碑

| 阶段 | 交付 |
|---|---|
| M1 | 工具协议、dataset/case API |
| M2 | eval runner 和 target client |
| M3 | scorer registry 和基础评分器 |
| M4 | report 和 run compare |
| M5 | 测试和示例 |

## 2. AI 编码任务

1. 实现数据模型和迁移。
2. 实现 dataset/case CRUD。
3. 实现 tool_invoke target。
4. 实现 http target。
5. 实现 schema、contains、regex、latency scorer。
6. 实现 eval.run。
7. 实现 markdown report。

## 3. 风险控制

- 限制并发和 timeout。
- 输出过大时截断或对象存储。
- target 调用失败必须记录，而不是中断整个 run。
