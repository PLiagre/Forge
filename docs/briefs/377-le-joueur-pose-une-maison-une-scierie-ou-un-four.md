# Lot #377 — Le joueur pose une maison, une scierie ou un four dans la 3D
Jalon : J4 · Machine : pc · Taille prévue : 220 lignes

## But
Dans la capitale en 3D, le joueur pose un bâtiment à la souris. Il appuie sur 1 (maison), 2 (scierie) ou 3 (four), puis clique sur une parcelle. L'outil dépose l'intention `poser_batiment` au monde, et la pièce du kit se dessine à son étape d'après le plan après le tick. Un refus s'affiche au panneau avec sa raison, qu'il vienne de l'outil (« aucune parcelle sous le point ») ou du monde (« parcelle déjà bâtie »). C'est le geste « pose un atelier (une scierie, un four) » de CAP.md (jalon 4), et c'est le sous-lot 4 de #262.

## Règle du monde
Sans objet : c'est un lot de vue et d'outil. Le monde reste le seul juge : il revalide l'intention au dépôt et ne change pas. `jeu/` n'est pas touché. Niveau de fidélité : sans objet.

Ce que l'outil reprend de `jeu/sim/MODELE.md`, sans rien y changer :

- **« Les intentions du joueur ».** `poser_batiment` est validé **au dépôt** (`_pose_batiment`, `sim/intentions.py` l. 149). Le monde refuse, dans l'ordre : « parcelle absente du plan » (une découpe encore en attente doit d'abord être appliquée), « parcelle déjà bâtie : <id> », « parcelle déjà promise : <id> », « nature inconnue ». Une parcelle en chantier convient. Au tick suivant, le contour de la parcelle devient l'emprise ; le bâtiment est en chantier, à zéro journée fournie. Sans `foyers`, le monde en met 1.
- **« Le chantier et ses bras ».** 2 journées par m² : 240 pour la parcelle de 8 m × 15 m du geste. Un foyer envoie 5 bras par tick. La pièce reste donc aux piquets (`LectureDuBatiment.Etape` : `Piquets` tant que fourni × 2 < requis) pendant toute la capture.

Ce qui existe sur master (4e20195), vérifié le 07/10/2026 :

- `Pont/PoseDeBatiment.cs` (#376) : `PoseDeBatiment.Natures` (`maison`, `scierie`, `four`), et `PoseDeBatiment.Calculer(PlanLu, PointLocal, string nature)`, qui rend une `BatimentPose` : `Presente`, `Absence`, `Parcelle`, `Nature`, `IntentionJson` (sans `foyers`). Refus de l'outil : `nature inconnue : …`, `point non fini`, `aucune parcelle au plan`, `aucune parcelle sous le point : (x, y)`. Il ne lit pas les bâtiments : « déjà bâtie », c'est le reçu du monde.
- `Desert/DesertRoadTool.cs` (291 lignes, #375) : mode route et mode parcelle (`ModeParcelle`, `EntrerParcelle`, `ValiderParcelle`, `AideParcelle`). `Clic(Vector2)` lance un rayon sur le seul `TerrainCollider` : les pièces posées ne l'arrêtent pas. Après un dépôt accepté, `enAttente` est posé, et `Attendre()` redessine rues, parcelles et bâtiments (`DessinerBatiments`, ligne `Bâtiments : …`) dès que le plan dépasse le tick du dépôt.
- `Editor/Captures/Lot375.cs` : les aides `Point(rue, i, s, h)`, `Milieu(terrain, rue, i)` et `Cliquer(camera, ville, outil, vise, points…)`, privées. `Lot362` : `Monde`, `Identifiant`, `Deposer`, `Tick`, `Lire`, déjà `internal static`.
- Les pièces du kit tiennent dans 8 m de façade, sauf la scierie (8,54 m, elle déborde de 0,31 m : brief #369). La maison tient en 6,79 m × 6,91 m. La capture pose donc une maison sur la parcelle de 8 m × 15 m du geste.
- Touches déjà prises dans la scène du désert : F, Tab, flèches, Z, Q, S, D, W, A, H, F1 à F9, P, Entrée, Échap. Aucune touche chiffre. Les chiffres suivent la position physique (Input System) : sur un clavier AZERTY, c'est la touche « & 1 », sans Maj.

Le lot ne s'appuie sur rien que J2 ou J3 doivent encore livrer : `/plan`, `/intention`, `poser_batiment`, #369, #375 et #376 sont sur master.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot375.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot377.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot377.cs.meta

Précisions :

- **`DesertRoadTool.cs`**. Le commentaire de classe gagne une ligne « Lot 377 ». Ce qui s'ajoute :
  - `public string NatureBatiment{get;private set;}` : la nature choisie, `null` hors du mode bâtiment. `public bool ModeBatiment=>NatureBatiment!=null;`. `public BatimentPose Pose{get;private set;}` : le dernier calcul, `null` tant qu'aucun n'a été fait.
  - Une constante `AideBatiment = "Clic : poser sur une parcelle · 1 : maison · 2 : scierie · 3 : four · Échap : annuler"`. La constante `Aide` gagne seulement ` · 1, 2, 3 : bâtiment` à la fin. `AideParcelle` ne change pas.
  - **`public void EntrerBatiment(string nature)`** : `points` vidé, `Recu = null`, `Pose = null`, `ModeParcelle = false`, `NatureBatiment = nature`, puis `Afficher(AideBatiment)`. Elle ne juge pas la nature : `Calculer` le fait au clic.
  - **`EntrerParcelle()`** et **`Annuler()`** passent aussi `NatureBatiment` à `null`. Rien d'autre n'y change.
  - **`Clic(Vector2)`** : le rayon et le refus « Ce point n'est pas sur le terrain. » ne changent pas. En mode bâtiment, le point (`roads.PointExact(hit.point)`) **ne va pas dans `points`** : il passe à une méthode privée `PoserBatiment(x, y)`, et `Clic` rend vrai. Le mode parcelle et le mode route ne changent pas.
  - **`PoserBatiment(x, y)`** (privée : seul `Clic` l'appelle), dans cet ordre :
    1. `Recu = null`, `Pose = null`.
    2. Si `erreurCellule` est posée : elle l'affiche et s'arrête. Elle lit `plan.Lire(Cellule)`. Plan absent : `Pas de plan : <absence>`.
    3. `Pose = PoseDeBatiment.Calculer(lu.Plan, new PointLocal(x, y), NatureBatiment)`. Une absence s'affiche `Bâtiment refusé par l'outil : <Absence>`, et **rien n'est déposé** : `Recu` reste `null`.
    4. Sinon, `Recu = depot.Deposer(Pose.IntentionJson)`. Accepté : `enAttente = Recu`, et le panneau dit `Bâtiment déposé au monde : <nature> sur la parcelle <id>, dessiné au tick suivant (après le tick <n>).`. Refusé : `Le monde refuse le bâtiment : <Erreur>`. Sans reçu : `Pas de reçu : <Absence>`.
    5. L'outil **reste en mode bâtiment**, avec la même nature.
  - **`Afficher`** : en mode bâtiment, comme en mode parcelle, le message (s'il n'est pas l'aide) vient d'abord, puis la ligne d'état `Bâtiment : <nature> · un clic sur une parcelle`, puis `AideBatiment`. Les modes route et parcelle ne changent pas.
  - **`Update`** : `digit1Key` ou `numpad1Key` appelle `EntrerBatiment(PoseDeBatiment.Natures[0])`, 2 la nature 1, 3 la nature 2. En mode bâtiment, Entrée ne fait rien. P et Échap ne changent pas.
  - **Rien d'autre ne change** : `Valider`, `ValiderParcelle`, `Intention`, `Attendre`, `Ouvrir`, `Rafraichir`, `DessinerParcelles`, `DessinerBatiments`, `Dessiner`, `Bilan`, ni aucun autre texte du panneau. Le redessin après le tick est celui d'`Attendre`, tel quel.
- **`Lot375.cs`** : seuls `Point`, `Milieu` et `Cliquer` passent de `static` à `internal static`, pour que `Lot377` les reprenne. Aucune autre ligne ne change.
- **`Lot377.cs`** : le scénario de la Photo. Il passe par les aides de `Lot362` et de `Lot375`. La parcelle et les deux poses passent par l'outil.
- **Le `.meta`** est celui qu'Unity génère.

## Conditions de succès

**SC1 — Unity compile, rien d'existant ne rougit.**
Le workflow `unity` est vert : aucune `error CS`. Sur le PC, les tests EditMode `Forge.Pont.Tests` (commande de SC1 du lot #376) rendent 0 et `failed="0"`, avec le même nombre de cas qu'avant. La PR cite les totaux. `py -m pytest jeu -q` reste vert.

**SC2 — la capture pose le bâtiment par le geste et montre les deux refus, et elle peut échouer (PC).**
La capture `-forgeLot 377` se termine sans exception du scénario et écrit `<scène>--batiment-pose.png`. Le scénario lève une exception (la capture échoue) si l'une des exigences de la Photo tombe, notamment :
- la parcelle n'est pas tracée par le geste, ou pas au plan après le tick ;
- le clic sur la chaussée n'est pas refusé par l'outil avec `aucune parcelle sous le point`, ou il atteint le monde (`Recu` non nul) ;
- le clic sur la parcelle ne forme pas la maison sur cette parcelle, ou le monde ne l'accepte pas ;
- après le tick, `Attendre()` est faux, le bâtiment n'est pas au plan, ou sa pièce n'est pas dessinée aux piquets sous la racine des bâtiments ;
- la seconde pose (un four, sur la même parcelle) n'est pas refusée par le monde avec `parcelle déjà bâtie : <id>`, ou le plan gagne un bâtiment après un tick.

La PR cite le texte du panneau sur la photo.

**SC3 — contre-épreuves (PC).** Faites à la main, dites dans la PR avec le message d'exception, chacune retirée ensuite :
- (a) `PoserBatiment` ne dépose pas l'intention : la capture échoue (pas de reçu accepté) ;
- (b) l'outil refuse lui-même une parcelle qui porte un bâtiment du plan, avant le dépôt : la capture échoue sur la seconde pose, car le refus ne vient plus du monde ;
- (c) après un dépôt accepté, `enAttente` n'est pas posé : `Attendre()` rend faux, et la capture échoue ;
- (d) en mode bâtiment, `Clic` ajoute le point à `points` sans poser : la capture échoue sur le clic de la chaussée (`Pose` nulle).

**SC4 — les modes route et parcelle ne changent pas (PC).**
Depuis `3d/` :
- les captures `-forgeLot 293`, `-forgeLot 362`, `-forgeLot 369` et `-forgeLot 375` se terminent sans exception ;
- `py local3d/atelier_desert.py routes` rend 0, et `routes --service-sourd` échoue toujours sur la faute du service sourd ;
- `py local3d/atelier_desert.py relance` et `py local3d/atelier_desert.py batiments` rendent 0.

La PR montre les sorties.

**SC5 — rien d'autre ne bouge.**
```
git diff --name-only origin/master...HEAD
git diff -U0 origin/master...HEAD -- 3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs | grep '^-[^-]'
git diff -U0 origin/master...HEAD -- 3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot375.cs | grep -c '^-[^-]'
```
La première commande ne nomme que les fichiers du Périmètre et ce brief. La deuxième ne montre que des lignes retirées des membres listés aux Précisions : l'en-tête de commentaire, `Aide`, `Afficher`, `Update`, `Clic`, `Annuler` et `EntrerParcelle`. Aucune ligne de `Valider`, `ValiderParcelle`, `Intention`, `Attendre`, `Ouvrir`, `Rafraichir`, `DessinerParcelles`, `DessinerBatiments`, `Dessiner` ou `Bilan` n'est retirée. La troisième rend au plus 3, et chaque ligne remplacée ne diffère que par `internal`. Hors du diff : tout `Pont/` (dont `PoseDeBatiment.cs` et ses tests), `DesertParcelles.cs`, `DesertBatiments.cs`, `DesertRoads.cs`, `DesertCityCamera.cs`, les autres captures (dont `Lot362.cs` et `Lot369.cs`), les scènes, `atelier_desert.py` et `jeu/`.

## Hors périmètre
- Choisir le nombre de foyers au chantier : l'intention n'en porte pas, le monde en met 1.
- Montrer à l'écran la parcelle survolée, ou un aperçu de la pièce avant le clic.
- Refuser dans l'outil une parcelle déjà bâtie ou déjà promise : c'est le reçu du monde qui le dit.
- Retirer ou déplacer un bâtiment posé.
- Rendre la scierie posable sur une parcelle de 8 m : c'est la largeur de la pièce du kit, pas le geste.
- Changer `PoseDeBatiment`, `TraceDeParcelle`, `ClientIntention`, `ClientPlan`, le dessin des parcelles ou des bâtiments, le kit, la caméra, les autres captures (hors des trois mots `internal` de `Lot375`), les asmdef, les scènes ou `jeu/`.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.

## Photo
Une rue de terre battue sur le sable. Le long de son bord gauche, la parcelle de 8 m × 15 m tracée par le geste du joueur, au cordeau. Dessus, la maison aux piquets, façade vers la rue. Le panneau, en bas à gauche, dit `Le monde refuse le bâtiment : parcelle déjà bâtie : <id>`, puis `Bâtiment : four · un clic sur une parcelle`, puis l'aide du mode bâtiment. Le plan fixe de la capture, pris avant, montre le sable vierge.

Le scénario `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot377.cs`, `[ScenarioDeCapture(377, "batiment-pose")]`, est au Périmètre. Il joue avec le service de la capture : port 8000, vitesse 0, 30 ticks poussés.
1. Il trouve `DesertRoadTool` et `DesertCityCamera` (exception sinon), et met l'outil en `automatique`.
2. Il dépose la première route `plaine` du jeu de gestes par `Lot362.Deposer(port, outil.Intention(plaine))`, puis `Lot362.Tick`. Il retrouve la rue par `Lot362.Identifiant`, et note `n0` et `b0`, les nombres de parcelles et de bâtiments au plan. Il appelle `outil.Ouvrir()`, avec vrai exigé.
3. **La parcelle, par le geste**, comme l'étape 4 de `Lot375` : `outil.EntrerParcelle()`, `Lot375.Cliquer` sur `Lot375.Point(rue, 5, 1, 3)` puis `Lot375.Point(rue, 5, 9, 17)`, la caméra visant `Lot375.Milieu(terrain, rue, 5)`, puis `outil.ValiderParcelle()`. Il exige `Tracee.Presente` et `outil.Recu.Acceptee`. Puis `Lot362.Tick` et `outil.Attendre()`, avec vrai exigé. Le plan relu compte `n0 + 1` parcelles. Il note `p`, l'identifiant de la parcelle `n0`, et `c`, le centre de ses quatre coins (au plan).
4. **Échap.** `outil.EntrerBatiment("maison")`, puis `outil.Annuler()`. Il exige `ModeBatiment` faux et `ModeParcelle` faux.
5. **Le clic sur la chaussée.** `outil.EntrerBatiment("maison")`. Il exige `ModeBatiment` vrai et `ModeParcelle` faux. Puis `Lot375.Cliquer` sur `Lot375.Point(rue, 5, 4, 0)`, l'axe de la rue. Il exige : `outil.Pose` non nulle, `Presente` faux, `Absence` qui commence par `aucune parcelle sous le point`, `outil.Recu` nul, et la première ligne du panneau qui commence par `Bâtiment refusé par l'outil : aucune parcelle sous le point`.
6. **La maison.** `Lot375.Cliquer` sur `c`. Il exige : `Pose.Presente`, `Pose.Parcelle == p`, `Pose.Nature == "maison"`, `outil.Recu.Acceptee`, une ligne du panneau qui commence par `Bâtiment déposé au monde : maison sur la parcelle <p>`, et `ModeBatiment` toujours vrai.
7. **Le tick.** `Lot362.Tick`, puis `outil.Attendre()`, avec vrai exigé. Le plan relu compte `b0 + 1` bâtiments. Le dernier, `b`, est sur la parcelle `p`, de nature `maison`, en chantier. `LectureDuBatiment.Etape(b)` vaut `Piquets`. L'entrée de `outil.Batiments` pour `b` vaut `piquets`. `outil.RacineBatiments` a un enfant `Bâtiment <id de b>`. Une ligne du panneau commence par `Bâtiments : `.
8. **La seconde pose, refusée par le monde.** `outil.EntrerBatiment("four")`, puis `Lot375.Cliquer` sur `c`. Il exige : `Pose.Presente` (l'outil ne lit pas les bâtiments), `outil.Recu` présent et refusé, `Recu.Erreur == "parcelle déjà bâtie : <p>"`, et la première ligne du panneau égale à `Le monde refuse le bâtiment : parcelle déjà bâtie : <p>`. Puis `Lot362.Tick` : le plan compte toujours `b0 + 1` bâtiments, et celui de la parcelle `p` est toujours la maison.
9. Il écrit le panneau au journal (`Debug.Log("CAPTURE_377 " + …)`). Il vise `c`, converti par `Lot362.Monde`. Le cap est `LectureDuBatiment.Poser(b).LacetDegres + 180` : la caméra regarde la façade depuis la rue. Il pose la caméra par `ville.Poser(centre, cap, 45, 35)`, puis il laisse passer 10 images.

Le codeur regarde l'image lui-même et le dit dans la PR. La parcelle et la maison aux piquets doivent y être entières, le cordeau visible, et le panneau lisible. S'il faut une autre distance (entre 25 et 60 m) ou une autre inclinaison pour les cadrer, il la change et le dit.

Une exception fait échouer la capture.
