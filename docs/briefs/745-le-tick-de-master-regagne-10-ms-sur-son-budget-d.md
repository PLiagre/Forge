# Lot #745 — Le tick de master regagne 10 ms sur son budget de 100
Jalon : J4 · Machine : vps · Taille prévue : 220 lignes

## But
Le monde de 1400 joue un jour au moins 10 ms plus vite qu'aujourd'hui, et exactement comme aujourd'hui, au bit près, pour que les prochains lots du moteur de J4 aient de la marge sous le budget de 100 ms.

## Le joueur
Rien de neuf à l'écran : c'est un lot de fond. Il prépare deux gestes de J4 qui touchent le moteur : **les sans-logis qui bâtissent sur les parcelles libres** (#414) et **la récolte de chaque lieu** (#723). Aujourd'hui le tick de base fait ~98 ms sur les runners de la CI pour un budget de 100 ms, et chaque lot du moteur tire à pile ou face sur les tests `chronometre` (#414 en est tombé le 16/10). Après ce lot, ces deux lots peuvent entrer sans faire sauter le budget. Le joueur verra alors ses sans-logis bâtir et la moisson de chaque lieu, à la même cadence de dix jours par seconde.

## Règle du monde
Aucune règle ne change. Ce lot ne touche que la manière de calculer. Toutes les sections de `jeu/sim/MODELE.md` restent vraies mot pour mot, et `MODELE.md` ne change pas. Pas de niveau de fidélité en jeu : aucun nombre du monde ne bouge.

**Pourquoi ce lot.** CAP.md, jalon 1, « Quand revenir sur cette décision » : au-delà de 100 ms, *une fois les gains évidents pris*, on porte le moteur en C#. `BUDGET_TICK_MS = 100` dans `jeu/sim/service.py`. Diagnostic du dépanneur sur #414 (16/10, runners de la CI) : `test_ateliers_budget` à 110,5 ms de médiane, `test_departs_budget_comparaison` à 113,7 ms, un tick sans l'étape des départs à 97,8 ms.

**Mesuré par le chef sur master `56f8dfd`, graine 0, VPS (2 cœurs, Python 3.12), le 20/10/2026.** 596 cellules, 1 364 arêtes, 6 619 lieux. Médiane des ticks 5 à 24 de `World.charger(0)` : **87 à 90 ms** au calme. Le VPS est partagé : la même mesure a sauté de 90 à 116 ms d'une course à l'autre. D'où la mesure alternée de SC4. Temps par étape (moyenne par tick, chaque étape enveloppée d'un chronomètre) :

| étape | ms/tick |
|---|---|
| `_apply_commerce` (dont `_initialiser_capacite_aretes` 5,1 ms) | 20,4 |
| `_apply_consumption` (dont `lieux.partager`, ~530 appels par tick) | 19,2 |
| `departs.appliquer_departs` | 10,6 |
| `_apply_production` | 8,6 |
| `prelevement.prelever` | 7,8 |
| `_apply_migration` (dont `_voisins_avec_surplus`) | 6,7 |
| `_apply_natalite` | 4,6 |
| `repartir_sur_les_lieux` | 3,9 |
| fabrication, mortalité, accord de fabrication, extraction, reste | ~10 |

Gains repérés, sans changer un résultat :
- **`_voisins_avec_surplus` balaie les 1 364 arêtes pour chaque cellule qui migre.** C'est le balayage linéaire que nomme CAP.md. Essai jetable (hors du dépôt) : une table `cellule → voisines terrestres`, construite une fois par tick dans `_apply_migration` dans l'ordre de `world.adjacency`, doublons compris. Résultat : migration de 7,4 à 4,7 ms, empreinte des 40 premiers ticks **identique** à master.
- **`_initialiser_capacite_aretes` : 5,1 ms.** Les facteurs de relief des deux bouts ne coûtent que 0,6 ms et les apports de routes 1 ms. Le reste se perd par arête (validation, `_cle_arête`, appels de constantes).
- **La consommation**, à travers `partager` (fractions exactes en entiers) et les tris `sorted(..., key=lambda)` refaits à chaque appel. Le contexte maritime relit aussi les arêtes plusieurs fois par tick.

Le codeur choisit ses gains. Il en faut **au moins 10 ms au total** (SC4). Ce qu'il change, il le change à l'intérieur d'un tick : rien n'est gardé sur `World` d'un tick à l'autre. Des tests ajoutent des arêtes entre deux ticks (`test_index_aretes_premiere_entree_repli_et_tick_suivant`), et des tests changent les constantes par `monkeypatch`.

**Pièges relevés (des tests existants les gardent ; aucun ne se modifie) :**
- `test_index_aretes_premiere_entree_repli_et_tick_suivant` compte les appels de `engine._index_aretes` : **un par tick**. Une nouvelle table de voisines ne passe pas par `_index_aretes`. `_capacite_transport_arete_kg(world, a, b, index=None)` et `_initialiser_capacite_aretes(world)` gardent leur signature. `test_tick_bit_pres_sur_une_annee` les remplace par leurs copies de #331 et compare l'année au bit près.
- `_tick_departs_variante` (test_commerce.py) remplace du texte dans la source de `engine.tick`. Les lignes `    _apply_migration(world, penuries)\n\n    departs.appliquer_departs(world)\n` restent telles quelles.
- `_alterer_fonction(…, '_sortir_par_bourg', …)` exige dans sa source `if manque <= 0 or cell.cell_id not in chemins:` et `    for lieu in lieux[1:]:`.
- `lieux.partager` reste appelé par le module, et seulement quand un partage est nécessaire : des tests le remplacent par `pytest.fail("partage inutile")`. `_apply_consumption` n'appelle ni `_facteur_transport_pour_cellule` ni `lieux_de_cellule` pour une cellule sans mine ou à un seul lieu (`test_capacite_calculs_inutiles_evites`).
- Les maillons restent appelés par leur nom de module : `_apply_commerce`, `_apply_consumption`, `_apply_migration`, `_lieux.repartir_sur_les_lieux`, `departs.appliquer_departs`, `prelevement.prelever`… Des dizaines de tests les remplacent par `monkeypatch`.
- `test_acces_directs_au_panier_hors_modele` interdit tout `.stocks` dans `sim/` hors de `model.py`.

## Périmètre
jeu/sim/engine.py
jeu/sim/lieux.py
jeu/sim/model.py
jeu/sim/tests/test_commerce.py
jeu/sim/tests/test_lieux.py
docs/mesures/745-tick.md

## Conditions de succès
- **SC1 — le même monde, au bit près, sur une année, contre master.** Le codeur écrit `/tmp/empreinte-745.py` (hors du dépôt). Le script : `World.charger(0)`, `rng = random.Random(0)`, puis 365 fois `retour = engine.tick(monde, rng, numero_tick=i)`. Après le chargement puis après chaque tick, il calcule `hashlib.sha256(json.dumps([monde.to_dict(), monde.stocks_mer, retour, rng.getstate()], sort_keys=True).encode()).hexdigest()` et écrit les 366 empreintes, une par ligne, dans le fichier donné en argument. Il le joue sur sa base (`git worktree add /tmp/base-745 $(git merge-base HEAD origin/master)`, puis `cd /tmp/base-745/jeu && python3 /tmp/empreinte-745.py /tmp/avant.txt`) et dans son chantier (`cd jeu && python3 /tmp/empreinte-745.py /tmp/apres.txt`). Ensuite `cmp /tmp/avant.txt /tmp/apres.txt` ne dit rien. Contre-épreuve : avec l'option `--decaler`, le script décale d'un cran (`math.nextafter`) le stock de nourriture du lieu de rang 1 de la première cellule à plusieurs lieux, juste après le tick 100. `cmp` sur ce fichier doit alors rougir, et `diff` doit nommer la ligne 102 (tick 100) comme première différence. Le compte rendu donne la première et la dernière empreinte des deux courses.
- **SC2 — les empreintes forge à 0 et 30 ticks.** Sur la base puis dans le chantier, depuis `jeu/` :
  `python3 -m forge --ticks 0 --seed 0 --sortie /tmp/f0 --sans-chronique`,
  `python3 -m forge --ticks 30 --seed 0 --sortie /tmp/f30 --sans-chronique`,
  `python3 -m forge --ticks 30 --seed 0 --ia --sortie /tmp/f30ia --sans-chronique`.
  Les trois `sha256sum …/monde.json` sont égaux avant et après. Mesuré sur `56f8dfd` : `10c8ddc2…` à 0 tick, `2d93a818…` à 30 ticks sans IA. Si la base a bougé, ses propres valeurs font foi. Contre-épreuve : les empreintes à 0 et à 30 ticks diffèrent entre elles, donc la comparaison n'est pas aveugle. Les tests qui figent déjà le monde passent sans retouche : `cd jeu && python3 -m pytest forge/tests/test_forge.py sim/tests/test_determinisme.py -q` (dont `test_forge_ia_sans`, `test_tick_bit_pres_sur_une_annee`, `test_registre_bit_pres`, `test_grenier_bit_pres`, `test_part_bit_pres`, `test_prelevement_bit_pres`).
- **SC3 — chaque raccourci rend ce que rendait l'ancien chemin.** `cd jeu && python3 -m pytest sim/tests/test_commerce.py sim/tests/test_lieux.py -q -s -k raccourci_745` : un test par fonction que le lot accélère, dans le fichier qui porte déjà ses tests (commerce, migration et arêtes dans `test_commerce.py` ; `partager` et la répartition dans `test_lieux.py`). L'ancien calcul reste appelable, comme `_arete_adjacence(world, a, b, index=None)` après #331 : un paramètre facultatif sans table refait le balayage d'avant. Chaque test compare les deux chemins sur `World.charger(0)` après 5 ticks, pour **toutes** les cellules ou arêtes concernées. Il exige l'égalité exacte (`==` sur les flottants, `is` sur les arêtes, même ordre des clés) et imprime le nombre de cas comparés (> 0). Contre-épreuve dans chaque test : un cas qui ferait mentir un raccourci fautif doit rougir, par exemple une arête doublée ou ajoutée entre deux ticks pour une table de voisines, ou une table gardée d'un tick à l'autre. Le test montre que la variante fautive donne un autre résultat (`pytest.raises(AssertionError)`).
- **SC4 — la marge, mesurée et écrite.** Le codeur écrit `/tmp/mesure-745.py` (hors du dépôt). Le script charge `World.charger(0)`, joue 5 ticks de chauffe, puis mesure 20 ticks par `time.perf_counter`. Il imprime leur médiane, puis, sur une seconde course, le temps moyen par tick de chaque étape de `engine.tick` (chaque maillon enveloppé dans son module, `_apply_commerce` mesuré au seul appel extérieur). Il joue le script **en alternance**, trois fois de chaque côté : base, chantier, base, chantier, base, chantier (dossiers de SC1). Il garde pour chaque côté la plus petite des trois médianes. Exigé : médiane du chantier ≤ médiane de la base − 10 ms, **et** ≤ 0,88 × médiane de la base. Le second seuil compte pour la CI, où le tick est ~12 % plus lent que sur le VPS. `docs/mesures/745-tick.md` donne : le commit de base, la date, les six médianes, la table des étapes avant et après (ms/tick, écart), et une phrase par gain qui dit ce qui coûtait et ce qui a été fait. Si le VPS est chargé (autre lot en cours, écart de plus de 15 % entre deux courses du même côté), le codeur rejoue et le dit.
- **SC5 — les chronomètres passent sans être touchés.** `cd jeu && python3 -m pytest -m chronometre sim/tests/ -q -s` passe : `test_tick_sous_le_budget_du_service`, `test_ateliers_budget`, `test_departs_budget_comparaison`, `test_budget_flux_et_contre_epreuve`, etc., toujours contre `BUDGET_TICK_MS` importé de `sim.service`. Leurs contre-épreuves (un maillon ralenti de `BUDGET_TICK_MS` doit lever `AssertionError`) restent en place et passent. Les médianes imprimées vont dans le compte rendu.
- **SC6 — rien d'autre ne bouge, aucun test ne s'assouplit.** `cd jeu && python3 -m pytest sim/tests/test_commerce.py sim/tests/test_lieux.py sim/tests/test_distribution_interieure.py sim/tests/test_monde.py sim/tests/test_foyers.py sim/tests/test_prelevement.py sim/tests/test_flux.py -q -m "not chronometre"` passe, et la CI entière est verte. `git diff origin/master -U0 -- jeu/sim/tests | grep '^-[^-]'` ne sort rien : on ajoute des lignes de test, on n'en retire ni n'en change aucune. `git diff --stat origin/master` ne montre que des fichiers du périmètre ; `jeu/sim/MODELE.md`, `jeu/sim/service.py` et `jeu/sim/constants.py` n'y sont pas.

## Hors périmètre
- Toute règle du monde : aucun nombre, aucune constante, aucun ordre de maillon ne change ; `MODELE.md` ne change pas.
- `BUDGET_TICK_MS`, `jeu/sim/service.py`, et tout seuil d'un test `chronometre` : le budget se lit, il ne se change pas. Aucun test plus serré (« < 90 ms ») n'est ajouté : la marge rendue est faite pour que #414 et #723 la dépensent.
- `departs.py`, `prelevement.py`, `plan.py` : leurs tests instrumentent la source et l'arbre de leurs fonctions (`test_prelevement.py`, `lire_stock_marchandise` compté par lieu dans `test_commerce.py`). Ce lot les laisse tels quels.
- Garder une table, un index ou un facteur sur `World` d'un tick à l'autre ; changer le format de `world.adjacency` ou de `data/`.
- Les sans-logis qui bâtissent (#414) et la récolte de chaque lieu (#723) ; le portage du moteur en C#.
- Unity et le PC.
