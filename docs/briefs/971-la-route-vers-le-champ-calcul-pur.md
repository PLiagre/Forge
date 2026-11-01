# Lot #971 — La route vers le champ, calcul pur
Jalon : J5 · Machine : vps · Taille prévue : 270 lignes

## But
Une fonction pure de `jeu/sim/programme_ia.py` sait dire, pour une maison de l'IA et au plus une fois par mois, quelle route elle tracerait du bord de sa place vers son champ le plus plein, et pourquoi : son bourg a eu faim le mois passé alors que ses champs gardaient des vivres, et son grenier paie la route sans descendre sous la réserve voulue. Une maison au grenier vide ne bâtit rien.

## Le joueur
C'est un lot de fond. Il prépare le geste du jalon J5 « regarder le monde vivre, puis s'en méfier ou s'en servir » : sur la carte, les maisons voisines tracent leurs routes pour des raisons qu'elles disent. Aujourd'hui, une maison de l'IA trace une route dès que son bourg a faim, dans une direction fixe, même sans un grain au grenier. Avec ce calcul, la route d'un voisin part vers le champ qui déborde pendant que le bourg a faim, et seulement si le voisin a de quoi payer ses ouvriers. Le joueur pourra lire dans la raison le grenier, la réserve, le coût, les jours de faim du bourg et les vivres des champs. Il comprendra alors qu'un voisin qui bâtit est un voisin qui a des réserves. Ce lot ne branche rien : le sous-lot 4 de #951 met ce calcul dans `decider_intentions`, puis #322 et #429 montrent ces gestes et leurs raisons sur la carte.

## Règle du monde
La règle découle de trois sections de `jeu/sim/MODELE.md`. La réserve voulue et la forme d'une raison viennent de **« Les décisions et les gestes de l'IA »**. La route qui vise un lieu, dans un cône de `ANGLE_ROUTE_INTERIEURE_DEGRES`, vient de **« La distribution à l'intérieur de la cellule »**, paragraphe « La route vers un lieu ». La place de 1400, ses maisons et le bord d'où partent les rues viennent de **« Le plan du bourg » / « Le plan de base »**. La faim du mois passé se lit dans **« Les flux sur trente jours »**. MODELE.md ne change pas dans ce lot : le monde ne joue pas encore cette règle. Le sous-lot 4 de #951 l'écrira en la branchant. Niveau 2, plausible, jamais sourcé.

**La fonction.** `proposer_route_vers_le_champ(monde, maison, releve)` rend une proposition `{maison, intention, raison}`, de la forme de celles de `sim/ia.py`, ou `None`. Elle n'écrit rien : ni le monde, ni le relevé, ni l'aléa. Elle ne garde aucun cache. Elle lit, dans cet ordre, et se tait (`None`) au premier manque :
1. **hors carte** : `maison.hors_carte` n'est pas `None` ;
2. **le bourg** : `maitre_du_bourg(monde, maison.cell_id)` doit valoir la clé du grenier, `_cle_du_grenier(maison)`. Un bourg tenu par une autre maison connue la fait taire. Un maître absent ou inconnu laisse passer l'`IntentionRefusee` de `maitre_du_bourg`, comme dans `decider_intentions` ;
3. **une fois par mois, lu au relevé** : si le relevé porte une entrée `tracer_route` de ce couple (`sorte`, `id`) avec `t − tick < FENETRE_FLUX_TICKS`, elle se tait. `t` vaut `monde.ticks_ecoules`, et une entrée refusée compte aussi. Les autres types de geste ne comptent pas ;
4. **le mois passé** : la fenêtre des flux doit être pleine (`_fenetre_pleine` de `sim/ia.py`). La faim du bourg compte les ticks de `t − FENETRE_FLUX_TICKS` à `t − 1` dont `monde.flux.jours[tick].affames` contient `(cell_id, 0)`. Zéro jour, elle se tait. `duree_faim_ticks` du bourg au tick courant n'est pas lue ;
5. **les champs** : ce sont les lieux de rang ≥ 1 de la cellule, rangés par rang, et leur nourriture se lit par `contenus_des_paniers`. Le champ visé est le plus plein, le plus petit rang à égalité. S'il n'y a aucun champ, ou si le plus plein porte 0 kg, elle se tait ;
6. **le grenier** : la clé doit être dans `monde.routes_des_lieux.noms` et son panier dans `monde.greniers`. Sinon, elle se tait. Une nourriture absente du panier pèse 0. La réserve voulue est `_reserve_voulue(monde, _lieux_de_la_maison(monde, cle))['reserve_voulue_kg']`. C'est le calcul déjà partagé par la part et le secours, salaires encore dus compris ;
7. **le tracé** : la direction du champ est `φ = atan2(y_k − y_0, x_k − x_0)`, lue sur les places de `routes_interieures._places_de(monde, cell_id)`. Sans places, elle se tait. Les écarts sont essayés dans cet ordre : 0, +p, −p, +2p, −2p…, tant que l'écart reste strictement sous `ANGLE_ROUTE_INTERIEURE_DEGRES`. Le pas `p` vaut `IA_PAS_ECART_ROUTE_DEGRES` (5), d'où onze écarts, de 0 à ±25°. Pour chaque écart `d`, l'angle vaut `θ = φ + radians(d)` et `ville1400._sortie(θ, DEMI_COTE_PLACE_1400_M)` donne le point du bord de la place et la direction `u`. La route va de ce point au point situé `IA_LONGUEUR_ROUTE_M` plus loin, sur une largeur de `IA_LARGEUR_ROUTE_M`. Les points sont des flottants non arrondis. Le premier écart retenu doit remplir deux conditions. D'abord, `lieu_de_la_route(Rue(0, points, largeur), places)` rend `(rang du champ, "")`. Ensuite, `verifier_base(monde, cell_id, points=…, largeur_m=…)` ne lève pas, donc aucune maison de 1400 n'est touchée. Une `IntentionRefusee` sans cause passe à l'écart suivant. Une `IntentionRefusee` avec cause (`BaseAbsente`) est relevée, comme dans `decider_intentions`. Si aucun écart ne passe, elle se tait ;
8. **le coût** : `journees = travail_requis_de_route(points, largeur)`, et `cout_kg = journees × SALAIRE_JOURNEE_KG`. Il faut `grenier > reserve + cout`, au sens strict. Sinon, elle se tait. Un grenier vide ne passe donc jamais, puisque `cout_kg ≥ SALAIRE_JOURNEE_KG > 0`.

**La proposition.** `maison` vaut `{sorte, id}`. `intention` vaut `{type: TYPE_TRACER_ROUTE, cell, maison: cle, points: [[x0, y0], [x1, y1]], largeur_m: IA_LARGEUR_ROUTE_M, foyers: IA_FOYERS_ROUTE}`. C'est exactement ce que `recevoir_intention` accepte d'un joueur. `raison` porte ces clés, sans arrondi :
- `regle` : `'route_vers_le_champ'` ;
- `grenier_nourriture_kg` ;
- `reserve_voulue_kg` ;
- `journees` ;
- `cout_kg` ;
- `faim_du_bourg_ticks` : les jours de faim du bourg dans la fenêtre ;
- `champs_nourriture_kg` : les rangs 1 à n, dans l'ordre, sans somme, comme dans la raison actuelle ;
- `champ_vise` : le rang ;
- `ecart_degres` : l'écart retenu, entier signé.

Le sous-lot 3 de #951 (le juge) relira ces noms : ils sont figés ici.

**Les imports.** `sim/programme_ia.py` importe `sim.ia` comme module : `import sim.ia as _ia`, puis `_ia._reserve_voulue`, `_ia._cle_du_grenier` et `_ia._fenetre_pleine`, appelés au moment du calcul. Jamais `from sim.ia import …`. Le branchement du sous-lot 4 fera `import sim.programme_ia as …` dans `ia.py`, et aucun des deux ordres d'import ne cassera. Le reste vient de `sim.intentions` (`maitre_du_bourg`, `verifier_base`, `IntentionRefusee`, `TYPE_TRACER_ROUTE`, `_lieux_de_la_maison`), de `sim.routes_interieures` (`_places_de`, `lieu_de_la_route`), de `sim.ville1400` (`_sortie`), de `sim.chantiers` (`travail_requis_de_route`), de `sim.model` (`contenus_des_paniers`) et de `sim.plan` (`Rue`).

**La constante.** `IA_PAS_ECART_ROUTE_DEGRES = 5` va dans le bloc IA de `jeu/sim/constants.py`. Son commentaire : « Niveau 2 : pas des écarts essayés autour de la direction du champ, sous ANGLE_ROUTE_INTERIEURE_DEGRES. » Elle est relue par `_constantes.X` à l'appel. `test_no_hardcoded` interdit 5, 30 et 50 en dur dans une fonction.

**Mesure du chef** (graine 0, base 6cc4f2fa, prototype `/tmp/proto971`). Elle est à re-mesurer, et elle n'est recopiée dans aucun test. `World.charger(0)` prend 3 s. Le montage se fait à `ticks_ecoules = 30`. Les jours 0 à 29 marquent `(cell_id, 0)` affamé pour chaque maison qui tient son bourg, et chaque grenier reçoit 10⁹ kg. On compte 35 maisons de l'IA sur la carte qui tiennent leur bourg. **16** reçoivent une route (grande-2, 10206, la première, à l'écart 0), avec des écarts de −10 à +15 et un coût de 240 ou 243 kg. **19** n'en reçoivent pas : à chaque écart, la route vise un autre lieu ou touche une maison de 1400, et chacune a au moins un écart refusé par les seules maisons (grande-1, 10237, la première). Toutes les cellules ont un champ plein au chargement.

## Périmètre
jeu/sim/programme_ia.py
jeu/sim/tests/test_programme_ia.py
jeu/sim/constants.py
jeu/sim/tests/README.md

## Conditions de succès
Toutes se lancent par `cd jeu && python3 -m pytest sim/tests/test_programme_ia.py -q`, sauf SC8. Le fichier de tests est neuf, comme le module : la demande le nomme. Une ligne du tableau de `sim/tests/README.md` dit ce qu'il protège : « le programme de l'IA : la route vers le champ, ses conditions et sa raison, pure, avec contre-épreuves ».

Le montage de référence est une fixture de module. Elle charge `World.charger(0)` et pose `ticks_ecoules = FENETRE_FLUX_TICKS`. Pour les jours 0 à 29, elle crée des `JourDeFlux(t)` dont `affames` contient `(cell_id, 0)` de chaque maison de `maisons_de_l_ia` qui est sur la carte et tient son bourg. Elle met 10⁹ kg de nourriture dans chacun de leurs greniers. Chaque test travaille sur une `deepcopy`. **M** est la première maison, dans l'ordre de `maisons_de_l_ia`, qui reçoit une proposition dans ce montage. Les comptes sont dérivés et affichés par `print`, jamais recopiés de la mesure du chef.

Une aide `_controler(monde, releve, proposition)` relit tout indépendamment de la fonction, avec `_places_de`, `lieu_de_la_route`, `verifier_base`, `travail_requis_de_route` et `_ia._reserve_voulue`. Les contre-épreuves l'appellent sous `pytest.raises(AssertionError)`.

- **SC1 — Une route vers le champ le plus plein, sur le vrai monde.** Le test appelle la fonction pour chaque maison du montage. Au moins une proposition sort, et leur nombre est affiché. Pour chaque proposition, `_controler` vérifie ceci :
  - les clés exactes de `maison`, `intention` et `raison` ;
  - `max(|x0|, |y0|) == DEMI_COTE_PLACE_1400_M` à 1e-9 près, et une longueur de `IA_LONGUEUR_ROUTE_M` à 1e-9 près ;
  - l'angle entre `p1 − p0` et φ vaut `|ecart_degres|` à 1e-9 près, l'écart reste strictement sous `ANGLE_ROUTE_INTERIEURE_DEGRES` et c'est un multiple du pas ;
  - `lieu_de_la_route` rend `(champ_vise, "")`, et `verifier_base` ne lève pas ;
  - `champ_vise` est l'argmax des vivres, le plus petit rang à égalité, et sa nourriture est positive ;
  - `faim_du_bourg_ticks` vaut 30 ;
  - `journees` et `cout_kg` suivent la règle, et `grenier > reserve + cout` ;
  - chaque écart essayé avant le retenu, dans l'ordre 0, +5, −5…, échoue soit sur le lieu visé, soit sur `verifier_base` ;
  - `recevoir_intention(deepcopy(monde), intention)` accepte la route, par le chemin du joueur.

  Contre-épreuves, chacune sur une copie de la proposition de M : les points tournés de 30° autour de `p0`, `p0` rapproché de l'origine d'1 m, `cout_kg + 1`, `champ_vise` remplacé par un autre rang, et une proposition à l'écart +10 là où un écart plus petit passe.
- **SC2 — Pure et déterministe.** Pour M et pour une maison qui se tait : `deepcopy((monde.__dict__, releve))` est inchangé après l'appel, et deux appels rendent la même chose. Deux montages chargés séparément donnent des propositions égales par `json.dumps`, pour toutes les maisons. Contre-épreuve : une enveloppe qui ajoute 1 kg au grenier de M avant d'appeler la fonction fait échouer le contrôle de pureté. L'aide est celle de `_ia_pure` de `test_intentions.py`, importée ou recopiée.
- **SC3 — Une maison au grenier vide ne bâtit rien.** Pour M, la référence est la proposition du montage, avec R = `reserve_voulue_kg` et C = `cout_kg`. Avec un grenier à 0, un panier sans nourriture ou un panier absent, la fonction rend `None`. Un grenier à R + C rend `None`, puisque l'inégalité est stricte. Un grenier à R + C − 1 rend `None` : le test affirme d'abord que R + C − 1 > R, donc une règle qui oublierait le coût proposerait ici et ferait échouer le test. Un grenier à R + C + 1 rend une proposition identique en dehors du grenier. Enfin, à R + C + 1, une rue en chantier ajoutée au plan du bourg de M, avec `travail_requis − travail_fourni = J`, rend `None`. Ce dernier cas montre que la réserve compte les salaires encore dus : la raison qu'on obtient en remontant le grenier de J × `SALAIRE_JOURNEE_KG` porte une réserve plus haute d'autant.
- **SC4 — Le bourg a eu faim le mois passé, ses champs gardaient des vivres.** Toujours pour M, chacun des cas suivants rend `None` :
  - aucun `(cell_id, 0)` dans la fenêtre ;
  - la faim d'un champ seulement, `(cell_id, 1)` sur 30 jours ;
  - une faim au tick −1 seulement, hors fenêtre ;
  - le jour `t − 1` retiré de `flux.jours`, ce qui rend la fenêtre incomplète ;
  - la nourriture de tous les champs à 0.

  Ces cas proposent, en revanche :
  - un seul jour de faim, au tick `t − 1`, avec `faim_du_bourg_ticks == 1` ;
  - `duree_faim_ticks` du bourg à 0 au tick courant ;
  - le champ de plus petit rang qui ne porte pas le maximum, porté à un kilo au-dessus de celui-ci : `champ_vise` change, et `_controler` passe.

  Contre-épreuves : dans le cas « faim d'un champ seulement », le test affirme que la cellule a bien eu faim, donc une règle qui lirait la faim de la cellule proposerait. Dans le cas sans faim du mois, mettre `duree_faim_ticks` du bourg à 5 rend toujours `None`, donc une règle qui lirait la faim du jour proposerait.
- **SC5 — Une fois par mois au plus, et seulement pour son bourg.** Pour M, un relevé qui porte une `tracer_route` de M à `t − FENETRE_FLUX_TICKS + 1`, acceptée ou refusée (clé `refus`), rend `None`. Ces relevés proposent : la même entrée à `t − FENETRE_FLUX_TICKS`, une `tracer_route` d'une autre maison à `t − 1`, et une `fixer_part` ou une `ouvrir_grenier` de M à `t − 1`. M rendue hors carte (`replace(maison, cell_id=None, hors_carte='hors carte')`) rend `None`. Un bourg dont le maître est une autre maison connue du registre rend `None`. Un maître inconnu lève `IntentionRefusee`.
- **SC6 — Ni maison de 1400 touchée, ni route hors des 30°.** Le test prend chaque maison du montage dont le grenier, la faim et les champs passent, mais qui reçoit `None`. Il affirme que, pour chacun des onze écarts, soit `lieu_de_la_route` vise un autre rang, soit `verifier_base` refuse. Il en compte au moins une, et le compte est affiché. Contre-épreuve : avec `programme_ia.verifier_base` remplacé par une fonction qui accepte tout (`monkeypatch`), au moins une de ces maisons reçoit une route, et le vrai `verifier_base` la refuse sur ses points. Avec un `verifier_base` qui refuse le seul écart 0 de M, M reçoit son premier écart suivant valide, et `_controler` passe. Avec `ville1400.base_de_cellule` qui lève `BaseAbsente`, la fonction lève `IntentionRefusee` au lieu de rendre `None`.
- **SC7 — La raison dit ce qui a décidé.** Pour M, la raison est égale, clé à clé, à la lecture du test : grenier, réserve, journées, coût, faim, champs, champ visé et écart. Contre-épreuves : une raison où `champs_nourriture_kg` est la somme au lieu de la liste échoue, comme une raison où `faim_du_bourg_ticks` est lu dans `duree_faim_ticks`, ou une raison sans `regle`.
- **SC8 — Rien n'est branché, rien d'existant ne bouge.** `cd jeu && python3 -m pytest sim/tests/test_no_hardcoded.py sim/tests/test_write_coverage.py sim/tests/test_intentions.py -q` passe. La commande `! grep -rln "programme_ia" sim --include=*.py | grep -v -e "sim/programme_ia.py" -e "sim/tests/test_programme_ia.py"` ne trouve rien. `git diff --exit-code origin/master -- jeu/sim/ia.py jeu/sim/MODELE.md jeu/sim/tests/test_intentions.py jeu/sim/tests/test_monde.py` est vide. Les commandes `python3 -c "import sim.programme_ia, sim.ia"` et `python3 -c "import sim.ia, sim.programme_ia"` passent toutes deux. Contre-épreuve : un `5` littéral glissé dans une fonction de `programme_ia.py` fait rougir `test_no_hardcoded`. On le vérifie à la main avant la PR, sans le committer.

## Hors périmètre
- Le branchement dans `decider_intentions`, la disparition de `route_si_bourg_affame`, la réécriture des tests de `test_intentions.py`, `test_monde.py` et de la forge, et le paragraphe de MODELE.md : c'est le sous-lot 4 de #951.
- Le juge de `test_monde` qui relit la raison `route_vers_le_champ` sans `sim/ia.py` : c'est le sous-lot 3 de #951.
- La mesure sur les trente derniers jours (`maisons_actives_30j`) : c'est le sous-lot 1 de #951 (#970).
- Savoir si le champ visé a déjà sa route, ou si la nouvelle route croise une rue déjà tracée : la fonction ne le regarde pas, et la règle de l'issue ne le demande pas.
- La longueur, la largeur et les foyers de la route : ils restent ceux de l'IA d'aujourd'hui (`IA_LONGUEUR_ROUTE_M`, `IA_LARGEUR_ROUTE_M`, `IA_FOYERS_ROUTE`).
- Le choix de la maison du joueur, l'ordre des maisons, le secours et la part : ils restent dans `decider_intentions`.
- Unity, le service et la photographie.
