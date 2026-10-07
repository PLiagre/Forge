# Lot #407 — La sixième terre de départ : l'émirat du Zab, en terre crue
Jalon : J4 · Machine : vps · Taille prévue : 240 lignes

## But
Le joueur peut choisir l'émirat du Zab parmi six terres de départ réelles, avec Biskra pour siège sous les Hafsides, pour préparer la construction de sa capitale en terre crue.

## Le joueur
Le joueur peut commencer au Zab, dans les oasis de Biskra, sous la suzeraineté des Hafsides : une terre pauvre aux portes du désert, que son suzerain voudra reprendre — et la seule dont la capitale se bâtit déjà en 3D, avec le kit du désert (décision du propriétaire, 7 octobre 2026).

Il voit sa maison, sa religion, son suzerain, ses sources et les habitants actuels de son siège dans la fiche. Ce lot de données prépare le geste de J4 : entrer dans sa capitale, tracer ses routes et ses parcelles, poser ses ateliers et choisir entre murs et maisons. Le lot #409 ouvrira la capitale choisie dans Unity ; #410 reliera carte et ville. La reprise historique par le suzerain donne le contexte du départ, sans imposer une conquête à la simulation.

Dépend de : aucun lot non livré. La base contient déjà `charger_seigneuries`, les fiches, le choix par intention, la photographie et `GET /departs`. Ce lot n'attend ni les maîtres et les greniers de J3, ni un nouveau kit, ni l'ouverture de la capitale.

## Règle du monde
Découle de « Les seigneuries de départ, vue dérivée », « La photographie de 1400, vue dérivée » et « La carte et les terres servies, vue dérivée » dans `jeu/sim/MODELE.md`.

Ajouter à `jeu/data/seigneuries-1400.json` une sixième ligne, identifiant 6, nom « Émirat du Zab », maison « Banou Mozni », religion `musulmane`, suzerain 35 (Hafsides), siège Biskra à 34,85° N et 5,73° E. Calculer les coordonnées par `projeter_epsg3035`, arrondies au centimètre : 3 926 430,32 m et 1 322 273,47 m. La cellule est calculée par `cellule_du_siege` et `point_dans_geometrie`, jamais enregistrée dans la table ni choisie par proximité.

Sources publiques vérifiées par le chef le 7 octobre 2026 : [Zab Emirate](https://en.wikipedia.org/wiki/Zab_Emirate) atteste les Banou Mozni à Biskra du milieu du XIVe siècle à 1402 ; [Zibans](https://fr.wikipedia.org/wiki/Zibans) atteste Biskra comme capitale sous les Béni Mozni ; [Émirat de Zab](https://fr.wikipedia.org/wiki/%C3%89mirat_de_Zab), section « Histoire », décrit l'allégeance hafside, formelle, et le retour dans son orbite après l'épisode mérinide. Ces faits couvrent le 1er janvier 1400 : le recours à Tozeur prévu par l'issue n'est pas nécessaire.

Le champ `source` cite les liens et les faits qu'ils soutiennent. Il déclare aussi « Chef de la maison au 1er janvier 1400 : non sourcé ». Un nom ne remplace cette mention que si une source publique l'atteste à cette date ; un gouverneur attesté en une autre année ne suffit pas. Cette déclaration arrive dans la fiche, la photographie et `/departs` par leur champ `source` existant, sans ajouter de personne ni changer le contrat JSON.

**Niveau 1** : maison, siège, religion et suzerain sourcés. **Niveau 2** : domaine réduit à sa représentation actuelle dans la cellule et ses lieux, sans frontières historiques détaillées. La fiche mesure les habitants de la cellule ; elle ne prétend pas mesurer la ville historique. Le chef a vérifié que le point appartient uniquement à 10103, que sa puissance est 35 et que sa population amorcée vaut 3 459 (graine 0). Aucun effectif ni rendement n'est fixé dans la nouvelle ligne. La section « Les seigneuries de départ » de `MODELE.md` décrit désormais six terres, Biskra et la déclaration du chef non sourcé.

Inventaire des adaptations de tests autorisées par l'issue, sans réduire leurs exigences :

- `test_seigneuries.py` : étendre `SUZERAINS` au Zab et `MAISONS` aux Hafsides ; `test_lecture` retire la religion de toutes les lignes musulmanes dans sa copie altérée, puisque modifier seulement Evrenos ne produit plus une absence ; `test_sieges` contrôle les six sièges ; `test_fiche` conserve ses comparaisons des cinq anciennes fiches, extraites par leur nom plutôt que par le déballage de toute la table, et ajoute Biskra.
- `test_puissances.py::test_projection_epsg3035_au_centimetre` : dériver le nombre de sièges de la table, comparer tous ses points et garder l'échantillon non vide, la tolérance de 0,01 m et les deux projections altérées.
- `test_maisons.py::test_capitale_maisons_ia_et_choix` : dériver les comptes 35, 34 et les cinq seigneuries des tables des capitales et des départs ; conserver le contrôle de chaque identité, du dépôt avant tick, de l'exclusion du seul joueur après tick et la contre-épreuve Bar. Les trente grandes maisons conservent leur propre référence.
- Les tests de photographie, de `/departs`, du pont Unity et du jalon 2 gardent leurs exigences ; ajouter leurs cas Zab dans les fichiers qui portent ces invariants. Les octets `/lieu` figés ne contiennent pas la liste des départs : les comparer au service, sans changer leur référence pour masquer un écart.

## Périmètre
jeu/data/seigneuries-1400.json
jeu/sim/MODELE.md
jeu/sim/tests/test_seigneuries.py
jeu/sim/tests/test_puissances.py
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_carte_servie.py

## Conditions de succès
SC1 — `python3 -m pytest jeu/sim/tests/test_seigneuries.py -q -k 'lecture or refus or zab'` rend six terres triées, conserve les cinq anciennes et trouve exactement le Zab musulman des Banou Mozni sous les Hafsides, avec les sources et la déclaration du chef. Ajouter, pour le Zab, les cas de source absente, vide ou blanche : chacun doit lever `PuissanceInvalide` en nommant l'identifiant et le champ `source`. Contre-épreuves : une copie privée du Zab échoue à la preuve des six terres ; une copie dont toutes les religions musulmanes sont retirées échoue toujours au contrôle des religions. Prouver d'abord le rouge du nouveau cas Zab sur la base à cinq terres.

SC2 — `python3 -m pytest jeu/sim/tests/test_seigneuries.py jeu/sim/tests/test_puissances.py -q -k 'sieges or zab or projection_epsg3035_au_centimetre'` vérifie le point réel projeté dans la géométrie de 10103, son attribution par `cellule_du_siege` et la puissance Hafsides ; tous les sièges restent distincts et cohérents. La fiche reprend la population et la production du moteur. Contre-épreuves : déplacer le point Zab hors carte est refusé ; déplacer son siège dans la cellule d'une ancienne terre ou lui donner un autre suzerain fait échouer le contrôle. La tolérance de projection ne change pas.

SC3 — `python3 -m pytest jeu/sim/tests/test_monde.py -q -k photographie_1400` inclut un nouveau cas de choix du Zab par intention, appliquée au tick suivant : `terre_choisie` égale sa fiche arrondie, avec Biskra, 10103, Banou Mozni, Hafsides, sources et déclaration du chef. Sans choix, elle reste `null` ; lire la fiche et photographier n'altèrent pas le monde. Contre-épreuve : le même contrôle échoue sur une copie de la photographie portant la fiche de Bar à la place du Zab.

SC4 — `python3 -m pytest jeu/sim/tests/test_carte_servie.py -q -k departs` exige les six identifiants de la table, dans l'ordre, et ajoute l'égalité de la fiche Zab servie avec `terre_choisie` au même tick après choix. Les habitants viennent du monde et suivent ses ticks. Contre-épreuves : supprimer le Zab du document servi fait échouer l'égalité des identifiants ; garder les fiches d'un tick antérieur échoue toujours au contrôle existant d'absence de cache.

SC5 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k capitale` vérifie que la vue IA gagne la maison du Zab et que choisir cette terre retire exactement cette seigneurie au tick suivant, en conservant les grandes maisons et les autres départs. Les comptes attendus se dérivent des tables, avec des échantillons non vides et des identités comparées. Contre-épreuve : omettre le Zab de la vue avant choix, ou le laisser après son choix, fait échouer ces contrôles ; conserver la contre-épreuve Bar existante.

SC6 — `python3 -m pytest jeu/sim/tests/test_monde.py -q -k reponse_figee_du_pont` compare strictement les réponses du service aux deux fichiers Unity `lieu-graine0-tick3.json` et `lieu-graine0-tick4.json`. L'ajout de la terre seule doit conserver ces octets et le contrat du pont. Contre-épreuve : un tick de plus donne toujours des octets différents ; ne remplacer ni le fichier ni l'égalité par une comparaison partielle.

SC7 — `python3 -m pytest jeu/sim/tests/test_epreuve_jalon2.py jeu/sim/tests/test_no_hardcoded.py jeu/sim/tests/test_write_coverage.py -q`, puis `python3 -m pytest jeu -q`, restent verts. La référence, le seuil et tous les témoins du jalon 2 restent ceux de la base. Contre-épreuves : les mondes sans aridité ou aux puissances mélangées restent refusés par l'épreuve J2 ; le littéral ajouté dans une copie de `seigneuries.py` reste détecté par la contre-épreuve existante de `test_controles`. Aucun test n'est supprimé, marqué à ignorer ou rendu moins exigeant.

## Hors périmètre
Ouverture de Biskra en 3D (#409), transition carte-ville (#410), scènes, captures et exécution Unity ou Blender. Attribution des maîtres des lieux, prélèvement, hommage, greniers et autres travaux encore attendus de J3. Personnes et succession de la maison (J6). Guerre ou reconquête hafside imposée en 1402 (J7). Nouvelle ville dans la table des villes, modification de la carte, des puissances, de l'amorçage, des constantes ou du tick. Nouveau champ dans le contrat des fiches. Toute autre écriture que les chemins du périmètre est interdite.
