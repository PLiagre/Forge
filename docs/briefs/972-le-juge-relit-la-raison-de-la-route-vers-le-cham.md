# Lot #972 — Le juge relit la raison de la route vers le champ
Jalon : J5 · Machine : vps · Taille prévue : 170 lignes

## But
`test_monde` sait relire, sur le monde seul et sans `sim/ia.py` ni `sim/programme_ia.py`, la raison `route_vers_le_champ` d'une route de l'IA : grenier, réserve voulue, journées, coût, jours de faim du bourg, vivres des champs, champ visé et écart. Une raison qui ment sur un seul de ces nombres est prise en faute.

## Le joueur
C'est un lot de fond. Il prépare le geste du jalon J5 « regarder le monde vivre, puis s'en méfier ou s'en servir » : sur la carte, les maisons voisines tracent leurs routes « pour des raisons qu'elles disent ». Le joueur lira dans la raison d'une route voisine le grenier, la réserve, le coût, les jours de faim du bourg et les vivres des champs. Ce lot garantit que ces nombres sont ceux du monde au jour du geste, relus par un juge qui ne partage aucun code avec l'IA. Sans lui, une raison pourrait dire « grenier plein » ou « bourg affamé » sans que ce soit vrai, et le joueur se méfierait d'un voisin sur un mensonge. Ce lot ne branche rien. Le sous-lot 4 de #951 met le calcul de #971 dans `decider_intentions` et branche ce juge sur la partie jouée. Puis #428 sert ces raisons, et #322 et #429 les montrent sur la carte.

## Règle du monde
Sans objet : c'est un lot d'outil. Il ne change ni le monde ni `jeu/sim/MODELE.md`. Le juge relit la règle que #971 a posée, et qui découle de trois sections de MODELE.md : **« Les décisions et les gestes de l'IA »** pour la réserve voulue et la forme d'une raison, **« Les flux sur trente jours »** pour la faim du mois passé, et **« La distribution à l'intérieur de la cellule »**, paragraphe « La route vers un lieu », pour la route qui vise un champ. MODELE.md recevra cette règle au sous-lot 4 de #951.

**Le juge.** `_lire_route_vers_le_champ(monde, maison, intention)` va dans `jeu/sim/tests/test_monde.py`, près de `_lire_raison_monde`. Il rend la raison telle que le monde la dit au tick courant, avec les neuf clés figées par #971, sans arrondi :
- `regle` : `'route_vers_le_champ'` ;
- `grenier_nourriture_kg` : `monde.greniers[cle].get(nourriture, 0)`. La clé vient de `_cle_de_maison`, qui existe déjà dans `test_monde` ;
- `reserve_voulue_kg` : elle est recalculée ici, à partir de l'index `monde.routes_des_lieux` lu comme le fait `_lecture_secours`. On somme les habitants des lieux de la maison, dans l'ordre de la table. On ajoute les journées encore dues des ouvrages en chantier de ses bourgs, multipliées par `SALAIRE_JOURNEE_KG`. La formule s'écrit `consommation × (RESERVE_VOULUE_JOURS / TICK_DURATION_DAYS) × habitants × RESERVE_VOULUE_PART_DES_HABITANTS + salaires`, dans cet ordre d'opérations, pour que l'égalité soit exacte. Une aide `_reserve_lue(monde, cle)` la porte ;
- `journees` : `travail_requis_de_route(intention['points'], intention['largeur_m'])`. Les points sont lus sur le geste déposé ;
- `cout_kg` : `journees × SALAIRE_JOURNEE_KG` ;
- `faim_du_bourg_ticks` : le nombre de ticks de `t − FENETRE_FLUX_TICKS` à `t − 1` dont `monde.flux.jours[tick].affames` contient `(cell_id, 0)` ;
- `champs_nourriture_kg` : `contenus_des_paniers` des lieux de rang ≥ 1, rangés par rang ;
- `champ_vise` : le rang du champ le plus plein, le plus petit rang à égalité. Il est lu sur les vivres, jamais sur la route ;
- `ecart_degres` : l'angle signé entre `p1 − p0` et la direction φ du bourg vers le champ visé. φ est lue sur `routes_interieures._places_de`. L'angle est ramené dans ]−180°, 180°] (`math.remainder`) et arrondi à l'entier.

Le juge n'importe ni `sim.ia` ni `sim.programme_ia`, ni à l'appel ni en tête de fichier. Il ne lit que le monde, le registre et les modules du moteur : `sim.model`, `sim.chantiers`, `sim.routes_interieures`, `sim.seigneuries` et `sim.constants`. Il n'écrit rien.

**Le contrôle.** `_controler_routes_vers_le_champ(lectures, propositions)` exige trois choses : au moins une proposition, une raison dans chacune, et `proposition['raison'] == lectures[(sorte, id)]`, à égalité exacte, comme `_controler_raisons`.

**Mesure du chef** (graine 0, base 31011599, prototype `/tmp/proto972`). Le montage est le `_monter()` de `test_programme_ia.py`. **16** propositions sortent, et le juge les égale toutes, à l'octet, avec des écarts de −10 à +15. Pour la première maison qui reçoit une route, une variante donne 8 jours de faim (un jour sur quatre) et ajoute une rue en chantier de 10 journées : la proposition sort encore, le juge l'égale, et la réserve monte de 30 kg. Le montage prend 4 s. Ces nombres sont à re-mesurer, et ils ne sont recopiés dans aucun test.

## Périmètre
jeu/sim/tests/test_monde.py
jeu/sim/tests/README.md

## Conditions de succès
Toutes se lancent par `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k route_vers_le_champ`, sauf SC5. Le lot ajoute un seul test, `test_ia_route_vers_le_champ_relue`, ou deux s'il sépare l'indépendance, et les deux aides décrites plus haut. Aucun test existant ne change. Le montage importe `_monter` et `_affamer` de `sim.tests.test_programme_ia`, comme `test_monde` importe déjà des aides de `test_intentions`. Le test appelle `programme_ia.proposer_route_vers_le_champ` pour chaque maison montée et compare chaque proposition au juge. **M** est la première maison qui reçoit une proposition. Les comptes sont dérivés et affichés par `print`, jamais recopiés de la mesure.

- **SC1 — Le juge égale le programme sur le monde préparé.** Pour chaque proposition du montage, la lecture du juge égale la raison, et le nombre de propositions comparées est affiché. Contre-épreuves : `_controler_routes_vers_le_champ(lectures, [])` échoue (échantillon vide), comme une proposition dont la clé `raison` est retirée.
- **SC2 — Une raison faussée champ par champ échoue.** Le test prend une copie de la proposition de M et fausse un seul champ à la fois. `_controler_routes_vers_le_champ` lève alors `AssertionError` dans chacun des cas suivants :
  - `grenier_nourriture_kg + 1` ;
  - `reserve_voulue_kg + 1` ;
  - `cout_kg + 1` ;
  - `faim_du_bourg_ticks − 1` ;
  - le premier élément de `champs_nourriture_kg` + 1 ;
  - `champs_nourriture_kg` remplacé par sa somme ;
  - `journees + 1` ;
  - `champ_vise` remplacé par un autre rang de la cellule ;
  - `ecart_degres + IA_PAS_ECART_ROUTE_DEGRES` ;
  - `regle` remplacée par `'route_si_bourg_affame'` ;
  - une clé retirée.

  Le test affirme aussi que chaque raison faussée diffère de l'originale, pour qu'aucun cas ne passe par hasard.
- **SC3 — Le juge suit le monde, pas un montage figé.** Sur des copies du montage, M reçoit encore une proposition dans chacune des variantes suivantes, et le juge l'égale :
  - (a) une faim du bourg réduite à un jour sur quatre, par `_affamer`. Le test affirme `faim_du_bourg_ticks` différent de 30 et différent de `duree_faim_ticks` du bourg ;
  - (b) une rue en chantier de J journées ajoutée au plan du bourg, construite comme dans SC3 de #971, avec le grenier remonté de J × `SALAIRE_JOURNEE_KG`. Le test affirme que la réserve lue a monté de J × `SALAIRE_JOURNEE_KG` ;
  - (c) le champ de plus petit rang qui ne porte pas le maximum, porté à un kilo au-dessus de celui-ci. Le test affirme que `champ_vise` a changé.

  Contre-épreuves, toutes sur ces variantes : une lecture qui prend `duree_faim_ticks` du bourg pour la faim diffère de la raison en (a). Une lecture qui oublie les salaires dus diffère en (b). Une lecture qui garde le `champ_vise` du montage diffère en (c). Les trois lectures sont écrites dans le test comme des enveloppes du juge qui remplacent un seul champ.
- **SC4 — Sans `sim/ia.py` ni le programme.** Les propositions sont calculées d'abord. Ensuite, sous `monkeypatch`, chaque fonction définie dans `sim.ia` et dans `sim.programme_ia` (`inspect.getmembers(…, inspect.isfunction)` dont `__module__` est le module) est remplacée par une fonction qui lève. Dans cet état, le juge rend les mêmes lectures, et SC1 passe encore. De plus, aucun nom global lu par le juge et ses aides (`__code__.co_names`, résolus dans les globales de `test_monde`) n'est le module `sim.ia` ou `sim.programme_ia`, ni un objet dont `__module__` est l'un d'eux. Contre-épreuves : sous le même patch, `programme_ia.proposer_route_vers_le_champ(monde, M, [])` lève, ce qui prouve que le patch mord. Une enveloppe du juge qui lit la réserve par `ia._reserve_voulue` lève aussi. Enfin, la vérification des noms, appliquée à une fonction dont les globales contiennent `sim.ia`, échoue.
- **SC5 — Rien d'existant ne bouge.** Ces commandes passent :
  - `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k "ia_ or raison"` ;
  - `cd jeu && python3 -m pytest sim/tests/test_programme_ia.py sim/tests/test_no_hardcoded.py -q`.

  De plus, `git diff --exit-code origin/master -- jeu/sim/ia.py jeu/sim/programme_ia.py jeu/sim/MODELE.md jeu/sim/tests/test_intentions.py jeu/sim/tests/test_programme_ia.py` est vide, et `git diff origin/master -- jeu/sim/tests/test_monde.py | grep '^-[^-]'` ne trouve rien : le lot n'ajoute que des lignes à `test_monde.py`. La ligne de `test_monde.py` dans le tableau de `sim/tests/README.md` ajoute « le juge relit la raison de la route vers le champ, sans sim/ia.py ».

## Hors périmètre
- Le branchement de `proposer_route_vers_le_champ` dans `decider_intentions`, la disparition de `route_si_bourg_affame`, et le branchement de ce juge dans `_verifier_raisons` et `test_ia_raisons_egalent_le_monde` sur la partie jouée de la graine 0 : c'est le sous-lot 4 de #951, avec la réécriture des tests de `test_intentions.py`, de `test_monde.py` et de la forge, et le paragraphe de MODELE.md.
- Vérifier que l'écart retenu est le premier valide, que la route ne touche aucune maison de 1400, ou que le geste respecte le mois : #971 l'éprouve déjà dans `test_programme_ia.py`. Le juge relit la raison, il ne refait pas la décision.
- Toute modification de `sim/ia.py`, de `sim/programme_ia.py`, du service, de la photographie ou de Unity.
