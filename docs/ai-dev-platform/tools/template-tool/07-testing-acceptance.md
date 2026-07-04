# template-tool 测试与验收

## 1. 单元测试

| 模块 | 用例 |
|---|---|
| `TemplatePackageService` | 缺少 template.yaml、非法路径、超大小 |
| `VariableSchemaService` | required、default、enum、regex、secret |
| `RenderEngine` | 内容替换、路径替换、二进制复制 |
| `OutputSafetyService` | 阻止 `../`、绝对路径、覆盖策略 |

## 2. 集成测试

- 注册合法 Zip，创建 template 和 version。
- 非法 packageName 返回字段级错误。
- preview 返回文件树且不生成正式产物。
- render 生成 Zip，路径和内容变量被替换。

## 3. 安全验收

- 包含 `../evil.txt` 的 Zip 被拒绝。
- 绝对路径文件被拒绝。
- secret 变量不出现在日志和 preview。
- `overwrite=false` 时不覆盖已有文件。

## 4. 性能验收

| 场景 | 指标 |
|---|---:|
| 100 文件模板 preview | < 1s |
| 1000 文件模板 render | < 3s |
| 100MB 模板包注册 | < 10s |

## 5. 端到端验收

controller 检索模板，AI 选择模板并传入变量，controller 调用 preview，AI 检查文件树，controller 调用 render，可选交给 sandbox-tool 编译。全流程必须可通过 `/tool/invoke` 完成。
