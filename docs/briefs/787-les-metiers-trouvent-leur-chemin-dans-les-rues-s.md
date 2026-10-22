# Lot #787 — Les métiers trouvent leur chemin dans les rues servies
Jalon : J4 · Machine : pc · Taille prévue : 290 lignes

## But
La vue sait préparer des trajets continus sur les rues servies vers les chantiers, les débouchés et les ateliers, ou expliquer pourquoi une destination manque.

## Le joueur
Lot de fond découpé de #421 « Les gens du bourg circulent dans les rues » : il prépare le geste de J4, entrer dans sa capitale et y marcher parmi ses habitants après avoir tracé ses rues et posé ses ateliers. Le joueur pourra reconnaître les ouvriers qui vont travailler, les paysans qui gagnent les sorties et les artisans qui rejoignent les ateliers ; il sentira que sa ville vit des destinations du monde. La demande fournie ne contient pas de phrase « Le joueur » distincte : ce gain reprend celui de #421 dans CAP.md. Le sous-lot 6 de #421 rendra ces parcours visibles ; #787 seul ne change rien à l'écran. Dépend de : #783, livré ; aucune dépendance à #784 pour calculer la géométrie.

## Règle du monde
Sans objet : calcul pur de vue, sans nouvelle règle ni écriture dans la simulation. Il lit les contrats de `jeu/sim/MODELE.md`, « Le plan du bourg », « Le plan de base » et « Le chantier et ses bras » : géométrie locale et rattachement collectif des ouvriers de niveau 2 inchangés. Un parcours visuel n'affecte ni emploi, ni travail fourni, ni transport, ni récolte. Les croisements restent de niveau 3 ; ce lot ne crée pas de réseau de circulation dans le monde.

Créer `TrajetsDesMetiers` dans `Forge.Pont`, avec `Calculer(LecturePlan lecture, string metier)`, sans UnityEngine, réseau, horloge, aléa, cache ni dépendance aux effectifs. Le résultat immuable porte la cellule et le tick lus, une liste de trajets et une absence générale éventuelle. Chaque trajet porte la référence locale de sa destination, celle de sa rue et soit ses `PointLocal`, soit une raison d'absence. Copier les collections en lecture seule. Lecture nulle/absente ou métier sans destination connue : absence nommée, aucune géométrie de remplacement. Le sous-lot 6 pourra utiliser ces résultats avec les comptes de #784, sans changer ceux-ci.

Destinations, sans inventer de bâtiments ni de personnes :
- `ouvriers` : chaque entrée de `ChantiersDuJour` ayant `Bras > 0`, retrouvée par `(Nature, Identifiant)` dans les rues, parcelles ou bâtiments. Un achèvement ce jour reste une destination même si `EnChantier` est faux. Zéro bras ne donne aucun trajet. Relevé absent : absence ouvrière nommant sa cause ; relevé vide : aucun chantier employant des bras. Une référence introuvable reste une entrée absente explicitement nommée, jamais silencieusement supprimée.
- `paysans` : extrémité finale des rues de base portant `VersCellId` et des rues de geste achevées portant `PorteCellId`, zéro compris. Ce sont des débouchés déclarés, pas des portes d'enceinte supposées ; une rue sans cette donnée ne devient pas une sortie par son orientation ou sa sorte.
- `artisans` : bâtiments achevés de nature `scierie` ou `four`, jamais maisons, bâtiments inconnus ou ateliers encore en chantier. Ce sont des destinations possibles, sans déduire combien d'artisans y travaillent. Les mineurs et métiers futurs restent sans destination déclarée dans ce lot.

Convention géométrique d'affichage, sans origine résidentielle inventée : un trajet parcourt une seule polyligne servie, pas un chemin entre deux rues. Vers un débouché ou un chantier de rue, reprendre les points de cette rue dans l'ordre, virages compris. Pour une parcelle ou un bâtiment, prendre la moyenne des sommets du contour ou de l'emprise comme cible de recherche ; projeter cette cible sur le segment de rue le plus proche, projection bornée aux extrémités. Le parcours suit les points depuis le début de cette rue jusqu'à cette projection, sans couper ses virages. Si ce préfixe est nul, utiliser le suffixe parcouru à rebours. Il s'arrête sur la rue : aucune entrée de bâtiment ni liaison hors rue n'est affirmée.

Les rues disponibles pour approcher parcelles et bâtiments sont celles de base et les rues de geste achevées. Une rue en chantier n'est parcourue que pour son propre chantier ayant des bras. Écarter les segments de longueur nulle ; sans parcours de longueur positive, déclarer la destination inaccessible avec sa référence. Sans base, conserver les possibilités des rues de geste ; sans aucune rue utilisable, ne tracer aucune ligne directe vers la cible. À distance égale, départager par source (base avant geste), rang de rue dans la base ou identifiant du geste, puis rang du segment. Ordonner les destinations de manière stable par nature puis référence locale ; les identifiants de rue, parcelle et bâtiment peuvent coïncider. Le rang de base ne vaut que dans cette lecture, jamais comme nouvelle clé spatiale persistée.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/TrajetsDesMetiers.cs
3d/unity/Assets/ForgeLocal3D/Pont/TrajetsDesMetiers.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TrajetsDesMetiersTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TrajetsDesMetiersTests.cs.meta
docs/briefs/787-les-metiers-trouvent-leur-chemin-dans-les-rues-s.md

## Conditions de succès
SC1 — Rouge d'abord, puis tous les tests du pont verts. Sur le PC, depuis la racine, en PowerShell, avec Unity 6000.0.43f1 :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot787.xml" -logFile "$env:TEMP\lot787.log"
```
Attendre la fin, sans `-quit` ; exiger un XML présent sans échec ni cas ignoré, avec les nouveaux cas exécutés. Écrire ces cas avant le calcul et constater le rouge, éventuellement à la compilation tant que son API manque. Ce nouvel invariant va dans `TrajetsDesMetiersTests.cs`. Contre-épreuve : XML absent, zéro cas neuf exécuté ou ancien cas rouge interdit la livraison.

SC2 — Chaque métier garde ses destinations. Commande : SC1. Témoins non vides : sorties de base et de geste, deux ateliers achevés, maison, atelier inachevé et chantiers des trois natures partageant un identifiant. Vérifier les références et les points, pas seulement le nombre de trajets. Inclure une rue en chantier avec bras, un chantier achevé ce jour avec bras, un chantier encore ouvert avec zéro bras et un relevé absent. Contre-épreuves : remplacer les bras du jour par `EnChantier`, confondre les trois identifiants ou envoyer les artisans aux maisons fait rougir les cas.

SC3 — Aucun raccourci ni sortie devinée. Commande : SC1. Une rue coudée `(0,0), (10,0), (10,10)` dessert un atelier centré en `(12,7)` : exiger `(0,0), (10,0), (10,7)`, jamais la diagonale. Tester aussi projection sur une extrémité, départ donnant un préfixe nul, segment nul et polyligne entièrement nulle. Une rue sans débouché, même orientée comme une sortie, n'attire aucun paysan ; une rue de geste en chantier portant une porte reste exclue des sorties. Contre-épreuves : relier directement cible et départ, supprimer le coude ou inférer une porte depuis les coordonnées fait échouer ces cas.

SC4 — Base, gestes et absences indépendants. Commande : SC1. Faire gagner alternativement une rue de base puis une rue de geste par la distance à la cible ; tester leur égalité et deux gestes reçus dans l'ordre inverse. Vérifier les points de projection attendus. Retirer la base conserve le trajet permis par le geste ; retirer toutes les rues, les ateliers, les débouchés ou l'objet d'un relevé déclare la cause pertinente, sans destination de remplacement. Un relevé vide et un relevé absent restent distinguables. Contre-épreuves : ne lire que la base, ne lire que les gestes, perdre une référence introuvable ou convertir une absence en trajet fictif fait rougir les cas.

SC5 — Résultats réutilisables sans mémoire. Commande : SC1. Calculer deux plans de la même cellule à des ticks distincts avec atelier déplacé et bras retirés, puis une lecture absente et une lecture valide ; exiger les nouvelles destinations et géométries, le tick exact et la conservation des premiers résultats. Tester un métier inconnu et tenter de modifier les collections exposées. Contre-épreuves : cache par cellule, ancienne géométrie conservée après une absence ou collection modifiable fait échouer ces cas.

SC6 — Compatibilité et budget. Commandes : SC1, `git diff --name-only`, `git diff --numstat`, `git ls-files --others --exclude-standard` et `git diff --check`. Compter aussi les fichiers neufs : moins de 300 lignes ajoutées et supprimées, cible 290 (environ 125 de calcul, 90 de tests, 8 de métadonnées et 67 de brief). Aucun test existant ne doit changer ou rougir, notamment `LesDebouchesEtLeReleveDuJourSontRelusExactement`, `UnNouveauReleveRemplaceLePrecedentEtSonAbsenceSeDeclare`, les comptes de `PassantsDuBourgTests` et les effectifs figés de la base de Biskra. Contre-épreuve : modification d'un lecteur, d'un témoin existant, d'un autre chemin ou total atteignant 300 refuse la livraison.

## Hors périmètre
Le moteur, sa documentation, le service Python et ses contrats ; toute règle d'emploi, salaire, récolte ou transport ; les lecteurs du pont et les comptes de #784. Pas de recherche de chemin entre rues, de carrefour, de franchissement d'enceinte, d'entrée d'atelier, de domicile affecté ni d'horaire individuel. Pas de modèles, animation, répartition des passants entre destinations, branchement à la capitale ou panneau : le sous-lot 6 de #421 porte leur circulation visible. Aucun test, aide ou témoin existant n'est modifié ni assoupli. Tout autre chemin que ceux du Périmètre est interdit.

## Photo
sans objet : ce lot ajoute seulement un calcul pur et ses tests, sans aucun appel depuis une scène et sans changement de ce qu'on voit à l'écran. Le sous-lot 6 de #421 branchera ces trajets à l'affichage des passants et portera son scénario de capture dans la capitale.
