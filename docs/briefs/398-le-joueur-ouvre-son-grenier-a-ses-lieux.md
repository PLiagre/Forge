# Lot #398 — Le joueur ouvre son grenier à ses lieux
Jalon : J3 · Machine : vps · Taille prévue : 280 lignes

## But
Une maison peut rendre du grain : l'intention `ouvrir_grenier` sort une quantité de son grenier, l'envoie en convois vers ses lieux, au prorata de leur dette (ou de leurs habitants si aucun n'a de dette), et le grain arrivé se mange comme le reste du panier.

## Le joueur
Quand ses gens ont faim, le joueur peut rendre du grain : il choisit combien, son grenier l'envoie à ses lieux affamés, et ceux qui seraient partis restent. C'est l'autre moitié de la décision du jalon 3 : prendre en bonne année, rendre en mauvaise. Après ce lot, le geste existe dans le monde, par `POST /intention` (seulement pour sa propre maison) et par `python3 -m sim --gestes`. Il voit sa dette baisser dans `/lieu` et dans la photographie. Le bouton sur la carte arrive avec #405, et le départ retenu avec #399.

## Règle du monde
Elle découle de `jeu/sim/MODELE.md`, sections « Le grenier d'une maison » (l'ouvrir), « Le prélèvement » (mêmes routes, même perte) et « Les intentions du joueur ». Niveau 2, plausible, jamais sourcé : la règle de répartition. Aucune constante nouvelle.

**Le dépôt.** `{"type": "ouvrir_grenier", "maison": <id du registre>, "kg": <quantité>}`, ces trois champs exactement. `foyers` est refusé comme tout champ inconnu : la tolérance actuelle de `recevoir_intention` pour `foyers` ne doit pas s'étendre à ce type. Les refus lèvent `IntentionRefusee`, dans cet ordre, sans rien changer à l'attente, aux greniers ni à `to_dict()` :
- `maison` n'est pas une chaîne, ou n'est pas l'`id` d'une fiche de `monde.maisons` : « maison inconnue ou mal formée : <repr> », même message que `fixer_part` ;
- la maison ne tient aucun lieu, c'est-à-dire qu'elle est absente de `monde.routes_des_lieux.noms` (par exemple une grande maison hors carte) : « maison sans lieu : <id> » ;
- `kg` est booléen, n'est pas un nombre, n'est pas fini, ou vaut ≤ 0 : « kg invalide : <repr> » ;
- le grenier n'en contient pas autant : « grenier insuffisant : <kg> kg demandés, <reste> kg disponibles ». Le reste se calcule ainsi : on part de `greniers[maison].get(nourriture, 0.0)` et on retire, **une par une et dans l'ordre**, les ouvertures de cette maison déjà en attente. C'est la même arithmétique qu'à l'application, donc le grenier ne devient jamais négatif à un ulp près ;
- les lieux de la maison n'ont ni dette ni habitants : « lieux sans dette ni habitants : <id> ».

Le geste accepté est un `OuvrirGrenier(maison, kg)` gelé, ajouté à la fin de la file. Deux ouvertures de la même maison s'additionnent : elles ne se remplacent pas comme deux `fixer_part`. Entre le dépôt et l'application, rien ne touche au grenier : l'étape Intentions précède la perte des greniers.

**L'application** (étape Intentions du tick `t`, `OuvrirGrenier.appliquer`). Elle ne lit ni `monde.maisons`, ni le registre, ni `lieu.maitre`. Les lieux de la maison sont les entrées de `routes_des_lieux` dont `maitre_idx` désigne cette maison, dans l'ordre de la table. Les étapes :
1. Retirer `kg` de la nourriture du grenier. La clé reste, à `0.0` si tout est parti.
2. Choisir les poids : `dette_alimentaire_kg` de chaque lieu, ou leur `population` si toutes les dettes sont nulles.
3. Répartir avec `sim.lieux.partager(kg, poids)`, dont la somme est exacte.
4. Mettre chaque part non nulle en route vers son lieu `(cell_id, rang)`, avec les `jours` de la table.

Les convois de secours vivent dans `World.secours` (arrivée → charges par lieu `(cell_id, rang)`), `{}` au chargement et pour un `World(...)` d'épreuve.

**La route.** C'est la même perte que le prélèvement : à chaque étape Prélèvement, avant les arrivées, chaque charge de secours garde `1 − PERTE_CONVOI_PAR_JOUR`, et le mangé s'ajoute à `mange_convois_kg`. Le convoi part au début du tick `t`, avant la Production. Sa première perte tombe donc à l'étape Prélèvement du même tick, et il arrive à l'étape Prélèvement du tick `t + jours − 1`, après exactement `jours` pertes : le lieu reçoit `part × (1 − PERTE_CONVOI_PAR_JOUR)^jours`, la formule du prélèvement. Un lieu à 1 jour mange son secours dès le tick de l'ouverture.

**L'arrivée** ajoute la charge à la nourriture du lieu et à celle de sa cellule, par `lire/ecrire_stock_marchandise`, en miroir exact du retrait du prélèvement. Ensuite, commerce et consommation la traitent comme le reste du panier. La livraison suit le lieu, jamais son maître : un lieu passé à un autre maître pendant la route reçoit quand même son convoi.

Quand `World.secours` est vide, le prélèvement ne parcourt rien de plus, et le tick reste sous `BUDGET_TICK_MS`. `to_dict()` publie `secours` seulement s'il n'est pas vide : une liste `[cell_id, rang, arrivee, kg]` triée, kg courant après pertes, sans arrondi. Sans geste, les octets et les empreintes figées restent ceux d'avant.

**Le service.** Sous `verrou_tick`, comme pour `fixer_part`, une ouverture du joueur exige un départ appliqué (« départ non appliqué : choisir une terre avant d'ouvrir le grenier ») et sa propre maison (« maison interdite : seule la maison du joueur peut ouvrir son grenier »). Le dépôt commun et `--gestes` acceptent toute maison connue : c'est le chemin de l'IA (#425).

**Mesures du prototype** (graine 0, Bar = `seigneurie-1`, lieux de la cellule 10430 à 1, 2, 1 et 2 jours). Le rendement est mis à zéro (`RNG_YIELD_LOW = RNG_YIELD_HIGH = 0`), les parts à la coutume, et un lieu de Bar entre en dette après 5 ticks (dettes 15, 25, 25, 25 kg). On pose alors 200 000 kg au grenier de Bar dans les deux mondes, et on les ouvre dans un seul.
- Répartition : 33 333, 55 556, 55 556 et 55 555 kg.
- Sur 6 ticks, la somme des dettes de Bar va de 20 354 à 156 532 kg avec le geste, et de 47 662 à 269 134 kg sans.
- Sortie 200 000 kg = arrivées 196 900,0011 + mangé 3 099,9989.
- Environ 5 s en tout, chargement compris.

## Périmètre
jeu/sim/intentions.py
jeu/sim/prelevement.py
jeu/sim/world.py
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/README.md
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_prelevement.py

## Conditions de succès
Les nouveaux tests portent `ouverture` dans leur nom. Jouer les fichiers un par un, jamais toute la suite d'un coup (elle dépasse l'heure).

- **SC1 — dépôt.** `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k ouverture`. Le test est paramétré sur chaque refus de « Le dépôt » : maison inconnue, mal formée (`True`, `None`, `1`) ou sans lieu ; kg booléen, `None`, chaîne, `nan`, `inf`, `0` ou négatif ; kg au-dessus du grenier ; une seconde ouverture qui, ajoutée à la première, dépasse le grenier ; `foyers` ; champ inconnu ; chacun des trois champs absent. Chaque refus laisse la file, les greniers et `to_dict()` identiques, et un dépôt valide est accepté, gelé et ajouté à la fin. Contre-épreuve dans le test : un dépôt qui ne compterait pas l'ouverture déjà en attente doit faire échouer le cas « seconde ouverture ».
- **SC2 — application sans registre.** Même commande. Après un dépôt, le tick s'exécute sous `_tick_sans_lecture_registre`, avec `EtatDeLieu.maitre` remplacé par une propriété qui lève. Le grenier perd exactement `kg`, et les parts sont proportionnelles aux dettes, ou aux populations quand les dettes sont nulles (cas au chargement). Contre-épreuve : un `appliquer` remplacé en mémoire par un `appliquer` qui ne retire rien du grenier doit faire échouer l'assertion.
- **SC3 — service.** Même commande. On démarre `ServeurMonde` dans un fil et on pose des kilos au grenier de la maison du joueur. Une ouverture est refusée en 400 avant le départ, puis pour une autre maison, sans changer le monde servi. Elle est acceptée (200) pour la maison du joueur et appliquée au tick suivant, et `recevoir_intention` direct accepte une autre maison. Contre-épreuve : `maison_du_joueur` remplacée en mémoire par l'autre maison doit faire échouer le refus attendu.
- **SC4 — conservation.** `cd jeu && python3 -m pytest sim/tests/test_prelevement.py -q -k ouverture`. Monde de graine 0, parts toutes à 0, `PERTE_GRENIER_PAR_AN` à 0, grenier de Bar à 200 000 kg, ouverture de 150 000 kg, puis `max(jours) + 1` ticks en enveloppant `prelevement.prelever`. On vérifie :
  - la sortie du grenier égale la somme des hausses de nourriture des lieux pendant l'étape, plus le `mange_convois_kg` gagné, plus ce qui reste dans `secours` (`rel=1e-12`) ;
  - chaque lieu reçoit `part × (1 − PERTE_CONVOI_PAR_JOUR)^jours` au tick `t + jours − 1` ;
  - les hausses du lieu et de sa cellule sont égales.

  Contre-épreuve : une arrivée neutralisée en mémoire (le grenier se vide, rien n'entre dans les lieux) doit faire échouer la conservation.
- **SC5 — direction.** Même commande. On reprend la recette des mesures (graine 0, rendement nul jusqu'à la première dette d'un lieu de Bar, grenier de Bar à 200 000 kg dans les deux copies, ouverture de 200 000 kg dans une seule, 6 ticks). À chaque tick, la somme des dettes des lieux de Bar est strictement plus basse avec le geste. L'échantillon est non vide : au moins un lieu de Bar en dette avant l'ouverture. Contre-épreuve : avec l'arrivée neutralisée, l'inégalité stricte doit échouer.
- **SC6 — le grain suit le lieu, et les octets.** Même commande. Pendant la route, on change le maître d'un lieu destinataire avec `ecrire_maitre`, et il reçoit quand même sa part. `secours` apparaît dans `to_dict()` tant qu'une charge roule, puis disparaît. Deux copies avec le même geste donnent les mêmes octets, et une copie sans geste ne porte ni `secours` ni de nouveau `mange_convois_kg`. Contre-épreuve : une livraison qui relirait le maître (remplacée en mémoire pour ignorer un lieu au maître changé) doit faire échouer le cas.
- **SC7 — rien n'a bougé sans geste.** Toutes ces commandes restent vertes :
  - `cd jeu && python3 -m pytest sim/tests/test_determinisme.py -q -k "bit_pres"` (empreintes figées du prélèvement et des parts) ;
  - `python3 -m pytest sim/tests/test_prelevement.py -q` (conservation sur un an, calibration et `test_tick_sans_maitre_ni_registre` : `prelevement.py` ne lit toujours ni `maitre` ni `maisons`) ;
  - `python3 -m pytest sim/tests/test_convois.py sim/tests/test_write_coverage.py sim/tests/test_chantiers.py -q` ;
  - `python3 -m pytest sim/tests/test_monde.py -q -k tick_sous_le_budget_du_service`.

  Contre-épreuve : ce sont des tests existants, déjà rouges sur leurs propres altérations.
- **SC8 — le modèle le dit.**
  - « Le grenier d'une maison » gagne un paragraphe « L'ouvrir » (retrait à l'étape Intentions, répartition par dette sinon habitants, niveau 2).
  - « Le prélèvement » dit la perte et l'arrivée des secours (`t + jours − 1`, `jours` pertes, `World.secours`, mangé dans `mange_convois_kg`).
  - « Les intentions du joueur » ajoute `ouvrir_grenier` à la liste fermée, avec ses refus et la garde du service. La phrase « l'ouvrir à ses lieux n'est pas simulé » disparaît.
  - `sim/README.md` nomme `ouvrir_grenier` (ligne de `sim/intentions.py`) et les secours (ligne de `sim/prelevement.py`).

  Le test de SC1 lit ces sections et le README, et vérifie qu'ils contiennent `ouvrir_grenier`, `OuvrirGrenier`, `World.secours` et `t + jours − 1`. Contre-épreuve : un texte lu sans ces mots doit le faire échouer.

## Hors périmètre
- Le bouton de la carte et le panneau du grenier dans Unity : #405.
- Les foyers qui restent ou partent selon le maître : #399. Ce lot ne touche pas à la migration.
- L'IA qui ouvre son grenier : #425. Ce lot donne seulement le chemin commun.
- Le dû au suzerain : #397.
- La publication des flux par `/lieu` et dans la photographie au-delà de `to_dict()` : #400.
- Le changement de maître d'un lieu : niveau 3, il n'existe que dans le test SC6.
- Le minerai, les objets, la capacité et le pillage des convois : niveau 3.
- Aucune constante nouvelle, aucune modification de `sim/engine.py`, de l'ordre du tick ni d'un test existant.
