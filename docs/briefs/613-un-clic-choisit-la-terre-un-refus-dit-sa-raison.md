# Lot #613 — Un clic choisit la terre, un refus dit sa raison
Jalon : J3 · Machine : pc · Taille prévue : 275 lignes

## But
Sur la carte de 1400, un clic sur le repère d'une terre de départ dépose au service le choix de cette terre ; l'écran dit le tick que le service nomme dans son reçu, ou le refus avec la raison que le monde donne.

## Le joueur
Le joueur, qui a comparé les six terres au survol (#624), clique sur celle où il veut commencer, par exemple le repère de la Morée. En haut de l'écran, il lit « Terre choisie : Despotat de Morée » et le tick après lequel le monde l'applique : son choix est un geste déposé dans le monde, pas un réglage de l'écran. S'il clique ensuite sur une autre terre, le Zab, le monde refuse et l'écran le dit avec la raison du monde : « départ déjà choisi : seigneurie-3 ». Il sent que le choix engage : on ne change pas de terre. Sous-lot 5 de #404 « Le joueur choisit sa terre sur la carte » : la caméra qui se pose sur son siège et ses quatre lieux suit, puis la part qu'il fixe sur ces lieux, le geste de J3.

Dépend de : #612 (#625, #626, #624 livrés : six repères dans la scène Carte, survol par `SurvolDeCarte`).

## Règle du monde
Sans objet : lot de vue. Le geste est l'intention existante `{"type": "choisir_depart", "seigneurie": <id>}` par `POST /intention` (« Les intentions du joueur » de `jeu/sim/MODELE.md`) : 200 `{"acceptee": true, "appliquee_au_tick": <tick publié>}`, appliquée au tick suivant ; 409 « départ déjà choisi : seigneurie-<n> » pour un choix retenu ou en attente ; 400 sinon. Unity ne juge rien : il dépose, puis affiche le tick et la raison tels que le service les rend, sans +1 ni refus local. Aucune règle, constante ou donnée du monde ne change ; le service Python n'est pas touché.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ReperesDeDepart.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ReperesDeDepartTests.cs
3d/unity/Assets/ForgeLocal3D/Carte/SurvolDeCarte.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot613.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot613.cs.meta
docs/briefs/613-un-clic-choisit-la-terre-un-refus-dit-sa-raison.md

**`ReperesDeDepart`** (même style dense ; repères, survol, fiche et leurs observables ne changent pas) :
- Un `ClientIntention(port, ClientDeparts.DelaiMinimal)` créé dans `Demarrer`, libéré dans `Arreter`, qui vide aussi l'état du choix.
- `public void Choisir(Vector2 ecran)` : `Survoler(ecran)` ; si une terre est survolée et qu'aucun dépôt n'est en vol, `Task.Run` dépose `{"type":"choisir_depart","seigneurie":<fiche.Id>}` (entier en `InvariantCulture`) ; hors de tout repère, rien n'est déposé ni affiché ; un clic pendant un dépôt en vol est ignoré. Jamais d'appel HTTP sur le fil principal.
- `Pas` relève le dépôt fini (avant la garde `complet`, sans changer la lecture des repères) et affiche son reçu. Observables : `public bool ChoixEnVol`, `public RecuIntention RecuDuChoix` (le dernier reçu), `public FicheDeDepart TerreDuChoix`, `public string ChoixAffiche` (null quand le panneau est caché).
- `public static string DireLeChoix(FicheDeDepart fiche, RecuIntention recu)`, entiers en `InvariantCulture`, exactement :
  - en vol (`recu == null`) : `Choix envoyé au monde : <Nom>` ;
  - accepté : `Terre choisie : <Nom>\nLe monde l'applique au tick suivant (après le tick <AppliqueeAuTick>).` — le tick du reçu, jamais celui de `/departs` ni un +1 ;
  - refusé : `Choix refusé pour <Nom> :\n<Erreur>` — la raison du service, verbatim ;
  - absent : `Choix sans réponse pour <Nom> :\n<Absence>`.
- Le panneau « Choix de la terre » : un `Image` de fond `FOND` dans la toile de `Construire`, ancré en **haut au centre** (`anchorMin = anchorMax = pivot = (0.5, 1)`, `anchoredPosition = (0, -MARGE)`), `VerticalLayoutGroup` + `ContentSizeFitter`, `Text` en police 24, `raycastTarget = false` partout ; caché tant qu'aucun choix n'est envoyé. Les quatre coins sont pris (fiche de cellule, horloge, absences, fiche de la terre).

**`SurvolDeCarte`** : `public void Cliquer(Vector2 position)`, même garde que `Survoler` (dans la fenêtre, hors panneau) puis `reperes.Choisir(position)` si `reperes != null`. Dans `Update`, sous le garde existant : la position est gardée à l'appui du bouton gauche (`wasPressedThisFrame`) ; au relâché (`wasReleasedThisFrame`), `Cliquer` seulement si la souris a bougé d'au plus `SEUIL_CLIC_PX = 6` depuis l'appui, pour qu'un glissé de `ParcoursDeCarte` ne choisisse jamais une terre. `ParcoursDeCarte`, la scène et `CarteBuilder` ne changent pas.

**Tests** (ajoutés à `ReperesDeDepartTests`) : le faux service apprend `POST /intention` — il note le chemin dans `recues` comme les autres, garde chaque corps reçu, attend `lenteurIntention` ms, rend la réponse suivante d'une file que le test remplit (404 si vide). Aucun cas existant ne change ; décrits en SC2–SC5.

## Conditions de succès
SC1 — Rouge d'abord, puis tout le pont vert. Sur le PC, à la racine, Unity de `3d/unity/ProjectSettings/ProjectVersion.txt`, en PowerShell :
```powershell
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot613.xml" -logFile "$env:TEMP\lot613.log"
```
Sans `-quit` ; sortie 0, XML sans échec ni cas ignoré, les nouveaux cas effectivement joués (zéro cas neuf est un échec) ; ils échouent avant le code. Les cas existants (`ReperesDeDepartTests` dont ceux de #624, `ClientIntentionTests`, `FicheDeCelluleTests`, `CarteDessineeTests`…) passent sans une ligne changée.

SC2 — Un clic dépose le choix de sa terre. Commande de SC1. Six repères posés (`Avancer`) ; file : 200 `{"acceptee":true,"appliquee_au_tick":7}`. `Choisir(carte.camera.WorldToScreenPoint(<repère de la Morée>.position))`, puis des pas jusqu'à `ChoixEnVol == false` : un seul `POST /intention`, corps exactement `{"type":"choisir_depart","seigneurie":3}` ; `TerreDuChoix.Nom == "Despotat de Morée"`, `RecuDuChoix.AppliqueeAuTick == 7`, `ChoixAffiche == "Terre choisie : Despotat de Morée\nLe monde l'applique au tick suivant (après le tick 7)."` écrit littéralement dans le test. Contre-épreuve : le tick de `/departs` est 3, un texte qui dirait 3 ou 8 rougit.

SC3 — Le second choix affiche le refus du service. Commande de SC1. File : 200 tick 3, puis 409 `{"acceptee":false,"erreur":"départ déjà choisi : seigneurie-3"}`. Clic sur la Morée, puis sur le Zab : deux `POST /intention`, le second avec `"seigneurie":6` (la vue ne refuse rien elle-même) ; `RecuDuChoix.Statut == 409`, `ChoixAffiche == "Choix refusé pour Émirat du Zab :\ndépart déjà choisi : seigneurie-3"`. Contre-épreuve dans le test : un 400 `{"acceptee":false,"erreur":"raison du faux service"}` s'affiche verbatim (« Choix refusé pour … :\nraison du faux service ») — un texte composé par Unity rougit.

SC4 — Hors d'un repère, rien ; sans service, l'absence se dit. Commande de SC1. Un clic au milieu de la mer (`WorldToScreenPoint` de (1e6, 0, 1e6) en local) : aucun `POST`, `ChoixAffiche == null`. File vide : le 404 se dit `Choix sans réponse pour Despotat de Morée :\n` suivi de l'absence de `ClientIntention`. Contre-épreuve : un dépôt fait sans terre survolée rougit le compte de requêtes.

SC5 — Le pas n'attend pas le service. Commande de SC1. `lenteurIntention = LENTEUR_MS` : `Choisir` et le `Pas` suivant durent moins de `DELAI_MAX_PAS_MS`, `ChoixEnVol` vrai, `ChoixAffiche == "Choix envoyé au monde : Despotat de Morée"` ; un second clic pendant le vol n'envoie rien (un seul `POST` une fois le dépôt fini). Le panneau « Choix de la terre » est ancré en (0.5, 1), ses deux graphiques `raycastTarget == false` (lus par réflexion, comme le cas du coin de #624). Contre-épreuve : un dépôt sur le fil principal dépasse 100 ms.

SC6 — La capture choisit puis montre un refus. Sans `-quit` ni `-nographics` :
```powershell
Unity.exe -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 613 -forgeSeed 0 -forgeCaptures "$env:TEMP\lot613" -logFile "$env:TEMP\lot613.log"
```
Sortie 0, journal `CAPTURE_613` avec les deux textes affichés. `Lot613.cs` (`[ScenarioDeCapture(613, "second-choix-refuse")]`) s'écrit comme `Lot624` : `Lot549.Ouvrir`, `SurvolDeCarte.automatique` et `ParcoursDeCarte.automatique` vrais, six repères actifs et aucune lecture en vol en 30 s au plus, `/departs` lu hors du fil pour le tick et les fiches de la Morée et du Zab (`Siege.Nom == "Biskra"`). Puis, par `SurvolDeCarte` seulement (`Survoler` puis `Cliquer` sur `carte.camera.WorldToScreenPoint(<repère>.position)`, jamais `ReperesDeDepart.Choisir`) : clic sur la Morée, attente du reçu (30 s) ; exige accepté, `AppliqueeAuTick ==` tick lu (le pilote ne passe pas `-forgeTicks` : rien de figé), `ChoixAffiche == DireLeChoix(Morée, reçu)`. Clic sur le Zab, attente ; exige `Statut == 409`, `Erreur == "départ déjà choisi : seigneurie-3"`, `ChoixAffiche == DireLeChoix(Zab, reçu)`, la fiche de la terre survolée est celle du Zab. Puis `Lot549.Photographier`, dix images de pose, `ChoixAffiche` inchangé. Les erreurs nomment l'attendu et l'observé.

SC7 — Sans premier choix, la capture rougit. Même commande avec `-forge613SansPremierChoix` (traité seulement dans `Lot613.cs`, qui saute le clic sur la Morée) : le Zab est accepté par le service, le contrôle du refus échoue, sortie 1 avec « refus attendu ». Ni compilation impossible, ni service absent, ni exception levée par le drapeau lui-même ne prouvent ce contrôle. Contre-épreuve : sans le drapeau, SC6 est vert.

SC8 — La photo montre le refus. Ouvrir le `*--second-choix-refuse.png` de SC6 : la carte entière, les six disques nommés, en haut au centre le panneau lisible « Choix refusé pour Émirat du Zab : départ déjà choisi : seigneurie-3 », en bas à droite la fiche du Zab, en bas à gauche la fiche de sa cellule, en haut à droite l'horloge ; aucun panneau ne recouvre un autre. Le codeur et le relecteur regardent eux-mêmes l'image. Contre-épreuve : refus absent, coupé, illisible ou sous un autre panneau refuse la livraison même avec sortie 0.

SC9 — Périmètre et taille. `git diff --check`, `git diff --name-only`, `git diff --numstat`, `git ls-files --others --exclude-standard` : seuls les six chemins du Périmètre ; ajouts et retraits cumulés, fichiers neufs et ce brief compris, sous 300 lignes. Budget : ~40 dans `ReperesDeDepart`, ~12 dans `SurvolDeCarte`, ~60 de tests, ~85 de capture, 2 de `.meta` (généré par Unity), ~75 de brief. Contre-épreuve : un autre chemin ou 300 lignes refuse la livraison.

## Hors périmètre
La caméra posée sur le siège choisi et les lieux du joueur surlignés (sous-lot suivant de #404), l'épreuve Morée ; relire `/monde` pour montrer la terre tenue ; changer de terre ou annuler un choix ; la scène `Forge_Carte.unity` et `CarteBuilder` (aucun composant ajouté) ; `ClientIntention`, les autres clients, les fixtures, `ParcoursDeCarte`, `FicheDeCellule`, `Lot624.cs`, `EpreuveCarte.cs` et le service Python. Aucun test existant ne change ni ne s'assouplit.

## Photo
`3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot613.cs`, lancé par SC6 sur le vrai service (graine 0, horloge à 0, tick du pilote) : la scène Carte s'ouvre en vue entière, les six repères se posent, le scénario clique par `SurvolDeCarte` sur la Morée (choix accepté), puis sur le Zab (refusé), et copie le cadrage par `Lot549.Photographier`. La photo `*--second-choix-refuse.png` montre les six terres nommées, en haut au centre le refus « départ déjà choisi : seigneurie-3 » pour l'Émirat du Zab, et en bas à droite la fiche du Zab survolé. Pas de PNG ajouté au dépôt.
