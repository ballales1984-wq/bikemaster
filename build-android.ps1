$env:ANDROID_HOME = "C:\Users\user\AppData\Local\Android\Sdk"
$env:NDK_HOME = "C:\Users\user\AppData\Local\Android\Sdk\ndk\27.1.12297006"
$env:JAVA_HOME = "C:\Program Files\Microsoft\jdk-17.0.16.8-hotspot"
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:NODE_OPTIONS = "--require D:\BikeMaster\symlink-patch.js"
Set-Location D:\BikeMaster\frontend

# Workaround for exFAT: Tauri cannot create symlinks on exFAT drives.
# Copy the .so to jniLibs before running Tauri, then run Gradle directly.
$SO_SRC = "D:\BikeMaster\frontend\src-tauri\target\aarch64-linux-android\release\libbikemaster_desktop_lib.so"
$SO_DST = "D:\BikeMaster\frontend\src-tauri\gen\android\app/src/main/jniLibs/arm64-v8a/libbikemaster_desktop_lib.so"

if (Test-Path $SO_SRC) {
    $jniDir = Split-Path $SO_DST -Parent
    if (!(Test-Path $jniDir)) { New-Item -ItemType Directory -Path $jniDir -Force | Out-Null }
    Copy-Item -Path $SO_SRC -Destination $SO_DST -Force
    Write-Host "Copied .so to jniLibs: $SO_DST"
} else {
    Write-Warning ".so not found at $SO_SRC — run 'npm run tauri android build' first to compile Rust"
}

npm run tauri android build 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tauri build failed (likely symlink on exFAT). Retrying with direct Gradle..." -ForegroundColor Yellow
    Set-Location D:\BikeMaster\frontend\src-tauri\gen\android
    Copy-Item -Path $SO_SRC -Destination $SO_DST -Force
    .\gradlew.bat assembleRelease 2>&1
}
