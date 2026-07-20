@echo off
start "BikeMasterBackend" /b C:\Python314\Scripts\uvicorn.exe bike_analyzer.backend.api.app_factory:create_app --factory --app-dir D:\BikeMaster --host 0.0.0.0 --port 8000
