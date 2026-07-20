param(
    [int]$BackendPort = 8000,
    [switch]$Background
)

$ErrorActionPreference = "Stop"

$cloudflared = Join-Path $env:USERPROFILE ".cloudflared\cloudflared.exe"
if (-not (Test-Path $cloudflared)) {
    Write-Host "ERROR: cloudflared not found at $cloudflared" -ForegroundColor Red
    Write-Host "Run the setup first or download from https://github.com/cloudflare/cloudflared/releases" -ForegroundColor Yellow
    exit 1
}

$backendUrl = "http://localhost:$BackendPort"
Write-Host "Starting cloudflared quick tunnel for $backendUrl ..." -ForegroundColor Cyan

$args = @("tunnel", "--url", $backendUrl)

if ($Background) {
    $proc = Start-Process -FilePath $cloudflared -ArgumentList $args -NoNewWindow -PassThru -Wait:$false
    Write-Host "Tunnel started in background (PID $($proc.Id))." -ForegroundColor Green
    Write-Host "Check the tunnel output to get the public URL." -ForegroundColor Yellow
} else {
    & $cloudflared @args
}
