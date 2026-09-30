# Lot #209 — Les grandes villes de 1400
Jalon : J2 · Machine : vps · Taille prévue : 290 lignes

## But
Le monde amorcé porte les grandes villes de 1400 et au moins leurs habitants, pour donner au choix de la terre de départ du jalon J2 sa géographie humaine.

## Règle du monde
Les villes sont un fait initial de **niveau 1** : nom, point et ordre de grandeur des habitants vers 1400, avec sources publiques consultées, date de l'estimation et incertitude déclarées. La table est non exhaustive ; elle inclut Paris, Londres, Venise, Constantinople, Le Caire, Alexandrie, Gand, Bruges, Milan, Grenade et Palerme, et couvre les autres grandes villes documentées de l'emprise. Une population moderne ou une estimation d'une autre époque ne devient pas silencieusement une population de 1400.

Cela prolonge « Population initiale par cellule », « Stock alimentaire initial » et « Le panier de marchandises » de `jeu/sim/MODELE.md`, et remplace le passage « Aucune liste de villes historiques ». La ville historique n'est pas le bourg dérivé des métiers : elle n'attend ni le lot des métiers, ni les puissances, ni les maisons. L'aridité de #203, la géométrie et le commerce sont présents sur la base ; aucun travail restant de J1 n'est requis.

`jeu/data/villes-1400.json` déclare ses sources et sa projection. Chaque ligne porte un nom unique, latitude/longitude de référence, point projeté en mètres, population entière positive et référence précise de l'estimation (URL et passage ou table). Les points projetés sont préparés dans l'EPSG:3035 déclaré par la carte ; documenter leur conversion depuis EPSG:4326. Aucune dépendance géographique nouvelle dans `sim/`, qui reste en bibliothèque standard.

`sim/villes.py` charge et valide la table, puis produit une attribution pure depuis les polygones de la carte reçue : intérieurs, trous et MultiPolygon compris. Une frontière commune se départage par le plus petit `cell_id`, indépendamment de l'ordre. Un point extérieur reste explicitement hors carte, nommé dans le résultat ; jamais de rattachement au centroïde le plus proche. Projection incompatible, géométrie absente ou table invalide sont refusées avant amorçage. Le résultat conserve les villes placées et hors carte ; il ne pose aucun champ ni identifiant de ville sur `Cell` et n'est pas lu par le tick.

Dans `World.charger`, après le calcul actuel lié à l'aridité, poser `population = max(population_actuelle, somme_des_populations_des_villes_contenues)`. Gand et Bruges se cumulent si elles occupent la même cellule ; on ne les remplace pas par la plus grande. Aucun double compte par addition au peuplement déjà amorcé. L'attribution utilise bien `carte_doc` lorsqu'il est fourni. Aucun plancher historique n'est réappliqué après l'amorçage.

**Décision A du propriétaire, déjà acquise.** Déclarer dans `sim/constants.py` `RESERVE_VILLES_TICKS = 30`, relue par son module à chaque amorçage. C'est un **proxy de niveau 2**, pas une réserve historique attestée : un mois environ de manque laisse agir les échanges sans garantir une année de survie. Cette valeur est fixée avant mesure et ne sera pas ajustée pour sauver les villes.

Pour une cellule urbaine, calculer `manque_kg = max(0, population - population_soutenable_de(cellule, carte)) × ration`. Son grenier supplémentaire vaut `manque_kg × RESERVE_VILLES_TICKS`, ajouté à la réserve ordinaire calculée sur sa population finale. Ce sont des kilogrammes de nourriture dans `Cell.stocks`, via les accès existants ; leur origine déclarée est une réserve antérieure au début de partie, non une production au premier tick. Aucun réapprovisionnement automatique, aucune protection contre le commerce qui peut exporter ce stock. Une cellule sans ville conserve exactement son ancien amorçage, sous son plafond, et ses cinq ticks ordinaires : « sans grenier » signifie sans **supplément urbain**, pas suppression de cette réserve existante.

La seule réécriture de test existant autorisée est `test_aucune_cellule_n_amorce_au_dessus_de_ce_qu_elle_nourrit` dans `test_survie.py`, selon la décision du propriétaire : aucune cellule n'a faim au premier tick, réserves comprises. Garder le contrôle du plafond pour toutes les cellules sans ville et ajouter les contre-épreuves dans ce même fichier. Les autres assertions existantes restent intactes, notamment le plafond mondial et la survie à long terme.

Dans `MODELE.md`, mettre à jour aussi « Déclaration explicite », « Population initiale par cellule » et « Stock alimentaire initial » : distinguer populations historiques et peuplement rural proxy, préciser la constante, sa raison, la formule du grenier, l'invariant révisé et l'absence de garantie après le premier tick. Le défaut d'eau du Nil reste déclaré : poser des habitants ne crée pas une crue.

## Périmètre
jeu/data/villes-1400.json
jeu/sim/villes.py
jeu/sim/world.py
jeu/sim/constants.py
jeu/sim/tests/test_villes.py
jeu/sim/tests/test_survie.py
jeu/sim/MODELE.md
docs/mesures/209-villes-1400.md

## Conditions de succès
Toutes les commandes partent de la racine. Prouver les contre-épreuves avant correction ; les mutations restent en mémoire ou dans des fichiers temporaires. Les compteurs et dénominateurs viennent des données ; un échantillon vide échoue. Les nombres 34 villes placées et 7 cellules déficitaires rapportés dans l'issue sont des mesures antérieures à vérifier, jamais des compteurs codés en dur.

SC1 — `python3 -m pytest jeu/sim/tests/test_villes.py -q -k sources` contrôle la table non vide, les villes requises, les sources non vides, la date/approximation déclarée, les coordonnées finies et les populations entières positives. Le compte rendu cite les références effectivement consultées et leurs limites. Contre-épreuves : table vide, source absente, nom dupliqué, population booléenne ou négative, coordonnée non finie et projection incompatible sont refusés en nommant la ligne ou le champ.

SC2 — `python3 -m pytest jeu/sim/tests/test_villes.py -q -k placement` vérifie des polygones synthétiques à résultats connus : intérieur, extérieur, trou, plusieurs morceaux et frontière partagée dans les deux ordres. Un cas doit appartenir à une cellule dont le centroïde n'est pas le plus proche. Sur la vraie table, chaque ligne est placée une fois ou déclarée hors carte, et chaque point placé appartient au polygone rendu. Contre-épreuves : l'attribution au plus proche échoue sur le cas discriminant ; un point déplacé hors de tous les polygones devient hors carte, sans habitant ajouté ; une géométrie manquante fait refuser le calcul.

SC3 — `python3 -m pytest jeu/sim/tests/test_villes.py -q -k amorcage` compare le monde à la somme de référence dérivée de la table par cellule, vérifie deux villes dans une cellule, un peuplement préalable plus grand que cette somme et le déterminisme. Les cellules sans ville restent identiques au calcul antérieur pour la même graine. Contre-épreuves : neutraliser l'application des habitants fait échouer les planchers sur un échantillon déficitaire non vide ; prendre le maximum des deux villes au lieu de leur somme fait échouer le cas synthétique. Après un tick, une cellule urbaine artificiellement dépeuplée n'est pas remise à son effectif historique.

SC4 — `python3 -m pytest jeu/sim/tests/test_survie.py -q -k 'amorce or grenier'` exige sur le monde entier non vide, graine 0, après `tick(monde, random.Random(0), numero_tick=0)`, zéro faim et zéro dette dans chaque cellule. Avant ce tick, vérifier le plafond hors villes et l'égalité des stocks à la formule ci-dessus ; doubler la constante double seulement le supplément. Contre-épreuves dans ce fichier : retirer **toute** la nourriture initiale des cellules urbaines déficitaires doit faire rougir le contrôle du premier tick ; ajouter un supplément à une cellule sans ville ou la peupler au-dessus de son plafond doit aussi rougir. Ne pas seulement mettre la constante à zéro : les cinq ticks ordinaires masqueraient le manque.

SC5 — `python3 -m pytest jeu/sim/tests/test_survie.py -q -s -k bilan_villes` joue une année calendaire complète, graine 0, avec `numero_tick` explicite à chaque appel et sans intervention. La cohorte est dérivée des cellules urbaines initialement au-dessus de leur plafond ; elle est non vide. Publier pour chacune noms, `cell_id`, population initiale/finale, réserve initiale/finale, dette finale et nombre de ticks avec faim ; compter celles qui « tiennent » : population finale au moins égale à l'initiale et dette finale nulle. Identifier les cellules de Paris, Le Caire, Alexandrie, Gand+Bruges, Milan, Grenade et Palerme citées dans l'issue et expliquer tout écart de cohorte. Aucun minimum de villes sauvées n'est exigé. Contre-épreuve : sur une cellule urbaine déficitaire isolée, sans production ni import, un stock fini s'épuise et la population baisse ; un renouvellement caché ou un plancher permanent fait échouer ce cas.

SC6 — `python3 -m pytest jeu -q` reste vert avec SC1–SC5 ajoutées et la seule réécriture autorisée en SC4. Les contrôles existants de conservation, déterminisme, constantes et clé spatiale gardent leurs exigences. Contre-épreuve : une duplication du grain lors d'un transfert doit toujours faire échouer `python3 -m pytest jeu/sim/tests/test_commerce.py -q`. `docs/mesures/209-villes-1400.md` consigne commandes, résultats rouges puis verts, villes hors carte et bilan annuel mesuré ; aucune valeur attendue ne remplace une mesure.

## Hors périmètre
Puissances, frontières politiques, maisons, métiers, lieux sous la cellule, carte du joueur, vues et Unity ; fleuves, crues, routes, nouvelle règle de commerce ou de production ; modification de la carte figée, ajout d'une clé spatiale, plafonnement des populations historiques et maintien forcé des villes après amorçage. Aucun autre test existant ne change. Tout chemin absent du périmètre est interdit.
