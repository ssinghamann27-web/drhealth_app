Write-Host "`nStopping DrHealth Full Stack..." -ForegroundColor Yellow

# Stop and remove containers
$containers = @("drhealth_fastapi", "prometheus", "grafana", "loki", "promtail", "cadvisor")
foreach ($c in $containers) {
    docker stop $c -t 3 2>$null
    docker rm $c -f 2>$null
}

# Kill stray Python/Uvicorn
$procs = "python", "python.exe", "uvicorn"
foreach ($p in $procs) {
    Get-Process -Name $p -ErrorAction SilentlyContinue | Stop-Process -Force
}

# Cleanup
Write-Host "`nCleaning Docker junk..." -ForegroundColor Cyan
docker network prune -f | Out-Null
docker volume prune -f | Out-Null
docker builder prune -af | Out-Null

Write-Host "`n All DrHealth services stopped successfully." -ForegroundColor Green
Write-Host "Local data safe at: C:\Users\ssing\drhealth_app\lib\ai_model"
Write-Host "System fully shut down. Run drhealth_start.ps1 to relaunch." -ForegroundColor Cyan
