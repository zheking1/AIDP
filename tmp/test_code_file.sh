#!/bin/bash
echo "=== Creating test PY file ==="
echo "# test file $(date)" > /watched-projects/test_watcher.py
echo "Created: test_watcher.py"

echo "Waiting 5 seconds..."
sleep 5

echo ""
echo "=== Events ==="
curl -s http://127.0.0.1:18091/api/watcher/projects/1/events

echo ""
echo "=== Stats ==="
curl -s http://127.0.0.1:18091/api/watcher/stats

echo ""
echo "=== Cleanup ==="
rm -f /watched-projects/test_watcher.py
echo "Done"