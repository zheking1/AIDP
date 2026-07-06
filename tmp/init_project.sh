#!/bin/bash
# Initialize openCode project

curl -X POST http://127.0.0.1:8883/api/projects/init \
  -H 'Content-Type: application/json' \
  -d '{
    "project_name": "openCode",
    "tech_stack": "Python 3.13 + FastAPI + PostgreSQL/SQLite",
    "architecture_summary": "AIDP (AI DevOps Platform) - AI DevOps Platform with staged context pipeline",
    "docs": [],
    "key_files": []
  }'
