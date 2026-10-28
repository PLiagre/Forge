# Lot #784 — Chaque passant représente dix habitants du bourg
Jalon : J4 · Machine : pc · Taille prévue : 290 lignes

## But
La vue sait dériver du bourg son nombre de passants, à raison de dix habitants par passant, et les répartir par métier pour préparer leur affichage.

## Le joueur
Lot de fond découpé de #421 « Les gens du bourg circulent dans les rues » : il prépare le geste du J4, entrer dans sa capitale et y marcher parmi ses habitants. Le joueur pourra sentir une ville qui se peuple ou se vide avec le monde, et reconnaître les métiers qui la font vivre. Le sous-lot 6 de #421 rendra cette projection visible en affichant les passants ; #784 seul ne change rien à l'écran. Dépend de : #783, dont il consomme `Lieu.Bourg.Population` et les métiers déjà lus dans `/lieu`.

## Règle du monde
Sans objet : projection de vue pure, sans règle démographique ni écriture dans le monde. Elle lit les contrats de `jeu/sim/MODELE.md`, « Les foyers par métier », « Les lieux d'une cellule, vue dérivée » et « Le chantier et ses bras » : rang 0 pour le bourg, métiers publiés en personnes pour la cellule, non-paysans rattachés au bourg par convention de niveau 2. Le facteur dix est une échelle d'affichage demandée par l'issue, jamais une taille de foyer ou une suppression d'habitants. Les populations du monde restent exactes, y compris le reliquat inférieur à dix.

Créer dans `Forge.Pont` une classe pure `PassantsDuBourg`, avec `public const int HABITANTS_PAR_PASSANT = 10` et `Projeter(LectureLieu lecture)`. Aucun `GameObject`, appel réseau, aléa, cache, horloge ou dépendance au plan. Son résultat immuable expose `Presente`, `Absence`, `long? Nombre` et `IReadOnlyDictionary<string, long> ParMetier`. Présent : raison nulle, nombre mesuré et dictionnaire copié en lecture seule ; absent : raison précise, nombre et dictionnaire nuls. Ce contrat sera consommé par le sous-lot 6, sans branchement à l'affichage dans ce lot.

Le total est exclusivement `N = P / HABITANTS_PAR_PASSANT`, division entière, où `P` est la population du lieu de rang 0, indépendamment de sa position dans la liste. Aucun minimum à un, plafond, arrondi au plus proche ou calcul d'après les maisons, les foyers ou le total cellulaire. Un bourg connu vide donne une projection présente de zéro, dictionnaire vide, même si sa cellule reste peuplée ; dans ce cas les métiers ne sont pas nécessaires.

Pour `P > 0`, exiger les métiers servis. Construire des poids visuels : chaque métier autre que `paysans` garde son compte de `Personnes` ; le poids des paysans vaut `max(0, P − somme des non-paysans)`, comme le décompte local des bras aux champs. Si les non-paysans dépassent `P`, leurs comptes restent des poids à normaliser, jamais des habitants locaux ajoutés. Cette répartition décrit seulement les représentants affichés ; elle ne prétend pas publier un nouveau recensement local. Accepter tous les noms de métiers non blancs, y compris futurs, sans liste fermée ; ne jamais utiliser le nombre de foyers.

Avec `W` la somme des poids positifs, attribuer à chaque métier `N × poids / W` au plancher ; distribuer les unités restantes aux plus grands restes, puis au nom par ordre ordinal croissant en cas d'égalité. Garder les métiers de poids positif dans le résultat, même avec zéro passant ; omettre les poids nuls. La somme vaut exactement `N`, indépendamment de l'ordre des entrées. Calcul entier exact, intermédiaires sans débordement jusqu'à 2^53 − 1 (par exemple `System.Numerics.BigInteger`) ; produire des comptes, jamais une liste de `N` objets.

Une lecture absente ou nulle, des lieux absents ou sans rang 0, une population locale absente ou hors de 0..2^53 − 1 donnent une absence nommée. Pour `P > 0`, même chose si les métiers sont absents ou non calculés, si un nom est blanc, si un compte de personnes est négatif, si leur somme diffère du total cellulaire ou si `P` dépasse ce total. Ces gardes appartiennent à la nouvelle projection ; les lecteurs existants et leurs contrats restent inchangés. Chaque appel relit seulement son argument ; une absence après une réussite ne conserve aucun résultat antérieur.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/PassantsDuBourg.cs
3d/unity/Assets/ForgeLocal3D/Pont/PassantsDuBourg.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PassantsDuBourgTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PassantsDuBourgTests.cs.meta
docs/briefs/784-chaque-passant-represente-dix-habitants-du-bourg.md

## Conditions de succès
SC1 — Rouge d'abord, puis tous les tests du pont verts. Sur le PC, depuis la racine, en PowerShell, avec Unity 6000.0.43f1 :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot784.xml" -logFile "$env:TEMP\lot784.log"
```
Attendre la fin, sans `-quit` ; exiger un XML présent, sans échec ni cas ignoré, et les nouveaux cas réellement exécutés. Écrire les tests avant la projection et constater leur échec, éventuellement à la compilation tant que son API manque. L'invariant est neuf : ses cas vont dans `PassantsDuBourgTests.cs` ; aucun test, aide ou témoin existant ne change. Contre-épreuve : zéro cas neuf exécuté, XML absent ou ancien cas rouge interdit la livraison.

SC2 — Total local au plancher. Commande : SC1. Nouveaux cas avec bourg non premier, cellule de 1 000 habitants et populations locales 0, 1, 9, 10, 19, 20 et 109 : vérifier respectivement 0, 0, 0, 1, 1, 2 et 10, ainsi que la constante publique à 10. Les métiers servis restent cohérents avec les 1 000 personnes ; leurs nombres de foyers sont volontairement différents des comptes de personnes divisés par cinq. Contre-épreuves : compter la première entrée, les 1 000 habitants cellulaires ou les foyers, imposer un passant minimum ou arrondir 19 à deux doit rougir.

SC3 — Répartition exacte, stable et ouverte. Commande : SC1. Témoin cellulaire : artisans 19 personnes, mineurs 24, paysans 957 ; bourg 109. Exiger dix passants : artisans 2, mineurs 2, paysans 6. Un second témoin de bourg 10 avec forgerons 5, mineurs 5 et paysans 990 donne forgerons 1 et mineurs 0, sans paysan représenté ; inverser l'ordre des métiers rend exactement le même résultat. Avec le premier témoin et un bourg de 20, les poids non paysans dépassent la population locale : exiger un artisan et un mineur, sans paysan. Vérifier somme et chaque part, pas seulement la constante. Contre-épreuves : arrondir chaque métier séparément donne neuf au premier témoin ; prendre les paysans cellulaires, ignorer un métier futur ou départager selon l'ordre reçu fait échouer ces cas.

SC4 — Croissance, départs et absence de mémoire. Commande : SC1. Projeter successivement, pour la même cellule, des lectures aux ticks distincts : population locale 19, 20, 9 puis 0, avec métiers cellulaires cohérents ; exiger 1, 2, 0 puis 0 et les répartitions recalculées. Changer aussi les métiers à population locale constante pour vérifier que les parts changent. Puis projeter une lecture absente et une lecture valide : l'absence est déclarée, puis le résultat se rétablit. Conserver les premiers résultats et vérifier qu'ils restent identiques après les appels suivants ; tenter de modifier le dictionnaire exposé doit échouer. Contre-épreuves : un cache par cellule, le maintien des passants après dépopulation ou la réutilisation du dictionnaire d'entrée fait rougir ces tests.

SC5 — Zéro mesuré, absence déclarée et grands comptes. Commande : SC1. Distinguer bourg vide dans une cellule peuplée, cellule vide avec bourg de population zéro et métiers `{}`, liste de lieux vide, liste sans rang 0 et population de rang 0 absente. Tester lecture nulle/absente, métiers absents/non calculés pour un bourg positif, nom blanc, compte négatif, somme cellulaire incohérente et population locale supérieure au total : résultat absent avec cause pertinente, aucun nombre de remplacement. Un bourg vide reste présent même sans métiers. Un bourg à 2^53 − 1 personnes, toutes d'un même métier, rend exactement 900719925474099 passants de ce métier, sans allocation proportionnelle à ce nombre ; tester aussi population locale négative et 2^53. Contre-épreuves : transformer une absence en zéro, déborder dans `N × poids` ou convertir les grands comptes en `int` fait échouer ces cas.

SC6 — Compatibilité, périmètre et budget. Commandes : SC1, `git diff --name-only`, `git diff --numstat`, `git ls-files --others --exclude-standard` et `git diff --check`. Vérifier tous les fichiers neufs, leurs métadonnées Unity et le brief : moins de 300 lignes ajoutées et supprimées, budget 290 (environ 100 de projection, 110 de tests, 14 de métadonnées et 66 de brief). Aucun test existant ne doit rougir ni être réécrit, notamment `ChaqueLieuGardeSaPopulationEtLeBourgSeTrouveParSonRang`, `LesFoyersServisSontRelusDansLOrdreEtSansLogement` et `DesFoyersNonCalculesOuAbsentsSeDeclarent`. Contre-épreuve : modification d'un lecteur, d'un test actuel ou d'un autre chemin, ou total ≥ 300, refuse la livraison.

## Hors périmètre
Le moteur et sa documentation, les contrats et le service Python, les lecteurs du pont, toute modification de population ou de métier, les intentions ; les trajets, destinations, affectations aux chantiers, horaires, animations, modèles et objets de passants ; l'intégration dans la capitale, les panneaux et les captures. Le sous-lot 6 de #421 consommera les comptes pour l'affichage. Aucun test existant n'est modifié ni assoupli. Tout autre chemin que ceux du Périmètre est interdit.

## Photo
sans objet : ce lot ajoute uniquement une projection pure et ses tests, sans changement de ce qu'on voit à l'écran. La capture des passants dans les rues appartient au sous-lot 6 de #421, qui branchera cette projection à l'affichage.
