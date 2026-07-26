param(
    [int]$BackendPort = 8000,
    [switch]$Background,
    [switch]$UpdateVercel
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

if ($Background -or $UpdateVercel) {
    $tempFile = [System.IO.Path]::GetTempFileName()
    $proc = Start-Process -FilePath $cloudflared -ArgumentList $args -NoNewWindow -PassThru -Wait:$false -RedirectStandardOutput $tempFile -RedirectStandardError $tempFile

    Write-Host "Tunnel started in background (PID $($proc.Id))." -ForegroundColor Green
    Write-Host "Waiting for tunnel URL..." -ForegroundColor Yellow

    $url = $null
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 2
        $content = Get-Content $tempFile -Raw -ErrorAction SilentlyContinue
        if ($content -match "https://[a-z0-9-]+\.trycloudflare\.com") {
            $url = $matches[0]
            break
        }
    }

    if ($url) {
        Write-Host "Tunnel URL: $url" -ForegroundColor Cyan
        $apiBase = "$url/api/v1"
        Write-Host "API Base: $apiBase" -ForegroundColor Cyan

        if ($UpdateVercel) {
            Write-Host "Updating Vercel VITE_API_BASE..." -ForegroundColor Yellow
            try {
                $vercelInput = "$apiBase`n"
                $vercelInput | npx vercel env add VITE_API_BASE production 2>&1 | Out-Null
                Write-Host "Vercel VITE_API_BASE updated to: $apiBase" -ForegroundColor Green
                Write-Host "Trigger a redeploy for the change to take effect (e.g., push a commit or use the Vercel dashboard)." -ForegroundColor Yellow
            } catch {
                Write-Host "Failed to update Vercel env via CLI." -ForegroundColor Red
                Write-Host "Update manually in the Vercel dashboard:" -ForegroundColor Yellow
                Write-Host "  VITE_API_BASE = $apiBase" -ForegroundColor Cyan
            }
        }
    } else {
        Write-Host "Could not detect tunnel URL from output." -ForegroundColor Red
        Write-Host "Check cloudflared output manually." -ForegroundColor Yellow
    }

    Remove-Item $tempFile -ErrorAction SilentlyContinue
} else {
    & $cloudflared @args
}
