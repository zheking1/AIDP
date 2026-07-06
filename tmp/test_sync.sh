#!/bin/bash
# Test real-time sync by creating a test file

echo "=== Creating test file ==="
echo "# Test file created at $(date)" > /home/docker/AI-Code/test_watcher.txt
echo "File created: test_watcher.txt"

echo ""
echo "=== Waiting 2 seconds for file-watcher to detect change ==="
sleep 2

echo ""
echo "=== Checking file-watcher events ==="
curl -s http://127.0.0.1:18087/api/watcher/projects/1/events 2>/dev/null || echo "API not available"

echo ""
echo "=== Checking code-index for new file ==="
curl -s "http://127.0.0.1:18086/api/search?query=test_watcher&project_id=1" 2>/dev/null || echo "API not available"

echo ""
echo "=== Cleaning up test file ==="
rm -f /home/docker/AI-Code/test_watcher.txt
echo "Test complete"
