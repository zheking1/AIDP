#!/bin/bash
# Test controller MCP

echo "=== Test MCP initialize ==="
curl -s -X POST http://127.0.0.1:8883/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "0.1.0"}}, "id": 1}'
echo ""

echo "=== Test MCP tools/list ==="
curl -s -X POST http://127.0.0.1:8883/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2}'
echo ""
