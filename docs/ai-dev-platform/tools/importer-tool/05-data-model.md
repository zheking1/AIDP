# importer-tool 数据模型设计

## 1. 设计原则

importer-tool 本身 **不存储文档内容**，只存储导入任务元数据、会话状态和导入日志。实际内容通过调用 controller 的 knowledge/skills/rules 模块 API 持久化。

表名前缀统一为 `it_`。

## 2. 表清单

| 表 | 用途 | MVP |
|---|------|:---:|
| `it_import_session` | 导入会话 | 是 |
| `it_import_item` | 会话中的单个文件/内容项 | 是 |
| `it_import_log` | 导入操作日志 | 是 |

## 3. `it_import_session`

```sql
create table it_import_session (
  id varchar(36) primary key,                -- UUID
  user_id varchar(100) not null,             -- 导入者
  project_id int,                            -- 关联项目
  scope varchar(20) default 'personal',      -- personal / global / project

  source_type varchar(20) not null,          -- text / url / file / directory
  source_uri text,                           -- 原始来源 URI 或路径

  status varchar(20) not null default 'pending',
  -- pending / classifying / acquiring / checking
  -- categorizing / persisting / completed / failed / cancelled

  total_items int default 0,                 -- 总项目数
  completed_items int default 0,             -- 已完成数
  failed_items int default 0,                -- 失败数
  skipped_items int default 0,               -- 跳过数

  metadata jsonb default '{}',               -- 扩展元数据

  created_at timestamptz not null,
  updated_at timestamptz not null,
  completed_at timestamptz
);

create index idx_it_session_user on it_import_session (user_id, created_at desc);
create index idx_it_session_status on it_import_session (status);
```

## 4. `it_import_item`

```sql
create table it_import_item (
  id varchar(36) primary key,                -- UUID
  session_id varchar(36) not null references it_import_session(id),
  item_index int not null,                   -- 序号

  filename varchar(500),                     -- 原始文件名
  content_hash varchar(64),                  -- SHA256

  classified_type varchar(20),               -- knowledge / skill / rule / plan
  classified_confidence varchar(10),         -- high / medium / low
  suggested_title varchar(500),
  suggested_tags jsonb default '[]',
  suggested_category varchar(200),
  suggested_severity varchar(20),            -- 仅规则类

  quality_passed boolean,                    -- 质量检查是否通过
  quality_issues jsonb default '[]',         -- issue 列表

  confirmed_type varchar(20),                -- 用户确认后的类型
  confirmed_tags jsonb default '[]',
  confirmed_category varchar(200),
  confirmed_severity varchar(20),

  persist_type varchar(20),                  -- 实际存储类型
  persist_id varchar(36),                    -- 存储后的 ID
  persist_url text,                          -- 访问链接
  persist_version int,                       -- 版本号

  status varchar(20) not null default 'pending',
  -- pending / awaiting_confirmation / confirmed / persisted
  -- skipped / failed / blocked

  error_message text,                        -- 错误信息

  created_at timestamptz not null,
  persisted_at timestamptz
);

create index idx_it_item_session on it_import_item (session_id, item_index);
create index idx_it_item_status on it_import_item (status);
```

## 5. `it_import_log`

```sql
create table it_import_log (
  id varchar(36) primary key,
  session_id varchar(36) not null references it_import_session(id),
  item_id varchar(36) references it_import_item(id),

  level varchar(10) not null,                -- info / warn / error
  message text not null,
  details jsonb default '{}',

  trace_id varchar(128),
  created_at timestamptz not null
);

create index idx_it_log_session on it_import_log (session_id, created_at);
```

## 6. 临时数据

导入流程中不落库的临时数据结构：

### ImportRequest

```json
{
  "source": {
    "type": "text|url|file|directory",
    "content": "",
    "url": "",
    "path": "",
    "pattern": "**/*.md",
    "name": ""
  },
  "user_id": "",
  "project_id": null,
  "scope": "personal",
  "auto_confirm": false
}
```

### ConfirmRequest

```json
{
  "session_id": "",
  "confirm": {
    "type": "knowledge",
    "tags": ["architecture"],
    "category": "architecture/overview",
    "severity": null,
    "skip_quality_warnings": false
  },
  "items": [
    {"index": 0, "type": "knowledge", "tags": [...], "category": "..."},
    {"index": 1, "type": "rule", ...}
  ]
}
```

## 7. 配置模型

```yaml
importer:
  quality:
    enabled: true
    blocking_severities: ["critical"]
    endpoint: "http://localhost:8883/api/quality/check"
  acquirer:
    max_file_size_mb: 5
    max_text_length: 100000
    url_timeout_seconds: 15
    url_max_length: 50000
    directory_max_files: 500
    text_extensions: [".md", ".txt", ".yaml", ".yml", ".json", ".xml", ".sql", ".py", ".js", ".ts", ".sh", ".properties", ".env", ".cfg", ".ini", ".toml", ".csv"]
    ignore_dirs: [".git", "node_modules", "__pycache__", "venv", "dist", "build", ".venv"]
  persist:
    endpoints:
      knowledge: "http://localhost:8883/api/knowledge/documents"
      skill: "http://localhost:8883/api/skills"
      rule: "http://localhost:8883/api/rules"
```

## 8. 数据保留

- 已完成的导入会话保留 90 天。
- 超过 90 天的自动归档清理。
- 失败的导入会话保留 7 天后清理。
