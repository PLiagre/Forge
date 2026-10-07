# Lot #375 — Le joueur trace une parcelle dans la 3D
Jalon : J4 · Machine : pc · Taille prévue : 210 lignes

## But
Dans la capitale en 3D, le joueur découpe une parcelle à la souris. Il appuie sur P, pose deux coins le long d'une rue, puis valide avec Entrée (ou annule avec Échap). L'outil dépose l'intention `decouper_parcelle` au monde, et la parcelle se dessine d'après le plan après le tick. Un refus s'affiche au panneau avec sa raison, qu'il vienne de l'outil ou du monde. C'est le geste « découpe des parcelles » de CAP.md (jalon 4), et c'est le sous-lot 2 de #262.

## Règle du monde
Sans objet : c'est un lot de vue et d'outil. Le monde reste le seul juge : il revalide l'intention au dépôt et ne change pas. `jeu/` n'est pas touché. Niveau de fidélité : sans objet.

Ce que l'outil reprend de `jeu/sim/MODELE.md`, sans rien y changer :

- **« Les intentions du joueur ».** `decouper_parcelle` entre au plan **en chantier** au tick qui suit le dépôt. Sans champ `foyers`, le monde met 1 foyer. Le monde **n'interdit pas** qu'une parcelle en chevauche une autre : c'est de niveau 3. Il ne refuse donc pas une seconde parcelle parce qu'elle est seconde. Ses refus sont ceux du dépôt (rue absente, segment hors de la rue, « façade dépasse le segment »…), et il les rend dans le reçu.
- **Le repère** est celui de #293 : le point `(x, y)` du plan devient `(-x, sol, -y)` dans Unity. `DesertRoads.PointExact(hit.point)` fait le chemin inverse, arrondi au centimètre.

Ce qui existe sur master (fb92f58), vérifié le 07/10/2026 :

- `Pont/TraceDeParcelle.cs` (#374) : `TraceDeParcelle.Calculer(PlanLu, PointLocal premier, PointLocal second)` rend une `ParcelleTracee`. Elle a `Presente`, `Absence`, `Rue`, `Segment`, `DebutM`, `FacadeM`, `ProfondeurM`, `Cote` et `IntentionJson` (sans `foyers`). Le premier point choisit la rue et le segment (à 10 m au plus). Le second donne la fin de la façade, le côté et la profondeur. Les refus de l'outil : `point non fini`, `aucune rue au plan`, `point trop loin d'une rue : …`, `façade dépasse le segment : …`, `façade nulle`, `second point dans la chaussée : …`.
- `Desert/DesertRoadTool.cs` (247 lignes) ne connaît que le mode route. Le clic gauche passe par `Clic(Vector2)`, qui ajoute à `points`. Entrée appelle `Valider()`, Échap `Annuler()`. Le panneau passe par `Afficher(texte)`, et `Aide` est la ligne d'aide. Après un dépôt accepté, `enAttente` est posé, et `Attendre()` redessine rues, parcelles et bâtiments dès que le plan dépasse le tick du dépôt. `Update` le rappelle tous les quarts de seconde. En `automatique`, c'est la capture qui l'appelle.
- `Editor/Captures/Lot362.cs` : les aides `internal static` `Monde`, `Identifiant`, `Deposer`, `Tick` et `Lire`, que `Lot369` réutilise déjà.
- La route `plaine_neuve` de `ksar_des_sept_puits` (la première route `plaine` du jeu de gestes) a 11 points et 4 m de largeur. Ses segments font environ 10 m, et la route tourne de 3° à chaque point. Le segment 5 va de (−38,55 ; 137,87) à (−48,33 ; 139,95), long de 9,9987 m. Le segment 7 va de (−58,21 ; 141,51) à (−68,15 ; 142,56), long de 9,9953 m.
- Aucune touche P n'est prise dans le projet (`DesertCityCamera` : F, Tab, flèches, ZQSD/WASD ; `DesertEnvironment` : H, F1–F9).

Le lot ne s'appuie sur rien que J2 ou J3 doivent encore livrer : `/plan`, `/intention`, `decouper_parcelle`, #362 et #374 sont sur master.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot375.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot375.cs.meta

Précisions :

- **`DesertRoadTool.cs`**. Le commentaire de classe gagne une ligne « Lot 375 ». Ce qui s'ajoute :
  - `public bool ModeParcelle{get;private set;}`, faux au départ. `public ParcelleTracee Tracee{get;private set;}` : le dernier calcul de l'outil, `null` tant qu'aucun n'a été fait.
  - Une constante `AideParcelle = "Clic : poser deux coins le long d'une rue · Entrée : déposer la parcelle · Échap : annuler"`. La constante `Aide` gagne seulement ` · P : parcelle` à la fin. C'est le seul texte du mode route qui change.
  - **`public void EntrerParcelle()`** : `points` vidé, `Recu = null`, `Tracee = null`, `ModeParcelle = true`, puis `Afficher(AideParcelle)`.
  - **`Annuler()`** passe aussi `ModeParcelle` à faux. Le reste ne change pas : points vidés, `Recu = null`, `Afficher(Aide)`. Échap ramène donc toujours au mode route.
  - **`Clic(Vector2)`** : le raycast et la conversion ne changent pas. En mode parcelle, s'il y a déjà deux points, le clic n'ajoute rien. Le panneau dit `Deux coins suffisent : Entrée pour déposer, Échap pour annuler.`, et la méthode rend faux. Sinon le point s'ajoute et l'aide du mode courant s'affiche.
  - **`public ParcelleTracee ValiderParcelle()`**, dans cet ordre :
    1. Hors du mode parcelle, elle rend `null` sans rien afficher.
    2. Avec moins de deux points : `Il faut deux coins.`, et elle rend `null`, points gardés.
    3. `Recu = null`. Les deux points sont copiés, puis `points` est vidé.
    4. Si `erreurCellule` est posée : elle l'affiche et rend `null`. Elle lit `plan.Lire(Cellule)`. Plan absent : `Pas de plan : <absence>`, et elle rend `null`.
    5. `Tracee = TraceDeParcelle.Calculer(lu.Plan, new PointLocal(x1, y1), new PointLocal(x2, y2))`. Une absence s'affiche `Parcelle refusée par l'outil : <Absence>`, et **rien n'est déposé** : `Recu` reste `null`.
    6. Sinon, `Recu = depot.Deposer(Tracee.IntentionJson)`. Accepté : `enAttente = Recu`, et le panneau dit `Parcelle déposée au monde : elle se dessine au tick suivant (après le tick <n>).`. Refusé : `Le monde refuse la parcelle : <Erreur>`. Sans reçu : `Pas de reçu : <Absence>`.
    7. Elle rend `Tracee`. L'outil **reste en mode parcelle** : le joueur peut tracer la suivante, et Échap le ramène au mode route.
  - **`Afficher`** : en mode parcelle, la ligne d'état vaut `Parcelle le long d'une rue · <n>/2 coin(s)`. Le texte de l'aide (`Aide` ou `AideParcelle`) se place sous l'état, comme l'est `Aide` aujourd'hui. En mode route, la ligne d'état ne change pas.
  - **`Update`** : P (`k.pKey.wasPressedThisFrame`) appelle `EntrerParcelle()`. Entrée appelle `ValiderParcelle()` en mode parcelle, `Valider()` sinon. Échap appelle toujours `Annuler()`.
  - **Rien d'autre ne change** : `Valider`, `Intention`, `Attendre`, `Ouvrir`, `Rafraichir`, `DessinerParcelles`, `DessinerBatiments`, `Dessiner`, `Bilan`, ni aucun autre texte du panneau. Le redessin après le tick est celui d'`Attendre`, tel quel.
- **`Lot375.cs`** : le scénario de la Photo. Il passe par les aides de `Lot362` pour tout appel direct au service. Le dépôt des parcelles, lui, passe par l'outil.
- **Le `.meta`** est celui qu'Unity génère.

## Conditions de succès

**SC1 — Unity compile, rien d'existant ne rougit.**
Le workflow `unity` est vert : aucune `error CS`. Sur le PC, les tests EditMode `Forge.Pont.Tests` (commande de SC1 du lot #374) rendent 0 et `failed="0"`, avec le même nombre de cas qu'avant. La PR cite les totaux. `py -m pytest jeu -q` reste vert.

**SC2 — la capture trace la parcelle par le geste et montre le refus, et elle peut échouer (PC).**
La capture `-forgeLot 375` se termine sans exception du scénario et écrit `<scène>--parcelle-tracee.png`. Le scénario lève une exception (la capture échoue) si l'une des exigences de la Photo tombe, notamment :
- les deux clics de la première parcelle ne passent pas par `Clic`, ou la parcelle n'est pas acceptée par le monde ;
- `Tracee` n'a pas la rue, le segment 5, le côté gauche, et un début de 1 m, une façade de 8 m et une profondeur de 15 m, à 0,05 m près ;
- après le tick, `Attendre()` est faux, ou la parcelle neuve n'est pas au plan et dessinée au cordeau ;
- la seconde parcelle n'est pas refusée par l'outil avec `façade dépasse le segment`, ou elle atteint le monde (`Recu` non nul, ou une parcelle de plus au plan après un tick).

La PR cite le texte du panneau sur la photo.

**SC3 — contre-épreuves (PC).** Faites à la main, dites dans la PR avec le message d'exception, chacune retirée ensuite :
- (a) `ValiderParcelle` ne dépose pas l'intention : la capture échoue (pas de reçu accepté) ;
- (b) dans `ValiderParcelle`, déposer `Tracee.IntentionJson.Replace("gauche","milieu")` : le panneau dit `Le monde refuse la parcelle : cote invalide : 'milieu'`, et la capture échoue. C'est la preuve qu'un refus du monde s'affiche avec sa raison ;
- (c) inverser les deux points passés à `Calculer` (le second d'abord) : la capture échoue sur la rue, le segment ou les mesures ;
- (d) `ValiderParcelle` dépose même quand `Tracee` est absente : la capture échoue sur la seconde parcelle.

**SC4 — le mode route ne change pas (PC).**
Depuis `3d/` :
- la capture `-forgeLot 293` se termine sans exception ;
- les captures `-forgeLot 362` et `-forgeLot 369` aussi ;
- `py local3d/atelier_desert.py routes` rend 0, et `routes --service-sourd` échoue toujours sur la faute du service sourd ;
- `py local3d/atelier_desert.py relance` rend 0.

La PR montre les sorties.

**SC5 — rien d'autre ne bouge.**
```
git diff --name-only origin/master...HEAD
git diff -U0 origin/master...HEAD -- 3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs | grep '^-[^-]'
```
La première commande ne nomme que les fichiers du Périmètre et ce brief. La seconde ne montre que des lignes retirées des membres listés aux Précisions : l'en-tête de commentaire, `Aide`, `Afficher`, `Update`, `Clic` et `Annuler`. Aucune ligne de `Valider`, `Intention`, `Attendre`, `Ouvrir`, `Rafraichir`, `DessinerParcelles`, `DessinerBatiments`, `Dessiner` ou `Bilan` n'est retirée. Hors du diff : tout `Pont/` (dont `TraceDeParcelle.cs` et ses tests), `DesertParcelles.cs`, `DesertBatiments.cs`, `DesertRoads.cs`, `DesertCityCamera.cs`, les autres captures (dont `Lot362.cs`), les scènes, `atelier_desert.py` et `jeu/`.

## Hors périmètre
- Le mode bâtiment, et trouver la parcelle sous un point (sous-lots 3 et 4 de #262).
- Choisir le nombre de foyers au chantier : l'intention n'en porte pas, le monde en met 1.
- Montrer à l'écran les coins posés, ou un aperçu de la parcelle avant Entrée.
- Refuser une parcelle qui en chevauche une autre : c'est de niveau 3 au modèle, et seul le propriétaire peut changer une règle du monde.
- Changer `TraceDeParcelle` (dont `SaisieMaxM`), `ClientIntention`, `ClientPlan`, le dessin des parcelles ou des bâtiments, la caméra, les autres captures, les asmdef, les scènes ou `jeu/`.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.

## Photo
Une rue de terre battue sur le sable. Le long de son bord gauche, une parcelle de 8 m × 15 m tracée par le geste du joueur : le cordeau sur ses quatre piquets, parce qu'elle est en chantier. Le panneau, en bas à gauche, dit `Parcelle refusée par l'outil : façade dépasse le segment : …`, puis `Parcelle le long d'une rue · 0/2 coin(s)`, puis l'aide du mode parcelle. Le plan fixe de la capture, pris avant, montre le sable vierge.

Le scénario `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot375.cs`, `[ScenarioDeCapture(375, "parcelle-tracee")]`, est au Périmètre. Il joue avec le service de la capture : port 8000, vitesse 0, 30 ticks poussés.
1. Il trouve `DesertRoadTool` et `DesertCityCamera` (exception sinon), et met l'outil en `automatique`.
2. Il dépose la première route `plaine` du jeu de gestes par `Lot362.Deposer(port, outil.Intention(plaine))`, puis `Lot362.Tick`. Il retrouve la rue par `Lot362.Identifiant` et note `n0`, le nombre de parcelles au plan. Il appelle `outil.Ouvrir()`, avec vrai exigé : la rue est posée sur le terrain.
3. **Échap.** `outil.EntrerParcelle()`, un clic, puis `outil.Annuler()`. Il exige `ModeParcelle` faux.
4. **La première parcelle, par le geste.** Il relit le plan et prend le segment 5 de la rue : `a`, `b`, `u = (b − a)/|b − a|`, et la normale gauche `n = (−u_y, u_x)`. Le premier coin est `p1 = a + 1·u + 3·n`, le second `p2 = a + 9·u + 17·n`. Il pose une RenderTexture de 1600 × 900 comme `Lot293`, et vise le milieu du segment de haut (`ville.Poser(milieu, ville.Cap, 85, 60)`). Puis `outil.EntrerParcelle()`, et `outil.Clic(camera.WorldToScreenPoint(Lot362.Monde(terrain, p.x, p.y)))` pour `p1` puis `p2` (vrai exigé). Il rend la caméra et appelle `outil.ValiderParcelle()`. Il exige :
   - `Tracee.Presente`, `Tracee.Rue` égal à la rue, `Segment == 5` et `Cote == "gauche"` ;
   - `DebutM`, `FacadeM` et `ProfondeurM` à moins de 0,05 m de 1, 8 et 15 ;
   - `outil.Recu.Acceptee`, une ligne du panneau qui commence par `Parcelle déposée au monde`, et `ModeParcelle` vrai.
5. **Le tick.** `Lot362.Tick`, puis `outil.Attendre()`, avec vrai exigé. Le plan relu compte `n0 + 1` parcelles, et la parcelle `n0` est en chantier. L'entrée `n0` de `outil.Parcelles` vaut `cordeau`. Une ligne du panneau commence par `Parcelles : `.
6. **La seconde parcelle, refusée.** Sur le segment 7 : `p1 = a + 5·u + 3·n` et `p2 = a + 12·u + 17·n`. Les deux clics se font comme en 4, la caméra visant de haut le milieu du segment 7, puis `ValiderParcelle()`. Il exige : `Tracee.Presente` faux et `Tracee.Absence` qui commence par `façade dépasse le segment`. `outil.Recu` est nul. La première ligne du panneau commence par `Parcelle refusée par l'outil : façade dépasse le segment`. Puis `Lot362.Tick` : le plan compte toujours `n0 + 1` parcelles.
7. Il écrit le panneau au journal (`Debug.Log("CAPTURE_375 " + …)`). Il vise le centre des quatre coins de la parcelle `n0`, convertis par `Lot362.Monde`, et pose la caméra par `ville.Poser(centre, ville.Cap, 50, 35)`. Puis il laisse passer 10 images.

Le codeur regarde l'image lui-même et le dit dans la PR. La parcelle doit y être entière, avec son cordeau visible, et le panneau lisible. S'il faut une autre distance (entre 25 et 60 m) ou une autre inclinaison pour la cadrer, il la change et le dit.

Une exception fait échouer la capture.
