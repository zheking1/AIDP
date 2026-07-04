#!/bin/bash
# AIDP Test Data Cleanup
# Clears test data to avoid uniqueness conflicts

DB_CONTAINER="novel-postgres"
DB_USER="novel_os"
DB_NAME="novel_os"

echo "=== AIDP Test Data Cleanup ==="
echo "This will clear test data from the database."
echo ""

# Check if running in test mode
if [ "$1" != "--confirm" ]; then
    echo "Usage: $0 --confirm"
    echo ""
    echo "This will delete:"
    echo "  - Skills with test prefix"
    echo "  - Rules with test prefix"
    echo "  - LLM models with test prefix"
    echo "  - Test evolutions"
    echo "  - Test reviews"
    echo ""
    echo "To proceed, run: $0 --confirm"
    exit 1
fi

echo "Clearing test data..."

# Clear test skills
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
DELETE FROM skill WHERE name LIKE 'test-%' OR name LIKE 'test_%' OR name LIKE 'integration-%';
" 2>/dev/null
echo "Cleared test skills"

# Clear test rules
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
DELETE FROM rule WHERE name LIKE 'test-%' OR name LIKE 'test_%' OR name LIKE 'integration-%';
" 2>/dev/null
echo "Cleared test rules"

# Clear test LLM models
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
DELETE FROM llm_model WHERE name LIKE 'test-%' OR name LIKE 'test_%' OR name LIKE 'integration-%';
" 2>/dev/null
echo "Cleared test LLM models"

# Clear test evolutions
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
DELETE FROM evolution WHERE title LIKE 'test-%' OR title LIKE 'test_%';
" 2>/dev/null
echo "Cleared test evolutions"

# Clear test reviews
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
DELETE FROM review WHERE summary LIKE 'test-%' OR summary LIKE 'test_%';
" 2>/dev/null
echo "Cleared test reviews"

# Clear test operation logs
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
DELETE FROM operation_log WHERE action LIKE 'test-%' OR action LIKE 'test_%';
" 2>/dev/null
echo "Cleared test operation logs"

echo ""
echo "Test data cleared successfully!"
