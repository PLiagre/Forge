@echo off
chcp 65001 >nul
rem Ouvre la fenêtre de disponibilité du PC pour la chaîne : charge du processeur,
rem interrupteur PC_ACTIF (la variable GitHub que lisent le pilote et les workflows
rem du PC), mode discret (priorité basse) et service du runner pc-forge.
set "PANNEAU=%~dp0disponibilite.py"
start "" pyw "%PANNEAU%"
