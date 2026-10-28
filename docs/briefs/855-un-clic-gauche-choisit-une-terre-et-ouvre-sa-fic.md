# Lot #855 — Un clic gauche choisit une terre et ouvre sa fiche
Jalon : J4 · Machine : pc · Taille prévue : 260 lignes

## But
Sur la carte, un clic gauche court garde la terre sous la souris et ouvre son dossier, un glisser déplace la carte sans rien choisir, Échap referme le dossier avant d'ouvrir le menu, et le clic droit ne fait plus rien.

## Le joueur
Le joueur clique une terre de la carte : elle se marque et son dossier « Territoire conservé » s'ouvre, comme dans tout jeu de grande stratégie. Glisser déplace toujours la carte, sans changer la terre choisie ; Échap referme la fiche, puis, s'il n'y a plus de fiche ouverte, ouvre le menu. Le clic droit est libre : il servira aux ordres. Il sent que la carte se prend en main sans mode d'emploi : il trouve sa capitale, ouvre son dossier d'un clic, et un double-clic sur son siège le fait toujours descendre dans sa ville (#729). C'est le premier des six lots de « La prise en main de la carte » (`CAP.md`, jalon 4). C'est un lot de fond du geste du J4 **passer de la carte à sa ville d'un geste** : il choisit d'abord ce qu'il regarde. #856 fera parler ce dossier en noms.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change, ni `jeu/sim/`, ni `jeu/sim/MODELE.md`, ni le service. Le dossier lit `/lieu?cell=` comme aujourd'hui (`DossierTerritoire`).

## Périmètre
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/MenuCabinet.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot855.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot855.cs.meta
docs/briefs/855-un-clic-gauche-choisit-une-terre-et-ouvre-sa-fic.md

Tout autre chemin est interdit ; le `.meta` est généré par Unity. `SurvolDeCarte`, `ParcoursDeCarte`, `PassageALaCapitale`, `FicheDeCellule`, `DossierTerritoire`, `DossierBourg` et les captures existantes ne changent pas : le glisser (gauche ou milieu) et le double-clic y marchent déjà. Dans `CabinetDeCarteTests.cs`, les cas s'ajoutent après les cas existants. Aucune ligne existante n'est modifiée ni retirée, et le panneau garde son nom « Territoire conservé » (`LesDeuxDossiersRestentOuvertsEtLesPanneauxArretentLesClics`). Budget : environ 35 lignes dans le cabinet, 10 dans le menu, 55 de tests, 90 de capture et 70 de brief, dans le style dense du cabinet.

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`, sur le PC, éditeur fermé, depuis la racine, en PowerShell. `INTERFACE` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot855-interface.xml -logFile 3d/unity/Temp/lot855-interface.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec, et les cas nommés réellement exécutés : zéro cas est un échec. Les tests s'écrivent d'abord et se voient rouges avant le code.

Le cabinet ajoute :
- `public const float SEUIL_CLIC_PX = 6f` : la même valeur que `SurvolDeCarte.SEUIL_CLIC_PX`, pour qu'un clic qui garde compte aussi pour le double-clic ;
- `public CelluleDeCarte Retenue` : la terre gardée, nulle sinon ;
- `public const string AIDE` : la ligne d'aide de la carte, sur une ligne, par exemple « Clic : choisir une terre · Glisser : déplacer · Molette : zoomer · Échap : fermer ». Elle remplace les deux copies actuelles du texte « Clic droit : conserver un territoire ». Le texte d'invitation du panneau dit « Clic gauche sur une terre pour ouvrir son dossier. » ;
- `public bool Noter(Vector2 ici, bool appui, bool relache, bool horsCarte, CelluleDeCarte sous)`. À l'appui, le cabinet retient le point de départ, sauf si l'appui est `horsCarte`. Dès que le pointeur s'en écarte de plus de `SEUIL_CLIC_PX`, même s'il y revient, ce n'est plus un clic. Au relâché, un clic parti de la carte, jamais éloigné et relâché hors d'un panneau appelle `Garder(sous)` et rend `true`. Un appui et un relâché dans la même image font un clic. `sous` nul ne change rien ; recliquer la terre gardée la garde ;
- `public bool HorsCarte(Vector2 ecran)` : vrai sans caméra, hors du `pixelRect` de la caméra de la carte, ou si `EventSystem.current.RaycastAll` trouve un graphique à ce point. Le calcul se fait au point donné, pas à la souris ;
- `public bool Relacher()` : rend `false` sans terre gardée. Sinon il retire la teinte (`SetPropertyBlock(null)`), remet `Retenue` à null, et le panneau retrouve son invitation au prochain `Afficher`.

`Update` ne lit plus `rightButton`. Il appelle `Noter` avec la souris : position, `leftButton.wasPressedThisFrame`, `wasReleasedThisFrame`, `HorsCarte` calculé seulement aux images d'appui ou de relâché, et `fiche.Survolee` après `fiche.Survoler(ici)` au relâché. Le cabinet n'appelle jamais `PassageALaCapitale` : le double-clic reste à `SurvolDeCarte`, et un clic compté deux fois ferait descendre sur un seul clic.

`MenuCabinet` ajoute `public Func<bool> AvantDOuvrir` et `public void Echap()` : menu ouvert, il le ferme ; sinon, si `AvantDOuvrir` rend `true`, rien de plus ; sinon il ouvre le menu. `Update` appelle `Echap()` au lieu de `Basculer()`, et la garde du champ de saisie reste. Le cabinet pose `AvantDOuvrir = Relacher`. L'aide du menu dit « Clic gauche » (choisir une terre et ouvrir son dossier), le glisser bouton gauche ou du milieu, « Double-clic » sur son siège pour entrer dans sa ville, et Échap qui ferme le dossier puis ouvre ou ferme le menu. Elle ne dit plus « Clic droit » et tient dans sa boîte de 410 px sans pousser le réglage du volume.

**SC1 — Un clic court garde la terre.** `INTERFACE`, cas `UnClicSansMouvementGardeLaTerre`. Le test appuie puis relâche au même point avec une cellule 7 bâtie comme `UnTerritoireConserveSurvitALaFinDuSurvol` : `Retenue` vaut la cellule 7, et après `Afficher` le panneau dit « Ville test ». Il refait le geste dans la même image, puis avec un relâché à exactement 6 px : la terre est gardée. Une cellule « Cellule 7 » posée sous la racine porte une teinte (`HasPropertyBlock`). Contre-épreuve : un cabinet qui ne garde qu'au clic droit rougit.

**SC2 — Un glisser ne change pas la terre gardée.** `INTERFACE`, cas `UnGlisserNeChangePasLaTerreGardee`. La cellule 7 est gardée par un clic. Puis trois gestes au-dessus d'une cellule 9 : un glisser de 40 px, un détour de 100 px revenu au point d'appui, et un relâché à 7 px. Après chacun, `Retenue` reste la cellule 7 et `Noter` rend `false`. Contre-épreuve : un cabinet qui juge le seul écart final, ou garde à tout relâché, rougit.

**SC3 — Un clic sur un panneau ne traverse pas.** `INTERFACE`, cas `UnClicSurUnPanneauNeTraversePas`. Trois gestes, sans terre gardée au départ : un appui `horsCarte` relâché sur la carte ; un appui sur la carte relâché `horsCarte` ; un relâché sans appui. Aucun ne garde rien. `HorsCarte` sans caméra rend `true`. Contre-épreuve : un clic jugé au seul relâché rougit le premier geste.

**SC4 — Échap ferme le dossier avant d'ouvrir le menu.** `INTERFACE`, cas `EchapFermeLeDossierAvantDOuvrirLeMenu`. La cellule 7 est gardée et le menu fermé. Un premier `Echap()` vide `Retenue`, laisse le menu fermé et retire la teinte ; le panneau redit l'invitation et plus « Ville test ». Un deuxième ouvre le menu, un troisième le ferme. Sans terre gardée, un `Echap()` ouvre aussitôt le menu. Contre-épreuve : un menu qui s'ouvre alors qu'une terre est gardée rougit.

**SC5 — Les aides disent les nouveaux gestes, et rien d'autre ne garde ni ne descend.** `INTERFACE`, cas `LesAidesDisentLesNouveauxGestes`. `AIDE` contient « Clic », « Glisser » et « Échap », pas « Clic droit », et sa `preferredWidth` dans le texte d'aide tient dans ses 1190 px. Le texte du menu (panneau inactif compris) contient « Clic gauche », « Double-clic » et « Échap », pas « Clic droit », et sa `preferredHeight` tient dans sa boîte. La source `Assets/Interface/CabinetDeCarte.cs` ne contient ni `rightButton` ni `PassageALaCapitale`. `SEUIL_CLIC_PX` égale `ForgeLocal3D.SurvolDeCarte.SEUIL_CLIC_PX`, lu par réflexion comme dans `ReperesDeDepartTests` ; un type introuvable échoue. Contre-épreuve : le code d'aujourd'hui rougit sur `rightButton` et sur « Clic droit ».

**SC6 — Le double-clic descend encore, et rien d'autre ne bouge.** Les commandes :
- `INTERFACE` passe sur toute l'assemblée ;
- `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot855-pont.xml -logFile 3d/unity/Temp/lot855-pont.log` passe sans échec, y compris les cas de `GesteDeClic` et du double-clic de `PassageALaCapitaleTests` ;
- `U -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 729 -forgeTicks 3 -forgeCaptures 3d/unity/Temp/lot855-double-clic -logFile 3d/unity/Temp/lot855-double-clic.log` sort 0, avec Biskra après la transition, sous le cabinet de ce lot ;
- `python3 -m pytest jeu -q` passe ;
- `git diff -U0 origin/master -- 3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs` ne montre aucune ligne retirée ;
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre ;
- `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

Contre-épreuve : un cas existant modifié, ou un fichier hors du Périmètre, refuse la livraison.

## Hors périmètre
- Les noms dans le dossier (#856), l'infobulle (#857), les modes de carte (#858), la barre du haut et la disparition de « Parcourir le monde » (#859), l'ouverture en pause (#860), la langue visuelle (#849, #850).
- Un ordre au clic droit : il ne fait plus rien sur la carte, et rien ne le remplace dans ce lot.
- Fermer « Plan du bourg », « Autres maisons » ou un feuillet par Échap. Retirer ou cacher le panneau « Territoire conservé » : il reste, avec son invitation, quand aucune terre n'est gardée.
- Changer le glisser, la molette, le survol, le double-clic, `ReperesDeDepart` ou une scène. Désélectionner d'un clic dans le vide.

## Photo
La photo montre la carte de 1400, la Morée marquée d'un clic gauche à la teinte de la terre gardée, et à droite le dossier « Territoire conservé » ouvert sur sa cellule, avec ses lieux lus au tick servi.

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot855.cs`, avec un scénario unique, `[ScenarioDeCapture(855, "moree-choisie-d-un-clic")]`, sur le modèle de `Lot655` et `Lot729`. Il réutilise `Lot549.Ouvrir/Photographier` et les aides `internal` de `Lot690` sans les changer. Chaque attente est bornée à 30 s, et toute absence échoue en nommant sa cause. Les étapes :
1. Ouvrir `Forge_Carte`. Exiger le vrai `CabinetDeCarte` et son `MenuCabinet`, mettre survol et parcours en `automatique`, attendre `Lot690.LecturePrete(cabinet.Partie)`, et exiger `Retenue` nulle.
2. Prendre la seule fiche de `/departs` dont `Siege.Nom == "Mistra"` (« Despotat de Morée ») et son `CellId`. Lire `/lieu?cell=` de cette cellule par `ClientLieu`. Placer le point du lieu de rang 0 par `PositionSurLaCarte(…, ReperesDeDepart.HAUTEUR_LIEU)`, et le cadrer comme `Lot729` (`Vue.Zoomer` puis `Vue.Centrer`). Le point écran `P` doit tomber sur la cellule de la Morée (`CelluleSous`), avec `HorsCarte(P)` faux.
3. Panneau : `Q` est le centre écran du panneau « Parcourir le monde », qui est au-dessus de la vue de la carte. Exiger `HorsCarte(Q)` vrai. Un appui puis un relâché par `cabinet.Noter(Q, …, HorsCarte(Q), celluleDeLaMoree)` laissent `Retenue` nulle.
4. Glisser : un appui à `P`, un pas à `P + (40, 0)`, puis un relâché là, avec la cellule de la Morée en `sous`. `Retenue` reste nulle.
5. Clic : un appui puis un relâché à `P` (avec `-forge855Glisser`, ce clic est remplacé par le glisser de l'étape 4). Exiger `Retenue.CellId` égal à la Morée, sinon échouer par « aucune terre gardée après le geste ». Exiger la teinte sur « Cellule <id> » et, sans toucher au panneau, que son texte commence par « Cellule <id> · tick ».
6. Échap : `menu.Echap()` vide `Retenue` sans ouvrir le menu, un deuxième l'ouvre, un troisième le ferme. Puis l'étape 5 se rejoue pour la photo.
7. Photo comme `Lot655` : `Lot549.Photographier`, la caméra sur toute l'image, et la toile « Cabinet » en `ScreenSpaceCamera` sur la caméra reçue. Exiger `Lot690.DansLeChamp` pour le texte du dossier et le point de la Morée dans le champ. Attendre dix images, puis revérifier `Retenue` et le texte.
8. La trace `CAPTURE_855` donne la cellule, `P`, `Q`, les résultats des étapes 3 à 6 et la première ligne du dossier.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 855 -forgeCaptures 3d/unity/Temp/lot855-photo -logFile 3d/unity/Temp/lot855-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 855 -forgeCaptures 3d/unity/Temp/lot855-glisser -forge855Glisser -logFile 3d/unity/Temp/lot855-glisser.log
```

La première sort 0 avec une image `*--moree-choisie-d-un-clic.png` : c'est la photo. La seconde, la contre-épreuve, sort 1 sans image : son journal dit « aucune terre gardée après le geste » pour le glisser de 40 px. Le codeur ouvre l'image lui-même. Une Morée non marquée, un dossier qui dit encore l'invitation ou « Lecture des lieux », ou un panneau coupé refusent la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, la sortie de la contre-épreuve et ce que montre l'image.
