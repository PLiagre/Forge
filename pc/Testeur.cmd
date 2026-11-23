@echo off
chcp 65001 >nul
rem Un passage du testeur, dans la session Windows ouverte du propriétaire : le
rem seul endroit du PC où le jeu a un écran. La tâche planifiée « ForgeTesteur »
rem le lance (pc\Installer_Testeur.cmd l'inscrit, une fois), et c'est le runner
rem de la chaîne qui la démarre (testeur-pc.yml). Il attend que l'écran soit
rem libre, joue le build figé de l'étape, et répond sur son issue.
rem
rem À la main : pc\Testeur.cmd --sonde            l'écran est-il libre ?
rem             pc\Testeur.cmd --palier 2 --maintenant --sans-publier
setlocal
set "ici=%~dp0"
set "passage=D:\Forge\.atelier\testeur"
if not exist "%passage%" mkdir "%passage%"
rem La demande du runner : un mot (jouer, sonde), jamais une commande.
set "mode=jouer"
if exist "%passage%\demande.txt" set /p mode=<"%passage%\demande.txt"
set "arguments=--depot-local D:\Forge"
if /i "%mode%"=="sonde" set "arguments=--sonde"
if not "%~1"=="" set "arguments=%*"
set PATH=%USERPROFILE%\.local\bin;%APPDATA%\npm;%PATH%
set PYTHONUTF8=1
set PYTHONPATH=%ici%..
rem Le code de la chaîne est celui de ce dossier, pas celui du dossier d'où l'on appelle.
cd /d "%ici%.."
del "%passage%\passage.code" 2>nul
py -m atelier --projet "%ici%.." testeur %arguments% > "%passage%\passage.log" 2>&1
echo %ERRORLEVEL%> "%passage%\passage.code"
if not "%~1"=="" type "%passage%\passage.log"
