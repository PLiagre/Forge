# Direction artistique de l’interface — validée le 14 octobre 2026

Révisée le 28 octobre 2026 : le cadre passe à la pierre, au bois brûlé et au métal patiné ; voir « [Révision du 28 octobre 2026](#révision-du-28-octobre-2026--pierre-bois-brûlé-registre) ». Ce qui n’y est pas changé reste valide.

Lecture du 14 octobre 2026 : les 108 PNG de `docs/direction-artistique/`, examinés dans les douze planches réduites ci-dessous. Dossier confirmé par le propriétaire. Concepts de niveau 2, sans valeur de source historique ni de capture du jeu ; les scènes après 1500 nourrissent les matières, pas le périmètre du premier siècle.

## Cinq principes

1. **Le territoire reste le sujet.** Une carte plein cadre et plusieurs dossiers visibles simultanément, selon le choix du propriétaire ; profondeur et chemins de `01_scenes/seigneurie_1400.png`. Les documents se rangent sur les côtés sans effacer leurs voisins.
2. **Le pouvoir a un visage et une matière.** Portrait proche, laine, bois, encre ; `03_personnages/seigneuresse_1400.png` et `08_institutions/conseil_1500.png`. Or discret, aucune armure décorative autour de chaque bouton.
3. **Une quantité renvoie à quelque chose de physique.** Sacs, charrettes, destinations ; `07_transports/grenier_1500.png` et `charrette_1400.png`. Montrer stock, trajet et destinataire plutôt qu’un bonus abstrait.
4. **La lumière guide le regard.** Surfaces mates, accents rares ; `06_production/forge_1450.png`. La cire marque une décision importante ; elle ne clignote pas.
5. **Une grammaire commune, des terres différentes.** `04_habitations/maison_oasis_1400.png`, `maison_nordique_1450.png` et `chaumiere_1400.png` : mêmes gestes, portraits et matières régionaux ; aucune identité fictive du corpus attribuée à une vraie dynastie.

## Palette et composition proposées

| Jeton | Hex | Rôle |
|---|---|---|
| fond | `#211E1A` | Cadre sombre, ombre des documents |
| papier | `#E8DDC9` | Surface de lecture mate, sans taches derrière les caractères |
| encre | `#302820` | Texte principal sur papier |
| secondaire | `#625548` | Légendes sur papier |
| accent | `#345261` | Sélection, liens et focus sur papier |
| alerte | `#8B342E` | Refus ou urgence, toujours avec mot et symbole |
| or | `#B49A61` | Filets et focus sur fond sombre ; jamais petit texte sur papier |
| accord | `#405444` | Confirmation accompagnée de son libellé |

Titres : serif humaniste, candidate Noto Serif ; corps et chiffres : sans serif, candidate Noto Sans, chiffres tabulaires si disponibles. Ce sont des choix proposés, pas des fontes présentes : vérifier licence, accents et rendu Unity avant intégration. Aucun gothique pour lire une décision. À 1080p : corps 18 px, titres 28 px, commandes 44 px de haut ; grille d’espacement 4/8/16/24/32 px, texte agrandissable à 150 %. Ces mesures règlent la présentation, jamais le monde.
Carte visible sur au moins deux tiers de la largeur au repos. Bande haute : maison, date reçue, pause et vitesse ; accès aux dossiers sur le bord ; lieux et décisions peuvent rester ouverts côte à côte. Chaque dossier conserve sa sélection ; ouvrir l’un ne ferme pas l’autre. À petite définition, réduire les dossiers en onglets explicites plutôt que les superposer sans contrôle. Papier clair sur cadre sombre et ornements discrets validés par le propriétaire.
Les panneaux évoquent des feuillets posés : papier peu grainé, filet fin, ombre courte, onglet de tissu ; sceau réservé aux engagements. En bataille, commandes basses et terrain dégagé. Les portraits portent les différences culturelles ; les cadres restent lisibles et sobres.
Icônes : silhouettes simples de sac, route, maison, arbre familial, bannière et livre, toujours nommées. Les blasons du corpus enseignent le contraste et la silhouette ; ils ne sont ni une police d’icônes ni les armoiries historiques du jeu. Alpha des originaux héraldiques à reprendre avant réemploi (réserve du catalogue).
Transitions : glissement court et fondu de 160 ms proposés, désactivables ; ouverture sans animation en mouvement réduit. Sons suggérés : froissement sec, bois posé, cire pressée ; volume séparé et aucune information donnée seulement par le son. Textes : « Ouvrir le grenier », « Ordre reçu », « Le monde ne répond pas » ; cause concrète, unités, aucune fausse certitude.
Interdits : tableur permanent, fenêtres génériques empilées, néon, dorure omniprésente, texture sous petit texte, couleur seule pour distinguer un état, portrait fictif présenté comme historique, nombre remplacé par zéro quand la donnée manque.

## Révision du 28 octobre 2026 — pierre, bois brûlé, registre

Demandée par le propriétaire : une interface **sombre, gothique et médiévale**, dans l’atmosphère d’un monde de fer et de pierre à la manière de Warhammer Fantasy. Cette référence donne une ambiance, rien d’autre : aucun de ses logos, de ses signes reconnaissables, de ses lettrages ni de ses assets n’entre dans Forge. Les lots qui la portent sont écrits dans [CAP.md](../../CAP.md), « La langue visuelle ».

**Ce qui reste.** Les cinq principes ci-dessus ; la carte plein cadre et les dossiers simultanés ; la lecture sur papier clair (`papier` reste `#E8DDC9`, et Noto Serif / Noto Sans restent les polices : les tests du socle les vérifient) ; corps 18 px, titres 28 px, commandes 44 px ; aucune lettre brisée pour lire une décision, un nom de lieu ou un nombre ; jamais la couleur seule pour dire un état.

**Ce qui change.** Le cadre autour des feuillets n’est plus un brun uni : c’est la **pierre** sombre pour le fond et le bandeau, le **bois brûlé** pour les tranches et les commandes, le **métal patiné** pour les ferrures, les séparateurs et les coins. Le papier devient un **registre** : rubriques, lignes de compte, notes en marge, sceau. Les accents chauds — rouge profond, cuivre, or vieilli — restent rares : un écran en porte peu, et chacun a un rôle.

### Jetons ajoutés

Les huit jetons du 14 octobre sont gardés tels quels. Le socle en ajoute sept ; un écran n’en invente aucun.

| Jeton | Hex | Rôle | Contraste mesuré |
|---|---|---|---|
| pierre | `#1C1B19` | Fond, bandeau haut, cadre de la carte | `papier` dessus : 12,8:1 |
| bois-brule | `#2B211B` | Tranche des feuillets, commande au repos | `papier` dessus : 11,7:1 |
| metal | `#3E3B33` | Ferrures, coins, séparateurs, commande inactive | `papier` dessus : 8,3:1 |
| sang | `#7A1E19` | Rubrique, alerte, refus, cire d’un engagement | sur `papier` : 7,7:1 |
| cuivre | `#A8683C` | Survol, filet de l’infobulle ; jamais un texte | sur `pierre` : 3,9:1 (trait seul) |
| or-vieilli | `#B49A61` (= `or`) | Sélection et focus sur fond sombre ; jamais un texte sur papier | sur `pierre` : 6,3:1 ; sur `papier` : 2,0:1, refusé |
| vert-de-gris | `#5E8C7A` | Confirmation sur fond sombre, avec son libellé | sur `pierre` : 4,5:1 |

Seuils, vérifiés par le contrôle du socle : **4,5:1** pour tout texte, **3:1** pour un trait ou un signe qui porte un état. Les couleurs des maisons et des calques sont des données servies : le thème ne les change pas, il les encadre.

### La hiérarchie d’un registre

- **La rubrique** : le titre d’un dossier, Noto Serif en capitales espacées, en `sang` sur papier ou en `papier` sur pierre ; un filet double de `metal` dessous.
- **La ligne de compte** : le libellé à gauche, le nombre servi à droite en chiffres alignés, son unité, et la date du tick reçu en pied de feuillet. Absence, attente et lecture périmée gardent leurs états d’UI-02.
- **La note en marge** : la cause, la raison d’une maison, la source ; `secondaire`, plus petite, jamais seule porteuse d’un nombre.
- **Le sceau** : la cire `sang` marque un engagement (part, grenier, mariage, guerre, emprunt) et lui seul ; il ne décore pas.
- **Les séparateurs** : un filet de métal, un losange au centre au plus ; pas de rinceaux, pas de chaînes, pas de pointes autour des boutons.

### Les états, une seule fois pour tous les écrans

| État | Matière et trait | Ce qui le dit sans couleur |
|---|---|---|
| repos | bois brûlé, filet de métal | — |
| survol | filet `cuivre` | infobulle après un court délai |
| focus clavier | double filet `or-vieilli` | contour visible au clavier |
| sélection | filet `or-vieilli` épais, marque sur la carte | le nom de la sélection écrit dans le bandeau ou le dossier |
| inactif | `metal`, texte atténué gardant 4,5:1 | la raison de l’inactivité, au survol |
| attente | filet pointillé | « En attente du monde » |
| reçu / appliqué | `vert-de-gris` sur pierre | « Ordre reçu », puis l’effet publié |
| refus / panne | `sang` | mot, signe et cause d’UI-02 |
| alerte | bandeau `sang` sur pierre | mot et signe ; elle ne clignote pas |

**L’infobulle** est un petit feuillet de papier au filet de cuivre : le nom de ce qu’on survole, ses valeurs servies avec leur unité et leur tick. Elle ne cache jamais l’objet qu’elle décrit, reste entière dans l’écran à 1280 × 720, et n’apporte aucun nombre qu’un dossier ne puisse montrer.

**Sur la carte**, le cadre reste sur les bords : la terre garde au moins deux tiers de la largeur. Le survol d’un lieu est un trait de cuivre, sa sélection un trait d’or vieilli et son nom ; la maison du joueur porte sa marque ; une alerte (un lieu qui a faim, une place assiégée) est en `sang` avec son signe. Aucune de ces marques ne recouvre la couleur servie du maître.

### Interdits ajoutés

Crânes, aigles bicéphales, comètes, marteaux ou épées en emblème, lettrages qui imitent le logo d’une licence ; pointes, chaînes et rivets autour de chaque commande ; parchemin brûlé ou taché sous le texte ; noir pur ; rouge à tout faire ; sang, flammes ou fumées animées dans l’interface ; tout fichier, police ou motif d’une licence tierce. Les matières se génèrent dans le dépôt, sans l’aléa du monde, comme celles du 18 octobre ([MATIERES.md](MATIERES.md)).

### Références du corpus

`06_production/forge_1450.png` (un seul foyer chaud dans la pierre et le fer), `08_institutions/justice_1420.png` (le rouge du pouvoir, les bannières), `08_institutions/traite_1700.png` (les sceaux d’un engagement), `08_institutions/imprimerie_1600.png` (l’encre sur papier mat), `07_transports/grenier_1500.png` (le bois sombre), `05_chateaux/chateau_1450.png` et `10_batailles/siege_1450.png` (la masse de pierre, la gravité sans ornement).

## Lecture image par image

Les noms sont relatifs à `docs/direction-artistique/`. Chaque catégorie renvoie à sa planche conservée dans `references/`. Aucune image n’est une maquette d’interface ni ne fournit une typographie exploitable : le choix typographique ci-dessus est une proposition. Les notes portent sur matière, palette, cadrage, densité, hiérarchie ou ornements visibles ; elles ne prétendent pas authentifier l’époque.

| Image | Ce qui frappe et ce qu’on en retient |
|---|---|
| [01_scenes](references/01_scenes.jpg) / chantier_route_1750.png | Pierre claire, travail au premier plan, pont en diagonale : le chemin explique le territoire. |
| 01_scenes/etat_industriel_1900.png | Panorama dense, cuivre du couchant, fleuve conducteur : garder des axes de lecture malgré la complexité. |
| 01_scenes/hiver_disette_1690.png | Bois sombre, neige froide derrière les visages, ration au centre : l’urgence reste humaine. |
| 01_scenes/marche_1520.png | Étoffes rouges, étals proches, arcades et profondeur : richesse matérielle sans cadre surchargé. |
| 01_scenes/moisson_1450.png | Or des gerbes, gestes proches, château éloigné : la richesse vient du travail visible. |
| 01_scenes/oasis_1400.png | Terre ocre, palmes et eau, marché étagé : identité du Zab sans décor occidental. |
| 01_scenes/quartier_industriel_1840.png | Brique sombre, pavés humides, silhouettes au premier plan : densité grave, lumière parcimonieuse. |
| 01_scenes/seigneurie_1400.png | Vallée ouverte, rivière et château hiérarchisés : modèle de respiration pour la carte. |
| 01_scenes/ville_portuaire_1600.png | Bleu du port, terrasses ocre, quai très actif : relier l’économie à ses accès. |
| [02_territoires](references/02_territoires.jpg) / bassin_houiller_1880.png | Terrils noirs, champs verts, rail diagonal : plusieurs usages du sol restent discernables. |
| 02_territoires/bocage_1400.png | Haies, chemin boueux, ciel ample : frontières discrètes, territoire continu. |
| 02_territoires/crue_1780.png | Eau grise et charrette proche : montrer l’obstacle par son effet sur un trajet. |
| 02_territoires/foret_nordique_1500.png | Troncs verticaux, lac froid, bois coupé : la ressource garde une origine visible. |
| 02_territoires/littoral_1650.png | Eau turquoise, pierre pâle, crique en retrait : accents frais localisés. |
| 02_territoires/marais_1500.png | Roseaux sourds, eau calme, pêcheur isolé : lecture par silhouette, peu d’ornement. |
| 02_territoires/oliveraie_1550.png | Murs et terrasses, verts gris, paniers : relier récolte et passage. |
| 02_territoires/steppe_1600.png | Grand ciel d’orage, herbes dorées, convoi diagonal : ampleur et vulnérabilité du déplacement. |
| 02_territoires/vallee_alpine_1450.png | Roches froides, pont étroit, pente forte : le relief rend les passages évidents. |
| [03_personnages](references/03_personnages.jpg) / agronome_1760.png | Portrait entier, épi tenu, rouge discret sur bleu : une fonction par un geste. |
| 03_personnages/artisane_1500.png | Lin clair, tissu bleu, regard latéral : présence quotidienne, texture sans apparat. |
| 03_personnages/diplomate_1650.png | Noir, col clair, lettre et carte en retrait : visage d’abord, fonction ensuite. |
| 03_personnages/ingenieur_1870.png | Costume sombre, plan roulé, pont derrière : portrait contextualisé sans texte ajouté. |
| 03_personnages/institutrice_1900.png | Noir et blanc, livre, lumière de fenêtre : silhouette calme, lecture verticale. |
| 03_personnages/intendant_1420.png | Laine brune, bâton, sacs : l’autorité s’ancre dans les réserves. |
| 03_personnages/marchand_1550.png | Bleu, lin, balance et produits : identité régionale et activité visibles ensemble. |
| 03_personnages/ouvriere_1840.png | Visage fatigué, châle rouge éteint, machines : gravité sans portrait héroïque. |
| 03_personnages/seigneuresse_1400.png | Velours rouge, voile clair, fenêtre : modèle du portrait de maison, or limité. |
| [04_habitations](references/04_habitations.jpg) / chaumiere_1400.png | Chaume, bois irrégulier, potager proche : matière simple, seuil habité. |
| 04_habitations/corons_1850.png | Brique répétée, rue humide, pompe centrale : rythme collectif lisible. |
| 04_habitations/immeuble_1750.png | Enduit clair, volets, rue commerçante : niveaux de lecture du seuil à la façade. |
| 04_habitations/immeuble_bourgeois_1880_v2.png | Pierre sculptée, vitrines et rouge ponctuel : richesse concentrée aux accès. |
| 04_habitations/maison_marchand_1550.png | Pignon de brique, colombage et ballots : fonction économique dans la silhouette. |
| 04_habitations/maison_nordique_1450.png | Rondins, toit végétal, lac froid : autre vocabulaire matériel, même lisibilité. |
| 04_habitations/maison_oasis_1400.png | Pisé mat, ouverture ombragée, jarres : modèle des surfaces chaudes du Zab. |
| 04_habitations/maison_ottomane_1650.png | Étage de bois en saillie, mur clair, végétation : contraste structure/remplissage. |
| 04_habitations/quartier_mixte_1900.png | Tramway, brique et colombage mêlés : l’ancien demeure dans le monde qui change. |
| [05_chateaux](references/05_chateaux.jpg) / chateau_1450.png | Masse de pierre dominant la vallée : pouvoir identifiable sans embellir chaque bord. |
| 05_chateaux/citadelle_ottomane_1550.png | Tours claires, mer bleue, artillerie proche : défense liée au passage maritime. |
| 05_chateaux/fort_1890.png | Ouvrage bas, fossé profond, herbe : la fonction prime la hauteur spectaculaire. |
| 05_chateaux/fort_bastionne_1650.png | Étoile vue de haut, terre et pierre : géométrie explicative à l’échelle stratégique. |
| 05_chateaux/fort_cotier_1850.png | Roche, embrasures, vagues : contrainte du site directement lisible. |
| 05_chateaux/kasbah_1450.png | Tours ocre, relief et palmeraie : autorité par la masse, motifs contenus. |
| 05_chateaux/manoir_1400.png | Tour modeste, cour productive, ruisseau : départ d’une petite maison, pas d’un empire. |
| 05_chateaux/porte_urbaine_1500.png | Arche, herse, bannières verticales : un seuil clairement annoncé. |
| 05_chateaux/residence_1750.png | Façade claire, jardin ordonné, vieille tour : continuité plutôt que remplacement décoratif. |
| [06_production](references/06_production.jpg) / acierie_1880.png | Orange incandescent dans le métal gris : un seul foyer attire le regard. |
| 06_production/centrale_1900.png | Cuivre et acier, lumière haute, machines massives : précision matérielle sans néon. |
| 06_production/chantier_naval_1650.png | Coque de bois dominant les ouvriers : forme finale et effort deviennent compréhensibles. |
| 06_production/filature_1830.png | Machines répétées, fibre claire, fenêtres : densité ordonnée par les travées. |
| 06_production/forge_1450.png | Enclume, bras, petit feu : contraste chaud localisé, travail au centre. |
| 06_production/irrigation_1500.png | Eau en axe, outil et cultures : une infrastructure relie cause et résultat. |
| 06_production/manufacture_1750.png | Bois des métiers, laine et tissus rouges : stocks et transformation cohabitent. |
| 06_production/mine_1550.png | Entrée noire, bois brut, paniers : chaîne de travail lisible depuis la source. |
| 06_production/moulin_1400.png | Roue sombre, eau, sacs et charrette : miniature naturelle d’un flux physique. |
| [07_transports](references/07_transports.jpg) / canal_1830_v2.png | Porte d’écluse proche, chargement sombre : capacité et passage matérialisés. |
| 07_transports/caravane_1450.png | Contre-jour cuivre, ballots, file de bêtes : rythme du trajet sans flèches envahissantes. |
| 07_transports/charrette_1400.png | Bœufs et sacs au premier plan : transport lourd, tangible et lent. |
| 07_transports/grenier_1500.png | Bois mat, grain doré, lumière de porte : référence centrale du dossier économique. |
| 07_transports/peniche_1600.png | Halage, berge et bateau chargé : l’effort de déplacement reste visible. |
| 07_transports/port_1700.png | Grue, tonneaux et cordes, cadrage dense : fonction repérable par les outils. |
| 07_transports/relais_1780_v2.png | Cour, chevaux relayés, voiture : réseau raconté par une halte. |
| 07_transports/train_1870.png | Longue horizontale noire, pont métallique : infrastructure comme ligne directrice. |
| 07_transports/vapeur_1900.png | Coque sombre et quai chargé : conserver l’échelle humaine dans les grands transports. |
| [08_institutions](references/08_institutions.jpg) / assemblee_1790.png | Gradins courbes, lumière haute, rouge sourd : hiérarchie du regard vers la parole. |
| 08_institutions/cloitre_1500.png | Pierre chaude, livres, jardin calme : lecture intime et respiration. |
| 08_institutions/conseil_1500.png | Table commune, étoffes et coffrets : référence des dossiers de gouvernement. |
| 08_institutions/dispensaire_1860.png | Linge clair, bois, geste précis : gravité des conséquences humaines. |
| 08_institutions/ecole_1900.png | Pupitres rangés, lumière latérale : lisibilité par rythme et espace libre. |
| 08_institutions/imprimerie_1600.png | Papier crème et presse noire : référence de l’encre et des documents mats. |
| 08_institutions/justice_1420.png | Estrade, rouge et bannières : pouvoir situé, audience peuplée. |
| 08_institutions/mosquee_1550.png | Pierre claire, cour ombragée, fontaine : dignité lumineuse sans code occidental imposé. |
| 08_institutions/traite_1700.png | Table, documents et sceaux rouges : engagement matérialisé, ornements en périphérie. |
| [09_armees](references/09_armees.jpg) / artillerie_1870.png | Canon en diagonale, fumée claire : action et équipe avant spectacle. |
| 09_armees/cavalier_1500.png | Silhouette isolée, rouge et cuir : unité identifiable sans halo artificiel. |
| 09_armees/convoi_1810.png | Chariots dans l’eau, tonneaux et fatigue : l’armée dépend de son ravitaillement. |
| 09_armees/homme_armes_1450.png | Acier brillant, posture entière, cour habitée : individu militaire dans un lieu civil. |
| 09_armees/infanterie_1750.png | Bleu et blanc, rang de fusils : rythme collectif et officier distinct. |
| 09_armees/infanterie_1900.png | Bleus sombres, jumelles, pierre : regard sur le terrain, commandes discrètes. |
| 09_armees/levee_1400.png | Équipements hétérogènes, cuir et laine : hommes prélevés dans une population concrète. |
| 09_armees/mousquetaires_1650.png | Préparation proche, fumée et bois : gestes différenciés, rouge mesuré. |
| 09_armees/piquiers_1550.png | Verticales répétées, rouge et acier : bannière et silhouette pour identifier. |
| [10_batailles](references/10_batailles.jpg) / bataille_1650.png | Panorama de formations, camp proche : terrain continu derrière l’action. |
| 10_batailles/escarmouche_1550.png | Talus et feuillage encadrent les tireurs : couverture et ligne de vue lisibles. |
| 10_batailles/garde_pont_1420.png | Pont oblique, pieux, eau sombre : enjeu spatial unique et clair. |
| 10_batailles/hopital_1850_v2.png | Toile, couvertures, lumière de grange : pertes racontées par leurs conséquences. |
| 10_batailles/ligne_1810.png | Ligne en pente, fumée blanche : profondeur tactique malgré la densité. |
| 10_batailles/rail_mobilisation_1870.png | Wagons, rampes, chevaux : continuité logistique entre guerre et économie. |
| 10_batailles/retour_1900.png | Étreinte au seuil, champs derrière : le retour appartient au même monde. |
| 10_batailles/siege_1450.png | Camp chargé devant château fumant : distinguer préparation, terrain et objectif. |
| 10_batailles/siege_bastion_1700.png | Tranchées et paniers en diagonale : le siège transforme un lieu réel. |
| [11_blasons](references/11_blasons.jpg) / bois_clair_1450.png | Arbre blanc sur vert, bord de métal usé : silhouette végétale nette. |
| 11_blasons/col_des_vents_1600.png | Pont bleu et étoile rouge sur crème : deux signes hiérarchisés. |
| 11_blasons/cuivre_1650.png | Marteaux d’or sur vert sombre : outils simples, contraste matériel. |
| 11_blasons/palmeraie_1600.png | Médaillon bleu et or, palmier : format distinct ; marque fictive, pas preuve historique. |
| 11_blasons/port_ambre_1550.png | Ancre claire, rouge, étoile d’or : lecture verticale, fond franc. |
| 11_blasons/roche_haute_1450.png | Sommets blancs sur rouge : motif géométrique massif et reconnaissable. |
| 11_blasons/trois_epis_1500.png | Épis d’or sur bleu : répétition calme, finesse à simplifier aux petites tailles. |
| 11_blasons/union_forges_1880.png | Engrenage argenté, gerbe d’or, rouge : vocabulaire industriel hors du premier siècle. |
| 11_blasons/val_rive_1450.png | Roue d’or et rivière blanche sur bleu : deux niveaux, espace négatif généreux. |
| [12_drapeaux](references/12_drapeaux.jpg) / bois_clair_1450.png | Bannière verte en pointe, arbre clair : même identité, support textile. |
| 12_drapeaux/col_des_vents_1600.png | Tissu crème horizontal, pont bleu : plis doux sans perdre le motif. |
| 12_drapeaux/cuivre_1650.png | Vert sombre, marteaux dorés, large champ : signes lisibles à distance. |
| 12_drapeaux/palmeraie_1600.png | Bleu, palmier et vagues : le motif sort du médaillon sans changer d’identité. |
| 12_drapeaux/port_ambre_1550.png | Rouge vif, ancre blanche, plis : accent réservé à l’identité, pas aux alertes. |
| 12_drapeaux/roche_haute_1450.png | Bannière découpée, montagne blanche : contour distinct de l’écu. |
| 12_drapeaux/trois_epis_1500.png | Bleu profond, trois épis espacés : composition stable sur tissu mouvant. |
| 12_drapeaux/union_forges_1880.png | Rouge, cercle denté, gerbe : symbole tardif à exclure des maisons de 1400. |
| 12_drapeaux/val_rive_1450.png | Bannière bleue verticale, onde claire : vocabulaire cohérent entre les supports. |
