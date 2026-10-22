# Lot #778 — Unity lit le panier, la faim et les maisons habitées
Jalon : J4 · Machine : pc · Taille prévue : 290 lignes

## But
Unity sait lire le panier et la faim du bourg ainsi que les maisons habitées, avec leur jour observé et leurs absences déclarées, pour préparer une capitale qui vit d'après le monde.

## Le joueur
Ce lot de fond prépare le geste de J4 : entrer dans sa capitale et choisir entre une route vers les champs, des maisons ou d'autres chantiers. Le joueur verra les étals suivre la faim réelle du bourg et les fumées et lumières suivre ses maisons habitées ; il pourra sentir les conséquences de ses choix dans sa ville. La suite de #420 qui branche ces effets au rendu rendra ces lectures visibles ; #778 seul ne change pas l'écran. La demande fournie n'a pas de phrase « Le joueur » distincte : celle-ci explicite son bénéfice selon `CAP.md`.

## Règle du monde
Sans objet : lecture de vue, sans règle ni écriture du monde. Les données de niveau 2 déjà décidées viennent de `jeu/sim/MODELE.md`, « Les lieux d'une cellule, vue dérivée » → « Ce que porte un lieu », « Ce que veut dire « affamée » », « Le panier de marchandises » → « Absence contre zéro », « Les foyers par métier » et « Le plan du bourg » → « Le plan de base ».

Dépend de : #776, qui apporte `/occupation` après #775 et son extension `/lieu?cell=X&bourg=1`. Les « données de 1 et 2 » de la demande sont ces deux contrats. Conserver les conventions livrées : maisons de 1400 toutes habitées, artisans logés dans les seules maisons bâties, sans addition des deux comptes. Ni le panier restant ni la faim cellulaire ne remplacent la faim locale.

Ajouter un lecteur public `ClientVieDuBourg`, dans `Forge.Pont`, avec deux lectures indépendantes `LireBourg(cellId)` et `LireOccupation(cellId)`, fondées sur `ServiceLocal` et `Lecture<T>` existants. Leurs données typées sont immuables, collections copiées en lecture seule. Ne modifier ni `ClientLieu.Lire`, ni ses modèles ou ses gardes, ni le transport commun.

- `LireBourg` demande exactement `GET /lieu?cell=X&bourg=1` et expose `cell_id`, tick/date de la réponse et le bloc `bourg` : rang 0, population, toutes les marchandises avec leurs valeurs exactes, `duree_faim_ticks` et tick local égal au tick racine. Aucun arrondi, complément de panier ou repli sur `lieux`, `stocks` ou `hunger_ticks` cellulaires. Une marchandise absente reste sans clé ; une valeur zéro est conservée.
- `LireOccupation` demande exactement `GET /occupation?cell=X` et expose cellule, rang 0, tick/date, `base` sous forme de couples rang/foyers, `batiments` sous forme de triplets identifiant/capacité/logés et `logement`. Conserver les ordres servis ; exiger les rangs de base successifs depuis zéro, les identifiants bâtis strictement croissants, foyers et capacités positifs. Pour des comptes calculés, chaque logé est entre zéro et sa capacité ; sommes des capacités et des logés égales aux totaux de `logement`. Ne recalculer ni capacité depuis une surface, ni affectation de familles.
- `logement:null` est une absence déclarée, accompagnée d'une raison exposée ; il exige une liste `batiments` vide, sans effacer `base`. `loges:-1` et `sans_logis:-1` ensemble déclarent les métiers non calculés : conserver ces valeurs et une raison, ainsi que les capacités et les `loges:-1` de chaque bâtiment. Un mélange de comptes calculés et non calculés est refusé. Des listes vides et des zéros réellement servis restent présents.
- Les clés du contrat demandé sont obligatoires, y compris celles dont la valeur peut être nulle. Cellule différente, rang autre que zéro, clé absente, mauvais type, entier fractionnaire ou hors des bornes du contrat, nombre non fini, stock négatif ou incohérence précitée refusent toute cette lecture avec données nulles et cause qui nomme le chemin fautif. Entiers sous 2^53, comptes et ticks non négatifs sauf les sentinelles prévues ; date positive selon `ServiceLocal.Date`.
- Les deux résultats portent leur propre tick/date. Ils ne forment pas un état commun garanti : aucune fusion, attente de tick ni donnée antérieure conservée ici. Les futurs consommateurs devront comparer cellule et tick avant de les associer au plan. Un échec HTTP ou réseau conserve sa cause explicite et ne restitue jamais la dernière réussite.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientVieDuBourg.cs
3d/unity/Assets/ForgeLocal3D/Pont/ClientVieDuBourg.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientLieuTests.cs
docs/briefs/778-unity-lit-le-panier-la-faim-et-les-maisons-habit.md

## Conditions de succès
Sur le PC Windows, depuis la racine, Unity 6000.0.43f1, éditeur fermé. La commande `TESTS` désigne le lancement PowerShell suivant, attendu jusqu'à sa fin, sans `-quit` :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot778.xml" -logFile "$env:TEMP\lot778.log"
```
Chaque passage exige sortie 0 et XML neuf sans échec, avec les nouveaux cas effectivement exécutés ; zéro cas ou cas ignoré échoue. Ajouter seulement des tests et leurs aides dans `ClientLieuTests.cs`, qui porte déjà les invariants de lecture des stocks, des foyers et du logement. Écrire ces cas avant le lecteur et constater leur rouge, éventuellement à la compilation tant que l'API manque. Employer des témoins JSON littéraux et le serveur HTTP local des tests ; les nouvelles aides ne changent pas les aides existantes.

SC1 — **Le bourg est relu exactement.** Commande : `TESTS`. Ajouter un témoin habité à panier fractionnaire, marchandise future et zéro explicite, dont les chiffres cellulaires diffèrent du bloc local ; vérifier toutes les valeurs, cellule, rang, tick/date et requête HTTP exacte. Couvrir faim locale positive avec surplus cellulaire, faim locale nulle avec faim cellulaire positive, puis panier alimentaire final nul et faim locale nulle. Retirer une marchandise conserve son absence. Contre-épreuves : remplacer le panier local par le cellulaire, arrondir une quantité ou déduire la faim du stock fait échouer ces comparaisons.

SC2 — **Les maisons gardent leurs comptes servis.** Commande : `TESTS`. Témoin non vide : base comprenant un îlot de plusieurs foyers et trois maisons bâties, occupée, partiellement occupée et vide. Vérifier chaque rang, identifiant, capacité et logé, l'ordre et le logement exact ; les familles de base ne s'ajoutent pas au logement. Ajouter séparément base habitée avec `logement:null` et aucun bâtiment, comptes non calculés avec capacités présentes, puis cellule valide vide. Contre-épreuves : remplacer `-1` par zéro, remplir la maison vide, compter un îlot pour un foyer ou additionner la base au logement fait rougir les mêmes assertions.

SC3 — **Chaque faute a une cause, sans résultat partiel.** Commande : `TESTS`. Nouveaux cas paramétrés retirant une à une les clés des deux contrats et altérant types, rangs, cellule, tick local, comptes et sommes. Couvrir doublon de rang ou d'identifiant, `loges > capacite`, sentinelles mélangées, stock négatif, entier négatif/fractionnaire/≥ 2^53 et JSON invalide. Chaque mutation prouve qu'elle a changé le témoin ; JSON valide hors du cas dédié. Exiger absence, données nulles et chemin précis, ou diagnostic JSON. Contre-épreuve : le témoin intact et les états déclarés de SC2 passent ; aucune absence ne devient une liste vide ou un zéro.

SC4 — **Les jours et les échecs ne se masquent pas.** Commande : `TESTS`. Servir successivement deux publications aux valeurs et ticks différents pour chacune des lectures, puis 404, 500 avec corps distinct, 302, port fermé et délai dépassé. Vérifier les nouvelles valeurs et dates, puis données nulles et cause de chaque échec ; le 302 n'est pas suivi. Relire un succès après un échec. Deux routes servies à des ticks différents gardent chacune leur tick ; aucune cohérence n'est inventée. Contre-épreuves : conserver le premier résultat, remplacer le tick ou masquer l'erreur par les données précédentes fait échouer ces cas.

SC5 — **Les preuves historiques et le budget restent intacts.** Commandes : `TESTS`, `git diff --check`, `git diff --numstat` et `git ls-files --others --exclude-standard`. Tous les anciens cas passent sans retouche, notamment `UnLieuServiEstReluExactement`, `UneMarchandiseNouvellePasseEtUneAbsenteNEstPasInventee`, `LeLogementEstReluTelQuel` (son témoin volontairement incohérent doit rester accepté par l'ancien lecteur), `DesFoyersNonCalculesOuAbsentsSeDeclarent` et les cas de population locale. Compter aussi les fichiers neufs et le brief : diff total strictement inférieur à 300 lignes ; viser environ 120 de lecteur, 95 de tests, 11 de métadonnées et 64 de brief. Contre-épreuves : un ancien cas rouge, une assertion ou aide existante modifiée, un chemin non autorisé ou un total ≥ 300 refuse la livraison.

## Hors périmètre
Tout autre chemin est interdit. Aucun changement de simulation, service Python, contrats, photographie, fichiers JSON figés, plan, logement historique, population ou faim. Pas de nouvelle règle du monde, de calcul de nourriture ou d'affectation de foyers dans Unity. Aucun branchement à la scène, panneau, fumée, étal, lumière, passant ou horloge ; aucune fusion de réponses HTTP en une publication supposée commune. Aucun test existant réécrit ou assoupli.

## Photo
sans objet : ce lot ajoute uniquement des lectures réseau typées et leurs tests, sans changement de ce qu'on voit à l'écran. La suite de #420 qui branche étals, fumées et lumières prendra la capture de la capitale vivante avec ces données ; aucun scénario de capture n'est nécessaire dans #778.
