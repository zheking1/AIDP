#!/bin/bash
# AIDP 服务启动脚本
# 使用前请先设置 DATABASE_URL 环境变量
# export DATABASE_URL='postgresql://user:password@127.0.0.1:5432/dbname'

if [ -z "$DATABASE_URL" ]; then
    echo "错误: DATABASE_URL 未设置"
    echo "请先设置环境变量: export DATABASE_URL='...'"
    exit 1
fi

echo "启动 AIDP 服务..."
cd /home/docker/AI-Code/controller && docker compose up -d
cd /home/docker/AI-Code/knowledge-tool && docker compose up -d
cd /home/docker/AI-Code/memory-tool && docker compose up -d
cd /home/docker/AI-Code/asset-tool && docker compose up -d
cd /home/docker/AI-Code/file-watcher && docker compose up -d

echo "服务启动完成"
docker ps --format 'table {{.Names}}\t{{.Status}}'
