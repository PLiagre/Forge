# Lot #610 — Le pont lit la fiche d'une maison
Jalon : J3 · Machine : pc · Taille prévue : 290 lignes

## But
Le pont Unity lit la maison demandée à `/maison?id=`, son nom, son siège et ses lieux tenus, avec des absences déclarées plutôt que des valeurs inventées.

## Le joueur
Lot de fond, découpé de #404 : il prépare le choix de sa terre sur la carte et la lecture de son domaine, pour savoir où il siège et quels lieux il gouvernera avant de décider combien leur prendre (J3). La demande porte sur « le nom, le siège (cellule, rang, nom, position sur la carte) et les lieux tenus ». Après ce lot, ces données sont accessibles au pont ; #404 les rendra visibles dans la fiche de choix sur la carte. Le joueur pourra y reconnaître sa maison et sa terre ; ce lecteur seul ne change encore rien à l'écran. Le service nécessaire est celui de #602, déjà présent dans ce chantier.

## Règle du monde
Sans objet : lecteur de vue, sans écriture dans le monde. Il suit `jeu/sim/MODELE.md`, « Les maisons servies, vue dérivée » et « Les lieux d’une cellule, vue dérivée » : l'identifiant de maison est une chaîne, chaque lieu est un couple `(cell_id, rang)`, et le point du siège vient du service. Aucune seconde clé spatiale, projection, recherche de siège ou génération de nom. Les noms historiques et plausibles gardent les niveaux 1 et 2 du service ; aucune règle ni constante du monde ne change.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientMaison.cs
3d/unity/Assets/ForgeLocal3D/Pont/ClientMaison.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientMaisonTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientMaisonTests.cs.meta

Dans `Forge.Pont`, ajouter `ClientMaison : IDisposable`, constructeur `(int port, TimeSpan delai)`, et `Lecture<MaisonLue> Lire(string identifiant)`. Réutiliser sans les modifier `ServiceLocal`, `Lecture<T>` et `PointCarte` : HTTP local, délai couvrant le corps, aucune redirection, préfixe d'absence `maison : `. Encoder l'identifiant avec `Uri.EscapeDataString` dans l'unique paramètre `id`. Une chaîne nulle ou vide hors espaces est refusée avant envoi par `ArgumentException` ; un identifiant inconnu reçoit l'absence du 404, sans exception ni ancienne fiche.

Types immuables dans ce seul fichier : `LieuTenu` porte `long CellId, Rang` ; `SiegeDeMaison` porte `long? CellId, Rang`, `string Nom`, `PointCarte? Position` ; `MaisonLue` porte `string Id, Nom`, `SiegeDeMaison Siege`, `IReadOnlyList<LieuTenu> Lieux`, `IReadOnlyDictionary<string, string> Absents`. Copier les collections et les exposer en lecture seule. `Nom` peut être nul uniquement avec sa raison ; le siège hors carte garde son nom mais ses deux nombres et sa position sont nuls. Les lieux restent dans l'ordre servi ; une liste vide est une mesure valide.

Exiger les clés `id`, `nom`, `siege`, `lieux`, `absents`, puis `siege.cell_id`, `siege.rang`, `siege.nom`, `siege.point` ; chaque lieu exige `cell_id` et `rang`. L'id doit égaler exactement celui demandé. Les textes présents et les raisons sont non vides hors espaces ; `absents` est un objet de raisons textuelles, conservées telles quelles, y compris `part` et `grenier`. Un `nom` nul exige `absents.nom`, et un nom présent ne peut pas porter cette raison. Le siège a soit ses deux entiers et son point, soit les trois valeurs nulles et une raison `absents.siege` ; une absence partielle ou une raison sur un siège présent refuse la fiche. `siege.nom` reste obligatoire et non nul dans les deux cas. Une clé manquante n'est jamais assimilée à une valeur nulle déclarée.

Entiers ≥ 0 strictement sous 2^53, coordonnées finies `siege.point.x_m` et `y_m`, relues exactement en mètres EPSG:3035. Les couples de lieux sont distincts ; le siège n'est pas obligé d'appartenir aux lieux tenus. Une seule faute refuse toute la réponse avec le chemin fautif, y compris dans le second lieu. Ignorer les champs supplémentaires : `sorte`, `suzerain`, `part`, `grenier`, `flux_30j`, `tick`, `date`, `latitude`, `longitude` ne sont pas interprétés ici.

## Conditions de succès
SC1 — Rouge d'abord, puis tous les tests du pont verts. Sur le PC, depuis la racine, avec la version de `3d/unity/ProjectSettings/ProjectVersion.txt`, exécuter en PowerShell :
```powershell
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot610.xml" -logFile "$env:TEMP\lot610.log"
```
Sans `-quit` ; attendre la fin, exiger sortie 0, XML sans échec et cas `ClientMaisonTests` effectivement exécutés, aucun ignoré. Les nouveaux cas échouent avant l'ajout du client ; zéro cas neuf est un échec. Contre-épreuve : remplacer provisoirement le nom relu par l'id fait rougir SC2 ; restaurer rend le vert. Conserver tous les cas existants, leurs noms, assertions et seuils.

SC2 — Lecture exacte et adresse exacte. Commande : `Unity.exe` de SC1. Le faux service `HttpListener` reprend le motif de `ClientMondeHorlogeTests` dans le nouveau fichier, sans toucher à cette classe. Témoin littéral : `{"id":"seigneurie-temoin","nom":"Maison d'Épreuve","siege":{"cell_id":9922,"rang":1,"nom":"Le Siège","point":{"x_m":4276473.25,"y_m":1135517.5}},"lieux":[{"cell_id":9922,"rang":1},{"cell_id":10417,"rang":0}],"absents":{}}`. Vérifier chaque valeur par égalité exacte, les deux lieux dans cet ordre, absence de raison, méthode GET et chemin `/maison?id=seigneurie-temoin`. Un second appel sur le même client sert un autre nom et d'autres lieux : seule la nouvelle fiche est rendue. Un id contenant `é /?&=+#` doit arriver comme un seul paramètre `id` égal à la chaîne d'origine après décodage. Contre-épreuves : permuter cellule et rang, remplacer une coordonnée par zéro, garder la première fiche ou omettre l'encodage fait échouer ces cas.

SC3 — Une absence déclarée reste une donnée lisible. Commande : `Unity.exe` de SC1. À partir du témoin, vérifier séparément `nom:null` avec `absents.nom` textuel, et siège hors carte avec `cell_id`, `rang`, `point` nuls et `absents.siege` textuel ; garder le nom du siège. Ces lectures sont présentes et portent les raisons exactes. Vérifier aussi `lieux:[]`, puis une raison supplémentaire `absents.part` : aucun lieu ni champ économique n'est inventé. Les clés supplémentaires ignorées n'empêchent pas la lecture. Contre-épreuves : retirer la raison, rendre une raison blanche, mettre un siège partiellement nul, ou ajouter `absents.nom` sur un nom présent refuse la fiche et nomme la faute ; restaurer le témoin rétablit la lecture.

SC4 — Toute faute est déclarée à son emplacement. Commande : `Unity.exe` de SC1. Cas paramétrés : retirer une à une toutes les clés exigées, y compris `lieux[1].rang` et les deux coordonnées ; remplacer les objets ou tableaux par un mauvais type ; id différent ; texte blanc ; entier négatif, fractionnaire ou ≥ 2^53 ; coordonnée non numérique ; couple de lieux répété. Chaque mutation vérifie qu'elle a réellement changé le témoin, reste du JSON valide et exige lecture absente, données nulles, cause non vide avec le chemin fautif. Tester aussi un JSON coupé et une coordonnée écrite `1e309` : le lecteur JSON existant les refuse avec « JSON invalide », sans exiger un chemin de clé à ce stade. Contre-épreuve : accepter une clé absente avec zéro ou une liste vide fait rougir son cas ; les versions intactes sont présentes. Aucun fichier ni test existant n'est réécrit.

SC5 — Maison inconnue, service absent et délai. Commande : `Unity.exe` de SC1. Après une lecture réussie, servir successivement 404 avec `{"erreur":"maison inconnue"}`, 500 avec un corps distinct et 302 : chacun rend une absence contenant statut et corps, aucune fiche ; le 302 n'entraîne aucune requête à sa destination. Port sans écouteur : « service absent ». Service muet avec délai court positif : « délai dépassé », sans fiche. Vérifier aussi ports hors 1..65535, délais nul, négatif, infini ou dépassant la minuterie, et id nul ou blanc refusés avant requête. Contre-épreuve : les mêmes données avec statut 200 sont lues ; suivre le 302 ou réutiliser la fiche précédente fait échouer les cas de refus.

SC6 — Périmètre et taille. Commandes : `git diff --name-only` et `git diff --numstat`, en comptant aussi les fichiers neufs et ce brief ; moins de 300 lignes ajoutées et supprimées au total, uniquement les quatre chemins autorisés et le brief porté par le chef. Les `.meta` viennent d'Unity. Budget prévu : environ 100 lignes de client, 110 de tests paramétrés, 18 de métadonnées et 60 de brief ; mutualiser les aides locales plutôt que réduire les preuves. Contre-épreuve : un chemin supplémentaire ou un total ≥ 300 refuse la livraison.

## Hors périmètre
Le service Python et son modèle ; toute mécanique, intention ou sélection de maison ; `/maisons`, `/departs`, les parts, greniers et flux ; les autres clients, `LecteurJson`, les aides communes, assemblages et tests existants. Aucun panneau, scène, dessin de carte ou rafraîchissement automatique : la fiche visible et le choix de départ restent dans #404. Aucun test existant ne doit rougir du fait de ce lecteur ajouté ; aucun test ne s'assouplit.

## Photo
sans objet : ce lot ajoute seulement un client HTTP et ses tests, sans appel depuis une scène ni changement de ce qu'on voit à l'écran. La fiche de choix visible de #404 portera son scénario de capture.
