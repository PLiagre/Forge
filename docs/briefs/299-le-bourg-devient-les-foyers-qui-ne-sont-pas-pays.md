# Lot #299 — Le bourg devient les foyers qui ne sont pas paysans
Jalon : J4 · Machine : vps · Taille prévue : 200 lignes

## But
La vue du bourg compte les habitants des foyers dont le métier n'est pas « paysans », et les champs comptent le reste. Le bourg que montrent la photographie, la chronique et le tableau devient celui des foyers par métier que le monde fait vivre depuis #297 et #298, et non plus une part recalculée à chaque lecture.

## Règle du monde
Sections de `jeu/sim/MODELE.md` : « Ce qu'est une ville, à l'échelle d'une cellule » (décision B : le bourg est la part des habitants qui ne tire pas sa nourriture des champs, et c'est une vue dérivée, jamais un champ stocké), et « Les foyers par métier » (amorçage A, prorata des plus forts restes). Niveau 2 : plausible, jamais sourcé.

- **Le bourg, c'est les métiers qui ne sont pas paysans.** Pour une cellule dont les métiers sont calculés (`lire_habitants_par_metier(cell)` ne rend pas `-1`), on a `habitants_du_bourg = somme des comptes dont le métier n'est pas constants.METIER_PAYSANS` et `habitants_des_champs = population − habitants_du_bourg`. Tout métier non paysan compte, y compris un métier qui n'existe pas encore dans le moteur : c'est ce que promettait la phrase « le jour où un second métier existera, la vue le comptera sans être réécrite ». Une cellule où personne n'exerce de métier non paysan a un bourg de 0, même si elle porte de riches gisements.
- **Une cellule sans métiers calculés reçoit ceux de l'amorçage.** Une cellule construite sans métiers (lecture `-1`), comme le `Cell` nu de `test_bourg_richesse_ordonne_habitants`, est comptée avec les métiers que l'amorçage A lui donnerait : `mineurs = int(population × part_miniere_de(gisements, facteurs_richesse_extraction()))`, paysans pour le reste. Son bourg reste donc exactement celui d'aujourd'hui. **Une seule fonction porte cette règle** : `metiers_d_amorcage(population, gisements)`, dans `sim/foyers.py`. Elle rend le dictionnaire des métiers dont le compte est strictement positif. `World.charger` (`sim/world.py`, l.215-221 aujourd'hui) et la vue l'appellent toutes deux. Les deux copies actuelles de la formule deviennent une seule.
- **La vue reste une vue.** Elle lit les métiers par `lire_habitants_par_metier` (qui rend une copie), ne modifie rien et n'écrit rien. Le moteur ne l'importe toujours pas. Aucun champ `bourg`/`ville`/`city` n'est créé, et `cell_id` reste la seule clé.
- **Le moteur ne change pas.** L'extraction, la production, la consommation et la distribution intérieure (`engine.py` l.180, 303, 326, 1013) continuent de lire `population × part_miniere_de(...)`. « Le tick ne lit pas les métiers » reste vrai.
- **L'écart se déclare.** À l'amorçage, la vue et le moteur comptent les mêmes personnes. Ensuite, naissances, morts et départs se répartissent entre les métiers au prorata (#298), alors que le moteur relit la part minière. Les deux nombres se séparent. Mesuré le 03/10/2026 sur la graine 0, avec la règle de ce lot : après 1 tick, 10 des 25 cellules minières s'écartent (1 personne au plus) ; après 30 ticks, les 25 (15 personnes au plus). Aucune cellule sans part minière ne s'écarte. MODELE.md le dit : le rang 0 que nourrit la distribution intérieure est la part minière du moteur, pas le bourg de la vue. Les réconcilier, c'est faire lire les métiers par le tick : c'est hors de ce lot.

## Périmètre
jeu/sim/aggregation.py
jeu/sim/foyers.py
jeu/sim/world.py
jeu/sim/MODELE.md
jeu/sim/tests/test_province.py
docs/briefs/299-le-bourg-devient-les-foyers-qui-ne-sont-pas-pays.md

Dans `test_province.py`, on **ajoute** des tests à la fin du fichier, sans en modifier aucun. Aucun test existant de `test_province.py`, de `test_distribution_interieure.py`, de `test_foyers.py` ni de `test_monde.py` ne change.

## Conditions de succès
Toutes les commandes se lancent depuis `jeu/`, au premier plan, bornées par `timeout`. Les nouveaux tests sont ajoutés à la fin de `sim/tests/test_province.py`.

- **SC1 — La vue compte les métiers, pas la part minière.** Commande : `timeout 300 python3 -m pytest sim/tests/test_province.py -q -k "bourg_compte_les_metiers"`. Le test prend les gisements d'une cellule de la carte dont la seule richesse est « majeure » (même échantillon que `test_bourg_richesse_ordonne_habitants`). Il construit trois cellules :
  - `Cell(population=100, habitants_par_metier={"forgerons": 4, "mineurs": 3, "paysans": 93})` : bourg 7, champs 93 ;
  - `{"paysans": 100}` avec ces mêmes gisements : bourg 0, champs 100 ;
  - une cellule amorcée vide (`population=0`, métiers `{}`) : bourg 0, champs 0.

  Pour chaque cellule, il vérifie que bourg + champs = population.
  Contre-épreuve : le test calcule aussi `int(100 × part_miniere_de(gisements majeurs, facteurs))`, l'ancienne règle, et affirme qu'elle ne vaut ni 7 ni 0. La vue d'aujourd'hui rougit donc sur les deux premiers cas. Un échantillon « majeure » vide fait échouer le test.

- **SC2 — Une cellule sans métiers reçoit l'amorçage, par une seule fonction.** Commande : `timeout 300 python3 -m pytest sim/tests/test_province.py sim/tests/test_foyers.py -q -k "bourg or amorcage"`. Pour chaque classe de richesse (échantillon de SC1, une cellule par classe), le nouveau test vérifie `repartition_bourg_de_cellule(Cell(cell_id=1, area_km2=1.0, population=10000), gisements).habitants_du_bourg == foyers.metiers_d_amorcage(10000, gisements).get(METIER_MINEURS, 0) == int(10000 × part_miniere_de(gisements, facteurs))`. Sur `World.charger(0)`, il vérifie aussi que chaque cellule porte exactement `foyers.metiers_d_amorcage(population, gisements de la carte)`.
  Contre-épreuve (dans le test, par `monkeypatch`) : on remplace `foyers.metiers_d_amorcage` par une version qui ajoute un mineur pris aux paysans. Le bourg d'un `Cell` nu **et** les mineurs d'un `World.charger(0)` rechargé changent tous les deux. Une seconde copie de la formule, dans `world.py` ou dans `aggregation.py`, ferait échouer cette contre-épreuve. `test_bourg_richesse_ordonne_habitants`, `test_bourg_sans_gisement_est_toute_campagne` et `test_amorcage` (`bourg == mineurs` au tick 0) restent verts sans retouche.

- **SC3 — Après des ticks, la vue suit les foyers et l'écart se mesure.** Commande : `timeout 300 python3 -m pytest sim/tests/test_province.py -q -s -k "bourg_suit_les_foyers"`. Le test joue `World.charger(0)` pendant 30 ticks avec `random.Random(0)` (environ 4 s). Puis, pour chaque cellule :
  - `habitants_du_bourg` = somme des métiers non paysans ;
  - `habitants_des_champs` = compte des paysans ;
  - bourg + champs = population.

  Il compte ensuite les cellules où le bourg diffère de `int(population × part_miniere_de(...))` et affiche `ecarts_bourg_part_miniere=<n> / <cellules minières>`. Il affirme `n > 0` (on a mesuré 25 / 25) et que toute cellule en écart a une part minière strictement positive. L'écart déclaré dans MODELE.md est donc réel, et limité aux cellules minières.
  Contre-épreuve : `n > 0` signifie que l'ancienne formule ne rend pas le compte des métiers sur au moins une cellule, donc la vue d'aujourd'hui échoue la première assertion. Un monde sans cellule minière fait échouer le test (échantillon vide).

- **SC4 — Le moteur et les tests existants ne bougent pas.** Commandes :
  - `timeout 300 python3 -m pytest sim/tests/test_distribution_interieure.py sim/tests/test_province.py sim/tests/test_foyers.py sim/tests/test_no_hardcoded.py -q` est vert ;
  - `timeout 300 python3 -m pytest sim/tests/test_monde.py -q -k "part_miniere or snapshot_bourg or amorcage"` est vert ;
  - `git diff --name-only origin/master` ne nomme pas `jeu/sim/engine.py` ;
  - `git diff origin/master -- jeu/sim/tests/ | grep -c '^-[^-]'` affiche `0` : on a seulement ajouté des lignes aux tests.

  Ces tests portent leurs propres contre-épreuves, qui restent actives : `test_bourg_une_seule_definition_part_non_agricole` (aucune lecture de `PART_MINIERE_*` dans `aggregation.py`, une seule fonction qui les lit dans `sim/`), `test_bourg_tick_ne_consulte_pas_la_vue`, `test_bourg_aucune_seconde_cle_spatiale` (préfixes `bourg`/`ville`/`city`), `test_bourg_ne_change_pas_sortie_sim`, `test_no_hardcoded_numeric_literals` (aucun littéral hors {0, 1, −1} dans `sim/`) et `test_gardes_et_documentation`.

- **SC5 — MODELE.md dit la nouvelle règle et l'écart.** Commande : `timeout 300 python3 -m pytest sim/tests/test_province.py -q -k "bourg_documente"`. Le nouveau test lit la section « ## Ce qu'est une ville, à l'échelle d'une cellule », jusqu'au prochain `\n## `. Elle doit contenir « paysans », « amorçage », « metiers_d_amorcage », « part_miniere_de » et « écart ». Elle ne doit plus contenir « ne les compte pas encore ». La section « ## La distribution à l'intérieur de la cellule » doit contenir « écart ». Les phrases de « Les foyers par métier » que contrôle `test_foyers.py` restent : TAILLE_FOYER, part_miniere_de, paysans, -1, « le tick ne lit pas les métiers ». La phrase « Extraction et vue du bourg gardent leur calcul de part minière » devient : l'extraction garde le sien, la vue compte les métiers.
  Contre-épreuve dans le test : la section privée du mot « écart » (`replace`) fait lever `AssertionError` par la fonction de contrôle (`pytest.raises`), sur le modèle de `test_documentation` dans `test_foyers.py`.

## Hors périmètre
- Faire lire les métiers par le tick : l'extraction, la production, la consommation et la distribution intérieure gardent `part_miniere_de`. Supprimer l'écart est un autre lot.
- `/lieu`, le contrat avec Unity, les fichiers figés `lieu-graine0-tick{3,4}.json` et `LecteurJsonTests.cs` : c'est le sous-lot 4 de #255, qui a sa propre question.
- Créer un nouveau métier dans le moteur : la vue le compterait, mais ce lot n'en invente aucun.
- Les vues qui lisent le bourg (`snapshot_export.py`, `vues/chronique/capture.py`, `vues/tableau/`, `vues/relief/`) : elles relisent `bourg_depuis_monde` et suivent seules, sans modification.
- Le logement des foyers, les quartiers, l'intégration des villes historiques nommées dans le bourg.
- `engine.py`, `model.py`, `constants.py` : aucun changement.
