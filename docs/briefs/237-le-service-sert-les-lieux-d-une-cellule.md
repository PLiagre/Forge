# Lot #237 — Le service sert les lieux d'une cellule
Jalon : J3 · Machine : pc · Taille prévue : 210 lignes

## But
Une seule lecture de `GET /lieu?cell=N` rend la cellule et la liste de ses lieux, chacun avec son rang, sa surface, ses habitants et son panier, identique à la photographie au même tick : Unity a sa source pour l'écran du jalon 3, « la cellule découpée en lieux ».

## Règle du monde
Sections de `jeu/sim/MODELE.md` : « Les lieux d'une cellule, vue dérivée », avec « Ce que porte un lieu » (#235) et « L'identité d'un lieu, et ce qui la change » (#234). **Niveau 2** : le découpage et le partage sont plausibles, jamais sourcés. Ce lot n'ajoute aucune règle au monde : il **publie** ce que le monde tient déjà. Le tick, l'amorçage, le partage, `/monde`, `/plan` et le snapshot de la CLI ne changent pas.

Décision du pilote sur la question technique de ce lot (réponse **A**, commentaire de l'issue) : on ajoute `"lieux"` à la liste exacte des clés que vérifie `LecteurJsonTests.cs`, avec de nouvelles vérifications (les 15 lieux de la cellule 9922, leurs rangs, leurs habitants qui font la population), et les deux réponses figées sont réécrites depuis le service. Le test reste aussi strict et vérifie en plus les lieux.

Ce que le service publie :

- **La clé `lieux` de `/lieu`.** Dans `_construire_etat` (`jeu/sim/service.py`), chaque document de `lieux` gagne `"lieux": lieux_en_photographie(cell_id, cellule)`, à côté de `foyers`, `tick` et `date`. `lieux_en_photographie` est importée de `sim.snapshot_export` : c'est **la fonction même** qui remplit `cells[].lieux` de la photographie, pas une copie. Une seule source, donc une seule forme : la liste est rangée par rang, chaque lieu porte exactement `rang`, `surface_km2` (lue de `lieux_de_cellule`), `population` et `stocks` (toutes les marchandises du panier de la cellule, un `0` y est une mesure).
- **Sans arrondi.** La clé s'ajoute **après** `_cellule_legere`, hors de `_round_tree`, comme la photographie qui garde ses lieux non arrondis (« Les restes des lieux gardent leur précision de conservation », `build_snapshot_document`). La somme des paniers des lieux égale donc le panier du monde au bit près ; elle n'égale pas le panier arrondi en tête de la réponse, et aucun test ne doit l'exiger.
- **Aucune seconde clé spatiale.** Un lieu publié ne porte ni `cell_id` recopié, ni `lieu_id`, ni aucun identifiant : son identité est le couple (`cell_id` de la réponse, `rang`). Le `cell_id` que nomme l'issue est celui qui est déjà en tête de la réponse.
- **La même photographie.** Ces octets sont construits dans `EtatPublie`, dans le même appel que `population`, `stocks`, `foyers`, `tick` et `date` : une lecture de `/lieu` donne toute la cellule au même jour et ne consulte pas le monde mutable. `_cellule_legere` ne change pas : `/monde` reste léger, sans `lieux`.
- **Rien n'est deviné.** Une cellule dont les lieux stockés ne correspondent pas au découpage lève `SnapshotExportError` (comportement de `lieux_en_photographie`), que le service laisse remonter : il ne publie jamais une liste inventée. Aucun littéral numérique n'est ajouté à `sim/` (`test_no_hardcoded.py`).
- **Le coût.** Mesuré le 04/10/2026 sur le VPS : pour 596 cellules et 6 619 lieux, `lieux_en_photographie` prend ~17 ms et la sérialisation ~13 ms par publication. Ce temps n'entre pas dans `duree_dernier_tick_ms` (qui ne mesure que `tick()`), mais il ralentit la cadence ; les tests d'horloge (`test_monde.py`, `test_determinisme.py`) doivent rester verts sans être touchés, et le test de SC1 imprime le temps mesuré de `_construire_etat` (mesuré, pas exigé).

Valeurs mesurées le 04/10/2026, graine 0, cellule 9922, par `World.charger(rng_seed=0)` puis `tick(world, random.Random(0), world.ticks_ecoules)` (le chemin du service), lues par `lieux_en_photographie` :
- tick 3 : 15 lieux ; population 109 752 ; bourg (rang 0) 7 404 habitants, `surface_km2` 1066.1257700000006 ; rangs 1 à 5 : 7 313 ; rang 6 : 7 311 ; rangs 7 à 14 : 7 309. Les rangs 1 à 14 ont 1053 km² et des paniers entiers (`72369`, sérialisés sans `.0`) ; le bourg porte les fractions (`"fer":45.890235000000075`).
- tick 4 : population 109 774 ; bourg 7 406 ; rangs 1 à 5 : 7 315 ; rang 6 : 7 313 ; rangs 7 à 14 : 7 310. Les 15 lieux changent entre les deux ticks.

Le fichier figé du tick 3 garde ses octets actuels et gagne, entre `"hunger_ticks":0,` et `"population":109752,`, la clé `"lieux":[{"population":7404,"rang":0,"stocks":{…},"surface_km2":1066.1257700000006},…]`. Ce texte est une prévision : les octets qui font foi sont ceux du service. Les deux fichiers sont **écrits depuis le service** (par exemple avec `lancer_service(0)` et `requete_service` de `test_monde.py`, `/tick?n=3` puis `/tick?n=1`), jamais tapés à la main, sans fin de ligne ajoutée. Leurs `.meta` ne changent pas.

## Périmètre
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/tests/test_monde.py
jeu/ville/README.md
jeu/ville/tests/test_contrat_cell_id.py
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick4.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/LecteurJsonTests.cs
docs/briefs/237-le-service-sert-les-lieux-d-une-cellule.md

Précisions :

- Dans `test_monde.py` et `test_contrat_cell_id.py`, on **ajoute** des tests à la fin du fichier, sans en modifier aucun. `test_service_reponse_figee_du_pont_est_celle_du_service`, `test_service_reponse_figee_du_pont_tick4_est_celle_du_service`, `test_service_lieu_rend_exactement_la_photographie_du_meme_tick` et `test_service_lieu_porte_les_foyers_du_tick` restent tels quels et passent sur les fichiers recréés.
- Dans `LecteurJsonTests.cs`, seul le cas `LaReponseFigeeEstRelueEnEntierSansListeFermee` change, avec l'accord donné par la réponse A. La liste exacte des clés gagne `"lieux"` à sa place triée : `{ "cell_id", "date", "food_deficit_kg", "foyers", "hunger_ticks", "lieux", "population", "stocks", "tick" }`. **Aucune assertion existante n'est retirée ni relâchée.** On ajoute, après celles des foyers, les vérifications de SC4.
- Les autres cas de `LecteurJsonTests.cs` et tout `ClientLieuTests.cs` ne changent pas et doivent rester verts. Vérifié à la lecture : `ClientLieu` lit sa réponse par `LecteurJson.LireObjet` et ignore une clé qu'il ne connaît pas ; `LeTexteFigeCoupeApresStocksEstRefuse` trouvera désormais le premier `"stocks":` dans les lieux, et le texte coupé là reste refusé à sa dernière position ; les remplacements de `"stocks":{` touchent aussi les paniers des lieux sans changer ce que lit le client ; les fragments `"fer":625.890235,` et `"population":109752` n'apparaissent qu'en tête.

## Conditions de succès
Les commandes Python se lancent depuis `jeu/`, au premier plan, bornées par `timeout` (`py` au lieu de `python3` sur le PC). Chaque test imprime ses compteurs ; un échantillon vide échoue ; aucun `cell_id` n'est écrit en dur dans les tests Python (les cellules se choisissent par leurs données).

**SC1 — `/lieu` porte les lieux de la photographie au même tick, pour toutes les cellules.**
Commande : `timeout 900 python3 -m pytest sim/tests/test_monde.py -q -s -k "lieu_porte_les_lieux"`.
Le nouveau test prend `photo = _photographie_cli(tmp_path, 0, 3)` et `photo4 = _photographie_cli(tmp_path, 0, 4)`, lance `lancer_service(0)` et fait `/tick?n=3`. Pour **chaque** cellule de `photo["cells"]`, il lit `/lieu?cell=<cell_id>` et vérifie :
- `lieu["lieux"] == cellule["lieux"]` (égalité exacte des structures relues, sans tolérance) ;
- chaque lieu a exactement les clés `{"population", "rang", "stocks", "surface_km2"}` ;
- les rangs valent `0 … n − 1` avec `n = len(lieux_de_cellule(cid, World.charger(0).cells[cid].area_km2))` (la surface du monde, pas celle, arrondie, de la photographie) ;
- la somme des `population` des lieux vaut `lieu["population"]`.

Il affiche `cellules_controlees=<n> lieux_controles=<m> cellules_a_plusieurs_lieux=<k>` et affirme `n == len(photo["cells"]) > 0` et `k > 0`. Il vérifie que les octets de `/monde` ne contiennent pas `b'"lieux"'`.
Contre-épreuves, dans le même test :
- la cellule témoin est la première (par `cell_id`) dont les lieux diffèrent entre `photo` et `photo4` ; après `/tick?n=1`, ses lieux servis diffèrent de ceux de `photo` et égalent ceux de `photo4`. Un service qui publierait des lieux figés, ou en retard d'un tick, échoue ;
- sur une copie des lieux de la photographie du tick 3, déplacer un habitant d'un lieu peuplé à un autre de la même cellule (total inchangé) rend la comparaison fausse : le contrôle voit un lieu, pas seulement la cellule.

**SC2 — aucune seconde clé spatiale dans `/lieu`.**
Commande : `timeout 600 python3 -m pytest sim/tests/test_monde.py -q -s -k "lieu_sans_seconde_cle"`.
Une fonction du test, `_cles_d_identite(document)`, parcourt la réponse en profondeur et rend les chemins de toutes les clés égales à `id` ou finissant par `_id`. Sur un service neuf (`lancer_service(0)`, tick 0), pour chaque cellule de `/monde`, elle rend exactement `{("cell_id",)}`. Le test affiche `reponses_controlees=<n>` et affirme `n > 0`.
Contre-épreuve, dans le même test : une copie d'une réponse où l'on ajoute `"lieu_id": 0` au premier lieu, puis une autre où l'on ajoute `"cell_id"` au premier lieu, sont chacune vues par la fonction (elle rend un chemin de plus que la tête).

**SC3 — les réponses figées sont celles du service.**
Commande : `timeout 300 python3 -m pytest sim/tests/test_monde.py -q -k "reponse_figee_du_pont"`. Les deux tests existants, inchangés, sont verts sur les fichiers recréés. Puis `grep -c '"lieux":\[{"population":7404,"rang":0,' ../3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json` affiche `1`, et `grep -c '"lieux":\[{"population":7406,"rang":0,' ../3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick4.json` affiche `1`.
Contre-épreuve, faite à la main et dite dans la PR : avec le service modifié, remettre l'ancien fichier du tick 3 (`git show origin/master:3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json`) fait rougir `test_service_reponse_figee_du_pont_est_celle_du_service`. Le fichier recréé le rétablit.

**SC4 — Unity relit la nouvelle réponse figée, clés exactes et lieux de 9922 (PC).**
Dans `LaReponseFigeeEstRelueEnEntierSansListeFermee`, après les assertions des foyers, on ajoute :
- `lieux` est une `List<object>` de 15 éléments ;
- chaque lieu est un objet dont les clés sont exactement `{ "population", "rang", "stocks", "surface_km2" }`, dans cet ordre, et son `rang` vaut son indice (0 à 14) ;
- les clés du panier de chaque lieu sont exactement celles du panier de tête, `{ "fer", "nourriture", "objet" }`, dans cet ordre (un lieu porte toutes les marchandises de sa cellule) ;
- la population du bourg (rang 0) vaut 7404 (`==`, sans tolérance) et sa surface est au moins celle de chaque autre lieu ;
- la somme des `population` des 15 lieux vaut `population` (109752).

Le workflow `unity` (poussée sur la branche) est vert : aucune `error CS`. Puis, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
(sans `-quit`, qui interrompt `-runTests`). Le code de sortie vaut 0 et le XML dit `failed="0"`. Il compte tous les cas de `LecteurJsonTests`, `ClientLieuTests`, `ClientPlanTests`, `ClientIntentionTests` et `PanneauLieuTests` : autant de cas qu'avant, aucun ignoré. `ClientLieuTests`, inchangé, relit les deux fichiers recréés : c'est la preuve que la nouvelle clé ne casse pas le client.
Contre-épreuve, faite à la main et dite dans la PR : remettre l'ancien `lieu-graine0-tick3.json` fait rougir `LaReponseFigeeEstRelueEnEntierSansListeFermee` (la clé `lieux` manque). Écrire `7405` à la place de `7404` pour la population du bourg dans le fichier fait aussi rougir le cas. Le fichier recréé le rétablit.
Garde de non-assouplissement : `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/LecteurJsonTests.cs | grep '^-[^-]'` n'affiche qu'**une** ligne, celle de la liste des clés. Sa remplaçante est identique, à l'insertion de `"lieux", ` près.

**SC5 — le modèle et le contrat de la ville le disent.**
Commande : `timeout 300 python3 -m pytest sim/tests/test_monde.py ville/tests/test_contrat_cell_id.py -q -k "lieux_documentes"`.
- `jeu/sim/MODELE.md` : la sous-section « ### Ce que porte un lieu » gagne un paragraphe : `GET /lieu?cell=X` porte `lieux`, par rang, chacun avec `rang`, `surface_km2`, `population` et `stocks`, lus par `lieux_en_photographie`, la fonction de la photographie, sans arrondi ; ces octets sont construits dans `EtatPublie` avec la photographie du tick ; aucun `cell_id` recopié ni `lieu_id` ; `/monde` ne les porte pas. Le nouveau test de `test_monde.py` lit la sous-section jusqu'au prochain `\n### ` ou `\n## ` et exige `/lieu`, `lieux_en_photographie`, `EtatPublie` et `/monde`.
- `jeu/ville/README.md` : le paragraphe de « ## Ce que ce contrat attend encore » qui annonce le lieu « au jalon 3 » est réécrit : le lieu existe, `GET /lieu?cell=N` porte `lieux` (`rang`, `surface_km2`, `population`, `stocks`), son identité est le couple (`cell_id` de la réponse, `rang`), dérivée, jamais une seconde clé. La phrase « viendra au jalon 3 » disparaît. Le nouveau test de `test_contrat_cell_id.py` lit la section jusqu'au prochain `\n## ` et exige `/lieu`, `lieux`, `rang`, `surface_km2`, `population`, `stocks` et `cell_id`, et l'absence de « viendra au jalon 3 ».
Contre-épreuve dans chaque test : la section privée de `/lieu` (`replace`) fait lever `AssertionError` par la fonction de contrôle (`pytest.raises`). Sur la base, le contrôle du README échoue (la phrase « viendra au jalon 3 » y est).

**SC6 — rien d'autre ne bouge.**
- `timeout 1800 python3 -m pytest sim ville -q` est vert, en particulier `test_determinisme.py` (`/lieu` octet pour octet d'une course à l'autre, horloge à 20 jours/s), les tests d'horloge de `test_monde.py`, `test_lieux.py`, `test_foyers.py`, `test_province.py` et `test_no_hardcoded.py` ;
- `git diff origin/master -- jeu/sim/tests/ jeu/ville/tests/ | grep -c '^-[^-]'` affiche `0` : on a seulement ajouté des lignes aux tests Python ;
- `git diff --name-only origin/master...HEAD` ne nomme que des chemins du périmètre. `snapshot_export.py`, `lieux.py`, `model.py`, `engine.py`, `world.py`, `ClientLieu.cs`, `LecteurJson.cs`, `ClientLieuTests.cs`, les schémas de `jeu/ville/Schemas/` et les asmdef n'apparaissent pas.

## Hors périmètre
- Lire ou montrer les lieux côté Unity (`ClientLieu`, `Lieu`, `PanneauLieu`, une scène) : un lot suivant du jalon J3.
- Le maître et le suzerain d'un lieu, le prélèvement, le transport vers le siège : les lots suivants du J3.
- Ajouter `lieux` à `/monde`, au snapshot, à la chronique, au tableau ou au relief ; une route `/lieu?cell=&rang=` ; un identifiant de lieu sous quelque forme que ce soit.
- Changer l'arrondi de la photographie, la forme de `lieux_en_photographie`, ou `SNAPSHOT_SCHEMA_VERSION`.
- Accélérer le tick ou la publication (#236).
- Le schéma filaire du contrat ville (`jeu/ville/Schemas/`) : seul `README.md` documente `/lieu`.
- Brancher les tests EditMode dans un workflow : ce geste appartient au propriétaire, en mode direct.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
