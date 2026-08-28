@echo off
REM One-click launcher: build the dashboard if needed, start the backend, open the browser.
cd /d "%~dp0"

where python >nul 2>nul || (echo Python not found on PATH. & pause & exit /b 1)

if not exist "dashboard\dist\index.html" (
  echo Building dashboard for the first time...
  pushd dashboard
  call npm install || (echo npm install failed & popd & pause & exit /b 1)
  call npm run build || (echo build failed & popd & pause & exit /b 1)
  popd
)

echo Starting FaultLine at http://localhost:8000
start "" http://localhost:8000
python src\dashboard_api.py
