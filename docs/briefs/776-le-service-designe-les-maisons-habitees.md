# Lot #776 — Le service désigne les maisons habitées
Jalon : J4 · Machine : vps · Taille prévue : 260 lignes

## But
Le service désigne de manière déterministe les maisons et îlots habités de la ville de 1400 et les maisons bâties qui logent des artisans, sans changer les comptes du logement.

## Le joueur
Le joueur verra quelles maisons de sa capitale sont habitées : leurs fumées et leurs lumières suivront les foyers annoncés par le monde, plutôt qu'un choix fait dans Unity. Ce lot de fond prépare le geste de J4 « des murs, ou des maisons » et l'écran « ses foyers par métier, leur logement » ; la suite PC de #420, dont il est découpé, rendra cette occupation visible. La demande fournie n'a pas de phrase « Le joueur » distincte : cette phrase explicite son bénéfice selon « La règle d'un lot » de `CAP.md`.

## Règle du monde
Sans objet : projection du service, sans nouvelle règle de simulation. Elle expose les conventions de **niveau 2**, plausibles, de `jeu/sim/MODELE.md`, « Les foyers par métier » et « Le plan du bourg » → « Le plan de base ». La réponse A du propriétaire sur #411, consignée dans le brief #566, s'applique : les maisons de 1400 sont pleines de leurs familles ; les artisans n'ont que les maisons bâties ; le logement et son panneau gardent leurs comptes. Aucune décision à reposer.

**Dépend de : #775**, livré sur cette base. Les deux lots écrivent `service.py` et `test_monde.py` ; conserver notamment l'extension `bourg=1` et ses tests.

Contrat à livrer :

- Ajouter `GET /occupation?cell=X`, réponse JSON canonique contenant exactement `cell_id`, `rang` (0), `tick`, `date`, `base`, `batiments`, `logement`. Les routes existantes gardent leurs documents et leurs octets ; aucun paramètre nouveau n'est nécessaire sur `/plan` ou `/lieu`.
- `base` est une liste de `{rang, foyers}`, dans l'ordre de `base.maisons` de `/plan`. Le rang est l'indice de la maison ou de l'îlot dans cette liste ; `foyers` reprend exactement sa valeur, y compris pour un îlot de plusieurs foyers. Toutes ces places sont habitées selon #411. Leur somme égale le nombre de foyers de la population du bourg à l'amorçage, dernier foyer incomplet compris. Ce peuplement initial reste celui de la base, sans réaffectation selon la population courante.
- `batiments` contient les seules maisons achevées du plan, triées par `identifiant`, chacune sous la forme `{identifiant, capacite, loges}`. Sa capacité suit exactement le logement existant : `max(1, int(aire_du_contour(emprise) // SURFACE_M2_PAR_FOYER_LOGE))`. Répartir le total existant `logement.loges` dans cet ordre : chaque maison prend le minimum de sa capacité et des foyers restant à placer. Une maison vide reste présente avec `loges: 0` ; un chantier ou un atelier est absent de cette liste. Ce tri est une convention de présentation, sans attribution de familles dans le monde.
- `logement` recopie exactement le bloc de `/lieu` du même état, ou vaut `null` quand ce bloc est absent. Les capacités et les logés des bâtiments retrouvent ses totaux ; `sans_logis` reste inchangé. Les foyers de la base ne s'ajoutent jamais à ces totaux et ne réduisent pas les sans-logis. Sans métiers calculés, chaque maison garde sa capacité et publie `loges: -1`, comme le total : aucun zéro n'est deviné.
- Les comptes des bâtiments et du logement sont copiés pendant `_construire_etat`, portés par `EtatPublie` et lus sans consulter le monde mutable. Réutiliser le calcul et le cache de base du service : calcul géométrique au plus une fois par cellule, jamais dans le tick ni pour toutes les cellules au démarrage. La partie d'occupation de la base peut être préparée et sérialisée avec ce cache immuable ; ne pas recopier sa géométrie dans la nouvelle réponse.
- `cell` absent, vide, répété ou non entier : HTTP 400 ; cellule inconnue : HTTP 404 ; base absente : HTTP 500 avec cellule et cause, par le refus `BaseAbsente` existant. Aucune réponse partielle ni liste vide de remplacement. Une cellule valide sans habitants peut rendre des listes vides et des zéros mesurés. `cell_id` reste la seule clé spatiale ; indices et identifiants sont ceux des objets existants, sans nouvelle clé de famille.

Documenter la route et ces conventions dans `MODELE.md`, près du logement et du plan de base, en conservant les règles actuelles. Aucun test existant ne doit rougir : sont notamment concernés les dictionnaires exacts du logement, son absence sans bâtiment, les réponses figées aux ticks 3 et 4, les empreintes sans IA, la base constante calculée une fois et la liste exacte de ses modules lecteurs. Le code reste dans `service.py`, déjà autorisé à lire cette base.

## Périmètre
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/tests/test_monde.py
docs/briefs/776-le-service-designe-les-maisons-habitees.md

## Conditions de succès
Commandes depuis la racine. Ajouter les cas à `test_monde.py`, sans retoucher les tests, aides, références ou assertions existants. Montrer d'abord leur rouge sur l'absence de la route, puis leur vert. Utiliser le vrai traitement HTTP d'un service à l'arrêt et des montages préparés avant publication. Les références viennent des plans, métiers et constantes, sans appeler la nouvelle projection ; les échantillons exigés ci-dessous ne peuvent pas être vides. Le diff total, brief compris, reste strictement inférieur à 300 lignes.

SC1 — **Les familles de la base sont toutes désignées.** Commande : `python3 -m pytest jeu/sim/tests/test_monde.py -q -k service_occupation_base`.
Sur une petite base habitée et une base dépassant `FOYERS_SANS_ILOTS`, comparer exactement indices et foyers à `/plan.base.maisons`, puis leur somme au rangement de la population d'amorçage. Exiger au moins un îlot de plusieurs foyers et couvrir un dernier foyer incomplet. Répéter après changement de la population courante : la base demeure identique. Contre-épreuves : retirer une maison, remplacer les foyers d'un îlot par 1 ou recalculer depuis la population courante fait échouer le même vérificateur.

SC2 — **Chaque maison bâtie retrouve les comptes du logement.** Commande : `python3 -m pytest jeu/sim/tests/test_monde.py -q -k service_occupation_batiments`.
Présenter à l'envers les identifiants d'au moins trois maisons achevées, de capacités différentes, avec une maison en chantier et un atelier. Paramétrer zéro artisan, une demande inférieure à la capacité laissant une maison partiellement occupée et une vide, puis une demande supérieure laissant des sans-logis, dernier foyer incomplet compris. Vérifier chaque affectation dans l'ordre déclaré, les bornes et les sommes exactes face à `/lieu.logement` au même tick. Ajouter métiers non calculés, plan vide et plan avec seulement un atelier. Changer séparément `TAILLE_FOYER` et `SURFACE_M2_PAR_FOYER_LOGE` avant publication sur des données où chacun change la référence. Contre-épreuves : inverser l'affectation entre deux maisons en gardant le total, loger dans le chantier, compter les foyers complets seulement, ou remplacer `-1` par zéro doit faire échouer le même contrôle.

SC3 — **La réponse reste celle du tick publié.** Commande : `python3 -m pytest jeu/sim/tests/test_monde.py -q -k service_occupation_publication`.
Publier un état avec des maisons et des artisans, puis changer le plan et les métiers du monde sans republier, avant la première lecture de `/occupation` : la réponse correspond toujours à l'ancien état. Republier : au moins une occupation change et tick/date concordent avec `/plan` et `/lieu`. Deux courses identiques donnent les mêmes octets canoniques. Un compteur sur le calcul de base montre un seul calcul malgré des lectures alternées de `/plan` et `/occupation` et plusieurs publications ; aucune base n'est calculée par la publication seule. Contre-épreuves : une réponse avec ancien tick ou affectation du nouvel état échoue au vérificateur de l'ancien ; une lecture du monde mutable échoue dès la première comparaison.

SC4 — **Absence déclarée et lecture sans effet.** Commande : `python3 -m pytest jeu/sim/tests/test_monde.py -q -k service_occupation_refus`.
Tester les refus HTTP du contrat, dont une base d'amorçage retirée avant sa première consultation. Comparer monde sérialisé, aléa, intentions en attente et octets des routes existantes avant/après lectures et refus. Un cas valide habité rend 200 ; un cas valide vide rend ses données mesurées. Contre-épreuves : un faux succès à base vide échoue au contrôle d'erreur ; un refus systématique échoue sur les deux cas valides ; une mutation de population fait échouer la comparaison du monde.

SC5 — **Les preuves déjà payées restent intactes.** Commandes : `python3 -m pytest jeu/sim/tests/test_monde.py jeu/sim/tests/test_foyers.py jeu/sim/tests/test_ville1400.py -q -k 'logement or reponse_figee or service_ia_sans or plan_service or sc7_rien or service_bourg'`, puis `python3 -m pytest jeu -q`.
Ajouter un cas `test_service_occupation_compatibilite` comparant les octets de `/monde`, `/lieu`, `/lieu?cell=X&bourg=1` et `/plan` avant/après consultation de la nouvelle route, sur un état habité avec logement. Le lancer par `python3 -m pytest jeu/sim/tests/test_monde.py -q -k service_occupation_compatibilite`. Contre-épreuve : le même comparateur rejette une copie d'ancienne réponse enrichie d'un champ d'occupation ou dont le logement inclut les foyers de la base. Garder les sondes existantes ; aucun fichier figé, seuil ou test existant n'est modifié.

## Hors périmètre
Rendu, animation, fumées, lumières et lecture Unity : suite PC de #420. Aucun changement du logement existant, de l'amorçage, des métiers, de la faim ou du tick. Pas de familles individuelles, parenté, propriété, loyer, déplacement, mortalité par maison ou attribution persistante ; aucune réinstallation dans les maisons de 1400. Aucun changement des formes ou des identifiants du plan, des intentions, de la photographie, des schémas ou des réponses ordinaires. Aucun test existant assoupli ni réécrit.
