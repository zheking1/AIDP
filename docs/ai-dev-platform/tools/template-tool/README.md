# template-tool 文档索引

`template-tool` 是 AIDP 的脚手架与模板渲染工具，负责管理项目模板、模块模板、配置模板、代码片段模板，并根据变量生成可下载或可写入工作区的文件。它让 AI 不必每次从零创建项目结构，而是基于团队沉淀的标准模板生成工程。

## 必读文档

| 文档 | 内容 |
|---|---|
| [01-requirements.md](./01-requirements.md) | 需求、模板类型、使用场景、边界 |
| [02-architecture.md](./02-architecture.md) | 架构、模板上传、解析、渲染、验证流程 |
| [03-module-design.md](./03-module-design.md) | 模块职责、模板引擎、变量校验、输出策略 |
| [04-api-capabilities.md](./04-api-capabilities.md) | API、capability、schema、错误码 |
| [05-data-model.md](./05-data-model.md) | 模板包、版本、渲染任务、对象存储 |
| [06-development-plan.md](./06-development-plan.md) | 里程碑、开发任务、风险控制 |
| [07-testing-acceptance.md](./07-testing-acceptance.md) | 测试用例、验收标准、安全检查 |
| [AI_IMPLEMENTATION.md](./AI_IMPLEMENTATION.md) | AI 编码实现提示 |

## MVP Capability

| capability | 权限 | 说明 |
|---|---|---|
| `template.create` | `template:write` | 注册模板包 |
| `template.search` | `template:read` | 检索模板 |
| `template.validate` | `template:read` | 校验变量 |
| `template.preview` | `template:read` | 预览渲染结果 |
| `template.render` | `template:write` | 渲染模板并生成产物 |
| `template.publish` | `template:write` | 发布模板版本 |

## 完成定义

- 支持 Zip 模板包。
- 支持 `template.yaml` 元数据。
- 支持文件内容和文件路径变量替换。
- 支持变量类型、必填、默认值、枚举、正则校验。
- 支持 preview 不落盘、render 生成产物。
- 输出路径必须防止目录穿越。
