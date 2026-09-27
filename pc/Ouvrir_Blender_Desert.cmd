@echo off
chcp 65001 >nul
rem Ouvre la source Blender du ksar du désert (refaite par py 3d\local3d\atelier_desert.py si absente).
set "BLENDER=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
set "SCENE=%~dp0..\3d\local3d\desert\sorties\villages\ksar_des_sept_puits\ksar_des_sept_puits.blend"
if not exist "%BLENDER%" (
  echo Blender 5.2 introuvable : %BLENDER%
  pause
  exit /b 1
)
if not exist "%SCENE%" (
  echo Scène absente : %SCENE%
  echo Elle n'est pas versionnée : py 3d\local3d\atelier_desert.py la refait.
  pause
  exit /b 1
)
start "" "%BLENDER%" "%SCENE%"
