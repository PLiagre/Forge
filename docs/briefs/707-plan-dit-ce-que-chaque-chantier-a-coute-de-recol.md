# Lot #707 — /plan dit ce que chaque chantier a coûté de récolte
Jalon : J4 · Machine : vps · Taille prévue : 275 lignes

## But
Le monde saura mesurer et publier la récolte que chaque chantier a fait perdre le jour même.

## Le joueur
Le joueur lit le prix agricole réel de chaque grand chantier : après avoir choisi de bâtir, il voit combien de récolte ses bras ont coûté ce jour-là et peut arbitrer entre poursuivre les travaux et garder ses gens aux champs. Ce lot rend ce coût disponible dans `/plan` ; #419 le montrera dans le panneau de la capitale et #508 dans la preuve complète de J4.

## Règle du monde
Niveau 2, plausible, jamais sourcé. Le lot découle de la section « Le chantier et ses bras » de `jeu/sim/MODELE.md`.

- Pour chaque chantier ordinaire, conserver pendant le tick le nombre de bras qu’il a pris à chaque lieu. Cette origine est une observation renouvelée, absente des sauvegardes et sans effet sur le travail, le salaire ou la récolte.
- À la production, mesurer pour chaque lieu l’écart entre sa récolte calculée avec les bras restés aux champs et la même récolte avec tous les bras des chantiers du jour rendus, sans nouveau tirage ni second tick. Répartir cet écart entre les chantiers au prorata des bras que chacun a pris dans ce lieu, puis sommer leurs parts sur les lieux. Ainsi, la somme attribuée aux chantiers égale exactement l’écart que le moteur mesure entre chantier et témoin ; des bras encore excédentaires en hiver ne créent aucun coût fictif.
- `/plan?cell=X` publie à sa racine la clé voisine `recolte_perdue_par_chantier` seulement si au moins un coût est strictement positif dans la cellule. Sa liste est triée rue, parcelle, bâtiment, puis identifiant ; chaque ligne porte exactement `nature`, `identifiant`, `recolte_perdue_kg`. Les kilos restent sans arrondi. Ne pas ajouter de champ aux lignes de `chantiers_du_jour`, dont les cinq clés restent exactes.
- Une autoconstruction, un chantier sans bras et un coût nul ne produisent aucune ligne. Le relevé est celui du dernier jour publié, figé avec son tick et sa date comme `chantiers_du_jour`, et ne se recalcule jamais à la lecture.

## Périmètre
jeu/sim/world.py
jeu/sim/chantiers.py
jeu/sim/engine.py
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_chantiers.py
jeu/sim/tests/test_monde.py
docs/briefs/707-plan-dit-ce-que-chaque-chantier-a-coute-de-recol.md

Tout autre chemin est interdit. Viser 275 lignes ajoutées et retirées, brief compris, sans reformater les fichiers.

## Conditions de succès
SC1 — Écrire d’abord les cas puis, depuis la racine, lancer `python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k recolte_perdue_par_chantier` : ils doivent rougir sur l’observation absente, puis passer. Dans un monde amorcé en juillet, déposer par les intentions au moins deux chantiers ordinaires qui prennent des bras dans au moins deux lieux, avec assez de grain ; dériver du moteur, au même rendement et avant prélèvement, l’écart de récolte de chaque lieu lorsque tous les bras des chantiers lui sont rendus. Exiger pour chaque chantier la somme des écarts locaux au prorata exact de ses propres bras, une somme générale strictement positive et égale à l’écart total mesuré. Contre-épreuves : échanger les origines de deux chantiers, attribuer tout l’écart au premier, refaire un tirage, compter le salaire ou publier zéro doivent faire échouer le vérificateur ; un échantillon vide échoue explicitement.

SC2 — `python3 -m pytest jeu/sim/tests/test_monde.py -q -k 'plan_chantiers_du_jour or plan_recolte_perdue_par_chantier'` prouve le contrat HTTP par le vrai service. Avant tout chantier et dans une autre cellule, `recolte_perdue_par_chantier` est absente. Une route financée et travaillée en juillet publie une ligne strictement positive, sans arrondi, égale à l’écart de récolte mesuré par le moteur au même tick ; l’ordre des natures et identifiants est stable. Les lignes existantes de `chantiers_du_jour` gardent exactement leurs cinq clés. L’ancien état publié garde ses octets après mutation du monde. Contre-épreuves : une ligne à zéro, un champ ajouté à `chantiers_du_jour`, le relevé d’une autre cellule ou un recalcul à la lecture font échouer les assertions.

SC3 — `python3 -m pytest jeu/sim/tests/test_chantiers.py jeu/sim/tests/test_monde.py jeu/sim/tests/test_determinisme.py -q`, puis `python3 -m pytest jeu -q`, passent. Vérifier que les origines et coûts journaliers n’entrent ni dans `World.to_dict()` ni dans les photographies, que deux parties identiques publient les mêmes octets, et que `MODELE.md` ainsi que le contrat de `/plan` nomment la mesure, son unité, son absence et son partage par lieu. Contre-épreuve : aucun test existant, comparaison exacte, garde d’absence, contrôle de conservation ou invariant documentaire n’est retiré, réécrit ou assoupli.

## Hors périmètre
Affichage dans Unity et panneau #419 ; cumul sur plusieurs jours ou estimation du coût restant ; choix de priorité entre chantiers ; changement du besoin de bras, de la saison, du rendement, du salaire, du grenier, du prélèvement ou des métiers ; autoconstruction ; déplacement individuel des ouvriers ; nouvelle règle agricole ou nouveau tirage.
