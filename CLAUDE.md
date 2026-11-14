# CLAUDE.md

Les règles du dépôt sont dans AGENTS.md, importé ici pour être chargé d'office :

@AGENTS.md

Chaque zone a ses règles et ses pièges, chargés quand on y travaille :
`jeu/sim/CLAUDE.md`, `3d/unity/CLAUDE.md`, `atelier/CLAUDE.md`.

## Tester

`python3` sur le VPS, `py` sur le PC. Sur le PC, toujours `PYTHONUTF8=1`,
`--basetemp=<un dossier à soi>` et `-p no:cacheprovider`.

```bash
# les tests de ce qu'on touche : un fichier, un nom
python3 -m pytest jeu/sim/tests/test_lieux.py -q -k ouverture
# les deux gardes du moteur, à jouer après tout changement de jeu/sim/
python3 -m pytest jeu/sim/tests/test_no_hardcoded.py jeu/sim/tests/test_write_coverage.py -q
# la chaîne
python3 -m pytest atelier/tests -q
```

La suite entière du jeu (`python3 -m pytest jeu -q`) est le travail de la CI :
sur le VPS elle prend près d'une heure et gêne tout le reste.

Unity, sur le PC seulement, une instance à la fois (détail et pièges dans
`3d/unity/CLAUDE.md`) :

```powershell
# les tests EditMode ; la liste se sépare par « ; », et on lit testcasecount dans le XML
& $unity -batchmode -projectPath 3d\unity -runTests -testPlatform EditMode -assemblyNames "Forge.Pont.Tests;Forge.Interface.Tests" -testResults $xml -logFile $journal
```

## Lancer le jeu

```bash
# une année du monde, sans écran : monde.json, carte.png, tableau.svg…
cd jeu && python3 -m forge --ticks 365 --seed 0 --sortie sortie
```

```powershell
# le dernier build de la nuit, sur la carte ; le lanceur démarre le service du monde
pc\Jouer.cmd --carte
# le build d'un worktree : le construire, puis le jouer avec son propre service
& $unity -batchmode -quit -projectPath 3d\unity -executeMethod ForgeLocal3D.Build.Nuit -forgeSortie D:\Forge\builds\<nom> -logFile $journal
py pc\jouer.py --carte -- D:\Forge\builds\<nom>\Forge.exe -screen-width 1920 -screen-height 1080 -screen-fullscreen 0
# ouvrir le projet dans l'éditeur, sur la ville du désert
pc\Ouvrir_Unity.cmd
```

`$unity` est `C:\Program Files\Unity\Hub\Editor\<version>\Editor\Unity.exe`,
la version étant celle de `3d/unity/ProjectSettings/ProjectVersion.txt`.

## La chaîne

```bash
python3 -m atelier agents          # les rôles, leurs modèles, leurs délais
python3 -m atelier tour --a-sec    # ce que le pilote ferait, sans rien faire
```
