# Lot #780 — Les étals montrent le panier du bourg
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
Les étals peuvent montrer une garniture proportionnelle aux marchandises réellement servies du bourg, jusqu'au comptoir alimentaire vide quand ses vivres sont épuisés.

## Le joueur
Le joueur qui entre dans sa capitale et y marche voit ses étals se garnir ou se vider selon les stocks du bourg ; il sent les conséquences d'une route vers les champs négligée au profit d'autres chantiers. Ce lot rapproche l'arbitrage de J4 entre ravitaillement et construction de son effet visible dans la ville, et prépare sa contre-épreuve « un étal plein dans un bourg affamé ». Il apporte le composant autonome et sa démonstration ; la suite de #420 le branchera à la capitale courante. La demande fournie n'a pas de phrase « Le joueur » distincte : celle-ci en explicite le bénéfice selon `CAP.md`.

## Règle du monde
Sans objet : lot de vue, sans écriture ni nouvelle règle du monde. Les stocks et la faim de niveau 2 viennent de `jeu/sim/MODELE.md`, « Le panier de marchandises » → « Absence contre zéro », « Ce que veut dire « affamée » » et « Les lieux d'une cellule, vue dérivée » → « Ce que porte un lieu ». Le volume montré est une représentation du stock local, sans transfert, consommation ni estimation de ration dans Unity.

Dépend de : #778, étape 4 de la découpe de #420, qui livre `Lecture<BourgLu>`, ses `Stocks`, `CellId`, `Rang`, `Tick`, `TickLocal` et `DureeFaimTicks`. L'étape 5 est #779 : aucun de ses fichiers n'est modifié, aucun appel à `EffetsDeMaison` ni attente de #779. Créer dans `Forge.Pont` un composant public `EtalDuBourg`, configuré explicitement avec `cell_id`, clé de marchandise, référence visuelle positive en kg et un enfant de garniture ; `Appliquer(Lecture<BourgLu>, LecturePlan)` reçoit les lectures, sans HTTP ni recherche globale.

La garniture possède un pivot à sa base et au moins un vrai `MeshRenderer` enfant ; sa forme et son échelle initiales représentent le plein. Le composant conserve cette échelle à la configuration, masque la garniture avant toute lecture, puis multiplie seulement sa hauteur par `min(1, stock_kg / reference_kg)`. Calculer le rapport en double avant conversion. Zéro masque toute la garniture ; un stock positif fractionnaire reste proportionnel, le dépassement sature au plein. Le comptoir, son auvent et les contenants vides restent visibles. La référence est un réglage de représentation, jamais une capacité économique ni un besoin alimentaire.

Lire exclusivement la clé exacte dans `BourgLu.Stocks`, sans alias ni marchandise de remplacement. Une clé absente masque la garniture avec une cause publique nommant la marchandise ; zéro est une mesure réussie sans cause d'absence. Une marchandise nouvelle fonctionne dès qu'un étal la désigne explicitement. La faim locale reste indépendante : elle ne remplit ni ne vide artificiellement le stock montré. Nourriture nulle avec faim nulle donne un étal vide sans annoncer de famine ; nourriture nulle avec faim positive donne aussi un étal vide, même si une autre marchandise reste disponible. Aucun repli sur les stocks cellulaires, les champs ou le grenier.

Avant tout affichage, exiger composant actif, configuration valide, lectures présentes, même cellule configurée, rang 0, `bourg.Tick == bourg.TickLocal == plan.Tick`. Une absence, un décalage ou une référence manquante masque l'ancienne garniture avec sa cause ; aucune réussite antérieure ne persiste. Refuser clé vide, référence nulle/négative/non finie, garniture hors du composant ou sans géométrie. Désactivation et destruction masquent la garniture sans détruire les objets fournis. Réappliquer le même état ne crée rien, ne multiplie pas l'échelle déjà réduite et ne touche aucun autre étal ni matériau partagé ; une lecture valide rétablit le rendu.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/EtalDuBourg.cs
3d/unity/Assets/ForgeLocal3D/Pont/EtalDuBourg.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/EtalDuBourgTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/EtalDuBourgTests.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot780.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot780.cs.meta
docs/briefs/780-les-etals-montrent-le-panier-du-bourg.md

## Conditions de succès
Sur le PC Windows, depuis la racine, éditeur fermé, `TESTS` désigne ce lancement PowerShell, attendu jusqu'à sa fin, sans `-quit` :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot780.xml" -logFile "$env:TEMP\lot780-tests.log"
```
Exiger sortie 0, XML neuf sans échec et nouveaux cas effectivement exécutés ; zéro cas ou cas ignoré échoue. Écrire d'abord les cas de rendu dans `EtalDuBourgTests.cs`, nouveau fichier portant cet invariant neuf, et constater leur rouge, éventuellement à la compilation avant le composant. Aucun test, témoin ou aide existant ne change ; les invariants de lecture restent dans `ClientLieuTests.cs`.

SC1 — **Le stock atteint la géométrie.** Commande : `TESTS`. Sur un vrai comptoir et une garniture avec `MeshRenderer`, référence 100 kg, appliquer 100, 50, 12.5, 0 puis 200 kg. Vérifier visibilité effective, échelles attendues 1, 0.5, 0.125, masquée puis 1, largeur/profondeur et base inchangées ; le comptoir reste visible. Tester une échelle initiale non unitaire. Contre-épreuves : booléen interne seul, échelle constante, réduction de tout l'étal ou rapport arrondi font rougir les assertions sur les objets et leurs dimensions.

SC2 — **Chaque marchandise garde son sens.** Commande : `TESTS`. Deux étals distincts suivent nourriture et bois dans le même bourg. Couvrir nourriture zéro avec bois positif, clé alimentaire retirée, clé nouvelle configurée, puis nourriture positive ; vérifier le bois inchangé et la cause seulement pour l'absence. Croiser faim locale nulle et positive avec stocks nuls et positifs : à stock égal, même garniture. Contre-épreuves : somme du panier, alias alimentaire, remplissage minimal au zéro ou faim déduite du stock font échouer ces cas ; le dictionnaire reçu reste inchangé.

SC3 — **Une lecture douteuse ne conserve rien.** Commande : `TESTS`. Après un succès, couvrir lectures absentes, cellule différente dans chaque lecture, rang non nul, tick du plan décalé, tick local décalé et configurations invalides précitées. Chaque refus masque la géométrie et nomme sa cause, puis une lecture/configuration rétablie rend le plein. Réappliquer dix fois un demi-stock conserve dimensions, références et nombre d'objets ; désactiver puis détruire masque sans détruire comptoir ou garniture. Contre-épreuves : ancienne garniture persistante, échelle divisée à chaque appel ou altération d'un étal témoin font rougir.

SC4 — **Le rendu se photographie et se regarde.** Commande `PHOTO`, avec rendu, sans `-nographics` ni `-quit` :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 780 -forgeCaptures "$env:TEMP\lot780-captures" -logFile "$env:TEMP\lot780-photo.log"
```
Exiger sortie 0, les trois PNG neufs décrits ci-dessous et leurs traces `CAPTURE_SCENARIO_OK`. Le scénario vérifie des géométries effectivement visibles dans le champ, leur hauteur et les comptoirs ; aucun témoin est un échec. Ouvrir soi-même les trois images : plein, demi-stock et comptoir alimentaire nu doivent être lisibles au même cadrage. Contre-épreuves : retirer le composant ou ses références fait échouer le scénario ; garniture cachée par l'auvent, stock encore visible au zéro ou images indiscernables refusent la photo même avec tests verts.

SC5 — **Les acquis, l'autonomie et la taille tiennent.** Commandes : `TESTS`, `git diff --check`, `git diff --name-only`, `git diff --numstat` et `git ls-files --others --exclude-standard`. Tous les tests existants, notamment lectures du bourg et effets #779, passent inchangés. Compter aussi les fichiers neufs, métadonnées et brief : total ajouté et supprimé strictement inférieur à 300 lignes ; viser 270, environ 80 de composant, 65 de tests, 50 de capture, 6 de métadonnées et 69 de brief. Contre-épreuves : ancien test rouge ou assoupli, fichier partagé avec #779, chemin interdit ou total ≥ 300 refuse la livraison.

## Hors périmètre
Tout autre chemin est interdit. Aucun changement de simulation, consommation, faim, service, contrat, lecteur, plan ou horloge. Pas de prix, vente, affectation de marchandises aux foyers ou nouveau geste du joueur. Aucun branchement automatique dans la capitale, fumée, lumière, passant ou optimisation globale ; ces suites de #420 restent séparées. Pas de scène, prefab, matériau, maillage ou export Blender enregistré : les souks existants fusionnent comptoir et denrées dans leurs maillages, leur séparation n'entre pas dans ce lot. Aucun test existant réécrit ou assoupli.

## Photo
`Lot780.cs` expose trois méthodes `static IEnumerator ...(Camera camera)` marquées `[ScenarioDeCapture(780, "01-etals-pleins")]`, `[ScenarioDeCapture(780, "02-demi-stock")]` et `[ScenarioDeCapture(780, "03-bourg-affame")]`. Une préparation commune monte deux comptoirs temporaires sur un sol plat près de la ville, avec géométrie séparée des denrées et matériaux du projet : nourriture et bois, nommés explicitement dans le journal de capture. Des primitives assemblées sont permises ; aucun étal du décor déjà garni ne sert de témoin vide.

Les trois scénarios appellent le vrai composant sur des témoins typés explicites du contrat #778 : plan et bourg de même cellule et même tick, nourriture 100 puis 50 puis 0 kg, référence 100, faim locale 0 puis 0 puis positive ; bois positif identique aux trois passages. Ce montage montre le composant, sans prétendre prouver le branchement au service réel réservé à la suite de #420. La troisième image montre le comptoir alimentaire nu et le bois conservé, sans transformer toute pénurie alimentaire en disparition des autres marchandises. Placer la caméra avec `DesertCityCamera.Poser`, en vue rapprochée plongeante découvrant les comptoirs, conserver ce cadrage et laisser passer quelques images. Toute référence absente ou témoin hors champ lève une erreur ; conserver les PNG hors du dépôt et examiner soi-même les trois captures.
