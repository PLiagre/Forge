# Lot #706 — Le chantier prend ses bras au bourg, puis aux lieux du même maître
Jalon : J4 · Machine : vps · Taille prévue : 295 lignes

## But
Le chantier prendra ses paysans dans les lieux du maître de la capitale et fera perdre à chacun la récolte correspondant aux bras qu’il lui retire ce jour-là.

## Le joueur
Le joueur choisit quand bâtir sa capitale : les ouvriers viennent d’abord du bourg, puis de ses lieux du même maître par rang, si bien qu’un chantier lancé à la moisson coûte plus de récolte qu’en hiver. Ce lot de fond réalise l’arbitrage de J4 entre bâtir et garder des bras aux champs ; #419 le rendra lisible dans le panneau de la capitale et #508 le montrera dans la preuve complète.

Dépend de : #705, livré par ses morceaux #718, #723, #724 et #720 sur la base de ce lot : récolte par lieu, besoin saisonnier et calibrage à 6,2 existent.

## Règle du monde
Niveau 2, plausible, jamais sourcé. Le lot découle des sections « Les foyers par métier », « Le rendement agricole et sa variabilité » et « Le chantier et ses bras » de `jeu/sim/MODELE.md`.

- Au début de Chantiers, remettre à zéro le compte journalier de chaque lieu après le retour des ouvriers de la veille. Pour les chantiers ordinaires d’une cellule, la réserve admissible est formée du bourg de rang 0, puis des autres lieux de cette cellule dont le maître actuel est celui du bourg, par rang croissant. Un lieu d’un autre maître ne fournit aucun bras, même si la cellule porte encore des paysans. Sans bourg, maître ou métiers calculés, ne rien inventer.
- Les paysans disponibles au bourg sont sa population moins les métiers non agricoles rattachés au bourg, avec plancher à zéro ; dans chaque autre lieu admissible, ce sont ses habitants moins ses ouvriers déjà pris ce jour. Garder les limites existantes par foyers du chantier, travail restant et grain payable, ainsi que les priorités rues, parcelles, bâtiments. Le manque de bras admissibles donne `sans_bras`.
- Chaque personne envoyée devient toujours un `ouvrier` dans les métiers cellulaires, ajoute une journée au chantier et augmente `ouvriers_du_jour` de son lieu d’origine. La somme de ces comptes égale les ouvriers ordinaires affectés ce jour. L’autoconstruction garde ses artisans et ne prend ni paysan ni part de récolte par cette règle.
- À la production du même tick, chaque lieu retranche ses propres `ouvriers_du_jour` de ses paysans avant d’appeler le facteur de bras saisonnier. Les mineurs et artisans restent retranchés du seul bourg. Pour un ancien état ou un montage direct portant des ouvriers cellulaires sans origine journalière, rattacher seulement ce reliquat au bourg : les contrôles existants gardent leur sens sans déplacer des bras vers un lieu arbitraire.
- `ouvriers_du_jour` est une observation dérivée du tick, initialisée à zéro et renouvelée, pas un second métier ni une population. Elle vit sur `EtatDeLieu` pendant le jour, mais n’entre ni dans la sauvegarde canonique, ni dans les photographies, ni dans le service par ce lot ; le tick suivant la recalcule depuis les chantiers. Les octets d’un monde sans chantier restent donc inchangés.
- Documenter dans « Le chantier et ses bras » l’ordre des lieux, le refus des lieux d’un autre maître, le compte journalier et la perte locale de récolte. Ne changer ni `BRAS_AUX_CHAMPS_PAR_KM2 = 6,2`, ni saison, rendement, salaire ou population amorcée.

## Périmètre
jeu/sim/model.py
jeu/sim/chantiers.py
jeu/sim/engine.py
jeu/sim/MODELE.md
jeu/sim/tests/test_chantiers.py
docs/briefs/706-le-chantier-prend-ses-bras-au-bourg-puis-aux-lie.md

Tout autre chemin est interdit. Viser 295 lignes ajoutées et retirées, brief compris, sans reformater les fichiers.

## Conditions de succès
SC1 — Écrire d’abord les nouveaux cas puis, depuis la racine, lancer `python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k bras_par_lieu` : ils doivent rougir sur la capacité absente, puis passer. Sur un monde amorcé, construire par l’intention une route de exactement 2 000 journées dans une cellule dont le bourg et au moins deux lieux de rang suivant ont le même maître, avec assez de grain et de foyers pour fournir les 2 000 journées le premier jour. Dériver les effectifs disponibles des populations et métiers ; exiger que le bourg soit vidé d’abord, que le rang suivant fournisse exactement le reste, que les rangs non atteints et les lieux d’un autre maître gardent zéro, et que somme des comptes, baisse des paysans, hausse des ouvriers et travail fourni valent tous 2 000. Au tick suivant, la route achevée ne prend personne et tous les comptes reviennent à zéro. Contre-épreuves : ordre inversé, bras pris à l’autre maître, compte cumulé sur deux jours, compte posé seulement au bourg ou somme différente du travail font échouer le même vérificateur ; échantillon vide ou route dont le requis n’est pas 2 000 échoue explicitement.

SC2 — `python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k chantier_janvier_juillet` prouve la direction demandée sur deux copies de `World.charger(0)`, même graine et même route de 2 000 journées limitée à un foyer par jour. Poser `ticks_ecoules` au jour éprouvé et passer le même `numero_tick` au moteur ; vérifier par la date dérivée qu’un cas est en janvier et l’autre en juillet. Pour chaque date, comparer au témoin sans intention la somme de `recoltes[cell_id][rang]` du bourg et des lieux de la même cellule qui ont son maître, avant prélèvement : perte de janvier exactement 0 kg, perte de juillet strictement positive. Exiger dans les quatre courses une récolte et un échantillon de lieux non vides, le même tirage, cinq journées fournies au chantier et des comptes journaliers égaux aux origines. Contre-épreuve : remplacer en mémoire le besoin de bras par le même calcul sans facteur de saison doit faire échouer cette direction ; un facteur constant, une comparaison de stocks après consommation ou des `ticks_ecoules` laissés à zéro ne valent pas preuve.

SC3 — `python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k 'recolte_diminue_avec_les_bras_envoyes or non_localises or documentation'` garde intact le contrôle existant du chantier sur le lieu unique et ajoute le cas de compatibilité : des ouvriers cellulaires sans compte local continuent de réduire le seul bourg, tandis que des ouvriers localisés réduisent exactement leur lieu et pas son voisin. Vérifier aussi que `World.to_dict()` et la sérialisation canonique omettent `ouvriers_du_jour`, mais qu’une copie du monde pendant le tick conserve ses comptes. Contre-épreuves : ignorer le compte local, soustraire tous les ouvriers à tous les lieux, traiter le reliquat ancien comme disponible ou publier le champ font échouer les assertions. Le contrôle documentaire doit refuser la disparition de l’ordre bourg puis rangs, de la condition de même maître ou de la saison.

SC4 — Depuis la racine, `python3 -m pytest jeu/sim/tests/test_chantiers.py jeu/sim/tests/test_foyers.py jeu/sim/tests/test_determinisme.py -q`, puis `python3 -m pytest jeu -q`, passent sans modifier leurs attentes existantes. Contre-épreuve : aucune empreinte, comparaison exacte, borne, contrôle de conservation ou test existant n’est retiré, réécrit ou assoupli ; les mondes sans chantier gardent leurs octets et leur état aléatoire.

## Hors périmètre
Publication des origines ou de la récolte perdue dans `/plan`, panneau #419, Unity, Blender et captures ; choix manuel des lieux ou de la priorité entre chantiers ; ouvriers pris dans une autre cellule ou chez un autre maître ; déplacement individuel, métier persistant par lieu, âge, sexe, outils et bêtes de trait ; autoconstruction, ateliers, salaire, grenier, prélèvement, consommation, démographie, commerce, IA, saison, rendement ou calibrage agricole.
