# Lot #771 — Les chefs réels des maisons de 1400, sourcés
Jalon : J6 · Machine : vps · Taille prévue : 280 lignes

## But
Le monde dispose des identités et des naissances attestées des chefs de 1400, avec leurs sources et leurs lacunes explicites, pour préparer les personnages de la dynastie.

## Le joueur
Ce lot de fond prépare le geste de J6 : incarner un personnage réel, le marier, éduquer ses enfants et jouer son héritier à sa mort. Le joueur pourra reconnaître son seigneur et les chefs voisins plutôt qu'une maison sans visage ; une naissance inconnue ne lui sera pas présentée comme un âge certain. Le chargement des personnes relève de la suite de #430 ; #445 les exposera au service et à la photographie, puis #446 rendra l'arbre visible dans Unity. Ce lot seul ne change aucun écran.

Dépend de : aucun lot non livré. Les trois tables historiques, `charger_registre_maisons` et ses preuves existent sur la base. Les gestes encore attendus de J4 et J5 ne sont pas nécessaires.

## Règle du monde
Découle de « Les maisons du monde », « Les maisons de 1400, vue dérivée » et « Les seigneuries de départ, vue dérivée » de `jeu/sim/MODELE.md`. Niveau 1 : identités, fonction au 1er janvier 1400 et naissances attestées par des sources publiques consultées. Aucune donnée plausible de niveau 2 n'entre dans cette table historique. Niveau 3 ici : personnes vivantes dans le moteur, familles, vieillissement et succession.

Créer `jeu/data/personnages-1400.json`, en UTF-8, avec `date = "1400-01-01"`, une déclaration de fidélité et une liste `chefs` triée par identifiant `maison`. Chaque ligne porte exactement une entrée du registre historique : `grande-…`, `institution-…` ou `seigneurie-…`. La base en donne 46 (30 grandes maisons, 10 institutions et 6 seigneuries) ; ces nombres sont un constat, jamais la référence codée des preuves. Inclure les sièges hors carte. Exclure les seigneurs plausibles ajoutés par l'attribution des lieux.

Une ligne porte `maison`, `nom`, `naissance`, `sources` et `lacunes`. `nom` est le nom complet attesté ou `null`. `naissance` est `null` ou un objet avec `valeur` et `precision` : `jour`, `mois`, `annee`, `vers` ou `intervalle`. Une date certaine suit ISO à sa précision réelle ; une approximation ou un intervalle conserve la formulation de la source. Ne jamais compléter une année par le 1er janvier, transformer « vers » en certitude, ni déduire une naissance d'un âge supposé.

`sources` contient `identite` et `naissance`, chacune `null` ou un objet `url` et `fait` : lien public précis et courte explication du fait attesté. La source d'identité doit établir la personne et sa fonction à la date de départ ; celle de naissance doit établir la valeur et sa précision. Une même page peut soutenir les deux, avec leurs faits séparés. `lacunes` porte les mêmes deux clés : un motif non blanc exactement quand la donnée correspondante manque. Une identité inconnue entraîne aussi une naissance inconnue ; une identité connue peut avoir une naissance inconnue. Les sources d'une absence peuvent être expliquées dans son motif, sans être présentées comme la preuve d'une personne.

Partir des liens déjà cités dans les trois tables et consulter les pages avant de renseigner leurs faits ; compléter par des sources publiques si nécessaire. Reprendre les chefs déjà attestés, sans remplacer la recherche par une série de valeurs nulles. Pour les maisons regroupant plusieurs branches, suivre la fonction et le siège représentés par le registre : Prague ne devient pas Buda, Heidelberg ne devient pas Munich. Si la source ne départage pas les titulaires au jour de départ, déclarer l'incertitude au lieu de choisir arbitrairement. Distinguer Manuel II à Constantinople de Théodore Ier à Mistra malgré le nom Paléologue commun.

Une institution garde son identifiant propre : renseigner son titulaire attesté quand il existe ; déclarer une direction collective ou un titulaire non établi sinon. Elle ne devient pas une dynastie héréditaire. Le chef du Zab reste déclaré non sourcé sur la base ; ne lui attribuer ni un prénom plausible ni un gouverneur attesté seulement à une autre date. Toute nouvelle identification exige une source qui couvre précisément le départ.

Ajouter dans « Les maisons du monde » de `MODELE.md` la provenance, le contrat des lacunes et la portée de cette table préparatoire ; les personnes restent non simulées. Aucun lecteur de production ni branchement dans `World`, le tick, les noms ou les vues. Inventaire des tests figés consultés : `test_registre_chargement`, `test_registre_world`, `test_noms_maisons`, `test_lecture_zab`, `test_photographie_1400_zab` et `test_service_ia_sans`. Aucun ne doit rougir : leurs effectifs, noms historiques avec prénom `null`, mentions du Zab et empreintes restent strictement ceux de la base. Ajouter les cas dans `test_maisons.py`, qui porte l'invariant du registre ; ne réécrire aucun test existant.

Budget indicatif, brief compris : 65 lignes de brief, 65 de données (une fiche lisible par ligne comme les tables existantes), 135 de preuves ajoutées et 15 de documentation. Rester sous 300 lignes de diff sans compacter artificiellement le code ni retirer de contre-épreuve.

## Périmètre
docs/briefs/771-les-chefs-reels-des-maisons-de-1400-sources.md
jeu/data/personnages-1400.json
jeu/sim/tests/test_maisons.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes les commandes partent de la racine. Les vérificateurs ajoutés acceptent un document en argument afin d'éprouver des copies altérées ; ils restent dans les tests. Prouver d'abord le rouge de SC1 avec les nouveaux cas et sans la table.

SC1 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k personnages_couverture` dérive indépendamment les identifiants attendus des capitales, des puissances sans maison et des seigneuries, puis les compare au résultat de `charger_registre_maisons` et aux lignes de `chefs`. Exiger des ensembles non vides, l'égalité exacte, l'unicité des lignes et leur ordre ; vérifier chaque catégorie, les deux Paléologue distincts et les entrées hors carte. Contre-épreuves : fichier absent, liste vide, retrait d'une ligne de chaque catégorie ou hors carte, doublon, remplacement par un identifiant inconnu ou plausible sont tous refusés. Ajouter une maison à la référence de test sans ajouter sa fiche doit échouer aussi : le contrôle ne recopie pas la liste à prouver.

SC2 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k personnages_sources` vérifie le schéma, la date de départ, les textes non blancs, les URL HTTP(S), les précisions autorisées et la validité calendaire des dates certaines, antérieures ou égales au départ. Les données présentes ont chacune leur source ; les données nulles ont chacune leur motif. Contre-épreuves sur des copies : date de départ changée, nom blanc, champ absent, source vide ou URL invalide, naissance sans source, précision inconnue, date impossible, naissance certaine après le départ et absence sans motif échouent séparément. Les approximations et intervalles sourcés sont conservés sans produire de date exacte.

SC3 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k personnages_attestes` compare des attentes historiques explicites, indépendantes de la nouvelle table, aux fiches : au moins les cinq départs déjà nommés dans les sources de `seigneuries-1400.json`, Constantinople et Mistra, un chef musulman de grande maison et un titulaire institutionnel vérifié. Fixer aussi deux naissances connues avec leurs précisions d'après les pages consultées, et contrôler les lacunes réelles de la table sur un échantillon non vide. Les faits et URL inscrits doivent permettre au relecteur de vérifier chaque attribution. Contre-épreuves : échanger Manuel et Théodore, décaler une naissance témoin, effacer toutes les identités ou toutes les naissances, enlever un motif de lacune, ou faire passer une approximation pour une date certaine font échouer les attentes correspondantes. Un lien présent ne vaut pas, à lui seul, preuve historique.

SC4 — `python3 -m pytest jeu/sim/tests/test_maisons.py jeu/sim/tests/test_seigneuries.py -q` puis `python3 -m pytest jeu/sim/tests/test_monde.py -q -k 'photographie_1400 or service_ia_sans'` conservent intégralement les invariants existants, notamment le registre, les prénoms historiques encore nuls dans les vues et les réponses figées du service. Contre-épreuves : leurs retraits de maisons, altérations de noms, suppressions du Zab et mutations d'octets restent détectés par les tests existants. Aucun compteur, témoin, seuil ou fichier de référence n'est modifié pour les faire passer.

SC5 — `python3 -m pytest jeu -q` et `git diff --check` réussissent. Contre-épreuves : tous les cas altérés de SC1 à SC4 restent exécutés et refusés dans cette suite ; une table vide ne peut donner un succès. Le diff reste limité aux quatre chemins autorisés et sous 300 lignes ; aucune modification de production ne peut être justifiée par ce lot de données.

## Hors périmètre
Chargement des personnages dans le monde et identité du personnage joué (suite de #430), familles (#431), mortalité, naissances simulées, traits, mariages, éducation, héritage et lois de succession. Génération de chefs plausibles, révision du registre ou des trois tables historiques, ajout de maisons, nouvelle clé spatiale, population, économie et intentions. Service et photographie (#445), arbre Unity (#446), captures et travaux PC. Toute écriture hors des chemins autorisés est interdite.
