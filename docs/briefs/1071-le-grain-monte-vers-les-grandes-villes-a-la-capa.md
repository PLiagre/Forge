# Lot #1071 — Le grain monte vers les grandes villes à la capacité d'un rayon de charroi et de batellerie
Jalon : J5 · Machine : vps · Taille prévue : 1000 lignes

## But
Une ville que ses champs ne nourrissent pas appelle chaque jour, par terre et
par la mer, le grain qui lui manque. Les arêtes qui la touchent portent le
charroi et la batellerie d'un rayon de quelques jours. Après un an, Paris,
Milan, Gand et Alexandrie gardent donc plus d'habitants et plus de grain
qu'avec le commerce d'avant, et Le Caire plus de grain.

## Le joueur
Le joueur retrouve ces villes mieux nourries après un an. C'est la phrase de
l'issue, avec la décision B de la direction : Alexandrie entre dans la preuve
des habitants, et Le Caire n'y est jugé que sur son grain.

Aujourd'hui (graine 0, IA active, 365 jours), Paris tombe de 275 000 à
153 052 habitants. Il ne meurt pas de faim : ses gens partent vers des voisins
mieux nourris, et il finit l'année avec 956 t. Alexandrie perd un tiers de ses
habitants par la faim, et Gand finit sans un grain. Les mesures jetables du
chef, prises le 12 novembre 2026, donnent un ordre de grandeur. Avec la
règle de ce lot, Paris finit à 284 985 habitants et 8 081 t, Milan à 196 333
habitants et 50 292 t, Gand à 89 260 habitants et 1 665 t, Alexandrie à
42 231 habitants et 1 252 t, et Le Caire à 23 196 t. Le test de SC3 refait
ces mesures sur le vrai code.

C'est un lot de fond du jalon 5. Il prépare « le monde tient seul » :
l'Europe qu'on retrouve après dix ans doit être encore celle de 1400. Il
prépare aussi la décision « un voisin mieux nourri attire les siens » : une
capitale qui se nourrit cesse de vider ses rues vers ses voisines. Deux lots
le rendront visible. #1026 portera la table à dix ans contre le commerce
d'avant. #429 mettra le grenier des capitales voisines dans l'infobulle du
socle.

## Règle du monde
La règle découle de `jeu/sim/MODELE.md`, « Le commerce entre cellules », qui
change dans deux de ses sous-sections : « Besoin, surplus et allocation »
pour l'appel, et « La capacité d'une arête » pour le rayon. Elle est de
niveau 2 : plausible, jamais sourcée. L'idée est médiévale : une grande ville
draine le grain de son contado et de ses fleuves, bien au-delà d'une journée
de route. Ni la part appelée ni la longueur du rayon ne sont sourcées.

**Ce qui fait une ville affamée** ne change pas depuis le lot #1057 : sa
population du snapshot du commerce dépasse `World.populations_soutenables[c]`.
Sans relevé des champs (`populations_soutenables` vaut `None`, le cas d'un
monde construit à la main), aucune cellule n'est affamée et la règle d'avant
s'applique. Une cellule absente d'un relevé qui existe lève l'erreur qui nomme
son `cell_id`, comme pour la garde.

**L'appel.** Seul le besoin change. La garde, le surplus, l'allocation,
l'écrêtage, les quais, le passage par le bourg et les chemins intérieurs ne
bougent pas.

```
ration(c) = population_c × consommation_unitaire(marchandise)
appel(c)  = P × (population_c − soutenable_c) × consommation_unitaire   si c est affamée
          = 0                                                            sinon
besoin(c) = max(0, ration(c) − stock_c, appel(c))
```

- `P = appel_ville_affamee_part` se lit dans `jeu/data/commerce.toml`
  (décision 37). Il vaut **1,0** : la ville appelle chaque jour tout ce que
  ses champs ne lui donnent pas. C'est la phrase de la décision B. Son
  lecteur `sim.constants.appel_ville_affamee_part(chemin=None)` relit le
  fichier à chaque appel. Il refuse, par une `ValueError` qui nomme la clé et
  le fichier, un fichier ou une clé absents, un booléen, une chaîne, et un
  nombre hors de [0, 1]. Un entier 0 ou 1 est accepté.
- Avec `P = 0`, le besoin redevient `max(0, ration − stock)` au bit près.
  C'est le commerce d'avant.
- L'appel nourrit les deux passes qui lisent `snapshot_needs`. Les voisines
  terrestres l'envoient sur l'arête. Le bassin le débarque au quai d'une
  ville qui a un port (Gand, Le Caire, Alexandrie), dans la limite du quai :
  c'est la batellerie de la mer. L'écrêtage côté receveur borne toujours ce
  qui arrive au besoin.
- Le surplus ne change pas. Une ville affamée dont le stock dépasse sa
  réserve de `reserve_ville_affamee_jours` jours peut donc, le même jour,
  recevoir par une arête et donner par une autre arête ou par la mer. Les
  deux se lisent sur le snapshot, donc aucun kilo reçu n'est revendu dans le
  même tick. Sur une arête entre deux villes qui appellent, l'ordre `if/elif`
  actuel de la passe 1b décide, comme aujourd'hui.

**Le rayon.** La formule de la capacité d'une arête ne change pas
(`_capacite_transport_arete_kg`, les tests qui l'appellent, les routes, le
relief et les modificateurs). Ce qui change, c'est la capacité du tick posée
par `_apply_commerce`, et seulement à l'appel extérieur, quand
`capacite_restante` vaut `None` (le tick ne la passe jamais). Juste après
`_initialiser_capacite_aretes(world)`, toute arête dont un bout est une
cellule affamée voit sa capacité du tick multipliée par
`R = rayon_ville_affamee_jours`. Le monde doit porter
`populations_soutenables`, et la population lue est celle du début du
maillon. Le plafond reste partagé entre les marchandises du tick, comme
avant. Seules les arêtes des cellules affamées sont parcourues, par l'index
des arêtes, et non toute l'adjacence : le tick reste sous ses 100 ms.

- `R` se lit dans `jeu/data/commerce.toml`. Il vaut **6** : le charroi d'un
  rayon de six jours se rassemble sur la frontière de la ville. Son lecteur
  `sim.constants.rayon_ville_affamee_jours(chemin=None)` relit le fichier à
  chaque appel. Il refuse, par une `ValueError` qui nomme la clé et le
  fichier, un fichier ou une clé absents, un booléen, un nombre non entier,
  et une valeur inférieure à 1.
- Avec `R = 1`, la capacité redevient celle d'avant, au bit près.
- Les mesures jetables du chef disent pourquoi il faut les deux réglages. Le
  rayon seul ne nourrit personne : avec `P = 0` et `R = 6`, Paris finit
  l'année comme avant (153 052 habitants, 956 t), car son grenier ne descend
  jamais sous un jour de ration et il n'appelle donc rien. L'appel seul
  nourrit, mais moins : avec `P = 1` et `R = 1`, Paris finit à 188 377
  habitants. Le codeur remesure ces trois réglages sur le vrai code et les
  recopie dans le rapport (SC3). Si `R = 6` ne tient pas la preuve de SC3 ou
  `test_soudure.py`, il peut régler `R`, et seulement `R`, sur la mesure d'un
  an : la valeur, sa mesure et la date vont dans le commentaire de
  `commerce.toml` et dans `MODELE.md`. `P` reste 1,0 : c'est la décision.
- Aucun kilo n'est créé ni détruit, et `food_deficit_kg` n'est pas touché.

Les deux lecteurs sont appelés une fois par marchandise consommée, et
seulement quand le monde porte `populations_soutenables`. Le moteur les
appelle par le module (`_constantes.appel_ville_affamee_part()`,
`_constantes.rayon_ville_affamee_jours()`), pour qu'un `monkeypatch` porte.

**Le décor d'avant.** `jeu/sim/tests/amorcage_d_avant.py` gagne
`couper_l_appel_des_villes(monkeypatch)`. Elle remplace les deux lecteurs par
des fonctions qui rendent 0 et 1. `garder_le_commerce_d_avant` l'appelle,
comme l'a demandé la direction, et `poser()` remplace aussi les deux
lecteurs. Le décor d'avant ne voit donc ni l'appel ni le rayon, même quand un
monde y garde son relevé des champs. La docstring du module ajoute « et
d'avant l'appel des villes affamées (lot #1071) ».

**La documentation.** La docstring de `_apply_commerce` et `MODELE.md`
donnent les deux formules, les deux constantes, leur niveau, les valeurs
neutres et la table de SC3. Le paragraphe de la réserve (#1057) dit que ses
chiffres (Alexandrie à 32,7 %, la table des sorties) ont été mesurés sans
l'appel. Il donne aussi la pire cellule de `test_soudure.py` mesurée après ce
lot.

## Périmètre
jeu/sim/engine.py
jeu/sim/constants.py
jeu/data/commerce.toml
jeu/sim/MODELE.md
jeu/sim/tests/amorcage_d_avant.py
jeu/sim/tests/test_commerce.py
jeu/sim/tests/test_determinisme.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_ville1400.py
jeu/sim/tests/test_ville_dense.py
jeu/forge/tests/test_forge.py
jeu/vues/relief/tests/test_carte1400.py
jeu/sim/tests/README.md
docs/mesures/2026-11-12-grain-vers-les-villes/RAPPORT.md
docs/mesures/2026-11-12-grain-vers-les-villes/scripts/mesure_un_an.py

`test_determinisme.py`, `test_monde.py`, `test_ville1400.py`,
`test_ville_dense.py`, `test_forge.py` et `test_carte1400.py` : seulement
leur empreinte. Dans ces fichiers, on ne change que la valeur d'une empreinte
épinglée qui bouge (SC6) et le commentaire qui la date. Ceux qui ne bougent
pas restent intacts.

Dans `test_commerce.py`, les tests existants ne changent pas, à une seule
exception, décrite en SC6 : la fixture `_epreuve_1057` reçoit
`couper_l_appel_des_villes` pour sa copie « réserve ». Aucune assertion
n'est retirée, aucune tolérance élargie, aucun cas sauté.

## Conditions de succès
Les commandes se lancent depuis `jeu/`. Tous les cas neufs vont dans
`sim/tests/test_commerce.py`, le fichier qui porte les invariants du commerce.
**Chaque épreuve est un seul test, sans fixture partagée** : un test du monde
de 1400 charge son propre `World.charger(0)`. Des fonctions d'aide communes
sont permises. Les 114 tests existants restent verts sans changement. Ils
construisent des mondes à la main, sans relevé des champs, ou lisent le décor
d'avant. La seule exception est `_epreuve_1057` (SC6). **Si un autre test
existant rougit, hors d'une empreinte de la liste de SC6, on s'arrête** : la
question remonte au propriétaire, et on n'assouplit pas le test. Cela vaut
aussi pour `test_soudure.py`, qui doit rester vert tel quel.

**SC1 — La règle sur un petit monde.**
`python3 -m pytest sim/tests/test_commerce.py -q -k "appel_ville_affamee and not donnee and not conservation"`.
Le petit monde a deux ou trois cellules posées à la main, voisines par terre.
`world.populations_soutenables` y est posé à la main, et les lecteurs sont
remplacés par `monkeypatch`. Un test par cas :
- (a) Une receveuse affamée (population 100, soutenable 40) a 30 jours de
  ration en stock. La source se nourrit et a un grand surplus. Avec `P = 1`
  et `R = 1`, la receveuse reçoit exactement `60 × consommation_unitaire`
  quand l'arête le permet. Avec `P = 0`, elle reçoit 0 kg.
- (b) La même scène avec une arête de capacité inférieure à l'appel. Avec
  `R = 1`, la receveuse reçoit la capacité. Avec `R = 6`, elle reçoit
  `min(appel, 6 × capacité)`.
- (c) Une receveuse qui se nourrit (soutenable 100 ≥ population 100) reçoit,
  avec `P = 1` et `R = 6`, exactement ce qu'elle reçoit avec `P = 0` et
  `R = 1`, au bit près, ainsi que sa source.
- (d) Une receveuse affamée a deux sources dont la somme des surplus dépasse
  l'appel. Elle reçoit l'appel et pas plus (écrêtage), et les sources gardent
  le reste.
- (e) Une receveuse affamée sur la côte, avec un bassin : le débarquement
  porte l'appel, dans la limite du quai.

Contre-épreuves :
- avec `P = 0` et `R = 1`, chacune des scènes donne, au bit près, les stocks
  du même monde sans `populations_soutenables` ;
- `populations_soutenables = None` avec `P = 1` et `R = 6` donne aussi la
  règle d'avant ;
- un relevé qui ne porte pas la receveuse lève une erreur qui nomme son
  `cell_id` ;
- sous `garder_le_commerce_d_avant(monkeypatch)`, les deux lecteurs rendent
  0 et 1.

**SC2 — Les données.**
`python3 -m pytest sim/tests/test_commerce.py -q -k "appel_ville_affamee_donnee or rayon_ville_affamee_donnee"`.
Sur `jeu/data/commerce.toml`, les lecteurs rendent 1,0 et la valeur de `R`
(6, ou celle que SC3 a réglée), et le fichier dit le niveau 2 en commentaire
pour chaque clé. Contre-épreuves, sur des fichiers écrits dans `tmp_path` :
- pour `P` : `-0.1`, `1.5`, `"1"`, `true`, une clé absente et un fichier
  absent lèvent chacun une `ValueError` qui nomme `appel_ville_affamee_part` ;
- pour `R` : `0`, `-3`, `2.5`, `"6"`, `true`, une clé absente et un fichier
  absent lèvent chacun une `ValueError` qui nomme `rayon_ville_affamee_jours`.

Une valeur réécrite dans le fichier est relue au prochain appel.

**SC3 — La preuve d'un an, un seul test.**
`python3 -m pytest sim/tests/test_commerce.py -q -s -k grain_monte_vers_les_villes_un_an`.
Le test charge `World.charger(0)` lui-même et en joue deux copies
(`copy.deepcopy`), graine 0, IA active, sans joueur, pendant 365 jours : à
chaque jour, `jouer_ia` puis `engine.tick`, comme l'épreuve de la soudure.
- « Le commerce de ce lot » : les données du dépôt.
- « Le commerce d'avant » : la même chose sous `couper_l_appel_des_villes`,
  dans un `monkeypatch.context()` qui couvre tout le jeu, pas seulement le
  chargement. La réserve des villes affamées reste celle du dépôt : on
  compare au monde de master, pas au monde d'avant #1057.

Chaque copie compte, par ville, les morts de `engine._apply_mortality`, en
l'enveloppant comme `test_soudure.py`, et les pertes nettes du pas des
départs. Ces pertes sont, jour par jour, `max(0, avant − après)`, sur
`sim.departs.appliquer_departs` enveloppé. Les villes se trouvent par leur
nom, dans `monde.attribution_villes.placees` : « Paris », « Milan », « Gand »,
« Alexandrie », « Le Caire ».

Le test affirme d'abord que la preuve est bien posée :
- les données du dépôt ne sont pas neutres (`P > 0` et `R > 1`) ;
- les cinq villes sont affamées au départ, ce qu'il dérive de
  `populations_soutenables` sans le recopier.

La preuve tient dans une fonction `_villes_moins_nourries(candidat, reference)`
qui rend la liste des fautes. Au 365e jour :
- Paris, Milan, Gand et Alexandrie ont strictement plus d'habitants et
  strictement plus de nourriture en stock (`lire_stock_marchandise`) dans le
  candidat que dans la référence ;
- Le Caire a strictement plus de nourriture en stock.

Le test affirme `_villes_moins_nourries(ce_lot, avant) == []`.

**Pourquoi Le Caire n'est pas jugé sur ses habitants : le test le dérive.**
Sous les deux règles, Le Caire n'a aucun mort par `_apply_mortality` et
aucune perte nette au pas des départs. Ses habitants ne bougent donc que par
les naissances et par les réfugiés de ses voisines : les juger mesurerait la
faim d'Alexandrie, pas la sienne. Le test affirme ces deux zéros et le dit
dans sa docstring. Si l'un d'eux tombe, le lot s'arrête : la décision B
reposait sur ce fait, et la question remonte au propriétaire.

**Contre-épreuve 1 : le commerce d'avant fait échouer la preuve.**
`_villes_moins_nourries(avant, avant)` nomme les cinq villes. Le test
affirme aussi que, dans la copie d'avant, Paris ne reçoit rien de toute
l'année, comme l'a mesuré le chef : l'appel est bien ce qui nourrit Paris.

Le test imprime, ville par ville, les habitants, le stock au 365e jour, les
morts et les pertes au départ, sous les deux règles. Le script
`docs/mesures/2026-11-12-grain-vers-les-villes/scripts/mesure_un_an.py`
rejoue la même année sous quatre réglages : `P = 0, R = 1` (avant),
`P = 0, R = 6` (le rayon seul), `P = 1, R = 1` (l'appel seul) et les
données du dépôt. Il donne la même table, plus la pire cellule de
`test_soudure.py` (part des habitants morts de faim). Le codeur recopie la
sortie dans `RAPPORT.md`, avec la commande, et la table du dépôt dans
`MODELE.md`.

**SC4 — La conservation, un seul test.**
`python3 -m pytest sim/tests/test_commerce.py -q -k conservation_appel_ville_affamee`.
Le test charge son propre monde et joue 30 jours sous les données du dépôt,
IA active. Il enveloppe l'appel extérieur de `engine._apply_commerce`, avec
une garde de profondeur comme `_Suivi1057`. À chaque appel :
- la masse de nourriture des cellules plus le bassin (`math.fsum`) est la
  même avant et après, à `1e-9 × masse` près ;
- pour chaque cellule affamée, la somme des paniers de ses lieux est égale à
  son stock après le commerce, à `1e-9` près en relatif ;
- aucune cellule affamée ne descend sous `min(stock avant, garde)`, où la
  garde est sa réserve de `reserve_ville_affamee_jours` jours. C'est
  l'invariant de #1057, cette fois dans le monde avec l'appel.

Contre l'échantillon vide, Paris reçoit plus de 0 kg sur ces 30 jours (la
somme des hausses de son stock pendant le commerce). Sinon le test échoue.

**Contre-épreuve 2 : une ville qui reçoit du grain sans qu'une cellule en
perde fait échouer la conservation.** Dans le même test, sur un nouveau
`World.charger(0)` et un seul jour, l'enveloppe ajoute 1 t au panier du
bourg de Paris et à son stock après le commerce. La vérification lève, dans
un `pytest.raises(AssertionError, match="masse non conservée")`.

**SC5 — Les valeurs neutres redonnent master, octet pour octet.** On prouve
le rouge d'abord, dans cet ordre, avant de toucher une empreinte :
1. Une fois le moteur codé, mettre `appel_ville_affamee_part = 0` et
   `rayon_ville_affamee_jours = 1` dans `commerce.toml`. Lancer dans leur
   version de master les tests à empreinte de SC6,
   `test_modificateurs.py::test_sans_modificateur_la_photographie_a_365_jours_est_celle_d_avant`,
   et `python3 -m pytest sim/tests/test_commerce.py -q -k "ville_affamee and not appel"`
   (les épreuves de #1057, fixture comprise, sans modification). Tous sont
   verts.
2. Remettre les vraies valeurs et relancer : la liste des tests rouges est
   celle des empreintes qui bougent, plus
   `test_premier_mois_ville_affamee_janvier_inchange_puis_exportent_moins`.
   Celui-ci rougit parce que l'appel change janvier.

Le pas 2 est la contre-épreuve du pas 1 : une règle qui ne ferait rien ne
rougirait aucune empreinte. Une fois `_epreuve_1057` isolée (SC6),
`test_premier_mois_ville_affamee_janvier_inchange_puis_exportent_moins`
redevient vert. Retirer `couper_l_appel_des_villes` de la fixture, à la main
et sans le committer, le fait rougir de nouveau. Le codeur note les deux
listes et les commandes dans `RAPPORT.md`.

**SC6 — Les empreintes recapturées, et l'épreuve de #1057 isolée.**
Les candidats sont :
- dans `test_determinisme.py`, `_PART_BASE`, `_PRELEVEMENT_BASE` et
  `_DU_BASE` (`-k bit_pres`) ;
- dans `test_monde.py`, les empreintes de `test_service_ia_sans` et des
  réponses figées aux ticks 3 et 4 ;
- les empreintes de `test_ville1400.py`, de `test_ville_dense.py`
  (`_EMPREINTES_BASE`), de `forge/tests/test_forge.py` et de
  `vues/relief/tests/test_carte1400.py`.

L'appel joue dès le premier jour : sur le monde de la soudure, les cellules
qui doivent différer sont les villes affamées et leurs voisines terrestres,
puis les ports par le bassin. Le codeur l'affirme sur la plus courte des
empreintes rouges. Après un tick, il compare cellule par cellule les stocks
de nourriture des deux réglages. Toute cellule qui diffère est une ville
affamée, une voisine terrestre d'une ville affamée, ou une cellule côtière
(le bassin). Au moins une ville affamée diffère. Il le note dans
`RAPPORT.md`. Les empreintes que SC5 trouve rouges sont recapturées sous
Linux, sans rien d'autre qui change, et le commentaire de chacune date la
mesure (« recapturée le …, lot #1071, appel des villes affamées »). Un
candidat que SC5 trouve vert ne change pas. `test_modificateurs.py` ne
change pas : sous `garder_le_commerce_d_avant`, il doit rester vert avec ses
deux valeurs, `win32` comprise.

`_epreuve_1057` éprouve la réserve seule, contre `N = 1`. Ses assertions
(janvier inchangé, Paris à 0 kg de sortie, sorties en baisse) parlent de la
réserve, pas de l'appel. La copie « réserve » de la fixture se joue donc dans
un `monkeypatch.context()` qui appelle `couper_l_appel_des_villes`, avec un
commentaire du lot. C'est le patron de #1029 et de #1057 pour
`test_modificateurs.py`. Ses assertions, ses chiffres et ses deux tests
restent identiques. Ils retrouvent leurs octets de master, comme SC5 1 le
montre. L'invariant de la réserve dans le monde réel est repris par SC4. La
copie d'avant y est déjà neutre, par `garder_le_commerce_d_avant`.
`test_conservation_ville_affamee_contre_epreuve_un_kilo_ajoute_est_vu` ne
change pas, et reste vert avec l'appel. `sim/tests/README.md` met à jour sa
table des empreintes et la ligne de `test_modificateurs.py`.

La preuve finale : `python3 -m pytest jeu -q` est vert en entier. Cela
comprend `sim/tests/test_soudure.py` tel quel et les budgets du tick,
inchangés (`test_monde.py::test_tick_sous_le_budget_du_service`,
`test_flux.py::test_budget_flux_et_contre_epreuve`). Si un test qui lit un
fichier figé du pont (`3d/unity/…/Pont/Tests/*.json`) rougit, le lot
s'arrête : ces fichiers sont hors du périmètre, et la question remonte au
propriétaire.

**SC7 — La documentation dit la règle.**
`grep -n "appel_ville_affamee_part" sim/MODELE.md data/commerce.toml sim/engine.py sim/constants.py`
et
`grep -n "rayon_ville_affamee_jours" sim/MODELE.md data/commerce.toml sim/engine.py sim/constants.py`
trouvent chacun les quatre fichiers. Contre-épreuve : sur master, les deux
commandes ne trouvent rien.

## Hors périmètre
- La tenue à dix ans et la table du jalon 2 contre le commerce d'avant :
  c'est la preuve de #1026, qui lira cette règle.
- Des naissances qui suivent le grain, ou toute autre règle qui ferait
  gagner des habitants au Caire (réponse C, écartée).
- Un fleuve dans les arêtes : la batellerie de ce lot est le rayon des
  arêtes et les débarquements du bassin. Le cours du Nil (`sim/fleuve.py`)
  n'entre pas dans le commerce.
- Un appel ou un rayon différents selon la ville, la saison ou la maison. Un
  modificateur sur l'appel : la grandeur n'entre pas au registre.
- Une ville affamée qui cesse de vendre quand elle appelle : la garde et le
  surplus de #1057 ne bougent pas.
- La formule de la capacité d'une arête (`_capacite_transport_arete_kg`), les
  routes, les convois et les départs.
- Les greniers des maisons, le secours et la part.
- La vue : ni Unity, ni l'infobulle, ni la photographie ne lisent l'appel
  (#429).
- Les fichiers figés du pont sous `3d/`, `test_soudure.py`,
  `test_modificateurs.py`, et tout chemin hors du Périmètre.
- Les prix et un marché : il n'y en a pas (jalon 8).
