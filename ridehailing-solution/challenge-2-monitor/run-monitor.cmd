@echo off
setlocal

set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..\..
set VENV_PY=%REPO_ROOT%\.venv\Scripts\python.exe

if not exist "%VENV_PY%" (
  echo [ERROR] Virtual environment Python not found:
  echo         %VENV_PY%
  echo Please create the venv first.
  pause
  exit /b 1
)

cd /d "%SCRIPT_DIR%"
"%VENV_PY%" "%SCRIPT_DIR%monitor.py"
echo.
echo monitor.py finished with exit code %ERRORLEVEL%.
pause
