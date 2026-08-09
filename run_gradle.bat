@echo off
set "JAVA_HOME=C:\Program Files\Microsoft\jdk-17.0.20.8-hotspot"
cd /d D:\BikeMaster\frontend\src-tauri\gen\android
call D:\BikeMaster\frontend\src-tauri\gen\android\gradlew.bat assembleDebug
