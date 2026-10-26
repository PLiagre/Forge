# Lot #654 — Le pont lit ce qui a circulé dans chaque lieu
Jalon : J3 · Machine : pc · Taille prévue : 260 lignes

## But
Le pont Unity sait relire, pour chaque lieu, les kilos prélevés et les personnes parties et arrivées sur trente jours, sans confondre une donnée absente avec un zéro mesuré.

## Le joueur
Lot de fond découpé de #405, « Le joueur règle sa part et ouvre son grenier sur la carte » : il prépare le geste de J3, fixer la part prise sur ses lieux et rouvrir son grenier quand ses gens ont faim. Ces chiffres permettront au joueur de voir ce que chaque lieu donne et les habitants qui le quittent ou le rejoignent, pour sentir le coût de son prélèvement et arbitrer entre remplir son grenier et garder ses gens. Le panneau de lecture issu de #405 rendra ces données visibles sur la carte ; ce lot seul ne change aucun écran. Dépend de : #400 (flux servis) et #611 (lieux relus), déjà présents dans ce chantier. Il ne dépend pas des comptes de maison de #653, qui touchent d'autres fichiers.

## Règle du monde
Sans objet : lecture de vue, sans modification du monde. Le contrat découle de `jeu/sim/MODELE.md`, « Les flux sur trente jours » et « Les lieux d'une cellule, vue dérivée », notamment « Ce que porte un lieu ». Chaque entrée de `/lieu?cell=X` porte `flux_30j` : `preleve_kg`, `partis_personnes`, `arrives_personnes`, sans arrondi. Les migrations sont des personnes brutes, dans les deux sens séparément, jamais un solde ni des foyers. Le service peut déclarer `flux_30j:null` quand les flux ne sont pas fournis ; des zéros fournis sont des mesures. Unity ne recalcule ni le prélèvement ni la fenêtre de trente jours. L'identité reste la cellule de la réponse et le rang du lieu ; aucune seconde clé spatiale. Aucune règle, constante ou fidélité du monde ne change.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientLieu.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientLieuTests.cs
docs/briefs/654-le-pont-lit-ce-qui-a-circule-dans-chaque-lieu.md

## Conditions de succès
SC1 — Rouge d'abord, puis tous les tests du pont verts. Sur le PC, depuis la racine, avec Unity 6000.0.43f1 du projet, en PowerShell :
```powershell
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot654.xml" -logFile "$env:TEMP\lot654.log"
```
Sans `-quit` ; attendre la fin du processus, exiger la sortie 0 et un XML neuf sans échec ni cas ignoré. Vérifier que chaque nouveau cas de `ClientLieuTests` a réellement été exécuté ; une sélection vide échoue. Ajouter les cas avant le lecteur et constater leur échec, y compris à la compilation si les propriétés manquent. Aucun test, témoin, aide, nom, assertion ou seuil existant ne change. Contre-épreuve : neutraliser la lecture des flux fait rougir les nouveaux cas ; restaurer rend le vert.

SC2 — Chaque lieu garde ses trois flux exacts. Commande : celle de SC1. Dans `ClientLieu.cs`, ajouter un type immuable `FluxDeLieu` avec `double PreleveKg`, `long PartisPersonnes`, `long ArrivesPersonnes`, puis à `LieuPlace` les propriétés en lecture seule `FluxDeLieu Flux` et `string AbsenceDesFlux`. Conserver les appels actuels du constructeur par des paramètres optionnels finaux. `Places` lit le bloc de chaque entrée et ignore les clés supplémentaires. Kilos : nombre fini ≥ 0 ; personnes : entiers ≥ 0 strictement sous 2^53, avec les aides locales existantes. Les trois valeurs sont conservées exactement, sans arrondi, conversion en foyers ni compensation des arrivées par les départs.

Ajouter un témoin construit en mémoire à partir de `lieu-graine0-tick3.json`, sans changer son fichier : au moins deux lieux, de rangs distincts, avec des triplets distincts, dont `(1234.56789, 7, 2)` et `(0.0, 0, 11)`. Les attentes viennent du témoin, jamais du nouveau lecteur. Comparer tous les rangs et tous les triplets dans l'ordre ; vérifier aussi cellule, tick, positions et maîtres conservés. Lire également les flux de chaque entrée de la fixture réelle, échantillon non vide exigé. Un compteur à `9007199254740991` reste exact. Contre-épreuves : arrondir les kilos, permuter les deux compteurs, attribuer les flux du bourg à tous ou omettre le dernier lieu fait échouer les comparaisons.

SC3 — Absence déclarée et zéro restent distincts, lieu par lieu. Commande : celle de SC1. Ajouter des cas où seul le second lieu perd `flux_30j`, puis le reçoit à `null` : la lecture de la cellule reste présente, le lieu conserve rang, position et maître, `Flux == null` et `AbsenceDesFlux` non vide nomme `lieux[1].flux_30j` avec une cause distinguant clé absente et valeur nulle déclarée. Les flux du premier lieu restent présents et inchangés. Un bloc avec les trois zéros donne au contraire un objet `Flux` non nul, ses zéros exacts et aucune raison d'absence. Les cas historiques sans ce bloc, notamment `LesAbsencesDeLieuxRestentDistinctesDesMesures`, restent verts sans modification ; les contrats de `lieux` absent ou vide restent inchangés. Contre-épreuves : remplacer l'absence par trois zéros, refuser une ancienne réponse sans flux ou effacer les flux de tous les lieux fait rougir ces cas.

SC4 — Un bloc présent fautif refuse la réponse avec son chemin. Commande : celle de SC1. Ajouter des cas paramétrés sur le second lieu du témoin de SC2 : `flux_30j` tableau, texte ou booléen ; retrait de chacune de ses trois clés ; chaque valeur à `null`, texte, booléen ou négative ; chacun des compteurs fractionnaire ou ≥ 2^53. Exiger `Presente == false`, `Lieu == null`, une absence avec cellule et chemin précis, par exemple `lieux[1].flux_30j.partis_personnes`. Un objet vide refuse sa première clé requise ; aucun triplet partiel n'est publié. Chaque mutation vérifie qu'elle a changé le seul endroit voulu et reste du JSON valide. Un nombre `1e309` doit être refusé comme « JSON invalide » par le lecteur JSON existant. Contre-épreuves : restaurer le témoin rend une lecture présente ; accepter une sous-clé absente comme zéro fait échouer son cas. Le `null` du bloc entier reste le cas déclaré de SC3.

SC5 — La nouvelle lecture remplace la précédente. Commande : celle de SC1. Sur le même `ClientLieu`, servir successivement le témoin de SC2, des valeurs différentes au second lieu, puis son bloc absent : vérifier les trois états exacts et l'absence de conservation des anciens flux. Une réponse avec une clé supplémentaire dans le bloc reste lisible. Le premier lieu ne change pas. Contre-épreuves : garder le premier triplet ou partager un même objet mutable entre lieux ou lectures fait échouer ces cas.

SC6 — Périmètre et taille tenus. Commandes : `git diff --check`, `git diff --name-only origin/master`, `git diff --numstat origin/master` et `git ls-files --others --exclude-standard` ; compter aussi les lignes des fichiers neufs, dont ce brief. Seuls les trois chemins du Périmètre sont autorisés, moins de 300 lignes ajoutées et supprimées au total. Budget : environ 55 lignes de client, 150 lignes de tests ajoutés et 55 lignes de brief. `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientLieuTests.cs` ne montre que des ajouts de cas et d'aides propres au lot. Contre-épreuve : un chemin supplémentaire, un test existant réécrit ou un total ≥ 300 refuse la livraison.

## Hors périmètre
Le service Python, les règles du monde et `MODELE.md` ; les comptes de maison de #653 ; toute modification des fixtures, tests ou aides existants ; les intentions de prélèvement et d'ouverture du grenier ; le panneau, les flèches, les scènes, les captures et l'épreuve de #405. Aucun calcul de flux, cache, nouvelle requête HTTP, agrégation entre lieux ou rapprochement de ticks dans Unity. Tout autre chemin est interdit.

## Photo
sans objet : ce lot d'outil ajoute uniquement des données au client HTTP et leurs tests, sans branchement à une scène ni changement de ce qu'on voit à l'écran. Le panneau de lecture issu de #405 portera le scénario de capture montrant ces nombres sur la carte.
