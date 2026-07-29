# importer-tool

对话式内容导入工具，通过自然语言交互将文档、知识、技能、规则导入 AIDP 平台。

## 解决的问题

AIDP 已有 Knowledge、Skills、Rules、Quality 等独立模块，但缺少一个**对话式编排层**来：

- 理解用户意图（这是知识还是规则？）
- 自动分类和打标签
- 运行质量检查
- 确认后写入对应模块

## 使用方式

通过 MCP 协议调用：

```text
/tool/invoke  importer.import
/tool/invoke  importer.import_batch
/tool/invoke  importer.classify
/tool/invoke  importer.preview
```

### 示例对话

```
用户: 帮我把这份架构文档导入知识库
Agent → importer.import(source={type:"text", content:"# 架构总览..."})
       → 返回分类建议 + 质量检查结果
       → 用户确认后持久化
       → "已导入知识文档「架构总览」"
```

## 文档

| 文档 | 说明 |
|------|------|
| [01-requirements.md](./01-requirements.md) | 需求说明 |
| [02-architecture.md](./02-architecture.md) | 架构设计 |
| [03-module-design.md](./03-module-design.md) | 模块设计 |
| [04-api-capabilities.md](./04-api-capabilities.md) | API 与 Capability |
| [05-data-model.md](./05-data-model.md) | 数据模型 |
| [06-development-plan.md](./06-development-plan.md) | 开发计划 |
| [07-testing-acceptance.md](./07-testing-acceptance.md) | 测试与验收 |
