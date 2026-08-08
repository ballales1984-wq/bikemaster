@echo off
set NDK_HOME=D:\BikeMaster\android-sdk\ndk\27.0.0
set ANDROID_HOME=D:\BikeMaster\android-sdk
set JAVA_HOME=C:\Program Files\Microsoft\jdk-17.0.20.8-hotspot
set PATH=C:\Program Files\Actian\VectorAI DB\dashboard;C:\Users\user\.cargo\bin;%PATH%
cd /d D:\BikeMaster\frontend
npm run tauri android build
