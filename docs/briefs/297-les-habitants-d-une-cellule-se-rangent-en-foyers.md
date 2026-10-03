# Lot #297 — Les habitants d'une cellule se rangent en foyers par métier
Jalon : J4 · Machine : vps · Taille prévue : 280 lignes

## But
Chaque cellule du monde chargé sait combien de ses habitants sont mineurs et combien sont paysans, et les range en foyers. Sa population est toujours exactement la somme de ses métiers, quelle que soit la façon dont on l'écrit. C'est le premier pas de « la population cesse d'être un entier par lieu et se compte en foyers » (CAP.md, jalon 4). La preuve du jalon est ici : « cent personnes agrégées en foyers puis désagrégées font cent personnes ; un métier n'existe que si quelqu'un l'exerce ».

## Règle du monde
Elle découle de « Ce qu'est une ville, à l'échelle d'une cellule », sous-section « D'où vient la donnée » : les habitants occupés par la mine sont `part_miniere_de(gisements, facteurs_richesse_extraction())`, et ils ont cessé de cultiver. Elle découle aussi de « Population initiale par cellule » (l'amorçage) et de « Le moteur sans état caché » (les constantes se relisent par leur module). Le propriétaire a tranché l'amorçage sur #255 (réponse A) : on ne le repose pas.

Ce que le monde sait après ce lot :

- **Une cellule tient ses habitants par métier.** Le nouveau champ `Cell.habitants_par_metier` est un dictionnaire `métier → personnes` (entiers > 0). `population` est **exactement** leur somme. Un métier sans personne n'a pas d'entrée. Il n'y a ni `bourg_*`, ni `ville_*`, ni `city_*` : `cell_id` reste la seule clé spatiale.
- **L'amorçage (réponse A).** Dans `World.charger`, une fois la population de la cellule fixée (villes comprises) :
  - les mineurs valent `int(population × part_miniere_de(gisements, facteurs_richesse_extraction()))`, où les gisements sont ceux de la carte de la cellule (`raw.get("gisements") or []`) ;
  - les paysans sont le reste ;
  - un métier à zéro n'apparaît pas, et une cellule vide a `{}`.

  La part minière vient de **l'appel** à `constantes.part_miniere_de`. Aucune fonction ne lit `PART_MINIERE_PAR_GISEMENT` ni `PART_MINIERE_MAXIMALE`. À l'amorçage, les mineurs égalent donc `habitants_du_bourg` de la vue `bourg_depuis_monde`, cellule par cellule.
- **Ranger en foyers, et rendre.** Un foyer a une taille constante, `TAILLE_FOYER = 5` (niveau 2). Le module neuf `sim/foyers.py` porte :
  - `ranger_en_foyers(personnes)`, qui rend un `Foyers(taille, complets, dernier)` figé, avec `0 ≤ dernier < taille`. Le dernier foyer peut être incomplet ; `dernier == 0` veut dire qu'il n'y en a pas. Exemples : 100 → `(5, 20, 0)` et 103 → `(5, 20, 3)`.
  - `rendre_les_personnes(foyers)`, qui rend `complets × taille + dernier`. Aller puis revenir rend le nombre de départ, à l'identique.
  - La propriété `Foyers.nombre` vaut `complets + (1 si dernier > 0)`.
  - La taille se relit à chaque appel par `_constantes.TAILLE_FOYER`.
- **Toute écriture de la population se répartit, sans perdre ni créer personne.** `cell.population = N` (ou `+=`, `-=`) sur une cellule dont les métiers sont calculés passe par `foyers.repartir(habitants_par_metier, N)` :
  - Si `N` égale la somme, rien ne change.
  - S'il n'y a aucun métier (cellule vide), les `N` personnes sont paysannes ; `N = 0` donne `{}`.
  - Sinon, chaque métier reçoit `N × n_métier // somme` (calcul entier, aucun flottant). Le reste va au métier le plus nombreux ; à égalité, au nom le plus petit. Les métiers tombés à zéro disparaissent.

  L'interception vit dans `Cell` (un `__setattr__` sur `population`). Le moteur n'est pas modifié : ses écritures (mort, naissance, migration) et celles des tests existants (`test_monde.py`, `test_seigneuries.py`, `test_villes.py`, `test_survie.py`) passent par là telles quelles. La valeur de `population` ne change jamais d'un bit.
- **Une cellule construite sans métiers les déclare non calculés.** `Cell(...)` sans `habitants_par_metier` garde l'absence. Pour une telle cellule :
  - `lire_habitants_par_metier(cell)` (dans `sim/model.py`) rend la sentinelle `-1`, sinon une copie du dictionnaire ;
  - une écriture de sa population s'applique comme aujourd'hui, et ses métiers restent non calculés.

  Rien ne se devine. Lèvent `FoyersInvalides` (`ValueError`), en nommant ce qui manque :
  - un `Cell` construit avec des métiers dont la somme diffère de `population` ;
  - un compte de métier nul, négatif, booléen ou non entier, ou un nom de métier vide ;
  - une écriture négative ou non entière (booléen compris) sur une cellule amorcée ;
  - `ranger_en_foyers` sur un nombre de personnes négatif, booléen ou non entier ;
  - une `TAILLE_FOYER` non entière ou inférieure à 1 ;
  - un `Foyers` avec `dernier ≥ taille` ou une valeur négative.
- **Le monde sérialisé porte les foyers.** `cellule_vers_dict` ajoute la clé `"foyers"`. Elle vaut `-1` pour des métiers non calculés. Sinon, c'est un dictionnaire `métier → {"personnes", "complets", "dernier"}`, rangé par `ranger_en_foyers`. `World.to_dict()` le porte donc, et l'empreinte d'un monde change avec ses foyers. `/lieu`, `/monde` et la photographie ne changent pas d'un octet : ils choisissent leurs champs (`_CHAMPS_ETAT`, `CHAMPS_MOBILES`).
- **Le tick ne lit pas les métiers.** L'extraction reste `cell.population × part`, la vue du bourg reste ce qu'elle est, et l'ordre du tick documenté ne bouge pas. Naissances, morts et départs par foyer, puis le bourg compté par les foyers non paysans, sont les sous-lots suivants de #255.

Niveau de fidélité : **niveau 2**. `TAILLE_FOYER = 5` est l'ordre de grandeur d'un ménage médiéval ; la règle de répartition d'une écriture est plausible, jamais sourcée. Restent de niveau 3, non simulés : l'âge, le sexe, la parenté, le logement d'un foyer, et tout métier autre que mineur et paysan.

Pièges payés ailleurs, à éviter :

- **`Foyers` vit dans `sim/foyers.py`.** `sim/model.py` l'importe comme module (`import sim.foyers as _foyers`), jamais par nom de classe. Sinon `test_write_coverage.py` découvre `Foyers` dans `sim.model` et lui demande un écrivain.
- **Le site d'écriture du nouveau champ.** Il est `Cell(..., habitants_par_metier=...)` dans `World.charger`, et son site de lecture est dans `sim/model.py`. `test_write_coverage.py` ne compte ni `self.x =`, ni un écrivain hors de `engine.py`, `world.py` et `model.py`.
- **Les noms dans `constants.py`.** `TAILLE_FOYER`, `METIER_MINEURS = "mineurs"` et `METIER_PAYSANS = "paysans"` y sont des constantes, lues par `_constantes.X`. Un littéral `5` dans une fonction fait rougir `test_no_hardcoded.py`.
- **Le mot « seigneurie ».** `world.py` ne le prend pas, même en commentaire : `test_pure` de `test_seigneuries.py` le refuse.

`MODELE.md` change de trois façons :

- une section neuve **« ## Les foyers par métier »**, placée juste après « Population initiale par cellule ». Elle porte :
  - l'amorçage A ;
  - la taille et le rangement ;
  - la règle d'une écriture ;
  - la sentinelle `-1` ;
  - les refus ;
  - le niveau 2 ;
  - « le tick ne lit pas les métiers » ;
- dans « Ce que le moteur ne fait toujours pas » (sous « Ce qu'est une ville »), « ni familles » devient : des foyers par métier existent, mais le bourg ne les compte pas encore ;
- dans « Ce que le moteur ne fait pas encore », la puce « répartir le travail » dit que les habitants ont désormais un métier, mineur ou paysan, que le tick ne lit pas encore.

## Périmètre
jeu/sim/foyers.py
jeu/sim/model.py
jeu/sim/world.py
jeu/sim/constants.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_foyers.py
docs/briefs/297-les-habitants-d-une-cellule-se-rangent-en-foyers.md

## Conditions de succès
Toutes les commandes se lancent depuis `jeu/`. Chaque test imprime ses compteurs, et un échantillon vide échoue. Aucun `cell_id` n'est écrit en dur : les cellules se choisissent par ce qu'on lit du monde, par exemple la plus petite `cell_id` qui a des mineurs.

- **SC1 — Cent personnes rangées puis rendues font cent personnes.** `python3 -m pytest sim/tests/test_foyers.py -q -s -k aller_retour`
  - `ranger_en_foyers(100) == Foyers(5, 20, 0)` et `ranger_en_foyers(103) == Foyers(5, 20, 3)`, avec `nombre` égal à 20 et 21.
  - Pour 0, 1, 4, 5, 100 et 103, puis pour chaque compte de métier de `World.charger(0)`, `rendre_les_personnes(ranger_en_foyers(n)) == n`. Le compteur `allers_retours` est imprimé et dépasse le nombre de cellules.
  - La taille se relit : avec `TAILLE_FOYER` patchée à 10, `ranger_en_foyers(103) == Foyers(10, 10, 3)`.
  - Contre-épreuve : le même contrôle, écrit comme une fonction du test qui reçoit la désagrégation, lève `AssertionError` quand on lui donne `lambda f: f.complets * f.taille`. Elle ignore le dernier foyer, donc 103 ne revient pas.
- **SC2 — Au départ, les mineurs sont la part minière tronquée, les autres sont paysans.** `python3 -m pytest sim/tests/test_foyers.py -q -s -k amorcage`
  - Pour chaque cellule de `World.charger(0)` : `sum(habitants_par_metier.values()) == population`.
  - Les mineurs égalent `int(population × part_miniere_de(...))` et `habitants_du_bourg` de `bourg_depuis_monde`.
  - Les clés sont dans `{METIER_MINEURS, METIER_PAYSANS}`, et aucune valeur n'est nulle.
  - Compteurs imprimés : `cellules_avec_mineurs` > 0, `cellules_sans_mineurs` > 0 (où la clé `mineurs` est absente), et `cellules_contrôlées == len(monde.cells)`.
  - Contre-épreuve : avec `PART_MINIERE_PAR_GISEMENT` patchée au double avant `World.charger(0)`, la part des mineurs dans la population totale augmente strictement (la population elle-même bouge, puisque la part minière retire des bras aux champs). L'amorçage passe par la fonction, il ne fige pas la part.
- **SC3 — Une écriture de la population se répartit sans perdre ni créer personne.** `python3 -m pytest sim/tests/test_foyers.py -q -s -k ecriture`
  - Sur une copie de `World.charger(0)`, on rejoue les écritures des tests existants : `= 0`, `= 1`, `= 100`, `+= 1`, `+= 1000` puis `-= 1000`, `= int(x) + 1`. Elles visent une cellule à mineurs et une sans mineurs. Après chacune, la somme des métiers égale `population`, aucun métier n'est à zéro, et `population` vaut exactement la valeur écrite.
  - Après `= 0`, les métiers sont `{}`. Après `= 0` puis `= 7`, ils sont `{METIER_PAYSANS: 7}`.
  - `repartir({"mineurs": 100, "paysans": 900}, 999)` rend `{"mineurs": 99, "paysans": 900}`.
  - On joue 30 ticks de `World.charger(0)` avec `random.Random(0)` : à chaque tick, l'invariant tient sur toutes les cellules (compteur `vérifications`).
  - Les refus : une écriture de `-1`, `2.5` ou `True` sur une cellule amorcée lève `FoyersInvalides`, et la population reste l'ancienne.
  - Contre-épreuve : une `repartir` fautive, qui ne donne pas le reste, passée au même contrôle d'invariant, le fait échouer sur 999.
- **SC4 — Une cellule construite sans métiers les déclare non calculés ; une incohérence est refusée.** `python3 -m pytest sim/tests/test_foyers.py -q -s -k non_calcule`
  - `Cell(cell_id=1, area_km2=10.0, population=50)` : `lire_habitants_par_metier` rend `-1`, et `cellule_vers_dict(...)["foyers"] == -1`.
  - `population = 60` s'applique, et les métiers restent `-1`.
  - Lèvent `FoyersInvalides` : un `Cell` avec `population=50` et `{"paysans": 49}`, un compte à 0, un compte booléen, un nom vide, `ranger_en_foyers(-1)`, `ranger_en_foyers(True)`, `TAILLE_FOYER` patchée à 0 puis à 2.5, et `Foyers(5, 1, 5)`. Le compteur `refus_observés` égale la longueur de la liste.
  - Contre-épreuve : `Cell(..., population=50, habitants_par_metier={"paysans": 50})` passe ; le refus ne vise que l'incohérent.
- **SC5 — `World.to_dict()` porte les foyers ; `/lieu` ne change pas.** `python3 -m pytest sim/tests/test_foyers.py -q -s -k serialisation`
  - Pour chaque cellule de `World.charger(0).to_dict()["cells"]`, `"foyers"` a les mêmes clés que ses métiers. Chaque entrée vaut `{"personnes": n, "complets": c, "dernier": d}` avec `c × TAILLE_FOYER + d == n`.
  - Deux `World.charger(0)` donnent le même JSON trié à l'octet.
  - `service._cellule_legere(cellule)` n'a pas de clé `"foyers"`.
  - Contre-épreuve : sur une copie, faire passer une personne de paysan à mineur sans toucher `population` (écriture directe dans le dictionnaire). `to_dict()["cells"][X]["population"]` reste égal, mais `to_dict()` et son SHA-256 diffèrent : la sérialisation voit les foyers.
- **SC6 — Aucune seconde lecture de la part minière, aucun champ de ville.** `python3 -m pytest sim/tests -q`
  - Toute la suite est verte, en particulier :
    - `test_une_seule_definition_part_miniere` et `test_moteur_consulte_part_miniere_par_fonction` (`test_monde.py`) ;
    - `test_bourg_une_seule_definition_part_non_agricole` et `test_bourg_aucune_seconde_cle_spatiale` (`test_province.py`) ;
    - `test_write_coverage.py`, `test_no_hardcoded.py` et `test_ordre_du_tick_documente_est_celui_du_code` ;
    - les fichiers figés de `/lieu`.
  - Contre-épreuve : un littéral `5` dans `sim/foyers.py` fait rougir `test_no_hardcoded.py`. Une lecture directe de `constantes.PART_MINIERE_MAXIMALE` dans `world.py` fait rougir `test_une_seule_definition_part_miniere`.
- **SC7 — Le modèle le dit.** `grep -n "^## Les foyers par métier" sim/MODELE.md` rend une ligne, et la section contient `TAILLE_FOYER`, `part_miniere_de`, « paysans » et `-1`. `jeu/sim/README.md` ajoute `sim/foyers.py` à sa table des modules.
  - Contre-épreuve : sur la base, la commande `grep` ne rend rien.
- **SC8 — Aucun test existant ne s'assouplit.** `git diff origin/master -- sim/tests | grep -E '^-[^-]'` ne rend rien.
  - Contre-épreuve : une ligne existante retirée ou modifiée apparaît dans la sortie.

## Hors périmètre
- Les naissances, les morts et les départs par foyer : le moteur (`sim/engine.py`) ne change pas, et ses écritures passent seulement par la répartition. C'est le sous-lot 2 de #255.
- Le bourg compté par les foyers non paysans. `sim/aggregation.py`, `RepartitionBourg` et la distribution à l'intérieur de la cellule ne changent pas : c'est le sous-lot 3.
- Les foyers dans `/lieu`, `/monde`, la photographie ou Unity, et donc les fichiers figés `lieu-graine0-tick{3,4}.json` (sous-lot 4, sur le PC).
- Le chantier qui prend des bras aux champs, l'atelier, et tout métier autre que mineur et paysan.
- Le logement d'un foyer, sa parenté, les âges ; les foyers rattachés à un lieu de rang ≥ 1.
- `sim/engine.py`, `sim/aggregation.py`, `sim/service.py`, `sim/snapshot_export.py`, `jeu/vues/`, `jeu/ville/`, `3d/`, et tout test existant.
