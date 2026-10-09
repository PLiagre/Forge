# Lot #547 — Le pont dessine les cellules de la carte servie
Jalon : J3 · Machine : pc · Taille prévue : 290 lignes

## But
Unity sait demander la carte de 1400 au service sans figer l'image, et poser chacune de ses 596 cellules à la couleur de sa puissance ; sans service, il dit « le monde ne répond pas » et ne pose rien.

## Le joueur
Pour la première fois, l'Europe de 1400 s'affiche dans Unity : chaque cellule servie par `sim/`, chaque royaume à sa couleur, les terres sans puissance en gris, les enclaves vides. Si le monde ne tourne pas, le joueur le lit en clair au lieu de fixer un écran vide. C'est le geste du jalon J3 « ouvrir sa carte » (#403) qui se prépare, avant d'y choisir sa terre (#404), puis d'y régler la part qu'il prend sur ses lieux et d'ouvrir son grenier (#405). Dans ce lot, seule la photo montre la carte : le sous-lot 3 de #523 (la scène `Forge_Carte`) la rendra ouvrable en jeu, et le sous-lot 2 y ajoutera contours, villes et caméra. Sous-lot 1 de #523 ; il dépend de #520 (`ClientCarte`) et de #542 (`MaillageDeCarte`), tous deux livrés.

## Règle du monde
Sans objet : lot de vue. Il lit, sans rien calculer du monde, « La carte et les terres servies, vue dérivée » et « Les puissances de 1400, vue dérivée » de `jeu/sim/MODELE.md`. Contours et puissances sont ceux du service ; le gris dit « sans puissance », jamais une puissance devinée. `cell_id` reste la seule clé spatiale.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/CarteDessinee.cs
3d/unity/Assets/ForgeLocal3D/Pont/CarteDessinee.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/CarteDessineeTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/CarteDessineeTests.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot547.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot547.cs.meta
docs/briefs/547-le-pont-dessine-les-cellules-de-la-carte-servie.md

Tout autre chemin est interdit. Précisions, sur le modèle de `PanneauLieu` (lecture en `Task.Run`, appliquée dans `Pas`) :

- **`CarteDessinee : MonoBehaviour`**, dans `Forge.Pont`. Champs publics `int port = PanneauLieu.DEFAULT_SERVICE_PORT` et `new Camera camera` (facultative). Constantes publiques `MESSAGE_ABSENCE = "le monde ne répond pas"` et `PERIODE_RELECTURE_S = 2f`. Méthodes `Demarrer()`, `Pas(double maintenant)`, `Arreter()`, appelées par `Start`, `Update` (`Time.realtimeSinceStartupAsDouble`) et `OnDestroy`. Lectures : `TexteAffiche`, `int CellulesServies` (-1 tant qu'aucune carte n'est posée), `int CellulesPosees` (enfants de la racine des cellules), `bool LectureEnVol`.
- **Lecture.** `Demarrer` construit la toile, écrit `carte : en attente de 127.0.0.1:<port>` et crée un `ClientCarte(port, ClientCarte.DelaiMinimal)`. `Pas` applique une lecture finie, puis, s'il n'y a ni carte posée ni lecture en vol et que l'heure est venue, en lance une : `Task.Run` qui appelle `Lire()`, puis `MaillageDeCarte.Mailler` hors du fil principal. Une `ArgumentException` du maillage devient une absence de cause `carte : <message>`. Après une absence, la lecture suivante part `PERIODE_RELECTURE_S` plus tard ; une fois la carte posée, plus aucune lecture ne part.
- **Absence.** Le texte vaut exactement `le monde ne répond pas`, un saut de ligne, puis la cause rendue par `ClientCarte` telle quelle. Aucune cellule n'est posée. Le texte s'affiche dans un `Text` sur une toile : `ScreenSpaceCamera` sur `camera` si elle est posée (comme `PanneauLieu`, pour que la capture le voie), sinon `ScreenSpaceOverlay`.
- **Pose**, sur le fil principal, une seule fois. Sous un enfant `Cellules de la carte`, dans l'ordre de `CarteMaillee.Cellules`, un objet `Cellule <cell_id>` par cellule : `MeshFilter` dont le `Mesh` reprend tels quels `Maillage.Sommets` et `Maillage.Triangles`, puis `RecalculateNormals` et `RecalculateBounds` ; `MeshRenderer` dont le matériau porte `Couleur`. Un matériau par couleur distincte, copié de `GraphicsSettings.currentRenderPipeline.defaultMaterial` comme `DesertParcelles`. Sans ce matériau, le texte dit `carte non dessinée : le pipeline de rendu n'a pas de matériau par défaut`, aucune cellule n'est posée et aucune lecture ne repart. Une fois posée, le texte vaut `""` et son objet est inactif. `CellulesServies` vaut `CarteLue.Cellules.Count`. `Arreter` libère le client et détruit les maillages et matériaux créés.
- **Tests** dans le nouveau `CarteDessineeTests.cs` seulement. Un faux `HttpListener` sur port libre, comme `PanneauLieuTests`, compte les requêtes et rend les octets de `carte-graine0.json` (lus sous `Application.dataPath`), ou une réponse choisie, avec une lenteur réglable. L'attendu se dérive de la fixture par `ClientCarte` puis `Mailler`, lus avant de poser le composant. Le compteur est remis à zéro ensuite.
- **Budget** : composant ≤ 90 lignes, tests ≤ 115, scénario ≤ 40. Les absences se regroupent en `[TestCase]`.

## Conditions de succès
**SC1 — compilation, suite verte, rouge d'abord.** Sur le PC, éditeur de `3d/unity/ProjectSettings/ProjectVersion.txt`, sans `-quit` : `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\pont-547.xml" -logFile "$env:TEMP\pont-547.log"`. Exiger : sortie 0, `failed="0"`, aucun cas ignoré, les cas nouveaux ci-dessous présents, tous les cas existants sous les mêmes noms et en même nombre. Le workflow `unity` est vert. Contre-épreuve : les tests écrits d'abord rougissent avec un `Pas` qui ne pose rien ; la PR garde ce constat.

**SC2 — autant de cellules posées que servies.** Commande SC1 avec `-testFilter Forge.Pont.Tests.CarteDessineeTests.La_carte_servie_pose_une_cellule_par_cellule_servie`. Après une lecture complète : le faux service a reçu une seule requête, de chemin `/carte`. `CellulesServies == CellulesPosees == 596`, égal au compte dérivé de la fixture. Les enfants portent `Cellule <cell_id>` dans l'ordre servi. Chaque `Mesh` a exactement les sommets (comparés par `==`) et les indices du maillage attendu. La couleur de chaque matériau égale `Couleur` à l'octet. Le nombre de matériaux distincts égale le nombre de couleurs distinctes dérivé (40 mesurés : 39 puissances et le gris). `TexteAffiche == ""`, son objet est inactif. Vingt `Pas` de plus, à 10 s d'écart chacun : toujours une requête et 596 cellules. Contre-épreuves : oublier la dernière cellule, poser deux fois, ou prendre la couleur par rang font rougir ce cas.

**SC3 — sans service, zéro cellule et le message, puis la carte au retour.** `-testFilter Forge.Pont.Tests.CarteDessineeTests.Sans_service_aucune_cellule_et_le_message`. Sans écoute sur le port : `CellulesPosees == 0`, `CellulesServies == -1`. La première ligne de `TexteAffiche` vaut exactement `le monde ne répond pas`, la seconde contient `service absent sur 127.0.0.1:<port>`, le texte est actif et `GetComponentInChildren<Text>().text == TexteAffiche`. On lance ensuite le faux service. Un `Pas` 1 s plus tard ne lance rien : zéro requête. Un `Pas` 2,5 s après l'absence lance une lecture, qui pose 596 cellules et efface le message. Contre-épreuve : un composant qui ne relit jamais, ou qui pose une carte vide, fait rougir ce cas.

**SC4 — une réponse illisible ne pose rien.** `-testFilter Forge.Pont.Tests.CarteDessineeTests.Une_reponse_illisible_ne_pose_rien`, en `[TestCase]` : un 404, et la fixture coupée de moitié. Résultat attendu : zéro cellule, première ligne `le monde ne répond pas`, seconde ligne qui contient respectivement `statut 404` et `JSON invalide`.

**SC5 — la lecture ne fige pas l'image.** `-testFilter Forge.Pont.Tests.CarteDessineeTests.Le_pas_ne_bloque_pas_pendant_la_lecture`. Avec 2 000 ms de lenteur au faux service, le `Pas` qui lance la lecture rend la main en moins de 100 ms, et `LectureEnVol` est vrai. Contre-épreuve : un `Lire()` appelé dans `Pas` fait rougir ce cas.

**SC6 — la photo est prise.** `Unity.exe -batchmode -quit -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeCaptures "$env:TEMP\cap547" -forgeLot 547 -logFile "$env:TEMP\cap547.log"`. Exiger : sortie 0, `CAPTURE_SCENARIOS lot 547 : 1`, un `CAPTURE_SCENARIO_OK` pour `Forge_Desert_Ville_ksar_des_sept_puits--carte-des-cellules.png`, aucun `CAPTURE : le scénario`. Contre-épreuve : avec une cellule de moins posée, le scénario lève et la commande sort à 1 ; la PR le dit.

**SC7 — périmètre et budget.** `git diff --name-only origin/master...HEAD` ne nomme que le périmètre. `git diff --numstat origin/master...HEAD` totalise moins de 300 lignes, brief compris. `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/ | grep -c '^-[^-]'` affiche `0`.

## Hors périmètre
Contours des cellules, noms des villes, caméra qui cadre la carte (sous-lot 2 de #523). Scène `Forge_Carte`, build settings, lanceur (sous-lot 3 de #523, puis #403). Survol, panneau, `/monde`, horloge, choix de la terre (#404), part et grenier (#405). Aucun changement de `ClientCarte`, `MaillageDeCarte`, `TriangulationDeCarte`, `PanneauLieu`, `ForgeCapture`, des tests existants, des asmdef, de `ProjectSettings/`, de `jeu/` ni de `MODELE.md`. Aucun chemin protégé de la chaîne.

## Photo
La carte de 1400 entière vue d'en haut, nord en haut : 596 cellules aux couleurs de leurs 39 puissances, les 31 sans puissance en gris, les trous laissés vides. Le plan fixe (le désert) sert de comparaison.

Scénario `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot547.cs`, `[ScenarioDeCapture(547, "carte-des-cellules")]`. ForgeCapture a lancé le service (graine 0, port 8000) et ouvert la scène du désert. Le scénario :
1. crée un objet `Carte des cellules` à la position (0 ; 20 000 ; 0), loin au-dessus du désert, y ajoute `CarteDessinee` avec `camera` = la caméra reçue ;
2. attend image par image, au plus 30 s en `Time.realtimeSinceStartupAsDouble`, que `CellulesServies >= 0`. Sinon il lève avec `TexteAffiche`. Il lève aussi si `CellulesPosees` vaut 0 ou diffère de `CellulesServies` ;
3. désactive `DesertCityCamera` et `VillageV2Visit` s'ils sont sur la caméra (la première reprend la transform à chaque image), puis coupe `RenderSettings.fog`. Il pose la caméra en (0 ; 23 300 ; 0), rotation (90 ; 0 ; 0), perspective, champ vertical 60°, plans proche 10 et lointain 10 000 : le désert, à 23 000 m, sort du champ, et la carte (environ 4 350 × 3 500 km) y tient entière ;
4. laisse passer 10 images et lève si la caméra a bougé.

Le codeur regarde le PNG lui-même et dit dans la PR ce qu'il y voit : cellules colorées, gris, enclaves vides, rien de coupé.
