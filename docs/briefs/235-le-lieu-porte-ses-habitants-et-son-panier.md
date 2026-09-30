# Lot #235 — Le lieu porte ses habitants et son panier
Jalon : J3 · Machine : vps · Taille prévue : 280 lignes

## But
Chaque lieu d'une cellule porte désormais ses habitants et son panier : l'amorçage les répartit, le tick les tient à jour, et la cellule est exactement la somme de ses lieux — le socle sur lequel le jalon 3 posera le maître de chaque lieu, puis le prélèvement (CAP.md, preuve du J3 : « les lieux d'une cellule font la cellule, rien ne se perd au découpage »).

## Règle du monde
Le lot #234 a découpé la surface d'une cellule en lieux (`sim/lieux.py`, identité (`cell_id`, `rang`), le rang 0 est le bourg). Ce lot y met les gens et les kilos, sans en créer ni en perdre un seul.

Cela découle de `jeu/sim/MODELE.md` : « Les lieux d'une cellule, vue dérivée » (le découpage, qui reste la seule source du nombre de lieux et de leurs surfaces), « Population initiale par cellule », « Le panier de marchandises » (absence contre zéro), « Ce qu'est une ville, à l'échelle d'une cellule » (le bourg) et « Le moteur sans état caché ». `cell_id` reste la seule clé spatiale : un lieu stocké ne porte que son `rang`, jamais un `cell_id` recopié ni un `lieu_id`.

**Niveau 2** : la répartition est plausible, jamais sourcée. **Niveau 3, pas simulé** : aucun mouvement propre aux lieux. Le tick continue de tout calculer à l'échelle de la cellule (production, commerce, repas, faim, morts, naissances, migration) ; la distribution à l'intérieur de la cellule **reste gratuite** ; le bourg ne concentre pas encore les gens de la ville (#209) ni ceux que `RepartitionBourg` compte hors des champs.

**La règle unique de partage** — `partager(total, poids) -> list`, dans `sim/lieux.py`, rang par rang (indice 0 = bourg). C'est la méthode du plus fort reste, en unités entières (une personne, un kilogramme) :
1. `S = somme(poids)` ; un poids négatif, non fini ou booléen, une somme nulle, un total négatif, non fini ou booléen sont refusés par `LieuxInvalides` — jamais devinés.
2. part exacte de chaque rang : `x_r = total × poids_r / S` ; part entière `floor(x_r)`.
3. unités restantes `u = floor(total) − Σ floor(x_r)` (bornée à `[0, nombre de lieux]`) : une unité de plus aux `u` rangs de plus grand reste `x_r − floor(x_r)`, à égalité le plus petit rang.
4. chaque rang ≥ 1 reçoit sa part entière ainsi obtenue ; **le bourg reçoit le reste**, `total − Σ parts des rangs ≥ 1`. Si ce reste est négatif, `LieuxInvalides`.

Pourquoi cette forme : les rangs ≥ 1 portent des entiers, et le reste d'un total moins un entier plus petit que lui se calcule sans arrondi en flottant (même argument que les surfaces de #234) ; la somme des lieux égale donc la cellule **au bit près**, pour les habitants (entiers) comme pour les kilos (flottants). Le plus fort reste évite le biais d'un partage « plancher partout, le reste au bourg », qui ferait grossir le bourg d'une fraction d'habitant par lieu à chaque tick.

**L'amorçage.** Dans `World.charger`, une fois la population et le panier de la cellule posés, ses lieux reçoivent la population et chaque marchandise du panier par `partager(total, surfaces des lieux)`, les surfaces venant de `lieux_de_cellule(cid, area)`.

**Le tick.** Un seul maillon neuf, **après la migration et avant l'avance du compteur** : pour chaque cellule qui porte des lieux, `repartir_sur_les_lieux(cellule)` remet ses lieux d'accord avec elle, quantité par quantité (population, puis chaque marchandise du panier) :
- si la somme des lieux (dans l'ordre des rangs) égale déjà le total de la cellule, rien ne bouge ;
- sinon `partager(total de la cellule, contenu actuel de chaque lieu)` : chacun garde sa proportion ;
- si tous les lieux sont à zéro pour cette quantité (une marchandise neuve dans la cellule, une population revenue de zéro), les poids sont les surfaces ;
- les lieux portent **exactement** les marchandises du panier de la cellule : une marchandise absente de la cellule est retirée des lieux (l'absence n'est pas zéro).
Cette règle suit ce que le tick a fait à la cellule, et aussi toute écriture faite à la cellule hors du tick (un test, un futur geste) : elle compare les lieux à la cellule, jamais à l'état d'avant.

Une cellule sans lieux (liste vide : les mondes d'épreuve construits à la main par `Cell(...)`) n'est pas découpée, et le tick ne lui en invente pas. Toute cellule d'un monde amorcé par `World.charger` porte ses lieux. Les compteurs de faim, la dette et les restes de mortalité, natalité et migration restent à la cellule.

### Ce que le codeur écrit

**1. `jeu/sim/model.py`** — une dataclass mutable `EtatDeLieu(_NoBadSpatialField)` avec **exactement** les champs `rang: int`, `population: int`, `stocks: dict[str, float]` ; sur `Cell`, un champ déclaré `lieux: list` (défaut : liste vide ; paramètre `lieux=None` de `__init__`, copié en liste). `cellule_vers_dict` ajoute `"lieux": [{"rang", "population", "stocks"} …]` dans l'ordre des rangs, paniers copiés : l'empreinte (`World.to_dict`) porte ainsi les lieux.

**2. `jeu/sim/lieux.py`** — `partager`, `repartir_sur_les_lieux(cellule)`, et `amorcer_lieux(cellule) -> list` (celle-ci sert à `World.charger`). Aucun littéral numérique autre que 0, 1, −1 dans un corps de fonction ; aucune constante neuve. `lieux_de_cellule`, `lieux_par_cellule`, `lieux_depuis_monde` ne changent pas.

**3. `jeu/sim/world.py`** — l'appel à `amorcer_lieux` pour chaque cellule amorcée.

**4. `jeu/sim/engine.py`** — le maillon, appelé par le module (`import sim.lieux as _lieux`, puis `_lieux.repartir_sur_les_lieux(cell)`) pour qu'un test puisse le remplacer ; la docstring de `tick()` nomme le maillon.

**5. `jeu/sim/snapshot_export.py`** — chaque cellule de la photographie porte `"lieux"` : pour chaque lieu stocké, `rang`, `surface_km2` (lue de `lieux_de_cellule`), `population`, `stocks`. Si le nombre de lieux stockés diffère de celui de la vue, `SnapshotExportError` qui nomme la cellule. Aucune fonction dont le nom contient « bourg ». `SNAPSHOT_SCHEMA_VERSION` ne change pas (voir Hors périmètre).

**6. `jeu/sim/tests/test_monde.py`** — **la seule retouche d'un test existant, décidée par le propriétaire (réponse A)** : ajouter `"lieux",` à l'ensemble `_CELL_KEYS`. Rien d'autre ne change dans ce fichier.

**7. `jeu/sim/tests/test_lieux.py`** — les cas des conditions ci-dessous, ajoutés à la suite ; les tests existants du fichier ne changent pas.

**8. `jeu/sim/MODELE.md`** — la section « Les lieux d'une cellule, vue dérivée » garde le découpage et gagne une sous-section « Ce que porte un lieu » : `EtatDeLieu`, la règle de partage et pourquoi elle est exacte, l'amorçage par les surfaces, le maillon du tick et ses cas (déjà d'accord, proportion, zéro → surfaces, absence), la cellule sans lieux, le niveau 2. La phrase « il ne reçoit aucun habitant » et « le tick ne la lit pas » sont réécrites : le tick ne lit pas les lieux pour calculer, il les remet d'accord à la fin. Dans « En une page », la liste du tick gagne le maillon entre la migration et l'avance du compteur, et le paragraphe des vues dérivées dit que les lieux portent désormais population et panier ; dans « Ce que le moteur ne fait pas encore », la puce « descendre sous la cellule » dit que les lieux portent habitants et paniers, mais que le tick calcule toujours à l'échelle de la cellule.

## Périmètre
jeu/sim/model.py
jeu/sim/lieux.py
jeu/sim/world.py
jeu/sim/engine.py
jeu/sim/snapshot_export.py
jeu/sim/tests/test_lieux.py
jeu/sim/tests/test_monde.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent depuis la racine par `python3 -m pytest jeu/sim/tests/test_lieux.py -q -s -k <nom>`. Chaque test imprime ses compteurs ; un échantillon vide échoue ; aucun `cell_id` n'est écrit en dur (les cellules se choisissent par leurs données). Le contrôle de conservation est **une fonction du test**, `_controle_conservation(monde)`, qui rend le nombre de cellules contrôlées et lève `AssertionError` au premier écart : pour chaque cellule, lieux non vides, rangs `0 … n − 1` avec `n = len(lieux_de_cellule(cid, area))`, `Σ population des lieux == cellule.population`, et pour chaque marchandise `set(stocks du lieu) == set(cellule.stocks)`, `sum(…) == cellule.stocks[m]` et `sum(Fraction(…)) == Fraction(cellule.stocks[m])` ; aucune valeur négative.

**SC1 — la règle de partage** (`-k partager`). Cas synthétiques : la somme rendue égale le total (en `Fraction`) ; chaque part, bourg compris, s'écarte de sa part exacte de moins d'une unité quand le total est entier ; les rangs ≥ 1 sont entiers ; `partager(9, [1] * 10)` rend neuf 1 aux rangs 0 à 8 et 0 au rang 9 ; un total flottant (`1234.75`) laisse sa fraction au bourg. Refus par `LieuxInvalides` pour un poids négatif, `nan`, `True`, des poids tous nuls, un total négatif ou `inf` (compteur `refus_observés` égal à la longueur de la liste). Contre-épreuve, dans le même test : le partage naïf « plancher pour les rangs ≥ 1, reste au bourg », écrit dans le test, échoue au contrôle « moins d'une unité » sur `(9, [1] * 10)` — le contrôle voit le biais.

**SC2 — l'amorçage conserve** (`-k amorcage`). Sur `World.charger(0)` : `_controle_conservation` rend `len(monde.cells)` ; au moins une cellule a plusieurs lieux peuplés ; la population totale des lieux égale celle des cellules. Contre-épreuve de l'issue, dans le même test : sur une copie profonde, retirer un habitant à un lieu peuplé (choisi par les données) fait lever le contrôle ; et un amorçage par un `partager` remplacé (`monkeypatch.setattr(sim.lieux, "partager", …)`) qui oublie une unité fait lever le contrôle sur le monde ainsi chargé — un découpage qui perd un habitant échoue.

**SC3 — le tick répartit par la même règle** (`-k tick`). Graine 0, `numero_tick` explicite, une année calendaire : `_controle_conservation` passe **après chaque tick** ; compteurs imprimés : cellules dont la population a changé, marchandises apparues dans une cellule en cours d'année, lieux dont le contenu a changé — les deux premiers > 0. Le test imprime aussi le temps moyen du tick et la part du maillon de répartition (mesurés, pas exigés). Un cas synthétique sur une cellule amorcée : une marchandise neuve se partage par les surfaces, une marchandise retirée quitte tous les lieux, une population écrite à la main se répartit au tick suivant. Contre-épreuve : avec `sim.lieux.repartir_sur_les_lieux` remplacé par une fonction qui ne fait rien, le contrôle lève après le premier tick.

**SC4 — les lieux ne changent pas le monde de la cellule** (`-k cellule`). Deux mondes graine 0, l'un dont on vide les lieux de chaque cellule (`lieux = []`), trente ticks avec la même graine : les états des cellules sans la clé `"lieux"` de `cellule_vers_dict` sont identiques. Puis, sur un monde amorcé, déplacer un habitant d'un lieu à un autre dans une même cellule (total inchangé) ne change aucun total de cellule après dix ticks. Contre-épreuve : la même comparaison voit l'écart d'un habitant écrit sur une cellule.

**SC5 — l'empreinte et la photographie portent les lieux** (`-k photographie`). Deux courses identiques de 25 ticks donnent le même `json.dumps(to_dict(), sort_keys=True)`, et chaque cellule y porte `"lieux"`. `build_snapshot_document(World.charger(0), 0, 0)` : chaque cellule a `"lieux"`, dans l'ordre des rangs, avec exactement les clés `{"rang", "surface_km2", "population", "stocks"}`, autant de lieux que la vue, la population sommée égale celle de la cellule, les surfaces égales à celles de `lieux_de_cellule`. Sur `serialize_snapshot`, `python3 -m sim --ticks 0 --seed 0 --json` rend deux fois les mêmes octets. Contre-épreuves : déplacer un habitant entre deux lieux d'une cellule, totaux inchangés, change l'empreinte `to_dict` et le SHA-256 de la photographie ; retirer un lieu stocké d'une cellule fait lever `SnapshotExportError` qui nomme son `cell_id`.

**SC6 — rien d'existant ne s'assouplit.** `python3 -m pytest jeu -q` est vert. `git diff master --numstat -- jeu/sim/tests/test_monde.py` rend `1 0`, et la ligne ajoutée est `"lieux",` dans `_CELL_KEYS` ; `git diff master --numstat -- jeu/sim/tests/test_lieux.py` rend 0 ligne retirée ; aucun autre test ne change. `test_no_hardcoded.py`, `test_province.py` (aucun attribut non déclaré sur `Cell`), `test_determinisme.py`, `test_commerce.py`, `test_survie.py`, `test_villes.py` restent tels quels. Contre-épreuve : sans la ligne `"lieux",` dans `_CELL_KEYS`, `python3 -m pytest jeu/sim/tests/test_monde.py -q -k schema_ferme` rougit (le test existant exige désormais les lieux) ; un littéral `2` glissé dans un corps de fonction de `lieux.py` rend `test_no_hardcoded` rouge.

**SC7 — le modèle le dit.** `awk '/^## Les lieux d.une cellule/{s=1;next} /^## /{s=0} s' jeu/sim/MODELE.md` contient « Ce que porte un lieu », `partager`, « plus fort reste », `repartir_sur_les_lieux` et « au bit près », et ne contient plus « ne reçoit aucun habitant ». `awk '/^## En une page/{s=1;next} /^## /{s=0} s' jeu/sim/MODELE.md | grep -c "lieux"` rend au moins 2. Contre-épreuve : sur la base, la première commande ne contient ni `partager` ni « Ce que porte un lieu », et contient « ne reçoit aucun habitant ».

## Hors périmètre
- Le maître d'un lieu, son suzerain, le prélèvement, le transport à l'intérieur de la cellule, la faim d'un lieu : les lots suivants du J3. Aucun calcul du tick ne se fait par lieu.
- La concentration des gens de la ville (#209) ou de `RepartitionBourg` dans le bourg ; `sim/aggregation.py` et `sim/villes.py` ne changent pas.
- La dette, les compteurs de faim et les restes de mortalité, natalité et migration par lieu.
- Le service (`/lieu`, `/monde`), la chronique, le tableau et Unity : aucun ne lit ni ne montre les lieux dans ce lot.
- `SNAPSHOT_SCHEMA_VERSION` reste `v0a-5` : `test_aridite.py` la fige, et la seule retouche d'un test existant autorisée est `_CELL_KEYS`. Changer la version attend un lot ou une décision du propriétaire.
- Toute constante neuve, la forme, la position et les noms des lieux, `jeu/data/`.
