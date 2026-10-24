# Lot #779 — Les maisons habitées fument et s’éclairent
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Une maison de la capitale peut montrer une fumée quand elle est habitée et dispose de nourriture dans son bourg, et une lumière du soir quand elle est habitée, d’après les lectures du monde.

## Le joueur
Le joueur qui entre dans sa capitale et y marche voit des maisons habitées fumer et s’éclairer le soir ; il sent que sa ville dépend de ses habitants et de ses vivres. Cela rapproche le geste de J4, bâtir des maisons ou une route vers les champs en payant ses chantiers au grenier, de ses conséquences visibles. Ce sous-lot de #420 apporte le composant et sa démonstration à l’écran ; la suite de #420 le branchera aux publications et aux maisons de la capitale courante. La demande fournie ne contient pas de phrase « Le joueur » distincte : celle-ci en explicite le bénéfice selon `CAP.md`.

## Règle du monde
Sans objet : lot de vue, sans écriture ni nouvelle règle de simulation. Il lit les conventions de niveau 2 de `jeu/sim/MODELE.md`, « Les foyers par métier », « Les lieux d’une cellule, vue dérivée » → « Ce que porte un lieu », « Le panier de marchandises » → « Absence contre zéro » et « Le plan du bourg » → « Le plan de base ». La fumée représente une activité domestique possible, sans consommation calculée par Unity ; elle ne prouve pas que chaque foyer a reçu sa ration. L’heure est celle de la présentation, jamais un second temps du monde.

Dépend de : #778, contrat de lecture de l’étape 4 de la découpe de #420 : `BourgLu`, `OccupationLue` et leurs `Lecture<T>`. Créer dans `Forge.Pont` un composant public `EffetsDeMaison`, appelé explicitement avec ces lectures, une `LecturePlan` et l’heure de présentation. Il reçoit les références d’un vrai `ParticleSystem` de fumée et d’une vraie `Light` ponctuelle, enfants de la maison ; aucune recherche globale ni lecture HTTP. Son initialisation conserve l’intensité positive configurée de la lampe. Les effets sont éteints avant la première lecture.

L’identité configurée distingue une case de base `(rang, indice de foyer)` d’un bâtiment de geste `identifiant`, dans le `cell_id` du plan ; jamais les deux. La base correspond à `plan.Base.Maisons[rang]`, avec même nombre de foyers dans `occupation.Base` et indice dans ses bornes : toutes ces cases sont habitées, même si `Logement` est nul ou non calculé. Un bâtiment doit être une maison achevée présente dans le plan et dans `occupation.Batiments` ; elle est habitée si `Loges > 0`, vide si zéro, inconnue si −1. Ne pas additionner base et logement ni réaffecter les foyers dans la vue.

Avant d’activer un effet, exiger trois lectures présentes du même `cell_id`, rang 0 pour bourg et occupation, et même tick que le plan, y compris `TickLocal`. Une identité sans correspondance, des lectures absentes ou décalées, des références manquantes ou une heure non finie/hors de 12..22 éteignent les deux effets avec une cause publique explicite. Une occupation inconnue les éteint aussi ; aucune réussite précédente ne reste affichée. Une nourriture absente déclare son absence et interdit la fumée, sans supprimer une occupation connue ni sa lumière.

Fumée active exactement si maison habitée et `BourgLu.Stocks["nourriture"]` présent et strictement positif. Un zéro mesuré coupe la fumée sans déclarer une absence ; les autres marchandises et `DureeFaimTicks` ne remplacent jamais ce stock. Lumière indépendante du stock : facteur visuel `Mathf.InverseLerp(18.2f, 21f, heure)`, comme le soir de `DesertEnvironment`, multiplié par l’intensité initiale si habitée, zéro sinon ; lampe désactivée quand son intensité est nulle. Aucune déduction de l’heure depuis le tick ni changement de `DesertEnvironment`.

Couper la fumée arrête l’émission et efface les particules déjà présentes (`StopEmittingAndClear`). Désactiver ou détruire le composant éteint ses effets. Réappliquer le même état ne crée ni objet ni matériau et ne relance pas une fumée déjà active ; une nouvelle lecture valide rétablit les effets. Le composant pilote exclusivement ses deux références, sans toucher aux matériaux partagés, aux autres maisons ni aux effets du décor.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/EffetsDeMaison.cs
3d/unity/Assets/ForgeLocal3D/Pont/EffetsDeMaison.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/KitDesBatimentsTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot779.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot779.cs.meta
docs/briefs/779-les-maisons-habitees-fument-et-seclairent.md

## Conditions de succès
Depuis la racine sur le PC Windows, éditeur fermé, la commande `TESTS` est ce lancement PowerShell, attendu jusqu’à sa fin, sans `-quit` :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot779.xml" -logFile "$env:TEMP\lot779-tests.log"
```
Exiger sortie 0, XML neuf sans échec et nouveaux cas effectivement exécutés. Ajouter les cas dans `KitDesBatimentsTests.cs`, qui porte les invariants des vrais objets de maison ; aucun cas, témoin ou aide existant ne change. Prouver leur rouge avant le composant, éventuellement à la compilation tant que l’API manque.

SC1 — **L’activité atteint les objets.** Commande : `TESTS`. Sur des instances du kit avec de vrais enfants `ParticleSystem` et `Light`, couvrir une case habitée d’un îlot de plusieurs foyers, une maison bâtie partiellement logée et une maison bâtie vide, aux heures 12, 18.2, 19.6 et 21. Vérifier émission, particules après simulation explicite, lampe activée et intensité attendue ; à 19.6 elle vaut la moitié de l’intensité configurée. Contre-épreuves : composant sans effet, maison vide allumée ou lumière toujours active font rougir les assertions sur les composants, même si un booléen interne paraît correct.

SC2 — **Le panier n’invente ni faim ni lumière.** Commande : `TESTS`. Pour la même maison habitée au soir, appliquer nourriture positive, zéro puis clé absente ; garder une autre marchandise positive. Seule la première produit des particules, les deux suivantes les effacent ; seule l’absence de clé a un diagnostic d’absence alimentaire. La lampe reste identique. Tester nourriture positive avec faim locale positive, puis zéro avec faim locale nulle. Contre-épreuves : utiliser un autre stock, conditionner la fumée à la faim nulle ou éteindre la lampe avec la nourriture fait échouer ces cas.

SC3 — **Occupation et publications restent exactes.** Commande : `TESTS`. Cas paramétrés : base avec logement nul puis −1, maison bâtie à −1, chantier, atelier, rang/indice/identifiant introuvable, compte de base différent, lecture absente, cellule différente, tick différent dans chacune des trois lectures et tick local différent. Seule la base correctement correspondante reste habitée malgré l’absence de logement. Ajouter références manquantes et heure invalide. Après un succès, chaque refus coupe les deux objets et nomme sa cause ; une lecture rétablie les rallume. Contre-épreuves : traiter −1 comme un logé, fusionner deux jours ou conserver les anciennes particules fait rougir.

SC4 — **Les effets restent locaux et stables.** Commande : `TESTS`. Réappliquer dix fois un état actif conserve références, nombre d’enfants et intensité ; une autre maison témoin garde ses réglages. Désactiver puis détruire le composant éteint sa lampe et vide sa fumée, sans détruire la maison ou les références fournies. Contre-épreuves : multiplier l’intensité courante à chaque appel, créer des enfants à chaque lecture ou laisser une fumée après désactivation fait échouer les mêmes contrôles.

SC5 — **La démonstration se photographie.** Commande `PHOTO`, avec rendu, sans `-nographics` ni `-quit` :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 779 -forgeCaptures "$env:TEMP\lot779-captures" -logFile "$env:TEMP\lot779-photo.log"
```
Exiger sortie 0, les deux PNG neufs décrits ci-dessous et leurs traces `CAPTURE_SCENARIO_OK`. Le scénario vérifie des maisons, particules et lampes réellement présentes dans le champ ; zéro témoin échoue. Ouvrir soi-même les deux images et vérifier fumée lisible, façades visibles et lumière perceptible. Contre-épreuves : enlever le composant ou ses références fait échouer le scénario ; une image sans fumée visible ou sans différence de lumière refuse la photo même avec tests verts.

SC6 — **Les acquis et la taille tiennent.** Commandes : `TESTS`, `git diff --check`, `git diff --name-only`, `git diff --numstat` et `git ls-files --others --exclude-standard`. Garder tous les anciens tests, notamment les neuf pièces du kit, les six maisons en terre et les lectures de logement de `ClientLieuTests`. Compter fichiers neufs, métadonnées et brief : moins de 300 lignes ajoutées et supprimées ; budget 285, environ 95 de composant, 65 de tests, 42 de capture, 14 de métadonnées et 69 de brief. Contre-épreuves : ancien test rouge ou assoupli, chemin non autorisé ou total ≥ 300 interdit la livraison.

## Hors périmètre
Tout autre chemin est interdit. Aucun changement du moteur, de ses constantes, du service, des contrats ou des lecteurs. Aucune consommation, redistribution alimentaire, affectation de foyers ou nouvelle horloge. Pas de branchement automatique dans la capitale, de modification de scène ou prefab enregistré, de nouvel asset, de panneau, d’étal, de passant ou d’optimisation globale ; ces suites de #420 restent séparées. Aucun test existant modifié ou assoupli.

## Photo
`Lot779.cs` expose deux méthodes `static IEnumerator ...(Camera camera)` avec `[ScenarioDeCapture(779, "01-maisons-le-jour")]` et `[ScenarioDeCapture(779, "02-maisons-le-soir")]`. Elles montent une démonstration temporaire avec de vraies maisons du kit, les deux effets configurés et le composant livré : case de base habitée, maison bâtie occupée et maison bâtie vide. Réutiliser la même préparation entre scénarios. Des témoins typés explicites du contrat #778, avec plan, cellule et tick concordants, pilotent cette démonstration ; ce n’est pas une preuve du branchement au service réel, réservé à la suite de #420.

À 12 h, nourriture positive : les deux maisons habitées fument, aucune lampe n’éclaire ; à 21 h, même état : elles fument et leurs lampes chaudes éclairent les façades, tandis que la maison vide reste sans effet. Poser les fumées au-dessus des toits, les lampes près des ouvertures ; réutiliser les matériaux déjà disponibles, sans asset neuf. Placer la caméra par `DesertCityCamera.Poser` en vue rapprochée des trois façades et des toits, appliquer l’heure à `DesertEnvironment` pour l’ambiance, puis laisser ou simuler les particules avant la photo. Vérifier la présence des trois témoins et de leurs effets dans le champ, et échouer explicitement si kit, matériau ou caméra manque. Les captures sortent sous le dossier temporaire de `PHOTO`, jamais dans git.
