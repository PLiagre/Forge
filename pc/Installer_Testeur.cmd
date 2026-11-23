@echo off
chcp 65001 >nul
rem Inscrit la tâche planifiée « ForgeTesteur », une fois : c'est par elle que le
rem testeur de la chaîne joue un build dans cette session Windows, la seule où le
rem jeu a un écran. Sans horaire, sans élévation, sans mot de passe.
rem   pc\Installer_Testeur.cmd            inscrire, ou réinscrire
rem   pc\Installer_Testeur.cmd -Retirer   la retirer
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer_testeur.ps1" %*
if errorlevel 1 pause
