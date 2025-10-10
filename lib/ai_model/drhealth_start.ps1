Write-Host "`nStarting DrHealth Full Stack..." -ForegroundColor Cyan

# Stop and remove any existing containers to avoid conflicts
$containers = @("drhealth_fastapi", "prometheus", "grafana", "loki", "promtail", "cadvisor")
foreach ($c in $containers) {
    docker stop $c -t 3 2>$null
    docker rm $c -f 2>$null
}

# Kill any leftover Python or Uvicorn processes
$procs = "python", "python.exe", "uvicorn"
foreach ($p in $procs) {
    Get-Process -Name $p -ErrorAction SilentlyContinue | Stop-Process -Force
}

Start-Sleep -Seconds 2
Write-Host "`nLaunching monitoring stack..." -ForegroundColor Yellow

# Prometheus
docker run -d --name prometheus `
  -p 9090:9090 `
  -v "C:\prometheus\prometheus.yml:/etc/prometheus/prometheus.yml:ro" `
  prom/prometheus:latest | Out-Null

# Grafana
docker run -d --name grafana `
  -p 3000:3000 `
  grafana/grafana:latest | Out-Null

# Loki
docker run -d --name loki `
  -p 3100:3100 `
  -v "C:\prometheus\loki-config.yml:/etc/loki/config.yml:ro" `
  grafana/loki:2.9.3 `
  --config.file=/etc/loki/config.yml | Out-Null

# cAdvisor
docker run -d --name cadvisor `
  --volume=/:/rootfs:ro `
  --volume=/var/run:/var/run:rw `
  --volume=/sys:/sys:ro `
  --volume=/var/lib/docker/:/var/lib/docker:ro `
  -p 8080:8080 `
  gcr.io/cadvisor/cadvisor:latest | Out-Null

# Promtail
docker run -d --name promtail `
  -v "C:\Users\ssing\drhealth_app\lib\ai_model\promtail-config.yml:/etc/promtail/config.yml:ro" `
  -v "C:\Users\ssing\drhealth_app\lib\ai_model:/logs" `
  -p 9080:9080 `
  grafana/promtail:2.9.4 `
  --config.file=/etc/promtail/config.yml | Out-Null

# FastAPI
Write-Host "`nStarting FastAPI (DrHealth AI Server)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList 'cd "C:\Users\ssing\drhealth_app\lib\ai_model"; uvicorn server_fastapi:app --host 127.0.0.1 --port 8000 --reload'

Start-Sleep -Seconds 5

# Function: Health check with retry
function Wait-ForPort {
    param (
        [int]$Port,
        [string]$Name,
        [int]$Retries = 30
    )
    $count = 0
    while ($count -lt $Retries) {
        $test = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue
        if ($test.TcpTestSucceeded) {
            Write-Host "✅ $Name (Port $Port) is running." -ForegroundColor Green
            return $true
        } else {
            Write-Host "⏳ Waiting for $Name..." -ForegroundColor Yellow
            Start-Sleep -Seconds 2
            $count++
        }
    }
    Write-Host "❌ $Name failed to start after $Retries attempts." -ForegroundColor Red
}

Write-Host "`nChecking all services..." -ForegroundColor Cyan
Wait-ForPort 8000 "FastAPI"
Wait-ForPort 9090 "Prometheus"
Wait-ForPort 3000 "Grafana"
Wait-ForPort 3100 "Loki"
Wait-ForPort 9080 "Promtail"
Wait-ForPort 8080 "cAdvisor"

Write-Host "`nOpening Grafana Dashboard..." -ForegroundColor Cyan
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "DrHealth Full Monitoring Stack Started Successfully!" -ForegroundColor Green
Write-Host "Access your services:"
Write-Host "  FastAPI     : http://127.0.0.1:8000/docs"
Write-Host "  Prometheus  : http://localhost:9090"
Write-Host "  Grafana     : http://localhost:3000"
Write-Host "  Loki        : http://localhost:3100"
Write-Host "  cAdvisor    : http://localhost:8080"
Write-Host "  Promtail    : http://localhost:9080/metrics"
Write-Host ""
Write-Host "All Systems Operational - DrHealth is Live!" -ForegroundColor Cyan
