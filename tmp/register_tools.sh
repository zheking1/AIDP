#!/bin/bash
# Register tools

curl -X POST http://127.0.0.1:8883/api/tools \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "knowledge-tool",
    "endpoint": "http://127.0.0.1:18081",
    "displayName": "Knowledge Tool",
    "description": "Document management"
  }'

echo ""

curl -X POST http://127.0.0.1:8883/api/tools \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "memory-tool",
    "endpoint": "http://127.0.0.1:18085",
    "displayName": "Memory Tool",
    "description": "Project memory storage"
  }'

echo ""

curl -X POST http://127.0.0.1:8883/api/tools \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "sandbox-tool",
    "endpoint": "http://127.0.0.1:18083",
    "displayName": "Sandbox Tool",
    "description": "Code execution sandbox"
  }'

echo ""

curl -X POST http://127.0.0.1:8883/api/tools \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "quality-tool",
    "endpoint": "http://127.0.0.1:18084",
    "displayName": "Quality Tool",
    "description": "Code quality checks"
  }'

echo ""

curl -X POST http://127.0.0.1:8883/api/tools \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "asset-tool",
    "endpoint": "http://127.0.0.1:18082",
    "displayName": "Asset Tool",
    "description": "Code asset management"
  }'

echo ""
echo "Done"
