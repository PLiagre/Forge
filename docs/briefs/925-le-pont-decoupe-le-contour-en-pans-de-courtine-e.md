# Lot #925 — Le pont découpe le contour en pans de courtine et pose une tour à chaque sommet
Jalon : J4 · Machine : pc · Taille prévue : 260 lignes

## But
Le pont Unity sait, par un calcul pur, découper le contour bouclé de l'enceinte servie en une tour de 7,2 m à chaque sommet et des pans de courtine d'au plus 10 m entre elles, chacun avec son centre et sa façade tournée vers l'extérieur. Il sait aussi dire l'étape du chantier du mur : piquets, murs ou fini.

## Le joueur
Lot de fond, découpé de #906 (lui-même tiré de #417 « L'enceinte se dessine, et ses portes s'ouvrent sur les rues »). Il prépare le geste du J4 de `CAP.md` : le joueur **trace son enceinte**, et l'écran du jalon montre « son enceinte ; ses chantiers ».

Aujourd'hui, Unity lit le contour du mur de Biskra (lot #904) et le kit a les étapes de la courtine et de la tour (lot #905). Mais personne ne sait encore où poser chaque pièce le long du tracé, ni laquelle des trois étapes montrer. Après ce lot, le carré de ±80 m de Biskra devient 4 tours et 64 pans de 9,55 m, tous à l'étape « piquets » tant que la moitié des 19 200 journées n'est pas fournie.

Le joueur ne voit encore rien de neuf. La suite de #906 percera les pans aux portes, puis le sous-lot de #417 qui dessine le mur posera ces pièces dans Biskra avec les étapes du kit. Le joueur verra alors son mur passer du cordeau à la terre banchée, puis au mur fini, et pèsera mieux « des murs, ou des maisons ».

## Règle du monde
Sans objet : convention de vue, rien ne retourne au monde. Le calcul lit ce que fixe `jeu/sim/MODELE.md`, section « Le plan du bourg » (niveau 2, inchangée) :
- le contour compte au moins 3 points ;
- il se referme du dernier point au premier : le côté de fermeture est un côté comme les autres ;
- `en_chantier == (travail_fourni < travail_requis)`.

La hauteur, les matériaux et l'allure du mur restent de niveau 3, non simulés. Les longueurs viennent du kit (fidélité 2) : `rempart_pise_10m` fait 10,07 m, et `tour_ksar_0` 7,2 × 7,2 m. L'étape suit la règle des bâtiments du lot #368 (`LectureDuBatiment.Etape`) : le mur entier montre une seule étape, comme un seul chantier.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/PansDeLEnceinte.cs
3d/unity/Assets/ForgeLocal3D/Pont/PansDeLEnceinte.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PansDeLEnceinteTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PansDeLEnceinteTests.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs
docs/briefs/925-le-pont-decoupe-le-contour-en-pans-de-courtine-e.md

Tout autre chemin est interdit. `ClientPlan.cs`, `EtapeDuBatiment.cs`, `KitDesBatiments.cs` et la fixture de Biskra ne changent pas. Unity génère les deux `.meta`.

Ce que fait le code, dans `namespace Forge.Pont`, dans le style de `PoseDuBatiment` et de `MaisonsDeLaBase` :
- `public enum NatureDePiece { Tour, Pan }`.
- `PieceDeLEnceinte`, en lecture seule :
  - `Nature` ;
  - `int Cote` : le sommet i pour une tour, le côté i (`c[i] → c[(i+1) % n]`) pour un pan ;
  - `int Indice` : le rang du pan sur son côté, à partir de `c[i]` ; 0 pour une tour ;
  - `CentreX`, `CentreY` (mètres locaux) ;
  - `AbscisseM` : distance du centre à `c[i]` le long du côté ; 0 pour une tour ;
  - `LongueurM` : celle du pan, ou `CoteTourM` pour une tour ;
  - `LacetDegres`.
- `DecoupeDeLEnceinte` : `Presente`, `Absence` (vide si présente), `IReadOnlyList<PieceDeLEnceinte> Pieces`. Absente, la liste est vide : jamais de découpe partielle.
- `public static class PansDeLEnceinte`, avec les constantes publiques `LongueurPanM = 10` et `CoteTourM = 7.2` :
  - `DecoupeDeLEnceinte Decouper(EnceinteDuPlan e)` ;
  - `EtapeDuBatiment Etape(EnceinteDuPlan e)`.
  - L'une et l'autre lèvent `ArgumentNullException` sur `null`.

La règle de `Decouper`, pour n points c[0…n−1] :
1. **Absences**, vérifiées dans cet ordre, chacune nommée :
   - « point i non fini » (NaN ou infini) ;
   - « côté i : longueur nulle » ;
   - « contour plat », si l'aire signée A (formule du lacet, côté de fermeture compris) vaut 0 ;
   - « sommet i : demi-tour », si la somme des normales des deux côtés du sommet a une norme < 1e-9.
2. **Façade d'un côté.** Pour u, le vecteur unitaire de `c[i] → c[i+1]`, la normale sortante est (uy, −ux) si A > 0, et (−uy, ux) sinon. Le contour peut donc tourner dans un sens ou dans l'autre. Le lacet suit la convention de `LectureDuBatiment` pour une façade f : `atan2(−fx, −fy)` en degrés, ramené dans [0 ; 360).
3. **Tours.** Une tour par sommet, centrée sur c[i]. Sa façade est la somme normalisée des normales sortantes des côtés i − 1 et i : la bissectrice extérieure.
4. **Pans.** Sur le côté i de longueur L, la place libre vaut `libre = L − CoteTourM`, soit une demi-tour retirée à chaque bout.
   - Si `libre ≤ 0`, ce côté n'a aucun pan.
   - Sinon, il a `k = ⌈libre / LongueurPanM⌉` pans de longueur `libre / k`, donc jamais plus longs que la pièce du kit.
   - Le pan j a pour abscisse `CoteTourM / 2 + (j + ½) · libre / k`, pour centre `c[i] + u · abscisse`, et la façade de son côté.
5. **Ordre.** Pour i = 0 … n − 1 : la tour i, puis les pans du côté i, dans l'ordre des j.

`Etape` : `!EnChantier` → `Fini`. Sinon, `Piquets` si `fourni × 2 < requis`, écrit sans débordement comme dans `LectureDuBatiment.Etape`, et `Murs` dans le cas contraire.

Budget : 85 lignes de code, 100 de `PansDeLEnceinteTests`, 15 ajoutées à `ClientPlanTests`, 4 de `.meta`, ce brief. Écrire serré.

## Conditions de succès
Unity, sur le PC, depuis la racine, en PowerShell, sans `-quit` :

```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot925.xml" -logFile "$env:TEMP\lot925.log"
```

On exige une sortie 0 et un XML neuf, sans échec ni cas ignoré. Chaque cas nouveau doit y figurer et avoir été exécuté : zéro cas nouveau est un échec. Écrire les cas d'abord et constater leur rouge. Tolérance 1e-9.

Les carrés de `PansDeLEnceinteTests`, construits par `new EnceinteDuPlan(…)` (foyers 2) :
- C160 : (−80,−80) (80,−80) (80,80) (−80,80), sens trigonométrique, le contour servi à Biskra ;
- C160h : les mêmes points dans l'ordre inverse, sens horaire ;
- C30 : (−15,−15) (15,−15) (15,15) (−15,15) ;
- C6 : (−3,−3) (3,−3) (3,3) (−3,3).

**SC1 — Le carré de Biskra se découpe en 4 tours et 64 pans.** `LeCarreSeDecoupeEnToursEtPans` exige, sur C160 :
- 68 pièces : la pièce 0 est la tour 0 ; les pièces 1 à 16 sont les pans du côté 0 ; la pièce 17 est la tour 1 ;
- chaque pan mesure 9,55 m ;
- tours en (−80,−80), lacet 45 ; (80,−80), lacet 315 ; (80,80), lacet 225 ; (−80,80), lacet 135 ;
- les pans du côté 0 sont à y = −80, lacet 0 : pan 0 en x = −71,625 (abscisse 8,375), pan 15 en x = 71,625 ;
- les lacets des côtés 1, 2 et 3 valent 270, 180 et 90 ; le pan 0 du côté 1 (pièce 18) est en (80, −71,625).

Contre-épreuves, chacune rougit SC1 :
- `Math.Round` au lieu du plafond donne 15 pans de 10,19 m ;
- des pans comptés sur L au lieu de `libre` mordent sur les tours ;
- une tour tournée comme son côté sortant n'a plus le lacet 45.

**SC2 — Le sens du tracé ne retourne pas le mur, et les petits côtés gardent leurs tours.** `LeSensEtLaTailleDuCarre` exige :
- C160h : 68 pièces. Son côté 0, de (−80,80) à (80,80), a ses pans à y = 80, lacet 180. Contre-épreuve : la normale (uy, −ux) prise sans regarder le signe de A tourne les pans vers l'intérieur (lacet 0) et rougit ;
- C30 : `libre` = 22,8, donc 3 pans de 7,6 par côté et 16 pièces. Ceux du côté 0 sont en x = −7,6, 0 et 7,6. Contre-épreuve : l'arrondi donne 2 pans de 11,4 et rougit ;
- C6 : 4 tours, aucun pan.

**SC3 — Une découpe impossible est déclarée absente.** `UneDecoupeImpossibleEstAbsente`, en `TestCase`, exige à chaque fois une découpe absente, sans pièce, dont l'absence contient le texte attendu :
- C160 avec le point 1 répété → « côté 1 : longueur nulle » ;
- (0,0) (10,0) (20,0) → « contour plat » ;
- (0,0) (40,0) (40,40) (40,20) (aire 400) → « sommet 2 : demi-tour » ;
- un point NaN → « point 2 non fini ».

`Decouper(null)` et `Etape(null)` lèvent `ArgumentNullException`. Contre-épreuve : une découpe qui saute le côté fautif garde des pièces et rougit.

**SC4 — L'étape suit la règle des bâtiments.** `LEtapeSuitLaRegleDesBatiments`, en `TestCase` (requis, fourni, en chantier → étape) :
- 19 200, 1, vrai → Piquets ;
- 19 200, 9 599 → Piquets ;
- 19 200, 9 600 → Murs ;
- 19 201, 9 600 → Piquets ;
- 19 201, 9 601 → Murs ;
- 19 200, 19 200, faux → Fini.

Pour chaque cas, l'étape est aussi celle que `LectureDuBatiment.Etape` rend pour un `BatimentDuPlan` de même travail. Contre-épreuve : `fourni × 2 ≤ requis` met 9 600 sur 19 200 aux piquets et rougit.

**SC5 — La Biskra murée servie se découpe.** `LaBiskraMureeSeDecoupe` est ajouté à `ClientPlanTests`, après `LaBiskraMureeEnChantierEstRelue`. Il lit `MUREE` par `LireBiskra(Fixture(MUREE))` et découpe `Plan.Enceinte`. Il exige une découpe présente de 68 pièces, la pièce 17 étant une tour en (80,−80), et `Etape == Piquets` (1 journée sur 19 200).

**SC6 — Périmètre, taille, rien d'assoupli.**
- `git diff --check` passe.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne nomment que le Périmètre.
- `git diff --numstat origin/master` fait moins de 300 lignes en tout, ce brief compris.
- `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs` n'a aucune ligne `-`.
- CI : `python3 -m pytest jeu -q` reste vert, sans changement.

## Hors périmètre
- Les portes : percer un pan au point d'une `PorteDuPlan`, poser `porte_ksar` (suite de #906).
- Tout dessin : prefabs du kit posés dans Biskra, mise à l'échelle d'un pan de 9,55 m, relief sous une pièce, inscription de l'enceinte dans `KitDesBatiments`, photo du mur (sous-lot de #417 qui dessine le mur).
- Une étape par pièce, ou un mur qui monte pan après pan : le monde ne sert qu'un chantier pour toute l'enceinte.
- Les tours `tour_ksar_1` et `tour_ksar_2`, un angle de rempart, un contour courbe.
- `sim/`, le service, `MODELE.md`, `ClientPlan.cs`, la fixture de Biskra.

## Photo
Sans objet : ce lot ajoute un calcul pur du pont et ses tests, sans rien brancher à une scène. Rien de ce qu'on voit à l'écran ne change. La photo de Biskra murée, ses tours et ses pans à l'étape des piquets, viendra avec le sous-lot de #417 qui dessine le mur, et son scénario de capture.
