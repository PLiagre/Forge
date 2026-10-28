# Lot #701 — La ville ouverte depuis la carte suit le siège, même dans l'éditeur
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Quand la carte ouvre la capitale du joueur, la ville s'ouvre sur la cellule du siège servie par le service, dans l'éditeur comme dans le jeu bâti.

## Le joueur
Le joueur qui choisit l'émirat du Zab dans le cabinet voit, au tick suivant, la carte céder la place à Biskra : sa ville et le panneau « Cellule 10103 », jamais le ksar de démonstration. C'est le geste de J4 « passer de la carte à sa ville d'un geste » (`CAP.md`). Aujourd'hui ce passage ouvre 1175 dans l'éditeur, où tournent toutes les épreuves et captures. Il ouvre aussi le ksar sans cellule dans le jeu bâti lancé par `Jouer.cmd --carte`, qui passe `-forgeCarte`. Ce lot rend le passage vrai partout, et l'épreuve de la capitale (#684, sous-lots 2 et 3) pourra le juger.

Dépend de : rien qui manque. `PassageALaCapitale` (#689, #690), `OuvertureDeLaCapitale.Decider` (#687), `DesertRoadTool.Lancer` (#688), `PanneauLieu.Ouvrir` (#686), le cabinet et `Lot549.Ouvrir` sont sur la base (6cdfd49).

## Règle du monde
Sans objet : lot de vue. Aucune règle, constante ni donnée ne change. La cellule vient du siège de `/maison`, comme le dit « Les maisons servies, vue dérivée » de `jeu/sim/MODELE.md`, déjà lu par `AiguillageDeCapitale`. Le choix suit « Les intentions du joueur » : reçu, puis `maison_du_joueur` au tick suivant. `cell_id` reste la seule clé.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/PassageALaCapitale.cs
3d/unity/Assets/ForgeLocal3D/Pont/OuvertureDeLaCapitale.cs
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PassageALaCapitaleTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/CapitaleDuJoueurTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot690.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot701.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot701.cs.meta
docs/briefs/701-la-ville-ouverte-depuis-la-carte-suit-le-siege-m.md

Tout autre chemin est interdit. Budget indicatif : 25 lignes de code, 65 de tests ajoutés, 12 dans `Lot690.cs`, 115 de capture, 2 de `.meta`, le reste pour ce brief. Ajouts et retraits cumulés restent sous 300 lignes : écrire serré.

Le mécanisme, à suivre tel quel :
- **La remise** (dans `PassageALaCapitale`, statique) : juste avant `ChargerScene(capitale.Scene)`, le passage retient la scène et `capitale.Cellule`, lue dans `/maison` par l'aiguillage. `public static long? PrendreCelluleRemise(string scene)` rend la cellule si la scène correspond, `null` sinon, et efface la remise dans les deux cas : une seule ville en profite. Rien d'autre ne pose de remise : Bar, Zab déjà confirmé à l'ouverture, ni une absence.
- **La décision** : une surcharge `OuvertureDeLaCapitale.Decider(arguments, editeur, long? remise, aiguillage)`. Une remise non nulle passe avant tout : `-forgeCarte`, `-forgeCell`, l'éditeur. Elle rend `Ville` sur cette cellule sans consulter l'aiguillage. Une remise négative lève `ArgumentOutOfRangeException` avant toute requête. Une remise nulle donne exactement l'ancienne décision : la surcharge à trois paramètres appelle la nouvelle avec `null` et garde son comportement.
- **La ville** : `DesertRoadTool.Lancer(arguments, editeur, panneau, long? remise = null)` passe la remise à `Decider`. `Awake` passe `PassageALaCapitale.PrendreCelluleRemise(gameObject.scene.name)`. Les appels existants (Lot688, DesertCityRelief…) ne changent pas.
- Une scène ouverte au lancement n'a pas de remise. Sans `-forgeCell`, l'éditeur ouvre donc toujours 1175 : les captures et les contrôles ne changent pas.

## Conditions de succès
Sur le PC, éditeur fermé, depuis la racine : `$u = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. `CAPTURE` = `& $u -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeSeed 0`, sans `-quit` ni `-nographics`, complété ci-dessous ; fichiers temporaires neufs à chaque lancement.

SC1 — La remise et la décision, en tests. Lancer `& $u -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot701-tests.xml" -logFile "$env:TEMP\lot701-tests.log"` : sortie 0, XML sans échec, `PassageALaCapitaleTests` et `CapitaleDuJoueurTests` réellement exécutés, cas neufs compris (une suite vide refuse la livraison). Les cas s'ajoutent sans retoucher les cas ni les aides existants. Chaque cas neuf commence par vider la remise : un cas existant en laisse une, car il remplace `ChargerScene`.
- Dans `PassageALaCapitaleTests` :
  - Zab confirmé : dans `ChargerScene`, la remise de la scène demandée vaut le `siege.cell_id` lu dans la fiche figée (pas un nombre écrit), et une seconde prise rend `null`.
  - Une prise par une autre scène rend `null` et efface la remise.
  - Bar, Zab déjà confirmé à l'ouverture, ou une absence : pas de remise.
- Dans `CapitaleDuJoueurTests`, avec le faux service qui sert le Zab et le compteur de `Compteur()`, comme `SansRequete` (qui appelle l'ancienne surcharge) :
  - Remise 10104 avec `Forge.exe` en éditeur, avec `-forgeCell 42` et avec `-forgeCarte` : `Ville 10104`, zéro appel.
  - Remise nulle en éditeur : 1175, comme l'ancienne surcharge.
  - Remise −1 : exception, zéro requête.

Contre-épreuves, à écrire et voir rougir avant le code : sans remise posée, le cas du Zab rougit ; une remise qui ne s'efface pas fait rougir la seconde prise ; une remise placée après `-forgeCarte` fait rougir ce cas.

SC2 — Le Zab choisi dans le cabinet ouvre Biskra. `CAPTURE -forgeLot 701 -forgeTicks 3 -forgeCaptures "$env:TEMP\lot701" -logFile "$env:TEMP\lot701.log"` : sortie 0, trace `CAPTURE_701` (tick avant/après, maison, cellule de l'outil, première ligne du panneau). Le scénario `[ScenarioDeCapture(701, "zab-biskra-depuis-la-carte")]` :
1. Il exige que le panneau du lieu de la première scène commence par `Cellule 1175 · tick ` : la scène ouverte sans `-forgeCell` garde 1175.
2. Il ouvre la carte par `Lot549.Ouvrir` et exige un seul passage, le cabinet construit et une `LecturePartie` prête. Pour l'attente et les lectures, il réutilise les aides de `Lot690` : seule leur visibilité passe de `private` à `internal`, sans autre changement.
3. Il trouve l'unique fiche « Émirat du Zab » et la choisit par `cabinet.Partie.Choisir`. Il attend le reçu accepté. Puis il laisse passer au moins deux périodes du passage, service joignable, `Absence` nulle et aucune scène demandée : le passage a vu le départ.
4. Il pousse un seul `POST /tick?n=1`. Il attend que `passage.SceneDemandee` vaille `TerresAvecKit.Scenes` du Zab, et exige `/monde` au tick N+1 avec la maison choisie.
5. Le chargement : le harnais photographie la caméra de la première scène, qu'un chargement unique détruirait. Le scénario remplace donc `passage.ChargerScene`, avant le tick, par un chargement de cette scène **à côté** (`LoadSceneMode.Additive`), sans rien décider à la place du passage. Une fois la scène chargée, il la rend active, puis décharge `Forge_Carte`.
6. Dans la scène neuve (handle différent de celle de la caméra), il prend l'unique `DesertRoadTool`, son `PanneauLieu` et sa `DesertCityCamera`. Il exige que `outil.Cellule` vaille le siège de `cabinet.Partie.Maison` et le `CellId` de la fiche, différent de 1175. Il exige aussi `outil.TickOuverture == N+1`. Le panneau doit commencer par `Cellule <siège> · tick <N+1>\n` en au plus 15 s, et ne jamais dire `Cellule 1175` (vérifié à chaque image).

Chaque attente a une borne d'au plus 30 s, et toute absence échoue en nommant sa cause. Contre-épreuve : `CAPTURE -forgeLot 701 -forge701SansRemise …` jette la remise par `PrendreCelluleRemise` juste avant le chargement (drapeau lu dans `Lot701.cs` seul). Il doit sortir 1, et le diagnostic doit dire que la ville s'est ouverte sur 1175.

SC3 — Rien d'autre ne bouge. `CAPTURE -forgeLot 688 …` et `CAPTURE -forgeLot 690 …` sortent 0 : 688 vérifie que le lancement sans argument suit l'éditeur, 690 que ses aides restent justes. Ensuite, `git diff --check`, `--name-only`, `--numstat` et `git ls-files --others --exclude-standard` : seuls les chemins du périmètre, moins de 300 lignes, brief compris. Contre-épreuve : un cas existant modifié, une capture autre que 690 touchée, ou un `Lot690.cs` changé au-delà des mots `private`/`internal` refuse la livraison.

## Hors périmètre
- La session de l'épreuve et son verdict (#684, sous-lots 2 et 3).
- Le retour de la ville à la carte et l'horloge qui suit la vue (#410).
- Le lanceur, le relief, l'aiguillage, `TerresAvecKit`, `PanneauLieu`, `CabinetDeCarte`.
- Le harnais `ForgeCapture`, les scènes, les fixtures, `jeu/`.
- Aucun changement de la règle de l'éditeur pour une scène ouverte au lancement.

## Photo
Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot701.cs` et laisse Unity générer son `.meta`. Après SC2, l'outil et la caméra de la ville neuve passent en `automatique`. Le scénario appelle `VueEnsemble()` (touche F) et attend dix images. Il copie la pose de cette caméra sur la caméra reçue (`camera.CopyFrom`), puis éteint la caméra neuve. Il rebranche la seule toile du `PanneauLieu` neuf sur la caméra reçue, sans changer son texte, sa place ni son mode `ScreenSpaceCamera`. Il exige les coins du texte dans le champ, attend dix images et revérifie la cellule et le texte. La photo montre Biskra en vue d'ensemble, sur le relief de sa cellule (#697), avec le panneau « Cellule 10103 · tick N+1 » en haut à gauche (cellule mesurée à la graine 0 par #688). Le codeur ouvre lui-même `*--zab-biskra-depuis-la-carte.png` : pas de carte, pas de ksar de 1175, panneau lisible. Une image vide, le désert de 1175 ou un panneau hors champ refusent la livraison, même avec sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, la sortie de la contre-épreuve sans remise et ce que montre l'image.
