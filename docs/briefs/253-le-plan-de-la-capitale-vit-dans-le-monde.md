# Lot #253 — Le plan de la capitale vit dans le monde
Jalon : J4 · Machine : vps · Taille prévue : 260 lignes

## But
Le monde tient, pour le bourg (rang 0) de chaque cellule, donc pour celle que le joueur fera sa capitale, un plan de rues, de parcelles et de bâtiments en mètres locaux. Ce plan est vide au départ, sérialisé avec l'état du monde et servi par `GET /plan?cell=`. C'est la source dont Unity redessinera la ville (preuve J4 : « une ville que seul Unity connaît » doit échouer).

## Règle du monde
Elle découle de « Les lieux d'une cellule, vue dérivée » (le rang 0 est le bourg, identité (`cell_id`, `rang`)) et de « Ce qu'est une ville, à l'échelle d'une cellule » (décision B : le bourg est une concentration dans la cellule, sans `bourg_id`). Le lot écrit une nouvelle section **« Le plan du bourg »** dans `jeu/sim/MODELE.md`, placée juste après « La distribution à l'intérieur de la cellule ».

Ce que le monde sait après ce lot :

- **Un plan par bourg, rangé sous `cell_id`.** `World.plans` est un dictionnaire `cell_id → Plan`. Le plan est celui du lieu (`cell_id`, 0), c'est-à-dire le bourg. Il n'y a ni `bourg_id`, ni `ville_id`, ni numéro de plan : `cell_id` reste la seule clé spatiale. Le bourg reste ce qu'il était, une **vue dérivée** de la population. Ce qui est stocké, c'est son plan, pas ses habitants.
- **Tout bourg a un plan, et il part vide.** `World.charger` donne à chaque cellule de la carte un plan vide, sans tirage : la graine n'y touche pas. Un `World` construit directement reçoit lui aussi un plan vide par cellule de `cells`. Le monde ne sait pas encore quelle cellule est la capitale du joueur : le choix de la terre est au jalon 2, les capitales voisines au jalon 5. Un plan par bourg sert les deux sans rien deviner, et il ne s'appuie sur rien que J2 ou J3 doivent encore livrer.
- **Ce que contient un plan.** Trois listes, chacune triée par `identifiant` (entier ≥ 0, unique dans sa liste) :
  - une **rue** : `identifiant`, `points` (au moins `POINTS_MIN_RUE = 2` points `(x, y)`), `largeur_m` (> 0, finie) ;
  - une **parcelle** : `identifiant`, `contour` (au moins `POINTS_MIN_CONTOUR = 3` points) ;
  - un **bâtiment** : `identifiant`, `parcelle` (l'identifiant d'une parcelle du même plan), `nature` (texte non vide), `emprise` (au moins `POINTS_MIN_CONTOUR` points).
- **Les mètres locaux.** Le repère est celui du bourg : x vers l'est, y vers le nord, en mètres, origine au centre du bourg. Une coordonnée est un nombre fini, jamais un booléen ni un texte. Le bourg n'a pas encore de position ni de forme dans la cellule (niveau 3, non simulé) : aucune borne de coordonnée n'est donc vérifiable, et aucune n'est inventée.
- **Rien ne se devine.** Un plan mal formé lève `PlanInvalide` en nommant ce qui manque : point non fini, rue à un point, largeur nulle, contour à deux points, identifiant en double, bâtiment sur une parcelle absente, nature vide.
- **Le tick ne lit pas le plan, et ne l'écrit pas.** Aucune règle existante ne change : production, consommation, distribution intérieure, commerce, faim, mort, naissance et migration restent identiques au bit près. Le plan entre seulement dans `World.to_dict()` (clé `"plans"`, cellules en chaîne triée, comme `"cells"`). L'empreinte d'un monde change donc avec son plan.
- **Le service sert le plan publié.** `GET /plan?cell=X` rend `{"cell_id", "rang": 0, "tick", "date", "rues", "parcelles", "batiments"}`. Ces octets sont construits avec la photographie du tick dans `EtatPublie`, comme ceux de `/lieu` ; une lecture n'attend jamais un tick. `/monde` et `/lieu` ne changent pas d'un octet.

Niveau de fidélité : **niveau 2** pour la forme du plan (plausible, jamais sourcée). Le plan vide de départ n'affirme rien. Restent de niveau 3, non simulés : la position et la forme du bourg dans la cellule, l'effet d'une rue ou d'un bâtiment sur le monde, et tout geste qui remplit le plan.

Dans « Ce que le moteur ne fait pas encore » et dans « Ce que le moteur ne fait toujours pas », les phrases qui disent « pas de bâtiments » deviennent : le plan peut porter des bâtiments, mais ils ne font rien. La liste des étapes du tick (« En une page ») ne change pas, puisque `test_ordre_du_tick_documente_est_celui_du_code` la compare au code.

Deux pièges payés ailleurs, à éviter :

- Les dataclasses du plan vivent dans `sim/plan.py` et **jamais dans `sim/model.py`**, qui ne doit pas non plus les importer. `test_all_dataclass_fields_have_write_and_read_sites` découvre toute dataclass visible dans `sim.model`, et le plan vide n'a pas d'écrivain dans le moteur.
- Les minimums de points sont des constantes nommées de `sim/constants.py`, lues par `_constantes.X`. Un littéral `2` ou `3` dans une fonction fait rougir `test_no_hardcoded.py`.

## Périmètre
jeu/sim/plan.py
jeu/sim/world.py
jeu/sim/service.py
jeu/sim/constants.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_lieux.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_determinisme.py
docs/briefs/253-le-plan-de-la-capitale-vit-dans-le-monde.md

## Conditions de succès
Toutes les commandes se lancent depuis `jeu/`.

- **SC1 — Un plan mal formé est refusé, un plan bien formé se sérialise trié.** `python3 -m pytest sim/tests/test_lieux.py -q -k plan`
  - Un plan d'une rue, une parcelle et un bâtiment, donnés dans le désordre, se construit et se sérialise trié par identifiant. Deux constructions donnent le même JSON à l'octet.
  - Chaque refus de « Rien ne se devine » a son cas, et chacun attend `PlanInvalide` : NaN, infini, booléen, texte, rue à un point, largeur 0 ou négative, contour à deux points, identifiant en double, parcelle absente, nature vide.
  - Contre-épreuve : un cas paramétré vérifie que le plan bien formé, modifié d'un seul défaut à la fois, lève l'erreur. Une vérification retirée de `sim/plan.py` fait rougir son cas.
- **SC2 — Le monde amorcé tient un plan vide par bourg, et sa sérialisation le porte.** `python3 -m pytest sim/tests/test_monde.py -q -k plan`
  - Pour `World.charger(0)` : `set(monde.plans) == set(monde.cells)`, l'ensemble n'est pas vide (un échantillon vide échoue), et chaque plan a trois listes vides.
  - `to_dict()["plans"]` a une entrée par cellule, et ces entrées sont égales au plan sérialisé.
  - Un `World(cells=…, adjacency=[])` construit directement a lui aussi un plan vide par cellule.
  - Contre-épreuve : on pose un plan non vide sur une cellule d'une copie. `to_dict()["cells"]` reste égal, mais `to_dict()` et son empreinte SHA-256 diffèrent : la sérialisation voit le plan.
- **SC3 — Même graine, même plan ; le tick ne le lit pas.** `python3 -m pytest sim/tests/test_determinisme.py -q -k plan`
  - Deux `World.charger(0)` ont des `to_dict()["plans"]` identiques à l'octet (JSON trié).
  - On prend deux mondes de même graine ; l'un reçoit un plan non vide sur sa plus petite `cell_id`. Ils jouent 30 ticks avec le même `random.Random(0)` : `to_dict()["cells"]` et `ticks_ecoules` restent identiques, et le plan non vide sort du tick inchangé à l'octet.
  - Un contrôle par arbre syntaxique vérifie que `sim/engine.py` ne lit aucun attribut `plans`.
  - Contre-épreuve : le même contrôle, appliqué à une source qui contient `world.plans`, la trouve. Et une copie dont un stock de cellule bouge d'un kilo fait échouer la comparaison des cellules : la mesure sait rougir.
- **SC4 — `GET /plan?cell=` sert le plan du monde, et refuse de deviner.** `python3 -m pytest sim/tests/test_monde.py -q -k plan`
  - Avec `lancer_service(0)` : pour la plus petite `cell_id` de `/monde`, `/plan?cell=X` rend 200, avec `cell_id == X`, `rang == 0`, `tick == 0`, trois listes vides et la date de `/horloge`.
  - Après `POST /tick?n=2`, il rend `tick == 2` et le plan toujours vide.
  - Deux services de graine 0, au même tick, rendent les mêmes octets.
  - Refus, sans faire avancer le monde (`/monde` reste à `tick == 0`) : `/plan` sans `cell` donne 400, `/plan?cell=abc` donne 400, et une `cell_id` absente de la carte donne 404 en la nommant.
  - Contre-épreuve « une ville que seul Unity connaît » : un `ServeurMonde` est lancé dans le processus de test, à vitesse 0 et port 0. On pose un plan non vide dans `serveur.world.plans[X]`, puis on appelle `jouer_un_tick()`. Les octets publiés pour X contiennent alors cette rue : le service lit le monde, il ne rend pas un document vide figé.
- **SC5 — Rien d'existant ne bouge, et `MODELE.md` le dit.** `python3 -m pytest sim/tests -q`
  - Toute la suite reste verte, en particulier `test_write_coverage.py`, `test_no_hardcoded.py`, `test_service_monde_est_leger_et_intention_ne_mute_rien` et `test_ordre_du_tick_documente_est_celui_du_code`.
  - `grep -n "^## Le plan du bourg" sim/MODELE.md` trouve la section.
  - `jeu/sim/README.md` cite `GET /plan?cell=...` à côté de `/lieu` et ajoute `sim/plan.py` à la table des modules.
  - Contre-épreuve : déplacer les dataclasses du plan dans `sim/model.py` fait rougir `test_write_coverage.py`, et un littéral `2` dans `sim/plan.py` fait rougir `test_no_hardcoded.py`.
- **SC6 — Aucun test existant ne s'assouplit.** `git diff origin/master -- jeu/sim/tests | grep -E '^-[^-]'` ne rend rien.
  - Les fichiers de test ne reçoivent que des ajouts.
  - Contre-épreuve : une ligne existante retirée ou modifiée apparaît dans la sortie.

## Hors périmètre
- Remplir le plan : tracer une rue, découper une parcelle, poser un atelier comme intention déposée dans `sim/`. `POST /intention` ne change pas.
- Ce que le plan fait au monde : bras pris aux champs, flux concentré par une route, coût en travail, foyers par métier. Le tick ne lit pas le plan.
- Désigner la capitale du joueur (jalon 2, choix de la terre) et les capitales de l'IA (jalon 5).
- La position et la forme du bourg dans la cellule, les bornes des coordonnées, et le contrôle qu'une emprise tient dans sa parcelle ou qu'une rue ne traverse pas un bâtiment.
- Relire un monde depuis sa sérialisation (`World` n'a pas de chargeur depuis `to_dict`) et la sauvegarde d'une partie.
- Le plan dans `/monde`, dans `/lieu` ou dans la photographie `--snapshot-json`.
- Unity : lire `/plan` et redessiner la ville, puis la relancer pour retrouver la même ville. C'est le lot de vue qui suit, sur le PC.
- `jeu/ville/`, `jeu/vues/`, `3d/`, et tout test existant.
