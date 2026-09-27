@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File outils\atelier.ps1 mesurer
pause
