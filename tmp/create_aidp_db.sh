#!/bin/bash
# Create AIDP database in PostgreSQL
docker exec novel-postgres psql -U novel_os -d novel_os -c "CREATE DATABASE aidp;" 2>&1 || echo "Database may already exist"
