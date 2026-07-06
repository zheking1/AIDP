#!/bin/bash
# Test real-time file sync

echo "=== Creating test file ==="
echo "# Test file for real-time sync" > /home/docker/AI-Code/test_realtime_sync.txt
echo "Created: test_realtime_sync.txt"

echo ""
echo "=== Waiting 3 seconds for sync ==="
sleep 3

echo ""
echo "=== Checking file-watcher events ==="
curl -s http://127.0.0.1:18091/api/watcher/projects/1/events

echo ""
echo "=== Checking code-index for new file ==="
curl -s "http://127.0.0.1:18086/api/search?query=test_realtime_sync&project_id=1" | head -c 200

echo ""
echo "=== Cleaning up ==="
rm -f /home/docker/AI-Code/test_realtime_sync.txt
echo "Done"
