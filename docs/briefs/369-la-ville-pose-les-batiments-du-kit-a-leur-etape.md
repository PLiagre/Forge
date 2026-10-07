# Lot #369 — La ville pose les bâtiments du kit à leur étape
Jalon : J4 · Machine : pc · Taille prévue : 290 lignes

## But
La capitale ouverte dans Unity pose sur chaque parcelle bâtie la pièce du kit du désert qui montre où en est son bâtiment : piquets, murs ou bâtiment fini. La pièce est au sol, au centre de l'emprise, façade tournée vers la rue. Une pièce absente ou qui déborde se déclare au panneau. Unity relancé repose les mêmes pièces (CAP.md, jalon 4 : « la capitale en 3D, dessinée d'après le plan que tient le monde (rues, parcelles, bâtiments) ; le chantier qui prend des bras aux champs »).

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde n'est décidé ici, et `jeu/` n'est pas touché. Niveau de fidélité : sans objet.

Ce que la vue lit de `jeu/sim/MODELE.md`, sans rien y changer :

- **« Le plan du bourg ».** Un bâtiment a une `nature` (texte libre non vide ; le geste ne pose que `maison`, `scierie` ou `four`), une `emprise` (le contour de sa parcelle, copié à la pose), `en_chantier == (travail_fourni < travail_requis)`. Les bâtiments sont servis triés par identifiant. « L'orientation, l'étage et les matériaux restent de niveau 3 » : la pose et l'étape sont une convention de la vue, qui ne retourne rien au monde.
- **« Le chantier et ses bras ».** Un bâtiment demande 2 journées par m² d'emprise : 300 pour 10 m × 15 m. Chaque foyer envoie 5 bras par tick.
- **« Les intentions du joueur ».** La façade est le côté `c0→c1` du contour, qui borde la chaussée.
- **Le repère** est celui de #293 : `(x, y)` du plan devient `(-x, sol, -y)` dans Unity (`DesertParcelles.Monde`).

Ce qui existe sur master (a492625), vérifié le 07/10/2026 :

- `Pont/EtapeDuBatiment.cs` (#368) : `LectureDuBatiment.Etape(b)` rend `Piquets`, `Murs` ou `Fini`. `LectureDuBatiment.Poser(b)` rend une `PoseDuBatiment` : `Presente`, `Absence`, `CentreX`/`CentreY` (plan), `FacadeX`/`FacadeY`, et `LacetDegres`, tel que `Quaternion.Euler(0, θ, 0)` tourne la façade `+Z` d'une pièce vers la rue.
- `Pont/KitDesBatiments.cs` (#368) : `KitDesBatiments.Charger()` (nul si l'asset manque). `Piece(nature, etape)` rend une `PieceDuKit` (`Presente`, `Prefab`, `Absence` : `nature sans pièce au kit : <nature>` ou `pièce manquante au kit : <nature> <étape>`).
- `Desert/DesertParcelles.cs` (#362) : le modèle à suivre (classe ordinaire, racine, `Dessiner` qui vide puis pose, description hachée en SHA-256).
- `Desert/DesertRoadTool.cs` (#362) : `Ouvrir`, `Attendre` et `Rafraichir` appellent `DessinerParcelles(PlanLu)`. Rien ne lit `PlanLu.Batiments`.
- Les neuf prefabs ont leur pied à y ≈ 0 et sont centrés sur l'origine (`3d/local3d/desert/sorties/kit/unity-kit.json`). Leur enveloppe au sol est au plus de 8,54 m × 5,40 m pour les murs de la scierie, 6,79 m × 6,91 m pour la maison, 3,45 m × 2,63 m pour le four. Une parcelle de 10 m × 15 m les contient toutes. Celle de 8 m, de #362, ne contient pas la scierie : elle déborde de 0,31 m.
- **La recette de la photo, rejouée en Python le 07/10/2026** sur le monde de la capture : graine 0, 30 ticks poussés par `ForgeCapture`, cellule 1175, 328 paysans.
  - La route `plaine_neuve` de `ksar_des_sept_puits`, la première scène du build, est déposée, puis un tick.
  - Trois `decouper_parcelle` à gauche, segments 4, 6 et 8 (longs de 10,0012, 10,0024 et 10,0035 m ; le segment 0 ne fait que 9,99998 m et refuserait une façade de 10 m). `debut_m` 0, `facade_m` 10, `profondeur_m` 15, `foyers` 100. Deux ticks : les trois parcelles sont achevées (15/15).
  - Trois `poser_batiment` : maison à 24 foyers, scierie à 12, four à 1. Trois ticks après la pose : maison 300/300 (finie), scierie 180/300 (murs), four 15/300 (piquets).
  - Centres et lacets : (−36,18 ; 127,40) à 195°, (−54,75 ; 131,34) à 189°, (−73,63 ; 133,33) à 183°.

Le lot ne s'appuie sur rien que J2 ou J3 doivent encore livrer : `/plan`, `decouper_parcelle`, `poser_batiment`, l'étape Chantiers, #360, #361, #362 et #368 sont sur master.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Desert/DesertBatiments.cs
3d/unity/Assets/ForgeLocal3D/Desert/DesertBatiments.cs.meta
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot362.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot369.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot369.cs.meta

Précisions :

- **`DesertBatiments.cs`** (neuf, namespace `ForgeLocal3D`) : `public sealed class DesertBatiments`, une classe ordinaire, pas un `MonoBehaviour`. La scène ne change pas.
  - **Constructeur** `DesertBatiments(Transform parent, Terrain terrain)`. Il charge `KitDesBatiments.Charger()`. Nul : il lève `InvalidOperationException("Pas de kit des bâtiments (Resources/KitDesBatiments) : les bâtiments ne sont pas dessinés.")`. Sinon il crée l'enfant `Bâtiments du plan` sous `parent`.
  - **`public Transform Racine`**, **`public string Empreinte`** : SHA-256, en hexadécimal minuscule, de la description du dernier dessin. Elle vaut le hachage de `""` avant tout dessin.
  - **`public List<(long identifiant,string etat,string message)> Dessiner(IReadOnlyList<BatimentDuPlan> batiments)`** :
    1. Elle **vide d'abord** la racine : `Object.DestroyImmediate` sur chaque enfant. Elle ne détruit **jamais** un maillage ni un matériau : ce sont ceux des prefabs du kit (assets).
    2. Puis, pour chaque bâtiment, dans l'ordre reçu, ces contrôles dans cet ordre. Le premier qui échoue rend `(id, "refusee", "Bâtiment <id> non posé : <cause>")` et rien n'est posé :
       - `LectureDuBatiment.Poser(b)` absente : la cause est son `Absence` ;
       - un point de l'emprise a `|x|` ou `|y|` > `terrainData.size.x / 2 − 1` (la limite de `DesertParcelles`) : la cause est `hors du terrain.` ;
       - `kit.Piece(b.Nature, LectureDuBatiment.Etape(b))` absente : la cause est son `Absence` ;
       - **la pièce déborde de son emprise**. On instancie le prefab (`Object.Instantiate(prefab, Racine)`), nommé `Bâtiment <id>`. Sa position est `(−CentreX, sol, −CentreY)`, où le sol est `terrain.SampleHeight(p) + terrain.transform.position.y` au centre. Sa rotation est `Quaternion.Euler(0, (float)LacetDegres, 0)`. Pour chaque `MeshFilter` de l'instance qui a un `sharedMesh`, tous LOD compris, les 8 coins de `sharedMesh.bounds` passent par `TransformPoint`. Ils sont ramenés au plan par `(−x, −z)`. Un coin est **hors** s'il est hors du polygone de l'emprise (règle pair-impair) et à plus de 0,05 m de son côté le plus proche. S'il y en a un, l'instance est détruite (`DestroyImmediate`), et la cause est `<nom du prefab> déborde de son emprise de <d> m.`, avec `d` la plus grande de ces distances, en `F2`, culture invariante.
    3. Sinon, l'entrée vaut `(id, "piquets" | "murs" | "fini", "")`, l'étape en minuscules.
    4. **La description** : une ligne par bâtiment, dans l'ordre. Chaque ligne donne `<id> <etat>`, puis, pour une pièce posée, le nom du prefab, la position monde de l'instance (x y z) et son lacet, chaque nombre en `F2`, culture invariante, séparés par des espaces. Un bâtiment refusé n'a que sa tête. Un plan sans bâtiment donne une description vide.
- **`DesertRoadTool.cs`**
  - Membres publics neufs : `public readonly List<(long identifiant,string etat,string message)> Batiments`, `public Transform RacineBatiments` et `public string EmpreinteBatiments` (relais, `null` et `""` sans `DesertBatiments`).
  - Dans `Awake`, après les parcelles : `new DesertBatiments(transform, roads.terrain)` dans un `try`. S'il lève, le message est gardé, affiché comme celui des parcelles, et aucun bâtiment n'est jamais dessiné.
  - Une méthode privée `DessinerBatiments(PlanLu)` remplace `Batiments` par le résultat de `Dessiner(lu.Batiments)`. Elle rend la ligne `Bâtiments : P aux piquets, M aux murs, F fini(s).`, suivie d'une ligne par bâtiment refusé (son `message`).
  - **`Ouvrir()`**, **`Attendre()`** et **`Rafraichir()`** : `"\n" + DessinerBatiments(lu.Plan)` s'ajoute juste après la ligne des parcelles. Les bâtiments sont dessinés **après** les parcelles, donc sur le sol où les rues sont posées.
  - Aucun texte existant du panneau ne change (`Plan du tick…`, `Après le tick…`, `Rue <id> refusée…`, `Parcelles : …`). Le commentaire de classe gagne une ligne « Lot 369 ».
- **`Lot362.cs`** : on rend `internal static` ses cinq aides privées `Monde`, `Identifiant`, `Deposer`, `Tick` et `Lire`, pour que `Lot369` les appelle (`Lot362.Tick(port)`…). C'est le seul changement : rien d'autre ne bouge, ni le corps des aides ni le scénario.
- **`Lot369.cs`** : le scénario de la Photo.
- **Les `.meta`** sont ceux qu'Unity génère.

## Conditions de succès

**SC1 — Unity compile, rien d'existant ne rougit.**
Le workflow `unity` est vert : aucune `error CS`. Sur le PC, les tests EditMode `Forge.Pont.Tests` (commande de SC1 du lot #368) rendent 0 et `failed="0"`, avec le même nombre de cas qu'avant. `py -m pytest jeu -q` reste vert.

**SC2 — la capture pose les trois étapes, et elle peut échouer (PC).**
La capture `-forgeLot 369` se termine sans exception du scénario et écrit `<scène>--batiments.png`. Le scénario lève une exception (la capture échoue) si l'une de ses exigences tombe (voir la Photo) :
- les trois bâtiments posés valent `fini`, `murs`, `piquets` ;
- le plan les donne à 300/300, 180/300 et 15/300 ;
- chaque pièce est à moins de 0,01 m de son centre à l'horizontale, et sa façade est tournée vers la rue ;
- le nombre d'enfants de la racine est celui des pièces posées ;
- `Rafraichir()` repose les mêmes pièces : même empreinte, même nombre d'enfants.

La PR cite la ligne `Bâtiments : …` du panneau et l'empreinte.

**SC3 — contre-épreuves (PC).** Faites à la main, dites dans la PR avec le message d'exception, chacune retirée ensuite :
- (a) dans `Lot369`, une façade de 8 m au lieu de 10 : la scierie est refusée, `chantier_scierie_murs déborde de son emprise de 0.3x m.` est au panneau, et la capture échoue ;
- (b) dans l'asset `KitDesBatiments`, renommer l'entrée `four` en `fourX` : le panneau dit `Bâtiment <id> non posé : nature sans pièce au kit : four`, et la capture échoue ;
- (c) `Dessiner` pose toujours la pièce `Fini` : la capture échoue sur les états ;
- (d) la rotation de la pièce laissée à `Quaternion.identity` : la capture échoue sur la façade ;
- (e) `Dessiner` ne vide pas la racine : la capture échoue sur le nombre d'enfants après `Rafraichir`.

**SC4 — les contrôles des routes et du relancement restent verts (PC).**
Depuis `3d/` :
- `py local3d/atelier_desert.py relance` rend 0, sans défaut dans ses trois rapports ;
- `py local3d/atelier_desert.py relance --sans-service-neuf` échoue toujours, sur les mêmes défauts qu'avant ;
- `py local3d/atelier_desert.py routes` rend 0 ;
- `routes --service-sourd` échoue toujours sur la faute du service sourd ;
- les captures `-forgeLot 361` et `-forgeLot 362` se terminent sans exception.

La PR montre les sorties.

**SC5 — rien d'autre ne bouge.**
```
git diff --name-only origin/master...HEAD
git diff -U0 origin/master...HEAD -- 3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot362.cs | grep -c '^-[^-]'
git diff -U0 origin/master...HEAD -- 3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot362.cs | grep '^+[^+]' | grep -vc 'internal static'
```
La première ne nomme que les fichiers du Périmètre et ce brief. La deuxième rend `5`, la troisième `0`. Hors du diff : `DesertParcelles.cs`, `DesertCityRelance.cs`, `atelier_desert.py`, tout `Pont/` (dont `EtapeDuBatiment.cs`, `KitDesBatiments.cs`, l'asset et les tests), les prefabs, les scènes et `jeu/`.

## Hors périmètre
- Le contrôle du relancement des bâtiments (`atelier_desert.py batiments`, `DesertCityRelance`) : sous-lot 3 de #363.
- Mettre une pièce à l'échelle de l'emprise, l'incliner sur la pente, aplanir ou peindre le terrain dessous.
- Retirer ou modifier les colliders des prefabs. Choisir une variante de maison (`maison_pise_1` à `5`). Une pièce pour une autre nature.
- Suivre les chantiers à l'horloge du jeu : la ville se redessine à l'ouverture, après une route et par `Rafraichir`.
- Un geste du joueur dans Unity pour poser un bâtiment.
- Toucher `Pont/`, `DesertParcelles.cs`, `DesertRoads.cs`, `DesertCityTerrain.cs`, `DesertCityRelance.cs`, `atelier_desert.py`, `routes.py`, les autres captures, les asmdef, les prefabs ou `jeu/`.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.

## Photo
Une rue de terre battue sur le sable. Le long de son bord gauche, trois parcelles de 10 m × 15 m cernées de chaux et de bornes blanches. Sur la première, la maison de pisé finie. Sur la deuxième, la scierie aux murs. Sur la troisième, le four aux piquets. Les trois façades regardent la rue. Le panneau dit `Bâtiments : 1 aux piquets, 1 aux murs, 1 fini(s).`. Le plan fixe de la capture, pris avant, montre le sable vierge.

La demande nomme la capture `Lot363`. Elle est ici `Lot369`, au numéro du lot qui la livre.

Le scénario `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot369.cs`, `[ScenarioDeCapture(369, "batiments")]`, au Périmètre, joue avec le service de la capture (port 8000, vitesse 0, 30 ticks poussés). Tout appel au service passe par les aides de `Lot362` (hors du fil de l'éditeur).
1. Il trouve `DesertRoadTool` et `DesertCityCamera` (exception sinon), et met l'outil en `automatique`.
2. Il dépose la première route `plaine` du jeu de gestes, puis un tick. Il retrouve la rue par `Lot362.Identifiant`, et note `n0` (parcelles) et `b0` (bâtiments) au plan.
3. Il dépose trois `decouper_parcelle` sur cette rue, à gauche : segments 4, 6 et 8, `debut_m` 0, `facade_m` 10, `profondeur_m` 15, `foyers` 100. Puis deux ticks. Il exige que les parcelles `n0`…`n0+2` du plan soient achevées.
4. Il dépose trois `poser_batiment` sur ces parcelles, dans l'ordre : `maison` à `foyers` 24, `scierie` à 12, `four` à 1. Puis trois ticks.
5. Il relit le plan et exige, pour les bâtiments `b0`…`b0+2` : maison 300/300 et pas en chantier, scierie 180/300, four 15/300.
6. Il appelle `outil.Ouvrir()`, le code même du `Start`, et exige :
   - vrai ;
   - les trois dernières entrées de `outil.Batiments` valent `fini`, `murs`, `piquets` ;
   - une ligne du panneau commence par `Bâtiments : ` ;
   - `RacineBatiments.childCount` égale le nombre d'entrées de `outil.Batiments` qui ne sont pas `refusee` ;
   - pour chacun des trois, l'enfant `Bâtiment <id>` existe. Sa distance horizontale à `(−CentreX, −CentreY)` de `LectureDuBatiment.Poser` est sous 0,01 m. Le produit scalaire de son `forward` (à l'horizontale, normalisé) avec `(−FacadeX, 0, −FacadeY)` dépasse 0,99.
7. Il note `EmpreinteBatiments` et le nombre d'enfants, appelle `outil.Rafraichir()` (vrai exigé), et exige la même empreinte et le même nombre d'enfants. L'empreinte diffère de celle d'un plan vide (SHA-256 de `""`).
8. Il vise le centre des 12 coins des trois emprises, convertis par `Lot362.Monde`. Le cap est `LacetDegres + 180` du bâtiment du milieu : la caméra regarde les façades depuis la rue. Il pose la caméra par `ville.Poser(centre, cap, 35, 70)` et laisse passer 10 images.

Le codeur regarde l'image lui-même et le dit dans la PR. Les trois pièces doivent y être entières et distinctes. S'il faut une autre distance (entre 50 et 90 m) pour les cadrer, il la change et le dit.

Une exception fait échouer la capture.
