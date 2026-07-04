# asset-tool 架构设计

## 1. 总体架构

```text
aidp-controller (HTTP)
    |
    | POST /tool/invoke
    v
┌─────────────────────────────┐
│  asset-tool (Python + FastAPI)│
│  ├── API Layer               │
│  ├── Service Layer           │
│  ├── Repository Layer        │
│  └── Template Engine         │
├─────────────────────────────┤
│  PostgreSQL                  │
└─────────────────────────────┘
```

## 2. 运行模式

### 2.1 Standalone 模式

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8081
```

或：

```bash
docker run aidp/asset-tool:latest
```

### 2.2 Managed 模式

由 controller 管理，通过 HTTP 调用。

### 2.3 Remote 模式

部署在远端，controller 只登记 endpoint。

## 3. 技术栈

| 能力 | 技术 |
|---|---|
| Runtime | Python 3.13 |
| HTTP | FastAPI |
| Schema | Pydantic |
| DB | PostgreSQL |
| ORM | SQLAlchemy 2.0 (async) |
| Migration | SQL migration |
| Template | Jinja2 (渲染) |
| Test | pytest |

## 4. 调用链路

### 4.1 资产检索

```text
receive /tool/invoke
  -> parse capability
  -> validate input
  -> resolve workspace/project
  -> permission check
  -> keyword search
  -> format results
  -> return response
```

### 4.2 模板渲染

```text
receive /tool/invoke
  -> parse capability
  -> validate input
  -> resolve workspace/project
  -> permission check
  -> get asset content
  -> parse template variables
  -> render template
  -> return result
```

## 5. 关键设计原则

- 工具只编排资产检索和模板渲染，不吞并业务逻辑。
- 所有外部调用都必须有 trace_id。
- 所有跨项目数据访问必须被权限检查拦截。
- 工具内部必须二次校验权限。
