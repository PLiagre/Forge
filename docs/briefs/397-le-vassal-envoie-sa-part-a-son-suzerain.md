# Lot #397 — Le vassal envoie sa part à son suzerain
Jalon : J3 · Machine : vps · Taille prévue : 280 lignes

## But
Chaque maison qui a un suzerain sur la carte lui envoie, en convoi, `PART_DUE_AU_SUZERAIN = 0,10` de ce qui entre dans son grenier par le prélèvement. Ce dû arrive des jours plus tard, entamé par la route, dans le grenier du suzerain. Un suzerain dont le siège est hors carte ne reçoit rien, et la raison est déclarée.

## Le joueur
Le joueur voit partir vers son suzerain une part de ce qui entre dans son grenier : c'est le prix de sa place dans la pyramide. Il la voit arriver, des jours plus tard, dans le grenier du suzerain. Pour Bar, c'est un dixième de chaque arrivage qui part vers les Valois, à Paris, et y arrive 9 jours plus tard.

Dans la décision du jalon J3 (« prendre plus aujourd'hui ou garder ses gens »), ce dû pèse aussi : le grenier ne garde que neuf dixièmes de ce que le joueur prend.

En J3, cette part est la coutume : le joueur ne la choisit pas. Après ce lot, le dû existe dans le monde, et `to_dict()` le montre en route vers le grenier du suzerain. Ensuite :
- #400 le fera dire au service et à la photographie ;
- #401 dessinera la flèche vers le suzerain sur la carte de la forge ;
- #403 et #405 la montreront dans Unity.

## Règle du monde
Section **« ## Le prélèvement »** de `jeu/sim/MODELE.md`. Un paragraphe neuf, **« Le dû au suzerain »**, s'ajoute après celui de `World.convois`. **Niveau 2** : la part de 0,10 est plausible, jamais sourcée. **Niveau 3**, pas simulé : l'hommage en hommes, en argent ou en service.

**La table des dus, au chargement.** `World.charger` calcule une table une seule fois, juste après `routes_des_lieux`, avec les mêmes `places` (sans les recalculer). Elle est gardée sur le monde sous `World.dus_des_vassaux` et reste hors de `to_dict`. Elle contient :
- **`routes`** : pour chaque maison dont le suzerain a un siège sur la carte, son identifiant → (identifiant du suzerain, `jours`). Les jours suivent exactement la règle de `routes_des_lieux` :
  - dans la même cellule, la distance des places entre le rang du vassal et celui du suzerain ;
  - sinon, le plus court chemin terrestre depuis la cellule du suzerain ;
  - sans chemin, `JOURS_DE_MER` ;
  - au moins 1 jour.
  L'exécutant factorise ce calcul avec `routes_des_lieux` plutôt que de le recopier.
- **`retenus`** : pour chaque vassal dont le suzerain a un siège hors carte (`cell_id` à `None`), son identifiant → le texte `hors_carte` du suzerain. C'est la raison déclarée. Le dû de ces vassaux reste dans leur grenier.
- **`par_indice`** : une liste dense alignée sur `routes_des_lieux.noms`. Elle contient `(indice du suzerain, jours)` ou `None`. Un suzerain sur carte absent de `noms` lève `RouteInvalide`, qui nomme le vassal. Le monde de ce brief n'en a aucun : il n'y a pas de repli.

Un `World(...)` d'épreuve porte une table vide.

**L'étape Prélèvement.** L'ordre reste celui de #573 : pertes en route, arrivées, départs. À l'arrivée d'une charge `kg × facteur` pour la maison d'indice `i` :
- si `par_indice[i]` vaut `(s, jours)` et que la part n'est pas nulle :
  - le dû vaut `entrée × PART_DUE_AU_SUZERAIN` ;
  - le grenier reçoit l'entrée moins ce dû ;
  - le dû part le même tick dans le groupe d'arrivée `tick + jours`, charge de l'indice `s`. Il s'inscrit comme un départ de récolte : division par le facteur du groupe, ajout au `total` du groupe.
- sinon, le grenier reçoit tout.

Le dû subit donc exactement `jours` pertes de `PERTE_CONVOI_PAR_JOUR`, et ses pertes s'ajoutent à `mange_convois_kg`.

Ce qu'un suzerain reçoit par convoi entre à son grenier comme son propre prélèvement. Un suzerain lui-même vassal en doit donc à son tour sa part.

Ce qui ne paie pas de dû :
- les secours de #398 : ils ne passent pas par cette arrivée ;
- les achats (jalon 8) ;
- un grenier rempli à la main.

`sim/prelevement.py` ne lit que `par_indice` et la constante. Il ne lit ni `maitre`, ni `maisons`, ni `suzerain`.

**Ce que le dû change, et ce qu'il ne change pas.** Le dû ne touche ni les lieux ni les cellules : il passe d'un grenier à un autre. La calibration de #574 tient donc telle quelle. Le chef l'a vérifié : à 30 ticks, le pickle des cellules est égal avec et sans dû. Dans `to_dict()`, une charge de dû apparaît dans `convois` sous le nom du suzerain qui la recevra.

**Mesures du chef** (prototype, master af53e53, graines 0 et 42, valeurs identiques) :

| mesure | valeur |
|---|---|
| vassaux routés | 2 118, vers 33 suzerains |
| vassaux retenus | 39 : 29 sous la Horde d'Or (`grande-21`), 10 sous Venise (`institution-13`) |
| suzerains eux-mêmes vassaux | aucun : la pyramide a deux étages, la cascade se prouve sur un monde fabriqué |
| jours | de 4 à 144 |
| table des dus | 0,07 s au chargement |

Bar (`seigneurie-1`) est vassal des Valois (`grande-3`), à 9 jours. Ses lieux sont à 1, 1, 2 et 2 jours. Avec une part de 0,5 au seul tick 0, et sans perte des greniers :
- au tick 2, le grenier de Bar porte 20 570,41 kg, soit 0,9 × Σ kg·0,99^j ;
- les Valois reçoivent 1 050,22 kg au tick 10 et 2 087,94 kg au tick 11, soit 0,1 × Σ kg·0,99^(j+9) ;
- les deux égalités sont exactes à l'ulp.

**Constante.** Dans `jeu/sim/constants.py`, `PART_DUE_AU_SUZERAIN = 0.10` s'ajoute près de `PART_COUTUMIERE`, avec une ligne de commentaire « Niveau 2, plausible : … ».

**Autre retouche de `MODELE.md`.** Dans « ## Les intentions du joueur », la liste « Niveau 3, pas simulé ici » cesse de citer « son dû au suzerain ».

## Périmètre
jeu/sim/constants.py
jeu/sim/convois.py
jeu/sim/world.py
jeu/sim/prelevement.py
jeu/sim/MODELE.md
jeu/sim/tests/test_prelevement.py
jeu/sim/tests/test_convois.py
jeu/sim/tests/test_determinisme.py
jeu/sim/tests/README.md

## Conditions de succès
Toutes les commandes partent de `jeu/` et visent un fichier, avec `-k`. **Ne jamais lancer la suite entière, ni `test_determinisme.py` en entier** (18 min). Chaque nombre comparé est dérivé des données et affiché (`print`), jamais écrit en dur, sauf les empreintes figées de SC6.

Décision **A** du pilote, sur la question technique de ce lot : deux tests existants posent `PART_DUE_AU_SUZERAIN = 0` et gardent toutes leurs vérifications (SC1) ; des tests neufs prouvent le monde avec dû.

- **SC1 — Le monde d'avant reste prouvé.**
  - `test_charge_et_jours_de_bar` (#573) ajoute une seule ligne en tête : `monkeypatch.setattr(c, 'PART_DUE_AU_SUZERAIN', 0)`.
  - `test_prelevement_bit_pres` (#574) reçoit le paramètre `monkeypatch` et la même ligne en tête.
  - Aucune assertion, empreinte de `_PRELEVEMENT_BASE` ou contre-épreuve de ces deux tests ne change. Le relecteur le vérifie avec `git diff` : les lignes retirées de ces deux fichiers ne sont que les deux signatures modifiées.
  - Commandes : `python3 -m pytest sim/tests/test_prelevement.py -q -k charge_et_jours_de_bar` et `python3 -m pytest sim/tests/test_determinisme.py -q -k "prelevement_bit_pres or part_bit_pres"`.
  - Contre-épreuve : sans la ligne ajoutée, ces deux tests rougissent. Le chef l'a vérifié sur le prototype : Bar reçoit 0,9 de l'attendu, et les points (0|42, 3) et (0|42, 20) changent.

- **SC2 — La table des dus.** Un test neuf de `test_convois.py`, sur `World.charger(0)`, vérifie que :
  - `routes` et `retenus` sont disjoints, non vides, et leur union est exactement l'ensemble des maisons dont `suzerain` n'est pas `None` ;
  - chaque retenu porte le `hors_carte` de son suzerain, et ce texte n'est pas vide ;
  - tout suzerain routé a un `cell_id` ;
  - tous les jours sont ≥ 1 ;
  - Bar va aux Valois, et ses jours égalent ceux que donne la règle de `routes_des_lieux` depuis le siège des Valois jusqu'au siège de Bar ;
  - `par_indice` a la longueur de `noms` et renvoie, pour chaque vassal routé, l'indice de son suzerain ;
  - un `World(...)` d'épreuve porte une table vide.

  Le test affiche les comptes et le temps de construction. Commande : `python3 -m pytest sim/tests/test_convois.py -q -k dus`.

  Contre-épreuves :
  - une table construite avec des `noms` privés d'un suzerain lève `RouteInvalide`, et le message nomme le vassal ;
  - une maison fabriquée dont le suzerain est inconnu lève une erreur.

- **SC3 — Bar paie les Valois.** Un test neuf de `test_prelevement.py`. Il pose :
  - `PERTE_GRENIER_PAR_AN = 0` ;
  - toutes les parts à 0, sauf Bar, à 0,5 au seul tick 0 ;
  - un relevé de la récolte prise à chaque lieu, comme dans `test_charge_et_jours_de_bar`.

  Il joue ensuite jusqu'à `max(jours des lieux) + jours du dû`. À chaque tick `t`, il vérifie, à `rel=1e-12` :
  - grenier de Bar = 0,9 × Σ kg·(1−p)^j sur les lieux tels que j ≤ t ;
  - grenier des Valois = 0,1 × Σ kg·(1−p)^(j+J) sur les lieux tels que j + J ≤ t, où J est le jour du dû.

  Les Valois sont à zéro tant que t < min(j) + J. À la fin, aucune charge n'est en route vers Bar ni vers les Valois. Les valeurs sont affichées.

  Contre-épreuves :
  - avec `PERTE_CONVOI_PAR_JOUR = 0`, les Valois reçoivent exactement 0,1 du prélevé, et avec perte ils reçoivent strictement moins : le transport coûte ;
  - avec `PART_DUE_AU_SUZERAIN = 0`, les Valois restent à zéro.

  Commande : `python3 -m pytest sim/tests/test_prelevement.py -q -k bar_paie -s`.

- **SC4 — Conservation sur deux étages, et pyramide vidée.** Un test neuf de `test_prelevement.py`, sur `copy.deepcopy` du monde chargé, joue 30 ticks avec un observateur enveloppant `prelevement.prelever`. Les suzerains routés ont une part nulle, pour que tout ce qui entre à leur grenier soit du dû. À chaque appel, l'observateur vérifie :
  - que le total `_total` est conservé à `rel=1e-12` ;
  - pour chaque vassal routé, ce qui entre à son grenier : il en déduit le dû parti (entrée ÷ 0,9 × 0,1) et l'inscrit à `t + J`.

  À la fin, la somme des greniers des suzerains égale Σ dû·(1−p)^J des dus arrivés (`rel=1e-9`), et elle est strictement positive.

  Second volet :
  - une épreuve où la pyramide est vidée (table des dus vide, posée sur la copie) donne, après 30 ticks, des greniers égaux à l'octet à ceux d'un monde joué avec `PART_DUE_AU_SUZERAIN = 0` ;
  - le grenier de Bar y est strictement plus grand que dans le monde avec dû ;
  - le pickle des cellules est identique dans les trois mondes : le dû ne touche aucun lieu.

  Contre-épreuve : un faux prélèvement qui, après l'original, rend à chaque vassal le dû qu'il vient d'envoyer (le dû arrive chez le suzerain sans quitter le grenier du vassal) fait lever l'assertion de conservation (`pytest.raises(AssertionError)`).

  Commande : `python3 -m pytest sim/tests/test_prelevement.py -q -k deux_etages -s`.

- **SC5 — Le suzerain vassal paie à son tour.** Un test neuf de `test_prelevement.py`, sur un `World(...)` fabriqué :
  - une cellule ; trois maisons a → b → c, avec une `TableRoutes` qui donne au moins un lieu à chacune ;
  - la table des dus posée à la main : a → b en 2 jours, b → c en 3 jours ;
  - part de a à 0,5, parts de b et c à 0 ;
  - un seul tick de prélèvement.

  Il vérifie, à `rel=1e-12` :
  - grenier de b = 0,9 × 0,1 × E·(1−p)² ;
  - grenier de c = 0,1 × 0,1 × E·(1−p)^5 ;
  - où E est l'entrée de a, et a garde 0,9 × E.

  Contre-épreuve : si c est retenu (b sans entrée dans `par_indice`), c reste vide et b garde tout son arrivage. Commande : `python3 -m pytest sim/tests/test_prelevement.py -q -k a_son_tour`.

- **SC6 — Le monde avec dû est figé.** Un test neuf de `test_determinisme.py`, `test_du_au_suzerain_bit_pres`, reprend `_empreintes_prelevement` sans monkeypatch : graines 0 et 42, points 1, 3 et 20. Les quatre couples des points 3 et 20 sont figés dans une table `_DU_BASE`, calculés une fois par l'exécutant. Il vérifie aussi :
  - au point 1, les empreintes sont égales à celles de `_PRELEVEMENT_BASE` : aucun convoi n'est encore arrivé ;
  - aux points 3 et 20, les deux empreintes diffèrent de `_PRELEVEMENT_BASE`.

  Contre-épreuves :
  - la vérification sur `{}` lève ;
  - elle lève aussi sur la table privée de (42, 20) ;
  - `math.nextafter` sur la nourriture du grenier des Valois fait lever la vérification recalculée de (42, 20).

  Commande : `python3 -m pytest sim/tests/test_determinisme.py -q -k du_au_suzerain_bit_pres`.

- **SC7 — Le modèle, et le tick sans registre.**
  - Un test neuf de `test_prelevement.py` trouve, dans `_section_prelevement`, « Le dû au suzerain », la valeur de `c.PART_DUE_AU_SUZERAIN` écrite avec une virgule (« 0,10 », dérivée de la constante), « hors carte », « à son tour », « niveau 2 » et « niveau 3 ».
  - Le même test vérifie que la section « ## Les intentions du joueur » ne contient plus « son dû au suzerain ».
  - Il vérifie enfin que `_lectures` sur `prelevement.py` ne trouve ni `suzerain`, ni `maitre`, ni `maisons`.
  - Contre-épreuve : la même lecture sur la section où « 0,10 » devient « 0,20 » lève.
  - `jeu/sim/tests/README.md` mentionne le dû, à la ligne de `test_prelevement.py` et à celle de `test_convois.py`.
  - Commande : `python3 -m pytest sim/tests/test_prelevement.py -q -k "modele or tick_sans_maitre"`.

- **SC8 — Rien d'autre ne bouge.** Ces commandes passent :
  - `python3 -m pytest sim/tests/test_prelevement.py -q -k "not calibration"` ;
  - `python3 -m pytest sim/tests/test_prelevement.py -q -k calibration` : le dû ne touche pas les cellules, donc 0,03 tient toujours ;
  - `python3 -m pytest sim/tests/test_convois.py sim/tests/test_write_coverage.py sim/tests/test_no_hardcoded.py -q` ;
  - `python3 -m pytest sim/tests/test_maisons.py -q -k "tick or grenier"`.

  `git diff -- sim/constants.py` n'ajoute que `PART_DUE_AU_SUZERAIN` et son commentaire. La PR affiche :
  - le temps de l'étape mesuré par `test_conservation_sur_un_an` ;
  - le temps de chargement de la table des dus.

## Hors périmètre
- Le joueur qui règle la part due de ses vassaux (J9, les lois) ; une part due différente par maison ; l'IA (jalon 5).
- Les secours de #398 et les achats (jalon 8) : ils ne paient pas de dû. Ce lot ne touche pas `World.secours`.
- Ce que fait un suzerain hors carte (Horde d'Or, Venise). Le dû y est retenu chez le vassal, et rien n'est inventé pour le joindre.
- Changer les maîtres, les suzerains ou la pyramide (registre de #390), les routes des lieux (#572), ou une autre constante. Remesurer la calibration : les cellules ne bougent pas.
- Tout affichage : service, `/lieu`, photographie, carte de la forge, Unity (#400, #401, #403, #405). La table des dus reste hors de `to_dict`.
- Modifier une assertion, une empreinte ou une contre-épreuve d'un test existant. La seule exception est la ligne `PART_DUE_AU_SUZERAIN = 0` de SC1, décidée en A.
