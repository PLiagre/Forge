# Lot #1010 — Les tests des intentions ne jouent plus l'ancienne règle des routes
Jalon : J5 · Machine : vps · Taille prévue : 180 lignes

## But
Les onze tests de `test_intentions.py` paramétrés par `_REGLES_IA` ne se jouent plus qu'avec la route vers le champ du programme. Le branchement du programme dans `decider_intentions` n'aura plus à les toucher.

## Le joueur
Le joueur n'y voit rien. C'est un lot de fond du geste du jalon 5 « regarder le monde vivre, puis s'en méfier ou s'en servir ». Sur la carte, les maisons de l'IA tracent leurs routes vers leur champ le plus plein, « pour des raisons qu'elles disent ». Ce lot prépare le branchement de cette route (#1000, dont il est découpé, après #1009 qui a fait de même pour `test_monde.py`). Après lui, le service et la forge rendront la route visible ; puis #428 servira ses raisons, et #322 et #429 les montreront sur la carte.

## Règle du monde
Sans objet : c'est un lot d'outil. Il ne change ni le monde, ni `jeu/sim/ia.py`, ni `jeu/sim/programme_ia.py`, ni `jeu/sim/MODELE.md`. L'ancienne règle (`route_si_bourg_affame`, section « Les décisions et les gestes de l'IA » de `MODELE.md`) reste celle du jeu jusqu'au branchement. Le propriétaire a décidé qu'elle disparaîtrait (réponse A à #951).

## Périmètre
jeu/sim/tests/test_intentions.py

## Conditions de succès
Ce que le codeur fait, et rien d'autre (les numéros de ligne sont ceux de master, 23d58d38) :
- ligne 898 : `_REGLES_IA = pytest.mark.parametrize('regle', ['programme'])`. Le paramètre `regle` reste dans les onze signatures, et `programme` reste dans les identifiants des cas. Ligne 899 : `_REGLE_DES_ROUTES = {'programme': 'route_vers_le_champ'}`.
- `_ia_monde` ne change pas : `test_ia_lecture_refus_avant_depot` l'appelle encore sans règle (`regle=None`), donc le `if regle == 'programme':` y reste.
- `test_ia_lecture_locale` : chaque dictionnaire `attendu` devient sa valeur `programme` (`False, True, False, True`), et `attendu[regle]` devient `attendu`.
- `test_ia_registre_choix` : les deux lignes `if regle == 'ancienne': test_ia_budget_annuel_et_branches(…)` partent.
- `test_ia_budget_annuel_et_branches` : le `if regle == 'programme':` disparaît, et son corps reste sans condition. `proposants` ne garde que `_routes_de(ia.decider_intentions(monde, []))`. Tout le bloc `if regle == 'ancienne':` (le budget annuel, jusqu'à son `return`) part. La variable `ancienne = ia.decider_intentions` et la contre-épreuve qui la lit restent : elles sont dans le cas `programme`.
- `test_ia_depot_commun_et_copies` : les points figés `[[0, 0], [40, 0]]` et leur `if` partent.
- `test_ia_raison_lue` : la ligne 1150 compare à `'route_vers_le_champ'`. Les deux `if regle == 'ancienne': … else:` partent, et le corps des `else` reste mot pour mot, désindenté. La fonction `lire()` ne change pas.
- `test_ia_refus_compte_pour_l_annee` : rien ne change (il n'a pas de branche ; sa fonction `ancienne` parle de la mesure, pas des routes).
- `test_ia_base_route_avant_depot` : les deux `if regle == 'ancienne':` et leurs points figés partent.
- `test_an_ia_sans_refus` : il lit `request.getfixturevalue('annee_programme')`. Le `if regle == 'programme':` disparaît, et son corps reste sans condition, sans le `return`. Tout ce qui suivait ce `return` (l'épreuve des treize rues sur `annee_ia`) part, avec l'import de `Rue` devenu inutile.
- `test_terres_ia` : `maison = next(…)`, sans la branche `maisons[0]`. `monkeypatch.undo()` reste avant `getfixturevalue('annee_programme')`, sinon les sondes du montage fausseraient l'année si elle est jouée ici la première fois. Le `if regle == 'programme':` disparaît, et son corps reste sans condition, sans le `return`. Partent : la ligne `original = ia.recevoir_intention`, la fonction `recevoir`, la boucle des 365 jours et sa vérification, qui ne servaient qu'à l'ancienne règle. Les affectations `monde, releve, depots = World.charger(0), [], []` partent aussi : le cas programme les remplace.
- `test_ia_budget_routes_seules` : `maison = next(…)`, et la ligne 2127 devient `assert routes([route_du(t - fenetre)])`.
- `test_ia_grenier_decision` : `_brancher_programme(monkeypatch)` sans condition. Les deux listes de types deviennent `['ouvrir_grenier', 'fixer_part']` et `['ouvrir_grenier']`. La ligne 2462 devient `assert _routes_de(ia.decider_intentions(reel, []), couple) == []`. Le `if regle == 'programme':` final disparaît, et son corps reste sans condition.
- Les commentaires qui opposaient les deux règles (lignes 1496, 2126, 2454) ne disent plus que celle du programme. La docstring de `_ia_monde` et le commentaire de la ligne 1062 restent.
- **La fixture `annee_ia` reste**, contrairement à ce que dit l'issue : `test_ia_part_sur_un_an` (ligne 2176), qui contrôle la part sur un an et n'est pas dans la liste, la lit. La retirer forcerait à réécrire ce test. Elle joue la règle par défaut du jeu : au branchement (#1000), elle jouera le programme d'elle-même.
- Aucune autre ligne du fichier ne change.

SC1 — Il ne reste que les cas du programme. `cd jeu && python3 -m pytest sim/tests/test_intentions.py --collect-only -q | grep -c ancienne` rend 0. `python3 -m pytest sim/tests/test_intentions.py --collect-only -q | grep -c programme` rend 15 : 4 `test_ia_lecture_locale`, 2 `test_ia_base_route_avant_depot`, et un cas pour chacun des neuf autres. Enfin, `grep -c "'ancienne'" sim/tests/test_intentions.py` rend 0. Contre-épreuve : sur master, la première commande rend 15, la deuxième 15 et le `grep` 20.

SC2 — Ces cas restent verts. `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k "lecture_locale or registre_choix or budget_annuel or depot_commun or raison_lue or refus_compte or base_route_avant_depot or an_ia_sans_refus or terres_ia or budget_routes_seules or grenier_decision"` passe : 15 cas verts, aucun sauté. Contre-épreuve : on rend `_brancher_programme` (dans `sim/tests/test_monde.py`) sans effet, avec un `return` en première ligne, dans une copie jetée ensuite. Les 15 cas doivent alors rougir :
- les quatorze qui passent par `_ia_monde(…, regle)` : l'assertion `regles == {_REGLE_DES_ROUTES[regle]}` voit `route_si_bourg_affame`. C'est le cas aussi de `test_ia_grenier_decision`, à son second montage ;
- `test_an_ia_sans_refus` : `annee_programme` n'a plus de `route_vers_le_champ`, donc `any(… == 'route_vers_le_champ')` échoue.

SC3 — Rien d'autre ne bouge. `cd jeu && python3 -m pytest sim/tests/test_intentions.py sim/tests/test_monde.py sim/tests/test_programme_ia.py -q` passe, `test_ia_part_sur_un_an` compris. Contre-épreuve : dans une copie jetée ensuite, on retire la fixture `annee_ia`, comme l'issue le disait ; `test_ia_part_sur_un_an` tombe en erreur (« fixture 'annee_ia' not found »). Dernière vérification : `git diff --name-only origin/master` ne liste que `jeu/sim/tests/test_intentions.py` et ce brief, et `git diff origin/master -- jeu/sim/ia.py jeu/sim/programme_ia.py jeu/sim/MODELE.md jeu/sim/tests/test_monde.py` est vide.

## Hors périmètre
- Brancher `proposer_route_vers_le_champ` dans `decider_intentions`, retirer `route_si_bourg_affame` de `sim/ia.py` et écrire la règle dans `MODELE.md` : c'est #1000. Au branchement, `_brancher_programme` n'aura plus d'effet, et `annee_ia` jouera la même année qu'`annee_programme`. Les fondre et retirer `_brancher_programme` reviendra à ce lot-là, comme la contre-épreuve `ancienne(monde, releve)` de `test_ia_budget_annuel_et_branches`.
- `test_ia_part_sur_un_an`, `annee_ia`, `test_ia_lecture_refus_avant_depot` et les autres tests sans `_REGLES_IA` : ils ne changent pas.
- `sim/tests/test_monde.py` (fait par #1009), `sim/tests/test_programme_ia.py` et `sim/ia.py` : ils ne changent pas.
- `jeu/sim/tests/durees.json` : il ne borne rien, et ses identifiants de cas sont déjà anciens.
- Aucune nouvelle mesure : ces cas sont déjà verts sur master.
