# Lot #548 — La carte trace ses contours, nomme ses villes et se cadre
Jalon : J3 · Machine : pc · Taille prévue : 250 lignes

## But
La carte de 1400 que pose `CarteDessinee` trace le bord de chacun de ses 746 anneaux servis, trous compris, écrit le nom de chacune de ses 57 villes à sa place, et apporte sa propre caméra, vue de dessus et nord en haut, qui tient toute la carte dans le champ quelle que soit la forme de la fenêtre.

## Le joueur
Sur la carte de 1400 dans Unity, le joueur voit où finit une cellule et où commence la suivante, et retrouve ses repères par les noms : Paris, Constantinople, Gênes. Il voit toute l'Europe d'un coup, sans chercher la carte avec la caméra. C'est le geste du jalon J3 « ouvrir sa carte » (#403) qui se prépare, avant d'y choisir sa terre (#404), puis d'y régler sa part et d'ouvrir son grenier (#405). Dans ce lot, seule la photo montre la carte : le sous-lot 3 de #523 (la scène `Forge_Carte`) la rendra ouvrable en jeu, avec la caméra créée ici. Sous-lot 2 de #523. Il dépend de #547 (`CarteDessinee`), livré.

## Règle du monde
Sans objet : lot de vue. Il lit, sans rien calculer du monde, « La carte et les terres servies, vue dérivée » de `jeu/sim/MODELE.md` : les anneaux de chaque `contour` et les `villes` (`nom`, `x_m`, `y_m`) de chaque cellule, tels que servis. Aucun nom de ville n'est inventé ni déplacé. Une ville que le service ne place pas (Venise, dans `villes_hors_carte`) n'est pas écrite.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/CarteDessinee.cs
3d/unity/Assets/ForgeLocal3D/Pont/TriangulationDeCarte.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/CarteDessineeTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot548.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot548.cs.meta
docs/briefs/548-la-carte-trace-ses-contours-nomme-ses-villes-et.md

Tout autre chemin est interdit. Précisions :

- **Une seule conversion.** Dans `TriangulationDeCarte.cs`, la seule ligne changée rend `Point(double x, double y, PointCarte origine)` `internal` au lieu de `private`. Contours et noms passent par elle, avec l'`Origine` de la `CarteMaillee` : ils tombent ainsi exactement sur les cellules, en km autour du centre de la carte, x vers l'est et z vers le nord.
- **La lecture rend aussi la carte lue.** Le résultat de la tâche de `CarteDessinee` porte la `CarteLue` en plus de la `CarteMaillee` ; `CellulesServies` en reste dérivé comme aujourd'hui.
- **Contours.** Ils sont posés par `Poser`, après les cellules, sous un enfant `Contours de la carte`. Il y a un objet `Contour <cell_id>.<rang>` par anneau, avec un `rang` qui compte de 0 dans la cellule. L'ordre est celui des cellules servies, puis des polygones, l'extérieur avant ses trous. Chaque objet porte un `LineRenderer` avec `useWorldSpace = false` et `loop = false`, car l'anneau est déjà fermé comme servi. Ses positions sont les points de l'anneau, tous et dans l'ordre, à la hauteur locale `HAUTEUR_CONTOUR = 0.5f`. La largeur vaut `LARGEUR_CONTOUR = 4f` km et il ne porte pas d'ombre. Un seul matériau sombre sert à tous les contours. Il est copié du matériau par défaut, comme les cellules, et ajouté à `crees`.
- **Noms.** Ils sont posés par `Poser` sous un enfant `Villes de la carte`. Il y a un objet `Ville <nom>` par ville, dans l'ordre des cellules puis des villes servies. Chaque objet porte un `TextMesh` comme dans `DesertRoadTool` : police `LegacyRuntime.ttf`, `font.material`, `anchor = MiddleCenter`, noir. Il est posé à la position convertie de la ville, à la hauteur `HAUTEUR_NOM = 1f`, avec une rotation `Euler(90, 0, 0)` pour qu'on le lise d'en haut, nord en haut. Le codeur règle `characterSize` pour qu'une ligne fasse environ 40 km à la photo, et dit la valeur retenue. **Ni `Text` d'UI ni `MeshFilter` hors des cellules** : les tests de #547 comptent les `MeshFilter` sous la carte, et ils exigent qu'aucun `Text` actif ne reste une fois la carte posée.
- **Caméra.** Si `camera` est nulle au `Demarrer`, le composant crée un enfant `Caméra de la carte` qui porte une `Camera`, l'affecte à `camera`, puis construit la toile dessus (`ScreenSpaceCamera`, comme aujourd'hui avec une caméra donnée). Cette caméra est orthographique, fond uni bleu sombre (la mer), proche 1, lointain 2 000. Une fois la carte posée, et à chaque `Pas` ensuite (la fenêtre peut changer de forme), le composant la cadre :
  - position au-dessus du centre de la boîte des cellules (`transform.TransformPoint`), à `HAUTEUR_CAMERA = 1000f` ;
  - rotation `Euler(90, 0, 0)` ;
  - `orthographicSize = max(demi-profondeur, demi-largeur / camera.aspect) × 1,03`.

  Une caméra **donnée** n'est jamais touchée : pas de cadrage, pas de création. C'est le cas de la capture de #547, qui reste ainsi juste. La carte est supposée ni tournée ni mise à l'échelle.
- **Sans carte**, ou sans matériau par défaut : ni contour ni nom. La caméra créée existe et montre le message.
- **Tests** : de nouveaux cas, ajoutés à `CarteDessineeTests.cs`. Ils réutilisent `Servir`, `Attendue`, `Poser` et `Lire`. L'attendu se dérive de la fixture : anneaux, points et villes viennent de la `CarteLue` lue par `ClientCarte`, l'origine de `Mailler`, et les positions de la formule `(x - origine.X) / 1000`, `(y - origine.Y) / 1000` en `float`, écrite dans le test. Aucune ligne existante n'est retirée ni changée.
- **Budget** : composant ≤ 140 lignes au total (89 aujourd'hui), cas nouveaux ≤ 85 lignes, scénario ≤ 45.

## Conditions de succès
**SC1 — compilation, suite verte, rouge d'abord.** Sur le PC, éditeur de `3d/unity/ProjectSettings/ProjectVersion.txt`, sans `-quit` : `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\pont-548.xml" -logFile "$env:TEMP\pont-548.log"`. Exiger :
- sortie 0, `failed="0"`, aucun cas ignoré ;
- les cas nouveaux ci-dessous présents ;
- tous les cas existants, dont les 5 de `CarteDessineeTests`, sous les mêmes noms et en même nombre, et verts.

Le workflow `unity` est vert. Contre-épreuve : les cas nouveaux, écrits d'abord, rougissent avec le `CarteDessinee` de #547. La PR garde ce constat.

**SC2 — un contour par anneau.** Commande SC1 avec `-testFilter Forge.Pont.Tests.CarteDessineeTests.Chaque_anneau_servi_a_son_contour`. Après une lecture complète, `Contours de la carte` porte autant de `LineRenderer` que d'anneaux dérivés : 746, dont 71 trous. Les noms suivent `Contour <cell_id>.<rang>` dans l'ordre servi. Chaque `positionCount` égale le nombre de points de son anneau, 19 789 au total. Chaque position égale par `==` le point converti, à `y == HAUTEUR_CONTOUR`. `useWorldSpace` et `loop` sont faux. Aucun `MeshFilter` n'est posé hors de `Cellules de la carte`. Contre-épreuves, chacune fait rougir ce cas :
- oublier les trous ;
- refermer l'anneau une seconde fois ;
- convertir sans l'origine.

**SC3 — un nom par ville.** `-testFilter Forge.Pont.Tests.CarteDessineeTests.Chaque_ville_servie_a_son_nom`. `Villes de la carte` porte autant de `TextMesh` que de villes dérivées : 57. Leurs `text` sont, dans l'ordre servi, les noms servis, tous distincts, dont `Constantinople`. Chaque `localPosition` égale par `==` la position convertie, à `y == HAUTEUR_NOM`. La rotation vaut `Euler(90, 0, 0)`. Aucun `Text` d'UI actif sous la carte. Contre-épreuve : sauter les villes d'une cellule, ou les placer au centre de leur cellule, fait rougir ce cas.

**SC4 — toute la carte dans le champ.** `-testFilter Forge.Pont.Tests.CarteDessineeTests.La_camera_cadre_toute_la_carte`. La carte est posée en (1 000 ; 50 ; −2 000) et sans caméra donnée. Après la pose :
- un seul enfant `Caméra de la carte` existe, `carte.camera` est cette caméra, elle est orthographique, et la toile est sur elle ;
- on prend tour à tour `camera.aspect` = 16/9, 4/3 et 0,5, avec un `Pas` après chaque changement ;
- à chaque fois, les quatre coins de la boîte dérivée des sommets attendus (en monde) ont un `WorldToViewportPoint` dans [0 ; 1] en x et en y, et une profondeur entre proche et lointain ;
- sur au moins un axe, les coins couvrent au moins 0,9 du champ, pour que la carte remplisse l'écran ;
- le coin nord est plus haut à l'écran que le coin sud.

Contre-épreuves, chacune fait rougir ce cas :
- ne cadrer que sur la largeur (échoue à 0,5) ;
- ignorer la position de la carte ;
- une caméra à 100 000 km ;
- le sud en haut.

**SC5 — sans carte, ni contour ni nom ; une caméra donnée reste où elle est.** `-testFilter Forge.Pont.Tests.CarteDessineeTests.Sans_carte_ni_contour_ni_nom` : sans service, après une lecture, aucun `LineRenderer` ni `TextMesh` sous la carte, et `Caméra de la carte` existe. `-testFilter Forge.Pont.Tests.CarteDessineeTests.Une_camera_donnee_n_est_pas_cadree` : on donne une caméra hors de la carte, posée en perspective en (5 ; 6 ; 7). Après la pose et cinq `Pas`, sa position, sa rotation et `orthographic` sont inchangées, et aucune `Caméra de la carte` n'est créée.

**SC6 — la photo est prise, celle de #547 aussi.** `Unity.exe -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeCaptures "$env:TEMP\cap548" -forgeLot 548 -logFile "$env:TEMP\cap548.log"`. Exiger :
- sortie 0 ;
- `CAPTURE_SCENARIOS lot 548 : 1` ;
- un `CAPTURE_SCENARIO_OK` pour `Forge_Desert_Ville_ksar_des_sept_puits--carte-contours-et-villes.png` ;
- aucun `CAPTURE : le scénario`.

La même commande avec `-forgeLot 547` reste à `CAPTURE_SCENARIO_OK`. Contre-épreuve : sans nom posé, le scénario lève et la commande sort à 1. La PR le dit.

**SC7 — périmètre et budget.** `git diff --name-only origin/master...HEAD` ne nomme que le périmètre. `git diff --numstat origin/master...HEAD` totalise moins de 300 lignes, brief compris. `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/ | grep -c '^-[^-]'` affiche `0`. `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/TriangulationDeCarte.cs | grep -c '^[-+][^-+]'` affiche `2`.

## Hors périmètre
Hors périmètre :
- scène `Forge_Carte`, build settings et lanceur (sous-lot 3 de #523, puis #403) ;
- zoom, déplacement de la caméra, survol, panneau et `/monde` ;
- choix de la terre (#404), part et grenier (#405) ;
- liste des villes hors carte ;
- taille des noms selon la population ;
- noms des puissances ou des maisons.

Aucun changement de `ClientCarte`, `MaillageDeCarte`, `PanneauLieu`, `ForgeCapture`, `Lot547.cs`, des tests existants, des asmdef, de `ProjectSettings/`, de `jeu/` ni de `MODELE.md`. Dans `TriangulationDeCarte.cs`, rien d'autre que la visibilité de `Point`. Aucun chemin protégé de la chaîne.

## Photo
La carte de 1400 entière, cadrée par sa propre caméra, nord en haut, sur fond de mer :
- les 596 cellules à leurs couleurs ;
- le bord sombre de chaque cellule et de chaque enclave ;
- les 57 noms de villes à leur place, lisibles.

Le plan fixe (le désert) sert de comparaison.

Scénario `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot548.cs`, `[ScenarioDeCapture(548, "carte-contours-et-villes")]`. ForgeCapture a lancé le service (graine 0, port 8000) et ouvert la scène du désert. Le scénario :
1. crée un objet `Carte de 1400` en (0 ; 20 000 ; 0) et y ajoute `CarteDessinee` **sans** lui donner de caméra : le composant crée la sienne ;
2. attend image par image que `CellulesServies >= 0`, au plus 30 s en `Time.realtimeSinceStartupAsDouble`, et lève sinon avec `TexteAffiche`. Il lève aussi dans trois cas :
   - `CellulesPosees` vaut 0 ou diffère de `CellulesServies` ;
   - aucun `LineRenderer` sous la carte ;
   - aucun `TextMesh` sous la carte ;
3. règle `carte.camera.aspect = 1600f / 900f`, la forme de la photo, et laisse passer une image pour que le composant recadre ;
4. éteint ce qui gêne, comme `Lot547` :
   - `DesertCityCamera`, `VillageV2Visit` et `DesertEnvironment` ;
   - `RenderSettings.fog` ;
   - `Panneau des routes` ;
5. fait `camera.CopyFrom(carte.camera)` sur la caméra reçue, remet son `aspect` à 1600/900 et éteint `carte.camera` ;
6. laisse passer 10 images et lève si la caméra reçue a bougé.

À 1 000 km au-dessus de la carte, avec un lointain de 2 000, le désert reste hors du champ. Le codeur regarde le PNG lui-même et dit dans la PR ce qu'il y voit : la carte entière et non coupée, les bords visibles, les noms lisibles, et ceux qui se chevauchent, le cas échéant.
