#!/bin/bash
# Scan openCode project via code-index - correct endpoint

echo "=== Creating project in code-index ==="
curl -X POST http://127.0.0.1:18086/api/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": 1,
    "name": "openCode",
    "description": "AIDP Platform"
  }'

echo ""
echo "=== Scanning project ==="
curl -X POST http://127.0.0.1:18086/api/projects/1/scan \
  -H 'Content-Type: application/json' \
  -d '{
    "local_path": "/home/docker/AI-Code",
    "ignored_patterns": [".git", "node_modules", "__pycache__", "*.pyc", "*.tar.gz", "data"]
  }'
