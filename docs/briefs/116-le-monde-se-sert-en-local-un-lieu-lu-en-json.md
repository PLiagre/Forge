# Lot #116 — Le monde se sert en local : un lieu, lu en JSON
Jalon : J1 · Machine : vps · Taille prévue : 280 lignes

## But
`python3 -m sim.service` (depuis `jeu/`) tient le monde et son horloge dans un processus local et sert en JSON, sur 127.0.0.1, l'état d'une cellule au tick courant — exactement celui que porte la photographie du même tick —, de sorte que le client Unity du jalon J1 lise les vrais chiffres de `sim/` au lieu d'une copie.

## Règle du monde
Sans objet : c'est un lot d'outil. Le service est un regard (CAP.md, jalon 1 : « Ce que le jalon change dans le monde : rien »). Il n'ajoute aucune règle, aucune constante du monde, aucun champ à `Cell` ni à `World`, et ne touche ni `engine.py`, ni `world.py`, ni `model.py`, ni `snapshot_export.py`, ni `MODELE.md`. Fidélité : sans objet.

Ce qu'il doit respecter du modèle (`jeu/sim/MODELE.md`, « La base de temps » et « En une page ») :

- **Un seul moteur.** Le monde se charge et avance comme dans `sim/__main__.py::_simulate` : `World.charger(rng_seed=S)`, un seul `random.Random(S)` créé au démarrage et consommé par tous les ticks successifs, chaque tick joué par `tick(world, rng, world.ticks_ecoules)`. Ainsi `POST /tick?n=2` puis `POST /tick?n=3` donnent le même monde que `python3 -m sim --ticks 5 --seed S`.
- **`cell_id` est la seule clé spatiale.** `/lieu` se lit par `cell`, un entier `cell_id` ; aucun `cityId`, aucun nom, aucune seconde clé.
- **Le numéro du tick suivant est `world.ticks_ecoules`** : c'est le `numero_tick` que `tick()` exige. Une intention reçue quand le monde a joué N ticks sera appliquée au tick numéroté N (le (N+1)-ième joué) ; le service le répond sous la clé `appliquee_au_tick`, dérivée du compteur, jamais calculée à part.
- **Rien ne se devine** (AGENTS.md, § 4) : paramètre absent, non entier ou inconnu → refus qui nomme la valeur reçue ; le monde n'est pas touché.

## Périmètre
jeu/sim/service.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_determinisme.py
jeu/sim/tests/README.md
jeu/sim/README.md

## Conditions de succès

Forme attendue du service (`jeu/sim/service.py`, bibliothèque standard seule : `http.server`, `json`, `argparse`, `threading`, `urllib.parse`, `random`, `http`) :

- `python3 -m sim.service --seed S --port P` ; `--seed` et `--port` ont des défauts nommés au niveau du module. `--port 0` laisse le système choisir un port libre. Le service écoute sur `127.0.0.1` seulement et, une fois le monde chargé, écrit **sa première ligne** sur la sortie standard (vidée) : `service prêt sur 127.0.0.1:<port réel>`.
- Toutes les réponses sont du JSON UTF-8 sérialisé de façon canonique (`sort_keys=True`, `ensure_ascii=False`, `separators=(",", ":")`), avec `Content-Length`. Les codes HTTP viennent de `http.HTTPStatus` (aucun littéral numérique dans un corps de fonction : `test_no_hardcoded.py` inspecte tout `sim/*.py`). Un verrou sérialise lectures et ticks.
- `GET /lieu?cell=<cell_id>` → `{"cell_id", "population", "stocks", "hunger_ticks", "food_deficit_kg", "tick", "date"}` : les quatre champs d'état sont ceux de `cellule_vers_dict`, arrondis **par la fonction d'arrondi de `sim.snapshot_export`** (`_round_tree`, importée, pas recopiée) pour que les flottants soient ceux de la photographie ; `tick` = `world.ticks_ecoules` ; `date` = `world.date_simulation`.
- `GET /monde` → `{"tick", "date", "cell_count", "cells": [...]}` : une entrée par cellule, triée par `cell_id`, avec les mêmes quatre champs d'état et `cell_id` — ni géométrie, ni centroïde, ni climat, ni gisements.
- `POST /tick?n=N` → joue N ticks (N entier ≥ 1, obligatoire) et rend `{"tick", "date"}`.
- `POST /intention` (corps : un objet JSON) → `{"acceptee": true, "appliquee_au_tick": world.ticks_ecoules}`. L'intention n'est ni appliquée ni stockée dans le monde (jalon 2).
- Refus : cellule inconnue → 404 `{"erreur": "..."}` dont le texte contient le `cell_id` reçu ; `cell` absent ou non entier, `n` absent, non entier ou < 1, corps d'intention qui n'est pas un objet JSON → 400 avec un message qui nomme le paramètre ; chemin inconnu → 404. Aucun refus ne fait avancer l'horloge.

Les cas de test démarrent un **vrai** service en sous-processus (`sys.executable -m sim.service --seed S --port 0`, `cwd=jeu/`), lisent le port sur la première ligne, parlent HTTP avec `urllib.request`, et arrêtent le processus en fin de cas (y compris en échec). Le lanceur est défini une fois dans `test_monde.py` ; `test_determinisme.py` l'importe.

**SC1 — `/lieu` rend la photographie du même tick, et un décalage d'un tick se voit.**
`python3 -m pytest jeu/sim/tests/test_monde.py -q -k service` passe. Le cas principal, avec S = 0 et N = 3 :
- produit deux photographies par la vraie ligne de commande, `python3 -m sim --ticks N --seed S --snapshot-json <tmp>` et la même à N+1 ;
- **dérive** la cellule témoin des données : la première cellule (par `cell_id`) dont `population`, `stocks`, `hunger_ticks` ou `food_deficit_kg` diffère entre les photographies N et N+1 ; aucune cellule trouvée → échec (un échantillon vide échoue) ;
- démarre un service de graine S, `POST /tick?n=1` puis `POST /tick?n=2` (l'horloge se cumule), et exige pour **chaque** cellule de la photographie N que `/lieu` rende les quatre champs d'état égaux (`==` sur les valeurs JSON relues) à ceux de la photographie, `tick == N` et `date == constants.date_de_tick(N)` ;
- contre-épreuve dans le même cas : `POST /tick?n=1`, puis la même comparaison contre la photographie N pour la cellule témoin **doit échouer** (la fonction de comparaison lève), et la comparaison contre la photographie N+1 doit réussir.

**SC2 — rien ne se devine.**
Un cas `service` de `test_monde.py` exige : `GET /lieu?cell=999999` (un `cell_id` absent de la carte, vérifié absent dans le cas) → 404 dont le corps contient `999999` ; `GET /lieu` sans `cell` et `GET /lieu?cell=abc` → 400 ; `POST /tick` sans `n`, `n=0` et `n=abc` → 400 ; `POST /intention` avec un corps `[1]` ou `pas du json` → 400. Après ces refus, `GET /monde` rend `tick == 0`. Contre-épreuve : un `POST /tick?n=1` valide fait passer `tick` à 1.

**SC3 — `/monde` est léger et fidèle ; l'intention attend son tick.**
Un cas `service` de `test_monde.py` exige : `cell_count` de `/monde` égal au nombre de cellules de `World.lire_carte()` et à `len(cells)` ; aucune entrée ne porte `geometry` ni `centroid` ; la population de chaque entrée égale celle de `/lieu` pour la même cellule. `POST /intention` avec `{"route": "essai"}` après 2 ticks rend `appliquee_au_tick == 2`, et les octets de `GET /monde` avant et après l'intention sont identiques (elle n'a rien appliqué).

**SC4 — deux services de même graine rendent les mêmes octets.**
`python3 -m pytest jeu/sim/tests/test_determinisme.py -q -k service` passe : deux services de graine 0, soumis à la même suite (`POST /tick?n=3`, `GET /monde`, `GET /lieu` sur la cellule de plus petit `cell_id`), rendent des corps **identiques octet pour octet**. Contre-épreuve : un service de graine 1 soumis à la même suite rend un `/monde` différent.

**SC5 — bibliothèque standard seule.**
Un cas `service` de `test_monde.py` lit par `ast` les imports de `jeu/sim/service.py` et exige que chaque module de tête soit dans `sys.stdlib_module_names` ou soit `sim`. Contre-épreuve paramétrée sur la fonction de contrôle : un source qui importe `requests` doit être refusé.

**SC6 — rien d'autre ne bouge.**
`python3 -m pytest jeu -q` passe entier, `test_no_hardcoded.py` et `test_write_coverage.py` compris. `git diff --name-only origin/master` ne rend que les fichiers du périmètre (et ce brief). `git diff origin/master -- jeu/sim/tests/test_monde.py jeu/sim/tests/test_determinisme.py` ne montre que des ajouts. `jeu/sim/README.md` gagne la ligne `sim/service.py` dans la table des modules et la commande de lancement ; `jeu/sim/tests/README.md` dit que `test_monde.py` porte aussi « le service local rend la photographie ».

## Hors périmètre
- le client C#, le panneau Unity, `pc\Jouer.cmd`, l'épreuve sur le PC et sa capture (lots `pc` suivants du jalon J1) ;
- l'horloge autonome (un jour par seconde, pause, accélération) : ici le temps n'avance que sur `POST /tick` ;
- appliquer, valider ou stocker une intention (jalon 2) ;
- le contrat ville (`jeu/ville/`) et le retrait du `cityId` ;
- le lieu comme subdivision de la cellule (jalon 3) ; le bourg et la province ne sont pas servis par `/lieu` ;
- toute modification de `engine.py`, `world.py`, `model.py`, `constants.py`, `snapshot_export.py`, `__main__.py` ou `MODELE.md` ;
- servir sur une autre adresse que 127.0.0.1, l'authentification, le HTTPS ;
- recopier `docs/mesures/2026-09-27-pont/service_pont.py` (ni ses mesures de durée, ni `/mesures`, ni son `--racine`).
