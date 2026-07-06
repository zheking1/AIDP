#!/bin/bash
# Add openCode to file-watcher

echo "=== Adding openCode to file-watcher ==="
curl -X POST http://127.0.0.1:18087/api/watcher/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "project_name": "openCode",
    "local_path": "/home/docker/AI-Code",
    "code_index_project_id": 1,
    "ignored_dirs": [".git", "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vscode", "data"],
    "ignored_patterns": ["*.pyc", "*.log", "*.tar.gz"]
  }'

echo ""
echo "=== Listing watched projects ==="
curl -s http://127.0.0.1:18087/api/watcher/projects

echo ""
echo "=== Getting watcher stats ==="
curl -s http://127.0.0.1:18087/api/watcher/stats
