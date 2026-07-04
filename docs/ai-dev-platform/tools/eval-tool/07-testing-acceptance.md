# eval-tool 测试与验收

## 1. 单元测试

- JSON schema scorer。
- contains_text scorer。
- regex scorer。
- latency scorer。
- report 汇总指标。

## 2. 集成测试

用 mock HTTP/tool target：

1. 创建 dataset。
2. 添加 3 个 case。
3. 执行 run。
4. 生成 report。

期望：

- 每个 case 有 result。
- 成功率计算正确。
- 失败原因可读。

## 3. 验收指标

- 100 个 case 串行执行稳定。
- target 失败不影响其他 case。
- report 包含失败列表和指标汇总。
- `/tool/invoke` 能调用全部 MVP capability。
