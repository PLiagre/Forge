# Lot #300 — /lieu sert les foyers par métier
Jalon : J4 · Machine : pc · Taille prévue : 170 lignes

## But
La réponse `GET /lieu?cell=X` du service porte, pour la cellule, ses foyers par métier (personnes et nombre de foyers), lus dans la même photographie publiée que sa population et ses stocks. Unity a ainsi une source pour l'écran du jalon 4, « les foyers du bourg par métier », et les deux réponses figées que relit le pont sont recréées depuis le service.

## Règle du monde
Section de `jeu/sim/MODELE.md` : « Les foyers par métier » (#297, #298, #299). Niveau 2 : la taille du foyer (`TAILLE_FOYER = 5`) est plausible, jamais sourcée. Ce lot n'ajoute aucune règle au monde : il **publie** ce que le monde tient déjà. Le tick, l'amorçage, la vue du bourg, `/monde` et le snapshot ne changent pas.

Décision du pilote sur la question technique de ce lot (réponse **A**, commentaire de l'issue) : on ajoute `foyers` à la liste exacte des clés que vérifie `LecteurJsonTests.cs`, et on recrée les deux réponses figées depuis le service. Le test reste aussi strict, avec en plus les chiffres de la cellule 9922.

Ce que le service publie :

- **La clé `foyers` de `/lieu`.** Une nouvelle fonction de `jeu/sim/service.py`, `_foyers_du_lieu(cellule)`, lit les métiers par `lire_habitants_par_metier(cellule)` (`sim/model.py`). Elle rend, par métier trié par nom, `{"personnes": n, "foyers": ranger_en_foyers(n).nombre}`. Le nombre de foyers compte le dernier foyer incomplet : 10 974 mineurs font 2 195 foyers, pas 2 194. Une cellule dont les métiers ne sont pas calculés (lecture `-1`) publie `"foyers": -1`, jamais un dictionnaire deviné. Une cellule amorcée vide publie `{}`. Aucun littéral numérique n'est ajouté à `sim/` : `test_no_hardcoded.py` reste vert.
- **La même photographie.** `_construire_etat` ajoute `foyers` aux seuls octets de `lieux`, dans le même appel qui construit `population`, `stocks`, `tick` et `date`. Une lecture de `/lieu` donne donc toute la cellule au même tick, et ne consulte pas le monde mutable. `_cellule_legere` ne change pas : `/monde` reste léger, sans `foyers`, et `test_foyers.py::test_serialisation` (qui exige `"foyers"` absent de `_cellule_legere`) reste vert. « Photographie publiée » désigne ici `EtatPublie`, celle du service. Le snapshot de la CLI (`snapshot_export.py`) n'est pas touché.
- **La forme canonique.** Les octets suivent `_serialiser` (clés triées, sans espaces). `foyers` se range entre `food_deficit_kg` et `hunger_ticks`. Les clés de chaque métier sont `foyers` puis `personnes`.

Valeurs mesurées le 03/10/2026, graine 0, cellule 9922, par `World.charger(rng_seed=0)` puis `tick(world, random.Random(0), world.ticks_ecoules)` (le chemin du service) :
- tick 3 : population 109 752 ; mineurs 10 974 personnes / 2 195 foyers ; paysans 98 778 / 19 756 ;
- tick 4 : population 109 774 ; mineurs 10 976 / 2 196 ; paysans 98 798 / 19 760.

Le fichier figé du tick 3 devient donc :
`{"cell_id":9922,"date":{"annee":1400,"jour_de_l_annee":4},"food_deficit_kg":0.0,"foyers":{"mineurs":{"foyers":2195,"personnes":10974},"paysans":{"foyers":19756,"personnes":98778}},"hunger_ticks":0,"population":109752,"stocks":{"fer":625.890235,"nourriture":1086412.323983,"objet":19.415859},"tick":3}`
Ce texte est une prévision. Les octets qui font foi sont ceux du service : les deux fichiers sont **écrits depuis le service** (par exemple avec `lancer_service(0)` et `requete_service` de `test_monde.py`, `/tick?n=3` puis `/tick?n=1`), jamais tapés à la main, sans fin de ligne ajoutée.

## Périmètre
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/tests/test_monde.py
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick4.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/LecteurJsonTests.cs
docs/briefs/300-lieu-sert-les-foyers-par-metier.md

Précisions :

- Dans `test_monde.py`, on **ajoute** des tests à la fin du fichier, sans en modifier aucun. `test_service_reponse_figee_du_pont_est_celle_du_service`, `test_service_reponse_figee_du_pont_tick4_est_celle_du_service` et `test_service_lieu_rend_exactement_la_photographie_du_meme_tick` restent tels quels et passent sur les fichiers recréés.
- Dans `LecteurJsonTests.cs`, seul le cas `LaReponseFigeeEstRelueEnEntierSansListeFermee` change, avec l'accord donné par la réponse A. La liste exacte des clés gagne `"foyers"` à sa place triée : `{ "cell_id", "date", "food_deficit_kg", "foyers", "hunger_ticks", "population", "stocks", "tick" }`. **Aucune assertion existante n'est retirée ni relâchée.** On ajoute, après celles de `stocks` :
  - `foyers` est un objet dont les clés sont exactement `{ "mineurs", "paysans" }`, dans cet ordre ;
  - chaque métier a exactement les clés `{ "foyers", "personnes" }`, dans cet ordre ;
  - les valeurs sont égales (`==`, sans tolérance) : mineurs 10974 personnes, 2195 foyers ; paysans 98778 personnes, 19756 foyers ;
  - la somme des `personnes` vaut `population` (109752).
  Les `.meta` des deux fichiers figés ne changent pas.

## Conditions de succès
Les commandes Python se lancent depuis `jeu/`, au premier plan, bornées par `timeout` (`py` au lieu de `python3` sur le PC).

**SC1 — `/lieu` porte les foyers du tick, pour toutes les cellules.**
Commande : `timeout 600 python3 -m pytest sim/tests/test_monde.py -q -s -k "lieu_porte_les_foyers"`.
Le nouveau test lance `lancer_service(0)`, fait `/tick?n=3`, puis rejoue le même monde dans le processus : `World.charger(rng_seed=0)`, et trois fois `tick(world, rng, world.ticks_ecoules)` avec `rng = random.Random(0)`. Pour **chaque** cellule de `/monde`, il vérifie :
- `lieu["foyers"] == {m: {"personnes": n, "foyers": ranger_en_foyers(n).nombre} for m, n in sorted(world.cells[cid].habitants_par_metier.items())}` ;
- la somme des `personnes` vaut `lieu["population"]` ;
- chaque `personnes` est strictement positif (un métier n'existe que si quelqu'un l'exerce).

Il affiche `cellules_controlees=<n>` et affirme `n == len(monde["cells"]) > 0`. Il vérifie aussi que les octets de `/monde` ne contiennent pas `b'"foyers"'`.
Contre-épreuves, dans le même test :
- un tick de plus (`/tick?n=1`), et les foyers de 9922 ne sont plus ceux du monde rejoué au tick 3. Un service qui publierait des foyers figés, ou en retard d'un tick, échoue ;
- pour 9922 au tick 3, `foyers` des mineurs vaut `ranger_en_foyers(n).nombre` et **diffère** de `n // TAILLE_FOYER`. Un service qui oublierait le dernier foyer incomplet échoue.

**SC2 — des métiers non calculés se déclarent, jamais devinés.**
Commande : `timeout 300 python3 -m pytest sim/tests/test_monde.py -q -k "foyers_du_lieu"`.
Le nouveau test appelle `service._foyers_du_lieu` sur trois cellules :
- `Cell(cell_id=1, area_km2=1.0, population=10)`, construite sans métiers : `-1` ;
- `Cell(cell_id=1, area_km2=1.0, population=0, habitants_par_metier={})` : `{}` ;
- `Cell(cell_id=1, area_km2=1.0, population=8, habitants_par_metier={"mineurs": 3, "paysans": 5})` : `{"mineurs": {"foyers": 1, "personnes": 3}, "paysans": {"foyers": 1, "personnes": 5}}`.

Contre-épreuve : le test affirme que le premier résultat n'est pas un dictionnaire. Une fonction qui retomberait sur l'amorçage ou sur `{"paysans": 10}` échoue.

**SC3 — les réponses figées sont celles du service.**
Commande : `timeout 300 python3 -m pytest sim/tests/test_monde.py -q -k "reponse_figee_du_pont"`. Les deux tests existants, inchangés, sont verts sur les fichiers recréés. Puis `grep -c '"foyers":{"mineurs":{"foyers":2195,"personnes":10974}' ../3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json` affiche `1`, et `grep -c '"foyers":{"mineurs":{"foyers":2196,"personnes":10976}' …/lieu-graine0-tick4.json` affiche `1`.
Contre-épreuve, faite à la main et dite dans la PR : avec le service modifié, remettre l'ancien fichier du tick 3 (`git show origin/master:3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json`) fait rougir `test_service_reponse_figee_du_pont_est_celle_du_service`. Le fichier recréé le rétablit.

**SC4 — Unity relit la nouvelle réponse figée, clés exactes et chiffres de 9922 (PC).**
Le workflow `unity` (poussée sur la branche) est vert : aucune `error CS`. Puis, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
(sans `-quit`, qui interrompt `-runTests`). Le code de sortie vaut 0 et le XML dit `failed="0"`. Il compte tous les cas de `LecteurJsonTests`, `ClientLieuTests`, `ClientPlanTests`, `ClientIntentionTests` et `PanneauLieuTests` : autant de cas qu'avant, aucun ignoré. `ClientLieuTests`, inchangé, relit les deux fichiers recréés : c'est la preuve que la nouvelle clé ne casse pas le client.
Contre-épreuve, faite à la main et dite dans la PR : remettre l'ancien `lieu-graine0-tick3.json` fait rougir `LaReponseFigeeEstRelueEnEntierSansListeFermee` (la clé `foyers` manque). Écrire `2194` à la place de `2195` dans le fichier fait aussi rougir le cas. Le fichier recréé le rétablit.
Garde de non-assouplissement : `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/LecteurJsonTests.cs | grep '^-[^-]'` n'affiche qu'**une** ligne, celle de la liste des clés. Sa remplaçante est identique, à l'insertion de `"foyers", ` près.

**SC5 — MODELE.md dit ce que publie `/lieu`.**
Commande : `timeout 300 python3 -m pytest sim/tests/test_monde.py sim/tests/test_foyers.py -q -k "lieu_documente or gardes_et_documentation"`.
Dans « ## Les foyers par métier », un paragraphe ajouté dit que `GET /lieu?cell=X` porte `foyers` : par métier, `personnes` et le nombre de `foyers`, dernier foyer incomplet compris. Il dit aussi `-1` quand les métiers ne sont pas calculés, que ces octets sont construits dans `EtatPublie` avec la photographie du tick, et que `/monde` ne les porte pas. Dans « ## Le plan du bourg », la phrase « `/monde`, `/lieu` et le snapshot restent inchangés » devient : le plan ne s'ajoute ni à `/monde`, ni à `/lieu`, ni au snapshot.
Le nouveau test lit la section « ## Les foyers par métier » jusqu'au prochain `\n## `. Elle doit contenir `/lieu`, `personnes`, `EtatPublie` et `/monde`. Les phrases que contrôle `test_gardes_et_documentation` restent : TAILLE_FOYER, part_miniere_de, paysans, -1, « le tick ne lit pas les métiers ».
Contre-épreuve dans le test : la section privée de `/lieu` (`replace`) fait lever `AssertionError` par la fonction de contrôle (`pytest.raises`), sur le modèle de `test_documentation` dans `test_foyers.py`.

**SC6 — rien d'autre ne bouge.**
- `timeout 900 python3 -m pytest sim -q` est vert, en particulier `test_determinisme.py` (`/lieu` octet pour octet d'une course à l'autre), `test_foyers.py`, `test_province.py`, `test_no_hardcoded.py` et `test_intentions.py` ;
- `git diff origin/master -- jeu/sim/tests/ | grep -c '^-[^-]'` affiche `0` : on a seulement ajouté des lignes aux tests Python ;
- `git diff --name-only origin/master...HEAD` ne nomme que des chemins du périmètre. `engine.py`, `model.py`, `foyers.py`, `snapshot_export.py`, `ClientLieu.cs`, `LecteurJson.cs`, `ClientLieuTests.cs` et les asmdef n'apparaissent pas.

## Hors périmètre
- Lire les foyers côté Unity (`ClientLieu`, `Lieu`, `PanneauLieu`) ou les afficher dans une scène : c'est un lot suivant du jalon J4.
- Ajouter `foyers` à `/monde`, au snapshot de la CLI, à la chronique, au tableau ou au relief.
- Une route `/foyers?cell=` séparée : c'était la réponse B, écartée.
- Le logement des foyers, les quartiers, un nouveau métier, faire lire les métiers par le tick, réduire l'écart entre le bourg de la vue et la part minière du moteur (#299).
- Toute modification de `engine.py`, `model.py`, `foyers.py`, `world.py`, `aggregation.py`, `constants.py`, du contrat ville (`jeu/ville/`) et des autres tests de `Forge.Pont.Tests`.
- Brancher les tests EditMode dans un workflow : ce geste appartient au propriétaire, en mode direct.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
