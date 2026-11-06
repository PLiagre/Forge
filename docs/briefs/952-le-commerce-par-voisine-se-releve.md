# Lot #952 — Le commerce par voisine se relève
Jalon : J5 · Machine : vps · Taille prévue : 170 lignes

## But
Le monde garde, pour chaque cellule, les kilos qu'elle a envoyés à chacune de ses voisines terrestres et reçus d'elle pendant les trente derniers jours. Une fonction de `sim/flux.py` relit ce relevé. Le relevé ne décide rien et ne change aucun nombre du monde.

## Le joueur
C'est un lot de fond. Il prépare un geste du jalon J5 : le joueur laisse filer les années et voit les maisons voisines « tracer leurs routes, pour des raisons qu'elles disent ». Aujourd'hui, l'IA ne trace qu'une route vers ses champs. Le commerce passe chaque jour d'une terre à l'autre, mais le monde ne le garde nulle part. `_apply_commerce` le calcule puis l'oublie (constat de #426).

Après ce lot, le monde sait par quelle frontière passent les vivres de chaque terre. Le sous-lot « route du commerce » de #426 s'en servira : une maison tracera sa route vers la voisine avec laquelle elle échange le plus. Sa raison dira combien de kilos, avec quelle terre, en trente jours. #428 (le service et la photographie montrent les voisins et leurs raisons) et #429 (la carte de Unity) rendront cette raison visible au joueur. Il pourra lire pourquoi un voisin bâtit vers telle frontière, et s'en méfier ou s'en servir.

## Règle du monde
Aucune règle du monde ne change. Le lot ajoute une observation, comme les autres registres de « ## Les flux sur trente jours ». Il la décrit dans **« ## Le commerce entre cellules »** de `jeu/sim/MODELE.md`, dans une sous-section neuve **« ### Le relevé par voisine »**. Il corrige aussi la phrase de « ## Les flux sur trente jours » qui dit « Les cellules sans lieux, les naissances, les morts et le commerce ne sont pas comptés ». Le commerce terrestre y devient compté, renvoyé à la sous-section neuve. Le relevé n'a pas de niveau de fidélité à lui : il mesure exactement les kilos que le commerce, de niveau 2, a déjà déplacés.

**Ce qui se relève.** Dans `JourDeFlux`, un champ neuf `commerce: dict` (vide par défaut), de clé `(source, receveur)` (deux `cell_id`) et de valeur les kilos. Une fonction neuve `noter_commerce(monde, transferts)` dans `sim/flux.py` l'accumule :
- `transferts` est la liste `final_transfers` de `_apply_commerce`, telle qu'elle vient d'être appliquée. Chaque élément est `(source, receveur, kilos, clé d'arête)`. Le corps la défait par `for source, receveur, kilos, _ in transferts` : un indice `[2]` serait un littéral refusé par `test_no_hardcoded`.
- Un appel vide ne crée aucun jour, comme `noter_personnes` et `noter_affames`. Un monde sans registre (`jour_courant` rend `None`) ne note rien.
- Seuls les kilos effectivement passés sont notés, après l'écriture des stocks. Les envois écrêtés à zéro ne figurent pas dans `final_transfers` et ne sont pas notés.
- Toutes les marchandises s'additionnent sous la même clé, comme le plafond d'arête qu'elles partagent. Aujourd'hui seule la ration passe : les autres n'ont jamais de besoin (« Pourquoi le minerai ne bouge pas »).
- Débarquements et expéditions par la mer ne sont pas relevés. Ils passent par le bassin, pas par une voisine (`_appliquer_flux_maritimes` n'appelle pas `noter_commerce`). La sous-section le déclare.

`_apply_commerce` (`sim/engine.py`) appelle `_flux.noter_commerce(world, final_transfers)` une fois par marchandise, juste après la boucle qui applique `final_transfers` et avant la mise à jour de `capacite_restante`. Rien d'autre ne change dans `engine.py`.

**Ce qui se relit.** `commerce_par_voisine(monde, cell_id) -> dict`, dans `sim/flux.py` :
- une cellule inconnue de `monde.cells` lève `ValueError`, comme `flux_de_lieu` ;
- les voisines sont dérivées de `monde.adjacency` : l'autre bout de chaque arête dont les deux bouts sont dans `monde.cells` et différents. Le nœud de mer en est donc exclu. Chaque voisine n'apparaît qu'une fois, clés triées par `cell_id` ;
- chaque voisine porte `{'envoye_kg': …, 'recu_kg': …}`. `envoye_kg` est la somme des `commerce[(cell_id, voisine)]` des jours de la fenêtre, `recu_kg` celle des `commerce[(voisine, cell_id)]`. Une voisine sans échange rend deux zéros mesurés (`0.0`). Une cellule sans voisine rend `{}` ;
- la fenêtre est celle des autres lecteurs : `_jours_de_fenetre` (jours de tick ≥ `ticks_ecoules − FENETRE_FLUX_TICKS`), et l'élagage de `jour_courant` ne change pas ;
- les kilos échangés avec une voisine sont `envoye_kg + recu_kg`. La sous-section le dit, sans ajouter de clé.

Le registre reste hors de `to_dict`, ne se sauvegarde pas, et aucune règle du tick ne le lit.

**Mesure du chef** (prototype jetable, graine 0, base 35790aa4, 31 ticks, jamais recopiée dans un test) : commerce terrestre nul au tick 0, puis de 1 à 24 couples (source, receveur) par tick, de 740 à 52 771 kg par tick. La mer en porte environ 7 000 000 par tick. Sur les 31 ticks : 52 couples distincts entre 48 cellules, pour 1 364 arêtes. Le couple le plus chargé, 8992 → 10168, fait 208 757 kg. On voit aussi des échanges dans les deux sens (10167 ↔ 8924). Le coût ajouté est de quelques dizaines d'additions par tick.

## Périmètre
jeu/sim/flux.py
jeu/sim/engine.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_flux.py

## Conditions de succès
Les cas neufs vont dans `jeu/sim/tests/test_flux.py`, qui porte l'invariant « les mesures des circulations restent exactes et sans effet sur le monde ». Aucun test existant n'est modifié : `git diff master --stat -- jeu/sim/tests` ne nomme que `test_flux.py`, et `git diff -U0 master -- jeu/sim/tests | grep '^-[^-]'` ne montre aucune ligne retirée.

- **SC1 — Le relevé d'un petit monde est exact, voisine par voisine.** `cd jeu && python3 -m pytest sim/tests/test_flux.py -q -k commerce_par_voisine_petit_monde`. Un `World` à quatre cellules, construit avec `_cellule_bourg` : 1 en surplus, adjacente à 2 et à 3, toutes deux en manque ; 4 adjacente à 3 seulement ; plus une arête `{'a': 1, 'b': _NOEUD_MER}` (`_NOEUD_MER = -1`, importé de `test_commerce.py`), sans `stocks_mer`. Après `engine._apply_commerce(monde, total)` :
  - `commerce_par_voisine(monde, 1)` a pour clés `[2, 3]`, et ses `envoye_kg` égalent exactement les hausses de stock de 2 et de 3, relues par `lire_stock_marchandise` sur une copie d'avant. Pour 2 et 3, `recu_kg` vers 1 égale la même hausse. `envoye_kg` de 1 vers 2 vaut `recu_kg` de 2 depuis 1 ;
  - la somme des `envoye_kg` de toutes les cellules égale `total[0]`, qui est strictement positif ;
  - `commerce_par_voisine(monde, 4) == {3: {'envoye_kg': 0.0, 'recu_kg': 0.0}}`, et `-1` n'est une clé pour aucune cellule ;
  - `commerce_par_voisine(monde, 999)` lève `ValueError`.

  Contre-épreuves : avec `flux.noter_commerce` remplacé par une fonction muette, le contrôle échoue. Un relevé qui intervertit source et receveur échoue aussi. Il est simulé en inversant les clés de `jour.commerce`.
- **SC2 — Sans commerce, rien ne bouge, pas même le registre.** `cd jeu && python3 -m pytest sim/tests/test_flux.py -q -k commerce_absent_aucun_jour`. Un petit monde où chaque cellule se nourrit seule : `_apply_commerce` laisse `total[0] == 0`, `monde.flux.jours` reste vide, et `to_dict()` est égal à celui d'avant. `flux.noter_commerce(monde, [])` ne crée aucun jour. `noter_commerce` sur un `SimpleNamespace` sans `flux` ne lève rien et n'ajoute pas d'attribut `flux`.

  Contre-épreuve : un `noter_commerce` qui appelle `jour_courant` avant de regarder si la liste est vide, recompilé en mémoire, fait échouer l'assertion « aucun jour ».
- **SC3 — Sur le vrai monde, le relevé égale le commerce terrestre et ne change rien au monde.** `cd jeu && python3 -m pytest sim/tests/test_flux.py -q -k commerce_par_voisine_monde_reel`. Deux copies du monde du module `monde` (graine 0) jouent 31 ticks avec `random.Random(0)`. La seconde a `flux.noter_commerce` muet. `engine._appliquer_flux_maritimes` est enveloppé dans les deux pour mesurer la part de la mer de chaque tick (`total_transported[0]` avant et après). À chaque tick :
  - la somme des valeurs de `jour.commerce` du tick égale, à `rel=1e-9`, le retour de `engine.tick` moins la part de la mer ;
  - chaque clé `(a, b)` de `jour.commerce` est une arête de `monde.adjacency` entre deux cellules du monde ;
  - `to_dict()` des deux copies est égal, ainsi que l'état des deux `random.Random`, au bit près ;
  - sur les ticks où le commerce terrestre est nul, `jour.commerce == {}`, et le `JourDeFlux` de ce tick est égal à celui de la copie muette.

  Le test exige au moins un tick à commerce terrestre positif. Il affiche avec `print` le nombre de ticks sans commerce terrestre, sans le borner. À 31 ticks, la somme des `envoye_kg` de toutes les cellules égale, à `rel=1e-9`, la somme des commerces terrestres mesurés des ticks 1 à 30. Le tick 0 est sorti de la fenêtre.

  Contre-épreuves : un `noter_commerce` qui ajoute 1e-9 kg au stock du receveur (par `ecrire_stock_marchandise`) fait échouer l'égalité des `to_dict()`. Le `noter_commerce` muet fait échouer l'égalité au commerce terrestre.
- **SC4 — La fenêtre est celle des trente derniers jours.** `cd jeu && python3 -m pytest sim/tests/test_flux.py -q -k commerce_par_voisine_fenetre`. Sur le petit monde de SC1, un `JourDeFlux(t)` avec `commerce = {(1, 2): 5.0}` est posé à la main. À `ticks_ecoules = t + FENETRE_FLUX_TICKS`, `commerce_par_voisine(m, 1)[2]['envoye_kg'] == 5.0`. À `t + FENETRE_FLUX_TICKS + 1`, il vaut `0.0`. Contre-épreuve : avec `flux._jours_de_fenetre` remplacé par tous les jours du registre, la seconde assertion échoue.
- **SC5 — Le modèle dit le relevé.** `cd jeu && python3 -m pytest sim/tests/test_flux.py -q -k commerce_par_voisine_documentation`. La section `## Le commerce entre cellules` contient `### Le relevé par voisine`, et celle-ci contient `commerce_par_voisine`, `noter_commerce`, `FENETRE_FLUX_TICKS`, `to_dict`, `envoye_kg`, `recu_kg` et le mot « mer ». La section `## Les flux sur trente jours` ne contient plus « et le commerce ne sont pas comptés ». Elle nomme `commerce_par_voisine`. Contre-épreuve : le même contrôle, appliqué au texte privé de la sous-section neuve, lève `AssertionError` ou `IndexError`. `jeu/sim/README.md` cite le commerce par voisine parmi ce que `sim/flux.py` observe (`grep -n "voisine" jeu/sim/README.md`).
- **SC6 — Tout le reste passe.** `python3 -m pytest jeu -q` passe en entier, en particulier `test_commerce.py`, `test_no_hardcoded.py`, `test_write_coverage.py` et `test_determinisme.py`. `python3 -m pytest jeu/sim/tests/test_flux.py -q -m chronometre` passe aussi (`test_budget_flux_et_contre_epreuve`, budget `BUDGET_TICK_MS`).

## Hors périmètre
- La route du commerce elle-même : le choix de la voisine, le geste de l'IA et sa raison. C'est le sous-lot « route du commerce » de #426. Aucun module de règles et aucun fichier de l'IA (`sim/ia.py`, `sim/programme_ia.py`) ne lit le relevé ici.
- Servir le relevé par le service (`/lieu`, `/maison`), la photographie ou Unity : #428 et #429.
- Relever le commerce de la mer, les chemins intérieurs entre lieux d'une cellule, ou le commerce par marchandise.
- Changer le commerce, ses capacités, son ordre, `FENETRE_FLUX_TICKS`, `jour_courant` ou les autres lecteurs de `sim/flux.py`.
- Modifier un test existant.
