# AIDP Deployment Script (Build on NAS)
# Copies source code to NAS and builds Docker images there

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
    @{ name = "controller"; localPath = "apps\controller"; port = 8883 }
)

function Write-Step { param([string]$msg) Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-OK { param([string]$msg) Write-Host "   OK: $msg" -ForegroundColor Green }
function Write-Fail { param([string]$msg) Write-Host "   FAIL: $msg" -ForegroundColor Red }

Write-Step "AIDP Deployment to $NasHost (Build on NAS)"

foreach ($tool in $tools) {
    $name = $tool.name
    $localPath = $tool.localPath
    $port = $tool.port

    Write-Step "Processing $name (port $port)"

    # Check local path exists
    if (-not (Test-Path $localPath)) {
        Write-Fail "Local path not found: $localPath"
        continue
    }

    # Create remote directory
    Write-Host "   Creating remote directory..."
    ssh -i $NasKey "${NasUser}@${NasHost}" "mkdir -p $NasDeployPath/$name"

    # Create tar of source, excluding unnecessary files
    Write-Host "   Packaging source code..."
    $sourceTar = "$name-source.tar.gz"
    tar czf $sourceTar -C $localPath --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='data' .
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Failed to create tar for $name"
        continue
    }

    # SCP to NAS
    Write-Host "   Uploading to NAS..."
    scp -i $NasKey $sourceTar "${NasUser}@${NasHost}:/tmp/$sourceTar"
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "SCP failed for $name"
        Remove-Item $sourceTar -Force -ErrorAction SilentlyContinue
        continue
    }

    # Extract on NAS
    Write-Host "   Extracting on NAS..."
    ssh -i $NasKey "${NasUser}@${NasHost}" "cd $NasDeployPath/$name && tar xzf /tmp/$sourceTar && rm /tmp/$sourceTar"
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Extract failed for $name"
        Remove-Item $sourceTar -Force -ErrorAction SilentlyContinue
        continue
    }
    Remove-Item $sourceTar -Force
    Write-OK "Source code uploaded"

    # Stop existing container if running
    Write-Host "   Stopping existing container..."
    ssh -i $NasKey "${NasUser}@${NasHost}" "docker stop $name 2>/dev/null; docker rm $name 2>/dev/null"
    Write-OK "Cleaned up"

    # Build Docker image on NAS
    Write-Host "   Building Docker image on NAS..."
    $imageTag = "aidp/$name`:0.1.0"
    ssh -i $NasKey "${NasUser}@${NasHost}" "cd $NasDeployPath/$name && docker build -t $imageTag ."
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Docker build failed on NAS for $name"
        continue
    }
    Write-OK "Image built"

    # Start container
    Write-Host "   Starting container..."
    $dbUrl = $env:DATABASE_URL
    if (-not $dbUrl) { $dbUrl = "postgresql+asyncpg://127.0.0.1:5432/db" }
    ssh -i $NasKey "${NasUser}@${NasHost}" "docker run -d --name $name --restart unless-stopped --network host -e DATABASE_URL=`"$dbUrl`" $imageTag"
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Docker run failed for $name"
        continue
    }
    Write-OK "Container started"

    # Wait and check health
    Write-Host "   Waiting for health check..."
    Start-Sleep -Seconds 3
    $healthCheck = ssh -i $NasKey "${NasUser}@${NasHost}" "curl -sf http://127.0.0.1:${port}/health"
    if ($healthCheck) {
        Write-OK "Health check passed: $healthCheck"
    } else {
        Write-Host "   Health check pending (may take a few more seconds)" -ForegroundColor Yellow
    }
}

Write-Step "Deployment complete!"
Write-Host "`nTools deployed:"
foreach ($tool in $tools) {
    Write-Host "  $($tool.name): http://${NasHost}:$($tool.port)/health"
}
