# Lot #738 — Les rues de 1400 se dessinent sur le sable
Jalon : J4 · Machine : pc · Taille prévue : 291 lignes

## But
Dans sa capitale, le joueur voit les rues et les ruelles de la ville de 1400 que tient le monde. Elles sont posées en rubans de terre battue sur le sable, sans toucher au terrain, et suivent le sol après chaque tick qui le change.
## Le joueur
« Le joueur voit les rues de sa ville, pas seulement l'espace entre les maisons. » Ce sous-lot de #412 sert le geste du J4 : entrer dans sa capitale en 3D et y marcher. À Biskra, les sept rues qui partent de la place ont désormais une chaussée de terre battue large de 6 m, bordée par les 33 maisons posées par #737. À hauteur d'homme, le joueur suit une rue au lieu de deviner un passage dans le sable. Quand il trace une route sur une rue de 1400, la chaussée reste posée sur le sol nivelé après le tick. Elle ne flotte pas et ne s'enterre pas. Le panneau dit combien de rues sont dessinées et combien sont coupées au bord du terrain. Dépend de : #735 (`PlanLu.Base`, `RueDeBase`) et #737 (`DesertMaisons1400`, branché dans `DesertRoadTool`), tous deux livrés sur la base. Rien n'est attendu de J3.
## Règle du monde
Sans objet : lot de vue. `jeu/sim/MODELE.md`, « Le plan de base », reste inchangé : la base est dérivée de la population d'amorçage, distincte des rues de geste, sans effet sur le tick. Unity lit `PlanLu.Base.Rues` (points, `LargeurM`, `Sorte`) et ne décide rien : ni tracé, ni largeur, ni prolongement. Mesure du 21/10 (graine 0, 596 bourgs) : 22 591 rues de base, toutes de deux points, 2 037 principales de 6 m et 20 554 ruelles de 3 m. 2 079 d'entre elles, dans 99 cellules, sortent du terrain utile (511 m) ; la plus lointaine va jusqu'à 1 550 m. Biskra (10103) a 7 principales d'environ 15 m, qui partent du bord de la place de ±50 m ; 1175 a 1 principale de 165 m et 8 ruelles ; Paris (10322) a 259 rues.
## Périmètre
3d/unity/Assets/ForgeLocal3D/Desert/DesertRues1400.cs
3d/unity/Assets/ForgeLocal3D/Desert/DesertRues1400.cs.meta
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Editor/DesertRues1400Preuve.cs
3d/unity/Assets/ForgeLocal3D/Editor/DesertRues1400Preuve.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot738.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot738.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot737.cs
docs/briefs/738-les-rues-de-1400-se-dessinent-sur-le-sable.md

Tout autre chemin est interdit. Budget, ajouts et suppressions compris : 75 lignes de dessinateur, 8 de branchement, 55 de preuve, 48 de capture, 4 dans Lot737, 6 de métadonnées et 95 de brief, soit 291 au plus. Unity crée les trois `.meta`. Aucune scène, aucun prefab, aucun asset de couche n'est régénéré.

`DesertRues1400` imite `DesertMaisons1400` : ce n'est pas un composant, et sa racine « Rues de 1400 » est sœur de « Maisons de 1400 », sous l'outil. Il reçoit le terrain et la couche `roads.terreBattue`. Le matériau part du matériau par défaut du pipeline, comme dans `DesertParcelles`. Il prend la `diffuseTexture` de la couche, sa teinte `diffuseRemapMax` et son lissé. Il ne projette pas d'ombre et n'a pas de collider. S'il manque le pipeline, la couche ou sa texture, le dessin le déclare comme une absence et ne fait aucun rendu de secours.

`Dessiner(BaseDuPlan)` vide d'abord sa seule racine, avec `DestroyImmediate`, maillages compris. Une base nulle donne « Rues de 1400 : base non servie ». Pour chaque rue, dans l'ordre servi :
- La rue est refusée et nommée par son rang si elle a moins de deux points, deux points confondus ou une largeur nulle ou non finie.
- Chaque segment est découpé au carré |x|, |y| ≤ taille/2 − 1 − largeur/2. La chaussée tient donc entière sur le terrain, avec la marge de 1 m des maisons. Une rue raccourcie est « coupée » ; une rue dont il ne reste rien est « hors du terrain ».
- Chaque morceau restant devient un rectangle centré sur l'axe, de la largeur servie, à bouts carrés et sans prolongement. Les sommets forment une grille au pas de 0,25 m au plus, en long comme en travers, bords compris. Chaque sommet est posé au sol lu sous lui (`SampleHeight` plus la hauteur du terrain), plus 0,06 m. Les triangles regardent le ciel.
- Les UV valent (x, z) du monde divisés par `tileSize` de la couche. Deux rubans qui se recouvrent montrent donc la même image.
- Le maillage est en index 32 bits s'il dépasse 65 535 sommets, et il y a un objet par rue.

Le terrain n'est jamais écrit : ni hauteur, ni couche peinte, ni touffe. `DesertRues1400` expose la racine, les rues servies, dessinées, coupées et hors du terrain, les refus, l'absence et une empreinte SHA-256 de la description (rang, état, sommets en F2), comme `DesertParcelles`. Sa ligne de panneau dit « Rues de 1400 : X dessinée(s) sur Y, C coupée(s) au bord du terrain, H hors du terrain », suivie d'une ligne par refus de forme. Les rues coupées et hors du terrain sont comptées, pas listées : Paris en a des centaines. Une base sans rue donne « 0 dessinée(s) sur 0 ».

`DesertRoadTool` crée le dessinateur dans `Awake`, puis le dessine dans `DessinerBatiments`, juste avant les maisons, depuis `lu.Base`. Il est ainsi redessiné à l'ouverture (`Ouvrir()` et `Ouvrir(cellule)`), par `Rafraichir()` et dans `Attendre()`, après les rues neuves de geste, donc sur le terrain que le tick vient de changer. La ligne entre au panneau avant celle des maisons. L'outil expose `Rues1400`. `PiecesAvantMaisons`, `EmpreinteAvantMaisons`, `Batiments`, `Parcelles` et leurs racines n'en comptent rien. Dans `Lot737.cs`, le choix de « la rue bordée de maisons » devient une méthode `internal` réutilisée par son scénario, sans changer le choix. Le commentaire de tête de `DesertRues1400` dit pourquoi les rubans sont posés et le sable laissé intact (le témoin vierge de `DesertCityRelance`).
## Conditions de succès
Sur le PC Windows, depuis la racine ; `Unity.exe` désigne Unity 6000.0.43f1. Attendre chaque processus, sans `-quit`. Écrire d'abord les contrôles et constater leur rouge avant le branchement. Chaque commande exige une sortie 0 et des résultats neufs non vides. Une exception, un cas sauté ou un ancien résultat ne vaut pas réussite. Aucun test existant n'est réécrit.

SC1 — Le ruban suit le sol sans toucher le terrain. Commande : `Unity.exe -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.DesertRues1400Preuve.Verifier -logFile "$env:TEMP/lot738-rues.log"`. Le contrôle sort explicitement en 0 ou 1 et journalise chaque cas « RUES1400 ok|ECHEC ».
- Il prépare un terrain temporaire de 1024 m, décalé en hauteur, en pente, et traversé d'une crête dont la pente passe de +0,25 à −0,25. Une couche porte une petite texture.
- La base contient :
  - une principale oblique de 6 m qui franchit la crête ;
  - une ruelle de 3 m qui part de son bord ;
  - une rue qui dépasse 511 m ;
  - une rue entièrement hors du terrain ;
  - une rue d'un seul point ;
  - une rue de largeur nulle.
- Exiger les compteurs : 3 rues dessinées sur 6, dont 1 coupée, 1 hors du terrain et 2 refus nommés.
- Au centre et aux milieux d'arête de chaque triangle, l'écart ruban − sol doit valoir entre 0,01 et 0,15 m.
- Les sommets doivent rester à largeur/2 de l'axe, à 0,01 m près, et les sommets de la rue coupée dans la limite. La longueur dessinée doit valoir la longueur découpée, à un pas près.
- `DesertRoads.Empreintes(terrainData)` doit rester identique avant et après deux dessins. Le second dessin donne la même empreinte de rubans, sans doublon.

Contre-épreuves : un pas de 2 m, un décalage de 0, une demi-largeur prise pour la largeur, une rue hors du terrain dessinée sans découpe, ou une texture peinte dans le terrain font chacun échouer un cas nommé.

SC2 — Les rubans sont redessinés quand le sol change. Même commande que SC1. Le contrôle élève une bosse de 0,5 m sous la principale par `SetHeights`. Les anciens sommets, rejugés sur le nouveau sol, doivent sortir de la fenêtre de SC1 : c'est la contre-épreuve, constatée dans le test. Après un nouveau `Dessiner`, la fenêtre doit tenir et le nombre d'objets rester le même. Les cas d'absence sont aussi joués :
- une base nulle donne l'absence sans « 0 dessinée » ;
- une base sans rue donne « 0 dessinée(s) sur 0 » ;
- une couche sans texture donne une absence nommée.

Chacun vide la racine après un dessin non vide. Un objet témoin placé sous « Maisons de 1400 » reste intact.

SC3 — Biskra montre ses sept rues, et le tick les garde au sol. Commande : `Unity.exe -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 738 -forgeSeed 0 -forgeTicks 0 -forgeCaptures "$env:TEMP/lot738-photos" -logFile "$env:TEMP/lot738-photo.log"`. Les scénarios de la section Photo exigent ce qui suit.
- À Biskra, lue dans `/departs` : 7 rues dessinées sur 7, aucune coupée ni refusée. Le texte réel du panneau contient la ligne des rues et les 33 maisons de #737.
- L'empreinte du terrain après l'ouverture est celle d'une copie vierge, calculée comme le fait `DesertCityRelance`.
- Un second `Rues1400.Dessiner` laisse l'empreinte du terrain et celle des rubans inchangées.
- Après une route de geste tracée par l'outil sur l'axe d'une rue de base, puis le tick et `Attendre()` : le sol a bougé de plus de 0,10 m sous au moins un sommet du ruban. Les sommets d'avant, rejugés, sortent de la fenêtre ; ceux d'après y tiennent tous. Il y a toujours 7 rubans et 33 maisons.

Contre-épreuves : supprimer le dessin dans `Attendre`, doubler les rubans ou peindre la chaussée dans le terrain fait échouer le scénario. Les PNG doivent être neuves et ouvertes par le codeur.

SC4 — Les preuves antérieures restent entières, et le lot tient sa taille.
- Depuis `3d/`, `py local3d/atelier_desert.py relance` passe ses trois sessions (tracer, relance, vierge) ; le sable vierge reste exigé tel quel.
- `Unity.exe -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.DesertMaisons1400Preuve.Verifier -logFile "$env:TEMP/lot738-maisons.log"` passe.
- `py pc/epreuve_jalon4.py --avec-unity --sortie "$env:TEMP/lot738-j4"` donne le même verdict que sur `origin/master` ; un écart se déclare.
- La CI passe : `python3 -m pytest jeu -q`.
- `git diff --check`, `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` vérifient la forme et le périmètre.
- La somme ajouts + suppressions de `git diff --numstat origin/master`, fichiers nouveaux et brief compris, reste sous 300.

Contre-épreuve : un ruban qui creuse ou peint fait échouer la session vierge.
## Hors périmètre
Le moteur, le service, `MODELE.md`, le lecteur du plan, les maisons de #737 et leur pose (#736). Ce lot ne dessine pas :
- la place ;
- les carrefours ou les jonctions arrondies ;
- les bas-côtés, les pavés ou les rigoles ;
- un ruban sous les routes de geste, qui restent peintes dans le terrain comme avant.

Il ne prolonge pas les rues vers `vers_cell_id`, n'agrandit pas le terrain pour Paris et ne touche pas aux kits ni aux scènes. La session d'épreuve multi-cellules et son verdict sont les sous-lots suivants de #412.
## Photo
`Lot738.cs` porte trois scénarios ordonnés, qui ouvrent Biskra comme `Lot737`, avec le service du harnais en pause.
- `[ScenarioDeCapture(738, "01-biskra-de-haut")]` cadre de haut, comme Lot737, la place, les sept rubans entiers et les maisons. Le cadrage est calculé sur les bouts des rubans, et le bilan du panneau doit être lisible.
- `[ScenarioDeCapture(738, "02-rue-a-hauteur-d-homme")]` reprend la rue et la pose de Lot737 (même méthode, `Poser` puis `DesertCityCamera.Descendre()`). C'est la même rue à hauteur d'homme, sa chaussée visible au premier plan entre les façades. Exiger au moins trois sommets de ce ruban devant la caméra, dans la moitié basse de l'image, et aucune caméra dans un mur.
- `[ScenarioDeCapture(738, "03-apres-le-tick")]` choisit la rue de 02 si l'outil accepte son essai, sinon la suivante dans l'ordre servi. Il pose, vus de haut comme Lot293, des clics aux deux bouts de son axe ; puis il appelle `Valider()`, `Lot362.Tick`, puis `Attendre()`. Il fait les contrôles de SC3, puis photographie la même rue à hauteur d'homme, chaussée posée sur la route nivelée.

Attendre quelques images, puis appeler `Placer()`. Aucun décor ni faux ruban n'est ajouté pour la photo. Le codeur ouvre les trois PNG et vérifie trois choses : la chaussée est continue et se lit, elle ne flotte ni ne s'enterre visiblement, et le panneau est entier. Les images restent dans le dossier temporaire, jamais dans les assets.
