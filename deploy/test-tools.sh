#!/bin/bash
# Test AIDP tools - POST requests

echo "=== Testing knowledge-tool search ==="
curl -s -X POST http://127.0.0.1:18081/api/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
echo ""

echo "=== Registering tools with controller ==="
# Register knowledge-tool
curl -s -X POST http://127.0.0.1:8883/api/tools \
  -H "Content-Type: application/json" \
  -d '{"name": "knowledge-tool", "endpoint": "http://127.0.0.1:18081", "displayName": "Knowledge Tool"}'
echo ""

# Register sandbox-tool
curl -s -X POST http://127.0.0.1:8883/api/tools \
  -H "Content-Type: application/json" \
  -d '{"name": "sandbox-tool", "endpoint": "http://127.0.0.1:18083", "displayName": "Sandbox Tool"}'
echo ""

# Register quality-tool
curl -s -X POST http://127.0.0.1:8883/api/tools \
  -H "Content-Type: application/json" \
  -d '{"name": "quality-tool", "endpoint": "http://127.0.0.1:18084", "displayName": "Quality Tool"}'
echo ""

# Register memory-tool
curl -s -X POST http://127.0.0.1:8883/api/tools \
  -H "Content-Type: application/json" \
  -d '{"name": "memory-tool", "endpoint": "http://127.0.0.1:18085", "displayName": "Memory Tool"}'
echo ""

echo "=== Listing registered tools ==="
curl -s http://127.0.0.1:8883/api/tools
echo ""

echo "=== Testing controller invoke ==="
curl -s -X POST http://127.0.0.1:8883/api/tools/sandbox-tool/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "sandbox.execute", "arguments": {"code": "print(42)", "language": "python"}}'
echo ""
