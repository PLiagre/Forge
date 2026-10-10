# Lot #408 — On ne bâtit que sur ses terres
Jalon : J4 · Machine : vps · Taille prévue : 290 lignes

## But
Le joueur et l'IA ne peuvent déposer une route, une parcelle ou un bâtiment que dans un bourg tenu par leur maison.

## Le joueur
Le joueur bâtit dans sa capitale, pas dans celle du voisin : tracer une route, découper une parcelle ou poser un bâtiment exige de tenir le bourg où on le fait. L'IA est tenue à la même règle. Un geste chez le voisin lui répond « ce lieu n'est pas à toi : <maître> », sans ouvrir de chantier.

Ce lot protège les gestes de J4 et leur arbitrage entre bras aux champs et bras au chantier. Il prépare l'entrée dans la capitale choisie (#409) et la transition carte-ville (#410) ; il ne livre pas leur écran. La preuve Python bâtit à Biskra. La migration de la preuve Unity fait l'objet du relais PC décrit ci-dessous, conformément à la décision A du pilote.

Prérequis vérifiés sur la base : le registre `World.maisons`, `EtatDeLieu.maitre`, leur attribution au chargement (prérequis de #391), le choix appliqué `maison_du_joueur`, les trois intentions et leurs plans sont présents. Le Zab (#407) existe : `seigneurie-6` tient le bourg de Biskra, cellule 10103. Paris est dans 10322, dont le bourg est tenu par `grande-3`, les Valois. Aucun prélèvement, flux, écran ou autre livraison encore attendue de J3 n'est nécessaire.

## Règle du monde
Découle de « Les intentions du joueur », « Les maisons du monde » et « Les lieux d'une cellule, vue dérivée » dans `jeu/sim/MODELE.md`. **Niveau 1** : maisons et sièges hérités, sans nouvelle donnée historique. **Niveau 2** : droit de bâtir attaché au maître actuel du bourg, comme le découpage plausible des lieux. **Niveau 3** : propriété des parcelles, conquête et contrôle d'une capitale distinct de la possession du bourg, hors de ce lot. Aucune constante nouvelle.

Ajouter le champ obligatoire `maison`, identifiant texte du registre, aux JSON de `tracer_route`, `decouper_parcelle` et `poser_batiment`. La garde commune lit le lieu de rang 0 de `monde.cells[cell].lieux` au moment du dépôt et compare son `maitre` avec cette maison. Elle ne recalcule pas l'attribution initiale, ne consulte pas la seule puissance de la cellule, ni le siège ou le suzerain pour autoriser un geste. Une maison connue différente reçoit exactement « ce lieu n'est pas à toi : <maître> », où `<maître>` est l'identifiant actuel du registre. Maison absente, inconnue ou mal formée, bourg absent ou maître absent/inconnu sont refusés explicitement ; rien n'est deviné. La garde précède toute modification de la file. Garder les validations géométriques et leurs messages ; l'application reste au tick suivant, sans nouvelle vérification territoriale au tick ni propriété stockée dans le plan.

Sous `verrou_tick`, le service exige une terre choisie et appliquée pour ces trois gestes : un choix encore en attente ne suffit pas. Il complète une copie de l'intention avec `maison_du_joueur`, en remplaçant une identité fournie par le client ; aucun client ne peut ainsi se faire passer pour les Valois. Le JSON normalisé passe ensuite par `recevoir_intention`, y compris pour la journalisation de la preuve. `choisir_depart` et `fixer_part` gardent leur contrat. Le reçu accepté conserve sa forme et son tick ; un refus rend 400 sans tick, publication ni dépôt.

L'IA convertit sa maison qui décide vers l'identifiant du registre (`grande-<id>` ou `identifiant_de_seigneurie(id)`) et le met dans l'intention elle-même. Son relevé conserve l'enveloppe existante `{tick, maison: {sorte, id}, intention}`. Elle ne propose rien dans un bourg tenu par une autre maison ; une donnée manquante reste un refus nommé. Faim locale, budget annuel, exclusion du joueur, ordre, absence d'aléa et dépôt commun restent exigés. `--gestes` exige la maison explicite par le même dépôt, sans dépendre d'un choix du joueur pour les gestes d'autres maisons.

Décision A déjà prise : adapter seulement le parcours Python de `pc/epreuve_jalon4.py` à Biskra. Déposer `choisir_depart` au tick 0 et l'appliquer avant les constructions, toujours aux ticks 2, 3 et 5, jusqu'au tick 10. Le journal conserve le choix et les trois gestes normalisés ; le rejeu complet les reprend tous. Le témoin rejoue le même choix au même tick, en retirant uniquement les constructions : une différence de maison choisie ne prouve pas un effet du chantier. Le jugement vérifie le choix identique et les trois types de construction non vides, l'égalité exacte service/rejeu, la différence avec le témoin, les plans et les foyers.

Inventaire des adaptations, sans assouplissement :

- `test_intentions.py` : compléter les références route/parcelle/bâtiment et les dépôts écrits directement avec leur maître réel ; les essais HTTP route et parcelle choisissent une terre, appliquée dans tous leurs témoins, puis ajustent les ticks attendus. Conserver les refus, leur ordre et leurs messages, les copies gelées, les coûts, les géométries et les contre-épreuves. L'égalité exacte du JSON IA gagne seulement `maison`.
- `test_intentions.py::test_intention_porte` et `test_chantiers.py::test_porte_achevement_ouvre_commerce` : déclarer explicitement registre et bourg maître dans leurs seuls mondes synthétiques ; ne pas faire inventer ces données au moteur ou au constructeur de geste. Garder toutes les variantes de porte et la preuve commerciale ; l'origine absente reste refusée par la validation de la porte. Les autres tests de chantier et de déterminisme utilisent les références enrichies, sans changer leurs attentes physiques.
- `test_monde.py` : les dépôts HTTP acceptés sans départ choisissent désormais une terre avant la mesure, à chronologie égale dans leurs témoins ; les routes déposées directement dans les essais de refus IA ajoutent le maître du bourg. Garder les comparaisons strictes service/CLI, le rejeu du relevé, les annulations et les empreintes sans geste. `test_carte1400.py` complète son exemple de route IA sans changer les contrôles de dessin.
- `test_epreuve_jalon4.py` : le journal normal contient le choix au tick 0 puis les trois constructions aux ticks 2, 3 et 5 ; les cellules/plans modifiés sont ceux de Biskra, dérivés du siège de la table. Ajouter les faux choix et la maison absente aux contre-épreuves ; garder journal vide, type absent, monde vide, octets altérés, faux témoin, conservation, port occupé, pannes et nettoyage. Les contrôles simulés du dessin Unity restent exigeants ; aucune capture ni référence Unity n'est remplacée.

Mettre à jour les contrats et les limites devenues fausses dans « Les intentions du joueur », « Les décisions et les gestes de l'IA » et « Le plan du bourg » de `MODELE.md`, ainsi que les exemples du README et un fichier `gestes-exemple.json` rejouable à Biskra. Factoriser la garde et les préparations de tests pour tenir sous 300 lignes de diff, brief compris.

## Périmètre
jeu/sim/intentions.py
jeu/sim/service.py
jeu/sim/ia.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/gestes-exemple.json
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_chantiers.py
jeu/vues/relief/tests/test_carte1400.py
pc/epreuve_jalon4.py
jeu/ville/tests/test_epreuve_jalon4.py
jeu/ville/README.md

## Conditions de succès
SC1 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k terres_depot` exerce les trois gestes avec une géométrie valide et leurs prérequis déjà au plan. Paris déposé par `seigneurie-3` (Morée) est refusé avec « ce lieu n'est pas à toi : grande-3 » ; le même geste par `grande-3` est accepté sans effet avant application. Contre-épreuves : retirer `maison`, fournir une identité inconnue ou mal formée, retirer le bourg ou son maître refuse sans changer monde ni file ; remplacer le maître entre deux dépôts inverse le droit, prouvant sa lecture actuelle. Prouver d'abord le rouge des nouveaux cas sur la base, notamment l'acceptation actuelle d'un geste sans maison.

SC2 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k terres_service` exerce chacun des trois types HTTP : sans choix ou avec choix en attente, refus ; après choix appliqué du Zab, dépôt à Biskra accepté et normalisé vers `seigneurie-6`. Contre-épreuve : envoyer `maison: grande-3` avec une cellule parisienne reste refusé, même après ce choix ; vérifier file, plan, tick et octets publiés inchangés à chaque refus. Le reçu accepté annonce le tick publié et le plan attend le suivant.

SC3 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k terres_ia` joue une année complète, graine 0, et contrôle chaque dépôt au moment où il arrive dans `recevoir_intention` : identité de l'intention égale à celle de la maison qui décide et au maître du rang 0. Le nombre de dépôts et celui des maisons contrôlées sont dérivés du relevé et strictement positifs. Contre-épreuves : attribuer un dépôt réel du relevé à une autre maison connue échoue au contrôle ; un relevé vide échoue ; une maison dont le bourg passe à un voisin ne propose plus de route. Garder le budget annuel et les autres cas IA existants.

SC4 — Depuis `jeu/`, `python3 -m sim --ticks 10 --seed 0 --gestes sim/gestes-exemple.json --monde-json /tmp/forge-408-exemple.json` réussit ; `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k 'ligne_de_commande_gestes or terres_gestes'` rejoue deux fois cet exemple et compare les octets, puis contrôle ses trois constructions à Biskra. Contre-épreuves : retirer `maison` d'un geste ou lui donner la Morée fait rendre 2, nomme l'entrée fautive et n'écrit aucune sortie neuve ; déplacer un point conserve l'échec de l'égalité existante.

SC5 — `python3 pc/epreuve_jalon4.py --sortie /tmp/forge-408-j4` rend 0 avec un départ Zab appliqué et identique dans les trois mondes, les trois gestes, des cellules et plans modifiés non vides, et service/rejeu égaux à l'octet. Contre-épreuve : `python3 pc/epreuve_jalon4.py --sortie /tmp/forge-408-j4-sourd --service-sourd` rend 1 parce que le bâtiment manque. `python3 -m pytest jeu/ville/tests/test_epreuve_jalon4.py -q` garde les falsifications existantes et ajoute un témoin sans départ ou avec un autre départ, tous refusés.

SC6 — `python3 -m pytest jeu/sim/tests/test_intentions.py jeu/sim/tests/test_chantiers.py jeu/sim/tests/test_determinisme.py jeu/sim/tests/test_monde.py jeu/vues/relief/tests/test_carte1400.py -q`, puis `python3 -m pytest jeu -q`, restent verts. Contre-épreuves : l'étape d'application neutralisée, la géométrie altérée, les foyers mal désagrégés et le relevé IA amputé continuent de faire échouer leurs contrôles existants. Aucun test supprimé, ignoré ou comparaison partielle ; aucune empreinte sans geste régénérée pour masquer une différence.

SC7 — `git diff --numstat` permet de sommer lignes ajoutées et retirées, y compris le brief et le nouvel exemple après leur prise en compte par le pilote : total strictement inférieur à 300. `git diff --name-only` ne contient que les chemins autorisés et le brief. Contre-épreuves : un total de 300 ou une écriture Unity fait refuser la livraison. `jeu/ville/README.md` consigne le relais PC et distingue les commandes Python validées de la preuve Unity encore à migrer ; prétendre cette dernière validée sans exécution PC fait refuser la livraison.

## Hors périmètre
Unity, Blender, scènes, captures et exécution `--avec-unity`. Relais explicite au pilote, selon la décision A : un lot PC distinct « La preuve Unity bâtit à Biskra après le choix du Zab », après #408, doit adapter `DesertCityPreuve.cs`, ses reçus, la recette Unity de `pc/epreuve_jalon4.py` et les parcours jouer/relance/vierge ; rejouer le même départ dans le témoin et réexécuter normal, service sourd et ville locale, avec capture. Il n'y a dans #408 aucune exemption territoriale pour conserver l'ancienne recette en 1175. L'ouverture normale de la capitale reste #409 ; ce relais concerne la preuve et doit être suivi séparément, sans être déclaré livré par ce brief.

Restrictions supplémentaires à une capitale parmi plusieurs bourgs possédés, cadastre, achat de parcelle, conquête, prélèvement, salaire en grain (#413), moisson saisonnière (#415), enceinte (#416), route vers les champs (#418), autres gestes IA et autres travaux de J3. Aucun changement du tick, du chargement, de la carte, de l'attribution des maîtres ou des tables historiques. Tout autre chemin que ceux du périmètre est interdit.
