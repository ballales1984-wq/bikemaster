@echo off
set JAVA_HOME=C:\Program Files\Microsoft\jdk-17.0.20.8-hotspot
set ANDROID_HOME=D:\BikeMaster\android-sdk
set NDK_HOME=D:\BikeMaster\android-sdk\ndk\27.0.0
"D:\BikeMaster\android-sdk\cmdline-tools\latest\bin\sdkmanager.bat" "platforms;android-34" "build-tools;34.0.0" --sdk_root="D:\BikeMaster\android-sdk"
