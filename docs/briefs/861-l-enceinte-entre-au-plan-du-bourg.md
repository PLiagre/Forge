# Lot #861 — L'enceinte entre au plan du bourg
Jalon : J4 · Machine : vps · Taille prévue : 275 lignes

## But
Le plan du bourg saura porter l'unique enceinte et le travail nécessaire à son chantier sans changer aucun monde qui n'en possède pas.

## Le joueur
Le joueur se rapproche du geste de J4 « trace son enceinte » : le monde pourra conserver le contour choisi et son coût en journées, au lieu de laisser cette donnée à la seule vue 3D. Ce lot de fond ne livre pas encore le tracé ; les sous-lots suivants de #416 déposeront et feront avancer ce chantier, puis #417 rendra l'enceinte visible dans la capitale.

## Règle du monde
Niveau 2, plausible, jamais sourcé. Le lot découle de la section « Le plan du bourg » de `jeu/sim/MODELE.md`.

Un `Plan` porte `enceinte: Enceinte | None`, jamais une liste ni un second identifiant spatial. Une enceinte porte un `contour` d'au moins `POINTS_MIN_CONTOUR = 3` points locaux finis et les quatre champs communs d'un chantier : `en_chantier`, `foyers`, `travail_requis`, `travail_fourni`. Ils suivent les invariants existants : entiers non négatifs sans booléens, fourni inférieur ou égal au requis, état de chantier exactement égal au travail restant et au moins un foyer quand il reste du travail. Une seule enceinte peut donc exister par plan.

Son travail requis vaut `max(1, ceil(périmètre bouclé × TRAVAIL_ENCEINTE_JOURNEES_PAR_M))`. Le périmètre comprend le segment du dernier point au premier. `TRAVAIL_ENCEINTE_JOURNEES_PAR_M = 30` est une constante de niveau 2, relue par le module au moment du calcul et non copiée à l'import.

`Plan.to_dict()` omet entièrement la clé `enceinte` quand elle vaut `None`, afin que plans vides, sauvegardes et empreintes anciennes restent identiques à l'octet. Quand elle existe, la clé publie son contour sous forme de listes et ses champs de chantier. Les trois reconstructions de `Plan` dans `intentions.py` et les deux dans `chantiers.py` conservent l'enceinte existante sans la recalculer ni la remplacer. La forme et le coût sont de niveau 2 ; portes, matériaux, effet défensif et siège restent de niveau 3.

## Périmètre
docs/briefs/861-l-enceinte-entre-au-plan-du-bourg.md
jeu/sim/constants.py
jeu/sim/plan.py
jeu/sim/intentions.py
jeu/sim/chantiers.py
jeu/sim/MODELE.md
jeu/sim/tests/test_lieux.py
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_chantiers.py
jeu/sim/tests/test_monde.py

## Conditions de succès
SC1 — `python3 -m pytest jeu/sim/tests/test_lieux.py -q -k enceinte` crée un plan sans enceinte puis avec une enceinte non vide, vérifie l'absence exacte de la clé dans le premier cas, sa copie canonique dans le second et tous les invariants de contour et de chantier. Contre-épreuves : deux points, une coordonnée non finie, un booléen à la place d'un compte, du travail fourni supérieur au requis, un état contradictoire ou un chantier sans foyer doivent chacun faire échouer le cas correspondant.

SC2 — `python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k enceinte` vérifie sur un triangle non dégénéré que le requis comprend bien les trois côtés et vaut `max(1, ceil(périmètre × 30))`. Modifier en mémoire `TRAVAIL_ENCEINTE_JOURNEES_PAR_M` doit changer le résultat du prochain appel. Les deux chemins de `chantiers.py` qui reconstruisent un plan sont exercés avec une enceinte témoin et la conservent exactement. Contre-épreuves : oublier le côté de fermeture, importer une copie de la constante ou perdre l'enceinte dans l'une des deux reconstructions fait rougir.

SC3 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k enceinte` applique successivement une route, une parcelle et un bâtiment à un plan doté d'une enceinte ; après chacune des trois reconstructions, l'enceinte et ses compteurs sont inchangés. Contre-épreuve : retirer la transmission de `enceinte` de chacun des trois appels à `Plan(...)` est détecté séparément, sans réduire les assertions existantes sur le geste appliqué.

SC4 — `python3 -m pytest jeu/sim/tests/test_monde.py -q -k 'plan_vide_par_cellule_et_empreinte_sensible or plan_service_publie'` garde exactement `{"rues": [], "parcelles": [], "batiments": []}` pour chaque plan vide et publie l'enceinte seulement lorsqu'elle existe. Contre-épreuve : sérialiser `enceinte: null`, ajouter une clé aux plans vides ou omettre une enceinte présente change l'empreinte ou la réponse et fait échouer la comparaison.

SC5 — `python3 -m pytest jeu/sim/tests/test_lieux.py jeu/sim/tests/test_intentions.py jeu/sim/tests/test_chantiers.py jeu/sim/tests/test_monde.py -q`, puis `python3 -m pytest jeu -q`, passent sans suppression, réécriture ni assouplissement d'un test existant. `git diff --check`, `git diff --name-only`, `git ls-files --others --exclude-standard` et `git diff --numstat` ne montrent que le périmètre et un total ajouté plus retiré strictement inférieur à 300 lignes, brief compris. Contre-épreuve : un ancien constructeur de plan cassé, une empreinte sans enceinte modifiée, un chemin supplémentaire ou un total d'au moins 300 lignes refuse la livraison.

## Hors périmètre
L'intention de tracer l'enceinte, sa garde territoriale, l'affectation des bras, le paiement en grain, l'avancement et l'achèvement de son chantier ; les portes, le croisement avec les rues, les matériaux, la hauteur, l'épaisseur, l'effet défensif et le siège ; le service au-delà de la sérialisation déjà issue du plan ; Unity, Blender, panneau, dessin et capture. Aucun test existant n'est assoupli et tout autre chemin est interdit.
