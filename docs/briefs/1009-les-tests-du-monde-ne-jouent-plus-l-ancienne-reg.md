# Lot #1009 — Les tests du monde ne jouent plus l'ancienne règle des routes
Jalon : J5 · Machine : vps · Taille prévue : 130 lignes

## But
Les quatre tests de la partie jouée de `test_monde.py` (rejeu des octets, mesure glissante, raisons relues contre le monde, service égal à la commande) ne se jouent plus qu'avec la route vers le champ du programme : le branchement du programme dans `decider_intentions` n'aura plus à les toucher.

## Le joueur
Le joueur n'y voit rien. C'est un lot de fond du geste du jalon 5 « regarder le monde vivre, puis s'en méfier ou s'en servir » : sur la carte, les maisons de l'IA tracent leurs routes vers leur champ le plus plein, « pour des raisons qu'elles disent ». Ce lot prépare le branchement de cette route (#1000, dont il est découpé). Après lui, le service et la forge la rendront visible ; puis #428 servira ses raisons, et #322 et #429 les montreront sur la carte.

## Règle du monde
Sans objet : c'est un lot d'outil. Il ne change ni le monde, ni `jeu/sim/ia.py`, ni `jeu/sim/programme_ia.py`, ni `jeu/sim/MODELE.md`. L'ancienne règle (`route_si_bourg_affame`, `MODELE.md` « Les décisions et les gestes de l'IA ») reste celle du jeu jusqu'au branchement. Le propriétaire a décidé sa disparition (réponse A à #951). Ses tests de `test_intentions.py` gardent leur variante `ancienne` jusque-là.

## Périmètre
jeu/sim/tests/test_monde.py

## Conditions de succès
Ce que le codeur fait, et rien d'autre :
- ligne 4021 : `_REGLES = pytest.mark.parametrize('regle', ['programme'])`. Le paramètre `regle` reste dans les quatre signatures, et l'identifiant `[programme]` reste dans les noms des cas.
- `test_ia_rejeu_octets` et `test_ia_mesure_reelle` : `jours, amorcage = _JOURS_DU_PROGRAMME, _AMORCAGE_PROGRAMME` (et `ticks, amorcage = …` dans le second). Dans le rejeu, la branche `if regle == 'ancienne'` part ; l'assertion `dites and len(dites) == len(routes)` et le `print` restent tels quels, sans condition.
- `test_ia_raisons_egalent_le_monde` : la branche `ancienne` du montage part, avec `PART_COUTUMIERE = 0` et `_verifier_raisons(70)`. Le `with pytest.MonkeyPatch.context() as branche` reste, sans condition. Tout le bloc `if regle == 'ancienne':` des assertions part (les dates figées `[25, 37, 39, 61, 64, 69]` et `[25, 37, 39, 63, 64, 69]` et leurs contre-épreuves). Le corps du `else` reste mot pour mot, désindenté. Le bloc du secours, qui suit, ne change pas.
- `test_service_ia_egal_cli` : la ligne `ticks, amorcage = …` devient `_JOURS_DU_PROGRAMME, _AMORCAGE_PROGRAMME`. Le `if regle == 'programme':` disparaît, et ses trois lignes restent sans condition.
- Aucune autre ligne du fichier ne change. `_brancher_programme`, `_controler_raisons`, `_lire_raison_monde`, `_lire_route_vers_le_champ`, `_verifier_raisons` et `_routes_du_releve` restent tels quels : `test_intentions.py` en importe une partie, et le cas `programme` s'en sert encore comme contre-épreuve (`_controler_raisons(lectures, releve)` sans `champ` doit échouer).

SC1 — Il ne reste que les cas du programme. `cd jeu && python3 -m pytest sim/tests/test_monde.py --collect-only -q -k "rejeu_octets or mesure_reelle or raisons_egalent or service_ia_egal_cli"` liste exactement 5 cas : `test_ia_rejeu_octets[programme]`, `test_ia_mesure_reelle[programme]`, `test_ia_raisons_egalent_le_monde[historique-programme]`, `test_ia_raisons_egalent_le_monde[calibre-programme]` et `test_service_ia_egal_cli[programme]`. Aucun ne porte `ancienne`. De plus, `grep -c "regle == 'ancienne'" sim/tests/test_monde.py` rend 0. Contre-épreuve : sur master, la même collecte liste 10 cas, dont 5 `ancienne`, et le `grep` rend 3.

SC2 — Ces cas restent verts. `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k "rejeu_octets or mesure_reelle or raisons_egalent or service_ia_egal_cli"` passe : 5 cas verts, aucun sauté. Contre-épreuve : on rend `_brancher_programme` sans effet (`return` en première ligne, dans une copie jetée ensuite). Ce qui doit alors rougir, et pourquoi :
- le rejeu : `assert dites and len(dites) == len(routes)` ;
- les deux cas des raisons : `all(… == 'route_vers_le_champ')` ;
- le service : `any(… == 'route_vers_le_champ')`.

La mesure glissante ne lit pas la règle. Elle garde ses contre-épreuves internes : l'ancienne mesure échoue, `verifier([])` échoue, la cellule −1 échoue, la part au jour 29 échoue. Elles restent dans le diff, inchangées.

SC3 — Rien d'autre ne bouge. `cd jeu && python3 -m pytest sim/tests/test_monde.py sim/tests/test_intentions.py -q` passe. Contre-épreuve : renommer `_brancher_programme` casse l'import de `test_intentions.py` (ligne 912) et l'amorçage des sous-processus, et fait échouer cette commande. Dernière vérification : `git diff --name-only origin/master` ne liste que `jeu/sim/tests/test_monde.py` et ce brief, et `git diff origin/master -- jeu/sim/ia.py jeu/sim/programme_ia.py jeu/sim/MODELE.md` est vide.

## Hors périmètre
- Brancher `proposer_route_vers_le_champ` dans `decider_intentions`, retirer `route_si_bourg_affame` de `sim/ia.py` et écrire la règle dans `MODELE.md` : c'est #1000. Au branchement, `_brancher_programme` et `_AMORCAGE_PROGRAMME` deviennent sans effet. Les retirer revient à ce lot-là.
- Les variantes `ancienne` de `test_intentions.py` (`_REGLES_IA`) : elles restent, puisque l'ancienne règle est encore celle du jeu.
- Les autres tests de `test_monde.py` qui jouent la règle par défaut (`test_ia_option_explicitement`, `test_service_ia_raison`, les tests de la forge) : ils ne changent pas.
- `jeu/sim/tests/durees.json` : il est indexé par nom de fonction, sans identifiant de cas, et il ne borne rien.
- Aucune nouvelle mesure : ces cas sont déjà verts sur master.
