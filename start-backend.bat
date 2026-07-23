@echo off
echo Building frontend...
cd frontend
call npm run build
cd ..

echo Deploying frontend to backend static directory...
robocopy frontend\dist bike_analyzer\backend\static /E /NFL /NDL /NJH /NJS /nc /ns /np

echo Starting BikeMaster backend on port 8000...
start "BikeMasterBackend" /b C:\Python314\Scripts\uvicorn.exe bike_analyzer.backend.api.app_factory:create_app --factory --app-dir D:\BikeMaster --host 0.0.0.0 --port 8000
