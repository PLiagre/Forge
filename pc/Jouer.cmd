@echo off
chcp 65001 >nul
rem Lance le dernier build Windows du jeu, fait chaque nuit par le runner du PC
rem dans D:\Forge\builds\dernier (jamais publié : il embarque les packs de l'Asset Store).
set "JEU=%~dp0..\builds\dernier\Forge.exe"
if not exist "%JEU%" (
  echo Aucun build : %JEU%
  echo Le build nocturne le dépose ; pc\Ouvrir_Unity.cmd ouvre le projet en attendant.
  pause
  exit /b 1
)
start "" "%JEU%"
