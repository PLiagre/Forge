# Lot #653 — Le pont lit la part, le grenier et les flux de sa maison
Jalon : J3 · Machine : pc · Taille prévue : 250 lignes

## But
Le pont Unity sait lire le suzerain, la part, le grenier et les flux servis d'une maison, avec les absences déclarées, pour préparer le choix du joueur entre prélever et rendre du grain.

## Le joueur
Lot de fond, découpé de #405 (« Le joueur règle sa part et ouvre son grenier sur la carte ») : il prépare le geste du jalon J3, fixer la part qu'il prend sur ses lieux et rouvrir son grenier quand ses gens ont faim. Pour arbitrer entre remplir sa réserve et garder ses gens, le joueur doit connaître sa part actuelle, son grenier, ce qui monte de ses lieux, le dû au suzerain, les pertes du transport et les départs et arrivées de personnes. Après ce lot, ces données publiées par `sim/` sont accessibles au pont ; le panneau de maison de #405 les rendra visibles sur la carte avant le réglage de part et l'ouverture du grenier. Ce lecteur seul ne change encore rien à l'écran. Dépend de : #602 et #610, déjà présents dans ce chantier.

## Règle du monde
Sans objet : lecteur de vue, sans écriture dans le monde. Le contrat existant est celui de `jeu/sim/MODELE.md`, « Les maisons servies, vue dérivée » : part et grenier nuls ont leur raison dans `absents`, les sept flux ordinaires sont toujours servis, leurs zéros sont des mesures, et les personnes ne sont pas des foyers. `suzerain:null` signifie une racine sans suzerain. Les salaires sont un champ conditionnel de la fenêtre, sans raison d'absence à inventer. Aucune règle ni constante du monde ne change ; aucun arrondi ou calcul de flux côté Unity.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientMaison.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientMaisonTests.cs
docs/briefs/653-le-pont-lit-la-part-le-grenier-et-les-flux-de-sa.md

**Pourquoi une méthode à côté de `Lire`.** Le cas existant `LesAbsencesDeclareesRestentLisibles` fige les propriétés de `MaisonLue` à `Id, Nom, Siege, Lieux, Absents`, et le témoin des cas existants ne porte ni `suzerain`, ni `part`, ni `grenier`, ni `flux_30j`. Ni `MaisonLue` ni `Lire` ne changent donc : `Lire` continue d'ignorer ces clés, et `ReperesDeDepart`, `Lot614.cs`, `Lot624.cs` qui l'appellent ne bougent pas.

**Ce qu'on ajoute dans `ClientMaison.cs`**, dans `Forge.Pont` :

- `public Lecture<ComptesDeMaison> LireComptes(string identifiant)` : même requête `GET /maison?id=` que `Lire` (même encodage, même refus d'un identifiant nul ou blanc avant envoi, mêmes absences pour 404, 500, 302, service absent, délai). Elle réutilise la fonction privée `Fiche` pour la partie commune, puis lit les quatre champs ; une seule faute refuse toute la réponse, avec le chemin fautif, comme dans `Lire`.
- `ComptesDeMaison`, immuable : `MaisonLue Maison`, `string Suzerain`, `double? Part`, `IReadOnlyDictionary<string, double> Grenier`, `FluxDeMaison Flux`. Les raisons restent accessibles dans `Maison.Absents`. Le grenier est copié et exposé en lecture seule.
- `FluxDeMaison`, immuable : `double PreleveKg, RecuKg, DuEnvoyeKg, MangeEnRouteKg, RenduKg`, `long PartisPersonnes, ArrivesPersonnes`, `double? SalairesPayesKg`.

**Règles de lecture** :

- `suzerain` : clé exigée ; un texte non vide hors espaces (identifiant de maison) ou `null`. `null` veut dire racine, sans suzerain, et n'exige aucune raison.
- `part` : clé exigée ; un nombre fini entre 0 et 1, ou `null`. `null` exige la raison `absents.part`, et une part présente ne peut pas porter cette raison (même règle que `nom`). La borne 0,6 du jeu (`PART_MAXIMALE`) n'est pas recopiée côté Unity.
- `grenier` : clé exigée ; soit `null` avec `absents.grenier`, soit un objet marchandise → kilogrammes, chaque clé non vide hors espaces et chaque valeur un nombre fini ≥ 0. Un grenier présent ne peut pas porter cette raison. `{}` est une mesure : un grenier vide, jamais assimilé à une absence.
- `flux_30j` : clé exigée, un objet. Y sont exigés `preleve_kg`, `recu_kg`, `du_envoye_kg`, `mange_en_route_kg`, `rendu_kg` (nombres finis ≥ 0, relus exactement) et `partis_personnes`, `arrives_personnes` (entiers ≥ 0 sous 2^53, avec `ServiceLocal.Entier`). `salaires_payes_kg` est facultatif : présent, c'est un nombre fini ≥ 0 ; sa clé absente donne `SalairesPayesKg == null`, jamais 0 : aucun salaire enregistré dans la fenêtre depuis l'ouverture, sans mesure des jours antérieurs. Un flux ordinaire absent ou nul refuse la fiche avec sa cause ; le contrat ne publie pas de flux ordinaire nul avec une raison. Les zéros restent des mesures.
- Une clé exigée manquante n'est jamais prise pour une valeur nulle déclarée : elle refuse la fiche avec « clé absente : <chemin> » (`part`, `grenier`, `flux_30j`, `flux_30j.rendu_kg`…). Les clés supplémentaires (`sorte`, `tick`, `date`, une autre clé de `flux_30j`) sont ignorées.

Réutiliser sans les modifier `ServiceLocal`, `Lecture<T>`, `LecteurJson`. Aucun autre fichier.

**Ce qu'on ajoute dans `ClientMaisonTests.cs`** : un second témoin littéral, `Complet`, égal à `Temoin` plus les clés servies : `"suzerain":"grande-temoin","part":0.25,"grenier":{"nourriture":1234.5,"bois":0},"flux_30j":{"preleve_kg":812.25,"recu_kg":790.5,"du_envoye_kg":81.0,"mange_en_route_kg":21.75,"rendu_kg":19.25,"partis_personnes":7,"arrives_personnes":2,"salaires_payes_kg":40.5}`, et de nouveaux cas qui le lisent par `LireComptes`. Une aide de mutation propre au témoin complet (sur le modèle de `Muter`, qui reste inchangée). Aucun cas, nom, assertion, témoin ni seuil existant n'est modifié ; les cas existants restent verts tels quels.

## Conditions de succès
SC1 — Rouge d'abord, puis tous les tests du pont verts. Sur le PC, depuis la racine, avec Unity 6000.0.43f1 indiqué par `3d/unity/ProjectSettings/ProjectVersion.txt`, en PowerShell :
```powershell
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot653.xml" -logFile "$env:TEMP\lot653.log"
```
Sans `-quit` ; attendre la fin, exiger la sortie 0, un XML sans échec, aucun cas ignoré, et les nouveaux cas de `ClientMaisonTests` effectivement exécutés (zéro cas neuf est un échec). Les nouveaux cas échouent à la compilation avant l'ajout de `LireComptes`. Tous les cas existants de `ClientMaisonTests` passent sans changement, y compris `LesAbsencesDeclareesRestentLisibles` et sa liste exacte des propriétés de `MaisonLue`. Contre-épreuve : faire lire `recu_kg` à la place de `preleve_kg` fait rougir SC2 ; restaurer rend le vert.

SC2 — Lecture exacte du témoin complet. Commande : celle de SC1. `LireComptes` sur `Complet` rend une lecture présente ; vérifier par égalité exacte le suzerain `grande-temoin`, la part 0,25, les deux marchandises du grenier et leurs kilos (le zéro du bois compris), les cinq kilos, les deux nombres de personnes et les salaires 40,5 ; la partie commune (`Maison`) égale celle que rend `Lire` sur le même corps ; requête `GET /maison?id=seigneurie-temoin`. Un second appel sur le même client sert d'autres nombres : seuls les nouveaux sont rendus. Le grenier exposé refuse l'ajout (`NotSupportedException`). Contre-épreuves : permuter `partis_personnes` et `arrives_personnes`, rendre la part en pourcentage ou garder la première lecture fait échouer ces cas.

SC3 — Une absence déclarée reste une donnée lisible, une mesure n'est pas une absence. Commande : celle de SC1. Cas séparés à partir de `Complet` : `suzerain:null` sans raison → présent, `Suzerain == null` ; `part:null` avec `absents.part` → présent, `Part == null`, raison exacte, espaces compris ; `grenier:null` avec `absents.grenier` → présent, `Grenier == null`, raison exacte ; `grenier:{}` → présent, grenier vide non nul, aucune raison ; part et sept flux à zéro → présent, zéros relus ; `salaires_payes_kg` retiré → présent, `SalairesPayesKg == null`, distinct d'un salaire servi à zéro. Contre-épreuves (refusées, chemin nommé) : `part:null` sans raison, `grenier:null` sans raison, raison blanche, `absents.part` sur une part présente, `absents.grenier` sur un grenier présent.

SC4 — Toute faute est nommée à son chemin. Commande : celle de SC1. Cas paramétrés sur `Complet`, chacun vérifiant que la mutation change le témoin, reste du JSON valide et rend une lecture absente, sans données, avec le préfixe `maison : ` et le chemin fautif : retirer une à une `suzerain`, `part`, `grenier`, `flux_30j` et ses sept clés exigées ; `suzerain` blanc ou nombre ; `part` négative, au-dessus de 1, texte ou booléen ; `grenier` tableau, clé blanche, kilos négatifs ou texte ; `flux_30j` tableau ou `null` ; chaque kilo ordinaire négatif ou `null` ; chacun des deux compteurs de personnes négatif, fractionnaire ou ≥ 2^53 ; `salaires_payes_kg` négatif ou `null`. Ajouter un nombre `1e309` : « JSON invalide », sans exiger un chemin après ce refus du lecteur JSON. Contre-épreuve : accepter une clé absente comme zéro ou `null` fait rougir son cas. Une faute limitée aux quatre champs nouveaux n'empêche pas `Lire` de rendre sa fiche : un cas ajouté le vérifie, ainsi que l'acceptation des clés inconnues par `LireComptes`.

SC5 — Pannes et appels illicites. Commande : celle de SC1. Après une lecture réussie par `LireComptes`, servir 404, 500 et 302 : chacun rend une absence avec statut et corps, sans comptes, et le 302 n'entraîne aucune requête vers sa destination. Port fermé et service muet donnent leurs causes « service absent » et « délai dépassé », sans ancienne fiche. `Temoin` seul rend l'absence « clé absente : suzerain » par `LireComptes` et reste lisible par `Lire`. Identifiant nul ou blanc refusé avant toute requête ; l'identifiant `é /?&=+#` arrive en un unique paramètre encodé. Contre-épreuves : servir `Complet` en 200 rend les comptes ; réutiliser les comptes précédents après panne ou suivre le 302 fait échouer ces cas.

SC6 — Périmètre et taille. Commandes : `git diff --name-only origin/master`, `git diff --numstat origin/master` et `git ls-files --others --exclude-standard` ; compter aussi les lignes des fichiers neufs listés, dont ce brief du chef. Seuls les trois chemins du Périmètre sont admis ; moins de 300 lignes ajoutées et supprimées au total. Budget prévu : environ 70 lignes de client, 120 de tests et 60 de brief, soit 250 lignes. `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientMaisonTests.cs` doit montrer uniquement des cas et aides ajoutés, sans retrait ni réécriture des cas actuels. Contre-épreuve : un chemin supplémentaire, un cas existant modifié ou un total ≥ 300 refuse la livraison.

## Hors périmètre
Le service Python, `jeu/sim/MODELE.md` et toute règle du monde ; les intentions `fixer_part` et `ouvrir_grenier` (`ClientIntention` suffit déjà) ; `ClientLieu` et ses `flux_30j` par lieu (autre sous-lot de #405) ; `MaisonLue`, `Lire` et leurs appelants (`ReperesDeDepart`, captures #614 et #624) ; le panneau « Ma maison », le curseur, le bouton, les points des lieux, les flèches, l'épreuve ; toute scène, tout `CarteBuilder`, toute capture. Aucun test existant n'est réécrit ni assoupli.

## Photo
sans objet : ce lot ajoute seulement une méthode de lecture au client HTTP et ses tests, sans appel depuis une scène ni changement de ce qu'on voit à l'écran. Le sous-lot « panneau de lecture » de #405, qui affichera ces nombres, portera son scénario de capture.
