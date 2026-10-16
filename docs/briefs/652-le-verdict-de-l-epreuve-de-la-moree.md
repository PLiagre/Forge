# Lot #652 — Le verdict de l'épreuve de la Morée
Jalon : J3 · Machine : pc · Taille prévue : 260 lignes

## But
Un script lance le service, fait jouer à Unity le choix de la Morée puis un second choix, pousse un tick et juge contre le monde : la terre cliquée est celle que le monde retient, le second choix est refusé pour la raison affichée, mot pour mot.

## Le joueur
Le joueur peut se fier à son geste : quand il clique sur la Morée sur la carte de 1400, le monde retient bien la terre cliquée, et quand il clique ensuite sur une autre terre, le monde refuse ce second choix pour la raison que le panneau lui affiche. C'est la preuve du geste « le joueur choisit sa terre sur la carte » (#404, jalon J3), dernier sous-lot de l'épreuve #615 : la session Unity de #651 joue le geste, ce lot dit s'il est vrai, et la contre-épreuve montre que le verdict rougit quand le monde retient une autre terre.

## Règle du monde
Sans objet : outil d'épreuve. Le script éprouve, sans les changer, les règles de `jeu/sim/MODELE.md`, section « Les intentions du joueur » : un `choisir_depart` accepté attend le tick suivant (`/monde` ne porte pas `maison_du_joueur` avant ce tick), `ChoixDepart.appliquer` pose alors `maison_du_joueur = "seigneurie-<n>"`, et un choix déjà en attente refuse le suivant par « départ déjà choisi : seigneurie-<n> » (409). Rien ne change dans `jeu/sim/` ni dans `3d/unity/`.

**Ce que le lot fait.** Un script, `pc/epreuve_moree.py`, sur le modèle exact de `pc/epreuve_carte.py` (#527), qu'il charge pour en reprendre `_lancer_service`, `_arreter`, `_requete` et `_impossible` (par `_charger`, comme `epreuve_carte` charge `jouer.py` et `epreuve_jalon1.py`) au lieu de les recopier.

```
py pc\epreuve_moree.py --sortie D [--terre N] [--seed S] [--unity CHEMIN]
```

1. **Avant tout** : Unity trouvé (`JALON1._unity_par_defaut()` ou `--unity`), port 8000 libre (`JOUER._repond`), sinon **2**. `D/rapport.json` et `D/verdict.txt` anciens effacés.
2. **La référence.** Service lancé (graine S, défaut 0, en pause) ; `GET /departs`. Par une fonction pure `terres(departs, terre)` → `(moree, cliquee, seconde)` (trois fiches de `/departs`) :
   - `moree` = la fiche dont `nom` vaut `MOREE = "Despotat de Morée"` (la Morée par son nom, jamais par son id) ; absente → `ValueError` ;
   - `cliquee` = la fiche d'id `--terre` si donné, sinon `moree` ; absente → `ValueError` ;
   - `seconde` = la première fiche servie dont l'id diffère de `cliquee`.
   Toute erreur de cette étape → **2** (« la référence n'a pas pu être lue au service : … »).
3. **La session de #651**, telle quelle :
   `Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveChoix.Jouer -logFile D/unity.log -forgeEpreuve D/rapport.json -forgeTerre <cliquee.id> -forgeSecondeTerre <seconde.id>`
   par `JALON1._unity`. Tout code non nul (1 = session impossible, 2 = arguments, ou délai dépassé) → **2** en citant la fin du journal, comme `epreuve_carte`. Rapport absent ou antérieur à l'essai (`JALON1.MARGE_HORODATAGE_S`) → **2**.
4. **Le monde, après la session** : `avant = GET /monde` ; `POST /tick?n=1` ; `apres = GET /monde`. Erreur → **2**. Le service est arrêté dans un `finally`.
5. **Le jugement**, par une fonction pure `juger(rapport, departs, avant, apres) -> (bool, list[str])`. Elle ne lit jamais `--terre` ni `rapport["terre"]` : l'attendu vient de la Morée servie, la contre-épreuve doit rougir par le monde. Avec `t = departs["tick"]`, `attendue = f"seigneurie-{moree['id']}"`, `bar` = la première fiche d'id ≠ `moree["id"]` (la seconde terre attendue) :
   - `rapport["defaut"]` non vide → écart, ligne « défaut : … », fin ;
   - `tick de la session : avant <tick_avant> · après <tick_apres> · /departs <t>` — égal si les deux valent `t` (la session n'a pas fait avancer le monde) ;
   - `maison avant le tick : /monde <avant.get("maison_du_joueur")!r> · attendu None` ;
   - `premier reçu : <statut> au tick <tick> « <raison> » · attendu 200 au tick <t> « »` ;
   - `second reçu : <statut> « <raison> » · attendu 409 « départ déjà choisi : <attendue> »` ;
   - `tick après la poussée : /monde <apres["tick"]> · attendu <t + 1>` ;
   - `maison après le tick : /monde <apres.get("maison_du_joueur")!r> · attendu <attendue>!r` ;
   - `premier texte : <premier_texte>!r · attendu <…>!r`, l'attendu étant `f"Terre choisie : {moree['nom']}\nLe monde l'applique au tick suivant (après le tick {t})."` ;
   - `second texte : <second_texte>!r · attendu <…>!r`, l'attendu étant `f"Choix refusé pour {bar['nom']} :\ndépart déjà choisi : {attendue}"`.
   Chaque ligne comparée finit par `· égal` ou `· ÉCART`, comme `epreuve_carte`. Les libellés sont ceux de `ReperesDeDepart.DireLeChoix` et de `deposer_intention`, en constantes du script.
6. **Le verdict** : `ÉGALITÉ` ou `ÉCART`, puis l'en-tête (`graine S`, `Morée servie : id 3 (Despotat de Morée)`, `terre cliquée par Unity : id N (<nom>)`, `seconde terre : id M (<nom>)`), puis les lignes du jugement, écrits dans `D/verdict.txt` et sur la sortie. **0** égalité, **1** écart, **2** épreuve impossible.

Mesuré sur master dd42e9c (rapports versés par #651, graine 0, service neuf en pause) : `/departs` sert au tick 0 les ids 1 à 6 dans l'ordre (1 Duché de Bar, 3 Despotat de Morée, 6 Émirat du Zab) ; la session rend 0 avec `premier` {200, 0, ""}, `second` {409, −1, "départ déjà choisi : seigneurie-3"} et les deux textes attendus ci-dessus. Avec `--terre 6`, Unity clique le Zab puis Bar : le premier reçu est accepté (200 au tick 0, donc égal), mais le second cite `seigneurie-6`, la maison après le tick est `seigneurie-6`, et le premier texte nomme l'Émirat du Zab : trois écarts.

## Périmètre
pc/epreuve_moree.py
jeu/ville/tests/test_epreuve_moree.py
jeu/ville/README.md
docs/mesures/615-epreuve-du-choix/verdict-normal.txt
docs/mesures/615-epreuve-du-choix/verdict-terre-6.txt

## Conditions de succès
SC1. **Le jugement est testé sur le VPS** : `python3 -m pytest jeu/ville/tests/test_epreuve_moree.py -q` passe. Le fichier charge `pc/epreuve_moree.py` comme `test_epreuve_carte.py` charge `epreuve_carte.py`, prend pour `/departs` la fixture servie `3d/unity/Assets/ForgeLocal3D/Pont/Tests/departs-graine0-tick3.json` (copiée, son `tick` mis à 0) et construit `avant` (`{"tick": 0, …}` sans `maison_du_joueur`) et `apres` (`{"tick": 1, …, "maison_du_joueur": …}`). Au moins ces cas :
- le rapport versé `docs/mesures/651-session-choix-moree/rapport-normal.json`, avec `apres` à `seigneurie-3`, est jugé égal, et chaque ligne comparée finit par « · égal » ;
- **la contre-épreuve du Zab** : un rapport de la session pour `-forgeTerre 6 -forgeSecondeTerre 1` (premier {200, 0, ""}, second {409, −1, "départ déjà choisi : seigneurie-6"}, textes de `DireLeChoix` pour le Zab et Bar), avec `apres` à `seigneurie-6`, est un écart ; les lignes « second reçu », « maison après le tick » et « premier texte » finissent par « ÉCART » et citent `seigneurie-6` ou « Émirat du Zab » ;
- le rapport versé `rapport-deja-choisi.json` (deux refus) est un écart sur « premier reçu » ;
- `avant` qui porte déjà `maison_du_joueur` est un écart sur « maison avant le tick » ;
- `tick_apres` à 1 (la session a fait avancer le monde) est un écart sur « tick de la session » ;
- paramétré : `premier_texte` avec « après le tick 1 », `second_texte` sans son saut de ligne, `second.raison` citant `seigneurie-1` — chacun un écart sur sa ligne (le texte est jugé mot pour mot) ;
- `defaut` non vide → écart dont la dernière ligne commence par « défaut : » ;
- `terres` sur un `/departs` sans la Morée lève `ValueError` ; `terres(departs, None)` rend la Morée, Morée, Bar et `terres(departs, 6)` la Morée, le Zab, Bar ;
- les libellés : chaque morceau de texte attendu (« Terre choisie : », « \nLe monde l'applique au tick suivant (après le tick », « Choix refusé pour », « départ déjà choisi : ») est présent dans `Pont/ReperesDeDepart.cs` ou `jeu/sim/intentions.py`, les champs du rapport (`tick_avant`, `tick_apres`, `premier`, `second`, `premier_texte`, `second_texte`, `defaut`) et les arguments `-forgeEpreuve`, `-forgeTerre`, `-forgeSecondeTerre` dans `Editor/EpreuveChoix.cs`, et `METHODE` y nomme l'espace, la classe et `public static void Jouer()` ;
- `main(["--sortie", …, "--unity", <chemin absent>])` rend 2 et nomme le chemin sur stderr.
Contre-épreuve : dans une copie de travail (non versée), remplacer dans `juger` l'attendu `attendue` par `apres.get("maison_du_joueur")` fait rougir le cas du Zab ; le codeur le montre dans la PR.

SC2. **L'épreuve réelle, sur le PC**, éditeur fermé, depuis la racine du dépôt : `py pc\epreuve_moree.py --sortie "$env:TEMP\lot652"` rend **0** ; le verdict commence par `ÉGALITÉ`, nomme `Morée servie : id 3 (Despotat de Morée)` et `seconde terre : id 1 (Duché de Bar)`, et porte `maison après le tick : /monde 'seigneurie-3' · attendu 'seigneurie-3' · égal`. Versé dans `docs/mesures/615-epreuve-du-choix/verdict-normal.txt`, précédé de trois lignes comme les verdicts de #527 : `commande : …`, `date : 2026-10-…, PC (…), Unity <version>, révision <sha>`, `code de sortie : 0`.

SC3. **La contre-épreuve réelle** : `py pc\epreuve_moree.py --sortie "$env:TEMP\lot652-zab" --terre 6` rend **1** ; le verdict commence par `ÉCART`, et ses lignes « second reçu » et « maison après le tick » citent `seigneurie-6` et finissent par « ÉCART ». Versé dans `verdict-terre-6.txt` avec le même en-tête (`code de sortie : 1`).

SC4. **L'impossible n'est jamais un écart** : sur le PC, un service lancé à la main sur le port 8000 avant le script (`py -m sim.service --seed 0 --jours-par-seconde 0`, depuis `jeu\`) fait rendre **2** au script, qui nomme le port pris, sans lancer Unity ; le codeur le montre dans la PR.

SC5. `jeu/ville/README.md` : une section « L'épreuve du choix », après « La session du choix de la terre » : ce que le joueur peut croire (une phrase), la commande, ce que fait le script (service en pause, `/departs`, la Morée par son nom, la seconde terre, la session de #651, `/monde` avant le tick, un tick, `/monde` après), ce qu'il juge, les codes 0 / 1 / 2, la contre-épreuve `--terre 6` et les liens vers les deux verdicts versés. Dans la section de la session, la phrase « le jugement est celui du script de #615, à venir, qui comparera au monde » renvoie désormais à cette section.

SC6. `python3 -m pytest jeu -q` passe en entier sur le VPS, et `git diff origin/master --stat` ne nomme que le Périmètre.

## Hors périmètre
- La session Unity `Editor/EpreuveChoix.cs` (#651), `ReperesDeDepart`, `SurvolDeCarte`, la scène `Forge_Carte` : inchangés. Si la session semble devoir changer, le dire dans la PR plutôt que l'écrire.
- `pc/epreuve_carte.py` et `pc/epreuve_jalon1.py` : chargés, pas modifiés.
- Une contre-épreuve sans service (déjà prouvée par la session de #651, code 1, que le script rend en 2).
- La descente de la caméra après le tick (#614) et toute capture.
- `jeu/sim/` : aucune règle du monde ne change.
- La preuve du jalon 3 (#406).

## Photo
sans objet : outil d'épreuve ; le script lance une session qui ne capture rien, et rien de ce que voit le joueur ne change. L'écran du refus est déjà la photo du lot 613 (`second-choix-refuse`).
