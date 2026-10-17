# Lot #686 — Le panneau du lieu suit une autre cellule
Jalon : J4 · Machine : pc · Taille prévue : 260 lignes

## But
Le panneau du lieu sait montrer une autre cellule que 1175 : `PanneauLieu.Ouvrir(long cellule)` fixe la cellule avant son démarrage, ou en change en cours de jeu, sans jamais afficher un chiffre de l'ancienne.

## Le joueur
Lot de fond, premier sous-lot de #680 « La ville s'ouvre sur le siège du joueur » (lui-même sous-lot de #409 « Le jeu ouvre la capitale du joueur »). Il prépare le geste du J4 de `CAP.md` : le joueur **entre dans sa capitale en 3D** et passe de la carte à sa ville d'un geste. Aujourd'hui, le panneau lit toujours la cellule 1175, ou celle de `-forgeCell` : à Biskra (cellule 10103), il montrerait les habitants d'une autre terre. Après ce lot, le panneau peut suivre la cellule où la ville s'ouvre. Rien ne change encore à l'écran : aucune vue n'appelle `Ouvrir`. Le troisième sous-lot de #680 le rendra visible : l'outil des routes ouvre la ville au siège et le panneau dit les chiffres de Biskra, avec la photo.

## Règle du monde
Sans objet : c'est un lecteur de vue. Le monde ne change pas. Le panneau lit `GET /lieu?cell=X` tel que le décrit `jeu/sim/MODELE.md` (« Les lieux d'une cellule, vue dérivée ») ; `cell_id` reste la seule clé spatiale, et `ClientLieu` refuse déjà une réponse dont le `cell_id` n'est pas celui demandé.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/PanneauLieu.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PanneauLieuTests.cs

Tout autre chemin est interdit. Ni `ClientLieu.cs`, ni `DesertRoadTool.cs`, ni aucune scène, aucune capture.

Budget : environ 45 lignes dans `PanneauLieu.cs`, 130 lignes de tests, le reste pour ce brief.

### Ce que fait `Ouvrir(long cellule)`
- **Avant le démarrage** (avant `Demarrer`, ou si `Demarrer` s'est arrêté faute de caméra) : il retient seulement la cellule. `Demarrer` lit alors cette cellule, à la place du défaut 1175 **et** de `-forgeCell` : l'appelant a déjà décidé (l'outil des routes lit `-forgeCell` lui-même). Sans appel à `Ouvrir`, `Demarrer` fait exactement ce qu'il fait aujourd'hui.
- **Après le démarrage**, pour une cellule valable :
  - la cellule lue devient la nouvelle ;
  - l'ancien affichage s'efface : le texte reprend **exactement** le texte d'attente de `Demarrer` (`service absent : en attente de 127.0.0.1:<port>`) ; le texte des foyers devient vide et son objet est désactivé ;
  - une lecture en vol pour l'ancienne cellule est abandonnée : son résultat n'est jamais appliqué ;
  - l'état du dernier affichage est remis à zéro. **Piège** : `Appliquer` saute la reconstruction quand le tick et l'absence n'ont pas changé ; deux cellules au même tick laisseraient le texte d'attente ;
  - `Ouvrir` lance lui-même la lecture de la nouvelle cellule, sans attendre le prochain `Pas` ni la période ;
  - si le client n'existe pas (un `-forgeCell` refusé au démarrage), `Ouvrir` le crée sur le même port.
- **Une cellule négative** est refusée, avant comme après le démarrage. Le texte devient `Cellule <c> invalide : un cell_id entier positif ou nul attendu.` (la phrase de `DesertRoadTool.Ouvrir(long)`). Les foyers sont vidés et cachés, une lecture en vol est abandonnée, et aucune requête ne part plus jusqu'au prochain `Ouvrir` valable. Avant le démarrage, c'est `Demarrer` qui affiche ce refus, sans créer de client.

`HttpClient` accepte deux requêtes à la fois : abandonner une tâche en vol ne demande aucun verrou. Le commentaire d'en-tête de la classe gagne une ligne « Lot 686 ».

## Conditions de succès
Commande PC (Unity 6000.0.43f1), commune à toutes les SC : `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults <temp>/pont.xml -logFile <temp>/pont.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec, et les nouveaux cas `PanneauLieuTests` réellement exécutés : zéro cas nouveau est un échec.

Les nouveaux cas utilisent le faux service `Servir` du fichier, tel quel. Pour la cellule 42, un document se tire de `Document(e)` en remplaçant `"cell_id":1175,` par `"cell_id":42,` (le test vérifie que le remplacement a eu lieu). Pour l'appel avant le démarrage, une petite aide pose le panneau comme `Poser`, mais appelle `Ouvrir` avant `Demarrer`. Une ligne « Cellule 42 · tick N » se relit avec `Relire(l[0], "Cellule ", " · tick ", "")`. Écrire ces cas, les voir rouges sur le code d'avant, puis obtenir le vert.

**SC1 — avant le démarrage, `Ouvrir` choisit la cellule lue.**
- `Ouvrir(42)`, puis `Demarrer` sans argument : après `Lire()`, `derniereRequete` vaut `/lieu?cell=42`, et la première ligne relue vaut {42, 12}.
- `Ouvrir(42)`, puis `Demarrer` avec `-forgeCell 7` : même attendu.

Contre-épreuve : un `Demarrer` qui ignore `Ouvrir` demande `/lieu?cell=1175` (ou 7) ; le faux service rend `cell_id` 42, le panneau dit « lieu illisible » et les deux cas rougissent.

**SC2 — après le démarrage, l'ancien affichage s'efface et la lecture part tout de suite.**
Le faux service rend 1175 au tick 12 avec foyers (`AvecFoyers`), puis 42 au tick 12, le même tick. Le test retient le texte d'attente juste après `Demarrer`, puis fait `Lire()` (1175 affiché, foyers visibles). Ensuite `Ouvrir(42)`. Sans aucun `Pas` :
- le texte égale le texte d'attente retenu ;
- `TexteFoyers` est vide et `ObjetFoyers` inactif ;
- dans les 10 s, le faux service reçoit une requête de plus, et `derniereRequete` vaut `/lieu?cell=42`.

Puis `Lire()` : la première ligne relue vaut {42, 12}, et `Reconstructions` a augmenté de un.

Contre-épreuves :
- un `Ouvrir` qui garde l'ancien texte fait rougir le premier point ;
- un `Ouvrir` qui attend le prochain `Pas` fait rougir le troisième ;
- un `Ouvrir` qui ne remet pas à zéro l'état du dernier affichage laisse le texte d'attente (même tick 12) et fait rougir la relecture.

**SC3 — une lecture partie pour l'ancienne cellule ne s'affiche jamais.**
`Servir(500, Ok(Document(Tick12)), Ok(<document de 42 au tick 13>))`, une nouvelle constante de 500 ms. Avec les deux réponses servies l'une après l'autre, la seconde arrive vers 1 s, sous le délai de 2 s du client. `Poser()`, `Pas(1)` (la lecture de 1175 part), puis `Ouvrir(42)` aussitôt. Ensuite, un `Pas` toutes les 10 ms, avec une horloge qui avance, jusqu'à lire « Cellule 42 » (10 s au plus). À chaque `Pas`, le texte ne contient jamais `Cellule 1175`. À la fin, la première ligne relue vaut {42, 13}.

Contre-épreuve : un `Ouvrir` qui change la cellule sans abandonner la lecture en vol laisse `Pas` appliquer la réponse de 1175 (valide pour 1175) ; « Cellule 1175 · tick 12 » s'affiche et le cas rougit.

**SC4 — une cellule négative est refusée, et le refus s'affiche.**
- **Avant** : `Ouvrir(-3)`, puis `Demarrer`, puis `Lire()`. Le texte commence par `Cellule -3 invalide`, `SansNombre` tient, et le faux service n'a reçu aucune requête.
- **Après** : 1175 lu avec foyers, puis `Ouvrir(-3)`. Le texte commence aussitôt par `Cellule -3 invalide`, les foyers sont vides et cachés. Vingt `Pas` sur plus de 5 s d'horloge : le nombre de requêtes ne bouge plus et le refus reste affiché. Puis `Ouvrir(42)` et `Lire()` : la première ligne relue vaut 42.

Contre-épreuves :
- un `Ouvrir` qui accepte −3 interroge `/lieu?cell=-3` : le compte de requêtes bouge et le cas rougit ;
- un refus qui laisse lire l'ancienne cellule voit « Cellule 1175 » revenir au tick suivant : le cas rougit.

**SC5 — un `-forgeCell` refusé se rattrape par `Ouvrir`.**
`Poser("-forgeCell", "abc")` affiche l'erreur actuelle. Puis `Ouvrir(42)` et `Lire()` : une seule requête, `/lieu?cell=42`, et la première ligne relue vaut 42.

Contre-épreuve : un `Ouvrir` qui ne crée pas le client ne lit rien, et le cas rougit.

**SC6 — rien d'existant ne bouge.**
- Les 25 cas existants de `PanneauLieuTests` passent, et toute l'assemblée `Forge.Pont.Tests` aussi. Le relevé des cas se compare à celui d'avant le lot.
- `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/PanneauLieuTests.cs | grep '^-[^-]'` ne sort rien : le fichier de tests ne fait que s'ajouter, aucune aide existante n'est modifiée.
- `git diff --name-only origin/master` ne liste que le périmètre et ce brief.

Contre-épreuve : modifier `Document`, `Servir`, `Poser` ou un cas existant fait sortir une ligne à la commande `grep`.

## Hors périmètre
- Appeler `Ouvrir` depuis une vue : ni `DesertRoadTool`, ni `OuvertureDeLaCarte`, ni une scène. C'est le troisième sous-lot de #680.
- La décision de la cellule à ouvrir (`-forgeCell`, éditeur, aiguillage de #679) : deuxième sous-lot de #680.
- Changer `LireCellule`, le texte d'attente, le port, la période, `ClientLieu`, les captures existantes (`Lot263`, `Lot388`, `Lot584`).
- Le lanceur `pc/jouer.py`, le relief de Biskra, toute clé servie, tout changement du monde ou de `MODELE.md`.

## Photo
Sans objet : ce lot ne change rien de ce qu'on voit à l'écran. Sans appel à `Ouvrir`, le panneau se comporte comme avant, et aucune vue ne l'appelle encore. Aucun `Lot686.cs` n'est ajouté. Le troisième sous-lot de #680 portera la photo de Biskra et de son panneau.
