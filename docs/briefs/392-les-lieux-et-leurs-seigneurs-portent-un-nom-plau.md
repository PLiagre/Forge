# Lot #392 — Les lieux et leurs seigneurs portent un nom plausible
Jalon : J3 · Machine : vps · Taille prévue : 295 lignes

## But
Le joueur pourra reconnaître les lieux et leurs maîtres par des noms historiques ou plausibles, identiques dans la photographie et `/lieu`.

## Le joueur
Sur la carte et dans les panneaux, le joueur lit « Haute-Rive, tenu par Gauthier de Vaux » plutôt que « lieu 10430-5, maison plausible-10430-4 » : ses voisins deviennent des gens, et ses lieux des endroits. Ce lot fournit les noms aux écrans ; #401 les rendra visibles sur la carte de la forge, #403 dans Unity. Il prépare le geste de J3 : reconnaître ses lieux et ceux des voisins avant de choisir combien prendre aux siens ou leur rendre du grain, pour remplir son grenier sans perdre ses gens.

## Règle du monde
Sans objet pour le tick : c'est une vue pure. Dépend de : #391, dont l'attribution et la publication des maîtres ont été livrées par #535 et #536. Découle de `jeu/sim/MODELE.md`, « Les lieux d'une cellule », « L'identité d'un lieu, et ce qui la change » et « Les maisons du monde ». **Niveau 1** : noms des sièges et villes, repris des données historiques existantes. **Niveau 2**, plausible, jamais sourcé : listes de noms, prénoms, aires et leur attribution. Aucun personnage, effet économique ni seconde clé spatiale n'est créé.

`sim/noms.py` charge et valide `data/noms-1400.json` par une fonction acceptant un chemin alternatif. Le fichier contient, par aire, les listes de lieux, maisons et prénoms de chefs, ainsi que des règles ordonnées d'attribution selon la puissance, sa religion et les coordonnées du centroïde. Prévoir au moins oïl, oc, germanique, italienne, ibérique, grecque, slave du Sud, hongroise, turque, arabe et berbère ; compléter pour les autres régions présentes. La religion vient de la table des puissances, pas d'un champ inventé sur la cellule. Les cellules sans puissance ont des règles géographiques explicites avec puissance et religion absentes déclarées ; aucun repli silencieux vers une langue. La première règle applicable détermine l'aire ; aucune règle, une aire sans listes, une liste vide, un élément vide ou des doublons sont refusés avec l'aire et la donnée en cause, ou la cellule sans règle.

Le choix dépend seulement de `cell_id` et du rang, dans des listes ordonnées : décalage déterministe et parcours sans réemploi dans la cellule, sans `hash()` de processus ni générateur aléatoire. Les listes doivent suffire au découpage réel ; une insuffisance est refusée explicitement, sans suffixe technique inventé. Le maximum actuel est 37 lieux, mais la capacité se vérifie depuis les données. Les maisons plausibles utilisent leur cellule et leur rang initial du registre, jamais le rang du lieu consulté : tous les lieux d'une maison montrent le même nom et le même prénom. Les noms de lieux sont distincts dans une cellule ; les noms des maisons plausibles le sont aussi, donc leurs chefs complets ne se confondent pas.

Le bourg de rang 0 prend d'abord le nom du siège d'une seigneurie placée dans la cellule ; plusieurs seigneuries se départagent par id croissant, comme l'attribution. Sinon, une ville attribuée par `attribuer_villes` lui donne son nom : population historique maximale, puis nom croissant à égalité. Sinon, son nom est plausible. Les autres rangs restent plausibles ; réserver le nom historique avant le parcours évite toute collision avec lui. Lire les sièges dans le registre déjà chargé et les villes dans leurs lecteurs existants, sans copier de faits historiques dans la nouvelle table ni déplacer une ville hors carte. Les maisons historiques gardent leur nom du registre ; leur prénom de chef reste `null`, absence déclarée, sans personne historique devinée.

Suivre **B**, décidé par le pilote : chaque cellule photographiée et chaque réponse `/lieu` reçoit un bloc frère de `lieux`, `noms = {"lieux": [{"rang": R, "nom": N}], "maisons": {IDENTIFIANT: {"nom": N, "prenom_chef": P}}}`. Les lieux suivent les rangs ; les maisons sont celles qui tiennent ces lieux, triées par identifiant. L'identifiant est une clé du dictionnaire, reliée à `lieux[].maitre`, sans champ `id` ou `*_id` supplémentaire. Un maître `None` d'un état manuel ne produit aucune maison devinée. Une même fonction pure fournit ces blocs aux deux publications, calculée pour le monde hors du tick, avec réemploi des attributions historiques disponibles. `/lieu` construit ses octets dans `EtatPublie` ; une lecture HTTP ne consulte pas le monde mutable. Les champs exacts des lieux, le registre et `World.to_dict()` restent intacts ; `/monde` et la version du schéma restent inchangés.

Dans « Les lieux d'une cellule », documenter les noms, leur provenance, la priorité historique, le bloc publié et ce qui les change : version des listes ou règles, données historiques, puissance/religion/position ou découpage. À carte, tables et rangs identiques, graine, tick, population, faim, maître consulté et ordre des dictionnaires ne changent pas le nom d'un lieu. Corriger les seules mentions disant les noms non simulés, aussi dans « Les maisons du monde » ; garder les descriptions et mots contrôlés des champs servis. Le nom de maison suit sa fiche, pas le lieu qu'elle tient. Documenter le bloc dans `jeu/ville/README.md`.

Budget, ajouts et retraits compris : brief 60, données 55, vue et raccords 75, preuves nouvelles 75, adaptations des contrôles figés et documentation 26, deux réponses JSON 4 ; total 295. Employer des listes JSON lisibles et des preuves paramétrées ; aucune modification du moteur ou du registre n'est nécessaire.

## Périmètre
jeu/data/noms-1400.json
jeu/sim/noms.py
jeu/sim/snapshot_export.py
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/ville/README.md
jeu/sim/tests/test_lieux.py
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_determinisme.py
jeu/sim/tests/test_monde.py
jeu/forge/tests/test_forge.py
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick4.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/LecteurJsonTests.cs
docs/briefs/392-les-lieux-et-leurs-seigneurs-portent-un-nom-plau.md

## Conditions de succès
Commandes depuis la racine. Ajouter les preuves aux fichiers qui portent leurs invariants et constater leur rouge avant l'implémentation. Chaque contrôle exige un échantillon non vide, dérive ses cellules, rangs et maisons des données et exerce sa contre-épreuve. Les seules adaptations d'assertions existantes autorisées par B sont l'ajout de `noms` à `_CELL_KEYS` et aux clés racine de la réponse C# figée, les empreintes complètes régénérées et le retrait de ce seul ajout avant les comparaisons anciennes. Conserver toutes les références, assertions et contre-épreuves antérieures, notamment les ensembles exacts des lieux et le contrôle récursif des clés spatiales.

SC1 — `python3 -m pytest jeu/sim/tests/test_lieux.py -q -k noms` : la vue couvre exactement tous les rangs de toutes les cellules, avec noms non vides et uniques par cellule. Le bourg de la cellule du siège de Bar-le-Duc porte exactement « Bar-le-Duc » ; contrôler aussi Stuttgart et Mistra. Tester une cellule avec plusieurs villes et le cas siège contre ville. Contre-épreuves : retirer un rang, vider un nom, dupliquer deux noms ou remplacer Bar-le-Duc par un nom plausible fait échouer le vérificateur ; inverser les populations des villes témoins change la priorité attendue.

SC2 — `python3 -m pytest jeu/sim/tests/test_lieux.py -q -k noms` : toutes les règles référencent des listes valides ; sur une cellule grecque réelle avec un rang non historique, le nom appartient à la liste grecque. Exercer aussi les critères géographiques, religieux et une cellule sans puissance. Contre-épreuves paramétrées sur des fichiers temporaires : vider chacune des trois listes, retirer une aire référencée, ajouter un texte vide ou un doublon, enlever la règle nécessaire ou réduire la liste sous la capacité de la cellule ; le chargement ou la projection refuse en nommant précisément la donnée. Un nom d'une autre aire échoue à l'appartenance attendue.

SC3 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k noms` : chaque maison plausible reçoit nom et prénom non vides issus de son aire ; les noms de maison sont uniques dans sa cellule, et ses lieux partagent exactement la même fiche publiée. Les maisons historiques gardent leur nom et un prénom `null`. Contre-épreuves : échanger une fiche entre deux maisons, attribuer un autre prénom à un seul lieu ou remplacer un nom historique fait échouer l'égalité avec la vue ; supprimer une maison tenue échoue à la couverture exacte.

SC4 — `python3 -m pytest jeu/sim/tests/test_determinisme.py -q -k noms` : mêmes noms sur deux chargements, graines différentes, ordre des cellules et du registre inversé, et après des ticks économiques ; consultations répétées sans mutation des cartes, tables, registre, monde ni état du générateur. Pendant le tick, remplacer les fonctions de noms par des fonctions qui lèvent : le tick réussit et conserve les mêmes empreintes complètes qu'un témoin, générateur compris. Contre-épreuves : un nom altéré échoue à la comparaison ; un lecteur factice qui écrit ou tire de l'aléa échoue au contrôle de pureté ; un appel factice à la vue pendant le tick déclenche la garde.

SC5 — `python3 -m pytest jeu/sim/tests/test_monde.py -q -k "noms or photographie_1400_schema or lieux_de_la_photographie or sans_seconde_cle"` : pour toutes les cellules au même tick, `/lieu.noms` égale exactement `photographie.cells[].noms` et la vue pure, rangs et maisons compris. Le nouveau bloc est obligatoire dans les ensembles exacts des cellules ; les lieux gardent leurs cinq champs exacts. Contre-épreuves : retirer le bloc, changer un nom ou relier une fiche au mauvais maître échoue ; les anciennes contre-épreuves d'habitants déplacés, tick décalé et clé spatiale ajoutée restent actives.

SC6 — `python3 -m pytest jeu/sim/tests/test_monde.py -q -k "service_ia_sans or reponse_figee or logement_sans_geste or lecteur_json or noms"` et `python3 -m pytest jeu/forge/tests/test_forge.py -q -k forge_ia_sans` : régénérer les deux JSON depuis le vrai service et les empreintes complètes de `/lieu` aux ticks 0 et 4 et de la forge aux ticks 0 et 30. Retirer seulement `noms`, puis resérialiser avec `_serialiser` ou `serialize_snapshot`, retrouve chaque empreinte actuelle avant #392, conservée comme référence ; les contrôles plus anciens retirent ensuite `maitre` comme avant. `/monde` garde ses empreintes. Les fichiers figés restent égaux aux octets servis ; l'édition de texte C# ajoute la clé racine et vérifie le bloc, sans changer les attentes des lieux ni exécuter Unity. Contre-épreuves : bloc absent ou nom modifié échoue au contrôle complet ; après retrait de `noms`, ajout de `ia` ou changement d'une population échoue encore à l'ancienne empreinte. Vérifier en Python les nouvelles attentes du texte C#, avec copie privée de `noms` qui échoue.

SC7 — `python3 -m pytest jeu -q` et `git diff --check` réussissent. Les contrôles documentaires existants restent intacts ; ajouter une preuve de la provenance et de la stabilité des noms dans « Les lieux d'une cellule », dont une copie privée de cette description échoue. Vérifier avec `git diff --numstat` que le diff livré, brief compris, reste strictement sous 300 lignes ajoutées et retirées ; un décompte atteignant 300 échoue.

## Hors périmètre
Écrans et carte de la forge ou Unity (#401, #403), exécution Unity/Blender, position des lieux (#393), personnes et succession, changement de maître, prélèvement et redistribution. Aucun nom stocké dans `Cell`, `EtatDeLieu` ou `World`, aucun changement du registre, des identifiants, de l'aléa, des règles du tick ou des données historiques existantes. Aucun test rendu moins exigeant. Tout chemin absent du périmètre est interdit.
