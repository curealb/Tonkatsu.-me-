@echo off
cd /d "%~dp0"
python preview.py
if errorlevel 1 pause
