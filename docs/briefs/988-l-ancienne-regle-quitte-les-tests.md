# Lot #988 — L'ancienne règle quitte les tests
Jalon : J5 · Machine : vps · Taille prévue : 110 lignes

## But
Plus aucun test ni aucun juge de `jeu/` ne nomme `route_si_bourg_affame` : chaque route de l'IA est relue contre la seule règle du jeu, la route vers le champ, et toutes les contre-épreuves restent.

## Le joueur
Le joueur n'y voit rien. C'est un lot de fond du geste du jalon 5 « regarder le monde vivre, puis s'en méfier ou s'en servir ». Sur la carte, les maisons de l'IA tracent leurs routes vers leur champ le plus plein, et chaque geste porte sa raison. Depuis #1011, le programme décide ces routes. Ce lot ferme le chantier de #973 (dont il est découpé, après #987) : les juges ne savent plus relire que cette raison. Une route qui porterait une autre règle les ferait rougir au lieu de passer par une lecture morte. Le joueur verra ces raisons dans le service avec #428, puis sur la carte avec #322 et #429. #1012 les écrit déjà en phrases dans « Autres maisons ».

## Règle du monde
Sans objet : c'est un lot d'outil. Le jeu, `jeu/sim/ia.py`, `jeu/sim/programme_ia.py` et `jeu/sim/MODELE.md` ne changent pas. La règle relue est celle de `MODELE.md`, « Les décisions et les gestes de l'IA » : `regle` vaut `route_vers_le_champ` pour une route. `route_si_bourg_affame` a quitté le code avec #1011, et le propriétaire a décidé sa disparition (réponse A à #951). Aujourd'hui, seuls les tests la nomment encore : 4 lignes de `test_monde.py` (3759, 4099, 4199, 4474) et 2 de `test_intentions.py` (2190, 2197).

## Périmètre
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_intentions.py

## Conditions de succès
Ce que le codeur fait (numéros de ligne de la base f7ce59b9) :

Dans `jeu/sim/tests/test_monde.py` :
- **`_lire_raison_monde` (3741–3774) disparaît.** C'est la lecture de l'ancienne raison. Sa seule autre lectrice est `test_ia_raison_lue` (voir plus bas).
- **`_controler_raisons(releve, champ)`** (3777) perd son paramètre `lectures` et sa branche `else`. Pour chaque `tracer_route`, il exige `'raison' in entree`, `entree['raison']['regle'] == 'route_vers_le_champ'`, une lecture `champ[tick][couple]` présente, et `entree['raison'] == lecture`. Il garde `assert routes`. Une route d'une autre règle échoue donc, au lieu d'être comparée à l'ancienne lecture.
- **`_verifier_raisons`** (3926) : `lectures` et le dictionnaire calculé dans `enveloppe` partent, ainsi que `_verifier_raisons.lectures`. `enveloppe` ne lit plus que les secours, avant `reel(monde, rng, numero)`. `lectures_champ`, `.secours` et `.champ` ne changent pas. L'appel devient `_controler_raisons(releve, lectures_champ)`.
- **`test_ia_raisons_egalent_le_monde`** (4073) : `champ = _verifier_raisons.champ`, et chaque appel prend la nouvelle signature. La contre-épreuve `regle_ancienne` devient `autre_regle`, qui pose `raison['regle'] = 'secours_apres_faim'`, une vraie règle du jeu, mais pas celle d'une route. Elle reste dans la boucle des quatre fausses raisons. `_controler_raisons(lectures, releve)`, appelé sans le champ, devient `_controler_raisons(releve, {})` et doit toujours échouer. Les autres contre-épreuves restent telles quelles : raison retirée, parts seules, relevé vide.
- **`test_ia_route_vers_le_champ_relue`** (4199) : la fausse raison `'règle'` devient `{'regle': 'secours_apres_faim'}`, et rien d'autre ne change.
- **`test_snapshot_ia_raison_et_refus`** (4466) : la raison écrite à la main prend la forme de la nouvelle. Ses clés sont exactement celles de `programme_ia.py` (lignes 127–137) : `regle: 'route_vers_le_champ'`, `grenier_nourriture_kg`, `reserve_voulue_kg`, `journees`, `cout_kg`, `faim_du_bourg_ticks`, `champs_nourriture_kg` (liste), `champ_vise` et `ecart_degres`. Les valeurs sont libres et non arrondies, et l'une d'elles dépend de `a.id` (comme `population` aujourd'hui). Le reste du test ne change pas : deux entrées, refus « pont coupé », contre-épreuves `raison` et `refus`.
- **`test_service_ia_raison`** (4846) : le service tourne toujours 31 ticks, et son relevé ne porte alors que trois parts (mesuré : `fixer_part` ×3 au tick 30, aucune route). `verifier` exige en plus que chaque raison porte la règle de son geste. La table s'écrit dans le test : `tracer_route` → `route_vers_le_champ`, `fixer_part` → `part_sur_projets_et_gens`, `ouvrir_grenier` → `secours_apres_faim`. Deux cas écrits à la main s'ajoutent au relevé lu. Le premier copie la première entrée et en fait une `tracer_route` qui porte une raison `route_vers_le_champ` : `verifier` l'accepte. Le second fait la même route avec la raison `part_sur_projets_et_gens` : `verifier` lève `AssertionError`. La contre-épreuve « raison retirée » reste. Les vraies routes du service sont déjà relues par `test_service_ia_egal_cli`, sur 100 ticks : ce lot n'y touche pas.

Dans `jeu/sim/tests/test_intentions.py` :
- **`test_ia_raison_lue`** (1085) : `_lire_raison_monde` n'est plus importé. `lire()` rend `_lire_route_vers_le_champ(monde, maison, proposition['intention'])`, sans condition : la branche de l'ancienne règle n'était jamais prise, puisque le test exige `attendue['regle'] == 'route_vers_le_champ'`. Toutes les contre-épreuves `eprouver` restent.
- **`test_ia_route_documentation`** (≈ 2181) : l'assertion `'route_si_bourg_affame' not in section` part. Une plus large la remplace : chaque mot en `snake_case` de la section (`re.findall(r'\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b', section)`, entre accents graves ou non) figure dans le texte de `jeu/sim/*.py`, tests exclus. Elle attrape l'ancienne règle comme tout autre nom mort. Mesuré sur la base : 47 mots, tous présents. La contre-épreuve `ancienne` devient `disparue` : elle insère `'\nregle_disparue'` sous le titre et doit lever `AssertionError`. La contre-épreuve « section absente » reste. `import re` se fait dans le test.

SC1 — Le nom a disparu. `grep -rn "route_si_bourg_affame\|_lire_raison_monde" jeu/` ne rend rien, et son code de sortie est 1. Contre-épreuve : sur la base, la même commande rend 10 lignes : 6 avec `route_si_bourg_affame`, 4 avec `_lire_raison_monde`.

SC2 — Le juge des raisons ne relit que la route vers le champ. `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k "raisons_egalent or route_vers_le_champ_relue"` passe : 3 cas verts, aucun sauté. Contre-épreuve, dans une copie jetée ensuite : on ajoute à `_controler_raisons` la ligne `if entree['raison'].get('regle') != 'route_vers_le_champ': continue` (une route d'une autre règle passerait sans être relue). La contre-épreuve `autre_regle` ne lève plus, et les deux cas `test_ia_raisons_egalent_le_monde` rougissent.

SC3 — La raison lue et la règle écrite. `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k "raison_lue or route_documentation"` passe. Contre-épreuve, dans une copie jetée ensuite : on ajoute ``La route suit aussi `route_si_bourg_affame`.`` à la section « Les décisions et les gestes de l'IA » de `MODELE.md`. `test_ia_route_documentation` rougit : le nom ne figure plus dans `jeu/sim/*.py`.

SC4 — Les cas écrits à la main portent la nouvelle raison. `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k "snapshot_ia_raison_et_refus or service_ia_raison"` passe, et `grep -n "'route_vers_le_champ'" sim/tests/test_monde.py` montre une ligne dans chacun des deux tests. Contre-épreuve, dans une copie jetée ensuite : on retire de `verifier` (dans `test_service_ia_raison`) la vérification de la règle par geste. La route qui porte une raison de part passe, son `pytest.raises` échoue, et le test rougit.

SC5 — Aucun test n'est assoupli, et rien d'autre ne bouge. `grep -c "pytest.raises" jeu/sim/tests/test_monde.py jeu/sim/tests/test_intentions.py` rend au moins 124 et 88 (base : 123 et 88). Les contre-épreuves sont remplacées une pour une, et le service en gagne une. `cd jeu && python3 -m pytest sim/tests/test_monde.py sim/tests/test_intentions.py -q` passe. `git diff --name-only origin/master` ne liste que les deux fichiers du périmètre et ce brief. `git diff origin/master -- jeu/sim/ia.py jeu/sim/programme_ia.py jeu/sim/MODELE.md` est vide. Contre-épreuve : sur la base, un compte de `pytest.raises` amputé de la contre-épreuve `regle_ancienne`, sans remplaçante, tomberait à 122 et ferait échouer le premier contrôle.

## Hors périmètre
- Unity. `3d/unity/Assets/Interface/DossierVoisins.cs` sait encore écrire la raison `route_si_bourg_affame` (ligne 92), et `DossierVoisinsTests.cs` la joue (ligne 10). `ForgeCapture.cs` (ligne 65, `-forgeServiceProgramme`) appelle encore `t._brancher_programme`, que #1011 a retiré de `test_monde.py`. Le nettoyage des deux et la capture de #1012 reviennent à un lot pc à créer : ce lot est vps et ne touche pas `3d/`.
- `jeu/sim/ia.py`, `jeu/sim/programme_ia.py`, `jeu/sim/MODELE.md` : déjà sans l'ancienne règle depuis #1011.
- La fusion des fixtures `annee_ia` et `annee_programme` de `test_intentions.py`, et le paramètre `regle` de `_REGLES` / `_REGLES_IA` (réduit à `['programme']`) : ils ne nomment pas l'ancienne règle, et ce lot ne les touche pas.
- `docs/briefs/` : les anciens briefs gardent leur texte d'époque.
- `jeu/sim/tests/durees.json` : indexé par nom de fonction, il ne borne rien, et aucun nom de test ne change.
