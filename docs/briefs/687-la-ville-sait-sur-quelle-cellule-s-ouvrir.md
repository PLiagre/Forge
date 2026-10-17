# Lot #687 — La ville sait sur quelle cellule s'ouvrir
Jalon : J4 · Machine : pc · Taille prévue : 230 lignes

## But
Le pont Unity sait décider, au lancement, sur quelle cellule la ville doit s'ouvrir, ou s'il faut passer à la carte. Il le décide d'après la ligne de commande, l'éditeur et l'aiguillage de #679, sans jamais inventer une cellule quand le service manque.

## Le joueur
Lot de fond, deuxième sous-lot de #680 « La ville s'ouvre sur le siège du joueur » (lui-même sous-lot de #409 « Le jeu ouvre la capitale du joueur »). Il prépare le geste du J4 de `CAP.md` : le joueur **entre dans sa capitale en 3D**. Au Zab, c'est Biskra, à la cellule de son siège (10103), et non plus le ksar de la cellule 1175 ; une terre sans kit, ou une partie sans terre choisie, l'envoie vers la carte. Ce lot prend seulement la décision et ne change rien à l'écran. Le troisième sous-lot de #680 la rend visible : `DesertRoadTool` et le panneau du lieu l'appliquent dans le jeu bâti, avec la photo de Biskra.

## Règle du monde
Sans objet : c'est une décision de vue. Le monde ne change pas, ni son niveau de fidélité, ni `jeu/sim/MODELE.md`. La cellule vient de `-forgeCell` quand l'appelant la donne. Sinon, elle vient du siège servi, lu par `AiguillageDeCapitale` (#679) dans `/monde` puis `/maison?id=` (`MODELE.md`, « Les maisons servies, vue dérivée »). `cell_id` reste la seule clé spatiale. La cellule 1175 n'est qu'un défaut de l'éditeur, jamais un remplaçant d'une absence.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/OuvertureDeLaCapitale.cs
3d/unity/Assets/ForgeLocal3D/Pont/OuvertureDeLaCapitale.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/CapitaleDuJoueurTests.cs

Tout autre chemin est interdit. Dans `CapitaleDuJoueurTests.cs`, le lot **ajoute** des cas à la classe existante. Il réutilise `Servir`, `Recues`, `Monde`, `Fige` et `Id` sans changer aucune ligne existante. Le `.meta` est généré par Unity, avec un GUID unique.

Budget : environ 50 lignes de code, 80 de tests, 11 de `.meta`, 90 de brief.

## Conditions de succès
Commande de toutes les SC (PC, Unity 6000.0.43f1) : `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults <temp>/pont.xml -logFile <temp>/pont.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec, et les nouveaux cas réellement exécutés et listés dans le XML. Zéro cas nouveau compte comme un échec.

**SC1 — la forme de la décision.**

Dans `Forge.Pont` (fichier `OuvertureDeLaCapitale.cs`), créer :
- `public static class OuvertureDeLaCapitale`, avec `public static Lecture<OuvertureDecidee> Decider(string[] arguments, bool editeur, Func<Lecture<CapitaleAOuvrir>> aiguillage)` ;
- `public enum ModeDOuverture { Ville, Carte, LaisseeALaCarte }` ;
- `public sealed class OuvertureDecidee`, immuable, qui expose `Mode`, `Cellule` (`long?`, renseignée seulement pour `Ville`) et `Scene` (`string`, égale à `OuvertureDeLaCarte.SCENE` seulement pour `Carte`, nulle sinon).

`Decider` est pure. Elle ne lit ni `Environment.GetCommandLineArgs()`, ni `Application.isEditor`, ni aucun port : tout vient de ses trois paramètres. Elle appelle `aiguillage` au plus une fois, et seulement dans le cas 4 ci-dessous. `arguments` ou `aiguillage` nul lève `ArgumentNullException` avant tout appel. Un `aiguillage` qui rend une `Lecture` nulle lève `InvalidOperationException`.

Les cas s'examinent dans cet ordre :
1. `OuvertureDeLaCarte.Demandee(arguments)` → `LaisseeALaCarte`, même si `-forgeCell` est là, valable ou non. `pc/jouer.py --carte` passe les deux arguments (ligne 189), et le jeu va aujourd'hui à la carte (`VueDeCarteTests`, ligne 93).
2. `-forgeCell` présent → `PanneauLieu.LireCellule(arguments, PanneauLieu.CELLULE_PAR_DEFAUT, out erreur)`. Avec une erreur, le résultat est `Lecture.Absent(erreur)`, avec ce texte-là, mot pour mot. Sinon, le résultat est `Ville` à cette cellule. Que l'on soit dans l'éditeur ou non ne change rien.
3. `editeur` vrai, sans `-forgeCell` → `Ville` à `PanneauLieu.CELLULE_PAR_DEFAUT` (1175). La capture de la chaîne (`atelier/pc.py`) et les contrôles de l'éditeur tournent sans `-forgeCell` ; ils doivent garder le ksar de 1175.
4. Sinon (jeu bâti, sans argument) → appel de `aiguillage()`. `Ville` donne `Ville` à `capitale.Cellule`. `Depart` et `PasDeKit` donnent `Carte`. Une absence donne `Lecture.Absent` avec la même cause, mot pour mot, jamais une `Ville` à 1175 ni une `Carte`.

Contre-épreuve : une `Decider` qui lit `Application.isEditor` au lieu de son paramètre rend 1175 dans les cas du jeu bâti joués en EditMode. Les cas de SC3 rougissent alors.

**SC2 — les arguments et l'éditeur ne font aucune requête.**

Le faux service sert `/monde` avec `maison_du_joueur` = l'`id` de la fixture du Zab, et `/maison?id=` sert la fixture du Zab. L'aiguillage passé est `() => { appels++; return AiguillageDeCapitale.Lire(port, TimeSpan.FromSeconds(5)); }`. Chaque cas exige `appels == 0` et `Recues()` vide.

| arguments | editeur | attendu |
|---|---|---|
| `Forge.exe -forgeCell 42` | faux | `Ville`, cellule 42, `Scene` nulle |
| `Forge.exe -forgeCell 42` | vrai | `Ville`, cellule 42 |
| `Forge.exe -forgeCell` | faux | absence égale à l'erreur que `PanneauLieu.LireCellule` rend pour ces arguments |
| `Forge.exe -forgeCell abc` et `Forge.exe -forgeCell -3` | faux | absence égale à l'erreur de `LireCellule`, qui nomme la valeur reçue |
| `Forge.exe` | vrai | `Ville`, cellule 1175 |
| `Forge.exe -forgeCell 1175 -forgeCarte` | faux | `LaisseeALaCarte`, cellule et scène nulles |
| `Forge.exe -forgeCarte -forgeCell abc` | vrai | `LaisseeALaCarte` |

Le test calcule l'erreur attendue en appelant `PanneauLieu.LireCellule` ; il ne recopie pas la phrase. Il vérifie aussi que `Decider(null, …)` et `Decider(…, null)` lèvent `ArgumentNullException`, sans requête.

Contre-épreuves :
- une `Decider` qui consulte l'aiguillage avant les arguments rougit sur `appels` ;
- une cellule fautive remplacée par 1175 rougit sur le cas `abc` ;
- une `-forgeCell` qui passe avant `-forgeCarte` rougit sur le cas de `jouer.py --carte`.

**SC3 — le jeu bâti suit l'aiguillage, et une absence reste une absence.**

`editeur` vaut faux, et les arguments sont `Forge.exe` seul. L'aiguillage est le même compteur qu'en SC2, branché sur le faux service et les fixtures figées de #679.

| service | attendu |
|---|---|
| `maison_du_joueur` = Zab, `/maison` sert la fixture du Zab | `Ville`, cellule 10103 ; `appels == 1` ; requêtes `GET /monde` puis `GET /maison?id=<id du Zab>` |
| Zab, avec `siege.cell_id` changé en 10104 (par `Remplacer`, comme dans `LaCelluleVientDuSiegeServi`) | `Ville`, cellule 10104 |
| `maison_du_joueur` = Bar, `/maison` sert la fixture de Bar | `Carte`, `Scene` = `OuvertureDeLaCarte.SCENE`, cellule nulle ; requêtes exactement `["GET /monde"]` |
| `/monde` sans `maison_du_joueur` | `Carte` ; requêtes exactement `["GET /monde"]` |
| aucun service sur le port | absence qui commence par `monde : ` et contient `monde : service absent` ; `appels == 1` |
| Zab, `/maison` statut 500 | absence qui contient `maison : statut 500` |

Un dernier cas passe l'aiguillage `() => Lecture<CapitaleAOuvrir>.Absent("cause témoin 687")`. Il exige une absence égale à `"cause témoin 687"`, et un aiguillage qui rend `null` lève `InvalidOperationException`.

Contre-épreuves :
- une absence remplacée par `Ville` à 1175, ou par `Carte`, rougit le cas « aucun service » ;
- une cellule écrite en dur à 10103 rougit le cas 10104 ;
- une `Decider` qui confond `PasDeKit` et `Ville` rougit le cas de Bar.

Écrire et constater ces tests rouges (avec une `Decider` qui lève `NotImplementedException`) avant d'implémenter, puis obtenir le vert.

**SC4 — les invariants existants restent verts.**

Commande : celle du haut, pour toute l'assemblée `Forge.Pont.Tests`. Aucun cas existant n'est retiré, renommé ou assoupli. Le relevé des cas se compare à celui d'avant le lot : mêmes cas, plus les nouveaux.

Contre-épreuve : `git diff --name-only origin/master` ne liste que le périmètre et ce brief. `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/CapitaleDuJoueurTests.cs` ne montre que des lignes ajoutées.

## Hors périmètre
- Appliquer la décision : `DesertRoadTool` (`Awake`, `Start`, `Ouvrir(cellule)`), `PanneauLieu.Ouvrir`, le passage à `Forge_Carte` dans le jeu bâti, le texte d'absence à l'écran, la photo de Biskra. C'est le troisième sous-lot de #680.
- Changer `OuvertureDeLaCarte`, `AiguillageDeCapitale`, `TerresAvecKit`, `PanneauLieu.LireCellule` ou leurs tests existants.
- Le lanceur (`pc/jouer.py`, qui passe encore `-forgeCell` : sous-lot 4 de #409) ; la carte qui ouvre la capitale ou dit « pas encore de kit » (#681) ; le relief de Biskra ; l'épreuve Zab/Bar.
- Toute lecture asynchrone, tout cache, toute nouvelle clé servie, tout changement du monde ou de `MODELE.md`.

## Photo
Sans objet : ce lot ne change rien de ce qu'on voit à l'écran, et aucune scène n'appelle encore `Decider`. Aucun `Lot687.cs` n'est ajouté. Le troisième sous-lot de #680 portera la photo de Biskra ouverte à la cellule de son siège.
