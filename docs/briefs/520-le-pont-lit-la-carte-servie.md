# Lot #520 — Le pont lit la carte servie
Jalon : J3 · Machine : pc · Taille prévue : 290 lignes

## But
Unity lit la carte que sert le service local (`GET /carte`). Il en tire, pour chaque cellule, son contour en mètres avec ses trous, sa puissance, sa maison et ses villes, ainsi que le nombre de cellules. Il attend au moins 10 s, et un service absent, lent ou fautif se déclare au lieu de rendre une carte inventée.

## Le joueur
Lot de fond. Il prépare l'écran du jalon 3, « la carte du joueur, dans Unity », et le premier geste qui s'y fait : ouvrir sa carte (#403), puis y choisir sa terre (#404) et y régler sa part (#405). Après ce lot, Unity connaît la carte de 1400 telle que le monde la tient : les frontières de chaque cellule, à qui elle est, et ses villes. Il ne la recopie pas. Le joueur ne voit encore rien de neuf. C'est le sous-lot 1 de #403 ; le maillage (sous-lot 3) puis la scène de la carte (sous-lot 4) la lui montreront.

## Règle du monde
Sans objet : c'est un lot d'outil, un lecteur. Aucun nombre du monde n'est décidé ici, et `jeu/` n'est pas touché. Niveau de fidélité : sans objet. Ce que le client lit est décrit dans `jeu/sim/MODELE.md`, « La carte et les terres servies, vue dérivée ». C'est une carte figée de 1400, la même pendant toute la partie.

### Ce que sert `/carte`, mesuré le 07/10/2026 sur master 1868805 (seed 0)
- Le service répond avec `_serialiser` : clés triées, UTF-8, sans espaces. Racine : `cell_count`, `cells`, `crs` (`"EPSG:3035"`), `tolerance_m`, `version`, `villes_hors_carte`.
- 596 cellules, triées par `cell_id` (1175 à 10466). Le corps fait environ 500 ko. La **première** requête prend 1,8 à 2 s, car la carte se calcule alors une fois pour toute la partie.
- Chaque cellule porte exactement `cell_id`, `contour`, `maison`, `puissance`, `relief`, `villes`.
  - `contour` vaut toujours `{"coordinates": …, "type": "MultiPolygon"}` (format GeoJSON). On y trouve des polygones, chacun fait d'anneaux : l'anneau 0 est l'extérieur, les suivants sont des trous. Un anneau est une suite de points `[x, y]`. Ces points sont des **entiers en mètres EPSG:3035** : x de 2,4 à 6,7 millions, y de 1,0 à 4,5 millions. Tout anneau est fermé (le dernier point égale le premier) et en a au moins 4. Au total : 675 polygones, dont **45 avec trous**, et 746 anneaux.
  - `puissance` et `maison` valent `{"id", "nom"}` ou `null`. 31 cellules n'ont pas de puissance et 120 n'ont pas de maison. Un `null` est une mesure : la cellule n'en a pas.
  - `villes` est une liste, souvent vide (550 cellules), de `{"nom", "population", "x_m", "y_m"}`. `x_m` et `y_m` sont des décimaux en mètres EPSG:3035. Il y a 57 villes en tout ; Venise est déclarée dans `villes_hors_carte`.
- `3d/unity/Assets/ForgeLocal3D/Pont/` a déjà `ClientLieu.cs` et `ClientPlan.cs`, deux clients sur le même modèle : `HttpClient` sans redirection, une minuterie qui tient le délai, une absence qui nomme sa cause, et des aides privées `Valeur`, `Tableau`, `Nombre`, `Entier`, `Decrire`, `CleRefusee`. Il a aussi `LecteurJson.cs`, qui rend les nombres en `double`. Un entier en mètres (moins de 10⁷) y reste exact.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientCarte.cs
3d/unity/Assets/ForgeLocal3D/Pont/ClientCarte.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientCarteTests.cs.meta

Précisions :

- **`ClientCarte.cs`**, dans l'espace de noms `Forge.Pont`, suit `ClientPlan.cs` pour la forme et les messages. Les aides privées y sont recopiées ; on ne crée aucune aide partagée et on ne touche à aucun autre fichier.
  - Types immuables. Leurs listes sont copiées en `ReadOnlyCollection`, et une liste ou un texte nul lève `ArgumentNullException` :
    - `PointCarte` (struct) : `double X`, `double Y`, en mètres EPSG:3035, relus tels quels, sans origine ni conversion ;
    - `PolygoneDeCarte` : `IReadOnlyList<PointCarte> Exterieur`, `IReadOnlyList<IReadOnlyList<PointCarte>> Trous` (vide s'il n'y a pas de trou). Les anneaux sont gardés **fermés**, comme servis ;
    - `IdentiteDeCarte` : `long Id`, `string Nom`. Il sert pour la puissance comme pour la maison ;
    - `VilleDeCarte` : `string Nom`, `long Population`, `PointCarte Position` ;
    - `CelluleDeCarte` : `long CellId`, `IReadOnlyList<PolygoneDeCarte> Contour`, `IdentiteDeCarte Puissance` et `IdentiteDeCarte Maison` (`null` quand le service sert `null`), `IReadOnlyList<VilleDeCarte> Villes` ;
    - `CarteLue` : `long CellCount`, `IReadOnlyList<CelluleDeCarte> Cellules`, dans l'ordre de la réponse ;
    - `LectureCarte` : `CarteLue Carte`, `string Absence`, `bool Presente`. On a soit une carte, soit une absence qui nomme sa cause, jamais les deux et jamais aucune, comme `LecturePlan`.
  - `ClientCarte : IDisposable` :
    - `public static readonly TimeSpan DelaiMinimal = TimeSpan.FromSeconds(10)`. Son commentaire dit pourquoi : la première requête prend 1,8 s, et le délai de 2 s des autres lectures n'y suffit pas ;
    - le constructeur `ClientCarte(int port, TimeSpan delai)` refuse un port hors de 1..65535, ainsi que tout délai inférieur à `DelaiMinimal`, `Timeout.InfiniteTimeSpan` compris, par `ArgumentOutOfRangeException` ;
    - `LectureCarte Lire()` demande `GET /carte` sur `127.0.0.1:<port>`. Le préfixe de toute absence est `carte : `. On garde les mêmes causes que `ClientPlan` : délai dépassé (avec sa durée en ms), service absent, statut autre que 200 (avec le corps reçu), JSON invalide. Pour une cause du service, la méthode ne lève jamais d'exception.
  - Ce que la lecture exige. Une seule faute refuse **toute** la carte, et le refus nomme le chemin pointé de la clé fautive (`cells[1].contour.coordinates[1][1][0]`) :
    - `crs` : exactement le texte `"EPSG:3035"`, puisque les mètres en dépendent ;
    - `cells` : un tableau **non vide**, car une carte sans cellule n'est pas une mesure. `cell_count` : un entier égal au nombre de cellules lues ;
    - `cells[i]` : un objet. `cell_id` : un entier ≥ 0, jamais deux fois le même dans la carte ;
    - `contour` : un objet dont `type` vaut `"MultiPolygon"`. `coordinates` est un tableau d'au moins un polygone ; chaque polygone a au moins un anneau ; chaque anneau a au moins 4 points et est fermé (premier point == dernier point, sinon le refus dit « fermé ») ; chaque point est un tableau d'exactement 2 nombres ;
    - `puissance` et `maison` : la clé est toujours présente. Sa valeur est `null`, ou un objet avec un `id` entier ≥ 0 et un `nom` en texte non vide hors espaces ;
    - `villes` : la clé est présente et vaut un tableau, éventuellement vide. Chaque ville a un `nom` en texte non vide, une `population` entière ≥ 0, et `x_m` et `y_m` en nombres ;
    - `relief`, `tolerance_m`, `version` et `villes_hors_carte` ne sont ni lus ni exigés. Une clé en plus est ignorée.
- **`ClientCarteTests.cs`**, dans l'espace de noms `Forge.Pont.Tests`. Le faux service est un `HttpListener` sur un port libre, comme dans `ClientPlanTests`. Il rend un statut et un corps, peut attendre une durée donnée avant de répondre, ou se taire (`muet`). Il retient le chemin et la requête reçus.
  - La constante `CARTE_TROIS` est écrite en littéral. Ce sont **trois vraies cellules** de `/carte` (seed 0), avec les clés dans l'ordre du service, et `cell_count` ramené à 3. Le chef l'a vérifié : c'est du JSON valide.
    `{"cell_count":3,"cells":[{"cell_id":10134,"contour":{"coordinates":[[[[4276473,1135517],[4314106,1026553],[4157452,1024145],[4166760,1118721],[4276473,1135517]]]],"type":"MultiPolygon"},"maison":null,"puissance":null,"relief":"plaine","villes":[]},{"cell_id":10196,"contour":{"coordinates":[[[[3255813,2017207],[3258432,2014942],[3252950,2017349],[3255813,2017207]]],[[[3260904,2014373],[3258233,2018288],[3248052,2019499],[3178677,2049953],[3214016,2181858],[3242818,2196329],[3344599,2164419],[3381106,2073504],[3289024,2001514],[3260904,2014373]],[[3256797,2044933],[3258232,2047203],[3254327,2044953],[3245580,2036516],[3242003,2025951],[3242985,2024693],[3248295,2030701],[3247211,2035050],[3251211,2041050],[3256797,2044933]]]],"type":"MultiPolygon"},"maison":{"id":6,"nom":"Barcelone"},"puissance":{"id":6,"nom":"Aragon"},"relief":"montagne","villes":[]},{"cell_id":10417,"contour":{"coordinates":[[[[3921201,3092821],[3947718,3062031],[3938366,3011532],[3893790,2985836],[3858975,3008678],[3849915,3077567],[3921201,3092821]]]],"type":"MultiPolygon"},"maison":{"id":27,"nom":"Valois-Bourgogne"},"puissance":{"id":3,"nom":"France"},"relief":"plaine","villes":[{"nom":"Tournai","population":40000,"x_m":3853625.55,"y_m":3075988.58},{"nom":"Valenciennes","population":23000,"x_m":3860893.43,"y_m":3047780.78}]}],"crs":"EPSG:3035","tolerance_m":1000,"version":"world-1400-v1","villes_hors_carte":["Venise"]}`

    Voici ce qu'elle couvre :
    - 10134 n'a ni puissance ni maison, et aucune ville ;
    - 10196 a deux polygones : un îlot de 4 points, puis un polygone de 10 points percé d'un trou de 10 points ;
    - 10417 a deux villes. Sa maison (27) et sa puissance (3) diffèrent : un client qui les confondrait rougit.
  - Une aide `RemplacerUneFois(source, ancien, nouveau)` exige que `ancien` paraisse **exactement une fois** dans `source` avant de le remplacer, comme dans `ClientPlanTests`.
  - Tous les cas construisent le client avec `ClientCarte.DelaiMinimal`.

## Conditions de succès

**SC1 — Unity compile et joue les tests (PC).**
Le workflow `unity` (poussée sur la branche) est vert, sans aucune `error CS`. Ensuite, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
(sans `-quit`). On attend un code de sortie 0 et `failed="0"` dans le XML. Le XML compte **au moins 25 cas** de `ClientCarteTests`, et tous les cas des autres classes de `Forge.Pont.Tests`, en même nombre et sous les mêmes noms que sur master. Zéro cas `ClientCarteTests` est un échec.
Contre-épreuve, faite à la main et dite dans la PR : un client qui lit `Puissance` dans la clé `maison` fait rougir SC2. Retirer ce changement le rétablit.

**SC2 — la carte servie est relue exactement (PC, dans SC1).**
Le faux service rend `200` et `CARTE_TROIS`. Le cas vérifie que `Lire()` a demandé le chemin `/carte`, sans requête, et que la lecture est `Presente`. Les valeurs sont **égales** (`==`, sans tolérance) aux littéraux, dans l'ordre de la réponse :
- `CellCount == 3`, `Cellules.Count == 3`, et les `CellId` sont 10134, 10196, 10417 ;
- 10134 :
  - `Puissance` et `Maison` sont nulles, `Villes.Count == 0` ;
  - un polygone, de 5 points extérieurs, sans trou ;
  - l'extérieur va de (4276473, 1135517) à (4166760, 1118721), puis revient à (4276473, 1135517) ;
- 10196 :
  - `Puissance` = (6, « Aragon »), `Maison` = (6, « Barcelone ») ;
  - `Contour.Count == 2`. Le polygone 0 a 4 points, de (3255813, 2017207) à (3255813, 2017207), et aucun trou. Le polygone 1 a 10 points extérieurs, de (3260904, 2014373) à (3260904, 2014373), et **un trou** de 10 points, de (3256797, 2044933) à (3256797, 2044933) ;
- 10417 :
  - `Puissance` = (3, « France »), `Maison` = (27, « Valois-Bourgogne ») ;
  - 7 points extérieurs, le premier étant (3921201, 3092821) ;
  - `Villes` : Tournai, 40000, (3853625.55, 3075988.58) ; puis Valenciennes, 23000, (3860893.43, 3047780.78).

Un second cas retire `"relief":"montagne",`, `"tolerance_m":1000,` et `,"villes_hors_carte":["Venise"]` (trois `RemplacerUneFois`, en gardant le JSON valide). La carte reste lue présente, avec les mêmes valeurs pour 10196 : ces clés ne sont pas exigées.

**SC3 — le délai tient au moins 10 s, et rien n'est inventé (PC, dans SC1).**
- `DelaiMinimal == TimeSpan.FromSeconds(10)`. Le constructeur lève `ArgumentOutOfRangeException` pour 9,999 s, pour `Timeout.InfiniteTimeSpan`, pour le port 0 et pour le port 65536. Il accepte 10 s.
- **Service lent** : le faux service attend **2 500 ms** puis rend `CARTE_TROIS`. La lecture est présente, avec 3 cellules.
- **Service muet** : la lecture est absente, `Carte` est nulle, et l'absence contient `carte : ` et `délai dépassé`. Un `Stopwatch` mesure **au moins 9 900 ms** avant la réponse.
- **Service absent** (aucun écouteur sur le port) : la lecture est absente, `Carte` est nulle, et l'absence contient `service absent`.
- **Statut 500** avec le corps `{"erreur":"x"}` : la lecture est absente, et l'absence contient `500` et `x`. **JSON coupé** (`CARTE_TROIS` sans son dernier caractère) : la lecture est absente, et l'absence contient `JSON invalide`.

Contre-épreuve, faite à la main et dite dans la PR : un `DelaiMinimal` de 2 s fait rougir le cas « service lent » et le cas du constructeur. Le remettre à 10 s les rétablit.

**SC4 — toute faute refuse la carte en nommant son chemin (PC, dans SC1).**
Chaque cas part de `CARTE_TROIS` et fait **un seul** `RemplacerUneFois`. Le texte avant `→` est remplacé par celui d'après la flèche. Chaque fragment de départ paraît exactement une fois dans `CARTE_TROIS`, ce que le chef a vérifié. Le cas appelle ensuite `Lire()` et exige : `Presente` faux, `Carte` nulle, une absence qui commence par `carte : ` et contient le chemin indiqué. Ces cas peuvent former un seul test paramétré.

| cas | remplacement | chemin exigé |
|---|---|---|
| autre projection | `"crs":"EPSG:3035"` → `"crs":"EPSG:4326"` | `crs` |
| compte faux | `"cell_count":3` → `"cell_count":4` | `cell_count` |
| cellule en double | `{"cell_id":10196,` → `{"cell_id":10134,` | `cells[1].cell_id` |
| cell_id négatif | `{"cell_id":10417,` → `{"cell_id":-1,` | `cells[2].cell_id` |
| pas un MultiPolygon | `"type":"MultiPolygon"},"maison":{"id":6` → `"type":"Polygon"},"maison":{"id":6` | `cells[1].contour.type` |
| polygone sans anneau | `]]],[[[3260904` → `]]],[],[[[3260904` | `cells[1].contour.coordinates[1]` |
| anneau à 3 points | `[4157452,1024145],[4166760,1118721],` → (rien) | `cells[0].contour.coordinates[0][0]` |
| anneau ouvert | `[4166760,1118721],[4276473,1135517]]` → `[4166760,1118721],[4276473,1135518]]` | `cells[0].contour.coordinates[0][0]` et `fermé` |
| coordonnée texte dans le trou | `[[3256797,2044933],` → `[["3256797",2044933],` | `cells[1].contour.coordinates[1][1][0]` et `un nombre attendu` |
| point à 3 nombres | `[3921201,3092821],[3947718` → `[3921201,3092821,0],[3947718` | `cells[2].contour.coordinates[0][0][0]` |
| puissance absente | `"puissance":{"id":3,"nom":"France"},` → (rien) | `clé absente : cells[2].puissance` |
| id de maison en texte | `"maison":{"id":27,` → `"maison":{"id":"27",` | `cells[2].maison.id` |
| nom blanc | `"nom":"Aragon"` → `"nom":" "` | `cells[1].puissance.nom` |
| maison qui n'est pas un objet | `"maison":null,` → `"maison":7,` | `cells[0].maison` |
| villes absentes | `,"villes":[]},{"cell_id":10196` → `},{"cell_id":10196` | `clé absente : cells[0].villes` |
| villes nulles | `"villes":[]},{"cell_id":10417` → `"villes":null},{"cell_id":10417` | `cells[1].villes` |
| population décimale | `"population":23000,` → `"population":23000.5,` | `cells[2].villes[1].population` |
| x_m absent | `"x_m":3860893.43,` → (rien) | `cells[2].villes[1].x_m` |

Il y a un cas de plus, coupé par `IndexOf` (le test vérifie que le texte a changé) : la liste `cells` entière remplacée par `[]`, et `"cell_count":3` par `"cell_count":0`. Il doit donner une absence qui contient `cells`, car une carte vide est refusée.

Contre-épreuve : un client qui rendrait `Maison = null` pour une clé `maison` absente, ou qui accepterait un anneau ouvert, fait rougir la ligne correspondante.

**SC5 — rien d'autre ne bouge.**
```
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC (pc\Tests.cmd)
git diff --name-only origin/master...HEAD
```
La suite du jeu reste verte. Le diff ne nomme que les quatre fichiers du Périmètre et ce brief. Les `.meta` sont ceux qu'Unity génère. `git diff --stat` reste sous 300 lignes ajoutées.

## Hors périmètre
- Ramener les contours en kilomètres autour d'une origine, les trianguler (avec trous), dessiner la carte, la caméra, le lanceur `Jouer --carte` : sous-lots 3 à 5 de #403.
- `/monde`, `/horloge`, la date, le survol, le panneau d'une cellule, la capture de la Lorraine, l'épreuve : sous-lots 2, 6, 7 et 8 de #403.
- Lire `relief`, `tolerance_m`, `version` ou `villes_hors_carte`. Vérifier qu'une ville tombe dans sa cellule, ou qu'un trou est dans son extérieur.
- `/departs` et la fiche d'une terre : #404.
- Une lecture asynchrone ou en cache. Toucher `ClientLieu.cs`, `ClientPlan.cs`, `LecteurJson.cs`, les asmdef, les autres tests, `jeu/` (service, carte servie, `MODELE.md`).
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.

## Photo
Sans objet : le lot ne change rien de ce qu'on voit à l'écran. `ClientCarte` lit une carte que rien n'affiche encore. Aucune scène, aucun outil d'éditeur et aucun panneau ne l'appelle avant le sous-lot 4 de #403 (la scène de la carte), qui portera son scénario de capture.
