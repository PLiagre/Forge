# Lot #703 — Le verdict de l'épreuve de la capitale
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Le joueur peut se fier au passage de la carte à sa capitale : une épreuve vérifie que le Zab ouvre le siège du monde au tick suivant et que Bar reste sur la carte avec son message sans kit.

## Le joueur
Le joueur choisit l'émirat du Zab dans le cabinet de la carte et entre, au tick suivant, dans Biskra, sa capitale ; avec le duché de Bar, il reste sur la carte et lit « Pas encore de kit pour cette terre ». Il retrouve la terre qu'il a choisie, sans être envoyé dans une autre ville. C'est le geste de J4 « passe de la carte à sa ville d'un geste » (`CAP.md`), rendu visible par #690 et #701, et joué par la session #702.

Ce lot de fond termine l'épreuve #684 : #702 relève ce que Unity ouvre, #703 le juge contre le siège servi par le monde. Il ne prouve ni les chantiers payés ni tout J4 (#508).

Dépend de : #702, livré sur la base `24fbba4`, avec `Editor/EpreuveCapitale.cs` et les rapports `docs/mesures/702-session-capitale/rapport-{zab,bar}.json`. #701 et le passage du siège à l'outil de ville sont également présents. Aucune livraison encore attendue de J3 n'est nécessaire.

## Règle du monde
Sans objet : outil d'épreuve, aucune règle ni donnée du monde ne change. Il vérifie les règles existantes de `jeu/sim/MODELE.md`, sections « Les intentions du joueur » (le choix s'applique au tick suivant) et « Les maisons servies, vue dérivée » (`GET /maison?id=X`, siège dans `siege.cell_id`). `cell_id` demeure la seule clé spatiale. Aucun niveau de vraisemblance nouveau.

Le codeur crée `pc/epreuve_capitale.py`, en réutilisant les aides de `pc/epreuve_carte.py` comme le fait `pc/epreuve_moree.py` : chargement du module, `_lancer_service`, `_arreter`, `_requete`, recherche et lancement borné d'Unity via `JALON1`. Ces modules restent inchangés.

Commande depuis la racine, éditeur fermé :

```powershell
py pc\epreuve_capitale.py --sortie D [--seed S] [--unity CHEMIN]
```

1. Préparer une sortie sans anciens rapports ni verdict réutilisables, puis vérifier Unity et le port 8000 libre. Pour chacun des deux essais, **lancer puis arrêter un service distinct**, graine S (défaut 0), en pause ; arrêt garanti par `finally`, y compris en cas d'erreur.
2. Dans chaque service neuf, lire `/departs` et `/monde` avant le choix. Retrouver les fiches par les noms exacts « Émirat du Zab » et « Duché de Bar », jamais par les ids 6 et 1 ni par leur position. Fiche absente ou ambiguë : impossible. Retenir la fiche de l'essai et `t = departs["tick"]` ; la maison attendue est `seigneurie-<id servi>`.
3. Appeler la session inchangée : `Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveCapitale.Jouer -logFile D/unity-<zab|bar>.log -forgeEpreuve D/rapport-<zab|bar>.json -forgeTerre <id servi>`. Ni `-quit` ni `-nographics`. Aucune cellule attendue n'est transmise à Unity. **La session pousse déjà l'unique tick** : le script ne poste ni intention, ni tick, ni vitesse.
4. Après la session, lire `/monde` et `/maison?id=seigneurie-<id servi>`. La référence spatiale est exclusivement `maison["siege"]["cell_id"]`, pas `depart["cell_id"]`, le rapport Unity, un argument ou 10103. Vérifier l'identité de la fiche et un siège renseigné ; aucune valeur de remplacement. Garder les références en mémoire pour le jugement avant d'arrêter le service.
5. Isoler une fonction pure `juger(rapport, departs, maison, avant, apres, avec_kit) -> (code, lignes)`, utilisable sur le VPS sans Unity. `avec_kit` est vrai pour l'essai Zab et faux pour Bar, jamais déduit du rapport ; le juge retrouve la fiche attendue par son nom dans `departs` et y lit t. Elle compare :
   - `rapport.terre` à l'id servi ; `avant.tick`, `rapport.tick_avant` et `rapport.choix.tick` à t ; aucune maison du joueur avant le choix ; reçu `{statut: 200, tick: t, raison: ""}` ;
   - `rapport.tick_apres`, `apres.tick` et `maison.tick` à t + 1 ; `apres.maison_du_joueur` à la maison attendue ;
   - Zab : scène `Forge_Desert_Ville_ksar_des_sept_puits`, cellule égale au siège servi, `tick_ouverture` t + 1, panneau exactement `Cellule <siège servi> · tick <t + 1>`, message vide ;
   - Bar : scène `Forge_Carte`, `cellule` et `tick_ouverture` à −1, panneau vide, message exactement « Pas encore de kit pour cette terre ».
6. **0** : les deux essais sont égaux ; **1** : au moins un résultat lisible diffère ; **2** : épreuve impossible, prioritaire sur 1. Unity absent, port pris, lancement/délai/code Unity non nul, rapport absent ou ancien, JSON ou champs requis invalides, `defaut` non vide, référence illisible ou siège absent donnent 2 avec leur raison. Un rapport complet, sans défaut, qui ouvre ailleurs ou ouvre une ville pour Bar donne 1. Les sentinelles −1 de Bar sont des mesures attendues ; elles ne remplacent jamais un champ absent. Une entrée vide ne donne jamais 0.
7. Écrire `D/verdict.txt` et afficher le résultat : `ÉGALITÉ`, `ÉCART` ou `ÉPREUVE IMPOSSIBLE`, code, graine, noms et ids servis, maison et siège de référence, puis valeurs observées et attendues pour chaque essai. Chaque comparaison finit par `· égal` ou `· ÉCART` ; une impossibilité nomme l'étape et sa cause. Une impossibilité précoce n'est pas couverte par un ancien verdict.

Budget de réalisation : environ 145 lignes de script, 95 de tests paramétrés, 15 de README et 30 de verdicts ; moins de 300 lignes au total, sans recopier les aides ni les rapports #702.

## Périmètre
pc/epreuve_capitale.py
jeu/ville/tests/test_epreuve_capitale.py
jeu/ville/README.md
docs/mesures/703-epreuve-capitale/verdict-normal.txt
docs/mesures/703-epreuve-capitale/verdict-contre-epreuve.txt

Tout autre chemin est interdit. Les rapports #702 et les fixtures du pont se lisent sans être modifiés.

## Conditions de succès
SC1 — **Le jugement peut rougir sur le VPS.** `python3 -m pytest jeu/ville/tests/test_epreuve_capitale.py -q` passe, après avoir montré son échec avant le script. Les tests chargent le script comme `test_epreuve_moree.py`, les deux vrais rapports #702, la fixture `Pont/Tests/departs-graine0-tick3.json` ramenée au tick 0 et les fixtures `maison-{zab,bar}-graine0-tick0.json`, copiées au tick 1. `avant` est au tick 0 sans joueur, `apres` au tick 1 avec la maison de l'essai. Ces adaptations de fixtures sont explicites, sans présenter ces copies comme de nouveaux relevés PC. Les deux rapports donnent 0 ; chaque comparaison est égale et l'échantillon comporte bien Zab et Bar.

Contre-épreuves paramétrées, par copies en mémoire des mêmes rapports :

- Zab avec `cellule = 1175`, puis avec **cellule et panneau tous deux à 1175** : 1, attendu toujours le siège 10103 ; une scène fausse, un panneau faux ou `tick_ouverture = 0` donnent aussi 1 ;
- Bar avec une ville ouverte (scène, cellule, tick et panneau de ville), ou avec le message vidé/modifié : 1 ; un simple changement de scène de Bar suffit également ;
- un tick après égal à t ou t + 2, un reçu refusé, une maison retenue différente : 1 ;
- changer uniquement le siège de la référence Zab en 99999 laisse le rapport original en écart ; aligner ensuite cellule et panneau sur 99999 rétablit 0, même si `depart.cell_id` reste 10103 : l'attendu vient réellement de `/maison` ; réordonner les départs ne change pas les terres trouvées ;
- rapport vide, champ requis manquant, défaut explicite, fiche absente ou siège nul : 2, jamais égalité par défaut.

SC2 — **L'orchestration est vérifiable sans PC.** La même commande de SC1 éprouve `main` avec les seules aides de processus/HTTP/Unity remplacées : deux services distincts, chacun arrêté, chaque session appelée avec l'id trouvé par nom ; deux rapports frais écrits par le faux appel Unity, aucune requête de mutation envoyée par Python. Contre-épreuves : code Unity non nul, rapport absent/ancien/invalide et échec HTTP rendent 2 et arrêtent le service lancé ; Unity introuvable et port occupé rendent 2 avant toute session. Un Zab observé ailleurs avec session à 0 produit un verdict global 1, pas 2 ; une impossibilité sur Bar le fait passer à 2. Les diagnostics nomment la cause.

SC3 — **Le vrai passage, sur le PC.** `py pc\epreuve_capitale.py --sortie "$env:TEMP\lot703-normal"` rend 0, avec deux services neufs et deux sessions #702. Le verdict contient Biskra au siège 10103 au tick 1, et Bar sur `Forge_Carte` avec le message exact. Copier ce verdict dans `docs/mesures/703-epreuve-capitale/verdict-normal.txt`, précédé de la commande, date, machine, version Unity, révision et code de sortie. Contre-épreuve : SC4 prouve qu'une ville cohérente à l'écran mais située ailleurs ne serait pas acceptée.

SC4 — **Le verdict rouge est conservé.** `python3 -m pytest jeu/ville/tests/test_epreuve_capitale.py -q -k contre_epreuve -s` exécute un cas nommé en conséquence, qui affiche les lignes et le code de `juger` pour le rapport Zab #702 dont cellule et panneau sont changés à 1175. Le test exige **1**, le siège attendu 10103 et deux lignes `ÉCART` (cellule et panneau). Le test passe parce que le jugement refuse la copie. Verser cette sortie dans `verdict-contre-epreuve.txt`, avec commande, date, révision, transformation exacte du rapport et distinction entre code pytest 0 et code du jugement 1. Les rapports sources restent intacts. Contre-épreuve du contrôle : remplacer localement l'attendu du juge par la cellule du rapport fait échouer ce test ; restaurer ensuite, sans verser la mutation.

SC5 — **La notice donne une preuve rejouable.** `python3 -m pytest jeu/ville/tests/test_epreuve_capitale.py -q` reste vert et `git diff --check` passe après mise à jour de `jeu/ville/README.md` : commande PC, service neuf par terre, référence `/maison`, tick poussé par Unity seul, codes 0/1/2, commande de contre-épreuve VPS et liens vers les deux verdicts sous `docs/mesures/703-epreuve-capitale/`. La section #702 renvoie à cette épreuve au lieu de l'annoncer à venir. Contre-épreuve : une notice qui dit que la cellule envoyée à Unity sert de référence, ou un verdict rouge présenté comme une mesure PC réelle, refuse la livraison.

SC6 — **Les preuves existantes gardent leur exigence.** `python3 -m pytest jeu -q` passe sur le VPS ; `git diff --check` passe et `git diff --numstat` reste sous 300 lignes de réalisation. Vérifier aussi les fichiers nouveaux avec `git ls-files --others --exclude-standard`. Contre-épreuve : une modification hors Périmètre, notamment dans les tests existants, les sessions Unity ou `jeu/sim/`, refuse la livraison ; aucun test existant n'est réécrit ni assoupli.

## Hors périmètre
Toute modification de la simulation, des données historiques, du pont, des scènes, de la remise du siège ou de la session #702 ; tout kit neuf ; le retour à la carte et l'horloge de #410 ; les gestes de construction et la preuve complète #508. Pas de nouvelle capture, ni de seconde simulation ou de verdict fondé sur les arguments transmis à Unity. Aucun changement des épreuves précédentes.

## Photo
sans objet : outil d'épreuve, aucun changement de ce que le joueur voit à l'écran. Le script lance la session existante sans modifier son geste ni sa caméra ; les captures de Biskra ouverte depuis la carte (#701) et du message de Bar (#690) portent déjà le résultat visible. Aucun scénario `Lot703.cs` n'est nécessaire.
