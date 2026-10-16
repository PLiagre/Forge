# Lot #624 — La fiche d'une terre s'ouvre au survol de son repère
Jalon : J3 · Machine : pc · Taille prévue : 270 lignes

## But
Sur la carte de 1400, la souris posée sur le repère d'une terre de départ ouvre sa fiche (terre, maison, siège, habitants de sa cellule, suzerain, voisins, lieux tenus), telle que le service la sert ; hors d'un repère, la fiche se cache.

## Le joueur
Le joueur promène la souris sur les six repères de la carte ; sur chacun, une fiche s'ouvre en bas à droite et lui dit ce qu'il prendrait en main : le nom de la terre, sa maison, son siège, combien de gens vivent dans sa cellule, qui est son suzerain, qui sont ses voisins et combien de lieux il tiendrait. Il compare la Morée (Mistra, Paléologue, sous Byzance) au Zab (Biskra, 3 459 habitants, sous les Hafsides) et pèse où commencer : une terre peuplée ou maigre, un suzerain fort ou faible, des voisins de sa puissance ou d'une autre. Sous-lot 2 de #612 (découpé de #404 « Le joueur choisit sa terre sur la carte ») : le clic qui choisit la terre suit, puis le geste de J3 sur les quatre lieux autour du siège.

Dépend de : #623 (#625 et #626 livrés : `ReperesDeDepart` est dans la scène Carte, ses six repères posés).

## Règle du monde
Sans objet : lot de vue. Terre, maison (texte), siège, cellule, habitants, suzerain et voisins viennent de `/departs` (« La carte et les terres servies, vue dérivée » de `jeu/sim/MODELE.md`), les lieux tenus de `/maison?id=seigneurie-<id>` (« Les maisons servies, vue dérivée »), tels que `ReperesDeDepart` les lit déjà. Rien n'est calculé, arrondi ni deviné dans Unity ; aucune règle, constante ou donnée du monde ne change.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ReperesDeDepart.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ReperesDeDepartTests.cs
3d/unity/Assets/ForgeLocal3D/Carte/SurvolDeCarte.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot624.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot624.cs.meta
docs/briefs/624-la-fiche-d-une-terre-s-ouvre-au-survol-de-son-re.md

**`ReperesDeDepart`** (même style dense, rien de ce qui est posé ni de ses observables ne change) :
- À la pose d'un repère (`Poser`), garder pour sa terre la `FicheDeDepart`, la `MaisonLue`, le `Tick` du `DepartsLus` lu et la position locale du repère. `Arreter` vide tout.
- `public void Survoler(Vector2 ecran)` : rayon de `carte.camera` sur le plan du repère (`transform.up`, `transform.TransformPoint(0, HAUTEUR_REPERE, 0)`), puis `SurvolerPoint`. `public void SurvolerPoint(Vector3 monde)` : passé en local (`InverseTransformPoint`), la terre survolée est celle dont le centre est à distance horizontale (x, z) ≤ `DIAMETRE_REPERE_KM / 2`, la plus proche s'il y en a plusieurs ; aucune sinon. `public void Quitter()`. Observables : `public FicheDeDepart Survolee`, `public string FicheAffichee` (null quand la fiche est cachée).
- `public static string Decrire(FicheDeDepart fiche, long tick, MaisonLue maison)`, entiers en `InvariantCulture`, sans séparateur de milliers. Pour la Morée de la fixture, exactement :
```
Despotat de Morée
Maison : Paléologue
Siège : Mistra, cellule 10340
Habitants de la cellule : 80919 au tick 3
Suzerain : Byzance
Voisins :
  cellule 10335, Byzance, 77525 habitants
  cellule 10347, Byzance, 55393 habitants
Lieux tenus : 4
```
  Un suzerain nul : « Suzerain : aucun, le monde n'en nomme pas » ; une puissance de voisin nulle (10087 du Zab) : « cellule 10087, aucune puissance nommée, 5509 habitants » ; aucun voisin : « Voisins : aucun ». Lieux tenus = `maison.Lieux.Count`. Le suzerain est `fiche.Suzerain` (la puissance, Hafsides 35 pour le Zab), jamais la maison du suzerain.
- La fiche : un `Image` de fond `FOND` (motif de `FicheDeCellule`) nommé « Fiche de la terre », dans la toile déjà créée par `Construire`, ancré en **bas à droite** (`anchorMin = anchorMax = pivot = Vector2.right`, `anchoredPosition = (-MARGE, MARGE)`), `VerticalLayoutGroup` + `ContentSizeFitter`, son `Text` en police 24 ; `raycastTarget = false` sur l'image et le texte. Le coin est libre : en bas à gauche la fiche de cellule, en haut à droite l'horloge, en haut à gauche le message d'absence des repères. Cachée par défaut et dès que rien n'est survolé.

**`SurvolDeCarte`** : `ReperesDeDepart reperes` pris dans `Awake` par `GetComponent` (absent toléré, testé par `!= null`, pas par `?.`). La logique d'`Update` passe dans `public void Survoler(Vector2 position)` : dans la fenêtre et hors d'un panneau, `fiche.Survoler(position)` et `reperes.Survoler(position)` ; sinon les deux `Quitter()`. `Update` garde son garde (`automatique`, souris absente) et appelle `Survoler(souris.position.ReadValue())`. Le `RequireComponent` reste celui de `FicheDeCellule` ; `EpreuveCarte`, `Lot526` et la scène ne changent pas.

**Tests** (ajoutés à `ReperesDeDepartTests`, même faux service, aucun cas existant touché) : décrits en SC2–SC4.

## Conditions de succès
SC1 — Rouge d'abord, puis tout le pont vert. Sur le PC, à la racine, Unity de `3d/unity/ProjectSettings/ProjectVersion.txt`, en PowerShell :
```powershell
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot624.xml" -logFile "$env:TEMP\lot624.log"
```
Sans `-quit` ; sortie 0, XML sans échec ni cas ignoré, les nouveaux cas de `ReperesDeDepartTests` effectivement joués (zéro cas neuf est un échec) ; ils échouent avant le code. Les cas existants (`ReperesDeDepartTests`, `FicheDeCelluleTests`, `CarteDessineeTests`, `HorlogeDeCarteTests`…) passent sans une ligne changée.

SC2 — La fiche dit les valeurs servies. Commande de SC1. Six repères posés (`Avancer` existant) ; pour chaque fiche lue par `ClientDeparts` sur la fixture, `SurvolerPoint` au centre de son repère (`r.position`) : `Survolee.Id == fiche.Id`, `FicheAffichee == Decrire(fiche, 3, maison lue par ClientMaison au faux service)`, et le texte contient, pris dans la fixture par le test : `fiche.Nom`, « Maison : » + `fiche.Maison`, « Siège : » + `fiche.Siege.Nom` + « , cellule » + `fiche.CellId`, `fiche.Habitants`, le nom du suzerain, chaque `cell_id` voisin, « Lieux tenus : 4 ». Pour la Morée, égalité avec le texte littéral ci-dessus écrit dans le test ; pour le Zab, « Suzerain : Hafsides », « cellule 10087, aucune puissance nommée, 5509 habitants » et sept voisins. Par l'écran aussi : `Survoler(carte.camera.WorldToScreenPoint(r.position))` ouvre la même fiche (la carte posée cadre sa caméra). Contre-épreuve dans le test : la Morée servie avec deux lieux (fiche `/maison` remplacée avant la pose) dit « Lieux tenus : 2 » — un compte figé à 4 rougit ; le texte du Zab n'est jamais celui de la Morée.

SC3 — Hors d'un repère, la fiche se cache. Commande de SC1. Au centre de la Morée décalé de `0,45 × DIAMETRE_REPERE_KM` en x local : fiche de la Morée ; décalé de `0,55 ×` : `Survolee == null`, `FicheAffichee == null` ; au milieu de la mer (1e6, 0, 1e6) : cachée ; `Quitter()` après un survol : cachée. Contre-épreuve : un rayon d'atteinte égal au diamètre (ou une fiche qui reste ouverte après `Quitter`) rougit ces cas.

SC4 — Le coin est libre. Commande de SC1. L'objet « Fiche de la terre » a `anchorMin == anchorMax == pivot == Vector2.right`, son image et son texte `raycastTarget == false` ; une fiche de cellule (`FicheDeCellule` sur le même objet) ancrée en `Vector2.zero` et le texte d'absence en `Vector2.up` ne la partagent pas. Contre-épreuve : un ancrage en bas à gauche ou en haut à droite rougit.

SC5 — La capture survole la Morée par `SurvolDeCarte`. Sans `-quit` ni `-nographics` :
```powershell
Unity.exe -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 624 -forgeSeed 0 -forgeTicks 3 -forgeCaptures "$env:TEMP\lot624" -logFile "$env:TEMP\lot624.log"
```
Sortie 0, journal `CAPTURE_624` avec le texte de la fiche. `Lot624.cs` (`[ScenarioDeCapture(624, "fiche-de-la-moree")]`) ouvre la scène par `Lot549.Ouvrir` (énumérateur déroulé comme `Lot626`), met `SurvolDeCarte.automatique` et `ParcoursDeCarte.automatique` à vrai, attend 30 s au plus six repères actifs sous « Repères des terres de départ » et aucune lecture en vol, lit lui-même hors du fil `/departs` (`ClientDeparts`) et `/maison?id=seigneurie-3` (`ClientMaison`) sur le port du composant, puis appelle `SurvolDeCarte.Survoler(carte.camera.WorldToScreenPoint(<repère « Repère Despotat de Morée »>.position))` — jamais `ReperesDeDepart.Survoler` directement. Il exige : tick lu 3 ; `Survolee.Nom == "Despotat de Morée"` ; `FicheAffichee == ReperesDeDepart.Decrire(fiche lue, tick lu, maison lue)` et contient « Mistra », « Paléologue », « Byzance » ; la fiche de cellule survolée en même temps est la cellule 10340 (le survol a bien été transmis aux deux). Puis `Lot549.Photographier`, dix images de pose. Les erreurs nomment l'attendu et l'observé.

SC6 — Hors du repère, la capture rougit. Même commande avec `-forge624HorsRepere` (traité seulement dans `Lot624.cs`) : le point visé est le centre de la Morée décalé d'un `DIAMETRE_REPERE_KM` vers l'est en local de la carte, mêmes contrôles sans changer leur référence : sortie 1 pour « aucune terre survolée » ; ni compilation impossible, ni service absent, ni exception levée par le drapeau lui-même ne prouvent ce contrôle. Contre-épreuve : sans le drapeau, SC5 est vert.

SC7 — La photo montre la fiche. Ouvrir le `*--fiche-de-la-moree.png` de SC5 : la carte entière, les six disques nommés, en bas à droite la fiche lisible de la Morée (Mistra, Paléologue, Byzance, voisins, 4 lieux), en bas à gauche la fiche de la cellule 10340, en haut à droite l'horloge, sans message d'absence. Le codeur et le relecteur regardent eux-mêmes l'image. Contre-épreuve : fiche absente, coupée, illisible ou posée sur un autre panneau refuse la livraison même avec sortie 0.

SC8 — Périmètre et taille. `git diff --check`, `git diff --name-only`, `git diff --numstat` et `git ls-files --others --exclude-standard` : seuls les six chemins du Périmètre ; ajouts et retraits cumulés, fichiers neufs et ce brief compris, sous 300 lignes. Budget : ~40 lignes dans `ReperesDeDepart`, ~8 dans `SurvolDeCarte`, ~55 de tests, ~85 de capture, 2 de `.meta` (généré par Unity), ~75 de brief. Contre-épreuve : un autre chemin ou 300 lignes refuse la livraison.

## Hors périmètre
Le clic qui choisit la terre et le refus affiché (#404, sous-lot suivant) ; la caméra au siège et les lieux surlignés ; la scène `Forge_Carte.unity` et `CarteBuilder` (aucun composant ajouté, pas de régénération) ; `FicheDeCellule`, `CarteDessinee`, les clients HTTP, les fixtures, `Lot526.cs`, `Lot626.cs`, `EpreuveCarte.cs` et le service Python. Aucune lecture nouvelle du service par le composant : la fiche dit ce que `ReperesDeDepart` a déjà lu. Aucun test existant ne change ni ne s'assouplit.

## Photo
`3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot624.cs`, lancé par SC5 sur le vrai service (graine 0, tick 3, horloge à 0) : la scène Carte s'ouvre en vue entière, les six repères se posent, le scénario pose le survol sur le disque de la Morée par `SurvolDeCarte.Survoler`, puis copie le cadrage par `Lot549.Photographier`. La photo `*--fiche-de-la-moree.png` montre les six terres nommées et, en bas à droite, la fiche du Despotat de Morée : maison Paléologue, siège Mistra, habitants de la cellule 10340, suzerain Byzance, ses deux voisins et ses 4 lieux. Pas de PNG ajouté au dépôt.
