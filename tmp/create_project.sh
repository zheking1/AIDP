#!/bin/bash
# Create openCode project

curl -X POST http://127.0.0.1:8883/api/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "openCode",
    "description": "AIDP (AI DevOps Platform) - AI DevOps Platform with staged context pipeline",
    "project_type": "ai-platform"
  }'
