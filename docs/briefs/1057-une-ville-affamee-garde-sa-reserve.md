# Lot #1057 — Une ville affamée garde sa réserve
Jalon : J5 · Machine : vps · Taille prévue : 700 lignes

## But
Une cellule dont les champs ne nourrissent pas les habitants garde dans son
grenier une réserve de `reserve_ville_affamee_jours` jours de ration, soit 365
jours, déclarée dans `jeu/data/commerce.toml`, et n'exporte que ce qui
dépasse. Au premier mois de 1400, Gand et Le Caire cessent donc de vider leur
soudure par la mer.

## Le joueur
Le joueur voit ses villes garder leur grain au lieu de vider leurs greniers
pour les voisines. C'est la phrase de l'issue.

Aujourd'hui, Gand et Bruges expédient 10 595 t au bassin pendant le premier
mois, soit un peu moins d'un jour de ration par jour. Le Caire en expédie
7 733 t et Florence 4 206 t, alors que leurs champs ne nourrissent que 39 %,
61 % et 77 % de leurs habitants. Après ce lot, ces villes finissent janvier
avec leur soudure presque entière, moins ce qu'elles ont mangé.

C'est un lot de fond du jalon 5. Il prépare « le monde tient seul » : après
dix ans, la Flandre et l'Italie du Nord doivent rester pleines. Il prépare
aussi la décision « un voisin mieux nourri attire les siens ». Deux lots le
rendront visibles : #1026, la table à dix ans contre le commerce d'avant, et
#429, le grenier des capitales voisines dans l'infobulle du socle.

## Règle du monde
Elle découle de `jeu/sim/MODELE.md`, « Le commerce entre cellules → Besoin,
surplus et allocation », qui change. Niveau 2 : plausible, jamais sourcé.
L'idée est médiévale : une ville que son contado ne nourrit pas interdit la
sortie de son grain. La durée de la réserve, elle, n'est pas sourcée.

**Ce qui fait une ville affamée.** Une cellule est *affamée* quand sa
population du snapshot du commerce dépasse ce que ses champs nourrissent au
rendement et à la saison moyens. On compare `snapshot_pop[cid]` et
`population_soutenable_de(cellule, carte)`, l'unique formule de production.
Cette formule ne dépend que de la surface et de la carte, qui ne bougent pas
pendant la partie. Le monde la relève donc une fois, à l'amorçage :
`World.charger` garde, dans un nouvel attribut
`World.populations_soutenables: dict[int, float] | None`, le `soutenable` que
sa boucle calcule déjà. Il n'y a ni second calcul ni lecture de la carte au
tick : un accès au dictionnaire par cellule offrante, le tick reste sous ses
100 ms. L'attribut se pose comme `populations_bourg_amorcage` : hors de
`to_dict`, hors de la photographie et de l'empreinte. Un monde construit à la
main (`World(cells=…)`, les petits mondes des tests) vaut `None`. C'est une
absence déclarée, comme `stocks_mer` : sans relevé des champs, la règle
d'avant s'applique. Si le dictionnaire existe mais qu'une cellule y manque, le
code lève une erreur qui nomme le `cell_id` et ne devine rien.

**Le surplus.** Seule la garde change. Le reste ne bouge pas : le besoin,
l'allocation, l'écrêtage, les quais, le passage par le bourg et les chemins
intérieurs.

```
ration_tick(c) = population_c × consommation_unitaire(marchandise)
garde(c)       = ration_tick(c)                                  si c n'est pas affamée
               = max(ration_tick(c),
                     N × population_c × consommation_unitaire / TICK_DURATION_DAYS)
                                                                 si c est affamée
surplus(c)     = max(0, stock_c − garde(c))
besoin(c)      = max(0, ration_tick(c) − stock_c)                (inchangé)
```

- `N = reserve_ville_affamee_jours`, lu dans `jeu/data/commerce.toml`
  (décision 37), vaut 365 et est de niveau 2. Le lecteur
  `sim.constants.reserve_ville_affamee_jours()` relit le fichier à chaque
  appel, comme les autres lecteurs de `jeu/data/` : `_apply_commerce` l'appelle
  une fois par marchandise consommée, et seulement quand le monde porte
  `populations_soutenables`. Il refuse, par une `ValueError` qui nomme la clé
  et le fichier, un fichier ou une clé absents, un booléen, un nombre non
  entier, ou une valeur inférieure à 1.
- Avec `N = 1`, la garde redevient la ration du tick, au bit près
  (`TICK_DURATION_DAYS = 1`). C'est le commerce d'avant, et c'est la
  contre-épreuve de tout ce lot.
- Avec `N = 365`, la soudure (212 jours de ration au 1er janvier) reste
  entière sous la réserve. Une ville affamée n'exporte donc rien, ni par
  terre ni par la mer : `_planifier_expedition` lit le même `_surplus`.
- Le besoin ne change pas. Une ville affamée dont le stock tombe sous un jour
  de ration reçoit toujours de ses voisines et du bassin.
- Aucun kilo n'est créé ni détruit : ce qui n'est pas exporté reste dans le
  panier de sa source. `food_deficit_kg` n'est toujours pas touché.

**Mesure du premier mois** (graine 0, IA active, 30 jours, prise par le chef
le 11 novembre 2026). La « règle d'avant » est N = 1, la « réserve » N = 365.
Huit cellules sur 596 sont affamées au départ : Le Caire (8992), Alexandrie
(10168), Grenade et Malaga (10209), Florence (10260), Paris (10322), Gand et
Bruges (10391), Gênes (10456), Milan (10466).

| ville | soutenable / habitants | expédié par la mer, règle d'avant | réserve | stock au 30e jour, avant → réserve |
|---|---|---|---|---|
| Gand et Bruges | 70 656 / 181 000 | 10 595 t | 0 t | 58 922 t → 69 465 t |
| Le Caire | 219 163 / 360 000 | 7 733 t | 0 t | 135 478 t → 143 211 t |
| Florence | 77 602 / 101 000 | 4 206 t | 0 t | 36 419 t → 40 624 t |
| Paris | 66 225 / 275 000 | 0 t | 0 t | 103 490 t → 103 490 t |
| Milan | 85 899 / 177 000 | 0 t | 0 t | 68 822 t → 68 822 t |

Paris et Milan n'exportent rien sous les deux règles : sans port, ils ne
vendent que par terre, et aucune de leurs voisines ne tombe sous un jour de
ration en janvier. **Paris ne compte donc pas comme preuve** (principe 8).
Les cellules qui se nourrissent ne changent pas de règle. Après 4 jours, seules
les six cellules affamées qui ont un port et le bassin diffèrent ; après 20
jours, treize cellules diffèrent, par les débarquements. Ces chiffres viennent
d'un script jetable du chef, qui cachait la réserve au snapshot. Le test de
SC3 les remesure sur le vrai code.

**La docstring de `population_soutenable_de`** (`jeu/sim/engine.py`, vers
la ligne 269) dit aujourd'hui « Lue à l'amorçage (`sim.world`) et par
personne d'autre : le tick ne la consulte jamais. » Le lot la corrige : elle
est lue à l'amorçage, et le commerce lit la valeur relevée alors
(`World.populations_soutenables`). La docstring de `_apply_commerce` et
`MODELE.md` (« Besoin, surplus et allocation », plus une phrase dans
« Population initiale par cellule ») donnent la nouvelle formule, la
constante, son niveau, la contre-épreuve N = 1 et le tableau ci-dessus.

**Le décor d'avant.** `jeu/sim/tests/amorcage_d_avant.py` sert le décor
d'avant la soudure : les réponses figées du pont, les calibrages cités dans
`MODELE.md` et les épreuves d'une famine précoce. Avec cinq jours de stock,
les villes affamées de ce décor seraient toutes sous la réserve et cesseraient
d'exporter, ce qui bougerait leurs octets. Le lot #1029 a réglé ce problème
pour la famine avec `couper_la_famine`. Celui-ci fait de même :
`garder_le_commerce_d_avant(monkeypatch)` remplace
`sim.constants.reserve_ville_affamee_jours` par une fonction qui rend 1.
`amorcer_comme_avant_la_soudure` et `poser()` l'appellent tous les deux, et la
docstring du module le dit (« le décor d'avant la soudure est aussi celui
d'avant la famine et d'avant la réserve des villes affamées »). Le moteur
appelle le lecteur par le module (`_constantes.reserve_ville_affamee_jours()`),
pour que le remplacement porte.

## Périmètre
jeu/sim/engine.py
jeu/sim/world.py
jeu/sim/constants.py
jeu/data/commerce.toml
jeu/sim/MODELE.md
jeu/sim/tests/amorcage_d_avant.py
jeu/sim/tests/test_commerce.py
jeu/sim/tests/test_modificateurs.py
jeu/sim/tests/test_determinisme.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_lieux.py
jeu/sim/tests/test_flux.py
jeu/sim/tests/test_convois.py
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_foyers.py
jeu/sim/tests/test_portes.py
jeu/sim/tests/test_ville1400.py
jeu/sim/tests/test_ville_dense.py
jeu/sim/tests/README.md
jeu/forge/tests/test_forge.py
jeu/vues/relief/tests/test_carte1400.py
docs/mesures/2026-11-11-ville-affamee/RAPPORT.md

Dans les fichiers de tests existants autres que `test_commerce.py` et
`test_modificateurs.py`, on ne touche **que** la valeur d'une empreinte
épinglée qui bouge (SC6), et le commentaire qui la date. On ne retire aucune
assertion, on n'élargit aucune tolérance et on ne saute aucun cas. Les fichiers
de cette liste qui ne bougent pas restent intacts.

## Conditions de succès
Les commandes se lancent depuis `jeu/`. Tous les cas neufs vont dans
`sim/tests/test_commerce.py`, le fichier qui porte les invariants du commerce.
Aucun de ses 101 tests existants ne change : ils construisent des mondes à la
main, sans `populations_soutenables`, et gardent la règle d'avant. **Si l'un
d'eux rougit, on s'arrête** : la question remonte au propriétaire, sans
assouplir le test.

**SC1 — La règle sur un petit monde.**
`python3 -m pytest sim/tests/test_commerce.py -q -k reserve_ville_affamee`.
On utilise deux cellules voisines par terre, posées à la main, avec
`world.populations_soutenables` posé à la main et le lecteur remplacé par
`monkeypatch` :
- (a) une source affamée (population 100, soutenable 50) avec 10 jours de
  ration, et une receveuse vide. Avec N = 30, la source n'envoie rien et garde
  son stock au kilo près.
- (b) la même source avec 40 jours de ration et N = 30 : elle envoie le besoin
  du jour de la receveuse, et son stock ne descend jamais sous 30 jours de
  ration.
- (c) une source qui se nourrit (soutenable 100 ≥ population 100) avec 10
  jours de ration et N = 365 : elle envoie exactement ce qu'elle envoie avec
  N = 1.
- (d) une source affamée qui manque (stock sous un jour de ration) : elle
  reçoit toujours son besoin d'une voisine qui se nourrit.

Contre-épreuves :
- dans (a), N = 1 fait partir le grain : l'envoi est strictement positif et
  égal, au bit près, à celui d'un monde sans `populations_soutenables` ;
- dans (a), `populations_soutenables = None` avec N = 365 envoie aussi :
  c'est la règle d'avant ;
- un dictionnaire qui ne porte pas la source lève une erreur qui nomme son
  `cell_id`.

**SC2 — La donnée.**
`python3 -m pytest sim/tests/test_commerce.py -q -k reserve_ville_affamee_donnee`.
Le lecteur rend 365 sur `jeu/data/commerce.toml`, et ce fichier dit le
niveau 2 en commentaire. Contre-épreuves, sur des fichiers écrits dans
`tmp_path` : `0`, `-3`, `2.5`, `"365"`, `true`, une clé absente et un
fichier absent lèvent chacun une `ValueError` qui nomme
`reserve_ville_affamee_jours`.

**SC3 — Le premier mois de 1400.**
`python3 -m pytest sim/tests/test_commerce.py -q -k premier_mois_ville_affamee`.
On charge `World.charger(0)` une fois, puis on joue deux copies
(`copy.deepcopy`), IA active (`jouer_ia` avant chaque `engine.tick`, comme
l'épreuve de la soudure), pendant 30 jours. Les sorties d'une cellule se
mesurent jour par jour : c'est la baisse de son stock de nourriture pendant
l'appel extérieur de `engine._apply_commerce`, que l'on enveloppe avec une
garde de profondeur comme dans `docs/mesures/2026-11-07-refonte/scripts/diagnostic_villes.py`.
Cette mesure est sûre : une cellule qui exporte a un besoin nul, donc ne
reçoit rien le même jour. Les villes se trouvent par leur nom, dans
`monde.attribution_villes.placees`.
- Les cellules affamées se dérivent de `populations_soutenables` : il en faut
  au moins deux, sinon l'échantillon est vide et le test échoue. Avec la
  donnée du dépôt (N = 365), le stock de départ de chacune est sous N jours de
  ration (le test l'affirme, pour que la preuve soit bien posée), et toutes
  sortent 0 kg en 30 jours. Le test nomme Gand (`placees["Gand"]`) et Le
  Caire.
- Le stock de Gand et celui du Caire au 30e jour sont strictement plus
  grands qu'avec la règle d'avant.
- Paris est affamé et sort 0 kg sous les deux règles. Le test l'affirme et
  l'écrit dans sa docstring, sans le compter dans la preuve.

Contre-épreuve : la seconde copie se joue sous `garder_le_commerce_d_avant`
(N = 1). Gand sort plus de 1 000 t et Le Caire plus de 1 000 t (mesuré :
10 595 t et 7 733 t), et au moins deux cellules affamées sortent plus de
0 kg. Une règle qui ne ferait rien ferait donc échouer la première copie. Le
test imprime les sorties et les stocks, ville par ville, sous les deux
règles. Le codeur recopie la table imprimée dans
`docs/mesures/2026-11-11-ville-affamee/RAPPORT.md`, avec la commande.

**SC4 — La conservation des kilos.** Le même test, ou son voisin
`-k conservation_ville_affamee`, sur la copie N = 365. À chaque appel
extérieur de `_apply_commerce`, la masse des paniers des cellules plus le
bassin (`math.fsum`, comme `_masse_totale_avec_bassin`) est la même avant et
après, à `1e-9 × masse` près. Et pour chaque cellule affamée qui ne reçoit
rien, la somme des paniers de ses lieux est égale à son stock avant et après.
Contre-épreuve : une enveloppe qui ajoute 1 t au panier de Gand après le
commerce fait échouer la vérification. Le test la joue sur un tick, dans un
`pytest.raises(AssertionError)`.

**SC5 — N = 1 redonne le monde d'avant, octet pour octet.** On prouve le
rouge d'abord, dans cet ordre, avant de toucher une empreinte :
1. Une fois le moteur codé, mettre `reserve_ville_affamee_jours = 1` dans
   `jeu/data/commerce.toml`, puis lancer les tests à empreinte de la liste de
   SC6, dans leur version de master. Ils sont tous verts.
2. Remettre 365 et relancer : la liste des tests rouges est celle des
   empreintes qui bougent.

Contre-épreuve : avec `amorcer_comme_avant_la_soudure` privé de
`garder_le_commerce_d_avant`, `python3 -m pytest forge/tests/test_forge.py -q -k test_forge_ia_sans`
rougit, et au moins une épreuve du décor d'avant avec lui. Avec
l'appel, tous redeviennent verts. Le codeur note les deux listes et les
commandes dans `RAPPORT.md`.

**SC6 — Les empreintes recapturées.** Les candidats, épinglés sur le monde de
la soudure, sont :
- dans `test_determinisme.py`, `_PART_BASE`, `_PRELEVEMENT_BASE` et
  `_DU_BASE` (`-k "bit_pres"`) ;
- dans `test_monde.py`, les empreintes de `test_service_ia_sans` et des
  réponses figées aux ticks 3 et 4 ;
- `test_ville1400.py:618`, `test_ville_dense.py` (`_EMPREINTES_BASE`), et les
  empreintes de `test_lieux.py`, `test_flux.py`, `test_convois.py`,
  `test_maisons.py`, `test_foyers.py`, `test_portes.py`,
  `forge/tests/test_forge.py` et `vues/relief/tests/test_carte1400.py`.

Ceux que SC5 trouve rouges sont recapturés sous Linux, sans rien d'autre
qui change. Le commentaire de chacun date la mesure (« recapturée le … ,
lot #1057, réserve des villes affamées »).

L'exception est `test_modificateurs.py::test_sans_modificateur_la_photographie_a_365_jours_est_celle_d_avant`.
Il épingle aussi une valeur `win32`, qu'on ne peut pas mesurer sur le VPS, et
il éprouve « sans modificateur, le monde d'avant ». Il reçoit donc
`garder_le_commerce_d_avant(monkeypatch)` à côté de `couper_la_famine`, avec
le commentaire du lot, et garde ses deux valeurs. C'est le patron de #1029.
`sim/tests/README.md` met à jour sa table des empreintes.

Le rouge est déjà prouvé par SC5 2.
La preuve finale : `python3 -m pytest jeu -q` est vert en entier, y compris
les budgets du tick, inchangés (`test_monde.py::test_tick_sous_le_budget_du_service`,
`test_flux.py::test_budget_flux_et_contre_epreuve`).
Si un test qui lit un fichier figé du pont (`3d/unity/…/Pont/Tests/*.json`)
rougit, le lot s'arrête : ces fichiers sont hors du périmètre, et la question
remonte au propriétaire.

**SC7 — La documentation dit la règle.**
`grep -n "reserve_ville_affamee_jours" sim/MODELE.md data/commerce.toml sim/engine.py`
trouve les trois fichiers.
`grep -n "le tick ne la consulte jamais" sim/engine.py` ne trouve plus rien.
Contre-épreuve : sur master, la première commande ne trouve rien et la
seconde trouve la ligne 269.

## Hors périmètre
- La tenue à dix ans et la table du jalon 2 contre le commerce d'avant :
  c'est la preuve de #1026, qui lira cette règle.
- Un N différent selon la ville, la saison ou la maison. Un modificateur
  sur la réserve : la grandeur n'entre pas au registre dans ce lot.
- Les greniers des maisons (`World.greniers`), le secours et la part : leurs
  règles ne bougent pas.
- La vue : ni Unity, ni l'infobulle, ni la photographie ne lisent la réserve
  (#429).
- Les fichiers figés du pont sous `3d/`, et tout chemin hors du Périmètre.
- Une ville qui achète au loin : il n'y a ni prix ni marché (jalon 8).
