# Lot #986 — Le montage de l'IA passe sur celui du programme
Jalon : J5 · Machine : vps · Taille prévue : 250 lignes

## But
Six tests de l'IA dans `test_intentions.py` montent le monde comme `test_programme_ia` et sont joués deux fois, avec l'ancienne règle des routes et avec le programme branché par le test : ils prouvent le dépôt, le registre des choix, les copies, la raison lue, le refus compté et la base vérifiée quelle que soit la règle qui choisit la route. L'ancienne règle reste celle du jeu.

## Le joueur
Le joueur n'y voit rien encore. Ce lot prépare le monde vivant du jalon J5, où chaque maison de l'IA trace sa route vers son champ le plus plein, pour une raison qu'elle dit. C'est le geste « regarder le monde vivre, puis s'en méfier ou s'en servir » : sur la carte, les maisons voisines tracent leurs routes « pour des raisons qu'elles disent ». Quand le programme remplacera l'ancienne règle, ces six tests garderont ce qui protège le joueur. Une maison voisine ne passe que par le chemin de ses gestes. Elle ne peut pas écrire dans le monde. Elle ne bâtit pas sur une maison de 1400. Et ce qu'elle dit de sa route est vrai au jour du geste. Après ce lot, brancher le programme ne demande plus de réécrire ces tests. Le sous-lot suivant de #973 le branche dans `decider_intentions`. Puis #428 sert ces raisons, et #322 et #429 les montrent sur la carte.

## Règle du monde
Sans objet : c'est un lot d'outil. Il ne change ni le monde, ni `jeu/sim/ia.py`, ni `jeu/sim/programme_ia.py`, ni `jeu/sim/MODELE.md`, ni `test_monde.py`, ni `test_programme_ia.py`. Les deux règles éprouvées découlent de **« Les décisions et les gestes de l'IA »**, de **« Les flux sur trente jours »** et de **« La distribution à l'intérieur de la cellule »** (paragraphe « La route vers un lieu »). MODELE.md recevra la route vers le champ au branchement (sous-lot 3 de #973).

**Le montage.** `_ia_monde(patch=None, regle=None)` remplace l'actuel `_ia_monde()`. Il :
- appelle `_monter()` de `test_programme_ia` : graine 0 au tick 30, trente jours de faim notés pour chaque bourg, grenier de 1e9 kg ;
- garde `duree_faim_ticks = 1` sur chaque bourg, pour l'ancienne règle ;
- quand `regle == 'programme'`, branche le programme par `_brancher_programme(patch)` de `test_monde` (#985) ;
- quand `regle` est donné, affirme que les routes de `ia.decider_intentions(monde, [])` disent toutes `_REGLE_DES_ROUTES[regle]` : `route_si_bourg_affame` pour l'ancienne règle, `route_vers_le_champ` pour le programme.

Sans `regle`, rien n'est branché et rien n'est affirmé. Les tests qui ne sont pas dans la liste (`test_ia_budget_annuel_et_branches`, `test_terres_ia`, `test_ia_budget_routes_seules`, `test_ia_lecture_refus_avant_depot`) appellent `_ia_monde()` sans argument et ne sont pas modifiés. `test_ia_refus_compte_pour_l_annee` appelle `test_ia_lecture_refus_avant_depot` sous le branchement du programme : avec une affirmation à chaque appel, il rougirait.

Les maisons de `_monter` sont exactement les 35 maisons sur la carte de l'actuel `_ia_monde`. Il y a trois aides de plus :
- `_REGLES_IA = pytest.mark.parametrize('regle', ['ancienne', 'programme'])` ;
- `_routes_de(propositions, couple=None)` garde les `tracer_route`, et seulement celles d'une maison quand `couple` est donné ;
- `_mois_affame(monde, maisons, t)` porte le monde au tick `t`, avec les trente jours d'avant notés affamés pour chaque bourg (même remplissage que `_monter`).

**Mesure du chef** (base f853b773, prototype `/tmp/proto986/jeu/sim/tests/test_intentions.py`, 241 lignes de diff) :
- Au montage, l'ancienne règle trace une route pour les 35 maisons. Le programme en trace pour 16 : grande 1 (Lancastre, `maisons[0]`) n'en a pas, et parmi les seigneuries seul Bar (1) et le Zab (6) en tracent. Les parts de grande-3, grande-12 et grande-19 tombent au jour 30.
- Mise en scène de la raison (bourg de 20 742 habitants, champs à 1000 + i kg, douze jours de faim) : `maisons[0]` trace sa route avec les deux règles si le grenier vaut 1 000 077,25 kg. Avec 77,25 kg, le programme se tait (réserve voulue ≈ 459 297 kg).
- Base de 10103 : le champ 3 seul plein → avec la vérification le programme se tait, sans elle il propose l'écart 0, refusé au dépôt (« maison de 1400 13 (1 foyers) touchée ») ; le champ 2 plein → l'écart 0 est accepté. Base de 10322 : le champ 4 → se tait, sans vérification refusé ; le champ 1 → accepté.
- 20 cas verts. Avec `_brancher_programme` neutralisé, les 10 cas `programme` rougissent.
- Durée : ≈ 3 min 20 s pour les 20 cas, contre ≈ 1 min 40 s pour les 10 d'aujourd'hui.

Ces nombres sont à re-mesurer. Aucun n'est figé dans un test, sauf les géométries de l'ancienne règle déjà figées.

## Périmètre
jeu/sim/tests/test_intentions.py
jeu/sim/tests/README.md

## Conditions de succès
Les six tests reçoivent `@_REGLES_IA`. Chaque cas monte son monde par `_ia_monde(monkeypatch, regle)`.
- Partout, `tick=0` devient `monde.ticks_ecoules` (le montage est au jour 30).
- Une comparaison qui ne vise que les routes passe par `_routes_de`, parce qu'au jour 30 une maison peut aussi proposer sa part.
- Les affirmations propres à l'ancienne règle (géométries, champs de sa raison, budget à l'année) restent, sous `if regle == 'ancienne'`. Le sous-lot 4 de #973 les retirera. Aucune n'est retirée par ce lot.

- **SC1 — Lecture locale.** `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k ia_lecture_locale` passe, avec 8 cas.
  - La maison est la première de `maisons` dont la règle trace une route au montage. Le second élément de `maisons_de_l_ia` reste sa copie hors carte.
  - La faim est posée pour les deux règles : `bourg.duree_faim_ticks = n` et `_affamer(monde, cell_id, range(t − n, t))`.
  - `attendu` devient une table par règle. On garde les quatre cas d'aujourd'hui pour `ancienne` : `(1, 10, 0) → True`, `(1, 10, 1000) → True`, `(0, 10, 0) → False`, `(1, 0, 1000) → False`. Pour `programme` : `False`, `True`, `False`, `True`. Le programme lit les vivres des champs et la faim du mois, pas la population.
  - On compare `bool(_routes_de(...))`.
  - Le retournement met la population à 10, les champs à 1000 kg, retourne la faim, et exige `bool(routes) != bool(faim)`.
  - La contre-épreuve `impur` reste.
- **SC2 — Registre des choix.** `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k ia_registre_choix` passe, avec 2 cas, sous `maisons_de_l_ia` remplacé par `maisons` comme aujourd'hui.
  - Pour Morée et Bar, choisies (`maison_du_joueur`) puis en attente (`ChoixDepart`), les maisons qui tracent une route égalent celles du montage sans choix, moins la seigneurie choisie.
  - Sans choix, on retrouve toutes celles du montage.
  - Contre-épreuve : au moins une des deux seigneuries trace une route sans choix (Bar, pour les deux règles). Sinon le filtre ne mord pas, et le test échoue.
  - Sous `ancienne`, le test appelle encore `test_ia_budget_annuel_et_branches()`, comme aujourd'hui.
- **SC3 — Dépôt commun et copies.** `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k ia_depot_commun` passe, avec 2 cas.
  - L'indice `route` est celui de la première `tracer_route` des propositions. Les copies faussées (`captures`, `releve`, `intentions_en_attente`) portent sur cette route.
  - L'intention notée égale celle proposée. Elle a exactement les clés `type`, `maison`, `cell`, `points`, `largeur_m` et `foyers`, avec `type == 'tracer_route'`, `maison == _cle_du_grenier`, `cell == cell_id`, `largeur_m == IA_LARGEUR_ROUTE_M` et `foyers == IA_FOYERS_ROUTE`. Sous `ancienne`, on garde aussi `points == [[0, 0], [40, 0]]`.
  - Toutes les propositions (parts comprises) sont capturées, refusées et déposées comme aujourd'hui.
  - La contre-épreuve `ecrire_plan` lit `i.get('cell')`, parce qu'une part n'a pas de cellule. Elle doit toujours lever `AssertionError`.
- **SC4 — Raison lue.** `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k ia_raison_lue` passe, avec 2 cas, sur `maisons[0]`.
  - La mise en scène d'aujourd'hui reste, avec deux changements : les douze jours de faim sont aussi posés par `_affamer`, et le grenier vaut 1 000 077,25 kg.
  - La proposition est la route de cette maison. Elle égale la lecture de sa règle, choisie par la règle que dit sa raison : `_lire_raison_monde` pour l'ancienne, `_lire_route_vers_le_champ(monde, maison, intention)` (#972) pour le programme.
  - Pour les deux règles : `regle == _REGLE_DES_ROUTES[regle]`, `champs_nourriture_kg == [1000 + i]` et `grenier_nourriture_kg == 1 000 077,25`.
  - Sous `ancienne`, on garde `bourg`, `departs` et `chantiers_en_cours`. Sous `programme`, `faim_du_bourg_ticks == 12` et `champ_vise` égale le dernier champ.
  - Les quatre mutations font différer la raison de la lecture, puis l'égaler après restauration : la faim à 13 jours (`duree_faim_ticks` et le flux), le premier champ à 1 kg, le grenier à 1 kg, et la rue en chantier retirée (la réserve du programme compte ses journées).
  - La raison d'origine diffère de la lecture d'un bourg sans faim.
  - Grenier absent, puis panier sans nourriture : `ancienne` garde `-1` et `0` ; `programme` ne trace aucune route pour cette maison.
- **SC5 — Refus compté.** `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k refus_compte_pour` passe, avec 2 cas.
  - Après le refus de toutes les propositions, `_routes_de(decider_intentions(monde, releve)) == []` : le refus compte dans le budget, à l'année pour l'ancienne règle, au mois pour le programme. Contre-épreuve : avec un relevé vide, les mêmes routes reviennent.
  - Le monde passe ensuite par `_mois_affame(monde, maisons, CALENDAR_DAYS_PER_YEAR + FENETRE_FLUX_TICKS)`. Une nouvelle année et un nouveau mois rouvrent les deux budgets : les maisons qui tracent égalent celles du premier tour. Les nouvelles entrées du relevé égalent ces propositions refusées, à leur tick, et le monde est inchangé.
  - Restent tels quels : `controle` et ses deux contre-épreuves, la mesure `maisons_actives_30j` et l'ancienne mesure, l'appel à `test_ia_lecture_refus_avant_depot(isole, 'cellule')`, et `deposer_puis_lever`.
- **SC6 — Base vérifiée avant le dépôt.** `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k ia_base_route_avant_depot` passe, avec 4 cas : `(10103, champ 3, champ 2)` et `(10322, champ 4, champ 1)` × les deux règles.
  - `ia._proposition_de_part` est tu pour ce test : la part de grande-3 tombe au jour 30.
  - Mise en scène, la même pour les deux règles : le champ bloqué seul plein (1000 kg, les autres 1 kg) et les 13 rues d'aujourd'hui. Aucune route n'est proposée, et le monde est inchangé.
  - Sous la sonde, `verifier_base` est remplacé dans `sim.ia` **et** dans `sim.programme_ia`. Une route est proposée, refusée au dépôt avec « maison de 1400 », et le monde est inchangé.
  - Une rue retirée et le champ libre seul plein : la route proposée est acceptée par `recevoir_intention`.
  - Sous `ancienne`, on garde `[[0, 52], [40, 52]]` et `[[0, 48], [40, 48]]`.
- **SC7 — Le branchement mord.** On neutralise la ligne `patch.setattr(ia, 'decider_intentions', decider)` dans une copie de `test_monde.py`. Les dix cas `programme` des six tests doivent alors échouer (mesuré : 10 échecs), au minimum par l'affirmation de `_ia_monde`. Ce contrôle se fait à la main dans une copie. Il ne laisse aucune trace dans le dépôt, et le relecteur peut le rejouer.
- **SC8 — Rien d'autre ne bouge.**
  - `cd jeu && python3 -m pytest sim/tests/test_intentions.py sim/tests/test_programme_ia.py sim/tests/test_chantiers.py sim/tests/test_no_hardcoded.py -q` passe. En particulier, `test_ia_budget_annuel_et_branches`, `test_terres_ia`, `test_ia_budget_routes_seules` et `test_ia_lecture_refus_avant_depot` passent sans modification de leur corps.
  - `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k "ia_ or raison"` passe.
  - `git diff --exit-code origin/master -- jeu/sim/ia.py jeu/sim/programme_ia.py jeu/sim/MODELE.md jeu/sim/tests/test_monde.py jeu/sim/tests/test_programme_ia.py` est vide.
  - Le tableau de `sim/tests/README.md` reçoit une ligne `test_intentions.py` : « le dépôt, le refus et le service des intentions ; les tests du dépôt, du choix, des copies, de la raison, du refus compté et de la base de l'IA sont joués avec l'ancienne règle et avec le programme branché par le test ».

## Hors périmètre
- Brancher `proposer_route_vers_le_champ` dans `decider_intentions` et retirer `route_si_bourg_affame` : sous-lot 3 de #973. Au branchement, `_brancher_programme` devient sans effet, et les cas `programme` restent verts sans réécriture.
- Les tests propres à la règle (`budget_annuel_et_branches`, `an_ia_sans_refus`, `terres_ia`, `budget_routes_seules`, `grenier_decision`) : sous-lot 3 de #973. Ce lot ne touche pas leur corps.
- Retirer les cas `ancienne` et les affirmations sous `if regle == 'ancienne'` : sous-lot 4 de #973.
- Le programme ne lit pas la population du bourg (cas `(1, 0, 1000)`) : ce lot l'éprouve tel que #971 l'a livré, il ne le corrige pas.
- Toute modification de `sim/`, de `test_monde.py`, de `test_programme_ia.py`, de la forge, du service, de la photographie ou de Unity.
