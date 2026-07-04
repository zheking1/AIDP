#!/bin/bash
# Set GitHub Token for SkillRouter
# Usage: ./set-github-token.sh YOUR_GITHUB_TOKEN

if [ -z "$1" ]; then
    echo "Usage: $0 YOUR_GITHUB_TOKEN"
    echo ""
    echo "To get a GitHub token:"
    echo "1. Go to https://github.com/settings/tokens"
    echo "2. Click 'Generate new token (classic)'"
    echo "3. Select 'repo' scope (for private repos) or 'public_repo' (for public repos only)"
    echo "4. Copy the token"
    exit 1
fi

TOKEN=$1
SETTINGS_FILE="/home/docker/AI-Code/SkillRouter/app/data/settings.json"

# Create settings directory if it doesn't exist
mkdir -p "$(dirname "$SETTINGS_FILE")"

# Read existing settings or create new
if [ -f "$SETTINGS_FILE" ]; then
    # Update existing settings
    python3 -c "
import json
with open('$SETTINGS_FILE', 'r') as f:
    settings = json.load(f)
settings['github_token'] = '$TOKEN'
with open('$SETTINGS_FILE', 'w') as f:
    json.dump(settings, f, indent=2)
print('GitHub token updated successfully')
"
else
    # Create new settings file
    echo "{\"github_token\": \"$TOKEN\", \"allow_registration\": true}" > "$SETTINGS_FILE"
    echo "Settings file created with GitHub token"
fi

# Restart SkillRouter to apply changes
docker restart skillrouter-app-1
echo "SkillRouter restarted"
