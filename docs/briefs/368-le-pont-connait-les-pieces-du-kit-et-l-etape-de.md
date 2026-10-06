# Lot #368 — Le pont connaît les pièces du kit et l'étape de chaque bâtiment
Jalon : J4 · Machine : pc · Taille prévue : 275 lignes

## But
Pour chaque bâtiment du plan, le pont sait quelle pièce du kit du désert le montre (piquets, murs ou bâtiment fini) et comment la poser sur sa parcelle (au centre de l'emprise, façade tournée vers la rue). Il charge ces neuf pièces hors de l'éditeur, et dit « absente » pour une nature que le kit n'a pas. Le sous-lot suivant de #363 pourra ainsi dessiner les bâtiments de la capitale « d'après le plan que tient le monde » (CAP.md, jalon 4).

## Règle du monde
Sans objet : c'est un lot d'outil, côté vue. Aucun nombre du monde n'est décidé ici, et `jeu/` n'est pas touché. Niveau de fidélité : sans objet.

Ce que la vue lit de `jeu/sim/MODELE.md`, sans rien y changer :

- **« Le plan du bourg ».** Un bâtiment a une `nature` (texte libre non vide : le geste `poser_batiment` ne pose que `maison`, `scierie` ou `four`, mais un bâtiment ancien peut porter un autre texte), une `emprise` (au moins 3 points, en mètres locaux du bourg, x vers l'est, y vers le nord), `en_chantier`, `travail_requis` et `travail_fourni`. `en_chantier` vaut exactement `travail_fourni < travail_requis`. L'emprise est le contour de la parcelle, copié tel quel à la pose.
- **« Les intentions du joueur ».** Le contour d'une parcelle est ordonné : `c0`, `c1` bordent la chaussée, `c2 = c1 + n·profondeur`, `c3 = c0 + n·profondeur`. « La façade borde la chaussée ; le lot va vers l'extérieur. » Le côté `c0→c1` de l'emprise est donc la façade, et le bâtiment regarde vers la rue, à l'opposé de l'intérieur du lot. Les exemples du modèle, sur la rue `[[0, 0], [40, 0], [40, 25]]`, largeur 4 m :
  - segment 0, gauche : `[(5, 2), (15, 2), (15, 22), (5, 22)]` ;
  - segment 0, droite : `[(5, −2), (15, −2), (15, −22), (5, −22)]` ;
  - segment 1, gauche, début 0, façade 25, profondeur 10 : `[(38, 0), (38, 25), (28, 25), (28, 0)]`.
- **Niveau 3 au modèle** : l'orientation d'un bâtiment, l'étage et les matériaux. La pose et l'étape calculées ici sont une convention de la vue. Elles ne retournent rien au monde.
- **Le repère** est celui que #293 a fixé : un point `(x, y)` du plan devient `(-x, sol, -y)` dans Unity (`DesertParcelles.cs`, l. 42). Une direction `(dx, dy)` du plan devient donc `(-dx, 0, -dy)`. La façade d'un prefab du kit regarde `+Z` (`Editor/DesertKit.cs`, l. 28 : « La façade regarde +Z (le -Y de Blender) »). `Quaternion.Euler(0, θ, 0)` envoie `+Z` sur `(sin θ, 0, cos θ)`.

Ce qui existe sur master (8a5e82c), vérifié le 07/10/2026 :

- `Pont/ClientPlan.cs` (#360) : `BatimentDuPlan(long identifiant, long parcelle, string nature, IList<PointLocal> emprise, bool enChantier, long travailRequis, long travailFourni)`, et `PointLocal(double x, double y)`. Rien ne lit encore `Batiments` hors des tests.
- `Pont/Forge.Pont.asmdef` référence `UnityEngine` (`noEngineReferences: false`). `Forge.Pont.Tests` (Editor seulement) référence `Forge.Pont`.
- Aucun dossier `Resources/` dans `3d/unity/Assets/ForgeLocal3D`, et aucun type nommé `Etape…` ni `KitDes…` dans le projet.
- Les neuf prefabs sont dans `Desert/Prefabs/`. Le nom de leur `GameObject` racine (`m_Name`) est celui du fichier :

| nature | étape | prefab | guid | fileID racine |
|---|---|---|---|---|
| maison | piquets | `chantier_maison_pise_0_piquets` | `e985289e398c5a7498a040675f3de1dd` | `1440978593232044162` |
| maison | murs | `chantier_maison_pise_0_murs` | `c09686b1f12716546a083dedc306a8e3` | `5284588481682110971` |
| maison | fini | `maison_pise_0` | `450a5528a7bc7334a83dcc57c20c1d6e` | `6017052373620483911` |
| scierie | piquets | `chantier_scierie_piquets` | `40be798ae938c5f4ab7500bc66b9b661` | `3202877963815112739` |
| scierie | murs | `chantier_scierie_murs` | `a4c30be3b92ac924ab5e597d48c960ee` | `2542185315372848113` |
| scierie | fini | `scierie` | `954a0aead40c1414a9a51063c80c21c7` | `2316758156945518571` |
| four | piquets | `chantier_four_pain_pise_piquets` | `a9a830a624ed67c46b98d3629df51fca` | `2561686787781917062` |
| four | murs | `chantier_four_pain_pise_murs` | `fb7d386753565a04dadc08b0f65054ed` | `891289277825046446` |
| four | fini | `four_pain_pise` | `a4d96dbbf41d1e64ca4442f83ec9e7cb` | `1143097596662638885` |

Le lot ne s'appuie sur rien que J2 ou J3 doivent encore livrer : `/plan`, `poser_batiment`, l'étape Chantiers, #360 et les neuf prefabs sont sur master.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/EtapeDuBatiment.cs
3d/unity/Assets/ForgeLocal3D/Pont/EtapeDuBatiment.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/KitDesBatiments.cs
3d/unity/Assets/ForgeLocal3D/Pont/KitDesBatiments.cs.meta
3d/unity/Assets/ForgeLocal3D/Desert/Resources.meta
3d/unity/Assets/ForgeLocal3D/Desert/Resources/KitDesBatiments.asset
3d/unity/Assets/ForgeLocal3D/Desert/Resources/KitDesBatiments.asset.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/KitDesBatimentsTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/KitDesBatimentsTests.cs.meta

Précisions :

- **`EtapeDuBatiment.cs`** (neuf, namespace `Forge.Pont`). Il ne contient **ni `UnityEngine` ni `UnityEditor`** : seulement `System` et les types de `ClientPlan.cs`. Il déclare :
  - `public enum EtapeDuBatiment { Piquets, Murs, Fini }` ;
  - `public sealed class PoseDuBatiment`, immuable :
    - `bool Presente` et `string Absence` (vide si présente, jamais nulle) ;
    - `double CentreX`, `CentreY` : en mètres du plan ;
    - `double FacadeX`, `FacadeY` : un vecteur unitaire du plan, perpendiculaire à `c0→c1`, tourné vers l'extérieur du lot ;
    - `double LacetDegres` : l'angle θ, dans `[0 ; 360)`, tel que `Quaternion.Euler(0, θ, 0)` tourne la façade `+Z` du prefab vers `(-FacadeX, 0, -FacadeY)` dans Unity. Soit `θ = atan2(-FacadeX, -FacadeY)` en degrés, plus 360 s'il est négatif.

    Quand `Presente` est faux, les cinq nombres valent `double.NaN`.
  - `public static class LectureDuBatiment` :
    - **`EtapeDuBatiment Etape(BatimentDuPlan b)`** : `Fini` si `!b.EnChantier`. Sinon `Piquets` tant que `b.TravailFourni × 2 < b.TravailRequis`, écrit sans débordement (`b.TravailFourni < b.TravailRequis - b.TravailFourni`). Sinon `Murs`. La nature n'y joue aucun rôle. `b` nul lève `ArgumentNullException`.
    - **`PoseDuBatiment Poser(BatimentDuPlan b)`** :
      1. `b` nul lève `ArgumentNullException`.
      2. Moins de 3 points d'emprise : absence `bâtiment <id> : emprise de <n> point(s)`.
      3. Une coordonnée non finie : absence `bâtiment <id> : point non fini`.
      4. Le centre est la **moyenne arithmétique des sommets** de l'emprise. Pour un rectangle, c'est son centre.
      5. `e = c1 − c0`. Si `|e| == 0` : absence `bâtiment <id> : façade nulle`.
      6. `m = (e.y, −e.x) / |e|`. Soit `s = m · (centre − milieu(c0, c1))`. Si `s == 0`, le centre est sur la ligne de façade : absence `bâtiment <id> : emprise plate`. Si `s > 0`, `m` pointe vers l'intérieur du lot, et on prend `−m`. La façade vaut ce vecteur.
      7. Le lacet se calcule comme dit plus haut.

      La façade est **toujours** le côté `c0→c1`, jamais « le côté le plus proche d'une rue » : la fonction ne lit pas les rues.
- **`KitDesBatiments.cs`** (neuf, namespace `Forge.Pont`) : `public sealed class KitDesBatiments : ScriptableObject`. Il n'utilise **pas `UnityEditor`**.
  - `[Serializable] public sealed class PiecesDUneNature { public string nature = ""; public GameObject piquets, murs, fini; }` (classe imbriquée ou voisine), et le champ sérialisé `public PiecesDUneNature[] natures = new PiecesDUneNature[0];`.
  - `public const string Ressource = "KitDesBatiments";` et `public static KitDesBatiments Charger()`, qui rend `Resources.Load<KitDesBatiments>(Ressource)`, `null` si l'asset manque.
  - `public PieceDuKit Piece(string nature, EtapeDuBatiment etape)`. `PieceDuKit` est immuable : `bool Presente`, `GameObject Prefab` (nul si absente), `string Absence` (vide si présente). Règles :
    - la nature se compare **à l'exact** (`string.Equals(…, StringComparison.Ordinal)`), sans tolérer casse ni espace ;
    - une nature nulle, ou qu'aucune entrée ne porte, donne l'absence `nature sans pièce au kit : <nature>` ;
    - une nature présente dont la pièce de cette étape est nulle donne `pièce manquante au kit : <nature> <étape en minuscules>`.

    Le kit ne choisit **jamais** une autre pièce (pas de maison par défaut, pas de fini à la place des murs).
  - Un commentaire de classe dit que l'asset vit sous `Desert/Resources/` pour être chargé hors de l'éditeur.
- **`Desert/Resources/KitDesBatiments.asset`** : un `MonoBehaviour` sérialisé (`--- !u!114 &11400000`). Son `m_Script` porte le guid de `KitDesBatiments.cs.meta`, et son `m_Name` vaut `KitDesBatiments`. `natures` a trois entrées, dans l'ordre `maison`, `scierie`, `four`. Chaque pièce est `{fileID: <fileID racine>, guid: <guid>, type: 3}`, d'après la table plus haut. L'asset peut être écrit à la main ou créé dans l'éditeur. Le codeur vérifie qu'Unity l'ouvre sans erreur et que l'inspecteur montre les neuf prefabs.
- **Les `.meta`** (deux scripts, le test, le dossier `Resources`, l'asset) sont ceux qu'Unity génère. Les prefabs ne bougent pas de `Desert/Prefabs/` : ils ne sont que référencés.
- **`KitDesBatimentsTests.cs`** (neuf, namespace `Forge.Pont.Tests`, NUnit). C'est un fichier neuf, et aucun fichier de test existant ne change. Une aide `Batiment(bool enChantier, long requis, long fourni, params (double, double)[] emprise)` construit un `BatimentDuPlan` (identifiant 7, parcelle 0, nature `maison`). Ses cas :
  - **les neuf pièces** : un `[TestCase(nature, etape, nom)]` par ligne de la table. `KitDesBatiments.Charger()` n'est pas nul. `Piece(nature, etape)` est présente, `Prefab.name == nom`, et `AssetDatabase.GetAssetPath(Prefab) == "Assets/ForgeLocal3D/Desert/Prefabs/" + nom + ".prefab"` ;
  - **les trois pièces d'une nature sont distinctes** : pour chaque nature, piquets, murs et fini sont trois objets différents ;
  - **absences déclarées** : `grenier`, `Maison`, `maison ` (espace final), `""` et `null`, à chaque étape. Chacune est absente, avec `Prefab` nul et une `Absence` qui contient `nature sans pièce au kit`, plus le texte de la nature quand il n'est pas nul ;
  - **pièce manquante** : un `ScriptableObject.CreateInstance<KitDesBatiments>()` à une seule entrée `maison` dont `murs` est nul. `Piece("maison", Murs)` est absente avec `pièce manquante au kit : maison murs`, et `Piece("maison", Piquets)` est présente. L'instance est détruite (`Object.DestroyImmediate`) en fin de cas ;
  - **bornes de l'étape**, requis 300 : fourni 0 → `Piquets`, 149 → `Piquets`, 150 → `Murs`, 299 → `Murs` (tous en chantier), puis 300, pas en chantier → `Fini`. Plus requis 1 : fourni 0 → `Piquets`. Et requis 301 : fourni 150 → `Piquets`, 151 → `Murs` ;
  - **façade des exemples de MODELE** (`Presente`, tolérance 1e-9) :

| emprise | centre | façade | lacet |
|---|---|---|---|
| `(5,2) (15,2) (15,22) (5,22)` | (10 ; 12) | (0 ; −1) | 0 |
| `(5,−2) (15,−2) (15,−22) (5,−22)` | (10 ; −12) | (0 ; 1) | 180 |
| `(38,0) (38,25) (28,25) (28,0)` | (33 ; 12,5) | (1 ; 0) | 270 |
| `(42,0) (42,25) (52,25) (52,0)` | (47 ; 12,5) | (−1 ; 0) | 90 |
| `(15,2) (15,22) (5,22) (5,2)` | (10 ; 12) | (1 ; 0) | 270 |

    La quatrième ligne est le segment 1 à droite, début 0, façade 25, profondeur 10, calculé par la règle du modèle : `c0 = (40,0) + (2,0)`. La cinquième est le rectangle de la première ligne, commencé à un autre coin. Elle prouve que la façade est lue sur `c0→c1` et non devinée. Pour chaque ligne, le test vérifie aussi `sin θ == −FacadeX` et `cos θ == −FacadeY` (θ en radians, tolérance 1e-9) ;
  - **absences de pose** : 2 points → `emprise de 2 point(s)` ; `(5,2) (5,2) (15,22)` → `façade nulle` ; `(0,0) (10,0) (20,0)` → `emprise plate` ; une coordonnée `double.NaN` → `point non fini`. Chaque cas exige `Presente` faux, l'`Absence` qui contient `bâtiment 7`, et `CentreX` NaN.

## Conditions de succès

**SC1 — Unity compile et joue les tests (PC).**
Le workflow `unity` (poussée sur la branche) est vert : aucune `error CS`. Puis, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
(sans `-quit`). Le code de sortie vaut 0 et le XML dit `failed="0"`. Les cas de `ClientPlanTests`, `LecteurJsonTests`, `ClientLieuTests`, `PanneauLieuTests` et `ClientIntentionTests` y sont, en même nombre et sous les mêmes noms qu'avant. `KitDesBatimentsTests` compte **au moins 40 cas**. Moins, c'est un échec. La PR cite les totaux du XML.

**SC2 — les neuf pièces se chargent hors de l'éditeur (PC, dans SC1).**
Les neuf `TestCase` des pièces passent. Contre-épreuves faites à la main, dites dans la PR, chacune retirée ensuite :
- (a) déplacer `KitDesBatiments.asset` hors de `Resources/` : les neuf cas rougissent (`Charger()` nul) ;
- (b) dans l'asset, échanger les `murs` et le `fini` de la scierie : deux cas rougissent sur le nom.

Et par lecture :
```
grep -c "UnityEditor" 3d/unity/Assets/ForgeLocal3D/Pont/KitDesBatiments.cs
grep -c "Resources.Load" 3d/unity/Assets/ForgeLocal3D/Pont/KitDesBatiments.cs
```
La première rend `0`, la seconde au moins `1`.

**SC3 — une nature sans pièce est déclarée absente (PC, dans SC1).**
Les cas `grenier`, `Maison`, `maison `, `""`, `null` et « pièce manquante » passent. Contre-épreuve, à la main, dite dans la PR : faire rendre la pièce `maison` à toute nature inconnue fait rougir les cas d'absence.

**SC4 — l'étape suit le travail fourni (PC, dans SC1).**
Les bornes 149, 150 et 300 sur 300 passent, ainsi que 150 et 151 sur 301. Contre-épreuves faites à la main, dites dans la PR, chacune retirée ensuite :
- (a) écrire `<=` à la place de `<` : le cas 150/300 rougit ;
- (b) ne jamais rendre `Fini` (un bâtiment achevé reste aux murs) : le cas 300/300 rougit.

**SC5 — la façade de l'exemple de MODELE (PC, dans SC1).**
Les cinq lignes de la table et les quatre absences de pose passent. Contre-épreuves, à la main, dites dans la PR :
- (a) ne pas retourner `m` quand il pointe vers l'intérieur : les lignes 2 et 4 rougissent ;
- (b) lire la façade sur `c1→c2` : la ligne 1 rougit.

Et par lecture :
```
grep -cE "UnityEngine|UnityEditor" 3d/unity/Assets/ForgeLocal3D/Pont/EtapeDuBatiment.cs
```
rend `0`.

**SC6 — rien d'autre ne bouge.**
```
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC (pc\Tests.cmd)
git diff --name-only origin/master...HEAD
```
La suite du jeu reste verte. Le diff ne nomme que les fichiers du Périmètre et ce brief. `ClientPlan.cs`, les prefabs et leurs `.meta`, les asmdef, `DesertRoadTool.cs`, `DesertParcelles.cs`, `DesertCityRelance.cs`, `atelier_desert.py`, les scènes et `jeu/` sont hors du diff.

## Hors périmètre
- Poser les pièces dans la ville, `DesertRoadTool`, le panneau et la capture : sous-lot 2 de #363.
- Le contrôle du relancement des bâtiments (`atelier_desert.py batiments`) : sous-lot 3 de #363.
- Mettre une pièce à l'échelle de l'emprise, la poser sur le relief, aplanir le terrain, ou vérifier qu'elle tient dans sa parcelle. La scierie, large de 8,5 m, déborde une parcelle de 8 m : la recette du sous-lot 2 en tient compte.
- Une pièce pour d'autres natures (grenier, …), ou d'autres variantes de maison (`maison_pise_1` à `5`).
- Déplacer, renommer ou modifier les prefabs, les modèles, `DesertKit.cs` ou `kit.py`.
- Toucher `ClientPlan.cs`, `ClientLieu.cs`, `ClientIntention.cs`, `LecteurJson.cs`, `PanneauLieu.cs`, les asmdef, les autres fichiers de tests, ou `jeu/` (dont `MODELE.md`).
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.

## Photo
Sans objet : le lot ne change rien de ce qu'on voit à l'écran. `KitDesBatiments` et `LectureDuBatiment` ne sont appelés par aucune scène, aucun outil d'éditeur ni aucun panneau avant le sous-lot 2 de #363. Ce sous-lot posera les pièces dans la ville et portera son scénario de capture.
