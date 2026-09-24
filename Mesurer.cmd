@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File outilstelier.ps1 mesurer
pause
