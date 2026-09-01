@echo off
REM ==============================================================================
REM AutoTask - Quick Start (no NSSM needed)
REM Opens backend and frontend in separate windows.
REM NOTE: Closing these windows will stop the app.
REM       Use install_services.ps1 for "run forever" with auto-restart.
REM ==============================================================================

set PROJECT_ROOT=C:\Autotask\Autotask
set BACKEND_DIR=%PROJECT_ROOT%\backend
set FRONTEND_DIR=%PROJECT_ROOT%\frontend
set PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe
set UVICORN=%PROJECT_ROOT%\.venv\Scripts\uvicorn.exe

echo Starting AutoTask Backend on port 8001...
start "AutoTask Backend" cmd /k "cd /d %BACKEND_DIR% && %UVICORN% main:app --host 0.0.0.0 --port 8001"

echo Building and starting AutoTask Frontend on port 5173...
start "AutoTask Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run build && npm run preview -- --host 0.0.0.0 --port 5173"

echo.
echo Both services started in separate windows.
echo Backend:  http://13.202.236.112:8001
echo Frontend: http://13.202.236.112:5173
echo.
echo Close those windows to stop the app, or use Ctrl+C inside each window.
pause
