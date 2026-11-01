# Lot #926 — Le pont pose une porte à chaque porte servie et le pan s'y ouvre
Jalon : J4 · Machine : pc · Taille prévue : 220 lignes

## But
Le pont Unity sait, par le calcul pur du lot #925, poser une porte à chaque porte que le monde sert sur l'enceinte : chaque porte retire le pan de courtine qu'elle couvre, se pose sur le mur à l'endroit servi et regarde dehors comme son côté.

## Le joueur
Lot de fond, découpé de #906 (lui-même tiré de #417 « L'enceinte se dessine, et ses portes s'ouvrent sur les rues »). Il prépare le geste du J4 de `CAP.md` : le joueur **trace son enceinte**, et l'écran du jalon montre « son enceinte ; ses chantiers ».

Aujourd'hui, Unity lit le contour du mur et ses portes (lot #904), et sait découper le contour en tours et en pans (lot #925). Mais un pan plein barre encore chaque rue qui sort de la ville : à Biskra, la rue du joueur, qui file vers l'ouest à y = 2,2, butte sur le pan 7 du côté ouest. Après ce lot, ce pan disparaît et une porte se pose en (−80 ; 2,2), tournée vers le dehors. Biskra murée compte alors 4 tours, 63 pans et 1 porte, autant de portes que le monde en sert.

Le joueur ne voit encore rien de neuf. Le sous-lot de #417 qui dessine le mur posera ces pièces dans Biskra avec les étapes du kit. Le joueur verra alors sa rue passer sous l'arc de la porte, à travers son mur. Il saura qu'un mur ne coupe pas ses routes, et pèsera mieux « des murs, ou des maisons ».

## Règle du monde
Sans objet : convention de vue, rien ne retourne au monde. Le calcul lit ce que fixe `jeu/sim/MODELE.md`, section « Le plan du bourg » (niveau 2, inchangée) :
- une porte est le croisement du contour bouclé avec l'axe d'une rue, `{point, rue, identifiant, largeur_m}` ;
- son point est arrondi à 6 décimales, et `controler_portes` le refuse à plus de `TOLERANCE_CHEVAUCHEMENT_M` = 0,01 m du contour ;
- le tri suit le côté, puis la distance au début du côté : le premier côté gagne quand une porte tombe sur un sommet.

Passage, péage, matériaux, effet défensif et siège restent de niveau 3, non simulés. La porte ne prend que la largeur servie (`largeur_m`, 4 m à Biskra). La pièce `porte_ksar` du kit (15,9 × 7,7 m, passage 4,4 m) et sa mise à l'échelle regardent le lot qui dessine. La porte partage l'étape unique du mur (`PansDeLEnceinte.Etape`, lot #925).

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/PansDeLEnceinte.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PansDeLEnceinteTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs
docs/briefs/926-le-pont-pose-une-porte-a-chaque-porte-servie-et.md

Tout autre chemin est interdit. `ClientPlan.cs`, `EtapeDuBatiment.cs` et la fixture de Biskra ne changent pas. Aucun fichier nouveau, donc aucun `.meta`.

Ce que fait le code, dans `PansDeLEnceinte.cs`, sans rien retirer de ce que #925 y a mis :
- `NatureDePiece` gagne `Porte`, en dernier : `{ Tour, Pan, Porte }`.
- Pour une porte, `PieceDeLEnceinte` porte :
  - `Cote` : le côté qui la porte ;
  - `Indice` : son rang dans la liste des portes servies ;
  - `CentreX` et `CentreY` : le point projeté sur le côté ;
  - `AbscisseM` : la distance de ce point à `c[i]` ;
  - `LongueurM` : la `LargeurM` servie ;
  - `LacetDegres` : le lacet des pans de son côté.
- La constante publique `TolerancePorteM = 0.01` vaut `TOLERANCE_CHEVAUCHEMENT_M` de `sim/constants.py`.
- `DecoupeDeLEnceinte Decouper(EnceinteDuPlan e, IReadOnlyList<PorteDuPlan> portes)` est la méthode nouvelle. `Decouper(e)` reste, et vaut `Decouper(e, new PorteDuPlan[0])`. Un `e` nul, une liste nulle ou une porte nulle lèvent `ArgumentNullException`.

La règle, après les absences et les calculs du contour de #925 (u, L, `libre`, k et la façade de chaque côté) :
1. **Le côté.** Pour la porte p, on mesure la distance de son point au segment `c[i] → c[(i+1) % n]`. Son côté est le premier i, dans l'ordre, dont la distance est la plus petite.
   - Si `!(distance ≤ TolerancePorteM)`, la découpe est absente : « porte p hors du mur ». Écrite ainsi, la condition attrape aussi un point NaN.
   - Les absences du contour passent avant celles des portes.
2. **La place.** On calcule l'abscisse `a = clamp(dot(point − c[i], u), 0, L)`, et le centre `c[i] + u · a`.
3. **Le pan couvert.**
   - Si le côté a des pans (`libre > 0`), le pan couvert est `j = clamp(⌊(a − CoteTourM / 2) / (libre / k)⌋, 0, k − 1)`. Une porte qui tombe dans la demi-tour d'un bout couvre donc le pan le plus proche.
   - Plusieurs portes peuvent couvrir le même pan : il ne disparaît qu'une fois, et chacune est posée.
   - Si le côté n'a aucun pan, la porte est posée et ne retire rien.
4. **Ordre.** D'abord les tours et les pans dans l'ordre de #925, moins les pans couverts. Puis les portes, dans l'ordre servi.

Budget : 35 lignes de code, 55 de `PansDeLEnceinteTests`, 10 ajoutées à `ClientPlanTests`, ce brief. Écrire serré.

## Conditions de succès
Unity, sur le PC, depuis la racine, en PowerShell, sans `-quit` :

```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot926.xml" -logFile "$env:TEMP\lot926.log"
```

On exige une sortie 0 et un XML neuf, sans échec ni cas ignoré. Chaque cas nouveau doit y figurer et avoir été exécuté, et tous les cas de #925 restent verts sans changement. Zéro cas nouveau est un échec. Écrire les cas d'abord et constater leur rouge. Tolérance 1e-9.

Les carrés C160, C160h et C6 sont ceux de #925. Les portes de test sont faites par `new PorteDuPlan(new PointLocal(x, y), "plan", 0, 4)`.

**SC1 — À Biskra, autant de portes posées que de portes servies.** `LaBiskraMureeOuvreSaPorte` est ajouté à `ClientPlanTests`, après `LaBiskraMureeSeDecoupe`. Il lit `MUREE` par `LireBiskra(Fixture(MUREE))`, puis appelle `Decouper(Plan.Enceinte, Plan.Portes)`. Il exige :
- une découpe présente de 68 pièces : 4 tours, 63 pans, et autant de portes que `Plan.Portes.Count` (1) ;
- la pièce 67 est la porte : côté 3, indice 0, en (−80 ; 2,2), abscisse 77,8, longueur 4, lacet 90 ;
- aucun pan ne reste au côté 3, indice 7 ; le côté 3 garde 15 pans ;
- la pièce 17 est toujours la tour en (80 ; −80).

Contre-épreuves, chacune rougit SC1 :
- une porte posée sans retirer son pan fait 69 pièces ;
- une porte oubliée en fait 67, sans porte ;
- une porte qui prend la façade du côté 0 a le lacet 0.

**SC2 — La porte retire le bon pan et regarde dehors.** `LaPorteOuvreLePanQuElleCouvre` exige, sur C160 :
- porte en (16 ; −80) : 68 pièces. Le pan 9 du côté 0 a disparu, la pièce 9 est le pan 8 et la pièce 10 le pan 10. La porte (pièce 67) est au côté 0, en (16 ; −80), abscisse 96, lacet 0 ;
- porte en (−78 ; −80), dans la demi-tour du coin : le pan 0 du côté 0 disparaît. La pièce 1 est le pan 1 en x = −62,075, et la pièce 16 la tour 1 ;
- porte en (80 ; 78,5) : elle est au côté 1, lacet 270, et retire le pan 15 de ce côté ;
- portes servies en (12 ; −80) puis (10 ; −80), sur le même pan : 69 pièces, 63 pans. La pièce 67 est la porte d'indice 0 en x = 12, la pièce 68 celle d'indice 1 en x = 10 ;
- porte en (0 ; −80,005) : présente, centre projeté en (0 ; −80) ;
- C160h, porte en (−80 ; 2,2) : côté 3, abscisse 82,2, pan 8 retiré, lacet 90. Le sens du tracé ne retourne pas la porte ;
- C6, porte en (0 ; −3) : 5 pièces, 4 tours et la porte, aucun pan retiré ;
- `Decouper(C160, new PorteDuPlan[0])` rend les mêmes 68 pièces que `Decouper(C160)`.

Contre-épreuves, chacune rougit SC2 :
- `Math.Round` au lieu du plancher retire le pan 10 pour la porte en (16 ; −80) ;
- un pan sans `clamp` sort du côté pour (−78 ; −80) ;
- une porte non projetée reste à y = −80,005 ;
- retirer un pan par son rang dans la liste, une fois par porte, ôte aussi son voisin : 62 pans au lieu de 63.

**SC3 — Une porte hors du mur rend la découpe absente.** `UnePorteHorsDuMurRendLaDecoupeAbsente`, en `TestCase`, exige à chaque fois une découpe absente, sans pièce, dont l'absence contient le texte attendu :
- C160, porte en (0 ; −79) → « porte 0 hors du mur » ;
- C160, portes en (10 ; −80) puis (0 ; −80,02) → « porte 1 hors du mur » ;
- C160, porte en (NaN ; −80) → « porte 0 hors du mur » ;
- contour plat (0,0) (10,0) (20,0) avec une porte en (5 ; 0) → « contour plat ».

`Decouper(C160, null)` et une liste qui contient `null` lèvent `ArgumentNullException`.

Contre-épreuves, chacune rougit SC3 :
- une tolérance de 1e-9 rend absente la porte en (0 ; −80,005) de SC2 ;
- `distance > TolerancePorteM` laisse passer le NaN ;
- une porte fautive sautée garde des pièces.

**SC4 — Périmètre, taille, rien d'assoupli.**
- `git diff --check` passe.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne nomment que le Périmètre.
- `git diff --numstat origin/master` fait moins de 300 lignes en tout, ce brief compris.
- `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/` n'a aucune ligne `-`.
- CI : `python3 -m pytest jeu -q` reste vert, sans changement.

## Hors périmètre
- Tout dessin : `porte_ksar` posée dans Biskra et mise à l'échelle, relief sous la porte, inscription de l'enceinte dans `KitDesBatiments`, photo du mur et de ses portes. C'est le sous-lot de #417 qui dessine le mur.
- Retirer plusieurs pans pour la largeur du modèle du kit (15,9 m) : la porte ne couvre que le pan de son point.
- Une étape propre à la porte : le monde ne sert qu'un chantier pour toute l'enceinte.
- Passage, péage, fermeture, défense : niveau 3.
- `sim/`, le service, `MODELE.md`, `ClientPlan.cs`, la fixture de Biskra.

## Photo
Sans objet : ce lot étend un calcul pur du pont et ses tests, sans rien brancher à une scène. Rien de ce qu'on voit à l'écran ne change. La photo de Biskra murée, avec sa rue sous la porte ouest, viendra avec le sous-lot de #417 qui dessine le mur, et son scénario de capture.
