@echo off
chcp 65001 >nul
rem Lance le dernier build Windows du jeu, fait chaque nuit par le runner du PC
rem dans D:\Forge\builds\dernier (jamais publié : il embarque les packs de l'Asset Store).
rem Le lanceur démarre le service de jeu\sim, puis le jeu, et arrête le service à sa fermeture.
rem Sans --cellule, le jeu lit la maison du joueur : capitale, carte, ou absence dite.
rem --cellule <cell_id> impose une cellule ; --carte ouvre la carte de 1400.
set "JEU=%~dp0..\builds\dernier\Forge.exe"
set "LANCEUR=%~dp0jouer.py"
set "SERVICE=%~dp0..\jeu\sim\service.py"
py "%LANCEUR%" %* -- "%JEU%"
if errorlevel 1 pause
