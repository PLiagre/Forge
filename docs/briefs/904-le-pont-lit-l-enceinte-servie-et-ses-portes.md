# Lot #904 — Le pont lit l'enceinte servie et ses portes
Jalon : J4 · Machine : pc · Taille prévue : 265 lignes

## But
Le pont Unity relit l'enceinte et les portes que `GET /plan` sert, accepte un chantier du jour de nature `enceinte`, et refuse une clé mal formée en la nommant : une capitale murée en chantier s'ouvre encore dans Unity.

## Le joueur
Lot de fond, découpé de #417 « L'enceinte se dessine, et ses portes s'ouvrent sur les rues ». Il prépare le geste du J4 de `CAP.md` : le joueur **trace son enceinte**. Il ne voit encore ni le mur ni les portes, mais une capitale murée en chantier ne casse plus la lecture de la ville. Aujourd'hui, une enceinte en chantier à Biskra fait servir chaque jour une ligne `{"nature":"enceinte",…}` dans `chantiers_du_jour`. `ClientPlan` refuse alors tout le plan (`ClientPlan.cs` l.333), et la ville reste vide avec « Pas de plan pour la cellule 10103 : … reçu le texte "enceinte" ». Après ce lot, Biskra s'ouvre avec ses 33 maisons, ses 7 rues et sa route en chantier, et Unity tient le contour du mur et ses portes. Le sous-lot de #417 qui dessine le mur et ses portes lira `PlanLu.Enceinte` et `PlanLu.Portes`.

## Règle du monde
Sans objet : lecture de vue, le monde ne change pas. Contrat : `jeu/sim/MODELE.md`, section « Le plan du bourg » (niveau 2, inchangé). `enceinte`, au plus une et omise sans enceinte, porte `contour` (≥ 3 points, bouclé), `en_chantier`, `foyers`, `travail_requis` et `travail_fourni`, cohérents comme un chantier. `portes` n'est publiée qu'avec une enceinte. Chaque porte a `point` [x, y], `rue` (`"plan"` ou `"base"`), `identifiant` (celui d'une rue du plan, ou le rang dans `base.rues`) et `largeur_m`. La ligne d'enceinte du relevé a l'identifiant `0` et vient après les bâtiments.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientPlan.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/plan-biskra-enceinte-graine0-tick3.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/plan-biskra-enceinte-graine0-tick3.json.meta
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot904.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot904.cs.meta
jeu/sim/tests/test_epreuve_enceinte.py
docs/briefs/904-le-pont-lit-l-enceinte-servie-et-ses-portes.md

Tout autre chemin est interdit. Les appelants de `new PlanLu(…)` (`Lot779`, `Lot780`, `Lot788`, les tests du pont) compilent sans être touchés.

Ce que fait le code, serré comme `Base()` :
- `EnceinteDuPlan` (`Contour`, `EnChantier`, `Foyers`, `TravailRequis`, `TravailFourni`) et `PorteDuPlan` (`Point`, `Rue` texte, `Identifiant`, `LargeurM`). Un contour ou une `Rue` `null` lève `ArgumentNullException`.
- `PlanLu` gagne `Enceinte` (`null` : aucune) et `Portes` (en lecture seule, vide sans enceinte), par deux paramètres facultatifs après `absenceDesChantiersDuJour` : `EnceinteDuPlan enceinte = null, IList<PorteDuPlan> portes = null`.
- `Lire`, après les rues et la base, avec `Objet`, `Contour`, `Chantier`, `Entier`, `Nombre` et `Valeur`. `enceinte` absente : `portes` doit l'être aussi, sinon « clé portes : des portes sans enceinte ». `enceinte` présente : un objet (null refusé), contour ≥ 3 points, `Chantier(...)`, `foyers` entier ≥ 0, et `portes` exigée. Chaque `portes[i]` : un objet ; `point` de exactement 2 nombres ; `rue` « plan ou base » ; `largeur_m` > 0 ; `identifiant` entier ≥ 0, qui nomme une rue du plan, en chantier ou non (« aucune rue N dans ce plan »), ou un rang < `Base.Rues.Count`, 0 sans base (« aucune rue de base N dans ce plan »). Aucune géométrie recalculée : `sim/portes.py` contrôle déjà.
- `ChantiersDuJour` accepte `enceinte`, et le message devient « rue, parcelle, batiment ou enceinte attendu ».
- La fixture : les octets exacts de `GET /plan?cell=10103` (5 296 octets, sans saut de ligne final), écrits par `Path.write_bytes`. Service à graine 0, vitesse 0 : `choisir_depart` (Zab, par `charger_seigneuries`), un tick, `ROUTE` et `ENCEINTE` de `test_epreuve_enceinte.py`, deux ticks. Unity génère son `.meta`.

Budget : 60 lignes de client, 55 de tests C#, 20 de Python, 8 de fixture et `.meta`, 40 de capture, ce brief.

## Conditions de succès
Unity, sur le PC, depuis la racine : `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot904.xml" -logFile "$env:TEMP\lot904.log"`. Sortie 0, XML neuf sans échec ni cas ignoré, chaque cas nouveau exécuté (zéro cas nouveau est un échec). Python : `py -m pytest jeu/sim/tests/test_epreuve_enceinte.py -q` (CI : `python3 -m pytest jeu -q`). Écrire les cas d'abord, et constater leur rouge sur le `ClientPlan` actuel.

**SC1 — La Biskra murée est relue exactement.** `LaBiskraMureeEnChantierEstRelue` sert la fixture par `Servir` et lit 10103. Attentes mesurées sur le service : `Tick == 3`, 0 parcelle, 0 bâtiment, 33 maisons et 7 rues de base. Une rue id 0, (-66, 2.2) → (-120, 2.2), 4 m, en chantier, 5 sur 108. Une enceinte (-80,-80) (80,-80) (80,80) (-80,80), en chantier, 2 foyers, 1 sur 19 200. Une porte (-80, 2.2), `Rue == "plan"`, identifiant 0, 4 m. Le relevé : `rue` 0 (5 bras, 15 kg, motif null), puis `enceinte` 0 (1 bras, 3 kg, motif null). Contre-épreuves : le `ClientPlan` d'avant rend une absence ; un lecteur qui saute la porte ou trie le relevé rougit.

**SC2 — Une enceinte ou une porte mal formée refuse tout le plan.** `[TestCase]` d'un nouveau `UneEnceinteOuUnePorteMalFormeeRefuseLePlan`, par `RemplacerUneFois(fixture, …)` et `Absence`. Chaque motif paraît une seule fois dans la fixture (vérifié). Ancien → nouveau : chemin, précision.
- `"enceinte":{"contour"` → `"enceinte":null,"x":{"contour"` : `enceinte`, « un objet attendu » ; `[[-80,-80],[80,-80],[80,80],[-80,80]]` → `[[-80,-80],[80,-80]]` : `enceinte.contour`, « au moins 3 points ».
- `"foyers":2` → `"foyers":1.5` : `enceinte.foyers`, « un entier » ; `"travail_fourni":1,"travail_requis":19200` → `"travail_fourni":19201,…` : `enceinte.travail_fourni`, « dépasse » ; `"en_chantier":true,"foyers":2` → `"en_chantier":false,…` : `enceinte.en_chantier`, « contredit ».
- `,"portes":[` → `,"portails":[` : `clé absente : portes` ; l'objet `"enceinte":{…19200},` → rien : `portes`, « sans enceinte ».
- `"point":[-80.0,2.2]` → `"point":[-80.0]` : `portes[0].point`, « exactement 2 nombres » ; `"rue":"plan"` → `"rue":"chemin"` : `portes[0].rue`, « plan ou base » ; `"largeur_m":4,"point"` → `"largeur_m":0,"point"` : `portes[0].largeur_m`, « > 0 ».
- `"identifiant":0,"largeur_m":4,"point":[-80.0,2.2],"rue":"plan"` → le même avec `"identifiant":3` : `portes[0].identifiant`, « aucune rue 3 » ; → `"identifiant":7,…,"rue":"base"` : même chemin, « aucune rue de base 7 ».
- `"nature":"enceinte"` → `"nature":"mur"` : `chantiers_du_jour[1].nature`, « enceinte attendu ».

Contre-épreuves : un lecteur qui garde un plan partiel ou ne vérifie pas la rue d'une porte rougit.

**SC3 — Une porte sur une rue de base exige la base.** `UnePorteDeBaseExigeLaBase` : la fixture dont la porte devient `"identifiant":0,…,"rue":"base"` est lue, avec `Portes[0].Rue == "base"`. Sans son bloc `base` (`"{" + texte.Substring(texte.IndexOf("\"batiments\":"))`), elle est refusée : « aucune rue de base 0 ». Contre-épreuve : un lecteur qui ne compte pas une base absente pour zéro rue rougit.

**SC4 — Sans enceinte, ni mur ni porte.** `UnPlanSansEnceinteNAPasDePorte` : sur `PLAN_JOUR`, sur `plan-biskra-graine0-tick0.json` et par `new PlanLu(1, 0, …)` à cinq arguments, `Enceinte == null` et `Portes.Count == 0`. Les deux classes nouvelles lèvent `ArgumentNullException` sur un `null`, et `Portes` refuse `Add`. Tous les tests existants restent verts sans une ligne changée. Contre-épreuve : lire `portes` par `Valeur` sans condition rougit tous les anciens tests.

**SC5 — La fixture est la réponse du service (Python).** `test_pont_plan_biskra_muree_fige` dans `test_epreuve_enceinte.py` joue la suite de la fixture sur `_service_local()` (de `test_carte_servie`) avec `requete_service`. Il exige les octets de `/plan?cell=10103` égaux à la fixture, et dans celle-ci `portes == PORTES`, une enceinte en chantier et une ligne `enceinte`. Contre-épreuves dans le test : au tick 1, avant les gestes, `/plan` n'a pas de clé `enceinte` ; un tick de plus et les octets diffèrent.

**SC6 — Périmètre, taille, rien d'assoupli.** `git diff --check` ; `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne nomment que le Périmètre ; `git diff --numstat origin/master` fait moins de 300 lignes, ce brief compris ; `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs jeu/sim/tests/test_epreuve_enceinte.py` n'a aucune ligne `-`.

## Hors périmètre
- Dessiner le mur et ses portes : sous-lot suivant de #417. Les marques de la photo sont des témoins de capture.
- Un outil Unity pour tracer l'enceinte ; le coût du chantier au panneau (#419).
- Les ouvriers vers l'enceinte : `TrajetsDesMetiers` rend « enceinte 0 introuvable », une absence déclarée laissée telle quelle ; `Lot788.Copier`, qui ne recopie pas l'enceinte.
- Le service, `sim/portes.py`, `MODELE.md` et les autres fixtures.

## Photo
Biskra murée en chantier, vue de haut : la ville de 1400 ouverte, la route en chantier, le contour lu de l'enceinte autour des maisons, et un poteau à sa porte sur la route. Avant ce lot, la même scène reste vide.

`Lot904.cs` : un scénario `[ScenarioDeCapture(904, "biskra-muree")]`, serré comme `Lot738`, service en pause ; chaque absence échoue en nommant sa cause.
1. Outil et caméra comme dans `Lot738`. Biskra par `ClientDeparts` (une seule fiche). `Lot362.Deposer` de `choisir_depart` (Zab), puis `Lot362.Tick`.
2. La route `[[-66,2.2],[-120,2.2]]` de 4 m et le carré ±80 de 2 foyers en `tracer_enceinte`, puis deux `Lot362.Tick`. Avec `-forge904SansEnceinte`, l'enceinte n'est pas déposée.
3. `Lot362.Lire` : une enceinte en chantier, une porte à (-80, 2.2), une ligne `enceinte` au relevé. Sous le drapeau : aucune des trois.
4. `outil.Ouvrir(cellule)` vrai, 33 maisons posées, 7 rues de 1400 dessinées.
5. Témoin, sauf sous le drapeau : un `LineRenderer` fermé sur `PlanLu.Enceinte.Contour` par `Lot362.Monde`, 1,5 m de large, 1 m au-dessus du sol, et un poteau de 6 m à chaque porte.
6. Caméra en surplomb à 65° ; les quatre coins du carré et la porte dans l'image, entre 0,02 et 0,98 ; dix images.
7. `lot904-rapport.json` dans le dossier de `-forgeCaptures`, refusé s'il existe déjà : cellule, tick, enceinte ou `null`, portes, natures du relevé, maisons posées, rues dessinées, `outil.Message`. Puis `Debug.Log("CAPTURE_904 …")`.

La photo, puis sa contre-épreuve (ville ouverte, sans témoin, rapport sans mur) :
```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 904 -forgeCaptures 3d/unity/Temp/lot904-photo -logFile 3d/unity/Temp/lot904-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 904 -forgeCaptures 3d/unity/Temp/lot904-sans-enceinte -forge904SansEnceinte -logFile 3d/unity/Temp/lot904-sans-enceinte.log
```
