#!/bin/bash
# AIDP Alert Script with Webhook Support
# Sends alerts when services are down

ALERT_LOG="/home/docker/AI-Code/logs/alerts.log"
CONFIG_FILE="/home/docker/AI-Code/alert-config.json"
mkdir -p /home/docker/AI-Code/logs

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Load webhook URL from config if exists
WEBHOOK_URL=""
if [ -f "$CONFIG_FILE" ]; then
    WEBHOOK_URL=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('webhook_url', ''))" 2>/dev/null)
fi

send_alert() {
    local name=$1
    local message=$2
    
    echo "$TIMESTAMP ALERT: $name - $message" >> "$ALERT_LOG"
    echo "[$TIMESTAMP] ALERT: $name - $message"
    
    # Send webhook if configured
    if [ -n "$WEBHOOK_URL" ]; then
        curl -s -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"AIDP Alert: $name is $message\", \"timestamp\": \"$TIMESTAMP\"}" \
            > /dev/null 2>&1
    fi
}

check_and_alert() {
    local name=$1
    local url=$2
    local status=$(curl -sf "$url" 2>/dev/null)
    if [ $? -ne 0 ]; then
        send_alert "$name" "DOWN at $url"
        return 1
    fi
    return 0
}

echo "=== AIDP Alert Check: $TIMESTAMP ==="

DOWN_COUNT=0

check_and_alert "knowledge-tool" "http://127.0.0.1:18081/health" || ((DOWN_COUNT++))
check_and_alert "asset-tool" "http://127.0.0.1:18082/health" || ((DOWN_COUNT++))
check_and_alert "sandbox-tool" "http://127.0.0.1:18083/health" || ((DOWN_COUNT++))
check_and_alert "quality-tool" "http://127.0.0.1:18084/health" || ((DOWN_COUNT++))
check_and_alert "memory-tool" "http://127.0.0.1:18085/health" || ((DOWN_COUNT++))
check_and_alert "controller" "http://127.0.0.1:8883/health" || ((DOWN_COUNT++))
check_and_alert "skillrouter" "http://127.0.0.1:8788/health" || ((DOWN_COUNT++))

echo "Alert check complete. Down: $DOWN_COUNT"
