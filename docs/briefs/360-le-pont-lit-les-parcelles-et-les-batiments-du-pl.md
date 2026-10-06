# Lot #360 — Le pont lit les parcelles et les bâtiments du plan
Jalon : J4 · Machine : pc · Taille prévue : 240 lignes

## But
Unity relit, dans le plan qu'il demande au service local (`GET /plan?cell=<cell_id>`), chaque parcelle et chaque bâtiment tels que le monde les tient : contour ou emprise, nature, chantier ou fini, travail requis et fourni. S'il ne peut pas, il dit pourquoi et ne devine jamais. La capitale en 3D aura ainsi de quoi dessiner ses parcelles et ses bâtiments « d'après le plan que tient le monde » (CAP.md, jalon 4). Les sous-lots suivants de #261 les dessineront.

## Règle du monde
Sans objet : c'est un lot d'outil, un lecteur. Aucun nombre du monde n'est décidé ici, et `jeu/` n'est pas touché. Niveau de fidélité : sans objet.

Le lot sert la preuve du jalon J4 : « Le plan de la ville vit dans le monde : Unity relancé redessine la même ville d'après le service ». Tout ce dont il a besoin est déjà sur master (6762aed). Il ne s'appuie sur rien que J2 ou J3 doivent encore livrer.

Ce qui existe, vérifié le 06/10/2026 :

- `jeu/sim/service.py` sert `/plan` : `Plan.to_dict()` plus `cell_id`, `rang`, `tick`, `date`. Le document porte toujours les trois listes `rues`, `parcelles`, `batiments`, triées par `identifiant`.
- `jeu/sim/plan.py` et `MODELE.md`, section « Le plan du bourg » :
  - une `Parcelle` a `identifiant` (entier ≥ 0), `contour` (au moins `POINTS_MIN_CONTOUR = 3` points `[x, y]`), `en_chantier` (booléen), `foyers`, `travail_requis`, `travail_fourni` (entiers ≥ 0) ;
  - un `Batiment` a `identifiant`, `parcelle` (identifiant d'une parcelle du même plan), `nature` (texte non vide : le geste ne pose que maison, scierie ou four, mais un bâtiment ancien peut porter un autre texte), `emprise` (au moins 3 points), puis les quatre mêmes champs de chantier ;
  - pour les deux : le fourni ne dépasse pas le requis, et `en_chantier` vaut exactement `travail_fourni < travail_requis`.
- `jeu/sim/tests/test_intentions.py` fige une parcelle servie : `{"identifiant": 0, "contour": [[5, d], [15, d], [15, d + 20], [5, d + 20]], "en_chantier": true, "foyers": 1, "travail_requis": …, "travail_fourni": 5}`.
- `3d/unity/Assets/ForgeLocal3D/Pont/ClientPlan.cs` (#292) ne lit que `cell_id`, `tick` et `rues`. Il y a déjà `PointLocal`, `RueDuPlan`, `PlanLu`, `LecturePlan`, et des aides privées `Valeur`, `Tableau`, `Nombre`, `Entier`, `Decrire`, `CleRefusee`. Toute clé fautive y est nommée par son chemin pointé (`rues[1].points[0]`). Hors des tests, `PlanLu` n'est construit nulle part ailleurs. `DesertRoadTool.cs` et `DesertCityRoads.cs` lisent `Plan.Rues` et `Plan.Tick`, contre le vrai service, qui sert toujours les trois listes.

Ce que le client respecte du modèle :

- **Les points sont en mètres locaux du bourg** (« Le plan du bourg »). Ils sont relus tels quels, sans conversion ni tri. L'ordre des parcelles et des bâtiments est celui de la réponse.
- **Une liste vide est une mesure.** `"parcelles": []` et `"batiments": []` sont l'état réel de toute cellule avant la première découpe. Elles donnent un plan présent à zéro parcelle ou zéro bâtiment. Une clé `parcelles` ou `batiments` **absente**, ou qui n'est pas un tableau, refuse le plan.
- **Ce qui se refuse plutôt que se devine** (AGENTS.md § 4). `en_chantier` ne vaut jamais faux par défaut. Un plan qui contredit le contrat du monde (fourni > requis, chantier qui ne correspond pas au travail restant, bâtiment sur une parcelle absente du plan) est refusé : les lots de dessin n'ont pas à choisir lequel croire. Aucun plan partiel n'est rendu.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientPlan.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs

Précisions :

- **`ClientPlan.cs`**
  - Deux types immuables neufs, dans le même fichier :
    - `ParcelleDuPlan` : `long Identifiant`, `IReadOnlyList<PointLocal> Contour`, `bool EnChantier`, `long TravailRequis`, `long TravailFourni` ;
    - `BatimentDuPlan` : `long Identifiant`, `long Parcelle`, `string Nature`, `IReadOnlyList<PointLocal> Emprise`, `bool EnChantier`, `long TravailRequis`, `long TravailFourni`.

    Leurs listes sont copiées en `ReadOnlyCollection`, comme `RueDuPlan.Points`. Une liste ou une nature nulle lève `ArgumentNullException`.
  - `PlanLu` gagne `IReadOnlyList<ParcelleDuPlan> Parcelles` et `IReadOnlyList<BatimentDuPlan> Batiments`. Son constructeur devient `PlanLu(long cellId, long tick, IList<RueDuPlan> rues, IList<ParcelleDuPlan> parcelles, IList<BatimentDuPlan> batiments)`. Aucune de ces listes n'est nulle.
  - `Lire` lit dans cet ordre : `cell_id`, `tick`, `rues` (code **inchangé** : la méthode `Rue` ne bouge pas, et une rue n'exige toujours ni `foyers` ni `travail_*`), puis `parcelles`, puis `batiments`. Un `CleRefusee` devient l'absence `plan <cellId> : …`, comme aujourd'hui. Les messages sont faits avec les aides existantes. Ce que chaque clé exige, et le chemin nommé en cas de refus :
    - `parcelles` et `batiments` : la clé présente et un tableau, sinon `clé absente : parcelles` ou `clé parcelles : un tableau attendu…` ;
    - `parcelles[i]` et `batiments[i]` : un objet ;
    - `identifiant` : un entier ≥ 0 (`Entier(…, 0)`) ;
    - `contour` et `emprise` : un tableau d'au moins **3** points. Chaque point `contour[j]` ou `emprise[j]` est un tableau d'exactement 2 nombres. La lecture des points est la même que pour une rue : une aide privée commune peut lire les points des parcelles et des bâtiments, mais la lecture des rues n'est pas réécrite ;
    - `en_chantier` : un booléen ;
    - `travail_requis` et `travail_fourni` : des entiers ≥ 0 ;
    - si `travail_fourni > travail_requis`, le refus nomme `…travail_fourni` et dit « dépasse le travail requis » ;
    - si `en_chantier != (travail_fourni < travail_requis)`, le refus nomme `…en_chantier` et dit « contredit le travail restant » ;
    - pour un bâtiment, `nature` : un texte non vide hors espaces. Il n'est pas borné à maison, scierie ou four ;
    - pour un bâtiment, `parcelle` : un entier ≥ 0 qui est l'`identifiant` d'une parcelle **lue dans ce plan**. Sinon le refus nomme `batiments[i].parcelle`.
  - `foyers`, `rang` et `date` ne sont ni lus ni exigés.
  - Le commentaire de classe dit « une rue, une parcelle ou un bâtiment mal formé refuse tout le plan ».
  - Ni l'asmdef, ni `LecteurJson.cs`, ni `ClientLieu.cs`, ni les `.meta` ne changent. Aucune dépendance neuve.
- **`ClientPlanTests.cs`**
  - **Aucune ligne existante ne change** : ni `PLAN_DEUX_RUES`, ni `Remplacer`, ni aucun des quinze cas. On ne fait qu'ajouter.
  - Une constante neuve `PLAN_BOURG` : c'est `PLAN_DEUX_RUES` dont `"parcelles":[],"batiments":[]` est remplacé par les deux listes ci-dessous. Elle est écrite en littéral. Ce plan est valide pour `sim/plan.py` (vérifié), et ses travaux requis sont ceux que `sim/chantiers.py` calcule pour ces surfaces (20, 12, 400, 240) :
    `"parcelles":[{"identifiant":0,"contour":[[5,2],[15,2],[15,22],[5,22]],"en_chantier":false,"foyers":0,"travail_requis":20,"travail_fourni":20},{"identifiant":1,"contour":[[-12.5,7.25],[-4.5,7.25],[-4.5,22.25],[-12.5,22.25]],"en_chantier":true,"foyers":1,"travail_requis":12,"travail_fourni":5}],"batiments":[{"identifiant":0,"parcelle":0,"nature":"maison","emprise":[[5,2],[15,2],[15,22],[5,22]],"en_chantier":false,"foyers":0,"travail_requis":400,"travail_fourni":400},{"identifiant":2,"parcelle":1,"nature":"scierie","emprise":[[-12.5,7.25],[-4.5,7.25],[-4.5,22.25],[-12.5,22.25]],"en_chantier":true,"foyers":1,"travail_requis":240,"travail_fourni":0}]`

    Le bâtiment 2 est sur la parcelle 1 : un client qui lirait l'identifiant à la place de la parcelle rougit. Les deux éléments de chaque liste diffèrent sur chaque champ.
  - Une aide neuve, `RemplacerUneFois(string source, string ancien, string nouveau)`. Elle exige que `ancien` paraisse **exactement une fois** dans `source` (`IndexOf == LastIndexOf`, et ≥ 0) avant de remplacer.
  - Les refus peuvent être un seul test paramétré (`[TestCase(ancien, nouveau, chemin)]`) qui appelle `Absence(CellFigee)` et exige que l'absence contienne le chemin.

## Conditions de succès

**SC1 — Unity compile et joue les tests (PC).**
Le workflow `unity` (poussée sur la branche) est vert : aucune `error CS`. Puis, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
(sans `-quit`). Le code de sortie vaut 0 et le XML dit `failed="0"`. Le XML compte les 15 cas existants de `ClientPlanTests`, sous leurs noms d'aujourd'hui, et ceux de `LecteurJsonTests`, `ClientLieuTests`, `PanneauLieuTests` et `ClientIntentionTests`, inchangés. Il compte aussi **au moins 20 cas neufs** de `ClientPlanTests`. Un nombre total de cas `ClientPlanTests` ≤ 15 est un échec.
Contre-épreuve, faite à la main et dite dans la PR : faire lire `EnChantier = false` à une parcelle dont la clé `en_chantier` manque fait rougir le cas « parcelle sans en_chantier » de SC4. Retirer ce changement le rétablit.

**SC2 — un plan servi est relu exactement (PC, dans SC1).**
Le faux service rend `200` et `PLAN_BOURG`. `Lire(9922)` rend `Presente`. Les valeurs sont **égales** (`==`, sans tolérance) aux littéraux, dans l'ordre de la réponse :
- `Rues` : les deux rues de `UnPlanServiEstReluExactement`, mêmes valeurs ;
- `Parcelles.Count == 2` :
  - parcelle 0 : `Identifiant` 0, contour `(5,2) (15,2) (15,22) (5,22)`, `EnChantier` faux, requis 20, fourni 20 ;
  - parcelle 1 : `Identifiant` 1, contour `(-12.5,7.25) (-4.5,7.25) (-4.5,22.25) (-12.5,22.25)`, `EnChantier` vrai, requis 12, fourni 5 ;
- `Batiments.Count == 2` :
  - bâtiment 0 : `Identifiant` 0, `Parcelle` 0, `Nature` `"maison"`, emprise des 4 points de la parcelle 0, `EnChantier` faux, requis 400, fourni 400 ;
  - bâtiment 2 : `Identifiant` 2, `Parcelle` 1, `Nature` `"scierie"`, emprise des 4 points de la parcelle 1, `EnChantier` vrai, requis 240, fourni 0.

Un second cas : `PLAN_BOURG` sans `"foyers":0,"travail_requis":400,` remplacé par `"travail_requis":400,` (le `foyers` du bâtiment 0 retiré) est lu présent, avec les mêmes valeurs. `foyers` n'est donc pas exigé.

**SC3 — une liste vide est une mesure (PC, dans SC1).**
- `PLAN_DEUX_RUES` (inchangé) est lu présent, avec `Parcelles` et `Batiments` non nulles, de `Count == 0` toutes les deux, et `Rues.Count == 2`.
- `PLAN_BOURG` avec la liste `batiments` entière remplacée par `[]` (coupée par `IndexOf`, comme dans `UnPlanSansRueEst…`, et le test vérifie que le texte a changé) est lu présent : `Parcelles.Count == 2`, `Batiments.Count == 0`. Le cas affirme `Assert.AreNotEqual(2, Batiments.Count)`.

Contre-épreuve : un client qui rendrait toujours des listes vides fait rougir SC2. Un client qui refuserait une liste vide fait rougir SC3.

**SC4 — toute parcelle ou tout bâtiment mal formé refuse le plan en nommant son chemin (PC, dans SC1).**
Chaque cas part de `PLAN_BOURG`, fait **un seul** remplacement par `RemplacerUneFois`, puis appelle `Lire(9922)`. Il exige `Presente` faux, `Plan` nul et une `Absence` qui contient `9922` et le chemin indiqué. Le texte avant `→` est remplacé par celui d'après la flèche. Chaque fragment de départ paraît exactement une fois dans `PLAN_BOURG` (vérifié). La faute porte toujours sur le **second** élément de sa liste.

| cas | remplacement | chemin exigé |
|---|---|---|
| identifiant négatif | `{"identifiant":1,` → `{"identifiant":-1,` | `parcelles[1].identifiant` |
| contour à 2 points | `"contour":[[-12.5,7.25],[-4.5,7.25],[-4.5,22.25],[-12.5,22.25]]` → `"contour":[[-12.5,7.25],[-4.5,7.25]]` | `parcelles[1].contour` |
| coordonnée texte | `"contour":[[-12.5,7.25]` → `"contour":[["-12.5",7.25]` | `parcelles[1].contour[0]` et `un nombre attendu` |
| point à 3 nombres | `"contour":[[-12.5,7.25],` → `"contour":[[-12.5,7.25,0],` | `parcelles[1].contour[0]` |
| parcelle sans en_chantier | `"en_chantier":true,"foyers":1,"travail_requis":12` → `"foyers":1,"travail_requis":12` | `parcelles[1].en_chantier` |
| fourni absent | `"travail_requis":12,"travail_fourni":5}` → `"travail_requis":12}` | `parcelles[1].travail_fourni` |
| requis en texte | `"travail_requis":12,` → `"travail_requis":"12",` | `parcelles[1].travail_requis` |
| fourni au-delà | `"travail_fourni":5}` → `"travail_fourni":13}` | `parcelles[1].travail_fourni` et `dépasse` |
| chantier fini mais déclaré en cours | `"travail_fourni":5}` → `"travail_fourni":12}` | `parcelles[1].en_chantier` et `contredit` |
| parcelle inconnue | `"parcelle":1,` → `"parcelle":7,` | `batiments[1].parcelle` |
| parcelle en texte | `"parcelle":1,` → `"parcelle":"1",` | `batiments[1].parcelle` |
| nature absente | `"nature":"scierie",` → (rien) | `batiments[1].nature` |
| nature blanche | `"nature":"scierie"` → `"nature":" "` | `batiments[1].nature` |
| nature nombre | `"nature":"scierie"` → `"nature":3` | `batiments[1].nature` |
| coordonnée nulle | `"emprise":[[-12.5,7.25]` → `"emprise":[[-12.5,null]` | `batiments[1].emprise[0]` |
| requis décimal | `"travail_requis":240,` → `"travail_requis":240.5,` | `batiments[1].travail_requis` |
| fourni négatif | `"travail_fourni":0}` → `"travail_fourni":-1}` | `batiments[1].travail_fourni` |
| en_chantier entier | `"en_chantier":true,"foyers":1,"travail_requis":240` → `"en_chantier":1,"foyers":1,"travail_requis":240` | `batiments[1].en_chantier` |
| élément non objet | `"batiments":[{` → `"batiments":[7,{` | `batiments[0]` |

Plus trois cas coupés par `IndexOf` (le test vérifie que le texte a changé) :
- **`parcelles` absente** : `"parcelles":[…],` retiré en entier → `clé absente : parcelles` ;
- **`batiments` absente** : `,"batiments":[…]` retiré en entier → `clé absente : batiments` ;
- **parcelles vidées sous des bâtiments** : la liste `parcelles` remplacée par `[]` → `batiments[0].parcelle`.

**SC5 — rien d'autre ne bouge.**
```
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC (pc\Tests.cmd)
git diff --name-only origin/master...HEAD
git diff origin/master...HEAD -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs | grep '^-[^-]'
```
La suite du jeu reste verte. Le diff ne nomme que les deux fichiers du périmètre, plus ce brief. La troisième commande ne sort **aucune ligne** : aucune ligne de test retirée ni modifiée. La méthode `Rue` de `ClientPlan.cs` n'apparaît pas dans le diff.

## Hors périmètre
- Dessiner les parcelles ou les bâtiments, et choisir la pièce du kit (piquets, murs, fini) selon le chantier : sous-lots 3 et 4 de #261.
- Redessiner les rues au lancement : sous-lot 2 de #261.
- Lire `foyers`, `rang` ou `date`. Exiger des rues de nouvelles clés (`foyers`, `travail_*`). Vérifier qu'un identifiant n'est pas en double, ou qu'une emprise tient dans sa parcelle.
- Borner `nature` à maison, scierie ou four.
- Toucher `DesertRoadTool.cs`, `DesertCityRoads.cs`, `ClientLieu.cs`, `ClientIntention.cs`, `LecteurJson.cs`, `PanneauLieu.cs`, les asmdef, les `.meta`, ou les autres fichiers de tests.
- Toucher `jeu/` (service, plan, chantiers, `MODELE.md`, tests).
- Toute lecture asynchrone, et toute dépendance externe.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.

## Photo
Sans objet : le lot ne change rien de ce qu'on voit à l'écran. `ClientPlan` gagne deux listes que rien n'affiche encore. Aucune scène, aucun outil d'éditeur, aucun panneau ne les lit avant les sous-lots 3 et 4 de #261, qui porteront chacun leur scénario de capture.
