# Lot #625 — Les repères des six terres de départ se posent sur la carte
Jalon : J3 · Machine : pc · Taille prévue : 285 lignes

## But
La carte Unity sait poser un repère sur le siège de chaque terre de départ servie, chacun dans la cellule de sa terre, et dire à l'écran celles qu'elle ne peut pas poser.

## Le joueur
Lot de fond, sous-lot 1 de #623 (découpé de #612, lui-même découpé de #404 « Le joueur choisit sa terre sur la carte »). Il prépare ce geste : en ouvrant la carte de 1400, le joueur verra les six terres où il peut commencer, chacune à sa place et nommée, et pèsera où commencer — près d'un suzerain fort ou d'un faible, une terre riche ou pauvre. Ici le composant existe et ses tests le prouvent, mais il n'est pas encore dans la scène : c'est le sous-lot 2 de #623 (scène régénérée + capture) qui le rendra visible ; la fiche au survol suit (#612, sous-lot 2).

## Règle du monde
Sans objet : lot de vue. Unity ne calcule rien : le siège est `siege.point` (x_m, y_m, EPSG:3035) de `/maison?id=seigneurie-<id>` (« Les maisons servies, vue dérivée » de `jeu/sim/MODELE.md`), la terre et sa cellule viennent de `/departs`. Aucune projection lat/lon, aucun point deviné.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/CarteDessinee.cs
3d/unity/Assets/ForgeLocal3D/Pont/ReperesDeDepart.cs
3d/unity/Assets/ForgeLocal3D/Pont/ReperesDeDepart.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/CarteDessineeTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ReperesDeDepartTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ReperesDeDepartTests.cs.meta

**`CarteDessinee`** : garder l'origine de `Mailler` à la pose (à côté de `reperage`) et exposer `public Vector3? PositionSurLaCarte(PointCarte point, float hauteur)` : la position **locale** (dans le transform de la carte) que `Place` donne déjà aux contours et aux noms ; `null` tant que la carte n'est pas posée. `Place`, `Tracer`, `Nommer`, les hauteurs et tout ce qui est posé restent tels quels.

**`ReperesDeDepart`** (`Forge.Pont`, `[DefaultExecutionOrder(10)]`, `[RequireComponent(typeof(CarteDessinee))]`, motif de `FicheDeCellule`) : `public int port` ; `Demarrer`/`Pas(double)`/`Arreter` publics, appelés par `Start`/`Update`/`OnDestroy`.
- Aucune lecture tant que `PositionSurLaCarte` rend `null`. Ensuite, hors du fil principal (`Task.Run`), une lecture = `ClientDeparts.Lire()` puis, pour chaque fiche de `/departs` sans repère, `ClientMaison.Lire("seigneurie-" + fiche.Id)` (les deux clients à `ClientDeparts.DelaiMinimal`, sans les modifier). Une seule lecture en vol ; `Pas` n'attend jamais.
- Au retour, dans `Pas` : un repère par fiche lue dont le siège a une `Position`, sous un enfant « Repères des terres de départ », nommé « Repère » + nom de la terre (`FicheDeDepart.Nom`), à `PositionSurLaCarte(position, HAUTEUR_REPERE)`, avec `public const float HAUTEUR_REPERE = 2f` (au-dessus de `HAUTEUR_NOM`). Il porte un disque plat de `DIAMETRE_REPERE_KM = 40` (cylindre primitif, collider retiré) teint `COULEUR_REPERE`, une couleur qu'aucune cellule ne prend, matériau tiré de `defaultMaterial` du pipeline comme `CarteDessinee`, et le nom de la terre en `TextMesh` comme les villes, un peu au nord du disque. Tout ce qui est créé est détruit par `Arreter`.
- Absences, dites dans un `Text` en haut à gauche sur `carte.camera` (motif de `FicheDeCellule`) : première ligne `public const string MESSAGE_ABSENCE = "terres de départ incomplètes"`, puis une ligne par manque : l'absence de `/departs` telle quelle (`departs : …`), ou « <nom de la terre> : » + l'absence de `/maison` (`maison : statut 404 …`), ou « <nom de la terre> : siège hors carte, » + `Absents["siege"]`. Aucun repère pour un manque. Tant qu'il manque quelque chose, une nouvelle lecture part `PERIODE_RELECTURE_S = 2` s plus tard ; les repères déjà posés ne bougent pas et ne se doublent pas. Toutes les fiches posées : le texte se cache et plus aucune requête ne part.
- Observables pour les tests : `ReperesPoses` (nombre), `TexteAffiche`, `LectureEnVol`.

**Tests** (`ReperesDeDepartTests`, faux `HttpListener` comme `FicheDeCelluleTests`, qui note chaque `PathAndQuery`) : `/carte` → `carte-graine0.json`, `/departs` → `departs-graine0-tick3.json` (statut réglable), `/maison?id=seigneurie-N` → une fiche écrite dans le test à partir de ces sièges mesurés (service graine 0, tick 3, master 2535e03 ; lieux `(cell, 0..3)`, `absents` vide), remplaçable par une réponse au choix pendant le test :

| id | maison | cellule | siège | x_m | y_m |
|---|---|---|---|---|---|
| 1 | Bar | 10430 | Bar-le-Duc | 3965409.11 | 2862646.57 |
| 2 | Wurtemberg | 10465 | Stuttgart | 4260932.34 | 2851742.83 |
| 3 | Paléologue | 10340 | Mistra | 5424441.58 | 1644956.82 |
| 4 | Branković | 10334 | Vučitrn | 5217097.38 | 2256208.68 |
| 5 | Evrenosoğulları | 10337 | Giannitsa | 5367717.15 | 2051967.94 |
| 6 | Banou Mozni | 10103 | Biskra | 3926430.32 | 1322273.47 |

Mesuré en reproduisant `ReperageDeCarte` (float, pair-impair, origine = centre de la boîte) : chaque siège tombe dans sa cellule et dans aucune autre.

## Conditions de succès
SC1 — Rouge d'abord, puis tout le pont vert. Sur le PC, à la racine, avec la version de `3d/unity/ProjectSettings/ProjectVersion.txt`, en PowerShell :
```powershell
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot625.xml" -logFile "$env:TEMP\lot625.log"
```
Sans `-quit` ; sortie 0, XML sans échec ni cas ignoré, cas `ReperesDeDepartTests` et le nouveau cas de `CarteDessineeTests` effectivement joués ; zéro cas neuf est un échec. Les nouveaux cas échouent avant le code. Tous les cas existants (`CarteDessineeTests`, `FicheDeCelluleTests`, `HorlogeDeCarteTests`…) passent sans une ligne changée.

SC2 — Six repères, chacun dans la cellule de sa terre. Commande de SC1. Les six fiches servies : `ReperesPoses == 6 ==` nombre de fiches lues par `ClientDeparts` sur la fixture ; pour chaque fiche, un seul objet « Repère <nom> », `localPosition` égale composante par composante à `((x − o.X)/1000, HAUTEUR_REPERE, (y − o.Y)/1000)` (o = `Mailler(...).Origine`, comme `Converti` de `CarteDessineeTests`), `HAUTEUR_REPERE > HAUTEUR_NOM`, et `carte.CelluleSous(position monde du repère).CellId == fiche.CellId` ; six cellules distinctes ; `COULEUR_REPERE` absente des couleurs des cellules posées. Requêtes : `/departs` une fois, chaque `/maison?id=seigneurie-N` une fois ; vingt `Pas` de plus sur 60 s n'en lancent aucune ; texte caché. Contre-épreuve dans le test : le siège de la terre suivante (rotation des six) n'est jamais dans la cellule de la terre ; et poser à `(x/1000, y/1000)` sans origine, ou à `(lat, lon)`, fait rougir.

SC3 — Une réponse absente se dit, sans repère inventé. Commande de SC1. Cas paramétrés sur Morée (`seigneurie-3`) : 404 `{"erreur":"maison inconnue"}`, puis siège hors carte (`cell_id`, `rang`, `point` nuls, `absents.siege` textuel). Cinq repères, aucun « Repère Despotat de Morée » ; `TexteAffiche` commence par `MESSAGE_ABSENCE` et contient « Despotat de Morée » et `statut 404` (ou la raison servie). Puis la vraie fiche servie : après `PERIODE_RELECTURE_S`, six repères, les cinq premiers sont les mêmes objets, le texte est caché. Et `/departs` en 500 : zéro repère, texte avec `departs : ` et `statut 500`, aucune requête `/maison`. Contre-épreuve : poser Morée à un point par défaut (0, 0 ou centre de cellule) donne six repères et rougit.

SC4 — La conversion exposée est celle de la carte. Commande de SC1. Nouveau cas dans `CarteDessineeTests` : avant la pose `PositionSurLaCarte` rend `null` ; après, pour chacune des 57 villes, `PositionSurLaCarte(v.Position, HAUTEUR_NOM)` égale exactement la `localPosition` du nom posé. Contre-épreuve : oublier l'origine ou inverser x et z rougit ce cas.

SC5 — Le pas n'attend pas. Commande de SC1. Avec `/departs` servi 2 s en retard, `Pas` rend la main en moins de 100 ms et `LectureEnVol` est vrai. Contre-épreuve : une lecture synchrone dans `Pas` rougit.

SC6 — Périmètre et taille. `git diff --name-only` et `git diff --numstat` (fichiers neufs et ce brief compris) : seuls les six chemins ci-dessus et le brief ; moins de 300 lignes. Budget : ~6 lignes dans `CarteDessinee`, ~95 de composant, ~110 de tests, ~6 dans `CarteDessineeTests`, 4 de `.meta` (générés par Unity). Contre-épreuve : un autre chemin ou ≥ 300 lignes refuse la livraison.

## Hors périmètre
La scène `Forge_Carte.unity`, `CarteBuilder`, toute capture (sous-lot 2 de #623) ; la fiche au survol (#612, sous-lot 2) ; le clic et le choix (#404) ; `ClientDeparts`, `ClientMaison`, `ServiceLocal`, `ReperageDeCarte`, les fixtures existantes et le service Python. Aucun test existant ne change ni ne s'assouplit.

## Photo
sans objet : le composant n'est dans aucune scène, rien ne change à l'écran ; le sous-lot 2 de #623 l'ajoute à la scène Carte et photographie la carte entière avec ses six repères.
