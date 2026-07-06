#!/bin/bash
# Add openCode to file-watcher via tool invoke API

echo "=== Adding openCode via tool invoke ==="
curl -X POST http://127.0.0.1:18087/tool/invoke \
  -H 'Content-Type: application/json' \
  -d '{
    "capability": "watcher.add_project",
    "arguments": {
      "project_name": "openCode",
      "local_path": "/home/docker/AI-Code",
      "code_index_project_id": 1,
      "ignored_dirs": [".git", "node_modules", "__pycache__", ".venv", "data"],
      "ignored_patterns": ["*.pyc", "*.log", "*.tar.gz"]
    }
  }'

echo ""
echo "=== List projects ==="
curl -X POST http://127.0.0.1:18087/tool/invoke \
  -H 'Content-Type: application/json' \
  -d '{
    "capability": "watcher.list_projects",
    "arguments": {}
  }'
