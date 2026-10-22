# Lot #431 — Les familles de 1400
Jalon : J6 · Machine : vps · Taille prévue : 290 lignes

## But
Le monde commence avec des familles reliées aux chefs de 1400, pour préparer les mariages et la transmission des terres.

## Le joueur
Le joueur a une épouse, des enfants, des frères : son héritier existe dès le premier jour, et les maisons voisines ont des fils et des filles à marier. Ce lot de fond fournit les personnes et leurs liens ; #435 désignera l'héritier selon la loi, #438 permettra de proposer un mariage et #446 montrera l'arbre familial. La fratrie se déduit des parents communs ; aucun héritier n'est désigné arbitrairement ici. Une famille historiquement sans enfant ne reçoit pas un héritier inventé.

## Règle du monde
Dépend de #430, présent sur la base : catalogue, construction de `World.personnages`, liens `World.chefs` et copie profonde par `to_dict()`. Aucun apport futur de J4 ou J5 n'est nécessaire. Étendre « Les personnes » de `jeu/sim/MODELE.md` : les familles initiales quittent le niveau 3 ; leur évolution y reste.

Appliquer la décision A du pilote : enrichir `jeu/data/personnages-1400.json`, conserver sa table `chefs` et ses faits, ajouter les familles dans ce même catalogue. Les personnes supplémentaires rejoignent le tuple existant, trié par identifiant stable ; les liens emploient ces identifiants. Une personne déjà présente n'est pas recréée comme conjoint ou enfant. Les institutions ne deviennent pas des dynasties. Aucun nouvel emplacement : le siège demeure celui de la maison, sans seconde clé spatiale.

Niveau 1 : pour chaque grande maison et seigneurie de départ, rechercher dans des sources publiques l'épouse et les enfants vivants au 1er janvier 1400. Enregistrer les faits et leurs URL, y compris les liens familiaux et la présence à cette date ; conserver les précisions des dates. Une absence attestée, un veuvage ou un célibat ne sont pas des lacunes à remplir. Un parent décédé nécessaire à un lien peut être référencé comme tel, sans devenir un conjoint vivant. Ne pas inclure comme vivants les enfants morts avant le départ ou nés après lui.

Niveau 2 : compléter les familles non documentées et celles des maisons plausibles par une règle déterministe, identique pour le joueur et l'IA. Un chef de plus de 20 ans reçoit une épouse lorsque rien d'attesté ne l'interdit ; le nombre et les dates des enfants dépendent de l'âge maternel. Déclarer dans le catalogue les paramètres de génération et documenter leur règle dans MODELE.md. Les hypothèses de naissance nécessaires à cette génération sont explicitement plausibles, séparées des naissances historiques inconnues ou approximatives ; aucune lacune ni source historique n'est écrasée. Une identité de chef historiquement absente reste absente et motivée.

Chaque lien désigne une personne existante ; aucun lien vers soi, doublon d'identité ou cycle de filiation. Un enfant naît après ses deux parents ; sa mère a entre 15 et 45 ans inclus à sa naissance. Pour les dates imprécises, conserver et contrôler les bornes disponibles, déclarer ce qui demeure non calculable et ne jamais transformer « vers » ou « inconnu » en jour certain. Les naissances générées permettent un contrôle effectif de ces âges. Le tirage familial ne consomme pas le générateur du tick et ne dépend ni de l'ordre des tables ni de la graine de la partie.

## Périmètre
jeu/data/personnages-1400.json
jeu/sim/personnages.py
jeu/sim/tests/test_maisons.py
jeu/sim/MODELE.md
docs/briefs/431-les-familles-de-1400.md

## Conditions de succès
SC1 — Depuis la racine, `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k 'personnages or personnes'` passe. Adapter les trois contrôles concernés (`test_personnages_sources`, `test_personnes_catalogue`, `test_personnes_chefs`) à la décision A : comparaison complète des chefs ET des familles, schéma fermé enrichi, aucune simple inclusion des anciens chefs dans une liste désormais incontrôlée. Conserver tous leurs cas de refus, ainsi que les contrôles de couverture, de faits attestés et de sérialisation. Contre-épreuves : chef retiré, doublon, source effacée, lacune vidée, nom ou naissance altérés continuent tous d'échouer ; une famille retirée ou altérée échoue aussi. Écrire les nouveaux cas et constater leur rouge avant l'implémentation.

SC2 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k familles_liens` contrôle le catalogue chargé et les personnes construites, sur des familles non vides : identifiants uniques, références résolues, cohérence des conjoints et des parents, absence de cycles, chronologie et bornes maternelles. Contre-épreuves soumises au validateur réel : enfant né avant sa mère ou son père, mère de 14 ou 46 ans, parent inconnu, auto-parenté, cycle et conjoint incohérent sont refusés ; les limites 15 et 45 ans sont acceptées. Une date indéterminée ne compte pas comme un âge vérifié.

SC3 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k familles_historiques` vérifie une attente indépendante du constructeur, tirée des sources consultées : épouse et ensemble complet des enfants de Charles VI vivants au départ, avec leurs naissances, parents et sources. Vérifier aussi que chaque grande maison et seigneurie a un état familial explicite : attesté, plausible ou lacune motivée. Contre-épreuves : enlever un enfant attendu, ajouter comme vivant un enfant déjà mort ou encore à naître, changer sa mère ou supprimer la source du lien fait échouer la preuve ; une table familiale vide échoue.

SC4 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k familles_plausibles` exerce des chefs et des mères d'âges différents, les seuils et toutes les maisons plausibles réellement chargées. Comparer entièrement les personnes et leurs liens entre deux chargements, graines 0 et 42 et ordres de tables inversés ; observer que les paramètres d'âge maternel gouvernent effectivement les naissances. Contre-épreuves : génération vide pour tous, épouse manquante pour un chef admissible, naissance hors bornes, hypothèse présentée comme sourcée ou résultat dépendant de l'ordre sont détectés. Une famille générée altérée est refusée par `valider_personnages`, pas seulement par une assertion du test.

SC5 — `python3 -m pytest jeu/sim/tests/test_maisons.py jeu/sim/tests/test_determinisme.py -q` conserve les preuves de copie profonde et de neutralité du tick, familles comprises. Étendre les mutations de `test_personnes_serialisation` aux liens et fiches familiales : altérer une copie sérialisée ne change pas le monde ; altérer une famille dans le monde se retrouve dans sa sérialisation. Contre-épreuves : lien familial partagé avec la copie, famille reconstruite à la lecture ou famille ignorée par la sérialisation sont détectés. `test_personnes_neutres` conserve ses gardes interdisant au tick de lire ou reconstruire les personnes et son égalité des habitants, de l'économie et de l'état aléatoire avec le témoin sans personnes.

## Hors périmètre
Vieillissement, naissances pendant la partie, mortalité, choix légal de l'héritier, partage, mariage proposé, dot, alliance, éducation, traits, ambitions, service et interface Unity. Ni généalogie exhaustive avant 1400, ni personnes futures imposées par l'histoire, ni modification des habitants pour financer les personnages. Aucun nouveau champ de premier niveau du monde, aucun changement de règle économique, aucun assouplissement des contre-épreuves existantes. Si le diff complet ne tient pas sous 300 lignes, demander une découpe ; ne pas retirer des maisons ou des contrôles pour le faire tenir.

## Demande technique de découpe — codeur, 22 octobre 2026

La décision A est applicable, mais ne résout pas la taille du lot. Le catalogue
contient 30 grandes maisons et 6 seigneuries, dont 3 identités absentes à
conserver, ainsi que 10 institutions. Le module actuel compte 98 lignes et les
preuves existantes des personnes 266 lignes. Ce sont des mesures de la base,
pas la taille d'une implémentation achevée.

Estimation du changement lisible : 120–160 lignes pour le schéma, les dates et
les liens ; 140–200 pour les familles et leurs sources ; 100–140 pour les
nouvelles preuves ; 30–50 pour la génération, les adaptations et la notice.
Soit 390–550 lignes ajoutées ou modifiées, hors suppressions. Cette estimation
dépasse le plafond ; aucune maison ni contre-épreuve ne doit être sacrifiée.

Découpe recommandée, à reprendre par le chef en conservant toutes les exigences :

1. Validateur des liens et des bornes chronologiques, exercé sur des familles
   d'épreuve non vides ; refus et limites de SC2, rouge avant implémentation.
2. Catalogue familial sourcé des 36 maisons et seigneuries, schéma fermé et
   couverture complète ; décision A et attentes historiques de SC3. SC1 reste
   à valider après la construction dans le monde, à l'étape 3.
3. Construction des familles attestées dans le monde, comparaison complète,
   réutilisation des personnes existantes et copie profonde ; SC1 et SC5.
4. Génération plausible paramétrée et déterministe, hypothèses séparées des
   faits historiques ; SC4 et toutes les preuves d'intégration SC1 à SC5.

Chaque étape dépend de la précédente ; son brief doit maintenir les tests
antérieurs au vert, sans annoncer une capacité encore non intégrée.

Premier témoin consulté pour SC3 : la section
[Marriage and issue de Charles VI](https://en.wikipedia.org/wiki/Charles_VI_of_France#Marriage_and_issue)
donne sept enfants vivants au départ : Isabelle (1389-11-09), Jeanne
(1391-01-24), Charles (1392-02-06), Marie (1393-08-22), Michelle
(1395-01-11), Louis (1397-01-22) et Jean (1398-08-31). Leur mère,
[Isabeau de Bavière](https://en.wikipedia.org/wiki/Isabeau_of_Bavaria), est née
vers 1370 : conserver cette approximation, sans inventer de jour ni prétendre
avoir vérifié un âge exact. Jeanne est aussi l'épouse du chef déjà présent
`personne-grande-28` ; elle doit avoir une seule identité dans le catalogue.
Le tableau permet les contre-épreuves de présence : Charles né en 1386 et
Jeanne née en 1388 sont morts avant 1400 ; Catherine née en 1401, Charles né
en 1403 et Philippe né en 1407 sont postérieurs au départ.

Le code, le catalogue et les tests restent inchangés en attente de cette
découpe ; cette note ne vaut pas réalisation des conditions SC1 à SC5.
