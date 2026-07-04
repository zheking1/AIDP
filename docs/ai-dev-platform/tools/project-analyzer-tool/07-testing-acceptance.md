# project-analyzer-tool 测试与验收

## 1. 单元测试

| 模块 | 用例 |
|---|---|
| `WorkspaceReader` | 路径越界、ignore、生僻编码、大文件跳过 |
| `LanguageDetector` | TypeScript、Python、Dart、SQL、YAML |
| `NodeAnalyzer` | scripts、dependencies、workspace |
| `PythonAnalyzer` | dependencies、entrypoints、test framework |
| `FastifyAnalyzer` | route、plugin、service |
| `SummaryService` | 摘要顺序稳定、缺失信息标记待确认 |

## 2. 集成测试

- 扫描 TypeScript/Fastify 示例，识别 package.json、routes、services、config。
- 扫描 Flutter 示例，识别 pubspec、lib、test、Widget。
- 增量扫描只更新变更文件。
- find_symbol 能找到类和路由。
- export_memory 调用 memory-tool mock。

## 3. 性能验收

| 场景 | 指标 |
|---|---:|
| 1 万文件全量扫描 | < 60s |
| 100 文件增量扫描 | < 10s |
| find_symbol | < 500ms |

## 4. 安全验收

- 不执行任何项目脚本。
- 不读取 workspace 外文件。
- 不保存完整源码。
- 跳过二进制和超大文件。

## 5. 端到端验收

controller 调用 `project.scan`，再调用 `project.summary`，AI 可基于 markdown 摘要说明技术栈、构建命令、核心目录和下一步开发入口。
