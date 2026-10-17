# Lot #614 — La caméra descend sur ses lieux
Jalon : J3 · Machine : pc · Taille prévue : 295 lignes

## But
Après application du choix de sa terre, le joueur arrive au-dessus de son siège et reconnaît ses lieux sur la carte par leur surlignage.
## Le joueur
« Quand `/monde` nomme la maison du joueur, l'écran lit sa fiche dans `/maison`, la caméra va au siège, les lieux du joueur sont surlignés à une couleur du joueur qui tranche sur celle de sa puissance, et les repères de départ s'effacent ; la capture montre Mistra et ses lieux surlignés. » Découpé de #404, ce lot prépare le geste de J3 porté par #405 : fixer la part prise sur ses lieux et ouvrir son grenier. Le joueur voit de quels lieux il vit, sans confondre son petit domaine avec toute la puissance qui l'abrite.
## Règle du monde
Sans objet : lot de vue, aucune règle ni donnée du monde ne change. Contrats lus dans `jeu/sim/MODELE.md`, « Les intentions du joueur », « Les maisons servies, vue dérivée » et « Les lieux d'une cellule, vue dérivée » : seul `/monde.maison_du_joueur` constate le départ appliqué ; `/maison?id=X` donne le siège et les couples (`cell_id`, `rang`) tenus ; `/lieu?cell=X` donne leurs points et maîtres. Aucune frontière de lieu inventée, aucune seconde clé spatiale. Fidélité héritée : niveau 1 pour Mistra, niveau 2 pour les autres placements plausibles ; aucune calibration du monde.

Dépend de : #611 et #613, présents dans ce chantier. Réutiliser leurs clients ; les lieux ne viennent jamais de `/monde`, et un reçu accepté ne vaut pas choix appliqué.
## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/FicheDeCellule.cs
3d/unity/Assets/ForgeLocal3D/Pont/ReperesDeDepart.cs
3d/unity/Assets/ForgeLocal3D/Pont/VueDeCarte.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ReperesDeDepartTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/VueDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot614.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot614.cs.meta
docs/briefs/614-la-camera-descend-sur-ses-lieux.md

Tout autre chemin est interdit. Budget, ajouts et retraits compris : 110 lignes de production, 65 de tests, 50 de capture, 2 de méta et 68 de brief, soit 295. Garder les responsabilités existantes : pas de nouvelle scène ni de composant à installer.

`FicheDeCellule` utilise `ClientMonde.LireAvecMaison()` dans sa tâche périodique existante et expose `MaisonDuJoueur` ; conserver `MondeLu`, `AbsenceDuMonde`, `Decrire` et les textes actuels. Une réponse absente efface la maison exposée et garde sa cause. Pas de deuxième boucle `/monde`. `ReperesDeDepart.Pas` consulte cette propriété si la fiche existe, avant son retour actuel sur `complet` ; sans fiche ou sans maison publiée, son comportement reste identique. Une tâche hors du fil principal lit la maison publiée, puis une seule fois chaque cellule distincte de ses lieux avec `ClientLieu`. Aucun calcul ni objet Unity dans cette tâche. Lectures et clients sont libérés à l'arrêt.

Avant la pose, vérifier siège placé, liste tenue non vide, chaque couple retrouvé à son rang avec point présent et maître égal à la maison demandée. Une absence, un rang introuvable ou une contradiction nomme sa cause dans le texte en haut à gauche déjà disponible ; aucun point de remplacement, aucun domaine partiel. Retenter après `PERIODE_RELECTURE_S`, sans attendre dans `Pas`. Ces lectures ne prétendent pas former une photographie au même tick : elles servent ici l'installation du domaine, pas des stocks ou des flux.

Sur succès seulement, poser un petit disque plat par lieu tenu, sans collider, au point converti par `CarteDessinee.PositionSurLaCarte`, au-dessus des contours ; identité des objets dérivée du couple cellule/rang. Une même `COULEUR_JOUEUR` blanche, distincte des couleurs des puissances, avec un bord sombre, rend les quatre points visibles ; les cellules et leurs matériaux restent intacts. Le texte en haut à gauche nomme la maison, le siège et le nombre de lieux servis. Cacher les disques et noms des départs, leur fiche survolée et le panneau du choix ; empêcher leur survol et leur clic, y compris si une ancienne lecture des départs se termine ensuite. Garder le reçu disponible dans ses propriétés.

Ajouter à `VueDeCarte` une méthode de centrage avec demi-hauteur demandée, soumise aux bornes existantes. Centrer sur le siège servi et cadrer tous les points tenus, rayon des disques et marge compris, avec au moins `DEMI_MIN_KM` ; utiliser cette vue, jamais déplacer seulement la caméra. La pose se fait une fois : les pas suivants ne dupliquent rien et ne reprennent pas la caméra au joueur. Relecture des changements de propriétaire pendant la partie reportée hors de ce lot.
## Conditions de succès
SC1 — Rouge d'abord, puis régression. À la racine sur le PC, Unity 6000.0.43f1, PowerShell, sans `-quit` :
```powershell
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot614.xml" -logFile "$env:TEMP\lot614-tests.log"
```
Sortie 0, aucun échec ni cas ignoré ; les cas ajoutés sont recensés et effectivement joués, zéro cas neuf échoue. Les nouveaux contrôles doivent échouer avant le code. Ajouter aux deux fichiers autorisés, sans changer aucune méthode, aide, fixture, assertion ou seuil existant. Contre-épreuve : les cas actuels de `ReperesDeDepartTests` comptent toujours six repères et leurs requêtes exactes avant publication du choix ; `ClientMondeHorlogeTests` conserve aussi le cas historique `maison_du_joueur:27` via `Lire()`.

SC2 — La maison publiée déclenche la descente. Commande SC1. Dans de nouveaux cas de `ReperesDeDepartTests`, réutiliser le faux service inchangé : son dictionnaire `maisons` sait déjà servir aussi `/monde` et `/lieu?cell=…`. Ajouter une fiche de cellule au montage neuf et piloter ses pas avec ceux de la carte et des repères. Servir un monde minimal valide sans maison, puis le même avec `maison_du_joueur:"seigneurie-3"` ; construire une réponse `/lieu` valide de cinq lieux placés, quatre tenus et un voisin. Attentes écrites dans le test, indépendantes du code de pose : chaque couple tenu a exactement un disque actif à sa position convertie, le voisin n'en a aucun ; la maison interrogée est celle publiée et la cellule n'est demandée qu'une fois. La caméra quitte la vue entière et son centre correspond au siège servi ; les quatre disques sont dans le champ, zéro départ actif. Contre-épreuves : sans maison publiée, même après un reçu accepté, les six départs restent et la caméra ne descend pas ; une réponse modifiée à trois lieux tenus doit en poser trois, jamais quatre figés.

SC3 — Absence déclarée, puis reprise. Commande SC1. Ajouter des cas paramétrés : maison en 404, siège hors carte avec sa raison, point tenu nul, rang tenu absent, maître contradictoire. Le domaine reste non posé, les repères présents, la caméra inchangée et le texte nomme la cause. Restaurer la réponse puis passer la période de reprise donne le domaine complet et efface l'absence. Contre-épreuve : une origine inventée ou une pose partielle fait rougir ces mêmes cas ; un tableau tenu vide ne peut pas valider la preuve.

SC4 — Rendu et navigation durables. Commande SC1. Vérifier les renderers actifs, leurs matériaux et positions, pas seulement un compteur : couleur du joueur différente de celle de la cellule, bord sombre présent, aucune couleur cellulaire changée. Après succès, survoler et cliquer l'ancien emplacement d'un départ ne dépose rien. Glisser la vue puis faire plusieurs pas conserve le nouveau centre et le nombre d'objets. Ajouter à `VueDeCarteTests` le centrage décentré et le centrage près d'un bord, en réutilisant `DansLaCarte`. Contre-épreuves : un recentrage à chaque pas, un repère encore cliquable ou une sortie des bornes rougit.

SC5 — La capture joue le vrai choix, puis son application. Sur le PC, sans `-quit` ni `-nographics` :
```powershell
Unity.exe -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 614 -forgeSeed 0 -forgeCaptures "$env:TEMP\lot614" -logFile "$env:TEMP\lot614-capture.log"
```
Sortie 0 et journal `CAPTURE_614` : maison publiée, siège Mistra, couples attendus et observés, repères actifs, cadrage. Le scénario attend au plus 30 s par étape. Contre-épreuve, même commande avec `-forge614RetirerLieu` : après la pose, désactiver réellement un disque tenu, puis exécuter le même contrôle ; sortie 1 avec le couple manquant. Le drapeau ne lève pas lui-même une exception ; une panne du service ou de compilation ne prouve rien.

SC6 — Photo et taille. Commandes : SC5, puis `git diff --check`, `git diff --name-only`, `git diff --numstat` et `git ls-files --others --exclude-standard`. Regarder soi-même le `*--mistra-et-ses-lieux.png` : Mistra nommé, ses quatre points visibles et distincts sur la puissance inchangée, aucun disque ni nom de départ, texte de la maison lisible, panneaux sans recouvrement. Contre-épreuve : un point hors champ, masqué, confondu avec le fond ou un ancien départ encore visible refuse la livraison malgré sortie 0. Seuls les chemins du Périmètre changent, moins de 300 lignes ajoutées et supprimées, fichiers neufs et brief inclus ; tout dépassement échoue.
## Hors périmètre
Règles et service Python, clients et leurs contrats, fixtures, tests existants, scène et `CarteBuilder`, `SurvolDeCarte`, captures antérieures et preuve générale de J3. Ni frontières inventées des lieux, ni lieux voisins dessinés, ni flux, part ou grenier (#405), ni nouvelle terre, annulation, changement de siège, animation de transition ou suivi des conquêtes. Aucun PNG dans git.
## Photo
Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot614.cs`, `[ScenarioDeCapture(614, "mistra-et-ses-lieux")]`. Ouvrir avec `Lot549.Ouvrir`, passer parcours et survol en automatique, attendre les six repères ; cliquer la Morée par `SurvolDeCarte`, exiger le reçu accepté, puis constater qu'en pause les départs et la vue entière restent. Faire avancer le vrai service d'un tick par `POST /tick?n=1`, hors du fil principal ; attendre la maison publiée et la descente normale. Lire séparément `/monde`, `/maison` et `/lieu` comme référence indépendante ; exiger Mistra, quatre couples tenus non vides et chacun de leurs objets rendus à sa place, aucun repère actif, siège et disques dans le champ. Appliquer la contre-épreuve SC5 avant ce contrôle si demandée. Copier le cadrage obtenu avec `Lot549.Photographier`, attendre dix images et revérifier ; ne jamais poser les disques ni centrer la vue depuis le scénario. La photo montre le résultat du geste réel : Mistra et ses lieux surlignés, les voisins gardant la couleur de leur puissance.
