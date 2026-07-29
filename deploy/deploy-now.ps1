# AIDP NAS Deployment Script (Build on NAS)
# Copies source code to NAS, builds Docker images, starts via Docker Compose

param(
    [string]$NasHost = "192.168.0.100",
    [string]$NasUser = "root",
    [string]$NasKey = "~/.ssh/nas_temp",
    [string]$NasDeployPath = "/home/docker/AI-Code"
)

$ErrorActionPreference = "Stop"

$tools = @(
    @{ name = "knowledge-tool"; localPath = "tools\knowledge-tool"; port = 18081 },
    @{ name = "asset-tool"; localPath = "tools\asset-tool"; port = 18082 },
    @{ name = "sandbox-tool"; localPath = "tools\sandbox-tool"; port = 18083 },
    @{ name = "quality-tool"; localPath = "tools\quality-tool"; port = 18084 },
    @{ name = "memory-tool"; localPath = "tools\memory-tool"; port = 18085 },
    @{ name = "skill-router"; localPath = "tools\skill-router"; port = 8788 },
    @{ name = "controller"; localPath = "apps\controller"; port = 8883 }
)

function Write-Step { param([string]$msg) Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-OK { param([string]$msg) Write-Host "   OK: $msg" -ForegroundColor Green }
function Write-Fail { param([string]$msg) Write-Host "   FAIL: $msg" -ForegroundColor Red }

Write-Step "AIDP Deployment to $NasHost (Build on NAS)"

# Step 1: Upload docker-compose.yml and init script to NAS
Write-Step "Uploading Docker Compose config"
ssh -i $NasKey "${NasUser}@${NasHost}" "mkdir -p $NasDeployPath/deploy"
scp -i $NasKey "docker-compose.yml" "${NasUser}@${NasHost}:$NasDeployPath/docker-compose.yml"
scp -i $NasKey "deploy\init-db.sql" "${NasUser}@${NasHost}:$NasDeployPath/deploy/init-db.sql"
Write-OK "Docker Compose config uploaded"

# Step 2: Upload and build each tool
foreach ($tool in $tools) {
    $name = $tool.name
    $localPath = $tool.localPath
    $port = $tool.port

    Write-Step "Processing $name (port $port)"

    if (-not (Test-Path $localPath)) {
        Write-Fail "Local path not found: $localPath"
        continue
    }

    ssh -i $NasKey "${NasUser}@${NasHost}" "mkdir -p $NasDeployPath/$name"

    Write-Host "   Packaging source code..."
    $sourceTar = "$name-source.tar.gz"
    tar czf $sourceTar -C $localPath --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='data' --exclude='venv' --exclude='.env' .

    Write-Host "   Uploading to NAS..."
    scp -i $NasKey $sourceTar "${NasUser}@${NasHost}:/tmp/$sourceTar"
    if ($LASTEXITCODE -ne 0) { Write-Fail "SCP failed for $name"; Remove-Item $sourceTar -Force -ErrorAction SilentlyContinue; continue }

    Write-Host "   Extracting on NAS..."
    ssh -i $NasKey "${NasUser}@${NasHost}" "cd $NasDeployPath/$name && tar xzf /tmp/$sourceTar && rm /tmp/$sourceTar"
    Remove-Item $sourceTar -Force
    Write-OK "Source code uploaded"

    Write-Host "   Building Docker image on NAS..."
    $imageTag = "aidp/$name`:0.1.0"
    ssh -i $NasKey "${NasUser}@${NasHost}" "cd $NasDeployPath/$name && docker build -t $imageTag ."
    if ($LASTEXITCODE -ne 0) { Write-Fail "Docker build failed for $name on NAS"; continue }
    Write-OK "Image built: $imageTag"
}

# Step 3: Stop old containers and start via Docker Compose
Write-Step "Starting services via Docker Compose"

$dbPassword = $env:AIDP_DB_PASSWORD
if (-not $dbPassword) { $dbPassword = "aidp_secret" }

$sessionKey = $env:CONTROLLER_SESSION_KEY
if (-not $sessionKey) { $sessionKey = "nas-deploy-key-2026" }

ssh -i $NasKey "${NasUser}@${NasHost}" @"
cd $NasDeployPath
export AIDP_DB_PASSWORD="$dbPassword"
export CONTROLLER_SESSION_KEY="$sessionKey"
docker compose down 2>/dev/null
docker compose up -d
"@

if ($LASTEXITCODE -eq 0) {
    Write-OK "All services started via Docker Compose"
} else {
    Write-Fail "Docker Compose failed"
}

# Step 4: Health checks
Write-Step "Running health checks"
Start-Sleep -Seconds 5

$healthEndpoints = @(
    "http://127.0.0.1:8883/health",
    "http://127.0.0.1:18083/health",
    "http://127.0.0.1:18084/health"
)

foreach ($ep in $healthEndpoints) {
    $result = ssh -i $NasKey "${NasUser}@${NasHost}" "curl -sf $ep 2>/dev/null || echo 'unreachable'"
    if ($result -and $result -ne 'unreachable') {
        Write-OK "$ep -> OK"
    } else {
        Write-Host "   $ep -> pending (may need more time)" -ForegroundColor Yellow
    }
}

Write-Step "Deployment complete!"
Write-Host "`nAccess URLs:"
Write-Host "  Controller: http://${NasHost}:8883"
Write-Host "  API Docs:   http://${NasHost}:8883/docs"
Write-Host "  Sandbox:    http://${NasHost}:18083/health"
Write-Host "  Quality:    http://${NasHost}:18084/health"