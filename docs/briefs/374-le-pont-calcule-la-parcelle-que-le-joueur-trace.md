# Lot #374 — Le pont calcule la parcelle que le joueur trace le long d'une rue
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
À partir du plan lu au service et de deux points posés au sol, le pont sait quelle parcelle le joueur trace le long d'une rue. Il forme l'intention `decouper_parcelle` que le monde acceptera, ou dit pourquoi il la refuse. Le geste « découpe des parcelles » de CAP.md (jalon 4) aura ainsi son calcul, sans Unity. Le sous-lot suivant de #262 n'aura plus qu'à le brancher sur la souris.

## Règle du monde
Sans objet : c'est un lot d'outil, côté vue. Le monde reste le seul juge : il revalide l'intention au dépôt et ne change pas. `jeu/` n'est pas touché. Niveau de fidélité : sans objet.

Ce que le calcul reprend de `jeu/sim/MODELE.md`, sans rien y changer :

- **« Les intentions du joueur ».** Une parcelle se dépose avec `{"type": "decouper_parcelle", "cell": X, "rue": R, "segment": S, "debut_m": D, "facade_m": F, "profondeur_m": P, "cote": "gauche"|"droite"}`. `foyers` est facultatif et vaut 1 par défaut, comme pour la route. Le monde refuse, entre autres : une rue absente du plan (une rue en chantier convient), un segment hors de la rue, `debut_m < 0`, `facade_m ≤ 0`, `profondeur_m ≤ 0`, et `debut_m + facade_m > longueur du segment` (« façade dépasse le segment », sans tolérance, longueur `math.dist(a, b)`).
- **La géométrie de la découpe.** Pour le segment de `a` à `b` : `L = dist(a, b)` et `u = (b − a) / L`. La normale gauche vaut `n = (−u_y, u_x)`, en regardant dans le sens du tracé. À droite, on prend `−n`. `d = largeur_m × 0,5`. La façade borde la chaussée, à `d` de l'axe, et le lot s'étend vers l'extérieur sur `profondeur_m`. Exemples du modèle, sur la rue `[[0, 0], [40, 0], [40, 25]]` de largeur 4 m :
  - segment 0, début 5, façade 10, profondeur 20 : gauche `[(5, 2), (15, 2), (15, 22), (5, 22)]`, droite `[(5, −2), (15, −2), (15, −22), (5, −22)]` ;
  - segment 1, gauche, début 0, façade 25, profondeur 10 : `[(38, 0), (38, 25), (28, 25), (28, 0)]`.
- **« Le plan du bourg ».** Le repère est local au bourg : x vers l'est, y vers le nord, en mètres. Une rue a au moins 2 points et une largeur > 0.

**La convention du geste** (propre à la vue, rien ne retourne au monde) : le joueur pose deux coins opposés de sa parcelle. Le **premier** se pose près de la rue : c'est lui qui choisit la rue et le segment. Le **second** dit jusqu'où va la façade le long de la rue, de quel côté s'étend le lot et à quelle profondeur. L'ordre des deux points le long de la rue n'a pas d'importance.

Ce qui existe sur master (bd1923b), vérifié le 07/10/2026 :

- `Pont/ClientPlan.cs` (#292, #360) : `PointLocal(double x, double y)`, `RueDuPlan(long identifiant, IList<PointLocal> points, double largeurM, bool enChantier)` et `PlanLu(long cellId, long tick, IList<RueDuPlan> rues, IList<ParcelleDuPlan> parcelles, IList<BatimentDuPlan> batiments)`.
- `Desert/DesertRoadTool.cs` (l. 158-160) forme l'intention `tracer_route` sans champ `foyers` : le monde en met 1.
- `jeu/sim/intentions.py` (l. 129-131) : `longueur = math.dist(a, b)`, puis le refus « façade dépasse le segment ».
- Aucun type `TraceDeParcelle` ni `ParcelleTracee` dans le projet. Aucun code C# ne forme `decouper_parcelle` hors des captures et des contrôles d'éditeur, qui l'écrivent en JSON brut.

Le lot ne s'appuie sur rien que J2 ou J3 doivent encore livrer : `/plan`, `decouper_parcelle` et `ClientPlan` sont sur master.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/TraceDeParcelle.cs
3d/unity/Assets/ForgeLocal3D/Pont/TraceDeParcelle.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TraceDeParcelleTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TraceDeParcelleTests.cs.meta

Précisions :

- **`TraceDeParcelle.cs`** (neuf, namespace `Forge.Pont`). Il ne contient **ni `UnityEngine` ni `UnityEditor`** : seulement `System`, `System.Globalization` et les types de `ClientPlan.cs`. Il déclare :
  - `public sealed class ParcelleTracee`, immuable :
    - `bool Presente` et `string Absence` (vide si présente, jamais nulle) ;
    - `long Rue` et `int Segment` : l'identifiant de la rue et le rang du segment, `-1` quand l'absence est déclarée ;
    - `double DebutM`, `FacadeM`, `ProfondeurM` : `double.NaN` quand l'absence est déclarée ;
    - `string Cote` : `"gauche"` ou `"droite"`, vide quand l'absence est déclarée ;
    - `string IntentionJson` : l'intention à déposer, `null` quand l'absence est déclarée.
  - `public static class TraceDeParcelle` :
    - `public const double SaisieMaxM = 10;` : la distance au-delà de laquelle le premier point est « trop loin d'une rue ». Un commentaire dit que c'est une convention de la vue.
    - **`ParcelleTracee Calculer(PlanLu plan, PointLocal premier, PointLocal second)`**. `plan` nul lève `ArgumentNullException`. Ensuite, dans cet ordre :
      1. Une coordonnée non finie (NaN ou infinie) dans l'un des deux points : absence `point non fini`.
      2. **La rue et le segment.** Pour chaque rue de `plan.Rues`, dans l'ordre de la liste, et chaque segment `i` de 0 à `Points.Count − 2` : on prend la distance du premier point au segment `[a, b]`, c'est-à-dire au point du segment le plus proche (projection bornée à `[a, b]`). Un segment de longueur nulle est ignoré : il ne porte aucune façade. Les rues en chantier comptent. On garde la plus petite distance **strictement**. À égalité, c'est donc la première rue de la liste qui gagne, puis le plus petit segment. Si aucun segment n'a de longueur non nulle (plan sans rue, ou seulement des segments nuls) : absence `aucune rue au plan`.
      3. Si cette distance est **> `SaisieMaxM`** : absence `point trop loin d'une rue : <distance> m > 10 m`. Une distance de 10 m pile est acceptée.
      4. Sur le segment retenu : `L = √(dx² + dy²)`, `u = (b − a) / L`, `n = (−u_y, u_x)`. Puis `t1 = (premier − a) · u` et `t2 = (second − a) · u`. `DebutM = min(t1, t2)` et `FacadeM = max(t1, t2) − min(t1, t2)`. Si `DebutM < 0` ou `DebutM + FacadeM > L` (ce même calcul, sans tolérance, comme le monde) : absence `façade dépasse le segment : <DebutM> + <FacadeM> > <L>`.
      5. Si `FacadeM == 0` : absence `façade nulle`.
      6. `h = (second − a) · n`. `Cote` vaut `"gauche"` si `h > 0` et `"droite"` sinon. `ProfondeurM = |h| − rue.LargeurM × 0,5`. Si `ProfondeurM ≤ 0` : absence `second point dans la chaussée : <|h|> m ≤ <demi-largeur> m`.
      7. Sinon, la parcelle est présente. `IntentionJson` vaut exactement, sans espace et dans cet ordre :
         `{"type":"decouper_parcelle","cell":<plan.CellId>,"rue":<Rue>,"segment":<Segment>,"debut_m":<DebutM>,"facade_m":<FacadeM>,"profondeur_m":<ProfondeurM>,"cote":"<Cote>"}`.
         Les nombres s'écrivent avec `ToString("R", CultureInfo.InvariantCulture)` : `5.0` donne `5`. **Aucun champ `foyers`** : le monde en met 1, comme pour la route de `DesertRoadTool`.

      Les nombres des messages s'écrivent aussi en `"R"` invariant. Aucun arrondi n'est fait : le monde reçoit les mesures telles que calculées. Le calcul ne lit ni les parcelles ni les bâtiments du plan : les chevauchements sont au niveau 3 du modèle. Si `Math.Sqrt` et `math.dist` diffèrent d'un dernier chiffre, sur une façade qui touche exactement le bout du segment, le reçu du monde rend son propre refus. Le pont ne le devine pas.
- **Les `.meta`** sont ceux qu'Unity génère.
- **`TraceDeParcelleTests.cs`** (neuf, namespace `Forge.Pont.Tests`, NUnit). C'est un fichier neuf, et aucun fichier de test existant ne change. Une aide construit un `PlanLu` de cellule 7, tick 0, sans parcelle ni bâtiment. La rue du modèle est `R0 = RueDuPlan(0, [(0,0), (40,0), (40,25)], 4, false)`. Tolérance 1e-9 sur les nombres. Les cas :

| # | plan | premier | second | attendu |
|---|---|---|---|---|
| 1 | R0 | (5, 3) | (15, 22) | rue 0, seg 0, début 5, façade 10, profondeur 20, gauche |
| 2 | R0 | (15, 1) | (5, 22) | comme 1 (ordre inversé) |
| 3 | R0 | (5, −3) | (15, −22) | rue 0, seg 0, début 5, façade 10, profondeur 20, droite |
| 4 | R0 | (39, 25) | (28, 0) | rue 0, seg 1, début 0, façade 25, profondeur 10, gauche |
| 5 | R0 | (40, 0) | (30, 15) | égalité seg 0 / seg 1 : seg 0, début 30, façade 10, profondeur 13, gauche |
| 6 | R0 en chantier | (5, 3) | (15, 22) | comme 1 |
| 7 | R0 + `RueDuPlan(5, [(0,50), (40,50)], 6, false)` | (10, 47) | (20, 30) | rue 5, seg 0, début 10, façade 10, profondeur 17, droite |
| 8 | R0 | (5, 10) | (15, 22) | présente : 10 m pile, comme 1 |
| 9 | R0 | (5, 10.01) | (15, 22) | `point trop loin d'une rue` |
| 10 | vide | (5, 3) | (15, 22) | `aucune rue au plan` |
| 11 | `RueDuPlan(2, [(3,3), (3,3)], 4, false)` seule | (3, 3) | (15, 22) | `aucune rue au plan` |
| 12 | R0 | (5, 3) | (45, 22) | `façade dépasse le segment` |
| 13 | R0 | (−3, 1) | (15, 22) | `façade dépasse le segment` (début négatif) |
| 14 | R0 | (5, 3) | (5, 22) | `façade nulle` |
| 15 | R0 | (5, 3) | (15, 1.5) | `second point dans la chaussée` |
| 16 | R0 | (5, 3) | (15, 2) | `second point dans la chaussée` (profondeur 0) |
| 17 | R0 | (NaN, 3) | (15, 22) | `point non fini` |
| 18 | R0 | (5, 3) | (15, +∞) | `point non fini` |
| 19 | R0 | (60, 1) | (70, 22) | `point trop loin d'une rue` (20 m du segment 1, 20,02 m du segment 0) |

  Pour chaque cas présent, le test vérifie aussi `Absence == ""`. Pour les cas 1, 3 et 4, il compare `IntentionJson` au texte exact :
  - 1 : `{"type":"decouper_parcelle","cell":7,"rue":0,"segment":0,"debut_m":5,"facade_m":10,"profondeur_m":20,"cote":"gauche"}` ;
  - 3 : le même avec `"cote":"droite"` ;
  - 4 : `{"type":"decouper_parcelle","cell":7,"rue":0,"segment":1,"debut_m":0,"facade_m":25,"profondeur_m":10,"cote":"gauche"}`.

  Ces trois intentions sont les trois exemples de MODELE : le monde en tire les contours du modèle. Le JSON ne contient pas `foyers` (`StringAssert.DoesNotContain`). Pour chaque cas absent, le test vérifie : `Presente` faux, l'`Absence` qui commence par le message attendu, `Rue == -1`, `Segment == -1`, `DebutM` NaN, `Cote == ""` et `IntentionJson` nul. Un dernier cas vérifie que `Calculer(null, …)` lève `ArgumentNullException`. Les cas s'écrivent en `[TestCase]` autant que possible, pour tenir la taille.

## Conditions de succès

**SC1 — Unity compile et joue les tests (PC).**
Le workflow `unity` (poussée sur la branche) est vert : aucune `error CS`. Puis, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
(sans `-quit`). Le code de sortie vaut 0 et le XML dit `failed="0"`. Les cas de `ClientPlanTests`, `LecteurJsonTests`, `ClientLieuTests`, `PanneauLieuTests`, `ClientIntentionTests` et `KitDesBatimentsTests` y sont, en même nombre et sous les mêmes noms qu'avant. `TraceDeParcelleTests` compte **au moins 20 cas**. Moins, c'est un échec. La PR cite les totaux du XML.

**SC2 — les exemples de MODELE (PC, dans SC1).**
Les cas 1 à 8 passent, avec les trois intentions exactes. Contre-épreuves faites à la main, dites dans la PR, chacune retirée ensuite :
- (a) inverser la normale (gauche ↔ droite) : les cas 1 et 3 rougissent ;
- (b) ne pas retirer la demi-largeur de la profondeur : les cas 1 et 4 rougissent (22 au lieu de 20) ;
- (c) prendre `DebutM = t1` au lieu du minimum : le cas 2 rougit ;
- (d) mesurer la distance à la droite infinie du segment au lieu du segment borné : le cas 19 rougit. Le point (60, 1) est à 1 m de la droite du segment 0, mais à 20,02 m du segment lui-même.

**SC3 — les refus (PC, dans SC1).**
Les cas 9 à 19 et le cas `null` passent. Contre-épreuves faites à la main, dites dans la PR :
- (a) écrire `≥` au lieu de `>` pour la distance de saisie : le cas 8 rougit ;
- (b) retirer le contrôle `DebutM < 0` : le cas 13 rougit ;
- (c) retirer le contrôle de la profondeur : les cas 15 et 16 rougissent.

Et par lecture :
```
grep -cE "UnityEngine|UnityEditor" 3d/unity/Assets/ForgeLocal3D/Pont/TraceDeParcelle.cs
grep -c "foyers" 3d/unity/Assets/ForgeLocal3D/Pont/TraceDeParcelle.cs
```
Les deux rendent `0`.

**SC4 — le monde accepte l'intention formée (VPS ou PC).**
```
cd jeu && python3 -m pytest sim/tests/test_intentions.py -q
```
reste vert, sans changement (133 cas sur master). Puis, à la main, dit dans la PR : déposer les trois `IntentionJson` des cas 1, 3 et 4 par `python3 -m sim --gestes` sur une cellule où la route `[[0,0],[40,0],[40,25]]` de 4 m est tracée au tick 0, découpes au tick 1, `--ticks 3 --monde-json`. La commande rend 0, et le plan final porte les trois contours du modèle. Le fichier de gestes n'est pas commité.

**SC5 — rien d'autre ne bouge.**
```
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC (pc\Tests.cmd)
git diff --name-only origin/master...HEAD
```
La suite du jeu reste verte. Le diff ne nomme que les fichiers du Périmètre et ce brief. `ClientPlan.cs`, `ClientIntention.cs`, `EtapeDuBatiment.cs`, les asmdef, `DesertRoadTool.cs`, les captures, les scènes et `jeu/` sont hors du diff.

## Hors périmètre
- Le mode parcelle de `DesertRoadTool` : clic au sol, conversion `(-x, sol, -y)` vers le plan, aperçu, Entrée, dépôt par `ClientIntention`, et la capture. C'est le sous-lot 2 de #262.
- Trouver la parcelle sous un point et former `poser_batiment` (sous-lot 3 de #262), puis le mode bâtiment (sous-lot 4).
- Choisir le nombre de foyers au chantier : l'intention n'en porte pas, le monde en met 1.
- Refuser une parcelle qui en chevauche une autre, coupe une rue ou sort du bourg (niveau 3 au modèle). Arrondir les mesures, borner la profondeur.
- Changer une règle du monde, `jeu/` (dont `MODELE.md` et `intentions.py`), `ClientPlan.cs`, `ClientIntention.cs`, les asmdef, ou les autres fichiers de tests.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.

## Photo
Sans objet : le lot ne change rien de ce qu'on voit à l'écran. `TraceDeParcelle` n'est appelé par aucune scène, aucun outil d'éditeur ni aucun panneau avant le sous-lot 2 de #262. C'est lui qui branche le calcul sur la souris et porte le scénario de capture.
