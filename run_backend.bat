@echo off
cd /d C:\Autotask\Autotask
C:\Autotask\Autotask\.venv\Scripts\uvicorn.exe backend.main:app --host 0.0.0.0 --port 8001
