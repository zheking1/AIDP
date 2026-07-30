# AIDP Controller Deploy — 单容器部署
# 所有工具已整合到 Controller，只需部署这一个容器

param(
    [string]$NasHost = "192.168.0.100",
    [string]$NasUser = "root",
    [string]$NasKey = "~/.ssh/nas_temp",
    [string]$NasDeployPath = "/home/docker/AI-Code"
)

$ErrorActionPreference = "Stop"

$name = "controller"
$localPath = "apps\controller"
$port = 8883

Write-Host "`n>> AIDP Controller Deployment to $NasHost" -ForegroundColor Cyan
Write-Host ("=" * 60)

# Upload docker-compose.yml
Write-Host "  Uploading docker-compose.yml..."
ssh -i $NasKey "${NasUser}@${NasHost}" "mkdir -p $NasDeployPath"
scp -i $NasKey "docker-compose.yml" "${NasUser}@${NasHost}:$NasDeployPath/docker-compose.yml"
Write-Host "  OK: docker-compose.yml uploaded"

# Upload source code
Write-Host "  Packaging controller source..."
$sourceTar = "controller-src.tar.gz"
& tar czf $sourceTar -C $localPath --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='data' --exclude='venv' --exclude='*.tar*' .

Write-Host "  Uploading to NAS..."
scp -i $NasKey $sourceTar "${NasUser}@${NasHost}:/tmp/$sourceTar"
Remove-Item $sourceTar -Force

Write-Host "  Extracting on NAS..."
ssh -i $NasKey "${NasUser}@${NasHost}" "cd $NasDeployPath/$name && tar xzf /tmp/$sourceTar && rm /tmp/$sourceTar"
Write-Host "  OK: Source code uploaded"

# Build Docker image on NAS
Write-Host "  Building Docker image on NAS..."
ssh -i $NasKey "${NasUser}@${NasHost}" "cd $NasDeployPath/$name && docker build -t aidp/$name`:0.1.0 ."
Write-Host "  OK: Image built"

# Restart via Docker Compose
Write-Host "  Restarting service..."
$dbPassword = if ($env:AIDP_DB_PASSWORD) { $env:AIDP_DB_PASSWORD } else { "jygame_postgres_01" }
$sessionKey = if ($env:CONTROLLER_SESSION_KEY) { $env:CONTROLLER_SESSION_KEY } else { "nas-deploy-key-2026" }

ssh -i $NasKey "${NasUser}@${NasHost}" @"
cd $NasDeployPath
export AIDP_DB_PASSWORD="$dbPassword"
export CONTROLLER_SESSION_KEY="$sessionKey"
docker compose down 2>/dev/null
docker compose up -d
"@
Write-Host "  OK: Service restarted"

# Health check
Write-Host "  Health check..."
Start-Sleep -Seconds 4
$health = ssh -i $NasKey "${NasUser}@${NasHost}" "curl -sf http://127.0.0.1:8883/health"
if ($health) { Write-Host "  OK: $health" -ForegroundColor Green } else { Write-Host "  Health check pending..." -ForegroundColor Yellow }

Write-Host "`n>>>> Deploy complete! <<<<" -ForegroundColor Green
Write-Host "  Controller: http://${NasHost}:8883"