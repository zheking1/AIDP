#!/bin/bash
# AIDP Health Monitor
# Checks all services and logs status

LOG_FILE="/home/docker/AI-Code/logs/health.log"
mkdir -p /home/docker/AI-Code/logs

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

check_service() {
    local name=$1
    local url=$2
    local status=$(curl -sf "$url" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "$TIMESTAMP,$name,UP"
        return 0
    else
        echo "$TIMESTAMP,$name,DOWN"
        return 1
    fi
}

echo "=== AIDP Health Check: $TIMESTAMP ===" | tee -a "$LOG_FILE"

DOWN_COUNT=0

check_service "knowledge-tool" "http://127.0.0.1:18081/health" | tee -a "$LOG_FILE"
[ $? -ne 0 ] && ((DOWN_COUNT++))

check_service "asset-tool" "http://127.0.0.1:18082/health" | tee -a "$LOG_FILE"
[ $? -ne 0 ] && ((DOWN_COUNT++))

check_service "sandbox-tool" "http://127.0.0.1:18083/health" | tee -a "$LOG_FILE"
[ $? -ne 0 ] && ((DOWN_COUNT++))

check_service "quality-tool" "http://127.0.0.1:18084/health" | tee -a "$LOG_FILE"
[ $? -ne 0 ] && ((DOWN_COUNT++))

check_service "memory-tool" "http://127.0.0.1:18085/health" | tee -a "$LOG_FILE"
[ $? -ne 0 ] && ((DOWN_COUNT++))

check_service "controller" "http://127.0.0.1:8883/health" | tee -a "$LOG_FILE"
[ $? -ne 0 ] && ((DOWN_COUNT++))

# Check SkillRouter
check_service "skillrouter" "http://127.0.0.1:8788/health" | tee -a "$LOG_FILE"
[ $? -ne 0 ] && ((DOWN_COUNT++))

# Check PostgreSQL
PG_STATUS=$(docker ps --filter name=novel-postgres --format '{{.Status}}' 2>/dev/null)
if [[ "$PG_STATUS" == *"Up"* ]]; then
    echo "$TIMESTAMP,postgresql,UP" | tee -a "$LOG_FILE"
else
    echo "$TIMESTAMP,postgresql,DOWN" | tee -a "$LOG_FILE"
    ((DOWN_COUNT++))
fi

# Check Redis
REDIS_STATUS=$(docker ps --filter name=redis --format '{{.Status}}' 2>/dev/null)
if [[ "$REDIS_STATUS" == *"Up"* ]]; then
    echo "$TIMESTAMP,redis,UP" | tee -a "$LOG_FILE"
else
    echo "$TIMESTAMP,redis,DOWN" | tee -a "$LOG_FILE"
    ((DOWN_COUNT++))
fi

echo "" | tee -a "$LOG_FILE"
if [ $DOWN_COUNT -eq 0 ]; then
    echo "All services healthy" | tee -a "$LOG_FILE"
else
    echo "WARNING: $DOWN_COUNT service(s) down" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"
