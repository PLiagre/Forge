@echo off
chcp 65001 >nul
rem Joue les tests du jeu (sim, vues, commande forge), puis les lanceurs de ce dossier.
cd /d "%~dp0.."
py -m pytest jeu -q
if errorlevel 1 (
  echo Des tests du jeu sont rouges.
  pause
  exit /b 1
)
py pc\verifier_lanceurs.py
pause
