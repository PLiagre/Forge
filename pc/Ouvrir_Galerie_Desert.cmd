@echo off
chcp 65001 >nul
rem Ouvre la galerie des captures du désert dans le navigateur.
set "GALERIE=%~dp0..\3d\local3d\desert\sorties\index.html"
if not exist "%GALERIE%" (
  echo Galerie absente : %GALERIE%
  pause
  exit /b 1
)
start "" "%GALERIE%"
