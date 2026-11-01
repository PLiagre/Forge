# Lot #788 — Les passants circulent dans la capitale et suivent ses lectures
Jalon : J4 · Machine : pc · Taille prévue : 295 lignes

## But
La capitale affiche les passants du bourg sur les trajets de leur métier et remplace cette foule quand une nouvelle lecture cohérente du monde arrive.

## Le joueur
Le joueur entre dans Biskra et marche dans une rue où les ouvriers vont aux chantiers, les paysans aux débouchés et les artisans aux ateliers ; il sent que la capitale se peuple, se vide et change de destinations avec le monde qu’il gouverne. Ce lot rend visible le geste de J4 « entrer dans sa capitale et y marcher » et achève l’intégration découpée de #421. Dépend de : #784 pour les effectifs, #786 pour le civil animé et #787 pour les trajets.

## Règle du monde
Sans objet : vue Unity pure, sans écriture ni règle nouvelle dans le monde. Elle lit `jeu/sim/MODELE.md`, « Les lieux d’une cellule, vue dérivée », « Les foyers par métier », « Le plan du bourg » et « Le chantier et ses bras ». `PassantsDuBourg` fixe les effectifs visuels et `TrajetsDesMetiers` les destinations ; ce lot ne réinterprète ni population, ni métier, ni travail. La marche, sa vitesse et la répartition entre plusieurs trajets sont des conventions d’affichage de niveau 2, sans effet sur le tick.

Ajouter `PassantsDeLaVille`, monté par `DesertRoadTool` avec le maillage et le matériau VAT de #786 référencés dans les deux scènes de ville. Toutes les 0,25 s, hors du fil principal, il lit `/lieu` et `/plan` pour la cellule ouverte. Il n’applique qu’une paire présente portant le même `cell_id` et le même tick ; une paire absente, discordante ou ancienne ne mélange rien et nomme sa cause. Ouvrir une autre cellule retire immédiatement la foule précédente. Une paire cohérente d’un tick neuf remplace toute la racine précédente avant de poser la nouvelle ; une relecture du même tick ne double rien.

Pour chaque métier dont #784 rend un compte positif, calculer les trajets de #787 et garder seulement ceux qui portent des points accessibles. Répartir les passants dans l’ordre ordinal des métiers, puis cycliquement dans l’ordre stable des trajets ; alterner leur sens et décaler leur phase d’après leur rang, sans aléa. Un métier sans trajet accessible ne reçoit aucun objet et reste déclaré dans le bilan, jamais posé sur une ligne inventée. Chaque passant suit la polyligne complète à 1,2 m/s, revient par le trajet inverse, épouse la hauteur du terrain, regarde dans le sens de marche et anime la phase `marche` du matériau VAT. Un `MaterialPropertyBlock` porte phase et teinte de tunique : aucun matériau n’est dupliqué par image.

Le composant expose pour l’épreuve la cellule et le tick appliqués, le nombre projeté, le nombre posé, les comptes posés par métier, les absences de trajet et sa racine courante. Ces mesures sont dérivées des lectures reçues ; `-1` signifie non calculé et zéro reste une mesure.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Desert/PassantsDeLaVille.cs
3d/unity/Assets/ForgeLocal3D/Desert/PassantsDeLaVille.cs.meta
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Desert/Scenes/Forge_Desert_Ville_ksar_des_sept_puits.unity
3d/unity/Assets/ForgeLocal3D/Desert/Scenes/Forge_Desert_Ville_oued_des_vents.unity
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot788.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot788.cs.meta
docs/briefs/788-les-passants-circulent-dans-la-capitale-et-suive.md

## Conditions de succès
SC1 — Rouge d’abord, compilation et acquis verts. Depuis la racine sur le PC Windows, éditeur fermé :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults '3d/unity/Temp/lot788-tests.xml' -logFile '3d/unity/Temp/lot788-tests.log'
```
Attendre la fin sans `-quit` ; exiger un XML présent, sans échec ni cas ignoré. Avant l’intégration, la commande photo de SC2 échoue parce qu’aucun scénario #788 ni aucune foule branchée n’existe. Après, les cas de #784 et #787 restent inchangés et verts. Contre-épreuve : XML absent, compilation rouge, cas ignoré ou test existant modifié refuse la livraison.

SC2 — Biskra suit une paire cohérente. Commande P :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 788 -forgeSeed 0 -forgeTicks 0 -forgeCaptures '3d/unity/Temp/lot788-photo' -logFile '3d/unity/Temp/lot788-photo.log'
```
Le scénario ouvre l’unique départ dont le siège se nomme Biskra, attend une paire `/lieu`–`/plan` cohérente et exige cellule et tick égaux dans les deux lectures. Il recalcule indépendamment #784 et #787, puis compare nombre projeté, métiers, trajets accessibles et objets posés au bilan du composant ; au moins trois passants et un trajet doivent être visibles. Contre-épreuve C : la commande de SC3 injecte une discordance de tick entre les deux lectures ; aucune nouvelle racine ne doit être appliquée. Accepter cette paire, mélanger ses effectifs et son plan, ou garder une mesure vide fait échouer le scénario.

SC3 — Une actualisation remplace, elle n’empile pas. Commandes : P, puis C dans un dossier neuf :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 788 -forgeSeed 0 -forgeTicks 0 -forgeCaptures '3d/unity/Temp/lot788-anciens' -forge788GarderAnciens -logFile '3d/unity/Temp/lot788-anciens.log'
```
P présente deux fois la même paire cohérente : la racine et ses identifiants restent inchangés, sans doublon. Elle présente ensuite une paire cohérente de contrôle au tick suivant avec un bourg vide : après une image, tous les anciens identifiants ont disparu, zéro passant et une racine vide sont déclarés. Une paire cohérente au tick suivant, reprenant les lectures réelles, rétablit enfin la foule pour la photo. C conserve volontairement une copie des anciens objets avant l’application du bourg vide : le même contrôle doit sortir non zéro après avoir écrit son image et son rapport. Contre-épreuves : détruire après avoir posé, conserver un ancien métier, doubler au même tick, transformer zéro en absence ou laisser C sortir zéro refuse la livraison.

SC4 — La marche et la rue se voient, avec le budget tenu. Commandes : P, C, `git diff --check`, `git diff --name-only`, `git diff --numstat` et `git ls-files --others --exclude-standard`. Ouvrir soi-même les deux PNG et les deux rapports JSON : P montre une rue entière de Biskra avec au moins trois civils entiers, espacés, orientés le long de la chaussée et dans des poses différentes ; aucun ne flotte ni traverse directement un virage. Le rapport porte cellule, ticks des deux lectures, effectifs projetés et posés par métier, références de trajet, objets avant/après et passants visibles. C montre l’empilement artificiel et le rapport nomme les anciens objets. Contre-épreuve : cadrage sans rue, civils immobiles, hors sol, tous superposés, rapport sans compte mesuré, chemin supplémentaire ou diff total supérieur ou égal à 300 refuse la livraison.

## Hors périmètre
Le moteur, `MODELE.md`, le service et ses contrats ; les calculs de #784 et #787, l’import, le VAT et le shader de #786 ; emploi, domicile, horaire, collision, évitement, carrefours, entrée dans les bâtiments, passants individuels persistants ou choix d’un métier. Pas de panneau, de son, d’optimisation ou de plafond de foule : les 60 images par seconde de la capitale dense appartiennent à #422. Aucun test existant n’est modifié ou assoupli. Tout autre chemin que ceux du Périmètre est interdit.

## Photo
`Lot788.cs` expose `[ScenarioDeCapture(788, "rue-de-biskra-vivante")]`. Il ouvre Biskra sur le vrai service, attend la paire cohérente et le remplacement vérifiés par SC2 et SC3, choisit une rue servie portant au moins trois passants, puis place `DesertCityCamera` de trois quarts à hauteur de rue pour montrer la chaussée, ses virages ou sa destination et les civils entiers. Il attend que leurs positions et phases diffèrent, exige au moins trois rendus de passants dans le champ et écrit `lot788-rapport.json`. Toute image ou rapport antérieur dans le dossier fait échouer le scénario.

Photo, commande P complète :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 788 -forgeSeed 0 -forgeTicks 0 -forgeCaptures '3d/unity/Temp/lot788-photo' -logFile '3d/unity/Temp/lot788-photo.log'
```
Contre-épreuve, commande C complète :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 788 -forgeSeed 0 -forgeTicks 0 -forgeCaptures '3d/unity/Temp/lot788-anciens' -forge788GarderAnciens -logFile '3d/unity/Temp/lot788-anciens.log'
```
P sort 0 et donne la photo du lot, car elle a le moins de drapeaux. C sort non zéro seulement après avoir écrit sa PNG et `lot788-rapport.json`. Joindre au compte rendu les deux PNG, les deux rapports JSON et les deux journaux.
