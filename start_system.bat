@echo off
title StandSpec AI — System Launcher
echo ======================================================================
echo           StandSpec AI — Indian Standards Procurement Platform
echo ======================================================================
echo.
echo [1/2] Launching StandSpec FastAPI Backend Server (Port 8000)...
start "StandSpec AI Backend (FastAPI)" cmd /k "python run_backend.py"

echo [2/2] Launching StandSpec React Frontend Dev Server (Port 5173)...
start "StandSpec AI Frontend (Vite)" cmd /k "cd frontend && npm run dev"

echo.
echo ======================================================================
echo System successfully initiated!
echo  - Frontend Web UI:  http://localhost:5173
echo  - Backend REST API: http://127.0.0.1:8000
echo  - Swagger API Docs: http://127.0.0.1:8000/docs
echo ======================================================================
pause
