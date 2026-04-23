@echo off
echo ========================================
echo Vision Browser Agent - Installation
echo ========================================
echo.

echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo ========================================
echo Installation complete!
echo ========================================
echo.
echo To run the agent:
echo   1. GUI Mode:    python agent_ui.py
echo   2. Quick Test:  python quick_start.py
echo   3. Custom:      python browser_agent.py
echo.
pause
