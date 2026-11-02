# Lot #985 — Le juge de la raison lit les deux règles
Jalon : J5 · Machine : vps · Taille prévue : 190 lignes

## But
Sur la partie jouée de la graine 0, `test_monde` relit chaque raison de route de l'IA selon sa règle : l'ancienne règle `route_si_bourg_affame` par sa lecture actuelle, et la route vers le champ par le juge de #972. Les quatre tests de la partie jouée sont aussi joués avec le programme de #971, branché par le test seul, assez de jours pour qu'il trace ses routes. L'ancienne règle reste celle du jeu.

## Le joueur
Le joueur n'y voit rien encore. Ce lot prépare le monde vivant du jalon J5, où chaque maison de l'IA trace sa route vers son champ le plus plein, avec une raison relue contre le monde. C'est le geste « regarder le monde vivre, puis s'en méfier ou s'en servir » : sur la carte, les maisons voisines tracent leurs routes « pour des raisons qu'elles disent ». Quand le joueur lira « grenier de tant, bourg affamé tant de jours, champ le plus plein » dans la raison d'un voisin, ce sera vrai au jour du geste, sur une vraie partie et pas seulement sur un monde préparé. Après ce lot, brancher le programme ne demande plus de toucher à ces quatre tests. Les sous-lots suivants de #973 le branchent dans `decider_intentions`. Puis #428 sert ces raisons, et #322 et #429 les montrent sur la carte.

## Règle du monde
Sans objet : c'est un lot d'outil. Il ne change ni le monde, ni `jeu/sim/ia.py`, ni `jeu/sim/programme_ia.py`, ni `jeu/sim/MODELE.md`. Les deux règles relues découlent de **« Les décisions et les gestes de l'IA »**, de **« Les flux sur trente jours »** et de **« La distribution à l'intérieur de la cellule »** (paragraphe « La route vers un lieu »). MODELE.md recevra la route vers le champ au branchement (sous-lot 3 de #973).

**Le branchement d'épreuve.** Une aide `_brancher_programme(patch)` est ajoutée à `test_monde.py`. Elle reçoit un `MonkeyPatch` et remplace `sim.ia.decider_intentions` par une enveloppe qui :
- appelle la vraie fonction ;
- retire les propositions `tracer_route` qu'elle a rendues ;
- parcourt `maisons_de_l_ia(monde)` dans l'ordre et saute les mêmes maisons que `decider_intentions` : les maisons hors carte, et la seigneurie du joueur, lue de la même façon (`maison_du_joueur`, sinon `ChoixDepart` en attente) ;
- pour chaque maison gardée, place d'abord `programme_ia.proposer_route_vers_le_champ(monde, maison, releve)` si elle n'est pas `None`, puis les autres propositions de cette maison, dans leur ordre d'origine ;
- affirme qu'aucune proposition d'origine (secours, part) n'est perdue.

`jouer_ia` lit `decider_intentions` dans les globales de `sim.ia` : le patch mord donc aussi dans `sim.__main__` et dans `sim.service`. Dans un processus fils, l'amorçage est `"import pytest, sim.tests.test_monde as t; t._brancher_programme(pytest.MonkeyPatch()); "` :
- pour le service, il passe par le paramètre `amorcage` qui existe déjà dans `lancer_service` ;
- pour la ligne de commande, `_ia_cli` reçoit un paramètre `amorcage=""`. Quand il est rempli, la commande devient `[sys.executable, '-c', amorcage + "import runpy; runpy.run_module('sim', run_name='__main__', alter_sys=True)", …]`, sur le modèle de `lancer_service` ;
- `_lancer_service_ia` reçoit aussi `amorcage=""`. Sans argument, ces deux aides restent identiques à aujourd'hui pour leurs autres appelants (lignes 4253, 4254, 4766 et 4782).

**La lecture par règle.**
- `_verifier_raisons(ticks)` enveloppe aussi `cli.jouer_ia`. Après le vrai appel et avant le tick, pour chaque entrée neuve du relevé de type `tracer_route` dont la raison dit `regle == 'route_vers_le_champ'`, elle note `_lire_route_vers_le_champ(monde, maison, entree['intention'])` dans `lectures_champ[tick][(sorte, id)]`, et elle l'expose en `_verifier_raisons.champ`. La lecture actuelle (`_lire_raison_monde`, faite dans l'enveloppe de `cli.tick`) ne change pas.
- `_controler_raisons(lectures, releve, champ=None)` prend la lecture selon la règle que dit la raison : `champ.get(tick, {}).get(couple)` pour `route_vers_le_champ`, et `lectures[tick][couple]` sinon. Une route sans lecture échoue par `AssertionError`, jamais par `KeyError`. Les appels existants à deux arguments gardent leur sens exact.

**Mesure du chef** (base 9f9a2081, graine 0, prototype `/tmp/proto985`, branchement comme ci-dessus, juge de #972) :

| Réglage | Routes du programme sur 100 jours |
|---|---|
| Monde réel (part 0,03, bras 6,2) | 65, 68, 70, 70, 94, 98 ; 0 refus ; premier geste du relevé : un `fixer_part` au jour 30 |
| Bras 0,1, part 0,03 | 62, 68, 70, 70, 92, 94, 94, 98 |
| Part 0, bras 6,2 | aucune route en 100 jours, ni en 160 |
| Part 0, bras 0,1 | une seule route, au jour 97 |

- Le juge égale toutes les raisons, à l'octet.
- Avec une part nulle, le grenier ne dépasse jamais réserve + coût. La variante programme du test des raisons garde donc la part réelle (voir SC1).
- Rejouer par `--gestes`, sans branchement, les 100 jours joués avec le programme redonne le même `--monde-json`, à l'octet.
- Durées : 100 jours avec le programme ≈ 82 s, contre ≈ 50 s avec l'ancienne règle et 13 s pour le rejeu des gestes.

Ces nombres sont à re-mesurer. Seules les dates de l'ancienne règle, déjà figées, restent dans un test.

## Périmètre
jeu/sim/tests/test_monde.py
jeu/sim/tests/README.md

## Conditions de succès
Une constante de test `_JOURS_DU_PROGRAMME = 100` porte la durée des variantes programme, avec un commentaire : la première route tombe vers le jour 65, et l'horizon garde de la marge. Les quatre tests reçoivent un paramètre `regle`, d'identifiants `ancienne` et `programme`.
- La variante `ancienne` garde son nombre de jours, ses réglages, ses dates figées et toutes ses contre-épreuves. Elle passe par le même code qu'aujourd'hui, hormis la lecture par règle.
- La variante `programme` branche le programme par `_brancher_programme` : un `monkeypatch` dans le processus de test, ou l'amorçage dans le processus fils.

Les dates et les comptes du programme sont affichés par `print`. Ils ne sont jamais figés.

- **SC1 — Les raisons se lisent selon leur règle.** `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k raisons_egalent` passe, avec quatre cas (`historique`/`calibre` × `ancienne`/`programme`).
  - `ancienne` : rien ne change. On garde 70 jours, une part nulle, les dates `[25, 37, 39, 61, 64, 69]` et `[25, 37, 39, 63, 64, 69]`, les contre-épreuves sur `bourg.duree_faim_ticks`, sur le premier champ, sur la raison retirée, sur l'échantillon vide et sur les seules parts, et le bloc du secours. On affirme en plus qu'aucune raison ne dit `route_vers_le_champ`.
  - `programme` : `_JOURS_DU_PROGRAMME` jours, avec la part coutumière réelle (pas de `PART_COUTUMIERE = 0`, sinon il n'y a aucune route) et le même `BRAS_AUX_CHAMPS_PAR_KM2` que le cas. On exige au moins une route. Toutes les routes disent `route_vers_le_champ`, aucune ne tombe avant `FENETRE_FLUX_TICKS`, et `_verifier_raisons` passe : chaque raison égale le juge à son jour. Le bloc du secours est rejoué tel quel.
  - Contre-épreuves de `programme`, chacune sur une copie du relevé qui lève `AssertionError` dans `_controler_raisons(lectures, copie, champ)` :
    - `faim_du_bourg_ticks + 1` sur la première route ;
    - son premier champ + 1 ;
    - `champ_vise` remplacé par un autre rang de sa cellule ;
    - `regle` remplacée par `'route_si_bourg_affame'` ;
    - la raison retirée ;
    - le relevé réduit à ses parts.
  - Deux contre-épreuves de plus : le relevé vrai contrôlé **sans** `champ` (une lecture unique, l'ancienne) échoue, et l'échantillon vide échoue.
- **SC2 — Le rejeu à l'octet, pour les deux règles.** `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k rejeu_octets` passe, avec deux cas.
  - `ancienne` garde ses 30 jours.
  - `programme` joue `_JOURS_DU_PROGRAMME` jours par l'amorçage : deux courses donnent le même résumé et les mêmes octets du monde, et le rejeu des gestes par `--gestes`, **sans** amorçage, redonne ces octets.
  - Pour les deux cas, la falsification porte sur la **première entrée `tracer_route`** des gestes. C'est déjà `gestes[0]` pour `ancienne`, qui ne change donc pas. Pour `programme`, le premier geste est une part sans `points`. Les octets doivent alors différer.
  - Contre-épreuves que le branchement mord : le relevé `programme` contient au moins une route, et toutes disent `route_vers_le_champ`. Celui d'`ancienne` n'en contient aucune qui le dise.
- **SC3 — La mesure glissante, pour les deux règles.** `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k mesure_reelle` passe, avec deux cas : `ancienne` à 31 jours, et `programme` à `_JOURS_DU_PROGRAMME`. Les bornes figées sur 31 sont dérivées de `ticks`, de façon que le cas `ancienne` reste identique :
  - une route vérifie `0 <= tick < ticks` ;
  - une part vérifie `FENETRE_FLUX_TICKS <= tick < ticks`, ce qui vaut `tick == 30` à 31 jours ;
  - les parts d'une même maison tombent toutes le même jour du mois (`tick % FENETRE_FLUX_TICKS`) ;
  - `controler_mesure` reçoit `ticks`, et la « tardive » du jour 30 devient celle du jour `ticks − 1`.

  Toutes les contre-épreuves restent, pour les deux cas : l'ancienne mesure échoue, `verifier([])` échoue, la cellule −1 échoue, et une part au jour 29 échoue.
- **SC4 — Le service égale la ligne de commande, pour les deux règles.** `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k service_ia_egal_cli` passe, avec deux cas.
  - `ancienne` garde ses 31 jours.
  - `programme` joue `_JOURS_DU_PROGRAMME` jours avec l'amorçage, dans le CLI comme dans le service. `/tick?n=…`, la date, `/ia`, les plans, les foyers et `_verifier_lieu_contre_photo` sont lus au même jour. Le relevé contient au moins une route `route_vers_le_champ`.
  - Les contre-épreuves restent dans les deux cas : le relevé faussé d'un jour, `/ia` absent sans option, et au moins un plan ou un lieu qui diffère sans IA.
- **SC5 — Rien d'autre ne bouge.**
  - Ces commandes passent sans modification des tests qu'elles lancent :
    - `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k "ia_ or raison"` ;
    - `cd jeu && python3 -m pytest sim/tests/test_programme_ia.py sim/tests/test_intentions.py sim/tests/test_no_hardcoded.py -q`.
  - `test_ia_route_vers_le_champ_relue` (le juge sans `sim/ia.py`, #972) reste tel quel.
  - `git diff --exit-code origin/master -- jeu/sim/ia.py jeu/sim/programme_ia.py jeu/sim/MODELE.md jeu/sim/__main__.py jeu/sim/service.py jeu/sim/tests/test_intentions.py jeu/sim/tests/test_programme_ia.py` est vide.
  - Les deux listes de dates de l'ancienne règle sont encore dans `test_monde.py`, inchangées.
  - La ligne de `test_monde.py` dans le tableau de `sim/tests/README.md` ajoute : « chaque raison de route est lue selon sa règle ; les quatre tests de la partie jouée sont aussi joués 100 jours avec le programme branché par le test ».

## Hors périmètre
- Brancher `proposer_route_vers_le_champ` dans `decider_intentions` et retirer `route_si_bourg_affame` : ce sont les sous-lots suivants de #973. Ils décideront aussi du sort des variantes `ancienne`. Au branchement, `_brancher_programme` devient sans effet. Le constat « à part nulle, le programme ne trace aucune route » leur revient : le cas `ancienne` du test des raisons joue à part nulle.
- La montée en charge d'`_ia_monde` sur le montage du programme, et les tests de `test_intentions.py` : sous-lot 2 de #973.
- Le coût du programme (≈ 1,6 fois l'ancienne IA sur 100 jours) : il est noté ici pour le branchement, et ce lot n'y touche pas.
- Toute modification de `sim/`, de la forge, du service, de la photographie ou de Unity.
