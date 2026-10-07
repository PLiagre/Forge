# Lot #259 — Une route finie concentre le commerce
Jalon : J4 · Machine : vps · Taille prévue : 285 lignes

## But
Le joueur pourra tourner une route vers une cellule voisine pour y faire passer davantage de commerce dès son achèvement, donnant du poids au choix de J4 « vers les champs, ou vers le marché ».

## Règle du monde
Règle de **niveau 2**, plausible, jamais sourcée, issue de « Le commerce entre cellules / La capacité d'une arête », « Les intentions du joueur », « Le plan du bourg » et « Le chantier et ses bras » de `jeu/sim/MODELE.md`. Le propriétaire a choisi **A** dans les commentaires de #259 ; cette décision est acquise.

La base contient `TraceRoute`, `Rue`, `World.plans`, le compte des journées et l'achèvement par `avancer_chantiers`. Les apports nécessaires de #258 sont présents : parcelles, bâtiments et leurs chantiers. Ce lot ne demande aucune livraison restante de J3 ; il ne change ni les maîtres des lieux, ni leurs prélèvements.

Le geste `tracer_route` reçoit un champ facultatif `porte_cell_id`, ajouté en fin des champs de `TraceRoute` et de `Rue` pour préserver leurs appels positionnels. Absent ou `null`, il signifie une route locale, sans effet sur le commerce entre cellules. Sinon, c'est un `cell_id` entier non négatif, sans booléen : une voisine terrestre distincte de la cellule du tracé. Le dépôt vérifie avant toute mise en attente que les deux cellules existent et qu'une arête de `world.adjacency` les relie. Comme le commerce terrestre actuel, cette relation relie deux cellules de `world.cells` ; un nœud mer ne convient pas. Aucun voisin n'est déduit des points ou du centre du bourg.

La porte est copiée dans l'intention gelée, puis dans la rue au tick suivant. Elle survit aux reconstructions du chantier par `dataclasses.replace`. `Plan.to_dict()` omet `porte_cell_id` quand il vaut `None` : les anciennes rues et les routes locales gardent leurs octets, y compris dans `/plan` et l'empreinte. Une porte renseignée figure dans ces mêmes sorties existantes, sans nouvelle clé spatiale ni nouvel identifiant de porte. `Rue` contrôle le type ; le dépôt contrôle le voisinage.

Une rue achevée (`en_chantier == False`) tournée vers cette voisine fournit **5 000 kg par tick et par mètre de largeur**, soit 20 t/jour pour 4 m au tick d'un jour. Déclarer `DEBIT_ROUTE_KG_PAR_M_PAR_TICK = 5000.0 * TICK_DURATION_DAYS` dans `constants.py`, lu par une fonction qui relit sa valeur à chaque appel. Les largeurs des rues achevées de a vers b et de b vers a s'additionnent, en ordre stable ; une route d'un seul côté suffit. Elles servent le plafond commun de l'arête, dans les deux sens et pour toutes les marchandises, sans multiplier les kilogrammes disponibles.

Dans `_capacite_transport_arete_kg`, unique lieu de calcul de la capacité terrestre :
`capacité = (base_frontière_actuelle + débit_route × somme_largeurs_achevées) × goulot_actuel`.
Le goulot reste le minimum des facteurs des deux reliefs ; sans carte, il vaut implicitement 1 comme aujourd'hui. La route de 4 m ajoute donc 6 000 kg en montagne. Le repli sans `shared_length_m` reste celui d'aujourd'hui. Une frontière ponctuelle garde une base nulle mais peut recevoir le débit d'une route. Une longueur ou un relief invalide reste refusé ; la route ne masque aucune erreur.

Sans apport routier, conserver exactement les opérations et retours actuels, notamment le retour immédiat pour une base nulle : aucune capacité ne change au bit près. Une rue locale, une rue en chantier et une rue tournée vers un autre voisin n'ajoutent rien à cette arête. La somme des largeurs se dérive dans une fonction de `plan.py` qui lit le monde passé, sans cache ni état global ; `engine.py` l'appelle sans accéder directement à `.plans`. Les mondes d'épreuve sans plans conservent leur comportement déclaré. Le commerce lit l'état après Chantiers : l'apport commence au tick où le travail requis est atteint.

Actualiser les sections citées de `MODELE.md`, « En une page » et les déclarations d'absence devenues fausses (« investir », routes dans « Le mur qui sépare la couche 1 de la couche 2 », effet des rues achevées). Distinguer l'apport commercial désormais simulé des effets locaux et des autres infrastructures encore absents.

## Périmètre
jeu/sim/plan.py
jeu/sim/intentions.py
jeu/sim/constants.py
jeu/sim/engine.py
jeu/sim/MODELE.md
jeu/sim/tests/test_lieux.py
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_chantiers.py
jeu/sim/tests/test_commerce.py

## Conditions de succès
Toutes les commandes partent de la racine. Ajouter les cas aux fichiers indiqués, sans modifier les assertions des tests existants. Prouver leur rouge avant le code. Chaque échantillon de cellules, rues ou arêtes utilisé est explicitement non vide. Le budget de 285 lignes inclut ce brief, environ 65 lignes de code, 110 lignes de tests et 30 lignes de modèle ; mutualiser les montages et paramétrer les cas.

**SC1 — Le joueur choisit une porte valide, sans effet au dépôt.**
`python3 -m pytest jeu/sim/tests/test_intentions.py jeu/sim/tests/test_lieux.py -q -k porte`
Ajouter les cas : absent, `null`, voisine réelle ; refus de `True`, texte, flottant, négatif, cellule inconnue, soi-même, cellule connue sans arête et nœud mer. Chaque refus nomme la porte et conserve plan, cellules et file. Un geste accepté conserve aussi le monde publié ; changer le JSON d'origine ne change pas la porte gelée. Au tick suivant, la rue porte la voisine. Le plan avec porte se reconstruit depuis son dictionnaire sans perte ; sans porte, le dictionnaire reste exactement celui de la base, clé absente. `Rue` refuse les mauvais types avec `PlanInvalide`. Contre-épreuve : falsifier la porte de la copie publiée fait échouer le contrôle de correspondance avec le geste ; le geste vers une non-voisine échoue avant son ajout à la file.

**SC2 — Le débit s'ajoute à la seule frontière choisie.**
`python3 -m pytest jeu/sim/tests/test_commerce.py -q -k routes_commerciales_capacites`
Sur un monde explicite avec au moins trois cellules et deux arêtes, contrôler la formule pour 4 m en plaine (+20 000 kg), en montagne (+6 000 kg), sans carte, avec longueur absente et avec longueur nulle. Comparer les deux sens et les appels avec et sans index. Paramétrer : route locale, route inachevée, autre porte, plusieurs rues et routes aux deux extrémités ; seule la somme des largeurs achevées concernées compte. La seconde arête conserve sa capacité exacte. Vérifier que longueur ou relief invalide reste refusé. Contre-épreuve : doubler la nouvelle constante en mémoire double seulement l'apport ; le contrôle nominal échoue. Retirer la contribution routière fait également échouer les attentes positives.

**SC3 — Le vrai chantier ouvre le commerce à son achèvement.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k porte`
Déposer une route de 6,5 m × 4 m, un foyer, vers une voisine : 13 journées requises sur la base. Avec assez de paysans, jouer les vrais ticks ; relever à l'entrée du commerce les capacités et la rue, sans remplacer Chantiers. Les deux premiers ticks ont 5 puis 10 journées fournies et la capacité ancienne ; le troisième a 13 journées, une rue achevée portant toujours sa porte et l'apport de 4 m. Le quatrième garde cet apport, sans nouvelle journée. Contrôler aussi le retour des bras et leur conservation avec les contrôles existants. Contre-épreuve : neutraliser `_avancer_chantiers` laisse la rue inachevée et fait échouer le contrôle du troisième tick.

**SC4 — Davantage de marchandises passent, sans en créer.**
`python3 -m pytest jeu/sim/tests/test_commerce.py -q -k routes_commerciales_flux`
Rejouer un petit monde avec source en surplus et receveuse en manque, tous deux au-delà du plafond avec route ; isoler le maillon commerce pour mesurer ses transferts. Avec route achevée et porte, le débit atteint la nouvelle capacité et dépasse strictement le témoin local sans porte. La masse totale reste identique et la baisse de la source égale le gain de la receveuse. Étendre les cas de budget partagé entre marchandises : la somme des transports ne dépasse jamais la capacité de l'arête. Deux mondes recevant les mêmes gestes et la même graine donnent le même état et le même état du générateur. Contre-épreuve : ignorer l'apport fait échouer l'inégalité stricte ; une copie avec un kilo ajouté fait échouer la conservation.

**SC5 — Sans route commerciale, la référence reste exacte et toute la suite passe.**
`python3 -m pytest jeu/sim/tests/test_commerce.py -q -k routes_commerciales_reference`
Réutiliser la référence figée `_REFERENCE_TICK_331` et le montage de `test_index_aretes_premiere_entree_repli_et_tick_suivant`, sans les modifier. Ajouter les variantes sans rue, rue locale achevée et rue avec porte encore en chantier, avec longueurs présente, absente et nulle et reliefs différents. Comparer les capacités à la référence par `float.hex()`, ainsi que les budgets initialisés, avec et sans index. Contre-épreuve : une capacité de référence falsifiée fait échouer la même comparaison.
`python3 -m pytest jeu -q` doit rester vert, notamment `test_plan_absent_de_l_arbre_du_moteur`, les routes locales déterministes, les dictionnaires exacts du service, `test_frontiere_ponctuelle_transport_zero`, le partage du plafond, `test_write_coverage.py` et `test_no_hardcoded.py`. Contre-épreuves existantes conservées : une lecture directe `world.plans` dans le moteur et une autre cellule altérée sont détectées. Aucun test existant n'est réécrit.

**SC6 — Le modèle décrit ce que les preuves jouent.**
`python3 -m pytest jeu/sim/tests/test_commerce.py -q -k routes_commerciales_modele`
Ajouter un contrôle qui lit les sections concernées et exige la porte facultative, le niveau 2, la constante, la somme des largeurs, le goulot, l'activation à l'achèvement et la compatibilité sans apport. Les phrases affirmant que la route achevée n'a aucun effet sur les flux disparaissent des déclarations actuelles. Contre-épreuve : supprimer la constante du texte lu ou y réintroduire cette absence fait échouer le même contrôle.

## Hors périmètre
Distribution entre champs et bourg, modification de la récolte, du coût ou des bras du chantier ; revêtement, ponts, ports, entretien, matériaux, salaires et prix. Aucun calcul de direction depuis la géométrie, raccordement entre tracés, déplacement du bourg ou création d'une entité porte. Aucun bonus maritime, aucune modification de la carte figée ou de l'allocation du commerce. Aucun changement d'Unity, Blender, du traceur 3D, du service ou des vues ; la porte est jouable par l'intention existante. Aucune nouvelle politique de l'IA : ses gestes locaux actuels restent valides. Aucun assouplissement ni réécriture d'un test existant. Tout chemin absent du périmètre est interdit.
