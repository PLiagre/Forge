@echo off
chcp 65001 >nul
rem Ouvre le projet Unity du jeu (3d\unity) sur la scène du désert, en mode Play.
set "UNITY=C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe"
if not exist "%UNITY%" (
  echo Unity 6000.0.43f1 introuvable : %UNITY%
  pause
  exit /b 1
)
start "" "%UNITY%" -projectPath "%~dp0..\3d\unity" -executeMethod ForgeLocal3D.DesertBuilder.OpenPlay
