$env:ANDROID_HOME = "C:\Users\user\AppData\Local\Android\Sdk"
$env:NDK_HOME = "C:\Users\user\AppData\Local\Android\Sdk\ndk\27.1.12297006"
$env:JAVA_HOME = "C:\Program Files\Microsoft\jdk-17.0.16.8-hotspot"
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:NODE_OPTIONS = "--require D:\BikeMaster\scratch\symlink-patch.js"

$NDK_BIN = "$env:NDK_HOME\toolchains\llvm\prebuilt\windows-x86_64\bin"
$env:CC_x86_64_linux_android = "$NDK_BIN\clang.exe"
$env:AR_x86_64_linux_android = "$NDK_BIN\llvm-ar.exe"
$env:PATH = "$NDK_BIN;$env:PATH"

$TAURI_DIR = "D:\BikeMaster\frontend\src-tauri"
$GEN_DIR = "D:\BikeMaster\frontend\src-tauri\gen\android"
$ANDROID_JNI = "$GEN_DIR\app/src/main/jniLibs"
$TARGET_DIR = "$TAURI_DIR\target"

Write-Host "=== Building Rust libraries for Android ==="

Write-Host "Building aarch64-linux-android (physical devices)..."
Push-Location $TAURI_DIR
cargo build --target aarch64-linux-android --release

Write-Host "Building x86_64-linux-android (emulators)..."
cargo build --target x86_64-linux-android --release --lib
Pop-Location

Write-Host "=== Copying native libraries to jniLibs ==="

$SO_ARM64 = "$TARGET_DIR\aarch64-linux-android\release\libbikemaster_desktop_lib.so"
$SO_X86_64 = "$TARGET_DIR\x86_64-linux-android\release\libbikemaster_desktop_lib.so"

# ARM64 (for physical Android devices)
if (Test-Path $SO_ARM64) {
    $arm64Dir = "$ANDROID_JNI\arm64-v8a"
    if (!(Test-Path $arm64Dir)) { New-Item -ItemType Directory -Path $arm64Dir -Force | Out-Null }
    Copy-Item -Path $SO_ARM64 -Destination "$arm64Dir\libbikemaster_desktop_lib.so" -Force
    Write-Host "Copied arm64-v8a .so"
}

# x86_64 (for Android emulators on x86 hosts)
if (Test-Path $SO_X86_64) {
    $x86_64Dir = "$ANDROID_JNI\x86_64"
    if (!(Test-Path $x86_64Dir)) { New-Item -ItemType Directory -Path $x86_64Dir -Force | Out-Null }
    Copy-Item -Path $SO_X86_64 -Destination "$x86_64Dir\libbikemaster_desktop_lib.so" -Force
    Write-Host "Copied x86_64 .so"
}

Write-Host "=== Building Android APK ==="
Set-Location $GEN_DIR
.\gradlew.bat assembleRelease

Write-Host "=== Build complete ==="
Get-ChildItem "$GEN_DIR\app/build/outputs/apk/release\*.apk" | Format-Table Name, Length, LastWriteTime
