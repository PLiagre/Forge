# Lot #609 — Le pont lit les terres de départ
Jalon : J3 · Machine : pc · Taille prévue : 290 lignes

## But
Le pont Unity sait lire chaque terre proposée par `/departs`, avec son identité, son siège, ses habitants, son suzerain et ses voisins, ou déclarer pourquoi la réponse est illisible.

## Le joueur
Lot de fond, découpé de #404 : il prépare « le joueur choisit sa terre sur la carte », geste du lot parent inscrit au J3 de `CAP.md`. Le joueur pourra reconnaître sa maison, son siège et les puissances voisines avant de choisir le domaine dont il gouvernera les quatre lieux. L'affichage et le choix dans la suite de #404 rendront ces fiches visibles ; #405 lui permettra ensuite de régler sa part et de rouvrir son grenier. Ce lecteur prépare donc la décision de J3 : remplir son grenier pour ses projets ou laisser assez de grain à ses gens pour les garder. À lui seul, il n'ajoute aucun écran.

## Règle du monde
Sans objet : lecteur de vue, sans changement du monde ni de son niveau de fidélité. Il respecte `jeu/sim/MODELE.md`, « Les seigneuries de départ, vue dérivée » et « La carte et les terres servies, vue dérivée » : chaque requête relit les fiches au tick servi, sans recalcul local ni cache des habitants. `habitants` mesure la cellule du siège, pas la population du siège ou des quatre lieux du joueur ; `cell_id` reste la seule clé spatiale. `suzerain` désigne la puissance, distincte de `maison_du_suzerain`. Dépend de : #402 (service) et #520/#521 (types et aides du pont), présents dans le chantier.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientDeparts.cs
3d/unity/Assets/ForgeLocal3D/Pont/ClientDeparts.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientDepartsTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientDepartsTests.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/departs-graine0-tick3.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/departs-graine0-tick3.json.meta
jeu/sim/tests/test_carte_servie.py

Tout autre chemin est interdit. Le seul ajout Python est un test dans le fichier qui porte déjà l'invariant de `/departs` ; aucune ligne existante n'est changée. Les `.meta` sont générés par Unity, avec des GUID uniques. Budget : environ 85 lignes de client, 105 de tests C#, 15 de test Python, 15 de fixture et métadonnées, 70 de brief ; réutiliser les aides existantes et paramétrer les cas de faute.

## Conditions de succès
**SC1 — la fixture vient du vrai service.** Commande : `python3 -m pytest jeu/sim/tests/test_carte_servie.py -q -k departs_fige_du_pont` (Windows : `py -m pytest` avec les mêmes arguments). Le codeur prélève une fois les octets de `GET /departs` sur le vrai service, graine 0, horloge arrêtée, après `POST /tick?n=3`, sans reformatage ni fin de ligne ajoutée. Ajouter `test_departs_fige_du_pont` : il lit cette fixture depuis la racine du dépôt, exige une liste non vide, puis refait ces requêtes avec `lancer_service(0)` et `requete_service`. Il exige un statut 200 et l'égalité exacte des octets ; il n'écrit jamais la fixture. Une seconde lecture au même tick est identique ; après `POST /tick?n=1`, les habitants d'au moins une fiche diffèrent. La commande recueille exactement un test. Contre-épreuve : changer un habitant ou ajouter une fin de ligne à la fixture fait échouer la comparaison ; restaurer les octets la rétablit.

Réponse vérifiée au vrai service dans ce chantier : 6 701 octets ; SHA-256 `493b98faf751b3f0dfd2eefb21b5a896a6853795077c305db6b2e6fd0b8d6776` ; `tick=3`, date `(1400, 4)`. Ce relevé décrit la provenance ; le test compare au service, sans prendre ce hash pour référence.

**SC2 — toutes les fiches et leurs voisins sont relus exactement.** Commande PC, Unity 6000.0.43f1 indiqué dans `ProjectVersion.txt` : `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults <temp>/pont.xml -logFile <temp>/pont.log` (sans `-quit`). Exiger une sortie 0, un XML sans échec et des cas `ClientDepartsTests` effectivement exécutés ; zéro cas est un échec. Un `HttpListener` local sur port libre sert la fixture relue du disque et retient la requête : `GET /departs`, sans paramètres ni corps.

Dans `Forge.Pont`, créer `ClientDeparts : IDisposable`, constructeur `(int port, TimeSpan delai)`, et `Lecture<DepartsLus> Lire()`. Réutiliser `ServiceLocal.Demander`, `Lecture<T>`, `DateDuMonde`, `IdentiteDeCarte` et les aides de lecture existantes, sans modifier leurs fichiers. `DepartsLus` expose `Tick`, `Date`, `Fiches` ; `FicheDeDepart` expose `Id`, `Nom`, `Maison` (texte), `Siege` (`Nom`, `Lat`, `Lon` en degrés), `CellId`, `Habitants`, `Suzerain` (`Id`, `Nom`, ou null), `Voisins`. Chaque voisin expose `CellId`, `Habitants`, `Puissance` (`Id`, `Nom`, ou null). Types immuables et listes copiées en collections de lecture seule ; l'ordre servi est conservé. Les champs supplémentaires du service sont ignorés.

Le test parcourt toutes les fiches et tous leurs voisins : pour chacun des champs exposés, il compare exactement à la valeur correspondante du document de fixture lu avec `LecteurJson`, sans appeler le lecteur de fiches pour fabriquer ses attentes ; il compare aussi les tailles des listes. Il exige les six identifiants 1 à 6 et les cellules `[10430,10465,10340,10334,10337,10103]`. Il vérifie notamment Morée : maison « Paléologue », siège `(Mistra,37.074,22.367)`, 80 919 habitants, suzerain `(25,Byzance)` ; Zab : maison « Banou Mozni », siège `(Biskra,34.85,5.73)`, 3 459 habitants, suzerain `(35,Hafsides)`, voisin 10087 avec puissance nulle. Contre-épreuve : lire le suzerain dans `maison_du_suzerain`, ou omettre une fiche ou un voisin, fait échouer ces comparaisons.

**SC3 — une clé fautive rend une absence qui dit sa cause.** Commande : `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults <temp>/pont.xml -logFile <temp>/pont.log`. Une faute refuse toute la réponse : `Presente=false`, `Donnees=null`, `Absence` commence par `departs : ` et indique le chemin exact et la cause (clé absente ou valeur attendue). Aucun résultat partiel ni zéro de remplacement. Les nombres entiers utilisent la garde existante : sous 2^53, non négatifs ; année et jour positifs. Textes non vides hors espaces ; coordonnées finies, latitude dans [-90,90], longitude dans [-180,180]. `departs` est un tableau non vide d'objets aux `id` distincts ; `voisins` est un tableau d'objets, éventuellement vide. Les clés `suzerain` et `puissance` sont présentes, avec null ou une identité valide.

Ajouter des cas paramétrés dérivés de la fixture. Toute mutation vérifie qu'elle a changé le témoin à l'endroit voulu et, hors JSON coupé, qu'il reste un JSON valide. Couvrir au moins :

| Faute injectée seule | Chemin et cause attendus |
|---|---|
| Retirer tour à tour `tick`, `date`, `departs` | La clé retirée, « clé absente » |
| Remplacer `departs` par `[]`, puis par null | `departs`, tableau non vide attendu |
| Dupliquer l'id de Bar dans la fiche Wurtemberg | `departs[1].id`, « déjà lu » |
| Retirer tour à tour `id`, `nom`, `maison`, `siege`, `cell_id`, `habitants`, `suzerain`, `voisins` de Morée | `departs[2].<clé>`, « clé absente » |
| Nom blanc ; maison remplacée par un objet | `departs[2].nom` ; `departs[2].maison`, texte non vide attendu |
| Siège nul ; nom du siège absent ; latitude 91 ; longitude en texte | `departs[2].siege` et les sous-clés respectives, avec la cause |
| Habitants négatifs, puis décimaux, puis booléens ; cellule négative | `departs[2].habitants` ; `departs[2].cell_id`, entier attendu |
| Suzerain remplacé par 25 ; son id en texte ; son nom absent | `departs[2].suzerain`, puis `.id` et `.nom`, avec la cause |
| Voisins nuls ; habitants du premier voisin négatifs ; sa cellule absente | `departs[2].voisins`, puis `[0].habitants` et `[0].cell_id` |
| Retirer la puissance nulle du voisin 10087 du Zab | `departs[5].voisins[1].puissance`, « clé absente » |
| Remplacer la puissance d'un voisin par un texte | Le chemin de sa puissance, null ou objet attendu |
| Jour de l'année à 0 ; réponse JSON coupée | `date.jour_de_l_annee`, entier positif attendu ; « JSON invalide » |

Un cas valide remplace le suzerain de Morée par null, ses voisins par `[]` et ses habitants par 0 : ces valeurs déclarées restent lisibles. Contre-épreuve : accepter une clé absente en lui donnant null ou 0, ou accepter une réponse partielle après la faute d'un voisin, fait rougir les cas correspondants. Écrire et constater ces tests rouges avant d'implémenter leur lecture, puis obtenir le vert ; ne modifier aucun test existant.

**SC4 — le service lent ou absent ne produit aucune fiche inventée.** Commande : `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults <temp>/pont.xml -logFile <temp>/pont.log`. Exposer `DelaiMinimal=TimeSpan.FromSeconds(10)` : `/departs` peut initialiser la carte à sa première lecture. Refuser avant toute requête un délai inférieur, infini ou dépassant la capacité de `ServiceLocal`, et un port hors de 1..65535. La fixture reçue après 2 500 ms reste présente ; un service muet rend « délai dépassé », un port sans service « service absent », un statut 500 conserve le code et le corps reçu dans l'absence. Contre-épreuve : un délai de 2 s fait échouer le cas lent ; rendre une liste vide à la place d'une absence fait échouer les assertions d'état.

**SC5 — les invariants existants restent verts.** Commandes : `python3 -m pytest jeu -q` (Windows : `py -m pytest jeu -q`) et la commande Unity de SC2 pour toute l'assemblée `Forge.Pont.Tests`. Aucun test existant retiré, renommé ou assoupli ; le relevé des cas Unity se compare à celui d'avant le lot. Le diff total reste strictement sous 300 lignes et ne touche que le périmètre et ce brief. Contre-épreuve : retirer le Zab de la réponse du service fait échouer `test_departs_zab` ; le lecteur ne doit pas contourner cet invariant avec une liste locale.

## Hors périmètre
Affichage des sièges et des fiches, clic de choix, dépôt de `choisir_depart`, changement du monde, de ses règles ou de ses tests existants ; lecture de `/maison` ou extension de `/monde` ; projection des coordonnées, identité spatiale supplémentaire, données recalculées, cache ou lecture asynchrone. Pas de lecture des champs `religion`, `source`, `production_kg_par_tick`, `maison_du_suzerain`, `cellules_du_suzerain`, `habitants_du_suzerain` dans ce client. Aucun changement d'assemblage, de dépendance, de scène, du service ou des aides partagées. Les suites de #404 portent l'affichage et le choix ; #405 porte les gestes de gouvernement.

## Photo
Sans objet : ce lot d'outil ne change rien de ce qu'on voit à l'écran ; aucune vue n'appelle encore le lecteur. La suite de #404 qui affiche les sièges et leur fiche portera son scénario de capture Unity. Aucun scénario `Lot609.cs` ni panneau de démonstration n'est ajouté ici.
