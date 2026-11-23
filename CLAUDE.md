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

La CI joue deux suites. La **suite rapide** est celle qu'une PR doit passer :
tout sauf les preuves longues (une année du monde, dix ans), qui portent la
marque `longue` d'après leurs durées mesurées (`jeu/conftest.py`). La **nuit**
(`nuit.yml`) joue tout. Sur le PC, la suite rapide prend une minute et demie :

```bash
cd jeu && py -m pytest . -q -n 8 -m "not chronometre and not longue"
```

La suite entière (`python3 -m pytest jeu -q`) reste le travail de la nuit : sur
le VPS elle prend des heures et gêne tout le reste.

Unity, sur le PC seulement, une instance par dossier de projet : deux
worktrees ont chacun la leur, et elles tournent ensemble (détail et pièges
dans `3d/unity/CLAUDE.md`) :

```powershell
# les tests EditMode ; la liste se sépare par « ; », et on lit testcasecount dans le XML
& $unity -batchmode -projectPath 3d\unity -runTests -testPlatform EditMode -assemblyNames "Forge.Pont.Tests;Forge.Interface.Tests" -testResults $xml -logFile $journal
```

## Mesurer le jour

Ce que coûte un jour du monde, là où le jeu le paie (`ServeurMonde.jouer_un_tick()`,
publication comprise), phase par phase, avec et sans IA. Sur le PC seulement.

```bash
cd jeu && PYTHONUTF8=1 py mesure_du_jour.py              # le tableau : 365 jours, graine 0
cd jeu && PYTHONUTF8=1 py mesure_du_jour.py --profil 10  # les dix fonctions les plus chères
```

Le PC n'est jamais au repos : le même jour y coûte du simple au double d'une heure à
l'autre. Le chiffre avant et après d'une optimisation se prend donc contre un checkout
de référence, les deux jouant en même temps, et son témoin prouve que rien de ce qui
est servi n'a changé :

```bash
cd jeu && PYTHONUTF8=1 py mesure_du_jour.py --contre <référence>/jeu   # le gain, manche par manche
cd jeu && PYTHONUTF8=1 py mesure_du_jour.py --temoin                   # à comparer à celui de la référence
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

Le testeur joue un build figé par l'écran, sur le PC seulement, dans la
session ouverte ; il ne lance rien tant que le propriétaire est au clavier :

```powershell
pc\Testeur.cmd --sonde                                       # l'écran est-il libre ? ne lance rien
pc\Testeur.cmd --palier 2 --maintenant --sans-publier        # jouer builds\palier-2, le rapport s'affiche
```
