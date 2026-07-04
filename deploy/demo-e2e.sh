#!/bin/bash
# AIDP End-to-End Demo: Programming Closed Loop

echo "=========================================="
echo "  AIDP Programming Closed Loop Demo"
echo "=========================================="
echo ""

echo "[Step 1] User Request"
echo "Task: Write a Python function to calculate factorial"
echo ""

echo "[Step 2] Generate Code (via controller → sandbox-tool)"
curl -s -X POST http://127.0.0.1:8883/api/tools/sandbox-tool/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "sandbox.execute", "arguments": {"code": "def factorial(n):\n    if n < 0:\n        raise ValueError(\"n must be non-negative\")\n    if n == 0 or n == 1:\n        return 1\n    result = 1\n    for i in range(2, n + 1):\n        result *= i\n    return result\n\nprint(factorial(5))\nprint(factorial(0))\nprint(factorial(10))", "language": "python"}}' | python3 -m json.tool
echo ""

echo "[Step 3] Quality Check (via controller → quality-tool)"
curl -s -X POST http://127.0.0.1:8883/api/tools/quality-tool/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "quality.check", "arguments": {"code": "def factorial(n):\n    if n < 0:\n        raise ValueError(\"n must be non-negative\")\n    if n == 0 or n == 1:\n        return 1\n    result = 1\n    for i in range(2, n + 1):\n        result *= i\n    return result", "checkType": "all"}}' | python3 -m json.tool
echo ""

echo "[Step 4] Store Result (via controller → memory-tool)"
curl -s -X POST http://127.0.0.1:8883/api/tools/memory-tool/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "memory.create", "arguments": {"project": "aidp-demo", "category": "code", "title": "factorial function", "content": "def factorial(n): if n < 0: raise ValueError; if n == 0 or n == 1: return 1; result = 1; for i in range(2, n + 1): result *= i; return result", "tags": "python,math,demo"}}' | python3 -m json.tool
echo ""

echo "[Step 5] Verify Memory Retrieval"
curl -s -X POST http://127.0.0.1:8883/api/tools/memory-tool/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability": "memory.search", "arguments": {"project": "aidp-demo", "query": "factorial"}}' | python3 -m json.tool
echo ""

echo "=========================================="
echo "  Demo Complete!"
echo "=========================================="
