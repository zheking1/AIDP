# project-analyzer-tool 需求说明

## 1. 背景

AI 进入一个已有项目时，常常需要先理解目录结构、技术栈、模块关系、入口类、接口层、数据库迁移、测试布局和构建方式。如果每次都全量读取仓库，成本高且容易漏掉关键文件。

`project-analyzer-tool` 通过扫描项目生成结构化快照，供 controller、memory-tool、knowledge-tool 和 AI Agent 使用。

## 2. 扫描范围

MVP 支持：

- 文件树和语言识别。
- Node/TypeScript 和 Python 依赖。
- Fastify route、service、repository。
- REST API 路由摘要。
- Flyway/Liquibase/SQL 迁移。
- Flutter/Dart lib/test 结构。
- Dockerfile、docker-compose、application.yml。
- 测试目录和测试框架识别。

## 3. 使用场景

- 新项目接入时生成项目概要。
- AI 开发前调用 `project.summary` 获取上下文。
- AI 需要找某个类或接口时调用 `project.find_symbol`。
- 变更后增量扫描并写入 memory-tool。
- 生成“当前项目适合调用哪些工具”的建议。

## 4. 功能需求

### 4.1 项目扫描

输入项目路径或仓库 URI，输出 scan_id 和 snapshot_id。必须支持：

- include/exclude glob。
- 最大文件大小。
- 忽略 `.git/dist/build/coverage/node_modules/.venv/__pycache__`。
- 只读扫描，不修改项目。

### 4.2 摘要生成

摘要包含：

- 技术栈。
- 构建命令。
- 模块列表。
- 关键入口。
- API 列表。
- 数据库迁移。
- 测试命令。
- 风险和待确认点。

### 4.3 符号查找

支持查找：

- TypeScript class/function/interface。
- Fastify route。
- Python class/function。
- 配置 key。

### 4.4 依赖图

输出模块依赖、外部依赖、版本和潜在冲突。

## 5. 非目标

MVP 不做完整 IDE 级语义分析，不编译项目，不做代码质量评分，不做跨仓库深度调用图。

## 6. 非功能需求

- 10 万文件仓库应可通过 ignore 策略完成扫描。
- 1 万文件项目全量扫描 P95 小于 60 秒。
- 增量扫描 P95 小于 10 秒。
- 结果可重复，文件排序稳定。

## 7. 验收范围

- 扫描 TypeScript/Fastify 示例项目。
- 扫描 Flutter 示例项目。
- 生成 markdown summary。
- 查找 Controller 路由。
- 查找类和配置。
- 将摘要导出到 memory-tool。
