# Brief 263 — Le joueur trace une route qui épouse le relief

## But

Dans la scène `Forge_Desert_Ville_<implantation>`, en Play, le joueur pose des
points sur le terrain et obtient une route qui suit le relief : terrain aplani
sous sa largeur, talus au-delà, sol peint en terre battue ou en pavés — et une
route trop raide est refusée avec un message qui dit pourquoi.

État de départ à mesurer :

```powershell
py local3d/atelier_desert.py terrain
Select-String -Path unity/Packages/manifest.json -Pattern "splines"
Get-ChildItem unity/Assets/ForgeLocal3D -Recurse -Filter "DesertRoad*"
```

Aujourd'hui, `terrain` passe sur les deux implantations (la V0, livrée par
la PR #91) ; le manifeste Unity ne connaît pas `com.unity.splines` ; aucun
script de route n'existe. Le terrain porte déjà, sculptées par
`paysage.field`, les anciennes rues du plan (`paysage.plan`) : une route
retracée dessus trouve un sol déjà plat. C'est pourquoi le jeu de gestes du
contrôle (SC1) sort aussi de ces rues.

Ce qui rend ce lot caduc : si un script sous `unity/Assets/ForgeLocal3D/`
creuse déjà un Unity Terrain le long d'une spline. Ce qui le rend bloqué :
si `py local3d/atelier_desert.py terrain` ne passe plus sur `master` (la
réparer d'abord, dans un autre lot), ou si le propriétaire refuse le
téléchargement du paquet `com.unity.splines`.

## Règle du monde

Ce lot ne touche aucune règle du monde simulé : `sim/` n'est pas concerné,
aucune section de `sim/MODELE.md` n'en découle. C'est un travail de
présentation dans un contexte imaginaire, **fidélité 2** (plausible, généré,
jamais sourcé). Le plan et ses raisons vivent dans
[`local3d/desert/VILLE.md`](../local3d/desert/VILLE.md), section V1.

Ce qu'une route doit faire, en termes de terrain :

- **Un geste** est une suite d'au moins deux points posés par le joueur,
  une largeur et un revêtement (`terre` ou `paves`). La spline
  (`com.unity.splines`) passe par ces points ; elle est échantillonnée tous
  les **0,5 m** — le pas du terrain.
- **Le profil en long suit le relief** : en chaque échantillon, la hauteur
  du terrain d'origine, puis un lissage (moyenne glissante sur une fenêtre
  de longueur fixée, ordre de grandeur plausible : une dizaine de mètres).
  Si le profil lissé dépasse **12 %** de pente quelque part, la route est
  **refusée** : rien ne change, et un message nomme la pente mesurée et
  l'endroit.
- **Le terrain s'aplanit sous la largeur** : chaque sommet de la grille
  couvert par la route prend la hauteur du profil au point de l'axe le plus
  proche. Au-delà, un **talus de pente 1:2 au plus** rejoint le terrain
  d'origine ; plus loin, rien ne bouge. Sur un versant plus raide que 1:2,
  ce talus ne rejoint jamais le terrain : si, quelque part, il ne l'a pas
  rejoint à une distance fixée du bord (ordre de grandeur plausible : une
  quinzaine de mètres), la route est **refusée** de la même façon, et le
  message nomme l'endroit.
- **Le sol se peint** : deux couches de terrain de plus (terre battue,
  pavés), soit six couches. Le bord de la peinture est irrégulier, tiré d'un
  bruit dont la graine est celle de l'implantation. Aucune touffe ne reste
  sur l'emprise de la route.
- **Tout se fait à l'exécution, sur une copie** du `TerrainData` :
  l'asset `Ville/Terrain_<implantation>.asset` reste intact. Même graine et
  mêmes gestes donnent le même terrain, à l'octet près.

Les paramètres du profil (pas, fenêtre de lissage, pente maximale, pente et
largeur maximale du talus, amplitude du bruit de bord) vivent **à un seul endroit** : Python les
écrit dans le fichier des gestes, Unity les y lit. Aucun des deux ne les
recopie en dur.

**Unity ne se juge pas lui-même.** Comme à la V0, la référence est
recalculée en Python, depuis la grille d'origine `hauteurs.f32` et avec le
découpage en triangles d'Unity (`terrain.interpolee`) : Unity exporte les
points de l'axe qu'il a échantillonnés et les hauteurs qu'il a obtenues ;
Python recalcule le profil attendu et compare. Un profil que le code C#
déclarerait et que le même code vérifierait serait un contrôle nommé
d'après sa cible (AGENTS.md, règle 2).

**Le geste du joueur passe par la même fonction que le contrôle.** Le clic
ne fait que convertir un point d'écran en point du terrain et appeler
l'entrée que le jeu de gestes appelle aussi. Clic gauche : poser un point ;
Entrée : valider ; Échap : annuler ; le refus s'affiche à l'écran. La
caméra reste celle de la scène (la caméra de city builder est le lot 265) ;
le contrôle peut ajouter à la scène l'orbite existante (`VillageV2Visit`)
pour viser, sans la modifier.

Les coordonnées des gestes sont celles de `paysage.py` (repère Blender) ;
Unity les reçoit par la même conversion que `DesertCityTerrain.P`.

## Périmètre

En écriture : `local3d/desert/routes.py` (nouveau : jeu de gestes dérivé
des données, paramètres, profil de référence, jugement du rapport Unity),
`local3d/atelier_desert.py` (l'action `routes`, et ses entrées dans
`ACTIONS` et `LOGS`), `unity/Assets/ForgeLocal3D/Desert/DesertRoads.cs` et
`unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs` (nouveaux, avec leurs
`.meta` : la pose d'une route sur la copie du terrain, et le geste du
joueur), `unity/Assets/ForgeLocal3D/Editor/DesertCityRoads.cs` (nouveau,
avec son `.meta` : le contrôle en Play, ses contre-épreuves, ses captures
et son rapport), `unity/Packages/manifest.json` et
`unity/Packages/packages-lock.json` (le seul ajout de `com.unity.splines`,
en version fixée, celle que le registre Unity propose pour 6000.0.43f1),
`local3d/desert/README.md` (une section « étape 2 — les routes ») et
`local3d/desert/VILLE.md` (seulement ce que V1 a appris, sous la forme de
la liste « pièges à ne pas refaire » de l'étape 1 ; jamais l'état du lot).

`unity/Assets/ForgeLocal3D/Editor/DesertCityTerrain.cs` entre aussi dans ce
périmètre, **dans sa seule fonction `Build`** : poser dans la scène le
composant des routes et créer les deux couches `Ville_terre_battue` et
`Ville_paves` (textures `chemin_sable` et `chemin_dalle`, déjà importées
sous `Desert/Textures/`). `Check`, `Measure`, `Transport`, `Seam` et les six
contre-épreuves de la V0 ne changent pas d'un caractère.

Les fichiers que les commandes régénèrent entrent avec eux : les deux scènes
`unity/Assets/ForgeLocal3D/Desert/Scenes/Forge_Desert_Ville_*.unity`, les
deux nouvelles couches sous `unity/Assets/ForgeLocal3D/Desert/Ville/Couches/`
(avec leurs `.meta`), et sous `local3d/desert/sorties/ville/<implantation>/routes/`
le fichier des gestes, le rapport Unity, le jugement Python et **au plus
quatre captures par implantation**.

Tout autre chemin est interdit, nommément : `local3d/desert/paysage.py`,
`local3d/desert/terrain.py`, `local3d/desert/textures.py`,
`local3d/desert/assets.py`, `local3d/desert/fabriquer.py`,
`local3d/desert/verifier.py`, `local3d/desert/urbanisme.py`,
`local3d/desert/recette.json`, `unity/Assets/ForgeLocal3D/Desert/Ville/Terrain_*.asset`,
`unity/Assets/ForgeLocal3D/Citadelle/` en entier (dont `CitadelTraversal.cs`,
réutilisé tel quel), les autres scripts de `unity/Assets/ForgeLocal3D/Editor/`
(`DesertTraversalCheck.cs`, `CitadelTerrainSample.cs`,
`CitadelEditorBridge.cs`…), `unity/Assets/Vendor/`, `unity/ProjectSettings/`,
tout `sim/`, `vues/`, `forge/`, `outils/`, `atelier/`, `.github/`,
`atelier.toml`, `AGENTS.md`, `OBJECTIF.md`, `docs/`, et les autres briefs.
La fiche 263 relève du périmètre implicite de la PR de lot ; aucune autre
fiche ni prose de `ROADMAP.md` ne change.

## Conditions de succès

Ces contrôles sont **locaux** : ils demandent Unity 6000.0.43f1 et la V0
reproduite. La CI GitHub ne les joue pas ; la PR joint le jugement JSON et
les captures, regardées. Une seule commande les porte tous, et elle sort en
code non nul au premier défaut :

```powershell
py local3d/atelier_desert.py routes
```

Elle joue les deux implantations, ou une seule avec `--disposition`.

### SC1 — Le jeu de gestes sort des données, et un jeu vide échoue

`routes.py` écrit le fichier des gestes de chaque implantation. Il contient
au moins une route de chacune de ces cinq familles, chacune **vérifiée sur
la grille d'origine** au moment où elle est tirée — jamais supposée :

- **anciennes rues** : les rues publiques au sol de `paysage.plan` (ni
  seuils, ni ruelles, ni liaisons), leurs points de passage repris comme
  points du joueur ;
- **plaine neuve** : une route dont tous les points sont à plus de 20 m de
  toute rue de `paysage.plan`, là où le terrain n'a jamais été sculpté ;
- **flanc de dune** : une route dont la pente en long, sur la grille, reste
  sous 12 %, et dont la pente en travers est comprise entre 20 % et 40 % sur
  au moins un tiers de sa longueur — il faut un talus, et il peut se
  refermer ;
- **trop raide en long** : une route dont la pente en long dépasse 30 % sur
  au moins 10 m (bord de la table de grès, ou montée droite dans une dune) ;
- **trop raide en travers** : une route presque de niveau en long, mais dont
  la pente en travers dépasse 60 % sur au moins 10 m (face d'avalanche d'une
  dune) — son talus ne peut pas se refermer.

Tous les dénombrements du rapport (routes posées, refusées, échantillons)
dérivent de ce fichier. Contre-épreuve : un fichier de gestes vide, ou
privé d'une famille, fait échouer la commande avec un message qui la nomme.

### SC2 — Le terrain sous l'axe suit le profil de référence

Pour chaque route posée, en chaque échantillon de l'axe : la hauteur du
terrain modifié (`SampleHeight`) et celle de la collision (rayon vertical)
sont à **±3 cm** du profil que Python recalcule depuis `hauteurs.f32`. La
pente mesurée sur le terrain modifié, d'un échantillon au suivant, ne
dépasse **12 %** nulle part. Le rapport donne la médiane, le 95ᵉ centile et
le maximum de l'écart, par implantation.

Contre-épreuve : Unity pose une route avec son profil relevé de **20 cm** ;
le jugement doit rougir, puis la route est retirée et le jugement repasse.

### SC3 — Le talus tient 1:2, et rien ne bouge au-delà

Sur des coupes en travers tous les 5 m le long de chaque route posée : entre
le bord de la route et le terrain d'origine, aucune pente ne dépasse 1:2
(50 %, à la quantification 16 bits près). Tout sommet de la grille hors de
l'emprise déclarée (largeur plus talus) garde **exactement** sa hauteur
d'origine.

Contre-épreuve : un sommet hors de l'emprise, relevé de 10 cm sur la copie,
fait rougir.

### SC4 — Les routes trop raides sont refusées, et le terrain n'a pas bougé

Chaque route des deux familles « trop raide » est refusée ; le message dit
laquelle des deux règles l'a refusée (pente en long, ou talus qui ne se
referme pas), la valeur mesurée et sa position le long de la route. Les
hauteurs, les couches et les touffes de la copie sont **identiques octet
pour octet** avant et après la tentative.

Contre-épreuve : la pente maximale passée de 12 % à 40 % dans les
paramètres, la route « trop raide en long » est posée — le contrôle de
refus doit rougir, puis tout est restauré et il repasse.

### SC5 — Le sol est peint, sans touffe

Sous l'axe de chaque route posée, la couche de son revêtement pèse plus que
chacune des cinq autres. Hors de l'emprise plus l'amplitude du bruit de
bord, les poids des six couches sont ceux d'origine. Aucune touffe sur
l'emprise. Les quatre couches de la V0 gardent leur ordre et leurs poids
hors des routes.

Contre-épreuves : les deux nouvelles couches échangées → rougit ; une touffe
posée sur une route → rougit.

### SC6 — Le marcheur parcourt chaque route, et un mur l'arrête

`CitadelTraversal` (sans modification) parcourt chaque route posée d'un
bout à l'autre, sur la collision du terrain modifié, sans téléportation :
aucun pas ne déplace le personnage de plus que sa vitesse le permet, et il
atteint la dernière extrémité à moins d'un mètre.

Contre-épreuve : un mur (collision en boîte) posé en travers d'une route
arrête le marcheur avant la fin ; le contrôle doit le constater, puis le mur
est retiré.

### SC7 — Même graine, mêmes gestes, même terrain ; l'asset reste intact

Le jeu de gestes est posé deux fois, sur deux copies fraîches : l'empreinte
(SHA-256 des hauteurs, des couches et des touffes) est la même. Posé avec
une autre graine, l'empreinte des couches diffère (le bruit de bord change).
Les hauteurs, couches et touffes de l'asset `Terrain_<implantation>.asset`
lues à la fin sont identiques à celles lues au début.

### SC8 — Le clic du joueur passe par la même entrée

Pour une route de la famille « plaine neuve », le contrôle projette ses
points à l'écran avec la caméra de la scène, les donne au gestionnaire de
clic de `DesertRoadTool`, puis valide : les points obtenus sont à moins de
0,5 m des points voulus, et l'empreinte du terrain est celle de la même
route posée par le jeu de gestes.

### SC9 — Captures, regardées

Par implantation, au plus quatre captures sous `routes/captures/` : route
sur la plaine, route à flanc de dune (talus visible), bord peint vu de près,
message de refus à l'écran. Chaque capture n'est pas uniforme (écart-type
des pixels non nul, mesuré par la commande). Celui qui livre les regarde et
dit, dans la PR, ce qu'il y a vu.

### SC10 — La V0 ne régresse pas

```powershell
py local3d/atelier_desert.py terrain --force
py -m atelier feuille valider --projet .
```

`terrain` reste valide sur les deux implantations, avec ses six
contre-épreuves, après le passage de `routes`.

## Hors périmètre

- les carrefours, l'accroche d'une extrémité à une route existante et le
  graphe des routes : c'est le lot 264 ;
- la caméra de city builder : c'est le lot 265 ;
- les matériaux photographiés des routes : c'est le lot 267 — ce lot-ci
  prend les textures procédurales `chemin_sable` et `chemin_dalle` telles
  qu'elles sont ;
- les ponts, les murs de soutènement, les escaliers : une route trop raide
  est refusée, pas aménagée ;
- enregistrer une partie, ou recharger une ville tracée : le déterminisme de
  SC7 suffit ici ; la démo qui rejoue les gestes est le lot 278 ;
- mesurer la tenue à 60 images/s : c'est le lot 276 ;
- modifier `paysage.py` ou `terrain.py`, donc le relief et la grille de la
  V0 ;
- toucher `sim/`, un test existant, ou calibrer un seuil après avoir vu une
  mesure.
