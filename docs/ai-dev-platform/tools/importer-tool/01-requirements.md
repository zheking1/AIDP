# importer-tool 需求说明

## 1. 背景

AIDP 平台已有 Knowledge（文档知识库）、Skills（技能）、Rules（规则）、Quality（质量检查）等独立模块，但每个模块只能通过各自 API 单独操作。当用户需要通过对话方式批量导入 RuoYi-Cloud-Plus 这类数百个文件的项目文档时，缺少一个**对话式编排层**来完成：

- 理解用户输入的意图（这是知识？技能？规则？还是计划？）
- 获取内容（粘贴文本、URL 抓取、文件读取、目录扫描）
- 自动分类和打标签
- 质量检查和安全扫描
- 确认后持久化到对应模块

`importer-tool` 填补这个空白，作为用户/Agent 与各存储模块之间的智能管道。

## 2. 产品目标

- 支持通过自然语言对话导入文档、知识、技能、规则、计划。
- 支持多种内容来源：直接粘贴、URL、文件路径、目录批量扫描。
- 自动分类内容类型和领域标签，用户确认后写入。
- 导入前自动运行质量检查（lint + 安全扫描），发现严重问题阻止导入。
- 支持幂等防重：相同内容不重复导入，可更新版本。
- 所有操作结果向用户对话式反馈。

## 3. 非目标

MVP 不做：

- 不替代 `knowledge-tool`、`skills` 模块的详细存储逻辑。
- 不做复杂的语义去重（仅靠 checksum + title 判重）。
- 不自动修改代码，只输出修复建议。
- 不做批量自动提交（每步需用户确认）。
- 不处理二进制文件导入（仅文本类内容）。

## 4. 内容类型

| 类型 | 目标存储 | 说明 | 示例 |
|------|---------|------|------|
| `knowledge` | KnowledgeDocument | 参考性文档，按需检索 | 架构总览、API 文档、ADR |
| `skill` | Skill | 可执行的 Agent 技能指令 | 代码审查 prompt、测试技能 |
| `rule` | Rule | 约束性规范，Agent 必须遵守 | 编码规范、技术栈锁定 |
| `plan` | KnowledgeDocument (tag:plan) | 方案计划类文档 | 开发蓝图、任务清单 |

## 5. 使用场景

### 5.1 单文档导入

用户粘贴一段 Markdown 或提供一个 URL，importer-tool 自动识别类型、打标签、检查质量，用户确认后存储。

### 5.2 目录批量导入

用户指定项目路径（如 `D:\Project\web\RuoYi-Cloud-Plus\docs\`），工具递归扫描、自动分类每个文件，生成导入清单供用户逐条确认或一键批量。

### 5.3 技能/规则导入

用户提供技能指令或规则文本，工具检测到 `instruction` 或 `severity` 关键字后自动路由到 skill/rule 模块，并提示补充 scope/group 等元数据。

### 5.4 增量更新

再次导入同一文件时检测到 checksum 变化，询问用户是否创建新版本覆盖。

## 6. 功能需求

### 6.1 内容获取 (Acquire)

- `text` — 直接接收文本内容。
- `url` — 抓取 URL 内容（HTML 转 Markdown）。
- `file` — 读取本地文件（支持 .md/.txt/.yaml/.json/.sql/.py 等文本格式）。
- `directory` — 扫描目录，按扩展名和白名单过滤，返回文件列表。

### 6.2 类型分类 (Classify)

- 基于内容特征自动判断 type（knowledge/skill/rule/plan）。
- 自动提取标题（文件名或首行 H1）。
- 自动推荐 tags、category、severity（规则类）。
- 分类结果展示给用户确认，允许修改。

### 6.3 质量检查 (Quality Check)

- 调用 `quality-tool` 或内置 `POST /api/quality/check`。
- lint 检查：行长度、尾随空格、文件末换行。
- 安全扫描：硬编码密钥、eval/exec、SQL 注入风险。
- 规则特有检查：必须包含 severity、有明确的约束语句。
- 技能特有检查：必须有 instruction 或 content 字段。
- critical 级别问题阻止导入；warning 询问用户是否跳过。

### 6.4 持久化 (Persist)

- 知识 → `POST /api/knowledge/documents`。
- 技能 → `POST /api/skills` (含 files)。
- 规则 → `POST /api/rules`。
- 计划 → `POST /api/knowledge/documents` (自动加 tag:plan)。
- 返回存储结果和访问链接。

### 6.5 幂等防重

- 计算 content 的 checksum（SHA256）。
- 相同 title + scope 下 checksum 一致 → 跳过。
- 相同 title + scope 下 checksum 不一致 → 提示更新版本。

## 7. 非功能需求

- 单文件导入 P95 小于 5 秒（含质量检查）。
- 目录扫描 100 个文件 P95 小于 30 秒。
- URL 抓取超时 15 秒。
- 所有操作记录 trace_id。
- 所有交互结果可回溯查看。

## 8. MVP 验收范围

- 工具协议接口可用（/health、/manifest、/capabilities、/invoke）。
- 可通过对话导入单个文档（支持 text/url/file 三种来源）。
- 自动分类内容类型和推荐标签。
- 导入前自动运行 quality check。
- 支持用户确认/修改后持久化。
- 支持幂等跳过和版本更新提示。
- 支持导入结果回显。
