# Lot #907 — Unity dessine l'enceinte du plan servi avec les pièces du kit
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
La capitale ouverte dans Unity montre l'enceinte que le monde sert : une tour à chaque sommet, les pans de courtine entre elles et une porte à chaque porte servie, à l'étape du chantier, avec les pièces du kit du désert.

## Le joueur
Découpé de #417 « L'enceinte se dessine, et ses portes s'ouvrent sur les rues ». Geste du J4 : le joueur trace son enceinte, et l'écran montre son enceinte et ses chantiers. Le monde lui fait déjà payer 19 200 journées pour le carré de ±80 m de Biskra (#904) ; le kit a les piquets, la levée et le mur fini (#905) ; le pont sait où poser chaque pièce (#925, #926). Après ce lot, il ouvre Biskra et voit ce mur au cordeau : quatre tours, 63 pans et la porte de la route de l'ouest, aux piquets tant que la moitié du travail n'est pas fournie. Il mesure « des murs, ou des maisons » : un chantier immense, encore aux piquets.

## Règle du monde
Sans objet : lot de vue. `jeu/` n'est pas touché. La vue lit `jeu/sim/MODELE.md`, « Le plan du bourg » : enceinte (contour bouclé, `en_chantier`, travail fourni et requis) et portes, fidélité 2, inchangée. Déjà en place : `PlanLu.Enceinte` nul sans mur et `Portes` (#904) ; `Decouper` rend tours, pans puis portes, et `Etape` une étape pour tout le mur (`fourni < requis - fourni` : piquets, sinon murs ; fini hors chantier) ; `Euler(0, lacet, 0)` tourne la façade +Z dehors. Les neuf prefabs sont dans `Desert/Prefabs/`. `Piece` déclare une pièce manquante, sans repli. L'asset ne connaît que `maison`, `scierie` et `four`. `DessinerBatiments` sert `Ouvrir`, `Ouvrir(cellule)`, `Attendre` et `Rafraichir`.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Desert/DesertEnceinte.cs
3d/unity/Assets/ForgeLocal3D/Desert/DesertEnceinte.cs.meta
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Desert/Resources/KitDesBatiments.asset
3d/unity/Assets/ForgeLocal3D/Pont/Tests/KitDesBatimentsTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot907.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot907.cs.meta
docs/briefs/907-unity-dessine-l-enceinte-du-plan-servi-avec-les.md

`KitDesBatiments.cs` ne change pas. Chaque `.meta` fait deux lignes (`fileFormatVersion`, `guid`).

**Asset.** Trois entrées en fin de `natures` : `courtine`, `tour`, `porte`, chacune avec `piquets`, `murs`, `fini`. Le fileID est le GameObject dont `m_Name` est le nom du prefab, pas un enfant `_LOD`. Exemple : `chantier_rempart_pise_10m_piquets`, fileID 6117145514765731145, guid 59bb6c64249513c46addebedf2c7f708. Courtine : `chantier_rempart_pise_10m_piquets`, `chantier_rempart_pise_10m_murs`, `rempart_pise_10m`. Tour : `chantier_tour_ksar_0_piquets`, `chantier_tour_ksar_0_murs`, `tour_ksar_0`. Porte : `chantier_porte_ksar_piquets`, `chantier_porte_ksar_murs`, `porte_ksar`.

**`DesertEnceinte`**, namespace `ForgeLocal3D`, classe ordinaire sur le modèle de `DesertBatiments`. Constructeur `(Transform parent, Terrain terrain, KitDesBatiments kit)`. Un kit nul lève `InvalidOperationException("Pas de kit des bâtiments (Resources/KitDesBatiments) : l'enceinte n'est pas dessinée.")`. Il crée l'enfant `Enceinte du plan`. `RacineBatiments` et `EmpreinteBatiments` ne bougent pas. Publics : `Racine`, `Kit` (get et set : la capture le remplace), `Posees`, `List<string> Refus`, `Empreinte` (SHA-256).

`Dessiner(EnceinteDuPlan e, IReadOnlyList<PorteDuPlan> portes)` vide d'abord la racine par `DestroyImmediate` (maillages et matériaux intacts), remet `Posees` à 0 et vide `Refus`. `e` nul : empreinte du texte vide, retour `""`. Découpe absente : empreinte du texte vide, `Enceinte non dessinée : ` plus l'absence, rien posé. Sinon l'étape est `Etape(e)`, le nom au kit `tour`, `courtine` ou `porte`, la pièce `Kit.Piece(nom, étape)`. Pièce absente, ou centre dont `|x|` ou `|y|` dépasse `terrainData.size.x / 2 - 1` : `Refus` reçoit `Pièce <i> de l'enceinte non posée : <cause>` (`hors du terrain.` pour le centre), et cet emplacement reste vide. Sinon l'instance s'appelle `Enceinte <nom> <Cote>-<Indice>`, posée en `(-CentreX, sol, -CentreY)`, `Euler(0, LacetDegres, 0)`. Une courtine a l'échelle `(LongueurM / LongueurPanM, 1, 1)` : la longueur de `wall()` est l'axe X. Tours et portes gardent l'échelle 1. Retour : `Enceinte : <étape en minuscules> · <T> tour(s), <P> pan(s), <G> porte(s).` comptés sur les pièces posées, puis une ligne par refus. L'empreinte hache une ligne par pièce, `<i> refusee` ou `<i> <nom> <Cote>-<Indice> <prefab> x y z lacet échelleX`, en `F2`, culture invariante.

**`DesertRoadTool`.** Champ `enceinte` et `public DesertEnceinte Enceinte => enceinte`. Dans `Awake`, après les bâtiments, le même `try` : `new DesertEnceinte(transform, roads.terrain, KitDesBatiments.Charger())`. Sur le retour de `DessinerBatiments` qui dessine les maisons (le `return` quand `batiments` est nul ne change pas) : si la ligne n'est pas vide, `"\n"` puis elle. Si `enceinte` est nul et que `lu.Enceinte` ne l'est pas, la cause à la place. Une ligne « Lot 907 » au commentaire de classe.

Budget du `numstat` : asset 12, tests 24, `DesertEnceinte` 74, outil 12, `Lot907` 72, `.meta` 4, ce brief. Serré comme `Lot904`.

## Conditions de succès
**SC1 — Le kit rend les pièces de l'enceinte, ou les déclare absentes.** Depuis la racine, Unity fermé :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot907-tests.xml -logFile 3d/unity/Temp/lot907-tests.log
```

Sortie 0, XML neuf, aucun échec ni cas ignoré. Les cas déjà là passent sans qu'une de leurs lignes change. Ajouts à `KitDesBatimentsTests` : `LesPiecesDeLEnceinteSeChargentHorsDeLEditeur`, 9 `TestCase` (`courtine`, `tour`, `porte` × trois étapes), nom du prefab et chemin `Assets/ForgeLocal3D/Desert/Prefabs/<nom>.prefab` ; `UnePieceDeLEnceinteManquanteEstDeclaree`, sur `Object.Instantiate(KitDesBatiments.Charger())`, murs de `porte` à nul → `pièce manquante au kit : porte murs` et prefab nul, piquets de `porte` et murs de `tour` inchangés, copie détruite. Contre-épreuves dites dans la PR : piquets de `tour` pointés vers le rempart, un cas rouge ; entrée `porte` retirée, trois cas rouges.

**SC2 — La photo peut échouer.** La commande sans drapeau `-forge907…` sort en 0 et écrit `lot907-rapport.json`. Une exigence du scénario qui tombe fait échouer la capture. Les deux autres sortent en 0 :
- `-forge907SansEnceinte` : 0 pièce posée, aucune ligne qui commence par `Enceinte` au panneau ;
- `-forge907SansPorte` : 67 pièces, un seul refus `Pièce 67 de l'enceinte non posée : pièce manquante au kit : porte piquets`, et le panneau `Enceinte : piquets · 4 tour(s), 63 pan(s), 0 porte(s).` suivi de cette ligne. Ni `Enceinte porte 3-0` ni `Enceinte courtine 3-7` : le pan 7 du côté ouest, celui que la porte de (−80 ; 2,2) retire sur le carré `[[-80,-80],[80,-80],[80,80],[-80,80]]`, reste vide.

Faites à la main, chacune doit faire échouer la capture, et dites dans la PR : (a) toujours l'étape `Fini` ; (b) la rotation laissée à `identity` ; (c) la racine pas vidée ; (d) une pièce absente remplacée par la pièce finie, sous `-forge907SansPorte`.

**SC3 — Rien d'autre ne bouge.** Les trois captures ci-dessous sortent en 0. `git diff --name-only origin/master` ne nomme que le Périmètre. `git diff --numstat origin/master` fait moins de 300 lignes, ce brief compris. `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/` n'a aucune ligne `-`. `python3 -m pytest jeu -q` reste vert.

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 369 -forgeCaptures 3d/unity/Temp/lot907-regres-369 -logFile 3d/unity/Temp/lot907-regres-369.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 737 -forgeCaptures 3d/unity/Temp/lot907-regres-737 -logFile 3d/unity/Temp/lot907-regres-737.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 904 -forgeCaptures 3d/unity/Temp/lot907-regres-904 -logFile 3d/unity/Temp/lot907-regres-904.log
```

## Hors périmètre
Incliner une pièce sur la pente, ou aplanir le sol sous le mur. Mettre la porte à la largeur servie : `porte_ksar` garde sa taille, et #926 n'ôte que le pan du point de la porte. `tour_ksar_1`, `tour_ksar_2`, un angle de rempart, une étape différente par pièce : le monde ne sert qu'un chantier. Le coût au panneau (#419). Un geste dans Unity pour tracer le mur. `sim/`, `Pont/` hors de `KitDesBatimentsTests.cs`, `KitDesBatiments.cs`, `DesertBatiments.cs`, les prefabs et les scènes.

## Photo
Biskra vue de l'ouest à 35°, ses 33 maisons de 1400 derrière le mur. Devant, la porte aux piquets sur la route du joueur, entre les deux tours du côté ouest et leurs pans au cordeau. Le panneau dit `Enceinte : piquets · 4 tour(s), 63 pan(s), 1 porte(s).`

`Lot907.cs`, `[ScenarioDeCapture(907, "biskra-enceinte")]`, échoue en nommant sa cause. Il refuse un `lot907-rapport.json` déjà présent. Outil, caméra et marcheur en `automatique`. Il rejoue `Lot904` : `choisir_depart` Biskra, un tick, route `[[-66,2.2],[-120,2.2]]`, enceinte `[[-80,-80],[80,-80],[80,80],[-80,80]]` à 2 foyers sauf sous `-forge907SansEnceinte`, deux ticks. Avec le mur : enceinte en chantier, `travail_fourni` 1, `travail_requis` 19200, porte (−80 ; 2,2). Sans mur : ni enceinte ni porte. Sous `-forge907SansPorte`, `outil.Enceinte.Kit` est une copie sans piquets de `porte`. `Ouvrir(cellule)` vrai, 33 maisons et 7 rues de 1400 : `Racine.childCount == Posees` (68 avec le mur), refus et ligne de panneau exacts, prefabs `chantier_tour_ksar_0_piquets` ×4, `chantier_rempart_pise_10m_piquets` ×63, `chantier_porte_ksar_piquets` ×1. Chaque pièce contre `Decouper` : écart horizontal < 0,01 m, lacet à 0,01°, pied au sol à 0,01 m. `Enceinte porte 3-0` au lacet 90. `Rafraichir()` vrai, même empreinte, même nombre d'enfants. Caméra `ville.Poser`, 35°, cap = lacet de la porte + 180, visée `Lot362.Monde(t, -80, 0)`, `aspect` 1600/900, recul `d *= 1.06f` depuis 40 m jusqu'à `DistanceMax`, tours (−80 ; ±80) et porte entre 0,02 et 0,98, caméra hors du carré (x Unity > 80), puis dix images. Rapport : cellule, tick, étape, travail fourni et requis, chaque pièce (nom, prefab, position, lacet), `posees`, `refus`, `empreinte`, panneau, puis `Debug.Log("CAPTURE_907 …")`.

Le codeur regarde les trois images et dit ce qu'il voit : le cordeau autour de la ville, la porte sur la route de l'ouest, et le trou laissé quand la pièce de porte manque.

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 907 -forgeCaptures 3d/unity/Temp/lot907-photo -logFile 3d/unity/Temp/lot907-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 907 -forgeCaptures 3d/unity/Temp/lot907-sans-enceinte -forge907SansEnceinte -logFile 3d/unity/Temp/lot907-sans-enceinte.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 907 -forgeCaptures 3d/unity/Temp/lot907-sans-porte -forge907SansPorte -logFile 3d/unity/Temp/lot907-sans-porte.log
```
