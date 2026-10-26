# Lot #730 — Une touche ramène de la ville à la carte, et Espace met la ville en pause
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Le joueur revient de sa ville à la carte avec C et suspend ou reprend le temps de la ville avec Espace.

## Le joueur
Dans la scène de la ville, C, à la même place en AZERTY et en QWERTY, ramène à `Forge_Carte` par la transition ; Espace met en pause ou reprend au rythme de la ville, et l'aide lui rappelle ces deux gestes. Il peut regarder et préparer ses constructions sans laisser filer les jours, puis retrouver ses terres d'une touche : c'est le passage carte–capitale de J4, issu de #410.

Dépend de : #728, présent sur la base : `TransitionDeVue`, `ReglagesDesVues` et leur ressource existent. La ville porte déjà `DesertRoadTool` et la carte `HorlogeDeCarte`. Ce lot n'attend ni la preuve de J3, ni le branchement carte–ville de #729, ni le lanceur de #731.

## Règle du monde
Sans objet : commandes de vue et de l'horloge existante, aucune règle de simulation modifiée. Le service reste seul maître des ticks ; aucun `Time.timeScale`, compteur local de jours ou appel automatique à `/tick`.

C lance `TransitionDeVue.Lancer(OuvertureDeLaCarte.SCENE, VueDuJeu.Carte, port)` : le monde en marche passe à `VITESSE_CARTE` après le chargement. Comme le garantit #728, un monde déjà en pause reste en pause pendant le retour. Espace lit `/horloge`, puis demande `0` si le monde avance, sinon `ReglagesDesVues.Charger().VitesseVille` par `ClientHorloge.Regler`. Reprendre n'utilise ni la dernière vitesse de la carte, ni le repli à 1 de `HorlogeDeCarte`.

## Périmètre
- docs/briefs/730-une-touche-ramene-de-la-ville-a-la-carte-et-espa.md
- 3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
- 3d/unity/Assets/ForgeLocal3D/Pont/CommandesDeVille.cs
- 3d/unity/Assets/ForgeLocal3D/Pont/CommandesDeVille.cs.meta
- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/TransitionDeVueTests.cs
- 3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot730.cs
- 3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot730.cs.meta

## Conditions de succès
Écrire les nouveaux cas et constater leur échec avant le code. Ajouter les cas au faux service de `TransitionDeVueTests`, sans retirer, renommer ou assouplir les cas existants. Le petit auxiliaire `CommandesDeVille` expose les actions testables ; `DesertRoadTool.Update` les branche sur `Keyboard.current.cKey.wasPressedThisFrame` et `spaceKey.wasPressedThisFrame`, derrière sa garde `automatique`. Il transmet son port réel. Aucun changement de scène sérialisée ni référence au clavier dans l'assemblée `Forge.Pont`.

Commande T, depuis la racine, dans PowerShell sur le PC, éditeur fermé : `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot730.xml" -logFile "$env:TEMP\lot730-tests.log"`. Sans `-quit` ; exiger une sortie 0 et un XML sans échec, avec chaque nouveau cas exécuté. Un XML absent ou zéro cas échoue.

SC1 — T vérifie que l'action de retour lance une seule transition vers `Forge_Carte`, avec fondu, puis envoie la vitesse de carte lue dans la ressource, sur le port du faux service. Deux demandes pendant le fondu ne chargent qu'une fois. Ajouter un cas de retour depuis la pause : scène chargée, vitesse toujours 0, aucun POST de vitesse. Contre-épreuve : remplacer la destination par la ville, supprimer le passage par la transition ou réveiller un monde en pause fait échouer ces cas.

SC2 — T vérifie Espace à partir d'une vitesse positive distincte des deux vitesses de vue : GET puis POST à 0 ; l'action suivante fait GET puis POST à `VitesseVille`. Tester aussi une ville ouverte alors que le service est déjà à 0 : elle reprend à `VitesseVille`. Les attentes sont bornées à 10 s ; les vitesses attendues viennent de la ressource. Contre-épreuve : reprendre à 1 ou à la vitesse précédente, ou ne régler que le temps d'Unity, fait échouer les assertions sur les requêtes reçues et la vitesse servie.

SC3 — T vérifie qu'une lecture d'horloge absente ou en erreur interdit le POST de pause/reprise et expose la cause, sans vitesse inventée. Le réseau reste hors du fil principal ; un service retenu ne bloque pas l'appel de l'action, borné à 200 ms, et les demandes de pause ne se chevauchent pas. Une pause en vol doit finir ou être annulée avant le retour, pour qu'aucun ancien POST n'écrase ensuite la vitesse de carte. Contre-épreuve : POST malgré un GET manqué, appel réseau bloquant ou réponse tardive qui remet la carte à 0 fait rougir les nouveaux cas de T.

SC4 — Commande P : `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 730 -forgeSeed 0 -forgeTicks 30 -forgeCaptures "$env:TEMP\lot730-photos" -logFile "$env:TEMP\lot730-photo.log"`. Sans `-nographics` ni `-quit`. Le scénario joue les vraies touches par le système d'entrée, avec relâchement entre pressions ; il vérifie aussi que `automatique` les ignore. L'aide visible contient « C : carte » et « Espace : pause / reprendre » dans les modes route, parcelle et bâtiment, y compris après le rafraîchissement du plan. Contre-épreuve : débrancher C ou Espace dans `Update`, supprimer une mention de l'aide ou ignorer `automatique` fait sortir P en échec ; appeler seulement les auxiliaires ne prouve pas ce branchement.

SC5 — T laisse notamment `HorlogeDeCarteTests`, `PassageALaCapitaleTests` et tous les anciens cas de `TransitionDeVueTests` verts. `git diff --check`, `git diff --name-only` et `git ls-files --others --exclude-standard` contrôlent les espaces et le périmètre ; le diff total du lot reste inférieur à 300 lignes ajoutées et retirées. Contre-épreuve : un test existant assoupli, un fichier hors périmètre ou un diff trop grand refuse la livraison.

## Hors périmètre
Le trajet carte–ville, le choix de terre ou de capitale, le lanceur, les règles du monde, les vitesses configurées, les paliers et boutons de la carte. Ne modifier ni `HorlogeDeCarte`, ni `TransitionDeVue`, ni `ClientHorloge`, ni les scènes, ni `ForgeCapture`, ni les autres captures. Garder les gestes de route, parcelle, bâtiment, caméra et marche ; C et Espace fonctionnent dans chacun de ces modes. Aucun test existant n'a à rougir du comportement demandé.

## Photo
`Lot730.cs` déclare deux scénarios ordonnés : `01-ville-et-aide`, puis `02-carte-apres-retour`. La commande P lance son propre service en pause ; ne pas lancer de second service. Réutiliser les aides de capture déjà sur la base lorsque cela réduit le code.

Le premier scénario cadre la ville avec `DesertCityCamera.VueEnsemble` ou `Poser`, rend l'aide lisible en entier et joue Espace : reprise à `VitesseVille` confirmée par `/horloge`, puis nouvelle pression et pause confirmée. Vérifier deux lectures de tick identiques en pause, espacées d'au moins une seconde. Vérifier les mentions d'aide dans les trois modes, puis revenir au mode route pour la photo. Ne pas fabriquer un texte réservé à la capture.

Le second reprend par Espace, attend l'accusé du service puis joue C. Utiliser le vrai fondu et son vrai réglage de vitesse. Uniquement dans le scénario, remplacer `TransitionDeVue.ChargerScene` par un chargement additif de la scène demandée pour conserver la caméra reçue par la capture ; aucune ouverture indépendante de carte ne doit remplacer C. Mettre la carte en scène active, écarter le désert et son aide, attendre la fin du fondu et une carte non vide (`CellulesPosees == CellulesServies > 0`), puis cadrer avec `Lot549.Photographier`. Exiger que l'horloge affiche la vitesse de carte effectivement relue au service. Chaque attente a une borne et lève une erreur si la condition manque.

P doit produire les deux PNG des scénarios, de contenu différent ; leur absence échoue. Le codeur ouvre lui-même les deux images : ville et aide lisibles sur la première, carte et horloge lisibles après retour sur la seconde, sans noir résiduel. Une image vide ou une aide coupée refuse la livraison même si T est verte.
