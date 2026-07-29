# AIDP 工具优化测试计划

## 一、测试环境

| 项目 | 值 |
|------|-----|
| NAS | `192.168.0.100` |
| SSH密钥 | `~/.ssh/nas_temp` |
| PostgreSQL | `novel-postgres:5432`, 用户 `novel_os` |
| Controller | `http://localhost:8883` |
| 项目标识 | `aidp` |

---

## 二、测试用例

### 2.1 code-index（端口 18086）

#### 2.1.1 基础健康检查
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:18086/health"
```
**预期**: `{"status":"ok","tool":"code-index","version":"0.1.0"}`

#### 2.1.2 MCP工具接口
```ps1
# 检查 manifest
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:18086/tool/manifest | python3 -m json.tool"
```
**预期**: 返回 capabilities 包含 `code.search`, `code.search.semantic`, `code.explore`, `code.calls`

```ps1
# 检查 capabilities
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:18086/tool/capabilities | python3 -m json.tool"
```

#### 2.1.3 边类型统一（验证小写）
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker exec code-index python3 -c \"
import sqlite3; conn = sqlite3.connect('/app/data/code_index.db');
rows = conn.execute('SELECT DISTINCT edge_type FROM edges LIMIT 20').fetchall();
print([r[0] for r in rows])\"
```
**预期**: 所有 edge_type 为小写 (`contains`, `calls`, `imports`, `extends`, `implements`, `references`)，不存在大写 (CONTAINS, CALLS, IMPORTS)

#### 2.1.4 新字段存在性
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker exec code-index python3 -c \"
import sqlite3; conn = sqlite3.connect('/app/data/code_index.db');
cols = [c[1] for c in conn.execute('PRAGMA table_info(nodes)').fetchall()];
new_fields = ['signature', 'docstring', 'return_type', 'params_json', 'file_hash'];
print('nodes columns:', cols);
print('new fields present:', all(f in cols for f in new_fields))
\""
```
**预期**: `new fields present: True`

#### 2.1.5 新表创建
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker exec code-index python3 -c \"
import sqlite3; conn = sqlite3.connect('/app/data/code_index.db');
tbls = [r[0] for r in conn.execute('SELECT name FROM sqlite_master WHERE type=\\\"table\\\"').fetchall()];
print('Tables:', tbls);
print('file_fingerprints exists:', 'file_fingerprints' in tbls);
print('node_embeddings exists:', 'node_embeddings' in tbls)
\""
```
**预期**: 两个新表都存在

#### 2.1.6 搜索API测试
```ps1
# 基本搜索
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s 'http://localhost:18086/api/search?project_id=1&q=index&limit=5'" | python3 -m json.tool

# 类型过滤搜索
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s 'http://localhost:18086/api/search/typed?project_id=1&node_type=function&limit=5'" | python3 -m json.tool
```
**预期**: 返回 JSON 结果，包含 `symbols` 数组和 `total` 字段

#### 2.1.7 符号搜索MCP调用
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18086/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"code.search\",\"input\":{\"project_id\":1,\"query\":\"index\",\"top_k\":5}}'" | python3 -m json.tool
```
**预期**: `success: true`, `output` 包含搜索结果

---

### 2.2 knowledge-tool（端口 18081）

#### 2.2.1 基础健康检查
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:18081/health"
```
**预期**: `{"status":"UP","tool":"knowledge-tool",...,"dependencies":{"postgres":"UP","storage":"UP","embedding":"UP"}}`

#### 2.2.2 Embedding Provider（Mock）
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:18081/tool/capabilities | python3 -m json.tool"
```
**预期**: 包含 `knowledge.search` capability

#### 2.2.3 文本搜索（原有接口）
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18081/api/knowledge/search -H 'Content-Type: application/json' -d '{\"query\":\"database\",\"top_k\":5}'" | python3 -m json.tool
```

#### 2.2.4 语义搜索（新接口）
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18081/api/knowledge/search/semantic -H 'Content-Type: application/json' -d '{\"query\":\"database\",\"search_mode\":\"hybrid\",\"top_k\":5}'" | python3 -m json.tool
```
**预期**: 返回 `items` 数组，每个 item 有 `score` 和 `score_breakdown`（exact/vector/text 三项分值）

#### 2.2.5 MCP knowledge.search 调用
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18081/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"knowledge.search\",\"input\":{\"query\":\"test\",\"top_k\":3}}'" | python3 -m json.tool
```
**预期**: `success: true`

#### 2.2.6 搜索模式切换测试
```ps1
# Vector模式
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18081/api/knowledge/search/semantic -H 'Content-Type: application/json' -d '{\"query\":\"api\",\"search_mode\":\"vector\",\"top_k\":3}'" | python3 -m json.tool

# Exact模式
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18081/api/knowledge/search/semantic -H 'Content-Type: application/json' -d '{\"query\":\"api\",\"search_mode\":\"exact\",\"top_k\":3}'" | python3 -m json.tool

# BM25模式
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18081/api/knowledge/search/semantic -H 'Content-Type: application/json' -d '{\"query\":\"api\",\"search_mode\":\"bm25\",\"top_k\":3}'" | python3 -m json.tool
```
**预期**: 各模式均返回结果，hybrid模式结果应最丰富

---

### 2.3 memory-tool（端口 18085）

#### 2.3.1 基础健康检查
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:18085/health"
```

#### 2.3.2 MCP Capabilities 验证
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:18085/tool/manifest | python3 -c \"import sys,json; d=json.load(sys.stdin); print([c['name'] for c in d['capabilities']])\""
```
**预期**: 包含 `memory.create`, `memory.search`, `memory.search.hybrid`, `memory.context`, `memory.update`, `memory.delete`, `memory.contradiction.check`, `memory.consolidate`

#### 2.3.3 记忆CRUD完整流程
```ps1
# 1. 创建记忆
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18085/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"memory.create\",\"input\":{\"project\":\"test-project\",\"category\":\"test\",\"title\":\"Test Memory\",\"content\":\"This is a test memory for API testing\"}}'" | python3 -m json.tool
# 记录返回的 id

# 2. 搜索记忆
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18085/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"memory.search\",\"input\":{\"project\":\"test-project\",\"query\":\"test\"}}'" | python3 -m json.tool

# 3. 更新记忆（替换 {id} 为实际ID）
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18085/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"memory.update\",\"input\":{\"memoryId\":1,\"title\":\"Updated Test Memory\"}}'" | python3 -m json.tool

# 4. 删除记忆
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18085/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"memory.delete\",\"input\":{\"memoryId\":1}}'" | python3 -m json.tool
```
**预期**: 创建成功返回id，搜索能找到，更新返回新title，删除返回 `deleted: true`

#### 2.3.4 混合搜索（新功能）
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18085/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"memory.search.hybrid\",\"input\":{\"project\":\"test-project\",\"query\":\"test memory\",\"top_k\":5}}'" | python3 -m json.tool
```
**预期**: `success: true`, `output.search_type: "hybrid"`, items 有 `score_breakdown`（bm25/tfidf/vector）

#### 2.3.5 矛盾检测（新功能）
```ps1
# 先创建一条记忆
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18085/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"memory.create\",\"input\":{\"project\":\"test-contra\",\"category\":\"test\",\"title\":\"Rule A\",\"content\":\"Use localStorage for cookie storage\"}}'" | python3 -m json.tool

# 检测矛盾
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18085/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"memory.contradiction.check\",\"input\":{\"project\":\"test-contra\",\"title\":\"Rule B\",\"content\":\"Do not use localStorage for cookie storage\"}}'" | python3 -m json.tool
```
**预期**: `has_contradictions: true` 或返回矛盾详情

#### 2.3.6 记忆整理（新功能）
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18085/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"memory.consolidate\",\"input\":{\"project\":\"test-contra\",\"similarity_threshold\":0.5}}'" | python3 -m json.tool
```
**预期**: `success: true`，返回 `total_memories`, `clusters_found`, `memories_merged`

#### 2.3.7 Context Package
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18085/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"memory.context\",\"input\":{\"project\":\"test-project\",\"query\":\"test\",\"limit\":5}}'" | python3 -m json.tool
```

---

### 2.4 aidp-controller（端口 8883）

#### 2.4.1 基础健康检查
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:8883/health"
```
**预期**: `{"status":"UP","service":"AIDP Controller","version":"0.1.0"}`

#### 2.4.2 MCP工具列表
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:8883/mcp -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}'" | python3 -m json.tool
```
**预期**: 返回所有注册工具，包含 `aidp_context`, `invoke_tool_mcp`, `list_registered_tools` 等

#### 2.4.3 aidp_context 调用
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:8883/mcp -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"aidp_context\",\"arguments\":{\"project_name\":\"aidp\",\"task\":\"test pipeline\"}}}'" 2>&1 | head -200
```
**预期**: 返回 context 结果，包含 `system_prompt`, `metadata`（含 cache_stats, fallback_status）

#### 2.4.4 invoke_tool_mcp 调用
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:8883/mcp -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"invoke_tool_mcp\",\"arguments\":{\"tool_name\":\"memory-tool\",\"capability\":\"memory.search\",\"arguments\":{\"project\":\"test-project\",\"limit\":5}}}}'" | python3 -m json.tool
```
**预期**: 返回搜索结果或错误（若之前未调用 aidp_context 则拒绝执行）

#### 2.4.5 流水线缓存验证
```ps1
# 第一次调用
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:8883/mcp -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"aidp_context\",\"arguments\":{\"project_name\":\"aidp\",\"task\":\"cache test\"}}}'" | python3 -c "import sys,json; d=json.load(sys.stdin); c=json.loads(d['result']['content'][0]['text']) if 'content' in d['result'] else d; print('cache_stats:', c.get('assembled_context',{}).get('metadata',{}).get('cache_stats',{}))"

# 第二次相同调用（应命中缓存）
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:8883/mcp -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"aidp_context\",\"arguments\":{\"project_name\":\"aidp\",\"task\":\"cache test\"}}}'" | python3 -c "import sys,json; d=json.load(sys.stdin); c=json.loads(d['result']['content'][0]['text']) if 'content' in d['result'] else d; print('cache_stats:', c.get('assembled_context',{}).get('metadata',{}).get('cache_stats',{}))"
```
**预期**: 第二次调用 hits > 第一次

---

### 2.5 quality-tool（端口 18084）

#### 2.5.1 基础健康检查
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:18084/health"
```

#### 2.5.2 MCP Manifest
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:18084/tool/manifest | python3 -c \"import sys,json; d=json.load(sys.stdin); print([c['name'] for c in d['capabilities']])\""
```

#### 2.5.3 代码检查
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18084/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"quality.check\",\"input\":{\"code\":\"def hello():\\n    print(\\\"world\\\")\",\"language\":\"python\"}}'" | python3 -m json.tool
```
**预期**: `success: true`, 返回 issues 列表

#### 2.5.4 多语言分析（新功能 - Python）
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18084/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"quality.check\",\"input\":{\"code\":\"class MyClass:\\n    def method(self, a, b, c, d, e, f):\\n        pass\",\"language\":\"python\"}}'" | python3 -m json.tool
```

#### 2.5.5 多语言分析（新功能 - JavaScript）
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18084/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"quality.check\",\"input\":{\"code\":\"function processData(a, b, c, d, e, f) { return a + b; }\",\"language\":\"javascript\"}}'" | python3 -m json.tool
```

#### 2.5.6 安全扫描
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18084/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"quality.security\",\"input\":{\"code\":\"import os\\nos.system(\\\"rm -rf /\\\")\\neval(\\\"print(1)\\\")\",\"language\":\"python\"}}'" | python3 -m json.tool
```
**预期**: 检测到 `os.system` 和 `eval` 危险调用

---

### 2.6 skill-router（端口 8788）

#### 2.6.1 基础健康检查
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:8788/health"
```

#### 2.6.2 MCP Manifest
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:8788/tool/manifest | python3 -c \"import sys,json; d=json.load(sys.stdin); print([c['name'] for c in d['capabilities']])\""
```
**预期**: 包含 `analyze_intent`, `resolve_task`, `skill_run` 等

#### 2.6.3 意图解析
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:8788/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"analyze_intent\",\"input\":{\"task\":\"帮我查找上次修复的cookie问题\",\"session_id\":\"test-session\"}}'" | python3 -m json.tool
```
**预期**: `success: true`，返回意图分析结果（intent, domains, tags_needed 等）

#### 2.6.4 技能解析
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:8788/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"skill_run\",\"input\":{\"task\":\"分析代码质量\",\"mode\":\"auto\",\"top_k\":3}}'" | python3 -m json.tool
```

---

### 2.7 sandbox-tool（端口 18083）

#### 2.7.1 基础健康检查
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s http://localhost:18083/health"
```

#### 2.7.2 Python代码执行
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18083/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"sandbox.execute\",\"input\":{\"code\":\"print(\\\"Hello from sandbox\\\")\\nprint(1+2+3)\",\"language\":\"python\"}}'" | python3 -m json.tool
```
**预期**: `success: true`，stdout 包含 "Hello from sandbox" 和 "6"

#### 2.7.3 Bash执行
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18083/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"sandbox.execute\",\"input\":{\"code\":\"echo hello && date\",\"language\":\"bash\"}}'" | python3 -m json.tool
```

#### 2.7.4 执行历史查询
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18083/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"sandbox.history\",\"input\":{\"limit\":5}}'" | python3 -m json.tool
```
**预期**: 返回历史执行记录

#### 2.7.5 安全检查（新功能）
```ps1
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -s -X POST http://localhost:18083/tool/invoke -H 'Content-Type: application/json' -d '{\"capability\":\"sandbox.execute\",\"input\":{\"code\":\"import os\\nos.system(\\\"ls\\\")\",\"language\":\"python\"}}'" | python3 -m json.tool
```
**预期**: 被安全检查阻止或限制执行

---

## 三、快速自动化测试脚本

将以下内容保存为 `test_all.ps1` 运行：

```ps1
$nas = "root@192.168.0.100"
$sshOpt = "-i ~/.ssh/nas_temp"

function Test-Tool($name, $url) {
    Write-Host "Testing $name..." -ForegroundColor Cyan
    $result = ssh $sshOpt $nas "curl -s $url"
    if ($result -match '"status":"ok"|"status":"UP"') {
        Write-Host "  $name : PASS" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  $name : FAIL - $result" -ForegroundColor Red
        return $false
    }
}

$passed = 0; $failed = 0

# 健康检查
$endpoints = @{
    "controller"   = "http://localhost:8883/health"
    "code-index"   = "http://localhost:18086/health"
    "knowledge-tool" = "http://localhost:18081/health"
    "memory-tool"  = "http://localhost:18085/health"
    "quality-tool" = "http://localhost:18084/health"
    "sandbox-tool" = "http://localhost:18083/health"
    "skill-router" = "http://localhost:8788/health"
}

foreach ($t in $endpoints.GetEnumerator()) {
    if (Test-Tool $t.Key $t.Value) { $passed++ } else { $failed++ }
}

# MCP Manifest检查
Write-Host "`nTesting MCP manifests..." -ForegroundColor Cyan
$mcpTests = @(
    @{name="code-index"; expected=@("code.search","code.search.semantic","code.explore","code.calls")},
    @{name="memory-tool"; expected=@("memory.create","memory.search","memory.search.hybrid","memory.contradiction.check","memory.consolidate")},
    @{name="knowledge-tool"; expected=@("knowledge.search")}
)

foreach ($t in $mcpTests) {
    $result = ssh $sshOpt $nas "curl -s http://localhost:$($t.name -eq 'code-index' ? '18086' : $t.name -eq 'memory-tool' ? '18085' : '18081')/tool/manifest"
    $caps = ($result | ConvertFrom-Json).capabilities.name
    $missing = $t.expected | Where-Object { $_ -notin $caps }
    if ($missing) {
        Write-Host "  $($t.name) MCP: FAIL - missing: $missing" -ForegroundColor Red
        $failed++
    } else {
        Write-Host "  $($t.name) MCP: PASS" -ForegroundColor Green
        $passed++
    }
}

Write-Host "`n=== Results: $passed PASS, $failed FAIL ===" -ForegroundColor $(if($failed -eq 0){'Green'}else{'Red'})
```

---

## 四、测试检查清单

| # | 测试项 | 状态 |
|---|--------|------|
| 1 | code-index 健康 | ☐ |
| 2 | code-index 边类型全部小写 | ☐ |
| 3 | code-index nodes新字段存在 | ☐ |
| 4 | code-index 新表(file_fingerprints/node_embeddings)创建 | ☐ |
| 5 | code-index 类型过滤搜索 | ☐ |
| 6 | code-index MCP code.search.semantic | ☐ |
| 7 | knowledge-tool 健康(dependencies全UP) | ☐ |
| 8 | knowledge-tool 三级语义搜索(hybrid) | ☐ |
| 9 | knowledge-tool 搜索模式切换(vector/exact/bm25) | ☐ |
| 10 | memory-tool 健康 | ☐ |
| 11 | memory-tool CRUD完整流程 | ☐ |
| 12 | memory-tool 混合搜索(含score_breakdown) | ☐ |
| 13 | memory-tool 矛盾检测 | ☐ |
| 14 | memory-tool 记忆整理 | ☐ |
| 15 | controller 健康 | ☐ |
| 16 | controller aidp_context(cache+fallback) | ☐ |
| 17 | controller invoke_tool_mcp跨工具调用 | ☐ |
| 18 | controller 缓存命中率验证 | ☐ |
| 19 | quality-tool 健康 | ☐ |
| 20 | quality-tool Python/JS多语言检查 | ☐ |
| 21 | quality-tool 安全扫描 | ☐ |
| 22 | skill-router 意图解析 | ☐ |
| 23 | sandbox-tool Python/Bash执行 | ☐ |
| 24 | sandbox-tool 安全检查 | ☐ |
