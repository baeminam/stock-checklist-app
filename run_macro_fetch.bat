@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Fetching macro data from public APIs (a few seconds)...
echo.
python macro_data_fetch.py > "%TEMP%\moneytrend_macro.json"
if errorlevel 1 (
    echo.
    echo Error occurred. Please check that Python is installed and on PATH.
    pause
    exit /b 1
)
clip < "%TEMP%\moneytrend_macro.json"
echo.
echo ===================================================
echo  Done. Result copied to clipboard.
echo  Open the scorecard app - Auto-fetch tab - paste
echo  with Ctrl+V, then click "Apply text".
echo ===================================================
echo.
pause
