# Lot #735 — Le pont lit la ville de 1400 servie
Jalon : J4 · Machine : pc · Taille prévue : 290 lignes

## But
Le pont Unity relit la ville de 1400 que `GET /plan` sert dans son bloc `base` (place, rues, maisons et leurs foyers), refuse tout le plan si ce bloc est mal formé, et déclare la base absente quand le service ne la sert pas.

## Le joueur
Lot de fond, sous-lot 1 de #412 « Unity dessine la ville de 1400 d'après le service ». Il prépare le geste du J4 de `CAP.md` : le joueur **entre dans sa capitale en 3D, la ville de 1400 que tient le monde, pas un décor**. Au Zab, c'est Biskra (cellule 10103) : 33 maisons d'un foyer autour de sa place, et 7 rues vers ses voisines. Après ce lot, le joueur ne voit encore rien de neuf, mais Unity sait lire cette ville telle que le monde la tient. Le sous-lot 3 de #412 (maisons de 1400 posées avec le kit, photo de Biskra) la dessinera ; le sous-lot 4 tracera ses rues.

## Règle du monde
Sans objet : lecture de vue, le monde ne change pas. Le contrat vient de `jeu/sim/MODELE.md`, paragraphe `GET /plan` et section « Le plan de base » (niveau 2, inchangé). `base_de_cellule` (`sim/ville1400.py`) sert `cell_id`, `place` (4 points), `rues` (`points`, `largeur_m`, `sorte` `principale` ou `ruelle`, `vers_cell_id` pour une principale seulement) et `maisons` (`emprise` de 4 points, `foyers` ≥ 1 ; une maison d'îlot en porte plusieurs). Le service met ce bloc en tête de `/plan` (`service.py`, `octets_plan`), constant d'un tick à l'autre. Un bourg sans foyer a zéro maison : c'est une mesure. Unity relit ces valeurs telles quelles, dans l'ordre servi, sans tri, arrondi ni calcul.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientPlan.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/plan-biskra-graine0-tick0.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/plan-biskra-graine0-tick0.json.meta
jeu/sim/tests/test_ville1400.py
docs/briefs/735-le-pont-lit-la-ville-de-1400-servie.md

Tout autre chemin est interdit. Les appelants de `ClientPlan` et de `new PlanLu(…)` (`DesertCityRelance`, `DesertCityRoads`, `DesertRoadTool`, `Lot361`, `Lot362`, `PoseDeBatimentTests`, `TraceDeParcelleTests`) ne sont pas touchés et compilent tels quels.

Ce que fait le code :
- Trois classes en lecture seule, dans le style de `RueDuPlan` : `RueDeBase` (`Points`, `LargeurM`, `Sorte`), `MaisonDeBase` (`Emprise`, `Foyers` en long), `BaseDuPlan` (`Place`, `Rues`, `Maisons`). Une liste ou un texte `null` lève `ArgumentNullException`.
- `PlanLu` gagne `BaseDuPlan Base` et un paramètre facultatif **en dernière position**, `BaseDuPlan @base = null`. `Base == null` déclare la base non servie ; aucune base n'est jamais inventée.
- `ClientPlan.Lire` lit la clé `base`. Absente : plan présent, `Base == null`. Présente : tout doit être bien formé, sinon `CleRefusee` refuse le plan entier en nommant chemin et indice. Exigences : un objet ; `base.cell_id` entier égal au `cell_id` du plan ; `base.place` d'au moins 3 points de exactement 2 nombres ; chaque `base.rues[i]` un objet, `points` d'au moins 2 points, `largeur_m` > 0, `sorte` texte non vide ; chaque `base.maisons[i]` un objet, `emprise` d'au moins 3 points, `foyers` entier ≥ 1 (message « au moins 1 foyer »). `vers_cell_id` n'est ni lu ni exigé.
- Réutiliser `Contour` (un paramètre de minimum est permis), `Tableau`, `Nombre`, `Entier`. Les messages existants (« un entier ≥ 0 », « au moins 3 points », « au moins 2 points ») ne changent pas.
- La fixture : les octets exacts de `GET /plan?cell=10103`, graine 0, tick 0 (4 768 octets, sans saut de ligne final), écrits par `Path.write_bytes` depuis le service. Unity génère son `.meta`.

Budget : 70 lignes de client, 95 de tests C#, 28 de Python, 8 de fixture et `.meta`, ce brief. Écrire serré, dans le style du pont.

## Conditions de succès
Unity, sur le PC, depuis la racine, en PowerShell, sans `-quit` : `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot735.xml" -logFile "$env:TEMP\lot735.log"`. On exige une sortie 0 et un XML neuf, sans échec ni cas ignoré, où chaque cas nouveau de `ClientPlanTests` figure et a été exécuté (zéro cas nouveau est un échec). Python : `py -m pytest jeu/sim/tests/test_ville1400.py -q` (CI : `python3 -m pytest jeu -q`). Écrire les cas d'abord et constater leur rouge.

Un nouveau littéral `PLAN_BASE` sert les SC C# : `PLAN_DEUX_RUES` précédé du bloc base, dans l'ordre de clés du service.
```
"{\"base\":{\"cell_id\":9922,\"maisons\":[{\"emprise\":[[10,10],[15,10],[15,18],[10,18]],\"foyers\":1},{\"emprise\":[[-30,5],[-20,5],[-20,25],[-30,25]],\"foyers\":12}],\"place\":[[-5,-5],[5,-5],[5,5],[-5,5]],\"rues\":[{\"largeur_m\":6,\"points\":[[5,0.5],[60,2.25]],\"sorte\":\"principale\",\"vers_cell_id\":9923},{\"largeur_m\":3.5,\"points\":[[0,5],[-2.5,40]],\"sorte\":\"ruelle\"}]}," + PLAN_DEUX_RUES.Substring(1)
```

**SC1 — La base servie est relue exactement.** `UneBaseServieEstRelueExactement` sur `PLAN_BASE` exige, dans l'ordre : les 4 points de la place ; les 2 rues (points, largeurs 6 et 3.5, sortes `principale` puis `ruelle`) ; les 2 maisons (emprises, foyers 1 puis 12) ; le reste du plan relu comme dans `UnPlanServiEstReluExactement`. Contre-épreuves : un lecteur qui trie, qui saute la ruelle (sans `vers_cell_id`) ou qui met 1 foyer partout rougit.

**SC2 — La vraie Biskra est relue.** `LaBaseDeBiskraServieEstRelue` sert la fixture par `Servir` et lit 10103. Attentes en dur, mesurées sur le service : `Tick == 0` ; 0 rue, 0 parcelle, 0 bâtiment de geste ; place (-50,-50) (50,-50) (50,50) (-50,50) ; 7 rues, toutes `principale`, de largeur 6 ; `rues[0]` = (50.0, 11.428924) → (64.622855, 14.771394) ; `rues[6]` = (50.0, -26.353112) → (63.269689, -33.347063) ; 33 maisons pour 33 foyers ; `maisons[0].Emprise[0]` = (-55.392334, -10.181982) ; `maisons[32].Emprise[2]` = (-63.427086, -48.928937) ; plus grande coordonnée absolue des emprises 69.186409. Contre-épreuve : une fixture d'une autre cellule ou d'un autre tick rougit.

**SC3 — Sans base, le plan est lu et la base déclarée absente.** `UnPlanSansBaseEstLuEtDeclareLaBaseAbsente` sur `PLAN_BOURG` exige `Presente`, `Base == null` et `VerifierBourg` vert. Tous les tests existants de `ClientPlanTests` restent verts, sans une ligne changée. Contre-épreuve : lire `base` par `Valeur` (clé exigée) rougit ce test et tous les anciens.

**SC4 — Une base mal formée refuse tout le plan.** `[TestCase]` d'un nouveau `UneBaseMalFormeeRefuseLePlan`, par `RemplacerUneFois(PLAN_BASE, …)` et `Absence`, qui exige chemin et précision (ancien → nouveau : chemin, précision ; chaque motif ancien paraît une seule fois, vérifié) :
- `"base":{"cell_id":9922,` → `"base":7,"x":{"cell_id":9922,` : `base`, « un objet attendu » ; `"cell_id":9922,"maisons"` → `"cell_id":9923,"maisons"` : `base.cell_id`, « 9923 » ;
- `"place":[` → `"lieu":[` : `clé absente : base.place` ; `"place":[[-5,-5],[5,-5],[5,5],[-5,5]]` → `"place":[[-5,-5],[5,-5]]` : `base.place`, « au moins 3 points » ;
- `"rues":[{"largeur_m":6` → `"voies":[{"largeur_m":6` : `clé absente : base.rues` ; `"points":[[0,5],[-2.5,40]]` → `"points":[[0,5]]` : `base.rues[1].points`, « au moins 2 points » ; `"largeur_m":3.5` → `"largeur_m":0` : `base.rues[1].largeur_m`, « > 0 » ;
- `,"sorte":"ruelle"` → rien : `base.rues[1].sorte`, « clé absente » ; `"sorte":"ruelle"` → `"sorte":""`, puis → `"sorte":3` : `base.rues[1].sorte`, « un texte non vide » ;
- `"maisons":[{` → `"maisons":[7,{` : `base.maisons[0]`, « un objet attendu » ; `"maisons":[{` → `"logis":[{` : `clé absente : base.maisons` ; `[[-30,5],` → `[[-30,5,0],` : `base.maisons[1].emprise[0]`, « exactement 2 nombres » ;
- `"foyers":12` → `"foyers":0` : `base.maisons[1].foyers`, « au moins 1 foyer » ; → `"foyers":1.5` : même chemin, « un entier » ; `,"foyers":12` → rien : même chemin, « clé absente ».

Contre-épreuves : un lecteur qui garde un plan partiel, ou dont le chemin est figé sur `[0]`, rougit.

**SC5 — Sans base, jamais sans liste.** `UneBaseNeSeFabriquePasSansListe` exige : `new PlanLu(1, 0, rues, parcelles, batiments)` compile avec `Base == null` ; le même appel avec une `BaseDuPlan` la rend ; chaque liste `null` des trois classes, et `Sorte` `null`, lève `ArgumentNullException`. Contre-épreuve : un paramètre obligatoire casse la compilation des appelants.

**SC6 — La fixture est la réponse du service (Python).** `test_pont_plan_biskra_fige` dans `test_ville1400.py` lance un `ServeurMonde(("127.0.0.1", 0), 0, 0)` dans un fil, comme `test_plan_service_base_constante_et_calculee_une_fois`. Il exige les octets de `GET /plan?cell=10103` égaux à la fixture, et 33 maisons et 7 rues dans la fixture. Contre-épreuves dans le test : la base de `/plan?cell=1175` diffère de celle de la fixture ; après `POST /tick?n=1`, les octets de 10103 diffèrent de la fixture, mais leur base reste égale.

**SC7 — Aucune base du monde ne serait refusée par le pont (Python).** `test_pont_bases_lisibles(campagne)` : une fonction de contrôle reprend les exigences de SC4 et passe sur les 596 `campagne.bases` (échantillon non vide, plus de 0 maison). Contre-épreuve dans le test : une copie de base où `largeur_m` vaut 0, puis une où `foyers` vaut 0, est rejetée par la fonction.

**SC8 — Périmètre, taille, rien d'assoupli.** `git diff --check` ; `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne nomment que le Périmètre ; `git diff --numstat origin/master` fait moins de 300 lignes en tout, ce brief compris ; `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs jeu/sim/tests/test_ville1400.py` n'a aucune ligne `-`.

## Hors périmètre
- Le service, `ville1400.py`, `MODELE.md` et les autres fixtures.
- `vers_cell_id`, la façade des maisons, la pose de l'îlot : sous-lot 2 de #412.
- Tout dessin : maisons du kit (sous-lot 3), rues en rubans (sous-lot 4) ; tout changement des appelants de `ClientPlan` et des autres clients du pont.

## Photo
Sans objet : ce lot ajoute une lecture au client `/plan` et ses tests, sans rien brancher à une scène. Rien de ce qu'on voit à l'écran ne change. La photo de Biskra et de ses 33 maisons de 1400 viendra au sous-lot 3 de #412, avec son scénario de capture.
