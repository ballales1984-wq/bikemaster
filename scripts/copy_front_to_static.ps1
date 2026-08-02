<#
.SYNOPSIS
    Build the Vue 3 frontend and copy the output to bike_analyzer/backend/static/.

.DESCRIPTION
    Runs `npm run build` in frontend/ and copies frontend/dist/* into
    bike_analyzer/backend/static/ so the FastAPI backend can serve the SPA
    locally (or in CI) without Docker.

.PARAMETER SkipBuild
    Skip the `npm run build` step and only copy an existing frontend/dist.

.PARAMETER Help
    Show usage.

.EXAMPLE
    .\scripts\copy_front_to_static.ps1           # build + copy
    .\scripts\copy_front_to_static.ps1 -SkipBuild # copy existing dist only
#>

param(
    [switch]$SkipBuild,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    Write-Host "Build the Vue 3 frontend and copy dist/ to bike_analyzer/backend/static/"
    Write-Host "Usage: .\scripts\copy_front_to_static.ps1 [-SkipBuild] [-Help]"
    exit 0
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$FrontendDir = Join-Path $RepoRoot "frontend"
$StaticDir = Join-Path $RepoRoot "bike_analyzer\backend\static"
$DistDir = Join-Path $FrontendDir "dist"

Write-Host "[copy_front_to_static] repo root: $RepoRoot"

if (-not $SkipBuild) {
    Write-Host "[copy_front_to_static] building frontend (npm run build)..."
    Set-Location $FrontendDir
    npm run build
    Set-Location $RepoRoot
}

if (-not (Test-Path $DistDir)) {
    Write-Error "[copy_front_to_static] $DistDir does not exist. Build may have failed."
    exit 1
}

if (-not (Test-Path $StaticDir)) {
    New-Item -ItemType Directory -Path $StaticDir | Out-Null
}

Write-Host "[copy_front_to_static] copying $DistDir\* -> $StaticDir\"
$items = Get-ChildItem -Path $DistDir -Force
foreach ($item in $items) {
    $dest = Join-Path $StaticDir $item.Name
    if (Test-Path $dest -PathType Container) {
        Remove-Item -Recurse -Force $dest
    } elseif (Test-Path $dest -PathType Leaf) {
        Remove-Item -Force $dest
    }
    Copy-Item -Path $item.FullName -Destination $StaticDir -Recurse -Force
}

$indexExists = Test-Path (Join-Path $StaticDir "index.html")
if ($indexExists) {
    Write-Host "[copy_front_to_static] done. index.html: OK"
} else {
    Write-Error "[copy_front_to_static] done but index.html is MISSING in $StaticDir"
    exit 1
}
