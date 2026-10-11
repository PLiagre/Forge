# Lot #572 — La route de chaque lieu jusqu'au grenier de son maître
Jalon : J3 · Machine : vps · Taille prévue : 260 lignes

## But
Au chargement, le monde sait pour chaque lieu qui prend sa récolte et combien de jours de route la séparent du siège de ce maître : une table calculée une fois, gardée hors de l'empreinte, que le tick ne lit pas encore.

## Le joueur
Le joueur ne voit encore rien bouger. Ce sous-lot de fond prépare le geste du jalon J3 « il voit sa part voyager jusqu'à son grenier » : sans durée de route, une part prélevée ne peut qu'apparaître d'un coup au grenier. Ici, chaque lieu du domaine du joueur sait à combien de jours il est de son siège : à Bar, le bourg est à 1 jour, le lieu de rang 1 (42 km) à 2 jours. Le sous-lot 2 de la découpe de #396 (prélèvement et convois) rend la route visible : la part part du lieu et n'arrive au grenier qu'après ces jours.

## Règle du monde
Nouvelle section **« ## Le prélèvement »** de `jeu/sim/MODELE.md`, placée juste après « ## Le grenier d'une maison » (avant « ## Les intentions du joueur »). Ce lot n'en écrit que le **premier paragraphe : la route**. Elle découle de « Les maisons du monde » (le maître de chaque lieu, le siège (`cell_id`, `rang`) de chaque maison) et de « Le commerce entre cellules » (le relief freine une arête, facteur = le plus petit des deux bouts).

**La table.** `World.charger` calcule, une seule fois et après l'attribution des maîtres et des fiches plausibles, `World.routes_des_lieux` : `(cell_id, rang)` du lieu → `Route(maitre, siege, jours)`, où `maitre` est l'identifiant de la maison qui tient le lieu, `siege` le couple `(maison.cell_id, maison.rang)` de cette maison, `jours` un entier ≥ 1. `Route` est une dataclass gelée de `jeu/sim/convois.py` (pas de `sim/model.py` : `test_write_coverage` y découvre toute dataclass). Un `World(...)` d'épreuve porte `{}`. La table n'entre pas dans `to_dict` : les octets du monde ne changent pas. Aucune variable de module, aucun `global` : la table vit sur le monde, comme `attribution_villes`.

**La durée.** `jours = max(1, ceil(distance_km / VITESSE_CONVOI_KM_PAR_JOUR))`. Un lieu qui est le siège de son maître est à 1 jour.
- **Même cellule** (`siege[0] == cell_id`) : la distance est celle des places des deux lieux, `sim/places.py`, `distance_km(places[cid][rang], places[cid][siege[1]])`, places calculées par `places_du_monde(monde)` au chargement. Le relief ne freine pas dans la cellule (niveau 3, non simulé).
- **Autre cellule** : le plus court chemin (Dijkstra, une recherche par cellule de siège) sur les arêtes **terrestres** de `World.adjacency` — celles dont les deux bouts sont dans `World.cells`, la règle du moteur ; une arête vers le nœud de mer ne se prend jamais. Longueur d'une arête : distance entre les centroïdes `centroid.x_m`, `centroid.y_m` (EPSG:3035, `metres_par_km()`), divisée par `min` des facteurs de `facteurs_transport_par_relief()` des deux cellules. Relief inconnu ou centroïde absent sur une arête empruntée : erreur qui nomme la cellule, jamais un repli. Le graphe ne se construit que si au moins un lieu a son maître hors de sa cellule.
- **Sans chemin terrestre** (une île, ou deux terres que rien ne relie) : `jours = JOURS_DE_MER`.

**Refus.** Un lieu sans maître (`maitre is None`) est absent de la table. Un maître absent de `World.maisons`, ou dont le siège est hors carte (`cell_id is None`), lève `RouteInvalide` (dans `convois.py`) qui nomme le couple du lieu.

**Constantes**, dans `jeu/sim/constants.py`, à côté de `PART_COUTUMIERE`, chacune avec son commentaire de **niveau 2** (plausible, jamais sourcé) :
- `VITESSE_CONVOI_KM_PAR_JOUR = 25.0` — un char à bœufs chargé, sur chemin de terre ;
- `JOURS_DE_MER = 10` — une traversée, chargement et attente du vent compris.

Elles se lisent **dans `sim/convois.py` seulement**, par `_constantes.X` relu à chaque appel, jamais dans `sim/engine.py` (sinon `test_chaque_constante_du_moteur_change_le_monde` les voit inertes sur le monde d'épreuve) ni par `from sim.constants import`. `test_no_hardcoded` refuse tout littéral autre que 0, 1, −1 : le `max(1, …)` passe, les kilomètres passent par `metres_par_km()`.

**Code.** `sim/convois.py` expose une fonction pure `routes_des_lieux(monde, places)` : elle lit `monde.cells` (le maître de chaque lieu), `monde.maisons`, `monde.adjacency`, `monde.carte`, et `places` (`cell_id` → places des lieux, la forme que rend `places_du_monde`), ne modifie rien, ne tire aucun aléa. Les mondes d'essai lui passent des `Place` construites à la main. `World.charger` l'appelle par un import local (comme `attribuer_maitres`) avec `places_du_monde(monde)`. `sim/engine.py` n'est pas touché.

**Mesures du chef (graine 0, à re-mesurer, jamais recopiées dans un test)** : 6 619 lieux, tous ont un maître siégeant dans leur propre cellule (0 route entre cellules sur la base : le chemin et la mer ne servent qu'aux mondes d'essai jusqu'à #397, vassal → suzerain) ; 4 706 lieux vont vers un siège de rang ≠ 0 (maisons plausibles). Jours : 2 569 lieux à 1, 1 034 à 2, 1 055 à 3, 831 à 4, … jusqu'à 14 (cellule 10167, 25 550 km², lieu 14 → `plausible-10167-12`, 335 km). Bar (`seigneurie-1`, cellule 10430) : rangs 0 à 3 → 1, 2, 1, 2 jours. Coût : `places_du_monde` 0,40 s, la table 0,02 s ; `World.charger` passe d'environ 1,64 s à 2,05 s. Le temps mesuré s'écrit dans le paragraphe de MODELE.md, avec la machine. 203 cellules sur 596 n'ont aucune arête terrestre.

## Périmètre
jeu/sim/convois.py
jeu/sim/constants.py
jeu/sim/world.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_convois.py
jeu/sim/tests/README.md

## Conditions de succès
Toutes dans `jeu/sim/tests/test_convois.py`, lancées par `cd jeu && python3 -m pytest sim/tests/test_convois.py -q`. Le monde de la graine 0 se charge une fois par module (fixture `scope="module"`). Chaque compteur est dérivé et affiché (`print`), jamais écrit en dur. Les mondes d'essai sont des `World(cells, adjacency, carte=…)` construits à la main (lieux, maîtres par `ecrire_maitre`, `monde.maisons` posé), sur lesquels le test appelle `routes_des_lieux` directement.

- **SC1 — La distance dans une cellule, sur le vrai monde.** Graine 0 : pour chaque lieu, `routes_des_lieux[(cid, rang)]` porte le maître du lieu, le siège `(cell_id, rang)` de sa fiche, et `jours == max(1, ceil(distance_km(places[cid][rang], places[s][r]) / VITESSE_CONVOI_KM_PAR_JOUR))` avec `places = places_du_monde(monde)` ; le nombre de lieux comparés vaut le nombre de lieux du monde et est > 0 ; tout lieu qui est le siège de son maître est à 1 jour ; le nombre de lieux à plus d'un jour est > 0 et affiché. Contre-épreuves : la même table recalculée avec des places où chaque lieu prend la place du bourg de sa cellule diffère sur un nombre de lieux > 0 (affiché) ; avec `VITESSE_CONVOI_KM_PAR_JOUR` remplacée en mémoire par le double, `routes_des_lieux(monde, places)` change les jours d'un nombre de lieux > 0, et la valeur remise rend la table à l'identique.
- **SC2 — Un chemin entre cellules, freiné par le relief.** Monde d'essai à quatre cellules, centroïdes en km : A (0, 0), B (50, 50), C (100, 0), D (50, 0) ; reliefs A, B, C `plaine`, D `montagne` ; arêtes terrestres A–B, B–C, A–D, D–C, plus A–S et C–S vers un nœud de mer S absent de `cells`. Le lieu de A a pour maître une maison siégeant en (C, 0) : `jours == 6` (par B, 141,4 km ; par D, 50/0,30 + 50/0,30 = 333 km). Contre-épreuves : relief ignoré (`facteurs_transport_par_relief` remplacée par une table à 1,0 partout) → 4 jours ; l'arête B–C retirée → 14 jours ; un relief inconnu sur B lève une erreur qui nomme B.
- **SC3 — Une île prend la mer.** Monde d'essai : A et E, reliées seulement par A–S et E–S au nœud de mer ; le lieu de E a pour maître une maison siégeant en (A, 0) : `jours == JOURS_DE_MER`. Contre-épreuves : mer ignorée — avec `JOURS_DE_MER` remplacée en mémoire par 3, la table dit 3 ; une arête terrestre A–E ajoutée donne la durée par terre (≠ `JOURS_DE_MER`, valeur dérivée des centroïdes choisis).
- **SC4 — Absence et refus déclarés.** Un `World(cells, adjacency)` construit à la main porte `routes_des_lieux == {}` ; un lieu sans maître est absent de la table ; un maître inconnu de `monde.maisons` lève `RouteInvalide` qui nomme le couple du lieu, un maître hors carte aussi. Contre-épreuve : le même monde avec un maître connu et placé rend une route.
- **SC5 — Le tick ne recalcule ni ne lit la table.** Sur le monde de la graine 0 (une copie), `sim.convois.routes_des_lieux` et `sim.places.places_du_monde` remplacés par des fonctions qui lèvent : trois `engine.tick` passent, et la table est égale (`==`) à celle d'avant. Par lecture AST de `jeu/sim/*.py` hors tests : `engine.py` n'importe pas `sim.convois` et ne lit pas l'attribut `routes_des_lieux` ; seul `world.py` l'écrit ; le nombre de modules parcourus est > 0. Contre-épreuves : un tick enveloppé qui recalcule la table lève ; le même détecteur appliqué au texte `"from sim.convois import routes_des_lieux"` le trouve.
- **SC6 — Rien d'autre ne bouge.** `"routes_des_lieux"` n'apparaît pas dans `json.dumps(monde.to_dict(), sort_keys=True)` ; deux `World.charger(0)` donnent la même table ; les attributs du module `sim.convois` sont les mêmes avant et après deux chargements (aucune variable de module). `cd jeu && python3 -m pytest sim -q` passe en entier **sans qu'aucun test existant soit modifié** : en particulier `test_maitre_tick` intact, les empreintes figées de `test_determinisme.py`, `test_no_hardcoded.py`, `test_write_coverage.py` (constantes déclarées et lues ; constantes du moteur), et les `deepcopy(monde.__dict__)` de `test_intentions.py`. Contre-épreuve : dans le test, le SHA-256 de `to_dict` auquel on ajoute à la main la table diffère de celui de `to_dict` seul.
- **SC7 — Le modèle le dit.** Un test lit la section « ## Le prélèvement » de MODELE.md (placée après « ## Le grenier d'une maison ») et y trouve `routes_des_lieux`, `VITESSE_CONVOI_KM_PAR_JOUR`, `JOURS_DE_MER`, `facteurs_transport_par_relief`, « niveau 2 », « niveau 3 » et un temps mesuré du chargement ; `jeu/sim/README.md` nomme `sim/convois.py` ; `jeu/sim/tests/README.md` nomme `test_convois.py`. Contre-épreuve : une section absente fait échouer la lecture (échantillon vide).

## Hors périmètre
- Le prélèvement lui-même, les convois en route, leur tick d'arrivée, la part provisoire à 0,03, les sept tests passés à part nulle (sous-lot 2 de la découpe de #396), la calibration et les nouvelles empreintes (sous-lot 3).
- Toute lecture de la table par le tick, `sim/engine.py`, le service, `/lieu`, la photographie, la chronique ou Unity (#400, #401, #405).
- La route intérieure de #418 et son « −1 jour de convoi » : attend que les convois existent.
- Le vassal qui envoie au suzerain (#397) : la table ne connaît que le maître direct.
- Ports, cabotage, saison de navigation, relief dans la cellule, routes construites : niveau 3, non simulés ici.
- Toucher `sim/places.py`, `sim/maitres.py`, `sim/engine.py` ou un test existant.
