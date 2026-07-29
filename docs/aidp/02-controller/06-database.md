# Database Design
The AIDP Controller uses PostgreSQL with SQLAlchemy async ORM. All tables are created automatically on startup via Base.metadata.create_all. Table names use the aidp_ prefix for the new unified platform models.
Auto-generated IDs use either auto-increment integers or UUID strings (gen_uuid()).

## 1. Project Tables

### aidp_projects (Unified project table, new architecture)
| Column | Type | Default | FK | Index | Notes |
|--------|------|---------|----|-------|-------|
| id | Integer | autoincrement PK | -- | PK | |
| name | String(256) | NOT NULL | -- | -- | |
| description | Text | NULL | -- | -- | |
| visibility | String(20) | private | -- | -- | private/internal/public |
| owner_id | String(100) | NULL | -- | Yes | |
| status | String(20) | active | -- | Yes | active/archived |
| tech_stack | Text | NULL | -- | -- | JSON array as string |
| created_at | DateTime | utcnow | -- | -- | |
| updated_at | DateTime | utcnow | -- | -- | ON UPDATE |
| deleted_at | DateTime | NULL | -- | -- | soft-delete |

Relationships: settings (1:1 ProjectSettings), members (1:N ProjectMember), access_logs (1:N ProjectAccessLog)

### aidp_project_members
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| project_id | Integer | NOT NULL | aidp_projects.id | Yes |
| user_id | String(100) | NOT NULL | -- | Yes |
| role | String(20) | viewer | -- | -- |
| invited_by | String(100) | NULL | -- | -- |
| joined_at | DateTime | utcnow | -- | -- |

Roles: admin, editor, viewer

### aidp_project_settings (1:1 with project)
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| project_id | Integer | NOT NULL | aidp_projects.id | Yes (unique) |
| instructions | Text | NULL | -- | -- |
| config | Text | NULL | -- | -- |
| integrations | Text | NULL | -- | -- |

### aidp_project_access_logs
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| project_id | Integer | NOT NULL | aidp_projects.id | Yes |
| user_id | String(100) | NULL | -- | -- |
| action | String(50) | NOT NULL | -- | -- |
| detail | Text | NULL | -- | -- |
| ip_address | String(45) | NULL | -- | -- |
| created_at | DateTime | utcnow | -- | Yes |

### aidp_project_init_tasks
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| project_id | Integer | NOT NULL | aidp_projects.id | Yes |
| task_id | String(64) | NOT NULL | -- | -- |
| status | String(20) | pending | -- | -- |
| started_at | DateTime | NULL | -- | -- |
| completed_at | DateTime | NULL | -- | -- |
| error_msg | Text | NULL | -- | -- |
| metadata_json | Text | NULL | -- | -- |
| created_at | DateTime | utcnow | -- | -- |

Task IDs: code_index, doc_import, tech_analysis, official_docs, file_watcher, git_hook, rules_extract, agent_setup, mcp_register
Status values: pending, running, completed, skipped, failed

### aidp_project_mappings (Cross-tool ID mapping)
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| controller_project_id | Integer | NOT NULL | aidp_projects.id | Yes |
| tool_name | String(64) | NOT NULL | -- | -- |
| tool_project_id | String(128) | NOT NULL | -- | -- |
| local_path | String(1024) | NULL | -- | -- |
| created_at | DateTime | utcnow | -- | -- |
## 2. Knowledge Tables

### aidp_knowledge_bases
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| user_id | String(100) | NULL | -- | Yes |
| name | String(200) | NOT NULL | -- | -- |
| slug | String(128) | NULL | -- | Yes |
| description | Text | NULL | -- | -- |
| kb_level | String(32) | project | -- | -- |
| parent_id | String(36) | NULL | aidp_knowledge_bases.id | Yes |
| domains | Text | [] | -- | -- |
| keywords | Text | [] | -- | -- |
| tech_stack | Text | [] | -- | -- |
| visibility | String(20) | private | -- | -- |
| chunking_strategy | String(50) | fixed | -- | -- |
| chunk_size | Integer | 500 | -- | -- |
| chunk_overlap | Integer | 50 | -- | -- |
| embedding_model | String(128) | text-embedding-3-small | -- | -- |
| document_count | Integer | 0 | -- | -- |
| total_chunks | Integer | 0 | -- | -- |
| extra_data | Text | {} | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | Yes |
| updated_at | DateTime(tz) | utcnow | -- | -- |
| deleted_at | DateTime(tz) | NULL | -- | -- |

kb_level: framework, template, project | visibility: private, team, public

### aidp_knowledge_documents
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| base_id | String(36) | NULL | aidp_knowledge_bases.id | Yes |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| user_id | String(100) | NULL | -- | Yes |
| title | String(500) | NOT NULL | -- | -- |
| source_type | String(50) | manual | -- | -- |
| source_uri | String(1000) | NULL | -- | -- |
| content | Text | NULL | -- | -- |
| mime_type | String(100) | NULL | -- | -- |
| file_size | Integer | 0 | -- | -- |
| chunk_count | Integer | 0 | -- | -- |
| category | String(100) | NULL | -- | Yes |
| embedding | Text | NULL | -- | -- |
| embedding_model | String(128) | NULL | -- | -- |
| tags | Text | [] | -- | -- |
| checksum | String(128) | NULL | -- | -- |
| version | String(128) | v1 | -- | -- |
| index_status | String(20) | pending | -- | Yes |
| summary | Text | NULL | -- | -- |
| visibility | String(20) | private | -- | -- |
| owner_type | String(32) | personal | -- | -- |
| created_by | String(100) | NULL | -- | -- |
| updated_by | String(100) | NULL | -- | -- |
| processing_status | String(20) | pending | -- | Yes |
| extra_data | Text | {} | -- | -- |
| promotion_status | String(20) | none | -- | Yes |
| promotion_report | Text | NULL | -- | -- |
| promotion_source_id | String(36) | NULL | -- | Yes |
| promotion_source_scope | String(20) | NULL | -- | -- |
| promotion_promoted_at | DateTime(tz) | NULL | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | Yes |
| updated_at | DateTime(tz) | utcnow | -- | -- |
| deleted_at | DateTime(tz) | NULL | -- | -- |

promotion_status: none, pending, reviewed, promoted, rejected, rolled_back
index_status: pending, indexing, indexed, error

### aidp_document_chunks
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| document_id | String(36) | NOT NULL | aidp_knowledge_documents.id | Yes |
| base_id | String(36) | NOT NULL | aidp_knowledge_bases.id | Yes |
| chunk_index | Integer | NOT NULL | -- | -- |
| content | Text | NOT NULL | -- | -- |
| embedding | Text | NULL | -- | -- |
| token_count | Integer | 0 | -- | -- |
| extra_data | Text | {} | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |

### aidp_knowledge_search_logs
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| base_id | String(36) | NULL | -- | Yes |
| project_id | Integer | NULL | -- | Yes |
| user_id | String(100) | NULL | -- | -- |
| query | Text | NOT NULL | -- | -- |
| results_count | Integer | 0 | -- | -- |
| top_score | Float | NULL | -- | -- |
| duration_ms | Float | NULL | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | Yes |

### aidp_project_knowledge_bindings
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| project_id | String(128) | NOT NULL | -- | Yes |
| knowledge_base_id | String(36) | NOT NULL | aidp_knowledge_bases.id | Yes |
| binding_type | String(32) | auto_matched | -- | -- |
| priority | Integer | 0 | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |

binding_type: explicit, auto_matched

### aidp_document_templates
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| name | String(200) | NOT NULL | -- | Yes |
| category | String(50) | NOT NULL | -- | Yes |
| content | Text | NOT NULL | -- | -- |
| variables | Text | [] | -- | -- |
| scope | String(20) | global | -- | Yes |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| user_id | String(100) | NULL | -- | Yes |
| description | Text | NULL | -- | -- |
| is_active | Boolean | TRUE | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |
| updated_at | DateTime(tz) | utcnow | -- | -- |

category: research, prd, arch, plan, dev, test, ops, meeting | scope: global, project
## 3. Memory Tables

### aidp_memory_entries
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| user_id | String(100) | NULL | -- | Yes |
| category | String(50) | other | -- | Yes |
| memory_tier | String(20) | semantic | -- | Yes |
| title | String(200) | NOT NULL | -- | -- |
| content | Text | NOT NULL | -- | -- |
| embedding | Text | NULL | -- | -- |
| embedding_model | String(128) | text-embedding-3-small | -- | -- |
| parent_id | String(36) | NULL | aidp_memory_entries.id | Yes |
| confidence_score | Float | 1.0 | -- | -- |
| ai_suggested | Boolean | FALSE | -- | Yes |
| ai_review_status | String(20) | approved | -- | -- |
| ai_review_comment | Text | NULL | -- | -- |
| merged_from | Text | NULL | -- | -- |
| access_count | Integer | 0 | -- | -- |
| last_accessed_at | DateTime(tz) | NULL | -- | -- |
| source_type | String(50) | manual | -- | -- |
| source_uri | String(500) | NULL | -- | -- |
| extra_data | Text | {} | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | Yes |
| updated_at | DateTime(tz) | utcnow | -- | -- |
| deleted_at | DateTime(tz) | NULL | -- | -- |

memory_tier: semantic, episodic, procedural | source_type: manual, import, ai_generated

### aidp_memory_relations
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| source_id | String(36) | NOT NULL | aidp_memory_entries.id | Yes |
| target_id | String(36) | NOT NULL | aidp_memory_entries.id | Yes |
| relation_type | String(50) | NOT NULL | -- | Yes |
| strength | Float | 1.0 | -- | -- |
| description | Text | NULL | -- | -- |
| extra_data | Text | {} | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |
| updated_at | DateTime(tz) | utcnow | -- | -- |

### aidp_memory_access_logs
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| memory_id | String(36) | NOT NULL | aidp_memory_entries.id | Yes |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| action | String(50) | NOT NULL | -- | -- |
| query | Text | NULL | -- | -- |
| user_id | String(100) | NULL | -- | -- |
| ip_address | String(45) | NULL | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | Yes |

### aidp_context_packages
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| name | String(200) | NOT NULL | -- | -- |
| description | Text | NULL | -- | -- |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| user_id | String(100) | NULL | -- | Yes |
| created_by | String(100) | NULL | -- | -- |
| memory_ids | Text | [] | -- | -- |
| generated_context | Text | NULL | -- | -- |
| total_tokens | Integer | 0 | -- | -- |
| is_template | Boolean | FALSE | -- | Yes |
| usage_count | Integer | 0 | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |
| updated_at | DateTime(tz) | utcnow | -- | -- |

## 4. Skills Tables

### aidp_skill_groups
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| name | String(100) | NOT NULL | -- | -- |
| description | Text | NULL | -- | -- |
| scope | String(20) | personal | -- | Yes |
| parent_id | String(36) | NULL | aidp_skill_groups.id | Yes |
| user_id | String(100) | NULL | -- | Yes |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| sort_order | Integer | 0 | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |
| updated_at | DateTime(tz) | utcnow | -- | -- |

scope: global, personal, project

### aidp_skills
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| name | String(200) | NOT NULL | -- | Yes |
| description | Text | NULL | -- | -- |
| scope | String(20) | personal | -- | Yes |
| instruction | Text | NULL | -- | -- |
| content | Text | NULL | -- | -- |
| tags | Text | [] | -- | -- |
| version | Integer | 1 | -- | -- |
| dependencies | Text | [] | -- | -- |
| exec_config | Text | {} | -- | -- |
| embedding | Text | NULL | -- | -- |
| embedding_model | String(128) | text-embedding-3-small | -- | -- |
| review_status | String(20) | approved | -- | Yes |
| review_report | Text | NULL | -- | -- |
| review_log | Text | [] | -- | -- |
| allow_risk_patterns | Text | [] | -- | -- |
| allowed_roles | Text | [] | -- | -- |
| sensitive | Boolean | FALSE | -- | -- |
| promotion_status | String(20) | none | -- | Yes |
| promotion_report | Text | NULL | -- | -- |
| promotion_source_id | String(36) | NULL | -- | Yes |
| promotion_source_scope | String(20) | NULL | -- | -- |
| promotion_promoted_at | DateTime(tz) | NULL | -- | -- |
| weight_config | Text | {} | -- | -- |
| examples | Text | [] | -- | -- |
| source_url | String(500) | NULL | -- | -- |
| source_type | String(50) | manual | -- | -- |
| source_id | String(200) | NULL | -- | -- |
| group_id | String(36) | NULL | aidp_skill_groups.id | Yes |
| user_id | String(100) | NULL | -- | Yes |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| extra_data | Text | {} | -- | -- |
| access_count | Integer | 0 | -- | -- |
| last_accessed_at | DateTime(tz) | NULL | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | Yes |
| updated_at | DateTime(tz) | utcnow | -- | -- |
| deleted_at | DateTime(tz) | NULL | -- | -- |

### aidp_skill_files
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| skill_id | String(36) | NOT NULL | aidp_skills.id CASCADE | Yes |
| path | String(500) | NOT NULL | -- | -- |
| content | Text | NULL | -- | -- |
| language | String(50) | NULL | -- | -- |
| is_entry | Boolean | FALSE | -- | -- |
| sort_order | Integer | 0 | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |
| updated_at | DateTime(tz) | utcnow | -- | -- |

### aidp_skill_evolutions
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| skill_id | String(36) | NOT NULL | aidp_skills.id CASCADE | Yes |
| old_version | Integer | NULL | -- | -- |
| old_content | Text | NULL | -- | -- |
| new_content | Text | NOT NULL | -- | -- |
| diff_summary | Text | NULL | -- | -- |
| trigger_reason | String(100) | manual | -- | -- |
| status | String(20) | pending | -- | -- |
| rollback_to | Integer | NULL | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |

trigger_reason: manual, ai_suggested, auto | status: pending, approved, rejected
## 5. Rules Tables

### aidp_rule_groups
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| name | String(100) | NOT NULL | -- | -- |
| description | Text | NULL | -- | -- |
| scope | String(20) | personal | -- | Yes |
| parent_id | String(36) | NULL | aidp_rule_groups.id | Yes |
| user_id | String(100) | NULL | -- | Yes |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| sort_order | Integer | 0 | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |
| updated_at | DateTime(tz) | utcnow | -- | -- |

### aidp_rules
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| name | String(200) | NOT NULL | -- | Yes |
| description | Text | NULL | -- | -- |
| content | Text | NOT NULL | -- | -- |
| category | String(50) | code_style | -- | Yes |
| severity | String(20) | medium | -- | -- |
| priority | Integer | 0 | -- | Yes |
| version | Integer | 1 | -- | -- |
| scope | String(20) | personal | -- | Yes |
| pattern | Text | NULL | -- | -- |
| auto_fix | Text | NULL | -- | -- |
| allowed_roles | Text | [] | -- | -- |
| tags | Text | [] | -- | -- |
| review_status | String(20) | approved | -- | Yes |
| review_report | Text | NULL | -- | -- |
| review_log | Text | [] | -- | -- |
| promotion_status | String(20) | none | -- | Yes |
| promotion_report | Text | NULL | -- | -- |
| promotion_source_id | String(36) | NULL | -- | Yes |
| promotion_source_scope | String(20) | NULL | -- | -- |
| promotion_promoted_at | DateTime(tz) | NULL | -- | -- |
| embedding | Text | NULL | -- | -- |
| embedding_model | String(128) | text-embedding-3-small | -- | -- |
| group_id | String(36) | NULL | aidp_rule_groups.id | Yes |
| user_id | String(100) | NULL | -- | Yes |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| is_active | Boolean | TRUE | -- | Yes |
| access_count | Integer | 0 | -- | -- |
| extra_data | Text | {} | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | Yes |
| updated_at | DateTime(tz) | utcnow | -- | -- |
| deleted_at | DateTime(tz) | NULL | -- | -- |

category: code_style, security, performance, naming, architecture
severity: low, medium, high, critical

## 6. Agents Tables

### aidp_agents
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| name | String(200) | NOT NULL | -- | Yes |
| role | String(100) | NULL | -- | -- |
| instructions | Text | NULL | -- | -- |
| scope | String(20) | personal | -- | Yes |
| parent_agent_id | String(36) | NULL | aidp_agents.id | Yes |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| user_id | String(100) | NULL | -- | Yes |
| config | Text | {} | -- | -- |
| extra_data | Text | {} | -- | -- |
| sort_order | Integer | 0 | -- | -- |
| is_active | Boolean | TRUE | -- | Yes |
| is_template | Boolean | FALSE | -- | Yes |
| created_at | DateTime(tz) | utcnow | -- | Yes |
| updated_at | DateTime(tz) | utcnow | -- | -- |
| deleted_at | DateTime(tz) | NULL | -- | -- |

M2M join tables:
- aidp_agent_skills: agent_id (String(36) FK aidp_agents.id CASCADE PK) + skill_id (String(36) FK aidp_skills.id CASCADE PK)
- aidp_agent_rules: agent_id (String(36) FK aidp_agents.id CASCADE PK) + rule_id (String(36) FK aidp_rules.id CASCADE PK)
- aidp_agent_knowledge: agent_id (String(36) FK aidp_agents.id CASCADE PK) + knowledge_base_id (String(36) FK aidp_knowledge_bases.id CASCADE PK)
## 7. Assets Tables

### aidp_assets
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| user_id | String(100) | NULL | -- | Yes |
| title | String(200) | NOT NULL | -- | Yes |
| description | Text | NULL | -- | -- |
| asset_type | String(50) | snippet | -- | Yes |
| language | String(50) | NULL | -- | Yes |
| format | String(50) | text | -- | -- |
| visibility | String(20) | project | -- | Yes |
| content | Text | NOT NULL | -- | -- |
| variables | Text | {} | -- | -- |
| extra_data | Text | {} | -- | -- |
| created_by | String(100) | NULL | -- | -- |
| updated_by | String(100) | NULL | -- | -- |
| access_count | Integer | 0 | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | Yes |
| updated_at | DateTime(tz) | utcnow | -- | -- |
| deleted_at | DateTime(tz) | NULL | -- | -- |

visibility: private, project, team, public

### aidp_asset_tags
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| asset_id | String(36) | NOT NULL | aidp_assets.id CASCADE | Yes |
| tag | String(100) | NOT NULL | -- | Yes |

## 8. Workflows Tables

### aidp_workflows
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| name | String(200) | NOT NULL | -- | Yes |
| description | Text | NULL | -- | -- |
| category | String(50) | development | -- | Yes |
| trigger | String(50) | manual | -- | Yes |
| trigger_config | Text | {} | -- | -- |
| variables | Text | [] | -- | -- |
| extra_data | Text | {} | -- | -- |
| project_id | Integer | NULL | aidp_projects.id | Yes |
| user_id | String(100) | NULL | -- | Yes |
| is_active | Boolean | TRUE | -- | Yes |
| is_template | Boolean | FALSE | -- | Yes |
| version | Integer | 1 | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |
| updated_at | DateTime(tz) | utcnow | -- | -- |
| deleted_at | DateTime(tz) | NULL | -- | -- |

category: development, testing, deployment, review
trigger: manual, webhook, schedule, event

### aidp_workflow_steps
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| workflow_id | String(36) | NOT NULL | aidp_workflows.id CASCADE | Yes |
| name | String(200) | NOT NULL | -- | -- |
| order | Integer | NOT NULL | -- | -- |
| agent_id | String(36) | NULL | aidp_agents.id | -- |
| skill_ids | Text | [] | -- | -- |
| rule_ids | Text | [] | -- | -- |
| conditions | Text | {} | -- | -- |
| input_mapping | Text | {} | -- | -- |
| output_mapping | Text | {} | -- | -- |
| timeout | Integer | 300 | -- | -- |
| on_success | Text | {} | -- | -- |
| on_fail | Text | {} | -- | -- |
| extra_data | Text | {} | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |
| updated_at | DateTime(tz) | utcnow | -- | -- |

### aidp_workflow_executions
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| workflow_id | String(36) | NOT NULL | aidp_workflows.id | Yes |
| status | String(20) | running | -- | Yes |
| trigger_type | String(50) | manual | -- | -- |
| trigger_data | Text | {} | -- | -- |
| current_step | Integer | 0 | -- | -- |
| variables | Text | {} | -- | -- |
| started_at | DateTime(tz) | utcnow | -- | -- |
| completed_at | DateTime(tz) | NULL | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |

status: running, completed, failed, cancelled

### aidp_workflow_execution_steps
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| execution_id | String(36) | NOT NULL | aidp_workflow_executions.id | Yes |
| step_id | String(36) | NULL | aidp_workflow_steps.id | -- |
| step_name | String(200) | NULL | -- | -- |
| step_order | Integer | NULL | -- | -- |
| status | String(20) | pending | -- | -- |
| started_at | DateTime(tz) | NULL | -- | -- |
| completed_at | DateTime(tz) | NULL | -- | -- |
| duration_ms | Integer | NULL | -- | -- |
| input_data | Text | {} | -- | -- |
| output_data | Text | {} | -- | -- |
| error | Text | NULL | -- | -- |
| retry_count | Integer | 0 | -- | -- |
| created_at | DateTime(tz) | utcnow | -- | -- |

status: pending, running, completed, failed, skipped
## 9. Models Table

### aidp_models (Unified LLM model registry)
| Column | Type | Default | FK | Index | Comment |
|--------|------|---------|----|-------|---------|
| id | Integer | autoincrement PK | -- | PK | |
| name | String(128) | NOT NULL | -- | -- | Display name |
| provider | String(64) | NOT NULL | -- | -- | OpenAI / DeepSeek / Local |
| model_name | String(256) | NOT NULL | -- | -- | Actual model ID |
| api_base | String(512) | NULL | -- | -- | API base URL |
| api_key | String(512) | NULL | -- | -- | Encrypted API key |
| task_types | JSON | [] | -- | -- | [chat, embedding, code] |
| status | String(32) | active | -- | -- | |
| priority | Integer | 0 | -- | -- | Higher = preferred |
| max_tokens | Integer | 4096 | -- | -- | Max output tokens |
| temperature | Float | 0.7 | -- | -- | 0=precise, 1=creative |
| created_at | DateTime | utcnow | -- | -- | |
| updated_at | DateTime | utcnow | -- | -- | ON UPDATE |

## 10. Core Tables (auth, registry, audit)

### users
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| username | String(64) | NOT NULL unique | -- | Yes |
| password_hash | String(255) | NOT NULL | -- | -- |
| email | String(255) | NULL unique | -- | Yes |
| nickname | String(128) | NULL | -- | -- |
| avatar_url | Text | NULL | -- | -- |
| role | String(32) | user | -- | -- |
| status | String(32) | active | -- | -- |
| is_verified | Boolean | FALSE | -- | -- |
| last_login_at | DateTime | NULL | -- | -- |
| created_at | DateTime | utcnow | -- | -- |
| updated_at | DateTime | utcnow | -- | -- |

Roles: super_admin, admin, developer, user, readonly
Status: active, inactive, suspended, pending
Relationships: sessions (1:N UserSession), api_keys (1:N ApiKey), audit_logs (1:N AuditLog)

### user_sessions
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| user_id | String(36) | NOT NULL | users.id CASCADE | Yes |
| session_token | String(255) | NOT NULL unique | -- | Yes |
| refresh_token | String(255) | NULL | -- | -- |
| ip_address | String(45) | NULL | -- | -- |
| user_agent | Text | NULL | -- | -- |
| expires_at | DateTime | NOT NULL | -- | -- |
| created_at | DateTime | utcnow | -- | -- |
| last_activity_at | DateTime | utcnow | -- | -- |

### login_logs
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| user_id | String(36) | NULL | users.id | Yes |
| username | String(64) | NULL | -- | -- |
| action | String(32) | NOT NULL | -- | -- |
| ip_address | String(45) | NULL | -- | -- |
| user_agent | Text | NULL | -- | -- |
| success | Boolean | FALSE | -- | -- |
| fail_reason | Text | NULL | -- | -- |
| created_at | DateTime | utcnow | -- | -- |

Actions: login, logout, login_failed, token_refresh, password_changed

### permissions
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| code | String(64) | NOT NULL unique | -- | Yes |
| name | String(128) | NOT NULL | -- | -- |
| description | Text | NULL | -- | -- |
| resource_type | String(32) | NULL | -- | -- |
| action | String(32) | NULL | -- | -- |
| created_at | DateTime | utcnow | -- | -- |

### role_permissions (M2M)
| Column | Type | FK |
|--------|------|----|
| role | String(32) PK | -- |
| permission_id | String(36) PK | permissions.id CASCADE |

### system_settings
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| key | String(128) | NOT NULL unique | -- | Yes |
| value | JSON | NULL | -- | -- |
| description | Text | NULL | -- | -- |
| is_encrypted | Boolean | FALSE | -- | -- |
| updated_by | String(36) | NULL | users.id | -- |
| updated_at | DateTime | utcnow | -- | -- |

### api_keys
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| user_id | String(36) | NOT NULL | users.id CASCADE | Yes |
| label | String(128) | NULL | -- | -- |
| key_hash | String(255) | NOT NULL unique | -- | Yes |
| key_preview | String(20) | NULL | -- | -- |
| raw_key | String(255) | NULL | -- | -- |
| scopes | JSON | [] | -- | -- |
| rate_limit_req_per_min | Integer | 60 | -- | -- |
| expires_at | DateTime | NULL | -- | -- |
| last_used_at | DateTime | NULL | -- | -- |
| is_active | Boolean | TRUE | -- | -- |
| created_at | DateTime | utcnow | -- | -- |

### audit_logs
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| user_id | String(36) | NULL | users.id | Yes |
| action | String(64) | NOT NULL | -- | Yes |
| resource_type | String(64) | NULL | -- | Yes |
| resource_id | String(64) | NULL | -- | Yes |
| resource_name | String(255) | NULL | -- | -- |
| old_values | JSON | NULL | -- | -- |
| new_values | JSON | NULL | -- | -- |
| ip_address | String(45) | NULL | -- | -- |
| user_agent | Text | NULL | -- | -- |
| created_at | DateTime | utcnow | -- | Yes |

Composite indexes:
- idx_audit_logs_user_action (user_id, action)
- idx_audit_logs_resource (resource_type, resource_id)
- idx_audit_logs_created (created_at)

### tool_registry
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| name | String(256) | NOT NULL unique | -- | Yes |
| display_name | String(256) | NULL | -- | -- |
| description | Text | NULL | -- | -- |
| version | String(32) | NULL | -- | -- |
| endpoint | String(512) | NOT NULL | -- | -- |
| status | String(32) | registered | -- | -- |
| last_health_check | DateTime | NULL | -- | -- |
| capabilities | JSON | NULL | -- | -- |
| created_at | DateTime | utcnow | -- | -- |
| updated_at | DateTime | utcnow | -- | -- |

status values: registered, healthy, unhealthy, unreachable, disabled

### tool_invocation (spelled tool_invocations in actual usage)
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| tool_name | String(256) | NOT NULL | -- | Yes |
| capability | String(256) | NULL | -- | -- |
| arguments | JSON | NULL | -- | -- |
| result | JSON | NULL | -- | -- |
| status | String(32) | NULL | -- | -- |
| duration_ms | Integer | NULL | -- | -- |
| error | Text | NULL | -- | -- |
| user_id | Integer | NULL | -- | -- |
| created_at | DateTime | utcnow | -- | -- |

Note: The ORM model uses __tablename__ = tool_invocation (no trailing s).

## 11. Other Tables

### agent_instructions
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| project_id | Integer | NOT NULL (0) | -- | -- |
| agent_type | String(100) | main | -- | -- |
| role | Text | NULL | -- | -- |
| constraints | JSON | {} | -- | -- |
| rules | JSON | [] | -- | -- |
| created_at | DateTime | now() | -- | -- |
| updated_at | DateTime | now() | -- | -- |

### review_queue
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| document_id | Integer | NULL | -- | -- |
| user_id | Integer | NULL | -- | -- |
| action | String(64) | NOT NULL | -- | -- |
| content | Text | NULL | -- | -- |
| status | String(32) | pending | -- | -- |
| review_comment | Text | NULL | -- | -- |
| reviewed_by | Integer | NULL | -- | -- |
| reviewed_at | DateTime | NULL | -- | -- |
| created_at | DateTime | now() | -- | -- |

### aidp_sandbox_executions
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | String(36) | UUID PK | -- | PK |
| user_id | String(100) | NULL | -- | Yes |
| language | String(32) | NOT NULL | -- | Yes |
| code | Text | NOT NULL | -- | -- |
| stdin | Text | NULL | -- | -- |
| stdout | Text | NULL | -- | -- |
| stderr | Text | NULL | -- | -- |
| exit_code | Integer | NULL | -- | -- |
| timed_out | Boolean | FALSE | -- | -- |
| created_at | DateTime | utcnow | -- | -- |
| duration_ms | Integer | NULL | -- | -- |

## 12. Legacy Tables

### app_projects (legacy)
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| name | String(256) | NOT NULL | -- | -- |
| description | String(1024) | NULL | -- | -- |
| project_type | String(256) | NULL | -- | -- |
| owner_id | String(128) | NULL | -- | -- |
| created_at | DateTime | now() | -- | -- |

### app_project_members (legacy)
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| project_id | Integer | NULL | app_projects.id | -- |
| user_id | String(128) | NULL | -- | -- |
| role | String(32) | member | -- | -- |
| created_at | DateTime | now() | -- | -- |

### app_project_configs (legacy)
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| project_id | Integer | NULL | app_projects.id | -- |
| env_type | String(32) | NOT NULL | -- | -- |
| config_key | String(256) | NOT NULL | -- | -- |
| config_value | String(512) | NULL | -- | -- |
| created_at | DateTime | now() | -- | -- |

### projects (legacy, from auth_models)
| Column | Type | Default | FK | Index |
|--------|------|---------|----|-------|
| id | Integer | autoincrement PK | -- | PK |
| name | String(128) | NOT NULL unique | -- | Yes |
| description | Text | NULL | -- | -- |
| tech_stack | String(256) | NULL | -- | -- |
| nas_path | String(512) | NULL | -- | -- |
| docs | JSON | [] | -- | -- |
| key_files | JSON | [] | -- | -- |
| architecture_summary | Text | NULL | -- | -- |
| is_active | Boolean | TRUE | -- | -- |
| created_at | DateTime | now() | -- | -- |
| updated_at | DateTime | now() | -- | -- |
