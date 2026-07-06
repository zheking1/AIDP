#!/bin/bash
# Delete duplicate project from PostgreSQL
docker exec novel-postgres psql -U novel_os -d aidp -c "DELETE FROM projects WHERE id = '00000000-0000-0000-0000-000000000002'"
echo "Done"