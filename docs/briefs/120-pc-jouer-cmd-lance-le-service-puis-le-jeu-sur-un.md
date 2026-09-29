# Lot #120 — pc\Jouer.cmd lance le service, puis le jeu sur une cellule du désert
Jalon : J1 · Machine : pc · Taille prévue : 290 lignes

## But
Le joueur double-clique `pc\Jouer.cmd` : le service de `sim/` démarre, le lanceur attend qu'il réponde, puis ouvre le dernier build sur une cellule chaude du sud de la carte, choisie par une règle lue dans les données, et le service s'arrête quand le jeu se ferme. C'est le premier geste du jalon J1 (CAP.md : « Le joueur lance `pc\Jouer.cmd`, choisit une cellule du monde (par défaut un lieu du désert…) et regarde »).

## Règle du monde
Sans objet pour le tick : c'est un lot d'outil. Le lanceur ne décide aucun nombre du monde, ne touche ni le moteur, ni `service.py`, ni `MODELE.md`. Niveau de fidélité du choix de la cellule : 1 (juste dans les grandes lignes : la cellule la plus ensoleillée de la carte est au sud).

Ce qu'il respecte de [`jeu/sim/MODELE.md`](../../jeu/sim/MODELE.md) et d'AGENTS.md :

- **`cell_id` est la seule clé spatiale** : le jeu reçoit `-forgeCell <cell_id>`, l'entier de `data/world-1400.json`. Aucun nom de lieu, aucune seconde clé.
- **Une référence se dérive des données** (AGENTS.md § 4) : la carte ne porte aucune température ; la seule mesure de chaleur qu'elle porte est `climat.insolation_annuelle_mj_m2` (couche climat, que le tick joue : MODELE.md, « Ce que le moteur ne fait pas encore », la sonde des couches). La règle : **la cellule dont l'insolation annuelle est la plus forte ; à égalité, le plus petit `cell_id`.** Sur la carte d'aujourd'hui, elle tombe sur la rive sud-est de la Méditerranée (≈ 30,4° N, 32,5° E, plaine littorale, ~160 000 habitants au tick 0) ; le code et la doc **n'écrivent pas** ce numéro, ils le calculent.
- **Une absence se déclare** : une cellule sans `climat.insolation_annuelle_mj_m2`, ou une carte sans cellule, fait lever une `ValueError` qui nomme la clé et le `cell_id` ; jamais de valeur par défaut, jamais de repli sur une cellule écrite à la main.

## Périmètre
pc/Jouer.cmd
pc/jouer.py
jeu/ville/cellule_du_desert.py
jeu/ville/README.md
jeu/ville/tests/test_cellule_du_desert.py
jeu/ville/tests/test_lanceur_jouer.py

Précisions (bibliothèque standard seule, partout ; tout littéral numérique autre que 0, 1, -1 est une constante nommée au niveau du module) :

- **`jeu/ville/cellule_du_desert.py`** (~40 lignes) : `choisir(monde: dict) -> int` applique la règle ci-dessus au document de la carte (`monde["cellules"]`) ; `charger_et_choisir(chemin: Path = <jeu/data/world-1400.json>) -> int` lit le fichier puis appelle `choisir`. Lancé en script (`py ville/cellule_du_desert.py` depuis `jeu/`), il écrit le `cell_id` seul sur une ligne. `jeu/ville/` n'a pas de `__init__.py` et n'en gagne pas : `pc/jouer.py` charge ce fichier par son chemin (`importlib.util.spec_from_file_location`), les tests aussi.
- **`pc/jouer.py`** (~90 lignes), tout ce que fait le lanceur, pour qu'il se prouve sous Linux comme sous Windows :
  ```
  py pc\jouer.py [--port P] [--cellule C] -- <commande du jeu…>
  ```
  1. `--cellule` absent → `charger_et_choisir()` ; présent → entier ≥ 0, sinon refus (argparse) qui nomme `--cellule` et la valeur. `--port` absent → `DEFAULT_SERVICE_PORT` **importé** de `sim.service` (8000, le port que lit `PanneauLieu`) ; jamais recopié.
  2. Le premier mot de la commande du jeu n'existe pas (ni fichier, ni `shutil.which`) → message qui nomme le chemin et dit que le build nocturne le dépose dans `builds\dernier\`, code 1, **service jamais démarré**.
  3. Quelque chose répond déjà sur `127.0.0.1:P` (une connexion TCP aboutit) → refus, code 1, qui nomme le port : sous Windows, `SO_REUSEADDR` laisserait un second service se lier au même port, et le jeu lirait un autre monde que le nôtre.
  4. Démarre `sys.executable -m sim.service --port P` avec `cwd` = `jeu/` (dérivé de `Path(__file__)`), sans `--seed` ni `--jours-par-seconde` (les défauts du service : un jour par seconde). Attend la ligne `service prêt sur 127.0.0.1:P` au plus `DELAI_SERVICE_PRET_S = 60` s (lecture dans un fil, pour ne pas bloquer au-delà du délai), puis exige que `GET /lieu?cell=C` rende 200. Service mort, délai dépassé ou autre statut → message qui nomme la cause (et le corps ou la fin de stderr reçus), service arrêté, code 1, **jeu jamais lancé**.
  5. Lance `<commande du jeu…> -forgeCell C` et attend sa fin.
  6. Dans un `finally` (fin du jeu, erreur, `KeyboardInterrupt`) : `terminate()`, attente de `DELAI_ARRET_S = 5` s, puis `kill()` si besoin. Rend le code de sortie du jeu.
  Il écrit une ligne par étape (`cellule C`, `service prêt sur 127.0.0.1:P`, `jeu fermé (code N)`, `service arrêté`), jamais de nombre du monde.
- **`pc/Jouer.cmd`** garde son en-tête (`@echo off`, `chcp 65001`, le commentaire du build nocturne) et nomme ses cibles par des lignes `set "NOM=..."` que `verifier_lanceurs.py` sait déjà lire : `JEU` (`%~dp0..\builds\dernier\Forge.exe`, seul attendu plus tard), `LANCEUR` (`%~dp0jouer.py`), `SERVICE` (`%~dp0..\jeu\sim\service.py`), `REGLE` (`%~dp0..\jeu\ville\cellule_du_desert.py`). Il appelle `py "%LANCEUR%" %* -- "%JEU%"` (les arguments du joueur, par exemple `--cellule 1175`, passent au lanceur) ; si le code de retour n'est pas 0, `pause` pour que le joueur lise la cause. Jamais `python` nu.
- **`jeu/ville/README.md`** : une section « La cellule par défaut du lanceur » qui dit la règle, pourquoi l'insolation (seule mesure de chaleur de la carte), l'égalité, les refus, la commande `py ville/cellule_du_desert.py`, et comment en choisir une autre (`pc\Jouer.cmd --cellule <cell_id>`). Elle n'écrit pas le numéro obtenu. Une ligne s'ajoute au tableau des fichiers.
- Les deux fichiers de tests vivent dans `jeu/ville/tests/` parce que la CI y joue tout dossier de tests de `jeu/` (étape « Les autres tests du jeu ») et que `pc\Tests.cmd` joue `py -m pytest jeu -q` : un test hors de `jeu/` ne protégerait rien.

## Conditions de succès

**SC1 — la cellule par défaut est dérivée de la carte, jamais écrite (VPS ou PC).**
```
python3 -m pytest jeu/ville/tests/test_cellule_du_desert.py -q
```
Passe, avec au moins ces cas :
- `choisir` sur la vraie carte rend le `cell_id` que le test recalcule **indépendamment** (tri des cellules par `(-insolation, cell_id)`) ; cette cellule est dans le **dixième le plus au sud** de la carte (sa `centroid.lat` ≤ le 10e centile des latitudes, calculé sur les données) ; et le monde du moteur (`World.charger(rng_seed=0)`) lui donne une population > 0 : le lieu est vivant ;
- le texte de `cellule_du_desert.py` et celui de `pc/jouer.py` ne contiennent **pas** ce `cell_id` écrit en chiffres ;
- `py ville/cellule_du_desert.py` (lancé par `subprocess` avec `sys.executable`, `cwd` = `jeu/`) écrit exactement ce `cell_id` et sort à 0.
Contre-épreuves, dans le même fichier : sur une copie de la carte où la cellule **la plus au nord** reçoit l'insolation maximale + 1, `choisir` rend cette cellule-là (le choix suit les données) ; deux cellules à égalité au maximum → le plus petit `cell_id` ; une cellule privée de `insolation_annuelle_mj_m2` → `ValueError` qui nomme la clé et son `cell_id` ; `{"cellules": []}` → `ValueError`.

**SC2 — lancé avec un faux jeu, le service répond, puis s'arrête quand le jeu se ferme (VPS ou PC).**
```
python3 -m pytest jeu/ville/tests/test_lanceur_jouer.py -q
```
Le faux jeu est un script Python écrit par le test dans `tmp_path`, lancé comme `[sys.executable, faux_jeu.py, <fichier de sortie>]` ; il lit `-forgeCell` dans ses arguments, fait `GET /lieu?cell=<C>` puis `GET /horloge` deux fois à 1,5 s d'écart, écrit ce qu'il a reçu (statuts, `cell_id`, les deux `tick`) dans le fichier de sortie, et sort avec le code demandé par le test. Le port est un port libre (socket liée au port 0 puis refermée), passé en `--port`. Cas :
- **le chemin nominal** : `sys.executable pc/jouer.py --port P -- <faux jeu>` sort à 0 ; le faux jeu a reçu `-forgeCell` égal à `charger_et_choisir()`, un `200` dont le `cell_id` est cette cellule, et un second `tick` **strictement plus grand** que le premier (l'horloge tourne) ; **après** la sortie du lanceur, une connexion à `127.0.0.1:P` est refusée (le service est arrêté). Ce contrôle d'arrêt est une fonction unique du test ; contre-épreuve dans le même cas : appliquée **pendant** que le faux jeu tourne (le faux jeu la note lui-même avant de sortir), elle dit « répond ».
- **le jeu plante** : faux jeu qui sort à 3 → le lanceur rend 3, et le port est refusé ensuite.
- **`--cellule 1175`** → le faux jeu reçoit `-forgeCell 1175` et un `200` dont le `cell_id` vaut 1175. `--cellule 99999999` (absent de la carte) → le lanceur sort non nul, le message contient `99999999` et `404`, le fichier de sortie du faux jeu **n'existe pas**, le port est refusé ensuite.
- **pas de build** : commande du jeu `tmp_path / "Forge.exe"` inexistant → sortie non nulle, le message nomme ce chemin et `builds`, le port n'a jamais répondu (aucun service démarré : le port reste refusé pendant et après).
- **port déjà pris** : le test écoute lui-même sur P → sortie non nulle, le message nomme P, le faux jeu n'a pas tourné.
- **le même port partout** : la valeur par défaut de `--port` de `jouer.py` est `sim.service.DEFAULT_SERVICE_PORT`, et égale la constante `DEFAULT_SERVICE_PORT` lue par expression régulière dans `3d/unity/Assets/ForgeLocal3D/Pont/PanneauLieu.cs` (fichier absent ou constante introuvable → échec qui le nomme).

**SC3 — `py pc/verifier_lanceurs.py` vérifie le lanceur (PC, puis VPS).**
```
py pc\verifier_lanceurs.py
```
Code 0 ; la sortie liste pour `Jouer.cmd` les cibles `LANCEUR`, `SERVICE` et `REGLE` à `ok`, et `JEU` à `ok` ou `absent (produit par le build nocturne)`. `verifier_lanceurs.py` **ne change pas**. Contre-épreuve, à la main et dite dans la PR : renommer temporairement `pc/jouer.py` fait sortir le vérificateur à 1 avec `LANCEUR  MANQUANT` ; le remettre le rétablit.

**SC4 — le vrai lanceur sur le PC.**
Sur le PC Windows, depuis `D:\Forge` : `py -m pytest jeu/ville/tests -q` passe (`terminate` et `SO_REUSEADDR` s'y comportent autrement que sous Linux : c'est là que SC2 compte). Puis, si `builds\dernier\Forge.exe` existe, `pc\Jouer.cmd` ouvre la scène du désert, le panneau montre la cellule choisie et un tick qui avance ; à la fermeture du jeu, `curl http://127.0.0.1:8000/horloge` échoue (connexion refusée). La PR dit ce qui a été joué, et si le build manquait, elle le dit au lieu de conclure.

**SC5 — rien d'autre ne bouge.**
```
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC (pc\Tests.cmd)
git diff --name-only origin/master...HEAD
```
La suite du jeu reste verte (`test_contrat_cell_id.py`, `test_no_hardcoded.py` compris). Le diff ne nomme que des chemins du périmètre (plus ce brief).

## Hors périmètre
- modifier `PanneauLieu.cs` (son défaut 1175, son port sérialisé), la scène, ou tout C# : le lanceur passe toujours `-forgeCell`, le défaut du panneau ne sert qu'à l'éditeur ;
- modifier `jeu/sim/service.py` (sa graine, sa vitesse, son port), le moteur, `MODELE.md`, `data/world-1400.json` ;
- modifier `pc/verifier_lanceurs.py`, `pc/Tests.cmd` ou les autres lanceurs ;
- choisir la cellule dans le jeu (un menu), régler la vitesse ou la pause depuis le lanceur ;
- arrêter le service quand la **console** est fermée de force (croix de la fenêtre, arrêt du processus `py`) : objet de travail Windows, lot suivant si le besoin se voit ;
- embarquer Python « embeddable » avec le build ; le build nocturne lui-même ;
- l'épreuve de bout en bout du jalon contre `--snapshot-json` et sa capture au journal ;
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
