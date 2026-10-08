# Lot #394 — Chaque seigneur a son grenier, qui se garde mal
Jalon : J3 · Machine : vps · Taille prévue : 285 lignes

## But
Le monde saura conserver séparément les réserves de chaque maison et retrouver dans ses pertes chaque kilogramme de nourriture abîmé au grenier.

## Le joueur
Fond. Le grenier est ce que le joueur gagne à prélever et ce qu'il peut rendre à ses gens : ce lot prépare « Le seigneur prélève sa part, et elle voyage jusqu'à son grenier » (#396) et « Le joueur ouvre son grenier à ses lieux » (#398). Garder du grain aura un coût : les rongeurs et la moisissure entament la réserve, tandis que rendre du grain en mauvaise année pourra retenir ses gens. #400 et #401 montreront cette réserve dans le service et la carte de la forge ; #405 permettra ces gestes sur la carte de Unity. Plus tard, le grenier paiera ses chantiers (J4, #413) et nourrira son armée (J7).

## Règle du monde
Dépend de : #390, dont le registre et son intégration au monde sont livrés par #512 et #513. Découle des sections « Les maisons du monde », « Le panier de marchandises », « La base de temps » et « Le moteur sans état caché » de `jeu/sim/MODELE.md`. Ajouter « Le grenier d'une maison » et actualiser « En une page » ainsi que les mentions des greniers encore non simulés.

Chaque maison du registre, institutions et maison du joueur comprises, possède un panier `grenier` (marchandise → kilogrammes), vide au chargement et indépendant de tous les autres paniers. Son emplacement est celui du siège déjà déclaré : (`cell_id`, `rang`), sans recopier une clé spatiale ni inventer de lieu pour un siège déclaré hors carte. Les habitants ne mangent jamais dans ce panier ; production, fabrication, commerce et répartition sur les lieux ne le remplissent ni ne le déplacent.

Conserver les fiches d'identité gelées et leur sérialisation actuelle à huit champs. Porter les réserves dans `World.greniers`, dictionnaire identifiant de maison → panier : `World.greniers[maison.id]` est le grenier de cette maison, pas une copie d'un stock ailleurs. Initialiser un panier distinct par fiche lors du chargement, et `{}` pour un `World(...)` sans registre. Le tick lit cet état matériel directement, sans consulter `World.maisons`, les tables ou les vues. Aucun changement de `MaisonDuMonde` ni des tests existants n'est nécessaire.

Déclarer `PERTE_GRENIER_PAR_AN = 0.25` dans `constants.py`. La part par tick est `p = PERTE_GRENIER_PAR_AN * TICK_DURATION_DAYS / CALENDAR_DAYS_PER_YEAR`. Sur le stock alimentaire courant `S`, retirer `S * p` une seule fois par tick ; après `n` ticks sans apport, le reste attendu est `S_initial * (1 - p)**n`. Il s'agit d'une perte journalière composée, sans retrait annuel supplémentaire. Relire les constantes par leur module à chaque calcul, dans une fonction dédiée ; aucun littéral de durée indépendant ni aléa.

Ajouter un maillon dans `sim/greniers.py`, appelé par `engine.tick` après la validation du numéro de tick, avant la fabrication. Respecter les objets d'épreuve historiques sans état de grenier, sans leur ajouter de réserve. Un panier vide reste exactement vide ; une nourriture explicitement à zéro reste à zéro ; une marchandise absente n'est pas ajoutée. Les autres marchandises gardent exactement leur poids.

Le monde n'a pas encore de compteur général de pertes : initialiser explicitement `World.pertes_kg = 0.0`, cumul en kilogrammes, et y ajouter chaque retrait effectif du grenier, sans arrondi. Ce stock perdu ne devient ni dette alimentaire ni nourriture ailleurs. `to_dict()` ajoute `greniers` seulement s'il existe des paniers non vides, indexés par identifiant et triés, avec des copies indépendantes sans arrondi ; ajouter `pertes_kg` seulement si le cumul est non nul. Ne changer aucune clé existante : tous les greniers vides et aucune perte doivent garder les octets antérieurs.

Niveau 2, plausible, jamais sourcé : taux de perte par rongeurs et moisissure. Niveau 3 : capacité du grenier et dégradation des autres marchandises, non simulées. Identités, sièges et raisons hors carte sont conservés. Budget indicatif, brief compris : moteur, état et constantes 70 lignes, nouveaux cas 140, modèle 20, brief 55 ; diff total inférieur à 300 lignes.

## Périmètre
jeu/sim/world.py
jeu/sim/constants.py
jeu/sim/engine.py
jeu/sim/greniers.py
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_survie.py
jeu/sim/tests/test_determinisme.py
jeu/sim/MODELE.md

## Conditions de succès
Commandes depuis `jeu/`, sauf SC6. Ajouter uniquement des cas aux fichiers qui portent les invariants, avec les noms indiqués ; prouver leur rouge avant l'implémentation. Les maisons attendues et compteurs se dérivent du registre ; toute épreuve positive exige des maisons et des points mesurés non vides. Les remplissages sont exclusivement des montages d'épreuve, jamais un apport du jeu.

SC1 — `python3 -m pytest sim/tests/test_maisons.py -q -k grenier_etat` vérifie un panier vide distinct pour chaque identifiant du registre, toutes sortes comprises, les homonymes séparés, et le registre matériel vide d'un monde sans maisons. Remplir une réserve ne change ni celles des autres maisons ni les paniers du siège ; les raisons hors carte restent intactes. Contre-épreuves : enlever un grenier, fusionner deux homonymes ou partager leur dictionnaire fait échouer le même contrôle de complétude ou d'indépendance.

SC2 — `python3 -m pytest sim/tests/test_survie.py -q -k grenier_pertes` joue 365 véritables ticks sur une réserve d'épreuve de 1 000 t, soit 1 000 000 kg. Vérifier le reste et la perte contre la formule ci-dessus avec un écart strictement inférieur à un kilogramme, et le cumul contre les retraits mesurés. Vérifier également un panier vide, une nourriture à zéro et une marchandise non alimentaire ; remplacer le taux par zéro puis par une autre valeur doit changer les résultats comme la formule le prévoit. Contre-épreuves : neutraliser le maillon ou injecter une perte double fait échouer la formule ; abîmer la marchandise non alimentaire ou ajouter une clé au panier vide fait échouer leur stabilité.

SC3 — `python3 -m pytest sim/tests/test_survie.py -q -k grenier_conservation` vérifie à chaque tick `stock_initial = stock_restant + (pertes_apres - pertes_avant)` sur un monde d'épreuve sans autre flux, avec plusieurs greniers alimentaires non vides et un cumul initial connu. La référence est le stock réellement injecté et mesuré ; vérifier le bilan à moins d'un kilogramme, sans effacer le cumul entre ticks. Contre-épreuves : retirer la nourriture puis restaurer seulement le compteur à sa valeur précédente doit faire échouer ce contrôle ; compter deux fois une perte échoue aussi. Un contrôle sur zéro grenier éprouvé est refusé.

SC4 — `python3 -m pytest sim/tests/test_maisons.py -q -k grenier_serialisation` vérifie l'absence des nouvelles clés lorsque toutes les réserves sont vides, puis les seuls paniers non vides et le cumul exact après une perte. Permuter les paniers ne change pas les octets ; modifier le document rendu ne modifie pas le monde. Contre-épreuves : omettre un panier rempli, arrondir un poids fractionnaire, publier un panier vide ou perdre le cumul fait échouer les assertions correspondantes. Les anciennes fiches sérialisées restent exactement celles du registre.

SC5 — `python3 -m pytest sim/tests/test_determinisme.py -q -k grenier_bit_pres` compare deux mondes distincts, l'un normal aux greniers vides, l'autre avec le seul nouveau maillon neutralisé. Comparer dès le chargement puis après chacun des 365 ticks, pour plusieurs graines dont 0 et 42 : octets complets de `to_dict()`, cellules et lieux sans arrondi, bassin maritime, retours du tick et états des générateurs. Aucune clé n'est retirée pour cette comparaison. Comparer aussi les cellules d'un monde au grenier rempli à celles d'un témoin vide : la faim et la consommation du siège restent identiques. Contre-épreuves : modifier un stock d'un seul flottant représentable, faire manger le siège dans son grenier ou supprimer tous les points doit faire échouer la garde correspondante.

SC6 — Depuis la racine, `python3 -m pytest jeu -q` et `git diff --check` réussissent. Conserver notamment `test_pure`, `test_registre_serialisation`, `test_registre_tick`, `test_registre_bit_pres`, les contrôles des constantes et ceux des paniers : aucune assertion existante n'est réécrite. Contre-épreuves : la lecture de `World.maisons` injectée par le test existant reste refusée ; le défaut de compteur de SC3 fait rougir la suite. `python3 -c 'from pathlib import Path; t=Path("jeu/sim/MODELE.md").read_text(); assert t.count("\n## Le grenier d\x27une maison\n") == 1; assert "PERTE_GRENIER_PAR_AN" in t'` vérifie la section ; retirer celle-ci d'une copie fait échouer le même contrôle. Relire son emplacement, sa formule, son bilan et ses niveaux contre les preuves.

## Hors périmètre
Tout apport au grenier, prélèvement (#396), voyage des parts, dû au suzerain (#397), ouverture aux lieux (#398), nouvelle intention ou décision d'IA. Aucun remplissage initial, capacité, bâtiment de stockage, dégradation non alimentaire, changement de propriété ou de siège, salaire de chantier ou ravitaillement militaire. Aucune modification des tables, des vues, des schémas d'export, du service ou de Unity ; aucun travail Blender. Aucun assouplissement d'un test existant. Tout chemin absent du périmètre est interdit en écriture.
