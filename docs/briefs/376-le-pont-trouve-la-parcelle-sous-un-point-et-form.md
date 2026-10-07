# Lot #376 — Le pont trouve la parcelle sous un point et forme la pose d'un bâtiment
Jalon : J4 · Machine : pc · Taille prévue : 240 lignes

## But
À partir du plan lu au service, d'un point posé au sol et d'une nature (maison, scierie ou four), le pont sait sur quelle parcelle le joueur veut bâtir. Il forme l'intention `poser_batiment` que le monde acceptera, ou dit pourquoi il ne la forme pas. Le geste « pose un atelier » de CAP.md (jalon 4) aura ainsi son calcul, sans Unity. Le sous-lot 4 de #262 n'aura plus qu'à le brancher sur la souris. C'est le sous-lot 3 de #262.

## Règle du monde
Sans objet : c'est un lot d'outil, côté vue. Le monde reste le seul juge : il revalide l'intention au dépôt et ne change pas. `jeu/` n'est pas touché. Niveau de fidélité : sans objet.

Ce que le calcul reprend de `jeu/sim/MODELE.md`, sans rien y changer :

- **« Les intentions du joueur ».** Un bâtiment se dépose avec `{"type": "poser_batiment", "cell": X, "parcelle": 0, "nature": "maison"}`. `foyers` est facultatif et vaut 1 par défaut. Le monde refuse, dans l'ordre : une cellule inconnue, une parcelle absente du plan (une parcelle en chantier convient), « parcelle déjà bâtie », « parcelle déjà promise », puis une `nature` autre que `maison`, `scierie` ou `four`, « sans tolérer casse ou espace » (`NATURES_BATIMENT` de `sim/intentions.py`, l. 16). Au tick suivant, le contour de la parcelle devient l'emprise du bâtiment.
- **« Le plan du bourg ».** Les parcelles sont triées par `identifiant`. Un contour a au moins 3 points (`POINTS_MIN_CONTOUR`). Le repère est local au bourg : x vers l'est, y vers le nord, en mètres. Le modèle n'interdit pas que deux parcelles se chevauchent (niveau 3).

**La convention du geste** (propre à la vue, rien ne retourne au monde) : le joueur choisit une nature, puis désigne un point du sol. Le bâtiment va sur la parcelle qui contient ce point. Si plusieurs parcelles le contiennent, c'est la première de la liste du plan, donc la plus petite par identifiant.

Ce qui existe sur master (1ba78f4), vérifié le 07/10/2026 :

- `Pont/ClientPlan.cs` (#292, #360) : `PointLocal(double x, double y)`, `ParcelleDuPlan(long identifiant, IList<PointLocal> contour, bool enChantier, long travailRequis, long travailFourni)`, `BatimentDuPlan(…)` et `PlanLu(long cellId, long tick, IList<RueDuPlan> rues, IList<ParcelleDuPlan> parcelles, IList<BatimentDuPlan> batiments)`. Le constructeur de `ParcelleDuPlan` ne vérifie pas le nombre de points du contour.
- `Pont/TraceDeParcelle.cs` (#374) : le modèle à suivre. Un résultat immuable, `Presente` / `Absence`, l'intention en JSON compact sans `foyers`, et aucun `UnityEngine`.
- Aucun type `PoseDeBatiment` ni `BatimentPose` dans le projet. Aucun code C# ne forme `poser_batiment` hors des captures (`Lot369`, `Lot263`) et de l'outil d'éditeur `DesertCityBatiments`, qui l'écrivent en JSON brut.
- Rejoué le 07/10 sur master : route `[[0,0],[40,0],[40,25]]` de 4 m sur la cellule 10003 au tick 0, les trois découpes du modèle au tick 1, puis les trois intentions des cas 1, 2 et 3 ci-dessous (cellule 10003) au tick 2. `python3 -m sim --gestes … --ticks 4 --monde-json …` rend 0. Le plan final porte les bâtiments 0 (maison), 1 (scierie) et 2 (four), en chantier, sur les parcelles 0, 1 et 2. La cellule 7 n'est pas sur la carte (« cell inconnu : 7 »).

Le lot ne s'appuie sur rien que J2 ou J3 doivent encore livrer : `/plan`, `poser_batiment` et `ClientPlan` sont sur master.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/PoseDeBatiment.cs
3d/unity/Assets/ForgeLocal3D/Pont/PoseDeBatiment.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PoseDeBatimentTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PoseDeBatimentTests.cs.meta

Précisions :

- **`PoseDeBatiment.cs`** (neuf, namespace `Forge.Pont`). Il ne contient **ni `UnityEngine` ni `UnityEditor`** : seulement `System`, `System.Collections.Generic`, `System.Globalization` et les types de `ClientPlan.cs`. Il déclare :
  - `public sealed class BatimentPose`, immuable :
    - `bool Presente` et `string Absence` (vide si présente, jamais nulle) ;
    - `long Parcelle` : l'identifiant de la parcelle, `-1` quand l'absence est déclarée ;
    - `string Nature` : la nature demandée, vide quand l'absence est déclarée ;
    - `string IntentionJson` : l'intention à déposer, `null` quand l'absence est déclarée.
  - `public static class PoseDeBatiment` :
    - `public static readonly IReadOnlyList<string> Natures` : exactement `maison`, `scierie`, `four`, dans cet ordre. Un commentaire dit que c'est la liste fermée du geste `poser_batiment` du monde (`NATURES_BATIMENT`).
    - **`public static bool Contient(IReadOnlyList<PointLocal> contour, PointLocal point)`** : la règle pair-impair. `contour` nul lève `ArgumentNullException`. Un contour de moins de 3 points, ou un point non fini, rend faux. Sinon, avec `j` le sommet qui précède `i` (le dernier pour `i = 0`, donc le contour est fermé), le point est dedans si le nombre d'arêtes pour lesquelles
      `(yi > py) != (yj > py)` et `px < (xj − xi) × (py − yi) / (yj − yi) + xi`
      est impair. C'est cette formule, telle quelle : un point sur le bord suit ce qu'elle rend, et aucun test ne le fige.
    - **`public static ParcelleDuPlan ParcelleSous(PlanLu plan, PointLocal point)`** : `plan` nul lève `ArgumentNullException`. Elle rend la première parcelle de `plan.Parcelles`, dans l'ordre de la liste, dont le contour contient le point. Sinon `null`. Elle ne lit ni les rues ni les bâtiments.
    - **`public static BatimentPose Calculer(PlanLu plan, PointLocal point, string nature)`**. `plan` nul lève `ArgumentNullException`. Ensuite, dans cet ordre :
      1. `nature` nulle, ou absente de `Natures` en comparaison **ordinale** (ni casse ni espace tolérés, comme le monde) : absence `nature inconnue : "<nature>"`, ou `nature inconnue : null` si elle est nulle.
      2. Une coordonnée non finie (NaN ou infinie) : absence `point non fini`.
      3. `plan.Parcelles` vide : absence `aucune parcelle au plan`.
      4. `ParcelleSous` rend `null` : absence `aucune parcelle sous le point : (<x>, <y>)`.
      5. Sinon, la pose est présente. `IntentionJson` vaut exactement, sans espace et dans cet ordre :
         `{"type":"poser_batiment","cell":<plan.CellId>,"parcelle":<Parcelle>,"nature":"<Nature>"}`.
         Les entiers s'écrivent en `CultureInfo.InvariantCulture`, les coordonnées du message en `ToString("R", CultureInfo.InvariantCulture)`. **Aucun champ `foyers`** : le monde en met 1, comme pour la route et la parcelle.

      Le calcul **ne lit pas les bâtiments** du plan : une parcelle déjà bâtie est rendue présente, et c'est le reçu du monde qui dit « parcelle déjà bâtie ». Une parcelle en chantier convient, comme au monde.
- **Les `.meta`** sont ceux qu'Unity génère.
- **`PoseDeBatimentTests.cs`** (neuf, namespace `Forge.Pont.Tests`, NUnit). C'est un fichier neuf : aucun fichier de test existant ne change. Une aide construit des `PlanLu` de cellule 7, tick 0, avec la rue `R0 = RueDuPlan(0, [(0,0), (40,0), (40,25)], 4, false)`. Le plan **B** porte, dans cet ordre :
  - `P0` : identifiant 0, `[(5,2), (15,2), (15,22), (5,22)]`, en chantier ;
  - `P1` : identifiant 1, `[(5,−2), (15,−2), (15,−22), (5,−22)]` ;
  - `P2` : identifiant 2, `[(38,0), (38,25), (28,25), (28,0)]` ;
  - `P4` : identifiant 4, un U : `[(50,0), (70,0), (70,20), (65,20), (65,5), (55,5), (55,20), (50,20)]` ;
  - `P6` : identifiant 6, un losange : `[(30,40), (40,50), (30,60), (20,50)]` ;
  - et un bâtiment : `BatimentDuPlan(0, 1, "maison", contour de P1, false, 0, 0)`.

  `P0`, `P1` et `P2` sont les trois contours d'exemple de MODELE. Les cas :

| # | plan | point | nature | attendu |
|---|---|---|---|---|
| 1 | B | (10, 12) | maison | parcelle 0 |
| 2 | B | (10, −12) | scierie | parcelle 1 (bâtie : le pont ne lit pas les bâtiments) |
| 3 | B | (33, 12) | four | parcelle 2 |
| 4 | B | (52, 10) | maison | parcelle 4 (bras gauche du U) |
| 5 | B | (68, 15) | maison | parcelle 4 (bras droit) |
| 6 | B | (60, 2) | maison | parcelle 4 (base du U) |
| 7 | B | (60, 10) | maison | `aucune parcelle sous le point` (creux du U) |
| 8 | B | (30, 50) | maison | parcelle 6 (centre du losange) |
| 9 | B | (22, 42) | maison | `aucune parcelle sous le point` (dans le cadre du losange, hors de lui) |
| 10 | B | (0, 30) | maison | `aucune parcelle sous le point : (0, 30)` (message exact) |
| 11 | `[P5, P0]`, P5 = id 5 `[(10,10), (20,10), (20,20), (10,20)]` | (12, 12) | maison | parcelle 5 |
| 12 | `[P0, P5]` | (12, 12) | maison | parcelle 0 |
| 13 | R0 seule, sans parcelle | (10, 12) | maison | `aucune parcelle au plan` |
| 14 | id 3, contour `[(0,0), (40,0)]` seul | (10, 0) | maison | `aucune parcelle sous le point` |
| 15 | B | (10, 12) | Maison | `nature inconnue : "Maison"` |
| 16 | B | (10, 12) | ` four` | `nature inconnue : " four"` |
| 17 | B | (10, 12) | (vide) | `nature inconnue : ""` |
| 18 | B | (10, 12) | atelier | `nature inconnue : "atelier"` |
| 19 | B | (10, 12) | null | `nature inconnue : null` |
| 20 | B | (0, 30) | Maison | `nature inconnue : "Maison"` (la nature d'abord) |
| 21 | B | (NaN, 12) | maison | `point non fini` |
| 22 | B | (10, −∞) | maison | `point non fini` |

  Pour chaque cas présent, le test vérifie aussi `Absence == ""` et `Nature` égale à la nature demandée. Pour les cas 1, 2 et 3, il compare `IntentionJson` au texte exact :
  - 1 : `{"type":"poser_batiment","cell":7,"parcelle":0,"nature":"maison"}` ;
  - 2 : `{"type":"poser_batiment","cell":7,"parcelle":1,"nature":"scierie"}` ;
  - 3 : `{"type":"poser_batiment","cell":7,"parcelle":2,"nature":"four"}`.

  Le JSON ne contient pas `foyers` (`StringAssert.DoesNotContain`). Pour chaque cas absent, le test vérifie : `Presente` faux, l'`Absence` exacte (cas 10, 15 à 20) ou qui commence par le message attendu, `Parcelle == -1`, `Nature == ""` et `IntentionJson` nul.

  S'y ajoutent :
  - `ParcelleSous(B, (10, 12))` rend la même instance que `B.Parcelles[0]` ; `ParcelleSous(B, (60, 10))` et `ParcelleSous(B, (NaN, 12))` rendent `null` ;
  - `Contient` d'un contour nul lève `ArgumentNullException` ;
  - `Calculer(null, …)` et `ParcelleSous(null, …)` lèvent `ArgumentNullException` ;
  - `Natures` vaut exactement `["maison", "scierie", "four"]`.

  Les cas s'écrivent en `[TestCase]` autant que possible, pour tenir la taille.

## Conditions de succès

**SC1 — Unity compile et joue les tests (PC).**
Le workflow `unity` (poussée sur la branche) est vert : aucune `error CS`. Puis, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
(sans `-quit`). Le code de sortie vaut 0 et le XML dit `failed="0"`. Les cas de `ClientPlanTests`, `LecteurJsonTests`, `ClientLieuTests`, `PanneauLieuTests`, `ClientIntentionTests`, `KitDesBatimentsTests` et `TraceDeParcelleTests` y sont, en même nombre et sous les mêmes noms qu'avant. `PoseDeBatimentTests` compte **au moins 27 cas**. Moins, c'est un échec. La PR cite les totaux du XML.

**SC2 — la parcelle sous le point (PC, dans SC1).**
Les cas 1 à 14 et ceux de `ParcelleSous` passent, avec les trois intentions exactes. Contre-épreuves faites à la main, dites dans la PR, chacune retirée ensuite :
- (a) remplacer la règle pair-impair par « le point est dans le rectangle qui encadre le contour » : les cas 7 et 9 rougissent ;
- (b) garder la dernière parcelle qui contient le point au lieu de la première : le cas 12 rougit ;
- (c) refuser une parcelle qui porte déjà un bâtiment : le cas 2 rougit ;
- (d) ne pas fermer le contour (ignorer l'arête du dernier sommet au premier) : le cas 9 rougit. Le point (22, 42) ne croise plus que l'arête (30,40)–(40,50) au lieu de deux.

**SC3 — les refus (PC, dans SC1).**
Les cas 15 à 22 et les cas `null` passent. Contre-épreuves faites à la main, dites dans la PR :
- (a) comparer la nature sans tenir compte de la casse : le cas 15 rougit ;
- (b) retirer les espaces de la nature avant de la comparer : le cas 16 rougit ;
- (c) chercher la parcelle avant de contrôler la nature : le cas 20 rougit.

Et par lecture :
```
grep -cE "UnityEngine|UnityEditor" 3d/unity/Assets/ForgeLocal3D/Pont/PoseDeBatiment.cs
grep -c "foyers" 3d/unity/Assets/ForgeLocal3D/Pont/PoseDeBatiment.cs
```
Les deux rendent `0`.

**SC4 — le monde accepte l'intention formée (VPS ou PC).**
```
cd jeu && python3 -m pytest sim/tests/test_intentions.py -q
```
reste vert, sans changement. Puis, à la main, dit dans la PR : un fichier de gestes trace la route `[[0,0],[40,0],[40,25]]` de 4 m sur la cellule 10003 au tick 0, découpe les trois parcelles du modèle au tick 1 (les `IntentionJson` des cas 1, 3 et 4 de `TraceDeParcelleTests`, cellule 10003), puis dépose au tick 2 les `IntentionJson` des cas 1, 2 et 3, avec `"cell":10003` au lieu de 7. `python3 -m sim --gestes <fichier> --ticks 4 --monde-json <sortie>` rend 0. Le plan final de la cellule 10003 porte trois bâtiments en chantier : maison sur la parcelle 0, scierie sur la 1, four sur la 2, chacun avec l'emprise de sa parcelle. Le fichier de gestes n'est pas commité.

**SC5 — rien d'autre ne bouge.**
```
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC (pc\Tests.cmd)
git diff --name-only origin/master...HEAD
```
La suite du jeu reste verte. Le diff ne nomme que les fichiers du Périmètre et ce brief. `ClientPlan.cs`, `ClientIntention.cs`, `TraceDeParcelle.cs`, les asmdef, `DesertRoadTool.cs`, les captures, les scènes et `jeu/` sont hors du diff.

## Hors périmètre
- Le mode bâtiment de `DesertRoadTool` : touche, choix de la nature, clic au sol, dépôt par `ClientIntention`, panneau et capture. C'est le sous-lot 4 de #262.
- Refuser dans l'outil une parcelle déjà bâtie ou déjà promise : le monde le dit dans son reçu.
- Choisir le nombre de foyers au chantier : l'intention n'en porte pas, le monde en met 1.
- Montrer à l'écran la parcelle survolée.
- Changer une règle du monde, `jeu/` (dont `MODELE.md` et `intentions.py`), `ClientPlan.cs`, `ClientIntention.cs`, `TraceDeParcelle.cs`, les asmdef, ou les autres fichiers de tests.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.

## Photo
Sans objet : le lot ne change rien de ce qu'on voit à l'écran. `PoseDeBatiment` n'est appelé par aucune scène, aucun outil d'éditeur ni aucun panneau avant le sous-lot 4 de #262. C'est lui qui branche le calcul sur la souris et porte le scénario de capture.
