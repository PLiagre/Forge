# Lot #908 — Le joueur trace son enceinte dans la 3D
Jalon : J4 · Machine : pc · Taille prévue : 245 lignes

## But
Dans sa capitale en 3D, le joueur trace le contour de son enceinte au clic sur le terrain. Entrée le dépose au monde comme `tracer_enceinte`, et le mur se dessine en chantier au tick suivant, ou bien le refus du monde s'affiche avec sa raison.

## Le joueur
Découpé de #417. C'est le geste du J4 « trace son enceinte », jusqu'ici réservé aux scénarios. À Biskra, le joueur appuie sur E et clique les coins de son mur autour de la ville : un trait rouge suit son tracé et se referme. Entrée confie ce tracé au monde ; Échap l'efface sans rien déposer. Au tick suivant, il voit son mur aux piquets : quatre tours, 63 pans et la porte sur sa route de l'ouest (#907). S'il trace un contour qui se croise, le monde refuse, et le panneau dit pourquoi. Il fait lui-même l'arbitrage « des murs, ou des maisons » : 19 200 journées pour le carré de ±80 m.

## Règle du monde
Sans objet : lot de vue et d'outil, `jeu/` n'est pas touché. Le geste suit la règle de `jeu/sim/MODELE.md`, « Les intentions du joueur » (`tracer_enceinte` et ses refus, fidélité 2) et « Le plan du bourg » (l'enceinte n'entre au plan qu'au tick suivant, en chantier). Le service remplace la `maison` par celle du joueur : l'outil ne l'envoie pas, comme pour `tracer_route`. Il n'envoie pas non plus `foyers`, qui vaut alors 1. Le monde reste le seul juge. L'outil ne refuse qu'un tracé de moins de trois coins, qui ne part jamais au monde.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot908.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot908.cs.meta
docs/briefs/908-le-joueur-trace-son-enceinte-dans-la-3d.md

Le `.meta` fait deux lignes (`fileFormatVersion: 2`, `guid` neuf).

**`DesertRoadTool`**, sur le modèle des modes parcelle (#375) et bâtiment (#377). Ajouter une ligne « Lot 908 » au commentaire de classe.
- `public bool ModeEnceinte{get;private set;}`.
- `public LineRenderer TraceEnceinte` : c'est le tracé en cours. Il vit dans l'enfant `Tracé de l'enceinte` de l'outil et se crée dans `Awake`. Son matériau est le matériau par défaut du pipeline, de couleur rouge profond, comme `DesertParcelles`. `widthMultiplier` vaut 1,5. Sans ce matériau, `TraceEnceinte` est nul, et en mode enceinte le panneau ajoute la ligne `Pas de matériau par défaut du pipeline : le tracé de l'enceinte ne se voit pas.`
- `public void EntrerEnceinte()` efface les coins, `Recu` et les autres modes, met `ModeEnceinte` à vrai et affiche `AideEnceinte` = `Clic : poser un coin du mur · Entrée : déposer l'enceinte · Échap : annuler`. `Aide` reçoit ` · E : enceinte` à la fin. `EntrerParcelle`, `EntrerBatiment`, `Annuler` et `PreparerOuverture` (quand la cellule change) remettent `ModeEnceinte` à faux.
- `Clic`, en mode enceinte, ajoute le point sans limite de nombre, puis affiche `AideEnceinte`.
- En mode enceinte, `Afficher` écrit `(texte==AideEnceinte?"":texte+"\n")+"Enceinte · "+points.Count+" coin(s)\n"+AideEnceinte`, puis le relief et `Gestes` comme aujourd'hui. `Afficher` tient aussi le tracé à jour. En mode enceinte avec au moins un coin, le tracé est activé avec `loop` vrai. Il suit le contour des coins, fermeture comprise, avec un sommet tous les 2 m. Le premier sommet d'un côté est son coin, et chaque sommet est à 1 m au-dessus du sol (repère `(-x, sol, -y)`, comme `Lot904`). Dans tout autre cas, le tracé est désactivé avec `positionCount` à 0.
- `public RecuIntention ValiderEnceinte()` rend nul hors du mode enceinte. Avec moins de trois coins, elle affiche `Il faut au moins trois coins.` et rend nul. Sinon :
  - `Derniers` reçoit les coins, puis les coins s'effacent (le tracé disparaît) ;
  - si la cellule est en erreur, son message s'affiche et la méthode rend nul ;
  - sinon `Recu = depot.Deposer(IntentionEnceinte(Derniers))`. Acceptée : `enAttente` reçoit le reçu, et le panneau dit `Enceinte déposée au monde : elle se dessine au tick suivant (après le tick N).` Refusée : `Le monde refuse l'enceinte : ` suivi de `Recu.Erreur`, ou `Pas de reçu : ` suivi de l'absence.
  
  Elle rend `Recu`, et l'outil reste en mode enceinte. Rien n'est dessiné ici : `Attendre` dessine l'enceinte par `DessinerBatiments`, qui ne change pas.
- `public string IntentionEnceinte(IReadOnlyList<(double x,double y)> coins)` rend `{"type":"tracer_enceinte","cell":C,"points":[[x,y],…]}`, nombres au format `R` en culture invariante, comme `Intention`.
- Dans `Update`, la touche E (`eKey`) appelle `EntrerEnceinte`. Entrée appelle `ValiderParcelle` en mode parcelle, `ValiderEnceinte` en mode enceinte, et `Valider` hors du mode bâtiment.

Budget du `numstat` : outil 40, `Lot908` 105, `.meta` 2, ce brief.

## Conditions de succès
**SC1 — La photo peut échouer.** La commande sans drapeau `-forge908…` (Photo) sort en 0, écrit deux images et `lot908-rapport.json`. Chaque exigence du scénario qui tombe fait échouer la capture. Les deux contre-épreuves sortent en 0 avec leurs propres exigences :
- `-forge908Croise` : les coins sont cliqués dans l'ordre `[[-80,-80],[80,80],[80,-80],[-80,80]]`. Le reçu est refusé avec l'erreur `enceinte : contour qui se croise`. La première ligne du panneau est `Le monde refuse l'enceinte : enceinte : contour qui se croise`. `Attendre()` est faux avant et après le tick. Au plan, ni enceinte ni porte. 0 pièce posée, et aucune ligne du panneau ne commence par `Enceinte :`.
- `-forge908Echap` : les mêmes quatre coins que la photo, puis `Annuler()` au lieu de `ValiderEnceinte()`. Le mode enceinte est faux, le tracé désactivé avec 0 sommet, `Recu` nul. `Attendre()` est faux, et après le tick il n'y a au plan ni enceinte ni porte, et 0 pièce posée.

Faites à la main, chacune doit faire échouer la capture, et dites dans la PR : (a) Entrée qui dessine le mur sans le déposer ; (b) un tracé jamais activé ; (c) le tracé laissé ouvert (`loop` faux) ; (d) un refus du monde affiché sans sa raison, sous `-forge908Croise` ; (e) Échap qui garde les coins, sous `-forge908Echap`.

**SC2 — Rien d'autre ne bouge.** Les trois captures ci-dessous sortent en 0, sans changement de leur scénario. `git diff --name-only origin/master` ne nomme que le Périmètre. `git diff --numstat origin/master` fait moins de 300 lignes, ce brief compris. `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/ jeu/` est vide. `python3 -m pytest jeu -q` reste vert.

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 369 -forgeCaptures 3d/unity/Temp/lot908-regres-369 -logFile 3d/unity/Temp/lot908-regres-369.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 737 -forgeCaptures 3d/unity/Temp/lot908-regres-737 -logFile 3d/unity/Temp/lot908-regres-737.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 907 -forgeCaptures 3d/unity/Temp/lot908-regres-907 -logFile 3d/unity/Temp/lot908-regres-907.log
```

## Hors périmètre
- Choisir le nombre de foyers du chantier (1 par défaut).
- Juger le contour dans Unity : croisement, place, maisons de 1400, terres. Le monde juge.
- Annuler le dernier coin seul, ou déplacer un coin.
- Le prix au panneau (#419), et la langue du socle pour le tracé et le panneau (#851).
- Un tracé d'enceinte pour l'IA (jalon 5).
- `sim/`, `Pont/`, `DesertEnceinte.cs`, le kit, les prefabs et les scènes.

## Photo
Deux images de Biskra. D'abord, le tracé en cours : un trait rouge fermé sur le carré de ±80 m autour des 33 maisons de 1400, vu d'en haut, avec au panneau `Enceinte · 4 coin(s)`. Ensuite, après Entrée et un tick, le mur aux piquets, vu de l'ouest : quatre tours, les pans au cordeau et la porte sur la route, avec au panneau `Enceinte : piquets · 4 tour(s), 63 pan(s), 1 porte(s).`

`Lot908.cs` porte deux scénarios qui échouent en nommant leur cause. Le second lit l'état laissé par le premier dans des champs statiques et refuse de jouer seul. Outil, caméra et marcheur passent en `automatique`.

**`[ScenarioDeCapture(908, "1-trace-en-cours")]`**
- Refuser un `lot908-rapport.json` déjà présent.
- Comme `Lot907` : Biskra par `ClientDeparts`, `choisir_depart`, un tick, la route `[[-66,2.2],[-120,2.2]]` de 4 m déposée par `Lot362.Deposer`, puis un tick.
- `Ouvrir(cellule)` vrai et `lieu.Ouvrir(cellule)`. On exige 33 maisons, 7 rues de 1400, et `Enceinte.Posees == 0`.
- `EntrerEnceinte()`. Pour chaque coin de `[[-80,-80],[80,-80],[80,80],[-80,80]]` (ordre croisé sous `-forge908Croise`) : sur une `RenderTexture` 1600 × 900, comme `Lot293`, `ville.Poser(Monde(coin), ville.Cap, 85, 60)`, puis `Clic(camera.WorldToScreenPoint(Lot362.Monde(t, x, y)))` doit rendre vrai.
- Le panneau porte la ligne `Enceinte · 4 coin(s)`. `TraceEnceinte` est activé avec `loop` vrai. Chaque coin a un sommet à moins de 0,05 m à l'horizontale, et chaque sommet est à 1 m du sol, à 0,01 m près.
- Le plan lu n'a toujours pas d'enceinte : sans Entrée, rien ne bouge.
- Caméra comme `Lot904` : surplomb à 65°, recul `×1,06` depuis 60 m jusqu'à `DistanceMax`, les quatre coins entre 0,02 et 0,98 de l'image (`aspect` 1600/900). Puis dix images.

**`[ScenarioDeCapture(908, "2-enceinte-en-chantier")]`**
- Sous `-forge908Echap`, `Annuler()`. Sinon, `ValiderEnceinte()`.
- `Derniers` vaut exactement les quatre coins cliqués, puisque `PointExact` arrondit au centimètre.
- Dépôt accepté : on exige le message de dépôt, un tracé désactivé, et `Attendre()` faux avant le tick.
- `Lot362.Tick`. Ensuite `Attendre()` est vrai, et le plan porte une enceinte en chantier dont le contour vaut les coins dans leur ordre, avec `travail_requis` 19200, l'étape `Piquets` (`PansDeLEnceinte.Etape`) et la porte (−80 ; 2,2).
- On exige `Enceinte.Posees == 68 == Racine.childCount`, `Enceinte porte 3-0` au lacet 90, et la ligne de panneau ci-dessus. Les contre-épreuves gardent les exigences de SC1.
- Caméra comme `Lot907` : de l'ouest à 35°, cap = lacet de la porte + 180 (90 sans porte), visée `Lot362.Monde(t, -80, 0)`, recul depuis 40 m jusqu'à ce que les tours (−80 ; ±80) et le point (−80 ; 2,2) tiennent entre 0,02 et 0,98, caméra à x Unity > 80. Puis dix images.
- Le rapport donne : la cellule, le tick, la variante (`depot`, `croise` ou `echap`), les coins, le reçu (acceptée, tick, erreur), l'enceinte au plan (contour, `en_chantier`, travail fourni et requis, ou `null`), les portes, `posees`, l'empreinte et le panneau. Ensuite `Debug.Log("CAPTURE_908 …")`.

Le codeur regarde les six images et dit ce qu'il voit : le trait fermé autour de la ville ; le mur aux piquets là où passait le trait ; le trait en sablier et la ville sans mur sous `-forge908Croise` ; la ville sans mur sous `-forge908Echap`.

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 908 -forgeCaptures 3d/unity/Temp/lot908-photo -logFile 3d/unity/Temp/lot908-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 908 -forgeCaptures 3d/unity/Temp/lot908-croise -forge908Croise -logFile 3d/unity/Temp/lot908-croise.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 908 -forgeCaptures 3d/unity/Temp/lot908-echap -forge908Echap -logFile 3d/unity/Temp/lot908-echap.log
```
