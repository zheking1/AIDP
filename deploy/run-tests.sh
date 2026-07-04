#!/bin/bash
# AIDP Test Runner
# Automatically cleans up test data before running tests

echo "=== AIDP Test Runner ==="
echo ""

# Step 1: Clear test data
echo "[Step 1] Clearing test data..."
/home/docker/AI-Code/clear-test-data.sh --confirm
echo ""

# Step 2: Run tests
echo "[Step 2] Running tests..."
cd /home/docker/AI-Code/SkillRouter

# Check if pytest is installed
if command -v pytest &> /dev/null; then
    pytest tests/ -v --tb=short
else
    echo "pytest not installed, running basic health checks..."
    echo ""
    
    echo "Checking SkillRouter..."
    curl -sf http://127.0.0.1:8788/health && echo " OK" || echo " FAILED"
    
    echo "Checking knowledge-tool..."
    curl -sf http://127.0.0.1:18081/health && echo " OK" || echo " FAILED"
    
    echo "Checking sandbox-tool..."
    curl -sf http://127.0.0.1:18083/health && echo " OK" || echo " FAILED"
    
    echo "Checking quality-tool..."
    curl -sf http://127.0.0.1:18084/health && echo " OK" || echo " FAILED"
    
    echo "Checking memory-tool..."
    curl -sf http://127.0.0.1:18085/health && echo " OK" || echo " FAILED"
    
    echo "Checking controller..."
    curl -sf http://127.0.0.1:8883/health && echo " OK" || echo " FAILED"
fi

echo ""
echo "=== Tests Complete ==="
