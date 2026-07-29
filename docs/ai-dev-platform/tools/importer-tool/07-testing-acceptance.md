# importer-tool 测试与验收

## 1. 单元测试

### 1.1 ContentAcquirer

| 用例 | 输入 | 预期 |
|------|------|------|
| text 来源 | `{type:"text", content:"# Hello"}` | 返回 content="# Hello", filename=null |
| url 来源 | `{type:"url", url:"https://example.com/doc"}` | 成功获取并转 Markdown |
| url 超时 | 超时 URL | 返回 SOURCE_FETCH_FAILED |
| file 来源 | 有效文件路径 | 正确读取内容 |
| file 不存在 | 无效路径 | 返回 SOURCE_FETCH_FAILED |
| file 过大 | >5MB 文件 | 拒绝读取 |
| 目录扫描 | 项目 docs 目录 | 返回白名单文件列表 |
| 目录扫描忽略 | 含 node_modules | 忽略匹配目录 |
| 目录穿越 | path="../outside" | 拒绝访问 |

### 1.2 ContentClassifier

| 用例 | 输入 | 预期 |
|------|------|------|
| 含 instruction 特征 | 内容含 "instruction:" + "content:" | type=skill |
| 含 severity 约束 | 内容含 "severity: critical" + "必须" | type=rule |
| 文件名含 plan | filename="erp-master-plan.md" | type=plan |
| 文件名含 ADR | filename="ADR-001-xxx.md" | type=knowledge |
| 通用 Markdown | filename="readme.md", 首行 H1 | type=knowledge |
| 无特征 | 短文本无关键词 | 返回 low confidence + 需确认 |

### 1.3 QualityGate

| 用例 | 输入 | 预期 |
|------|------|------|
| 无问题内容 | 干净的 Markdown | passed=true, issues=[] |
| lint 问题 | 超长行 | passed=true, issues=[warning] |
| 安全扫描命中 | 含硬编码密码 | passed=false, issues=[critical] |
| 规则缺 severity | rule 内容无 severity 字段 | 附加 issue |
| skill 缺 instruction | 内容无 instruction | 附加 issue |
| API 不可用 | controller 返回 503 | 降级内置检查 |

### 1.4 ContentPersister

| 用例 | 输入 | 预期 |
|------|------|------|
| 知识写入 | knowledge 内容 | 调用 POST /api/knowledge/documents |
| 技能写入 | skill 内容+files | 调用 POST /api/skills |
| 规则写入 | rule 内容 | 调用 POST /api/rules |
| 幂等跳过 | 相同 checksum | 返回 skipped |
| 版本更新 | 不同 checksum + 已有 | 提示更新 |
| API 失败 | controller 500 | 返回 PERSIST_FAILED |

### 1.5 ImportOrchestrator

| 用例 | 输入 | 预期 |
|------|------|------|
| 完整导入流程 | text 来源 | pending→classifying→acquiring→checking→categorizing→persisting→completed |
| 自动确认 | auto_confirm=true | 跳过用户确认步骤 |
| 质量阻塞 | critical issue | 状态变为 blocked，不进入 persist |
| 用户取消 | confirm=false | 状态变为 cancelled |

## 2. 集成测试

### 2.1 端到端单文件导入

```text
步骤:
1. 调用 /tool/invoke  importer.import, source=text
2. 检查返回 session_id, status=awaiting_confirmation
3. 调用 /tool/invoke  importer.import 带上 confirm
4. 检查返回 status=completed, 有 target_id
5. 调用 controller GET /api/knowledge/documents/{target_id} 验证已存在
```

### 2.2 端到端 URL 导入

```text
1. 用 Python 启动一个本地 HTTP 服务器提供测试 Markdown 文件
2. 调用 importer.import, source=url
3. 确认导入
4. 验证内容正确
```

### 2.3 端到端目录批量导入

```text
1. 准备测试目录，含 5 个不同类型文件（2 knowledge + 1 rule + 1 skill + 1 plan）
2. 调用 importer.import_batch
3. 检查返回清单分类是否正确
4. 逐个确认后批量导入
5. 验证所有文件已存储到对应模块
```

### 2.4 幂等测试

```text
1. 导入文件 A
2. 再次导入相同文件 A
3. 返回 skipped, 不重复创建
4. 修改文件 A 后再导入
5. 提示版本更新
```

## 3. 验收标准

### 3.1 必须通过（P0）

- [ ] 工具协议接口全部可用（/health → 200、/manifest → 正确、/capabilities → 列表）
- [ ] 单文件导入（text 来源）成功完成全流程
- [ ] 单文件导入（url 来源）成功完成全流程
- [ ] 单文件导入（file 来源）成功完成全流程
- [ ] 批量目录导入（directory 来源）成功完成全流程
- [ ] 内容类型自动分类准确率 > 80%（基于测试集）
- [ ] 质量检查发现 critical 问题时阻止导入
- [ ] 幂等防重：相同内容不重复导入
- [ ] 用户确认机制：确认前不写入

### 3.2 建议通过（P1）

- [ ] 四种类型（knowledge/skill/rule/plan）都可正常导入
- [ ] 导入历史可查询
- [ ] 导入状态可回溯
- [ ] 失败时返回结构化错误码
- [ ] 标签推荐合理（人工评估）

### 3.3 增强（P2）

- [ ] 导入后触发 knowledge chunking 索引
- [ ] 导入后自动绑定到项目
- [ ] AI 模型增强分类准确率
- [ ] 导入结果 dashboard

## 4. 测试工具

Python pytest + httpx（用于模拟 controller API）。

测试 fixture：

```python
@pytest.fixture
def mock_controller():
    """启动一个 FastAPI TestClient 模拟 controller API"""
    ...

@pytest.fixture
def sample_knowledge_doc():
    return {"title": "架构总览", "content": "# 架构总览\n\n系统采用..."}

@pytest.fixture
def sample_skill_doc():
    return {"name": "code-review", "instruction": "你是一个代码审查专家...", "content": "## 审查规则..."}

@pytest.fixture
def sample_rule_doc():
    return {"name": "编码规范", "content": "## 编码规范\n\nseverity: high\n\n必须遵守..."}
```

## 5. 性能测试

| 场景 | 目标 |
|------|------|
| 单文件 text 导入 | < 2s |
| 单文件 URL 导入 | < 18s (含网络) |
| 目录扫描 100 个文件 | < 5s |
| 批量导入 50 个文件 | < 60s |
| quality check 内存占用 | < 200MB |
