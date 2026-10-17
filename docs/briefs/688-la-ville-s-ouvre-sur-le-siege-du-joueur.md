# Lot #688 — La ville s'ouvre sur le siège du joueur
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Au lancement, la ville applique la décision de #687 : le jeu ouvre la cellule du siège du joueur, avec un panneau du lieu qui la suit dès sa première lecture ; sinon il passe à la carte de 1400, ou il affiche l'absence.

## Le joueur
Troisième sous-lot de #680 (lui-même sous-lot de #409 « Le jeu ouvre la capitale du joueur »). C'est le geste du J4 de `CAP.md` : le joueur **entre dans sa capitale en 3D**. Le joueur qui a choisi le Zab lance le jeu et entre dans Biskra : le panneau du lieu dit « Cellule 10103 », ses 3 480 habitants, et non plus le ksar de la cellule 1175. Sans terre choisie, ou sur une terre sans kit, il arrive sur la carte de 1400, où il choisit sa terre. Il sent que le jeu l'attend chez lui. Limite à dire : `pc/jouer.py` passe encore `-forgeCell` (le sous-lot 4 de #409 le retire). Ce chemin vaut donc pour le jeu bâti lancé sans argument, et le scénario de la photo le rejoue.

## Règle du monde
Sans objet : c'est un lot de vue. Le monde, son niveau de fidélité et `jeu/sim/MODELE.md` ne changent pas. La cellule vient de `-forgeCell`, ou du siège servi par `/maison` (« Les maisons servies, vue dérivée »), lu par `AiguillageDeCapitale` (#679) et décidé par `OuvertureDeLaCapitale.Decider` (#687). `cell_id` reste la seule clé spatiale.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot688.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot688.cs.meta

Tout autre chemin est interdit. `PanneauLieu`, `OuvertureDeLaCapitale`, `OuvertureDeLaCarte`, `AiguillageDeCapitale`, les scènes, `Lot584.cs` et tous les tests ne bougent pas. L'issue nomme `Lot680.cs`, le numéro du lot parent ; la chaîne photographie avec `-forgeLot 688`, donc le scénario s'écrit `Lot688.cs`, avec `[ScenarioDeCapture(688, "biskra-au-lancement")]`. Le `.meta` est généré par Unity.

Budget : environ 35 lignes dans l'outil, 130 dans le scénario, 11 de `.meta`, le reste pour ce brief.

### Ce que fait l'outil
Une méthode publique : `public Lecture<OuvertureDecidee> Lancer(string[] arguments, bool editeur, PanneauLieu panneau)`. Elle appelle `OuvertureDeLaCapitale.Decider(arguments, editeur, () => AiguillageDeCapitale.Lire(Port, DelaiAiguillage))`, où `DelaiAiguillage` vaut 5 s (le `Delai` d'1 s des gestes reste celui des gestes). Elle applique ensuite la décision, puis la rend. Le paramètre `panneau` peut être nul : la scène de l'oued n'a pas de panneau.
- **Ville(c)** : `Cellule = c`, `erreurCellule = null`, `plan` et `depot` créés sur `Port` s'ils manquent, puis `panneau?.Ouvrir(c)`. Aucun plan n'est lu ici : `Ouvrir()` le dessine, comme aujourd'hui.
- **Carte** : `SceneManager.LoadScene(decision.Scene)`.
- **LaisseeALaCarte** : rien. `OuvertureDeLaCarte` change déjà de scène.
- Pour **Carte** et **LaisseeALaCarte**, `Cellule = -1` et `erreurCellule = "La carte de 1400 s'ouvre : aucune capitale à ouvrir ici."`.
- **Absence** : `Cellule = -1` et `erreurCellule` = la cause, mot pour mot.
- Dans ces trois derniers cas, le panneau du lieu est éteint (`enabled = false`) : il ne lit rien, et `Ouvrir()` affiche `erreurCellule` sans lire aucun plan.

`Awake` remplace les lignes 91 à 93 (lecture de `-forgeCell` et clients) par `Port = PanneauLieu.DEFAULT_SERVICE_PORT;` puis `Lancer(Environment.GetCommandLineArgs(), Application.isEditor, FindFirstObjectByType<PanneauLieu>())`. L'appel reste dans `Awake`. Unity joue tous les `Awake` d'une scène avant le premier `Start`. Le panneau reçoit donc `Ouvrir(c)` avant son `Demarrer`, et aucune lecture de 1175 ne part (#686, SC1). `Start` reste `Ouvrir()`. Le commentaire d'en-tête gagne une ligne « Lot 688 ».

Ce qui change à l'écran, et seulement là :
- dans le jeu bâti sans argument, l'aiguillage décide ;
- avec un `-forgeCell` refusé, le panneau des routes affiche la même erreur, mot pour mot, mais le panneau du lieu, éteint, ne la répète plus.

Avec un `-forgeCell` valable, et dans l'éditeur sans argument (1175), le panneau lit la même cellule qu'avant, sur le même port. Les épreuves et les captures restent donc les mêmes.

## Conditions de succès
Sur le PC, éditeur fermé, depuis la racine : `$u = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. `CAPTURE` note ci-dessous la commande `& $u -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeSeed 0`, suivie des arguments indiqués. Chaque commande prend un dossier `-forgeCaptures` et un `-logFile` neufs sous `$env:TEMP`. Le code de sortie se lit, puis le journal.

**SC1 — le Zab entre dans Biskra par le chemin du lancement.** `CAPTURE -forgeLot 688` rend 0, avec les 30 ticks par défaut du harnais. Le scénario suit cet ordre, et chaque défaut lève une exception qui le nomme :
1. Le scénario trouve `DesertRoadTool`, `DesertCityCamera` (sur la caméra de la photo) et `PanneauLieu`. Le panneau commence par `Cellule 1175 · tick <T>` : la capture sans `-forgeCell` garde le ksar.
2. Il retient la pose de la caméra : `Vise`, `Cap`, `Inclinaison`, `Distance`.
3. Il lit `/departs` par `ClientDeparts` (délai `ClientDeparts.DelaiMinimal`, dans un `Task.Run`). Il y prend l'unique fiche au siège `Biskra` : tick `T`, `Id`, `CellId`.
4. Il dépose `choisir_depart` par `Lot362.Deposer`, puis joue `Lot362.Tick`.
5. `outil.Lancer(new[] { "Forge.exe" }, false, panneau)` doit rendre `Ville` à `CellId`, et `outil.Cellule` doit valoir `CellId`.
6. Puis `outil.Ouvrir()` doit être vrai, avec `TickOuverture == T + 1`.
7. En 15 s au plus, le texte du panneau doit commencer par `Cellule <CellId> · tick <T+1>\n`. Il ne contient jamais `Cellule 1175` après `Lancer` : le scénario le vérifie à chaque image.
8. La pose retenue n'a pas bougé (écart ≤ 1e-3) : l'ouverture ne déplace pas la caméra.
9. Le journal porte une ligne `CAPTURE_688` : siège, seigneurie, cellule (10103), tick, décision et première ligne du panneau.

Contre-épreuve : une version de `Lancer` qui ignore l'aiguillage rend 1175 (étape 5 rouge).

**SC2 — sans le choix, la scène passe à la carte.** `CAPTURE -forgeLot 688 -forge688SansChoix` saute l'étape 4 (le tick est joué). Il rend 1. En dix images au plus, le scénario lit la scène active : il doit trouver `Forge_Carte`, et lever `sans choix, la ville passe à la carte : scène active Forge_Carte`. Contre-épreuve : un `Lancer` qui ne charge pas la carte laisse la scène du ksar. Le message nomme alors cette scène-là, et le contrôle de SC2 (`Forge_Carte` dans le journal) rougit.

**SC3 — le panneau suit la ville.** `CAPTURE -forgeLot 688 -forge688SansPanneau` passe `null` au lieu du panneau à l'étape 5. Il rend 1 à l'étape 7, et le message cite le texte resté à `Cellule 1175`. Contre-épreuve : sans le drapeau, SC1 rend 0.

**SC4 — une absence n'ouvre aucun plan.** `CAPTURE -forgeLot 688 -forge688CelluleFautive` remplace les arguments de l'étape 5 par `Forge.exe -forgeCell abc`. `Lancer` doit rendre l'absence égale à l'erreur de `PanneauLieu.LireCellule` pour ces arguments. Le test calcule cette erreur, il ne la recopie pas. Puis `outil.Ouvrir()` doit être faux, avec `outil.Message` égal à cette erreur, `TickOuverture == -1` et `panneau.enabled` faux. Le scénario lève alors `absence : <erreur> ; aucun plan ouvert ; panneau du lieu éteint`, et rend 1. Si une seule de ces trois choses manque, il lève un autre message, qui la nomme.

**SC5 — les épreuves et les captures gardent leur cellule.**
- `py pc\epreuve_jalon1.py --sortie "$env:TEMP\f688-j1"` rend 0. Avec `--cellule 10103`, il rend 0 aussi : `-forgeCell` passe par `Decider` puis par `panneau.Ouvrir`. Avec `--decalage 1`, il rend toujours 1.
- `CAPTURE -forgeLot 584` rend 0, comme avant le lot.
- `& $u -batchmode -projectPath 3d/unity -runTests -testPlatform EditMode -testResults "$env:TEMP\f688.xml" -logFile "$env:TEMP\f688-tests.log"` : le XML ne compte aucun échec, et le relevé des cas est celui d'avant le lot.
- `git diff --name-only origin/master` ne liste que le périmètre et ce brief.

**SC6 — la photo est propre au lot.** Après SC1, `*--biskra-au-lancement.ecart.txt` vaut au moins 0,02. Le codeur, puis le relecteur, regardent l'image eux-mêmes. On doit y voir la ville entière en vue d'ensemble, le panneau du lieu `Cellule 10103` avec ses habitants, et aucun chiffre de 1175.

## Hors périmètre
- `pc/jouer.py` et ses tests (sous-lot 4 de #409) ; le relief de Biskra (sous-lot 5) ; l'épreuve Zab/Bar (sous-lot 6).
- La carte qui ouvre la capitale, ou qui dit « pas encore de kit » (#681). La ville de 1400 dessinée d'après la base (#412).
- Toute lecture asynchrone de l'aiguillage, tout changement de `PanneauLieu`, de `Decider`, des scènes, du monde ou de `MODELE.md`.

## Photo
Biskra au lancement : la ville du kit vue en entier par la caméra du joueur, et le panneau du lieu qui dit « Cellule 10103 · tick 31 », 3 480 habitants, 696 foyers de paysans. Le scénario `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot688.cs` joue SC1, puis appelle `ville.VueEnsemble()` : c'est la touche F du joueur, même point visé et même cap que l'ouverture, à 40° et 450 m. Il vérifie `Vise` (x, z) et `Cap` contre la pose retenue, puis attend dix images.

Pourquoi la vue d'ensemble, et non la place d'ouverture que nomme l'issue ? Mesuré sur le service (graine 0, 30 ticks, Zab choisi, un tick) : les plans de 1175 et de 10103 sont vides (0 rue, 0 parcelle, 0 bâtiment). À la place d'ouverture, la photo ne différerait du plan fixe que par quelques chiffres du panneau : bien moins des 2 % de pixels que la chaîne exige, et la photo serait refusée. La vue d'ensemble garde la caméra du joueur, son point visé et son cap. Ce n'est pas le plan à 50° de #584.
