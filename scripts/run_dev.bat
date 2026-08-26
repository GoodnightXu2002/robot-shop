@echo off
setlocal

cd /d "%~dp0\.."

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo Running local project check...
"%PYTHON%" scripts\check_project.py
if errorlevel 1 (
    echo.
    echo Project check failed. Please fix the messages above before starting Flask.
    exit /b 1
)

echo.
echo Starting Robot Shop at http://127.0.0.1:5000
"%PYTHON%" app.py
