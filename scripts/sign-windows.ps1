# Sign Windows executables with a code-signing certificate
#
# Usage:
#   pwsh scripts/sign-windows.ps1                          # generate cert + sign
#   pwsh scripts/sign-windows.ps1 -PfxPath <file.pfx> -PfxPassword <pwd>  # use existing cert
#   pwsh scripts/sign-windows.ps1 -Target <path>           # sign a specific file/dir
#
# Requires signtool.exe (Windows SDK) on PATH or in the default SDK location.
param(
    [string] $PfxPath,
    [string] $PfxPassword,
    [string] $Target,
    [string] $TimestampServer = "http://timestamp.digicert.com",
    [string] $StoreName = "My",
    [switch] $GenerateCert,
    [int] $CertMonths = 2
)

$ErrorActionPreference = "Stop"

# Locate signtool.exe
function Find-SignTool {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
        "${env:ProgramFiles}\Windows Kits\10\bin"
    )
    foreach ($base in $candidates) {
        if (Test-Path $base) {
            $ver = Get-ChildItem $base -Directory | Where-Object { $_.Name -match '^\d' } | Sort-Object Name -Descending | Select-Object -First 1
            if ($ver) {
                $exe = Join-Path $ver.FullName "x64\signtool.exe"
                if (Test-Path $exe) { return $exe }
            }
        }
    }
    $found = Get-Command signtool -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    throw "signtool.exe not found. Install Windows 10/11 SDK."
}

$SignTool = Find-SignTool
Write-Host "Using signtool: $SignTool"

# Generate a self-signed code-signing certificate if none provided
if (-not $PfxPath -or -not (Test-Path $PfxPath)) {
    if ($GenerateCert -or -not $PfxPath) {
        Write-Host "Generating self-signed code-signing certificate..."
        $PfxPath = $PfxPath ? $PfxPath : "$env:TEMP\bikemaster-codesign.pfx"
        $PfxPassword = $PfxPassword ? $PfxPassword : "BikeMasterDev123!"
        $subject = "CN=BikeMaster Development"
        $thumbprint = (New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject -KeyUsage DigitalSignature -CertStoreLocation "Cert:\CurrentUser\$StoreName" -NotAfter (Get-Date).AddMonths($CertMonths)).Thumbprint
        $cert = Get-ChildItem "Cert:\CurrentUser\$StoreName\$thumbprint"
        Export-PfxCertificate -Cert $cert -FilePath $PfxPath -Password (ConvertTo-SecureString -String $PfxPassword -Force -AsPlainText)
        Write-Host "Certificate saved to: $PfxPath"
        Write-Host "Password: $PfxPassword"
        Write-Warning "NOTE: Self-signed certs are NOT trusted by Windows Smart App Control (SAC). Use this only for local testing."
        Write-Host "  For SAC compliance, use a CA-signed code-signing certificate (ZeroSSL, DigiCert, Sectigo)."
    }
}

if (-not $PfxPath -or -not (Test-Path $PfxPath)) {
    throw "No certificate found. Pass -PfxPath or run with -GenerateCert."
}

Write-Host "Using certificate: $PfxPath"

# Determine targets to sign
if ($Target) {
    $files = @($Target)
} else {
    $releaseDir = "frontend/src-tauri/target/release"
    $bundleDir = "frontend/src-tauri/target/release/bundle"
    $files = @()
    if (Test-Path "$releaseDir/bikemaster-desktop.exe") {
        $files += "$releaseDir/bikemaster-desktop.exe"
    }
    foreach ($sub in @("msi", "nsis")) {
        $dir = "$bundleDir/$sub"
        if (Test-Path $dir) {
            $files += Get-ChildItem $dir -Filter "*.msi", "*.exe" | Select-Object -ExpandProperty FullName
        }
    }
}

foreach ($file in $files) {
    if (-not (Test-Path $file)) { continue }
    Write-Host "Signing: $file"
    & $SignTool sign /f $PfxPath /p $PfxPassword /fd SHA256 /tr $TimestampServer /td SHA256 /v "$file"
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Signing failed for: $file (exit code $LASTEXITCODE)"
    } else {
        Write-Host "Signed OK: $file"
    }
}

Write-Host "`nDone. Verify with:"
Write-Host "  signtool verify /pa /v <file.exe>"
