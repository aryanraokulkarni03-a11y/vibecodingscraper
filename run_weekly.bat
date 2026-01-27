@echo off
cd /d "%~dp0"

echo ==========================================
echo   Vibe-Coding Trend Scraper - Weekly Run
echo ==========================================
echo.

:: 1. Check/Create Virtual Environment
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)

:: 2. Activate Virtual Environment
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment broken. Please delete .venv folder and try again.
    pause
    exit /b 1
)

:: 3. Check Dependencies
python -c "import rich" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    :: Install playwright browsers if needed
    playwright install
)

:: 4. Run the orchestrator
echo [INFO] Starting scraper system...
echo.
python execution/run_weekly.py

:: Pause to keep window open
echo.
echo ==========================================
echo   Run Complete. Closing in 60 seconds...
timeout /t 60
