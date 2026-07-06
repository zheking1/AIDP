#!/bin/bash
# Add openCode via API with correct JSON

curl -X POST http://127.0.0.1:18091/api/watcher/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "project_name": "openCode",
    "local_path": "/home/docker/AI-Code",
    "code_index_project_id": 1,
    "ignored_dirs": [".git", "node_modules", "__pycache__", ".venv", "data"],
    "ignored_patterns": ["*.pyc", "*.log", "*.tar.gz"]
  }'

echo ""
echo "=== List projects ==="
curl -s http://127.0.0.1:18091/api/watcher/projects
