param(
    [int]$BackendPort = 8000,
    [switch]$Background
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: ssh (OpenSSH Client) is not available on this system." -ForegroundColor Red
    exit 1
}

$backendUrl = "http://localhost:$BackendPort"
Write-Host "Starting localhost.run tunnel for $backendUrl ..." -ForegroundColor Cyan

$args = @(
    "-o", "StrictHostKeyChecking=no"
    "-o", "ServerAliveInterval=30"
    "-R", "80:localhost:$BackendPort"
    "localhost.run"
)

if ($Background) {
    $proc = Start-Process -FilePath "ssh" -ArgumentList $args -NoNewWindow -PassThru -Wait:$false
    Write-Host "Tunnel started in background (PID $($proc.Id))." -ForegroundColor Green
    Write-Host "Check the tunnel output to get the public URL." -ForegroundColor Yellow
} else {
    & ssh @args
}
