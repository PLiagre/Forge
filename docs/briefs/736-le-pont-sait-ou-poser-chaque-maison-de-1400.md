# Lot #736 — Le pont sait où poser chaque maison de 1400
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
Le pont Unity sait, par une fonction pure, où poser chaque logis de la ville de 1400 servie : la façade de chaque maison de base tournée vers sa rue, et chaque îlot de k foyers coupé en k cases, rang par rang depuis la rue.

## Le joueur
Lot de fond, sous-lot 2 de #412 « Unity dessine la ville de 1400 d'après le service ». Il prépare le geste du J4 de `CAP.md` : le joueur **entre dans sa capitale en 3D, la ville de 1400 que tient le monde, pas un décor**. Après ce lot, le joueur ne voit encore rien de neuf, mais Unity sait tourner chaque maison vers sa rue : à Biskra, les 33 maisons regardent leurs 7 rues, des deux côtés ; dans une grande ville, chaque îlot devient autant de logis que de foyers. Le sous-lot 3 de #412 posera ces maisons avec le kit du désert et prendra la photo de Biskra : le joueur verra chaque maison tournée vers sa rue.

## Règle du monde
Sans objet : convention de vue, rien ne retourne au monde. Elle lit ce que fixe `jeu/sim/MODELE.md`, section « Le plan de base » (niveau 2, inchangée) : la façade d'une maison longe sa voie, en retrait du bord de la chaussée ; un îlot de k foyers fait `5 × min(k, 5)` m de façade et `40 k / façade` m de profondeur (25 × 32 m pour 20 foyers). La base ne sert ni la façade ni le découpage : Unity les déduit de la géométrie servie, sans constante de `sim/`. L'orientation reste de niveau 3, comme pour `LectureDuBatiment`.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/MaisonsDeLaBase.cs
3d/unity/Assets/ForgeLocal3D/Pont/MaisonsDeLaBase.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/MaisonsDeLaBaseTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/MaisonsDeLaBaseTests.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs
docs/briefs/736-le-pont-sait-ou-poser-chaque-maison-de-1400.md

Tout autre chemin est interdit. `ClientPlan.cs`, `EtapeDuBatiment.cs` et la fixture de Biskra ne changent pas. Unity génère les deux `.meta`.

Ce que fait le code, dans `namespace Forge.Pont`, dans le style de `PoseDuBatiment` :
- `CaseDeMaison`, en lecture seule : `int Maison` (le rang de la maison dans `BaseDuPlan.Maisons`), `int Indice` (0 … foyers − 1), `CentreX`, `CentreY` (mètres locaux), `LacetDegres`, `LargeurM`, `ProfondeurM`.
- `PoseDesMaisons` : `Presente`, `Absence` (vide si présente), `IReadOnlyList<CaseDeMaison> Cases`. Absente, la liste est vide : jamais de pose partielle.
- `MaisonsDeLaBase.Poser(BaseDuPlan @base)` : `null` lève `ArgumentNullException` ; zéro maison rend une pose présente sans case. Les cases sortent dans l'ordre des maisons, puis des indices.

La règle, maison par maison (rang i) :
1. L'emprise a exactement 4 points, sinon absence « maison i : emprise de n points ».
2. **Façade.** Pour chaque arête a = 0…3 (`c[a] → c[(a+1) % 4]`), chaque rue de base dans l'ordre servi et chaque segment `p → q` de ses points (arêtes et segments de longueur nulle sautés) : le segment compte s'il est parallèle, `|e × s| / (|e| |s|) < 0,001` (constante publique `SinusParallele`), et si le milieu M de l'arête se projette dans le segment, `0 ≤ (M − p)·s / |s|² ≤ 1`. Sa distance est `|(M − p) × s| / |s|`. La façade est l'arête de plus petite distance ; à égalité, la première trouvée. Aucune : absence « maison i : aucune rue parallèle ». Sorte, largeur et nom de la rue ne jouent pas.
3. **Repère.** F = longueur de la façade, u = son vecteur unitaire de `c[a]` vers `c[a+1]`, G = moyenne des 4 coins, n = la normale à u tournée vers G, P = 2 (G − M)·n. P ≤ 0 : absence « maison i : emprise plate ». Le lacet est celui de `LectureDuBatiment` pour la façade sortante f = −n : `atan2(−fx, −fy)` en degrés, ramené dans [0 ; 360). Le calculer ainsi, ou appeler `LectureDuBatiment.Poser` sur l'emprise tournée pour commencer en `c[a]`.
4. **Cases.** k = foyers ; N = ⌈√(k F / P)⌉ cases par rang, R = ⌈k / N⌉ rangs. La case j a pour rang r = j / N (0 contre la rue) et pour place q = j mod N (0 du côté de `c[a]`) ; centre `c[a] + u (q + ½) F/N + n (r + ½) P/R`, largeur F/N, profondeur P/R, le lacet de sa maison. Le dernier rang, le plus loin de la rue, est partiel : il garde ses k − N(R − 1) premières places. Une maison d'un foyer donne une case : la maison entière.

Budget : 85 lignes de code, 95 de `MaisonsDeLaBaseTests`, 25 ajoutées à `ClientPlanTests`, 4 de `.meta`, ce brief. Écrire serré.

## Conditions de succès
Unity, sur le PC, depuis la racine, en PowerShell, sans `-quit` : `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot736.xml" -logFile "$env:TEMP\lot736.log"`. On exige une sortie 0 et un XML neuf, sans échec ni cas ignoré, où chaque cas nouveau figure et a été exécuté (zéro cas nouveau est un échec). Écrire les cas d'abord et constater leur rouge. Tolérance 1e-9 sur la base synthétique, 1e-5 sur Biskra.

La base synthétique de `MaisonsDeLaBaseTests`, construite par `new BaseDuPlan(…)` (place quelconque) :
- rues : 0 `principale` (50,0)→(150,0), largeur 6 ; 1 `ruelle` (90,3)→(90,63), largeur 3 ; 2 `ruelle` (134,−20)→(194,−20) ; 3 `ruelle` (134,−40)→(134,−100) ;
- maisons : 0 (62.5,12)(62.5,4)(57.5,4)(57.5,12), 1 foyer, au nord de la rue ; 1 (62.5,−4)(62.5,−12)(57.5,−12)(57.5,−4), 1 foyer, au sud ; 2 (92.5,8)(100.5,8)(100.5,3)(92.5,3), 1 foyer, maison d'angle sur la ruelle 1, dont le flanc est à 3 m de l'axe de la principale et la façade à 2,5 m de celui de la ruelle ; 3 (132.5,−4)(132.5,−36)(107.5,−36)(107.5,−4), îlot de 20 ; 4 (132.5,13.6)(132.5,4)(107.5,4)(107.5,13.6), îlot de 6.

**SC1 — Chaque maison regarde sa rue.** `LesMaisonsDeLaBaseRegardentLeurRue` exige 29 cases (somme des foyers), dans l'ordre (Maison, Indice), et : maison 0 → (60, 8), lacet 0, 5 × 8 ; maison 1 → (60, −8), lacet 180 ; maison 2 → (96.5, 5.5), lacet 90, 5 × 8 ; îlot de 20 → 20 cases de 6.25 × 6.4, lacet 180, indices 0 (110.625, −7.2), 3 (129.375, −7.2), 4 (110.625, −13.6), 19 (129.375, −32.8) ; îlot de 6 → 6 cases de 6.25 × 4.8, lacet 0, indices 0 (129.375, 6.4), 3 (110.625, 6.4), 4 (129.375, 11.2), 5 (123.125, 11.2). Contre-épreuves (mesurées sur cette base) : sans le parallélisme, l'îlot de 20 se tourne vers le bout de la ruelle 2 ; avec la droite au lieu du segment, les deux îlots se tournent vers la ruelle 3 ; en ne lisant que les principales, la maison d'angle tourne le dos à sa ruelle ; N = k, ou les rangs comptés depuis le fond, déplacent les cases. Chacune rougit SC1.

**SC2 — Le seuil de parallélisme et les absences.** `UnePoseImpossibleEstDeclareeAbsente` exige : la principale finie en (150, 0.05) (sinus 0,0005) rend les mêmes 29 cases ; finie en (150, 0.15) (sinus 0,0015), la pose est absente, nomme « maison 1 » et « aucune rue parallèle », et n'a aucune case (la maison 0 trouvait encore la ruelle 1) ; la maison 0 réduite à 3 points rend « maison 0 : emprise de 3 points » ; une base sans maison est présente, sans case ; `Poser(null)` lève `ArgumentNullException`. Contre-épreuves : un seuil de 0,01 rend la pose présente à 0.15 ; une pose qui saute la maison fautive garde des cases. Chacune rougit SC2.

**SC3 — Biskra se pose face à ses rues.** `LaBaseDeBiskraSePoseFaceASesRues`, ajouté à `ClientPlanTests` (qui sait servir la fixture), lit 10103 comme `LaBaseDeBiskraServieEstRelue`, puis pose sa base. Il exige 33 cases ; la case k a `Maison == k`, `Indice == 0`, largeur 5, profondeur 8, centre égal à la moyenne des 4 coins de l'emprise k. Les arêtes de façade, mesurées sur le générateur, sont `133113313111313313113313131331313` (maison 0 à 32) : pour chaque k, `LectureDuBatiment.Poser` d'un `BatimentDuPlan` dont l'emprise k commence à cette arête rend le même lacet que la case. Attentes en dur : case 0 en (−52.762008, −6.266451), lacet 181.886541 ; case 32 en (−62.2654, −53.500643), lacet 313.737296. Contre-épreuve : poser toujours la façade sur `c0 → c1`, comme un bâtiment de geste, tourne les 33 maisons d'un quart de tour et rougit.

**SC4 — Périmètre, taille, rien d'assoupli.** `git diff --check` ; `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne nomment que le Périmètre ; `git diff --numstat origin/master` fait moins de 300 lignes en tout, ce brief compris ; `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs` n'a aucune ligne `-`. CI : `python3 -m pytest jeu -q` reste vert, sans changement.

## Hors périmètre
- Le service, `ville1400.py`, `MODELE.md`, `ClientPlan.cs`, la fixture de Biskra.
- Tout dessin : maisons du kit à l'échelle de leur case, sous leur racine, et photo de Biskra (sous-lot 3 de #412) ; rues de base en rubans (sous-lot 4).
- Le relief sous une case, l'altitude, le choix d'un modèle du kit par case.
- Une façade sur une rue de geste, une maison touchée par un geste.

## Photo
Sans objet : ce lot ajoute une fonction pure du pont et ses tests, sans rien brancher à une scène. Rien de ce qu'on voit à l'écran ne change. La photo de Biskra, ses 33 maisons tournées vers leurs rues, viendra au sous-lot 3 de #412, avec son scénario de capture.
