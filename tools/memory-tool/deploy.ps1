# Memory Tool Deployment Script for NAS
$ErrorActionPreference = "Stop"

$NAS_IP = "192.168.0.100"
$SSH_KEY = "$env:USERPROFILE\.ssh\nas_temp"
$REMOTE_DIR = "/volume1/docker/memory-tool"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Memory Tool Deployment to NAS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Target: $NAS_IP" -ForegroundColor Gray
Write-Host ""

# Step 1: Copy files to NAS
Write-Host "Step 1: Copying files to NAS..." -ForegroundColor Yellow
$filesToCopy = @(
    "app",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml"
)

foreach ($file in $filesToCopy) {
    Write-Host "  Copying $file..." -ForegroundColor Gray
    $localPath = Join-Path $PWD $file
    $remotePath = "${NAS_IP}:${REMOTE_DIR}/"
    
    if (Test-Path $localPath -PathType Container) {
        # Directory - use rsync-like approach with scp -r
        scp -i $SSH_KEY -r $localPath $remotePath
    } else {
        # File
        scp -i $SSH_KEY $localPath $remotePath
    }
}

# Step 2: Rebuild and restart container
Write-Host ""
Write-Host "Step 2: Rebuilding container..." -ForegroundColor Yellow
$commands = @"
cd $REMOTE_DIR
docker-compose down
docker-compose build --no-cache
docker-compose up -d
sleep 5
docker-compose ps
"@

$commands | ssh -i $SSH_KEY admin@$NAS_IP

# Step 3: Check health
Write-Host ""
Write-Host "Step 3: Checking health..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

try {
    $response = Invoke-RestMethod -Uri "http://${NAS_IP}:18085/health" -TimeoutSec 10
    Write-Host "  Health check: OK" -ForegroundColor Green
} catch {
    Write-Host "  Health check: Failed - $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Access URLs:" -ForegroundColor Gray
Write-Host "  - Web UI: http://${NAS_IP}:18085/memories" -ForegroundColor Cyan
Write-Host "  - Graph:  http://${NAS_IP}:18085/memories/graph" -ForegroundColor Cyan
Write-Host "  - Context: http://${NAS_IP}:18085/context" -ForegroundColor Cyan
Write-Host "  - Review: http://${NAS_IP}:18085/review" -ForegroundColor Cyan
