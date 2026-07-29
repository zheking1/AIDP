# Memory Tool NAS Deployment Script
# Run this script to deploy the memory tool to NAS

param(
    [string]$NasIp = "192.168.0.100",
    [string]$SshKey = "$env:USERPROFILE\.ssh\nas_temp",
    [string]$RemotePath = "/volume1/docker/memory-tool",
    [string]$LocalPath = "D:\Project\openCode\tools\memory-tool"
)

$ErrorActionPreference = "Stop"

function Write-Header($text) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $text -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Write-Step($text) {
    Write-Host "[STEP] $text" -ForegroundColor Yellow
}

function Write-Success($text) {
    Write-Host "[OK] $text" -ForegroundColor Green
}

function Write-Error($text) {
    Write-Host "[ERR] $text" -ForegroundColor Red
}

# Step 1: Verify local files
Write-Header "Memory Tool Deployment to NAS"
Write-Host "Target: $NasIp"
Write-Host "Local: $LocalPath"
Write-Host "Remote: $RemotePath`n"

Write-Step "Verifying local files..."
$requiredFiles = @(
    "app",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml"
)

foreach ($file in $requiredFiles) {
    $fullPath = Join-Path $LocalPath $file
    if (-not (Test-Path $fullPath)) {
        Write-Error "Missing required file: $file"
        exit 1
    }
}
Write-Success "All required files found"

# Step 2: Test SSH connection
Write-Step "Testing SSH connection..."
try {
    $testResult = & ssh -i $SshKey -o ConnectTimeout=10 -o StrictHostKeyChecking=no "admin@$NasIp" "echo 'SSH_OK'" 2>&1
    if ($testResult -match "SSH_OK") {
        Write-Success "SSH connection successful"
    } else {
        Write-Error "SSH connection failed: $testResult"
        exit 1
    }
} catch {
    Write-Error "SSH connection failed: $_"
    exit 1
}

# Step 3: Create remote directory
Write-Step "Creating remote directory..."
& ssh -i $SshKey "admin@$NasIp" "mkdir -p $RemotePath" 2>&1 | Out-Null
Write-Success "Remote directory ready"

# Step 4: Backup existing data
Write-Step "Backing up existing data on NAS..."
$backupCmd = @"
cd $RemotePath
if [ -d "data" ]; then
    backup_dir="data.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    cp -r data "$backup_dir"
    echo "Backed up to $backup_dir"
fi
"@
& ssh -i $SshKey "admin@$NasIp" $backupCmd 2>&1 | ForEach-Object {
    if ($_ -match "Backed up") {
        Write-Success $_
    }
}

# Step 5: Copy files to NAS
Write-Step "Copying files to NAS (this may take a while)..."
$filesToCopy = @("app", "requirements.txt", "Dockerfile", "docker-compose.yml")

foreach ($file in $filesToCopy) {
    $localFile = Join-Path $LocalPath $file
    Write-Host "  Copying $file..." -ForegroundColor Gray -NoNewline
    
    try {
        if (Test-Path $localFile -PathType Container) {
            # Directory - remove existing first, then copy
            $rmCmd = "rm -rf $RemotePath/$file"
            & ssh -i $SshKey "admin@$NasIp" $rmCmd 2>&1 | Out-Null
            
            # Use tar for faster directory transfer
            $tarCmd = "tar -cf - -C `"$LocalPath`" `"$file`" | ssh -i `"$SshKey`" `"admin@$NasIp`" `"tar -xf - -C $RemotePath`""
            Invoke-Expression $tarCmd 2>&1 | Out-Null
        } else {
            # File
            & scp -i $SshKey -o ConnectTimeout=30 "$localFile" "admin@${NasIp}:${RemotePath}/" 2>&1 | Out-Null
        }
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " FAILED" -ForegroundColor Red
        Write-Error "Failed to copy $file`: $_"
        exit 1
    }
}
Write-Success "All files copied"

# Step 6: Build and restart container
Write-Step "Building and restarting container..."
$deployCmd = @"
cd $RemotePath
echo "Stopping existing container..."
docker-compose down 2>/dev/null || true

echo "Building new image..."
docker-compose build --no-cache 2>&1

echo "Starting container..."
docker-compose up -d 2>&1

echo "Waiting for startup..."
sleep 5

echo "Container status:"
docker-compose ps
"@

$deployResult = & ssh -i $SshKey "admin@$NasIp" $deployCmd 2>&1
$deployResult | ForEach-Object {
    if ($_ -match "error|Error|ERROR|failed|Failed|FAILED") {
        Write-Error $_
    } elseif ($_ -match "successfully|Successfully|done|Done|started|Started") {
        Write-Success $_
    } else {
        Write-Host "  $_" -ForegroundColor Gray
    }
}

# Step 7: Health check
Write-Step "Performing health check..."
Start-Sleep -Seconds 3

try {
    $response = Invoke-RestMethod -Uri "http://${NasIp}:18085/health" -TimeoutSec 10 -ErrorAction Stop
    Write-Success "Health check passed"
    
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "`nAccess your Memory Tool at:" -ForegroundColor White
    Write-Host "  http://${NasIp}:18085/" -ForegroundColor Cyan
    Write-Host "  http://${NasIp}:18085/memories" -ForegroundColor Cyan
    Write-Host "  http://${NasIp}:18085/memories/graph" -ForegroundColor Cyan
    Write-Host "  http://${NasIp}:18085/context" -ForegroundColor Cyan
    Write-Host "  http://${NasIp}:18085/review" -ForegroundColor Cyan
    
} catch {
    Write-Error "Health check failed: $_"
    Write-Host "`nContainer may still be starting. Check logs with:" -ForegroundColor Yellow
    Write-Host "  ssh -i $SshKey admin@$NasIp 'cd $RemotePath && docker-compose logs'" -ForegroundColor Gray
}
