# Lot #362 — La ville dessine les parcelles du plan
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Après avoir posé ses rues, la capitale ouverte dans Unity trace au sol le contour de chaque parcelle du plan que tient le monde. Une parcelle encore en chantier porte un cordeau tendu sur des piquets. Une parcelle achevée porte une borne à chaque coin. Unity relancé redessine les mêmes parcelles, et devant un service neuf il n'en dessine aucune (CAP.md, jalon 4 : « dessinée d'après le plan que tient le monde (rues, parcelles, bâtiments) »).

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde n'est décidé ici, et `jeu/` n'est pas touché. Niveau de fidélité : sans objet.

Ce que la vue respecte de `jeu/sim/MODELE.md` :

- **« Le plan du bourg ».** Une parcelle a un `identifiant`, un `contour` d'au moins 3 points en mètres locaux du bourg, et `en_chantier == (travail_fourni < travail_requis)`. Les parcelles sont servies triées par identifiant. Leurs chevauchements, entre elles, avec une rue ou avec l'extérieur du bourg, sont de niveau 3 : la vue dessine le contour tel quel, sans le corriger ni le refuser pour cela. « Aucun bâtiment ni flux ne découle encore de son achèvement » : les bornes ne sont qu'un dessin.
- **« Le chantier et ses bras ».** Une parcelle s'achève quand son travail fourni atteint le requis. Le cordeau ou les bornes ne font que lire `en_chantier`.
- **Le repère** est celui que #293 a fixé pour les rues : un point `(x, y)` du plan devient, dans Unity, `(-x, hauteur du terrain, -y)`. C'est la conversion de `DesertCityRelance.World` et de `Lot361.Monde`.

Ce qui existe sur master (f8414ec), vérifié le 06/10/2026 :

- `ClientPlan.cs` (#360) rend `PlanLu.Parcelles`, une liste de `ParcelleDuPlan` (`Identifiant`, `Contour`, `EnChantier`, `TravailRequis`, `TravailFourni`) dans l'ordre servi. Un plan contradictoire est refusé en entier.
- `DesertRoadTool.cs` (#361) : `Ouvrir()`, appelée par `Start`, prépare une copie vierge du terrain et pose toutes les rues du plan par `Dessiner`. `Attendre()` pose les rues neuves après un tick. Ni l'un ni l'autre ne lit les parcelles.
- `DesertCityRelance.cs` et `atelier_desert.py relance` (#361) : trois sessions Unity (`Tracer`, `Relancer`, `Vierge`). Aucune ne crée de parcelle.
- La scène `Forge_Desert_Ville_<id>` est construite par `DesertCityTerrain.cs`. Le lot n'y ajoute **aucun** composant : tout ce qu'il dessine est créé à l'exécution par l'outil, comme son panneau.
- Mesuré le 06/10/2026 sur le monde du service (graine par défaut, cellule 1175, 327 paysans). Une rue de 11 points, à pas de 10 m, est tracée, suivie d'un tick. Deux `decouper_parcelle` sont ensuite déposées sur cette rue : la première sur le segment 3 (`debut_m` 1, `facade_m` 8, `profondeur_m` 15, `cote` gauche, `foyers` 100), la seconde sur le segment 4 (mêmes mesures, `foyers` 1 par défaut). Après un tick, puis un autre tick avec une route déposée, on obtient la parcelle 0 achevée (12/12) et la parcelle 1 en chantier (10/12). C'est la recette du contrôle et de la photo.

Le lot ne s'appuie sur rien que J2 ou J3 doivent encore livrer : `/plan`, `decouper_parcelle`, l'étape Chantiers, #360 et #361 sont sur master.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Desert/DesertParcelles.cs
3d/unity/Assets/ForgeLocal3D/Desert/DesertParcelles.cs.meta
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Editor/DesertCityRelance.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot362.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot362.cs.meta
3d/local3d/atelier_desert.py

Précisions :

- **`DesertParcelles.cs`** (neuf) : une classe C# ordinaire, `public sealed class DesertParcelles`. Ce n'est **pas** un `MonoBehaviour`, et la scène ne change donc pas.
  - **Constructeur** `DesertParcelles(Transform parent, Terrain terrain)`. Il crée l'enfant `Parcelles du plan` sous `parent`, et cinq matériaux partagés, copies de `GraphicsSettings.currentRenderPipeline.defaultMaterial`, chacun avec sa couleur (`material.color`) :
    - ruban de chantier : sable gratté (0,50 ; 0,38 ; 0,26) ;
    - ruban achevé : chaux (0,93 ; 0,91 ; 0,86) ;
    - piquet : bois sombre (0,30 ; 0,20 ; 0,12) ;
    - cordeau : chanvre (0,55 ; 0,33 ; 0,18) ;
    - borne : pierre blanchie (0,90 ; 0,88 ; 0,82).

    Sans matériau par défaut, il lève `InvalidOperationException`.
  - **`public Transform Racine`** : l'enfant `Parcelles du plan`.
  - **`public string Empreinte`** : SHA-256, en hexadécimal minuscule, de la description du dernier dessin (définie plus bas).
  - **`public List<(long identifiant,string etat,string message)> Dessiner(IReadOnlyList<ParcelleDuPlan> parcelles)`**.
    1. Elle **vide d'abord** la racine : `Object.DestroyImmediate` sur chaque enfant et sur son maillage. Un `Destroy` différé laisserait les anciens enfants comptés dans la même image.
    2. Puis, pour chaque parcelle, dans l'ordre reçu :
       - **hors du terrain** : un point du contour a `|x|` ou `|y|` > `terrainData.size.x / 2 − 1`. Rien n'est posé. L'entrée vaut `(id, "refusee", "Parcelle <id> hors du terrain : non dessinée.")` ;
       - **sinon**, elle crée l'enfant `Parcelle <id>`, qui porte :
         - **le ruban au sol** : un seul maillage (`MeshFilter` + `MeshRenderer`). Chaque côté du contour, coin `i` vers coin `i+1` (le dernier vers le premier), est échantillonné à pas égaux d'au plus 0,5 m, ses deux bouts compris. À chaque échantillon, deux sommets à ±0,10 m de l'axe, perpendiculairement au côté et à l'horizontale, à la hauteur du terrain + 0,03 m. Deux triangles par pas. Il est en matériau de ruban de chantier si `EnChantier`, de ruban achevé sinon ;
         - **en chantier, le cordeau** : à chaque coin, un piquet, cube 0,06 × 0,8 × 0,06 m, centre à sol + 0,35 m. Entre deux coins consécutifs, le dernier vers le premier, un cordeau : cube 0,03 × 0,03 × longueur, tendu droit d'un point à sol + 0,6 m au-dessus d'un coin au point à sol + 0,6 m au-dessus de l'autre (`LookAt`). L'entrée vaut `(id, "cordeau", "")` ;
         - **achevée, les bornes** : à chaque coin, une borne, cube 0,3 × 0,5 × 0,3 m, centre à sol + 0,15 m, tournée dans l'axe du côté qui part de ce coin. L'entrée vaut `(id, "bornes", "")`.

       Le « sol » d'un point est `terrain.SampleHeight(p) + terrain.transform.position.y`. Il se lit sur le terrain du moment : la copie où les rues sont déjà posées. Piquets, cordeaux et bornes sont des `GameObject.CreatePrimitive(PrimitiveType.Cube)`. Leur collider est retiré (`DestroyImmediate`), et ils reçoivent le matériau partagé de leur rôle.
    3. **La description**, dont `Empreinte` est le hachage : une ligne par parcelle, dans l'ordre. Chaque ligne donne `<id> <etat>`, puis la position monde de chaque pièce posée dans l'ordre de création (piquets, cordeaux ou bornes), puis chaque sommet du ruban. Chaque coordonnée est écrite en `F2`, culture invariante, séparée par des espaces. Une parcelle refusée n'a que sa tête. Un plan sans parcelle donne une description vide.
- **`DesertRoadTool.cs`**
  - Membres publics neufs :
    - `public readonly List<(long identifiant,string etat,string message)> Parcelles` : le dernier dessin, dans l'ordre du plan ;
    - `public Transform RacineParcelles` et `public string EmpreinteParcelles` : relais de `DesertParcelles`, `null` et `""` si elle n'existe pas.
  - Dans `Awake`, l'outil crée sa `DesertParcelles(transform, roads.terrain)`. Si elle lève, il affiche son message et ne dessine jamais de parcelle.
  - Une méthode privée `DessinerParcelles(PlanLu)` remplace `Parcelles` par le résultat de `Dessiner`. Elle rend la ligne du panneau `Parcelles : C en chantier, B achevée(s).`, suivie d'une ligne par parcelle refusée (son `message`).
  - **`Ouvrir()`** : après les rues, et seulement après elles, `DessinerParcelles(lu.Plan)`. Sa ligne s'ajoute au panneau sous les lignes des rues.
  - **`Attendre()`** : après les rues neuves, il redessine toutes les parcelles du plan relu. Une rue neuve a pu changer le sol sous elles.
  - **`public bool Rafraichir()`** (neuve) : elle lit le plan. S'il est absent, ou si la cellule est en erreur, elle l'affiche et rend faux, sans toucher aux parcelles. Sinon elle redessine les parcelles, affiche `Plan du tick T : ` suivi de la ligne des parcelles, et rend vrai. Elle ne touche pas aux rues. Aucun appel périodique : seuls le contrôle et un geste l'appellent.
  - Les lignes des rues (`Plan du tick…`, `Après le tick…`, `Rue <id> refusée par le relief…`) ne changent pas de texte.
- **`DesertCityRelance.cs`** : **on n'y fait qu'ajouter des lignes**. Aucune ligne existante n'est retirée ni modifiée (voir SC6).
  - Une classe sérialisée neuve `Trace{public long identifiant=-1;public string etat="",message="";}`.
  - Une ligne neuve de champs dans `Rapport` :
    - `parcelles_plan` (`Trace[]`) : chaque parcelle relue par le `ClientPlan` du rapport, état `cordeau` si `EnChantier`, `bornes` sinon ;
    - `parcelles` (`Trace[]`) : `tool.Parcelles` ;
    - `pieces_parcelles` (`int`) : le nombre d'enfants de `tool.RacineParcelles`, -1 si elle est nulle ;
    - `empreinte_parcelles` : `tool.EmpreinteParcelles`.

    Ils sont remplis dans `Run`, par des lignes ajoutées (la lecture des parcelles dans le bloc `using` du `ClientPlan`).
  - **`Tracer`** gagne deux insertions :
    - **entre `report.traces=…` et la route raide** : la rue de plaine est `traces[0]`. Si elle manque, c'est un défaut, et pas de parcelle. Sinon, deux dépôts `decouper_parcelle` par `ClientIntention` dans un `Task.Run`, comme celui de la route raide : `"rue":<plaine>,"segment":3,"debut_m":1,"facade_m":8,"profondeur_m":15,"cote":"gauche","foyers":100`, puis la même chose sur `"segment":4`, sans `foyers`. Chaque reçu non accepté est un défaut. Puis `Tick(port,faults)` ;
    - **après le dernier `Tick` de la méthode** : `tool.Rafraichir()`. S'il rend faux, c'est un défaut.
  - **Défauts ajoutés à `JugerTracer`** :
    - `parcelles_plan` qui n'est pas exactement 2 parcelles, la première `bornes` et la seconde `cordeau` (« le plan n'a pas une parcelle achevée puis une en chantier ») ;
    - `parcelles` différente de `parcelles_plan` (mêmes identifiants, mêmes états, même ordre) ;
    - une parcelle `refusee` ;
    - `pieces_parcelles != 2`.
  - **Défauts ajoutés à `JugerRelance`** :
    - `parcelles` différente de `parcelles_plan`, ou de `tracer.parcelles` ;
    - `pieces_parcelles != 2` ;
    - `empreinte_parcelles != tracer.empreinte_parcelles` (« les parcelles relancées n'ont pas l'empreinte de la session tracer »).
  - **Défauts ajoutés à `JugerVierge`** :
    - `parcelles_plan` non vide ;
    - `parcelles` non vide, ou `pieces_parcelles != 0`, avec un défaut qui contient « parcelle(s) dessinée(s) contre un service vide ».
  - Le commentaire de classe dit que les sessions portent aussi les parcelles.
- **`atelier_desert.py`** : dans `relance`, une ligne `print` **ajoutée** après la ligne de chaque session. Elle donne `parcelles : <id état, …> ; plan : <id état, …> ; pièces <n> ; empreinte des parcelles <h>`. Rien d'autre ne change, docstring comprise : ni les actions, ni les options, ni `routes`, ni le service.
- **`Lot362.cs`** : le scénario de la Photo.
- **Les deux `.meta`** sont ceux qu'Unity génère.

## Conditions de succès

**SC1 — Unity compile, rien d'existant ne rougit.**
Le workflow `unity` est vert : aucune `error CS`. Sur le PC, les tests EditMode `Forge.Pont.Tests` (commande de SC1 du lot #360) rendent 0 et `failed="0"`, avec le même nombre de cas qu'avant. `py -m pytest jeu -q` reste vert.

**SC2 — les parcelles reviennent au relancement (PC).**
Depuis `3d/` : `py local3d/atelier_desert.py relance` rend 0, et les trois rapports existent sans défaut. Valeurs exigées par Unity, relues dans les rapports pour la PR :
- `tracer.json` : `parcelles_plan` = `[0 bornes, 1 cordeau]`, `parcelles` identique, `pieces_parcelles` 2. Tout ce que #361 exigeait tient encore (2 traces, 3 rues, `empreinte != vierge`).
- `relance.json` : `parcelles` = `parcelles_plan` = `tracer.parcelles`, `pieces_parcelles` 2, `empreinte_parcelles` **égale** à celle de `tracer.json`. L'empreinte du terrain égale toujours celle de `tracer.json`.
- `vierge.json` : `parcelles_plan` vide, `parcelles` vide, `pieces_parcelles` 0, et tout ce que #361 exigeait.

La PR cite les lignes imprimées des trois sessions.

**SC3 — contre-épreuve : aucune parcelle contre un service vide (PC).**
`py local3d/atelier_desert.py relance --sans-service-neuf` rend un code non nul. `vierge.json` porte un défaut qui contient « parcelle(s) dessinée(s) contre un service vide », à côté de « la ville n'est pas revenue vierge ». Son `parcelles_plan` compte 2 parcelles. La PR montre la sortie.
Contre-épreuves faites à la main et dites dans la PR, chacune retirée ensuite :
- (a) `Dessiner` pose toujours le cordeau, quel que soit `EnChantier` : `tracer` rougit (parcelles ≠ plan) ;
- (b) `Ouvrir` ne dessine pas les parcelles : `relance` rougit (parcelles ≠ plan, pièces 0) ;
- (c) `Dessiner` ne vide pas la racine avant de dessiner : `tracer` rougit sur `pieces_parcelles` ;
- (d) `Dessiner` décale chaque pièce de 1 cm vers l'est à chaque appel (compteur statique) : `relance` rougit sur `empreinte_parcelles`.

**SC4 — le contrôle des routes et celui de #361 restent verts (PC).**
`py local3d/atelier_desert.py routes` rend 0 sans défaut. `routes --service-sourd` échoue toujours sur la faute du service sourd. La capture de #361 (`-forgeLot 361`) se termine toujours sans exception.

**SC5 — la photo se prend (PC).**
La capture du lot (`-forgeLot 362`) se termine sans exception du scénario et écrit `<scène>--parcelles.png`. Le codeur regarde l'image lui-même. On doit y voir la rue de terre battue, la parcelle aux bornes blanches et la parcelle au cordeau sur ses piquets. Il le dit dans la PR.

**SC6 — rien d'autre ne bouge.**
```
git diff --name-only origin/master...HEAD
git diff origin/master...HEAD -- 3d/unity/Assets/ForgeLocal3D/Editor/DesertCityRelance.cs 3d/local3d/atelier_desert.py | grep '^-[^-]'
```
La première commande ne nomme que les fichiers du Périmètre et ce brief. La seconde ne sort **aucune ligne** : aucun défaut existant n'est retiré ni modifié, et `atelier_desert.py` ne gagne que sa ligne `print`. `DesertRoads.cs`, `DesertCityRoads.cs`, `DesertCityTerrain.cs`, `ClientPlan.cs`, `Lot361.cs`, `Lot263.cs`, `routes.py`, les scènes et `jeu/` sont hors du diff.

## Hors périmètre
- Dessiner les bâtiments du plan (piquets, murs, fini du kit) : sous-lot 4 de #261.
- Un geste du joueur dans Unity pour découper une parcelle.
- Suivre l'avancement des chantiers à l'horloge du jeu (relecture périodique du plan) : la ville se redessine à l'ouverture, après une route, et par `Rafraichir`.
- Refuser une parcelle pour son relief, son chevauchement d'une rue ou d'une autre parcelle (niveau 3 au modèle). Aplanir ou peindre le terrain sous une parcelle : le terrain n'est pas touché.
- Ajouter un composant ou une référence sérialisée à la scène, ou toucher `DesertCityTerrain.cs`.
- Toucher `DesertRoads.cs`, `DesertCityRoads.cs`, `ClientPlan.cs`, `ClientIntention.cs`, `Lot361.cs`, `Lot263.cs`, `routes.py`, les asmdef, ou `jeu/`.
- Toucher `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md` ou `CAP.md`.

## Photo
Une rue de terre battue sur le sable. Le long de son bord gauche, deux parcelles de 8 m sur 15 m, côte à côte : la première achevée, cernée d'un trait de chaux, avec une borne blanche à chaque coin ; la seconde en chantier, cernée de sable gratté, avec un cordeau tendu sur quatre piquets. Le panneau dit `Parcelles : 1 en chantier, 1 achevée(s).`. Le plan fixe de la capture, pris avant, montre le sable vierge.

Le scénario `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot362.cs`, `[ScenarioDeCapture(362, "parcelles")]`, au Périmètre, joue avec le service de la capture (port 8000, vitesse 0). Tout appel au service passe hors du fil de l'éditeur (`Task.Run`), comme `Lot361` :
1. Il trouve `DesertRoadTool` et `DesertCityCamera` (exception sinon), et met l'outil en `automatique`.
2. Il dépose la première route `plaine` du jeu de gestes par `ClientIntention.Deposer(outil.Intention(plaine))` (reçu accepté exigé), puis un tick (`POST /tick?n=1`, statut 200). Il relit le plan et retrouve l'identifiant de la rue, comme `Lot361.Identifiant` (copié, pas partagé). Il note le nombre de parcelles du plan, `n0`.
3. Il dépose les deux `decouper_parcelle` de `Tracer` sur cette rue (segment 3 avec `foyers` 100, segment 4 sans `foyers`), avec reçus acceptés, puis deux ticks.
4. Il appelle `outil.Ouvrir()`, le code même que le `Start` joue au lancement. Il exige :
   - vrai ;
   - les deux dernières entrées de `outil.Parcelles` (les parcelles d'indices `n0` et `n0+1` du plan) valent `bornes` puis `cordeau` ;
   - `outil.Message` contient une ligne qui commence par `Parcelles : `.
5. Il vise le centre des 8 coins des deux parcelles, relus au plan et convertis par `(-x, sol, -y)`. Il pose la caméra par `ville.Poser(centre, ville.Cap, 50, 35)` et laisse passer 10 images.

Une exception fait échouer la capture.
