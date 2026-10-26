# Lot #690 — La carte pose le passage au chargement, photo de Bar
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Après avoir choisi Bar dans le cabinet et laissé passer un jour, le joueur reste sur la carte et voit pourquoi sa capitale ne s'ouvre pas encore en 3D.

## Le joueur
En choisissant le Duché de Bar, le joueur voit « Pas encore de kit pour cette terre » après l'application de son choix et comprend qu'il gouverne depuis la carte. Ce sous-lot de #681 rend visible le passage préparé par #689 : le geste de J4 « passer de la carte à sa ville d'un geste » ouvre Biskra au Zab et explique l'attente des autres kits jusqu'au jalon 9, conformément à `CAP.md`.

Dépend de : #689. `PassageALaCapitale`, `AiguillageDeCapitale`, `CabinetDeCarte`, `LecturePartie` et `Lot549.Ouvrir/Photographier` sont présents sur la base ; aucun apport futur de J3 n'est requis.

## Règle du monde
Sans objet : lot de vue. Aucune règle, donnée historique, constante ou clé spatiale ne change. Le choix suit le chemin existant de « Les intentions du joueur » de `jeu/sim/MODELE.md` : reçu accepté, puis `maison_du_joueur` publiée au tick suivant. Les lectures suivent « La carte et les terres servies, vue dérivée » et « Les maisons servies, vue dérivée ». Le panneau lit l'aiguillage de #689 ; ni le reçu ni le cabinet ne décident de l'ouvrir.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/PassageALaCapitale.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PassageALaCapitaleTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot690.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot690.cs.meta
docs/briefs/690-la-carte-pose-le-passage-au-chargement-photo-de.md

Tout autre chemin est interdit. Budget indicatif : 25 lignes d'installation, 40 de tests ajoutés, 130 de capture, 2 de `.meta`, le reste pour ce brief ; ajouts et retraits cumulés restent sous 300 lignes.

Dans `PassageALaCapitale`, reprendre le mécanisme de chargement du cabinet : initialisation après chargement, abonnement unique à `SceneManager.sceneLoaded` et traitement immédiat de la scène active. Pour la seule scène `OuvertureDeLaCarte.SCENE`, poser le composant manquant sur chaque objet `CarteDessinee` appartenant à cette scène, avec le port de cette carte. Une seconde notification ne crée rien et conserve l'instance existante. Le `Start` actuel prend sa caméra après `CarteDessinee`. Aucun lien vers `Forge.Interface` dans le pont ; aucun changement de la décision, du panneau ou de sa cadence de #689.

## Conditions de succès
Sur le PC, éditeur fermé, depuis la racine : `$u = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. Chaque lancement utilise des fichiers temporaires neufs. `CAPTURE` désigne `& $u -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeSeed 0 -forgeLot 690`, complété par les arguments ci-dessous ; sans `-quit` ni `-nographics`.

SC1 — Installation limitée à la carte, sans doublon. Ajouter les cas au fichier qui porte déjà l'invariant, sans modifier les cas existants, puis exécuter :
```powershell
& $u -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests,Forge.Interface.Tests -testResults "$env:TEMP\lot690-tests.xml" -logFile "$env:TEMP\lot690-tests.log"
```
Les nouveaux cas exercent le rappel de chargement sur des scènes temporaires, sans les sauvegarder : carte sans passage puis deuxième appel (exactement une instance, même instance et bon port), passage déjà présent (conservé), autre scène portant une carte (aucun ajout), scène sans carte (aucun ajout). Sortie 0 et XML sans échec, avec les nouveaux cas, `PassageALaCapitaleTests`, `CabinetDeCarteTests` et `LecturePartieTests` réellement exécutés ; une suite vide ne prouve rien et refuse la livraison. Contre-épreuves : sans installation le premier cas rougit ; sans garde de doublon ou de scène les cas correspondants rougissent. Écrire et constater ces échecs avant l'installation. Les tests actuels sur la confirmation vue, l'absence, la cadence et la survie du panneau au cabinet restent inchangés.

SC2 — Bar choisi par le cabinet montre le message après un tick. Exécuter `CAPTURE -forgeTicks 3 -forgeCaptures "$env:TEMP\lot690-normal" -logFile "$env:TEMP\lot690-normal.log"` : sortie 0, scénario effectivement exécuté et trace `CAPTURE_690` avec tick avant/après, terre, maison et scène. Le scénario unique `[ScenarioDeCapture(690, "bar-sans-kit")]` :

- ouvre `Forge_Carte` avec `Lot549.Ouvrir`, exige exactement un passage installé sur la carte et ne l'ajoute jamais ;
- exige le vrai `CabinetDeCarte` construit, sa toile active et `ReperesDeDepart` désactivé par lui ; attend une lecture réussie de `cabinet.Partie`, sans maison, avec départs non vides et choix possible ;
- trouve exactement une fiche dont `Nom == "Duché de Bar"`, dérive son identifiant et le tick N des lectures, puis appelle `cabinet.Partie.Choisir(fiche.Id)` et attend son reçu accepté ; aucun dépôt direct par le prototype ou par le scénario ;
- avant tout tick, relit indépendamment `/monde` par `ClientMonde.LireAvecMaison` : tick N, maison absente, passage sans message ni scène demandée ;
- pousse exactement un `POST /tick?n=1`, hors du fil principal, puis attend les lectures normales du cabinet et du passage ; une lecture indépendante doit confirmer N+1 et la maison choisie, identique à celle du cabinet ;
- exige le texte exact `PassageALaCapitale.MESSAGE_SANS_KIT`, le panneau actif dans la hiérarchie, `SceneDemandee == null` et la scène active toujours `Forge_Carte`, puis prend la photo décrite ci-dessous.

Les appels attendus ont une borne explicite, au plus 30 s par attente ; absence, tâche fautive, liste vide ou reçu refusé échouent en nommant leur cause. Le service du harnais reste en pause : ne pas activer l'horloge. Contre-épreuve : lancer cette commande avant l'installation échoue pour passage absent, sans que le scénario le répare ; sans tick, SC3 rougit.

SC3 — Le reçu seul ne montre rien. Exécuter `CAPTURE -forgeTicks 3 -forge690SansTick -forgeCaptures "$env:TEMP\lot690-sans-tick" -logFile "$env:TEMP\lot690-sans-tick.log"`. Ce drapeau, traité uniquement dans `Lot690.cs`, omet seulement le POST du tick. Après le reçu accepté, laisser au moins deux périodes de lecture du passage, service joignable, en vérifiant à chaque image que le panneau reste caché et la scène inchangée ; relire `/monde` pour confirmer tick N et maison absente. Puis garder l'exigence positive de SC2 sur le message : sortie 1 pour message attendu mais absent, avec ces observations dans le diagnostic. Une panne, une erreur de compilation ou une exception inconditionnelle liée au drapeau ne compte pas. Contre-épreuve : enlever seulement le drapeau rend SC2 vert.

SC4 — La photo contient le vrai panneau. Exécuter aussi `CAPTURE -forgeCaptures "$env:TEMP\lot690-pilote" -logFile "$env:TEMP\lot690-pilote.log"`, avec les ticks par défaut du pilote : sortie 0, contrôles relatifs à N, sans tick final figé. Ouvrir soi-même les PNG `*--bar-sans-kit.png` des deux lancements normaux : carte lisible et message entier, sans vue du désert ni message d'absence. Le cabinet reste construit et actif. Contre-épreuve : une toile encore reliée à la caméra désactivée, un texte hors champ ou masqué refuse la livraison même avec sortie 0 ; la photo initiale ne remplace pas celle du scénario.

SC5 — Diff borné. Exécuter `git diff --check`, `git diff --name-only`, `git diff --numstat` et `git ls-files --others --exclude-standard`. Compter le brief et les fichiers neufs : moins de 300 lignes ajoutées et retirées, uniquement les cinq chemins du périmètre. Contre-épreuve : une scène réécrite, un fichier d'interface modifié, un test existant assoupli ou 300 lignes refuse la livraison.

## Hors périmètre
Toute écriture dans `Assets/Interface`, les scènes, leurs constructeurs, les autres captures, le harnais et les paramètres Unity. Aucun changement de `TerresAvecKit`, de l'aiguillage, des clients, des fixtures ou de `jeu/`. Pas de nouveau kit pour Bar, de retour ville/carte (#410), de lanceur (#682), de relief (#683), ni de nouvelle règle de choix.

## Photo
Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot690.cs` et laisse Unity générer son `.meta`. Le scénario joue SC2 avec le vrai service, copie le cadrage de la carte par `Lot549.Photographier`, puis rebranche explicitement la toile du passage sur la caméra reçue par le scénario : elle est sans parent, donc l'aide de #549 ne la parcourt pas. La retrouver par son lien à l'ancienne caméra et son message, en exigeant une seule correspondance ; ne pas recréer le panneau, changer son texte, sa position ou forcer sa visibilité. Garder son mode `ScreenSpaceCamera`, sa distance de plan et le viewport du cabinet. Contrôler la caméra de la toile, son activité et les limites du texte dans le champ, attendre dix images et revérifier message, maison et scène. La photo montre la carte avec « Pas encore de kit pour cette terre » après le choix de Bar au tick N+1 ; les PNG restent hors du dépôt. Le compte rendu rapporte les commandes, le rouge initial, la contre-épreuve sans tick et l'inspection des images.
