#!/bin/bash
# Scan openCode project via code-index

echo "=== Scanning openCode project ==="
curl -X POST http://127.0.0.1:18086/api/index/scan \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": 1,
    "project_name": "openCode",
    "source_type": "local",
    "local_path": "/home/docker/AI-Code",
    "ignored_dirs": [".git", "node_modules", "__pycache__", ".venv", "venv", "*.pyc", "*.tar.gz"]
  }'
