@echo off
chcp 65001 >nul
rem Lance le dernier build Windows du jeu, fait chaque nuit par le runner du PC
rem dans D:\Forge\builds\dernier (jamais publié : il embarque les packs de l'Asset Store).
rem Le lanceur démarre d'abord le service de jeu\sim, ouvre le jeu sur la cellule
rem la plus ensoleillée de la carte (ou celle de --cellule <cell_id>), et arrête
rem le service quand le jeu se ferme. Avec --carte, le jeu s'ouvre sur la carte de 1400.
set "JEU=%~dp0..\builds\dernier\Forge.exe"
set "LANCEUR=%~dp0jouer.py"
set "SERVICE=%~dp0..\jeu\sim\service.py"
set "REGLE=%~dp0..\jeu\ville\cellule_du_desert.py"
py "%LANCEUR%" %* -- "%JEU%"
if errorlevel 1 pause
