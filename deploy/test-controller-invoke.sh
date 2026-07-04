#!/bin/bash
# Test controller invoke

echo "=== Test quality check via controller ==="
curl -s -X POST http://127.0.0.1:8883/api/tools/quality-tool/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "quality.check", "arguments": {"code": "x = 1\nprint(x)", "checkType": "lint"}}'
echo ""

echo "=== Test memory search via controller ==="
curl -s -X POST http://127.0.0.1:8883/api/tools/memory-tool/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "memory.search", "arguments": {"project": "test", "query": "test"}}'
echo ""

echo "=== Test sandbox execute via controller ==="
curl -s -X POST http://127.0.0.1:8883/api/tools/sandbox-tool/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "sandbox.execute", "arguments": {"code": "print(42)", "language": "python"}}'
echo ""
