import json, time, os, sys, subprocess as sp
from datetime import datetime

BASE = "http://127.0.0.1:8883"
SESSION = "/tmp/aidp_test.txt"
results = []
ts = str(int(time.time()))

def api(method, path, data=None):
    cookie = f"-b {SESSION}" if os.path.exists(SESSION) else ""
    data_arg = f"-H 'Content-Type: application/json' -d '{json.dumps(data)}'" if data else ""
    cmd = f"curl -s {cookie} -X {method} '{BASE}{path}' {data_arg}"
    r = sp.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return r.stdout.strip()

def login():
    sp.run(f"curl -s -c {SESSION} -X POST '{BASE}/api/auth/login/form' -d 'username=admin&password=admin123' -o /dev/null", shell=True, capture_output=True)
    r = api("GET", "/api/auth/users?limit=1")
    return "items" in r

def test(name, status, detail=""):
    icon = {"PASS":"✅","FAIL":"❌"}.get(status,"ℹ️")
    print(f"  {icon} {name}: {detail}")
    results.append({"name":name,"status":status,"detail":detail})

def test_page(path, page_name):
    r = api("GET", f"{path}?embed=1")
    if "Internal Server Error" in r:
        test(f"{page_name} 页面", "FAIL", "500 Internal Server Error")
    elif len(r) < 100:
        test(f"{page_name} 页面", "FAIL", f"响应过短 ({len(r)} chars)")
    else:
        test(f"{page_name} 页面", "PASS", f"{len(r)} bytes")

def test_list(api_path, name):
    r = api("GET", api_path)
    try:
        d = json.loads(r)
        items = d.get("items", d.get("results", []))
        total = d.get("total", len(items))
        test(f"{name} 列表", "PASS", f"{total} 条")
    except:
        test(f"{name} 列表", "FAIL", f"JSON解析失败: {r[:80]}")

def test_create(api_path, name, data):
    r = api("POST", api_path, data)
    try:
        d = json.loads(r)
        if "detail" in d:
            test(f"{name} 创建", "FAIL", f"错误: {d['detail']}")
            return None
        new_id = d.get("id")
        test(f"{name} 创建", "PASS", f"id={new_id}")
        return new_id
    except:
        test(f"{name} 创建", "FAIL", f"响应异常: {r[:80]}")
        return None

def test_delete(api_path, item_id, name):
    r = api("DELETE", f"{api_path}/{item_id}")
    try:
        d = json.loads(r)
        if d.get("success"):
            test(f"{name} 删除", "PASS", f"id={item_id}")
        else:
            test(f"{name} 删除", "FAIL", str(d))
    except:
        test(f"{name} 删除", "FAIL", r[:80])

def report():
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    print(f"\n{'='*50}")
    print(f"  测试报告")
    print(f"  总计: {len(results)} | 通过: {passed} | 失败: {failed} | 通过率: {passed/len(results)*100:.1f}%")
    print(f"{'='*50}")
    if failed:
        print(f"\n失败项:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  ❌ {r['name']}: {r['detail']}")
    open("/tmp/aidp_test_report.json","w").write(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n报告已保存: /tmp/aidp_test_report.json")

print(f"AIDP 系统测试 @ {datetime.now().isoformat()}")
print(f"目标: {BASE}")
print("="*50)

if not login():
    test("登录", "FAIL", "登录失败")
    report()
    sys.exit(1)
test("登录", "PASS", "admin 登录成功")

# ───── 1. 知识库管理 ─────
print(f"\n{'─'*40}\n[1] 知识库管理\n{'─'*40}")
test_page("/knowledge/bases", "知识库管理")
test_list("/api/knowledge/bases", "知识库管理")
kid = test_create("/api/knowledge/bases", "知识库管理", {"name":f"测试KB-{ts}","description":"自动测试"})
if kid: test_delete("/api/knowledge/bases", kid, "知识库管理")

# ───── 2. 文档管理 ─────
print(f"\n{'─'*40}\n[2] 文档管理\n{'─'*40}")
test_page("/knowledge/documents", "文档管理")

# ───── 3. 知识搜索 ─────
print(f"\n{'─'*40}\n[3] 知识搜索\n{'─'*40}")
test_page("/knowledge/search", "知识搜索")

# ───── 4. 文档模板 ─────
print(f"\n{'─'*40}\n[4] 文档模板\n{'─'*40}")
test_page("/knowledge/templates", "文档模板")
test_list("/api/knowledge/templates/list", "文档模板")
tid = test_create("/api/knowledge/templates/create", "文档模板", {"name":f"测试TPL-{ts}","category":"prd","content":f"# {ts}"})
if tid: r = api("DELETE", f"/api/knowledge/templates/{tid}")

# ───── 5. 代码资产 ─────
print(f"\n{'─'*40}\n[5] 代码资产\n{'─'*40}")
test_page("/assets", "代码资产")
test_list("/api/assets/list", "代码资产")
aid = test_create("/api/assets/create", "代码资产", {"title":f"测试AST-{ts}","asset_type":"snippet","content":"print(1)","language":"python"})
if aid: test_delete("/api/assets", aid, "代码资产")

# ───── 6. 全局技能 ─────
print(f"\n{'─'*40}\n[6] 全局技能\n{'─'*40}")
test_page("/skills/global", "全局技能")
test_list("/api/skills/list?scope=global", "全局技能")

# ───── 7. 个人技能 ─────
print(f"\n{'─'*40}\n[7] 个人技能\n{'─'*40}")
test_page("/skills/personal", "个人技能")
test_list("/api/skills/list?scope=personal", "个人技能")
sid = test_create("/api/skills/create", "个人技能", {"name":f"测试SK-{ts}","scope":"personal","instruction":f"test {ts}","tags":["test"]})
if sid: test_delete("/api/skills", sid, "个人技能")

# ───── 8. 全局规则 ─────
print(f"\n{'─'*40}\n[8] 全局规则\n{'─'*40}")
test_page("/rules/global", "全局规则")
test_list("/api/rules/list?scope=global", "全局规则")

# ───── 9. 个人规则 ─────
print(f"\n{'─'*40}\n[9] 个人规则\n{'─'*40}")
test_page("/rules/personal", "个人规则")
test_list("/api/rules/list?scope=personal", "个人规则")
rid = test_create("/api/rules/create", "个人规则", {"name":f"测试RL-{ts}","scope":"personal","content":f"rule {ts}","category":"security"})
if rid: test_delete("/api/rules", rid, "个人规则")

# ───── 10. Agent ─────
print(f"\n{'─'*40}\n[10] Agent管理\n{'─'*40}")
test_page("/agents", "Agent管理")
test_list("/api/agents/list?scope=personal", "Agent管理")
gid = test_create("/api/agents/create", "Agent管理", {"name":f"测试AG-{ts}","scope":"personal","role":"tester","instructions":f"agent {ts}"})
if gid: test_delete("/api/agents", gid, "Agent管理")

# ───── 11. 流程引擎 ─────
print(f"\n{'─'*40}\n[11] 流程引擎\n{'─'*40}")
test_page("/workflows", "流程引擎")
test_list("/api/workflows/list", "流程引擎")
wid = test_create("/api/workflows/create", "流程引擎", {"name":f"测试WF-{ts}","category":"development","steps":[{"name":"步骤1","order":0}]})
if wid: test_delete("/api/workflows", wid, "流程引擎")

# ───── 12. 记忆列表 ─────
print(f"\n{'─'*40}\n[12] 记忆中心\n{'─'*40}")
test_page("/memory/memories", "记忆列表")
test_list("/api/memory/memories", "记忆列表")
mid = test_create("/api/memory/memories", "记忆列表", {"title":f"测试MEM-{ts}","content":f"content {ts}","category":"other"})
if mid: test_delete("/api/memory/memories", mid, "记忆列表")

# ───── 13. 记忆图谱 ─────
test_page("/memory/graph", "记忆图谱")

# ───── 14. 记忆检索 ─────
test_page("/memory/search", "记忆检索")

# ───── 15. 代码沙箱 ─────
print(f"\n{'─'*40}\n[15] 代码沙箱\n{'─'*40}")
test_page("/sandbox", "代码沙箱")
r = api("POST", "/api/sandbox/execute", {"code":"print('hello')","language":"python"})
try:
    d = json.loads(r)
    test("沙箱 执行", "PASS", f"exit_code={d.get('exit_code')}") if "stdout" in d else test("沙箱 执行", "FAIL", str(d)[:60])
except:
    test("沙箱 执行", "FAIL", r[:60])

# ───── 16. 质量检查 ─────
print(f"\n{'─'*40}\n[16] 质量检查\n{'─'*40}")
test_page("/quality", "质量检查")
r = api("POST", "/api/quality/check", {"code":"x=1","check_type":"lint"})
try:
    d = json.loads(r)
    test("质量 检查", "PASS", f"issues={d.get('issue_count')}, score={d.get('score')}")
except:
    test("质量 检查", "FAIL", r[:60])

# ───── 17. Admin ─────
print(f"\n{'─'*40}\n[17] 管理后台\n{'─'*40}")
test_page("/admin/projects", "Admin项目管理")
test_page("/admin/skills", "Admin技能管理")
test_page("/admin/rules", "Admin规则管理")

# Report
report()