# AIDP Deployment Script
# Deploys all tools to NAS at /home/docker/AI-Code/

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

Write-Step "AIDP Deployment to $NasHost"

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

    # Build Docker image
    Write-Host "   Building Docker image..."
    $imageTag = "aidp/$name`:0.1.0"
    docker build -t $imageTag $localPath 2>&1 | Select-Object -Last 3
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Docker build failed for $name"
        continue
    }
    Write-OK "Image built: $imageTag"

    # Save image to tar
    $tarFile = "$name.tar"
    Write-Host "   Saving image to $tarFile..."
    docker save $imageTag -o $tarFile
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Docker save failed for $name"
        continue
    }
    Write-OK "Image saved"

    # SCP to NAS
    Write-Host "   Uploading to NAS..."
    scp -i $NasKey $tarFile "${NasUser}@${NasHost}:/tmp/$tarFile"
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "SCP failed for $name"
        continue
    }
    Write-OK "Uploaded to NAS"

    # Load image on NAS
    Write-Host "   Loading image on NAS..."
    ssh -i $NasKey "${NasUser}@${NasHost}" "docker load -i /tmp/$tarFile && rm /tmp/$tarFile"
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Docker load failed on NAS for $name"
        continue
    }
    Write-OK "Image loaded on NAS"

    # Copy source code to NAS
    Write-Host "   Copying source code to NAS..."
    ssh -i $NasKey "${NasUser}@${NasHost}" "mkdir -p $NasDeployPath/$name"
    # Create tar of source, excluding unnecessary files
    $sourceTar = "$name-source.tar.gz"
    tar czf $sourceTar -C $localPath --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='data' .
    scp -i $NasKey $sourceTar "${NasUser}@${NasHost}:/tmp/$sourceTar"
    ssh -i $NasKey "${NasUser}@${NasHost}" "cd $NasDeployPath/$name && tar xzf /tmp/$sourceTar && rm /tmp/$sourceTar"
    Remove-Item $sourceTar -Force
    Write-OK "Source copied"

    # Stop existing container if running
    Write-Host "   Stopping existing container..."
    ssh -i $NasKey "${NasUser}@${NasHost}" "docker stop $name 2>/dev/null; docker rm $name 2>/dev/null"
    Write-OK "Cleaned up"

    # Start container
    Write-Host "   Starting container..."
    $dbUrl = "postgresql+asyncpg://novel_os:jygame_postgres_01@host.docker.internal:5432/novel_os"
    ssh -i $NasKey "${NasUser}@${NasHost}" "docker run -d --name $name --restart unless-stopped -p ${port}:${port} -e DATABASE_URL=`"$dbUrl`" --add-host host.docker.internal:host-gateway $imageTag"
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

    # Cleanup local tar
    Remove-Item $tarFile -Force -ErrorAction SilentlyContinue
}

Write-Step "Deployment complete!"
Write-Host "`nTools deployed:"
foreach ($tool in $tools) {
    Write-Host "  $($tool.name): http://${NasHost}:$($tool.port)/health"
}
