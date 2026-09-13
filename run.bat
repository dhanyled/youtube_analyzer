@echo off
cd /d "%~dp0"
echo Membuka YouTube Search Intelligence Dashboard...
uv run python run_dashboard.py
pause
