@echo off
echo Starting MCTV Elite Advertising Bot...
echo.
cd /d "%~dp0"
python -m streamlit run app.py
pause
