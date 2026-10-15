# Lot #626 — La scène Carte montre les six terres de départ
Jalon : J3 · Machine : pc · Taille prévue : 285 lignes

## But
En ouvrant la scène Carte, le joueur voit les six terres de départ, chacune nommée et repérée sur son siège.

## Le joueur
En ouvrant la carte de 1400, le joueur voit les six terres où il peut commencer, chacune à sa place et nommée, et peut situer son futur domaine parmi les puissances voisines. Ce sous-lot 2 de #623 rend visible le composant livré par #625 et prépare le choix de sa terre de #404, puis le geste de J3 : gouverner ses lieux, fixer sa part et ouvrir son grenier. La fiche au survol et le choix effectif restent aux lots suivants.

Dépend de : #625, dont `ReperesDeDepart`, ses observables et ses tests sont déjà présents dans ce chantier.

## Règle du monde
Sans objet : lot de vue. Les terres viennent de `/departs`, les sièges de `/maison`, selon « La carte et les terres servies, vue dérivée » et « Les maisons servies, vue dérivée » de `jeu/sim/MODELE.md`. Le composant de #625 les affiche ; aucune donnée historique, règle, constante du monde ou clé spatiale ne change.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/CarteBuilder.cs
3d/unity/Assets/ForgeLocal3D/Carte/Forge_Carte.unity
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot626.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot626.cs.meta
docs/briefs/626-la-scene-carte-montre-les-six-terres-de-depart.md

Dans `CarteBuilder.Construire`, ajouter une seule fois `ReperesDeDepart` au même objet « Carte de 1400 » que `CarteDessinee`. Régénérer la scène avec ce constructeur, sans retouche manuelle du YAML. Les identifiants internes régénérés sont attendus ; le GUID du fichier scène reste celui de son `.meta` existant. La liste du build est déjà correcte et ne doit pas changer.

`Lot626.cs` porte `[ScenarioDeCapture(626, "six-terres-de-depart")]`. Il ouvre la scène sauvegardée par `Lot549.Ouvrir`, en déroulant son énumérateur comme les captures #525 et #526 ; il exige le composant présent dans cette scène et ne l'ajoute jamais lui-même. Après attente bornée à 30 s des repères, il photographie par `Lot549.Photographier`, puis laisse dix images de pose. Les erreurs nomment les nombres attendus et observés et `TexteAffiche` si une lecture manque.

## Conditions de succès
SC1 — Rouge d'abord, puis scène branchée. Sur le PC, éditeur fermé, depuis la racine, utiliser Unity 6000.0.43f1, version de `3d/unity/ProjectSettings/ProjectVersion.txt`. Écrire d'abord le scénario et lancer la commande SC2 sur l'ancienne scène : sortie 1 pour composant absent, avec compilation et service fonctionnels. Puis exécuter en PowerShell :
```powershell
Unity.exe -batchmode -quit -projectPath 3d/unity -executeMethod ForgeLocal3D.CarteBuilder.Construire -logFile "$env:TEMP\lot626-scene.log"
```
Sortie 0 ; la scène sauvegardée porte exactement un `ReperesDeDepart` sur l'objet de la carte, et SC2 passe. Contre-épreuve : la scène sans ce composant fait toujours échouer SC2 ; le scénario ne répare pas la scène à sa place.

SC2 — La carte entière porte les six terres réellement servies. Sans `-quit` ni `-nographics` :
```powershell
Unity.exe -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 626 -forgeSeed 0 -forgeTicks 3 -forgeCaptures "$env:TEMP\lot626-normal" -logFile "$env:TEMP\lot626-normal.log"
```
Sortie 0, scénario effectivement joué et journal `CAPTURE_626` avec les comptes. Le scénario lit indépendamment `/departs` par `ClientDeparts`, sur le port du composant : absence ou liste vide échoue, la référence contient six fiches. Sous « Repères des terres de départ », les enfants actifs sont exactement ces six « Repère <nom> », sans doublon ; leur nombre égale `ReperesPoses` et celui des fiches servies. Chacun possède son disque avec renderer actif et son nom en `TextMesh`. Leurs positions sont dans le champ de la caméra photographiée, entre ses plans de coupe ; les cellules posées restent égales aux cellules servies, non nulles, et la vue reste celle de la carte entière. Contre-épreuve : cinq objets réels, même avec `ReperesPoses == 6`, doivent échouer selon SC3 ; aucun succès fondé sur le seul compteur du composant.

SC3 — Un repère retiré fait rougir la capture. Le drapeau suivant est traité seulement dans `Lot626.cs` : après la pose complète, désactiver `ReperesDeDepart`, détruire un enfant repère réel et laisser passer une image, puis exécuter les mêmes contrôles que SC2, sans modifier leur référence :
```powershell
Unity.exe -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 626 -forgeSeed 0 -forgeTicks 3 -forge626RetirerRepere -forgeCaptures "$env:TEMP\lot626-manque" -logFile "$env:TEMP\lot626-manque.log"
```
Sortie 1 pour cinq repères réels au lieu des six servis ; ni compilation impossible, ni service absent, ni exception volontaire déclenchée par le drapeau ne prouvent ce contrôle. Contre-épreuve : retirer seulement le drapeau rend SC2 vert.

SC4 — Les invariants existants restent verts. Exécuter :
```powershell
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot626-tests.xml" -logFile "$env:TEMP\lot626-tests.log"
```
Sortie 0, XML sans échec ni cas ignoré ; `ReperesDeDepartTests` et `CarteDessineeTests` sont effectivement joués. Aucun test existant n'est modifié : les comptes de maillages des tests de carte isolée ne changent pas quand le constructeur de scène reçoit un autre composant. Contre-épreuves : les cas existants de maison absente exigent cinq repères, ceux sans service zéro ; les nouvelles gardes de scène et de capture rougissent selon SC1 et SC3.

SC5 — La photo montre le résultat. Exécuter SC2, puis ouvrir son fichier `*--six-terres-de-depart.png` : carte entière, six disques distincts et leurs noms, du Zab aux terres d'Europe, sans panneau du désert ni message d'absence. Le codeur et le relecteur regardent eux-mêmes cette image. Contre-épreuve : une simple photo initiale du désert, un cadrage coupé, un repère masqué ou un nom illisible refuse la livraison même avec sortie 0.

SC6 — Taille et chemins. Exécuter `git diff --check`, `git diff --name-only`, `git diff --numstat` et `git ls-files --others --exclude-standard`. Seuls les cinq chemins du Périmètre sont autorisés ; compter aussi les fichiers neufs et ce brief, ajouts et retraits cumulés : moins de 300 lignes. Budget : environ 100 lignes pour la scène régénérée, 90 pour la capture, quelques lignes de constructeur et de `.meta`, le reste pour ce brief. Contre-épreuve : un chemin supplémentaire ou un total de 300 lignes refuse la livraison.

## Hors périmètre
Le composant `ReperesDeDepart`, sa conversion et ses tests, les clients HTTP, les fixtures et toute la simulation. Aucun clic de choix, fiche de terre au survol, changement de couleur ou de taille des repères, ajout de terre, règle historique ou geste de prélèvement. Les autres captures, dont `Lot549.cs`, restent inchangées ; ni scène du désert, ni paramètres du projet, ni liste du build ne changent.

## Photo
`3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot626.cs`, lancé par SC2, ouvre `Forge_Carte` par `Lot549.Ouvrir`, attend les repères issus du vrai service, puis copie le cadrage de la carte entière par `Lot549.Photographier`. La photo `*--six-terres-de-depart.png` montre les six terres nommées à leur siège sur la même carte de 1400. Elle est produite dans le dossier temporaire de capture pour le pilote, sans ajouter de PNG au dépôt ; moins de six repères réels fait échouer le scénario.
