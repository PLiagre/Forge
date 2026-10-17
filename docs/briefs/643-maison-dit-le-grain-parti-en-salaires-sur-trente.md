# Lot #643 — /maison dit le grain parti en salaires sur trente jours
Jalon : J4 · Machine : vps · Taille prévue : 280 lignes

## But
Le joueur lit, à côté du grain prélevé et reçu par sa maison, le grain réellement parti en salaires de chantier pendant les trente derniers jours.

## Le joueur
Il compare ce qu'il prend à ses gens et ce que ses chantiers lui coûtent. Il voit quelle part du grain arrivé à son grenier repart vers les ouvriers avant de poursuivre ses constructions : ce lot sert l'arbitrage de J4 entre champs et chantiers et prépare le panneau de la capitale #419, qui le rendra visible en 3D.

Dépend de : #642, livré sur la base `173efb6`, après le paiement #641 (`dcc425a`). Les maîtres des bourgs, les greniers, le paiement effectif, la mémoire des flux et `/maison` existent déjà ; aucune livraison encore attendue de J3 n'est nécessaire. Ce lot vient de la découpe de #413.

## Règle du monde
Sans objet pour les règles : c'est une observation des paiements de niveau 2 déjà décrits dans `jeu/sim/MODELE.md`, « Le chantier et ses bras » et « Le grenier d'une maison ». Étendre les contrats de « Les flux sur trente jours » et « Les maisons servies, vue dérivée », sans changer le salaire ni son trajet.

- Ajouter à `JourDeFlux` une mémoire des salaires par identifiant de maison, vide par défaut et indépendante des indices des routes. Au débit effectif dans `avancer_chantiers`, y accumuler une seule fois le même `montant` pour le maître actuel du bourg. Plusieurs cellules payées par une maison s'additionnent ; un changement de maître ne réattribue jamais ses anciens paiements. Aucun paiement ne dépend de l'existence de cette mémoire, du registre des maisons ou d'une route de prélèvement.
- Observer le montant déjà calculé au paiement, sans relire le tarif à la publication. Ne pas le déduire de la baisse quotidienne du grenier, du travail cumulé, des ouvriers survivants ou de la somme du relevé par chantier : pertes, prélèvements, autres retraits et ordre des additions peuvent différer. Le dernier jour incomplet compte son paiement réel ; un chantier arrêté ne crée aucun paiement. Le versement au bourg et le débit du grenier sont le même salaire, compté une seule fois.
- Utiliser `jour_courant` et `_jours_de_fenetre`, avec `FENETRE_FLUX_TICKS` relue comme aujourd'hui. Le salaire payé au tick 0 compte après trente ticks écoulés et sort après trente et un, même sans nouveau salaire. La mémoire reste dans `World.flux`, hors sauvegarde et `to_dict`, sans nouvelle étape du tick ni état de module ; aucune règle ne la lit.
- Dans `MatiereMaisons`, copier les cumuls de salaires dans la même passe sur les jours que les autres flux, dans leur ordre existant, sans parcours des jours pour chaque maison. `document_de_maison` ajoute `flux_30j.salaires_payes_kg`, sans arrondi, uniquement lorsque cette maison a payé dans la fenêtre. Son absence signifie aucun salaire enregistré dans cette fenêtre depuis l'ouverture ; elle ne prétend pas mesurer des jours antérieurs au démarrage. Après expiration du dernier paiement, le champ disparaît. Documenter ce contrat conditionnel dans le README.
- Conserver les cinq champs et le résultat par défaut de `flux_de_maison`, ainsi que les fiches sans salaire, exactement comme sur la base. Ajouter des cas dédiés au nouveau champ ; ne pas modifier `CHAMPS_KG`, les vérificateurs ou les assertions des tests existants. Cette extension conditionnelle conserve notamment le contrôle des cinq zéros sans route et les égalités exactes des fiches sans chantier.
- Le service utilise la matière copiée de `EtatPublie`, y compris avant la première lecture d'une fiche : aucune lecture du monde vivant au GET. La photographie qui réutilise `document_de_maison` reçoit naturellement le même champ pour le joueur et son suzerain ; ne pas créer une seconde représentation. Tick, date, cache et verrou des maisons gardent leur contrat actuel.

## Périmètre
jeu/sim/flux.py
jeu/sim/chantiers.py
jeu/sim/maisons_servies.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_flux.py
jeu/sim/tests/test_maisons_servies.py

## Conditions de succès
Commandes depuis la racine. Ajouter les cas aux fichiers qui portent les invariants, sans modifier les tests existants. Faire rougir les nouveaux cas sur la base avant de coder. Budget total, brief compris : environ 280 lignes, strictement moins de 300 ; réutiliser les aides d'épreuve existantes.

SC1 — **Les kilos du bon payeur.** `python3 -m pytest jeu/sim/tests/test_flux.py -q -k salaires_comptes`. Réutiliser `_epreuve_salaire` : route, parcelle et bâtiment prêt travaillent, dont un dernier jour incomplet ; mesurer le débit autour de Chantiers et le recouper avec les différences de travail et le versement au bourg. Couvrir deux cellules partageant un payeur, un autre payeur, puis un changement de maître entre deux jours : chaque débit reste attribué à celui qui l'a payé. Inclure un payeur sans route de prélèvement, sans bloquer son paiement. Avec un tarif non entier, conserver le montant calculé au débit, pas une soustraction de flottants imposée exacte. Contre-épreuves : déplacer un salaire vers l'autre maison, le compter deux fois ou remplacer le montant par le travail cumulé fait échouer le même vérificateur ; une épreuve sans paiement positif échoue.

SC2 — **Trente jours, au tarif du paiement.** `python3 -m pytest jeu/sim/tests/test_flux.py -q -k salaires_fenetre`. Payer au tick 0 puis à un autre tarif un jour suivant ; faire avancer le compteur jusqu'aux limites de la fenêtre et contrôler chaque contribution d'après les débits relevés ces jours-là. Vérifier les lectures après trente et trente et un ticks, puis l'expiration de tous les paiements ; couvrir un jour sans grain et un chantier achevé suivi de jours sans chantier. Changer le tarif après paiement ne change pas le passé. Contre-épreuves : réintroduire le salaire expiré, conserver seulement le dernier jour ou recalculer les anciens kilos au nouveau tarif doit faire échouer le contrôle.

SC3 — **Fiche servie et publication figée.** `python3 -m pytest jeu/sim/tests/test_maisons_servies.py -q -k maison_salaires`. Par le vrai service HTTP, financer un chantier et mesurer ses paiements pendant Chantiers, en isolant son débit des pertes et recettes des autres étapes. Vérifier `/maison?id=X` : champ conditionnel dans `flux_30j`, kilos exacts observés, prélevé et reçu inchangés, bonne maison, tick et date. Couvrir l'ouverture sans paiement, plusieurs ticks demandés ensemble, un arrêt qui conserve les paiements encore dans la fenêtre et la disparition après expiration. Après publication et avant la première lecture, modifier la mémoire vivante et le tarif : la fiche publiée reste identique, même avec `verrou_tick` pris ; l'ancien `EtatPublie` reste inchangé après une nouvelle publication. Vérifier aussi que `document_de_maison` donne les mêmes salaires pour la photographie. Contre-épreuves : supprimer ou altérer le salaire, substituer celui d'une autre maison ou fournir au vérificateur une fiche tirée du monde mutable doit échouer.

SC4 — **Une mesure ne commande rien.** `python3 -m pytest jeu/sim/tests/test_flux.py -q -k salaires_neutralite`. Jouer deux mondes financés identiques avec les mêmes générateurs ; effacer ou falsifier la mémoire des salaires de l'un entre les ticks. Retours du moteur, `to_dict`, stocks maritimes et états d'aléa restent égaux ; publier la matière ne modifie ni le monde ni l'aléa. Vérifier explicitement que les salaires observés ne sont pas sauvegardés. Contre-épreuve : modifier le grain réel ou une journée de travail dans une copie fait échouer cette comparaison ; elle ne doit pas ignorer les stocks ni le plan.

SC5 — **Contrats existants conservés.** `python3 -m pytest jeu -q`. Conserver notamment `test_ouverture_secours_refus_et_maisons_absentes`, `test_toutes_les_fiches_exactes_et_contre_epreuves`, `test_publication_figee_et_cache_a_la_demande`, les épreuves de photographie, les comptes de salaire #641 et le relevé #642. Contre-épreuve : leurs altérations existantes de flux, de payeur, de paiement et de publication restent rejetées ; aucune assertion remplacée, exclusion du salaire réel ou référence modifiée pour faire passer le lot. Les nouveaux cas exigent une valeur positive puis son expiration, et échouent donc si l'observation des salaires est neutralisée.

## Hors périmètre
Le panneau #419, Unity, Blender et les captures PC ; les autres vues et leurs légendes ; un salaire par lieu ou par chantier sur trente jours ; la monnaie, les matériaux, un financement initial ou une nouvelle règle de paiement. Aucun changement des intentions, des droits, des maîtres, des routes, des prélèvements, des pertes, de la récolte, de l'ordre du tick ou du contrat de `/plan`. Ne pas étendre systématiquement à six champs les anciens flux ni modifier un test existant. Tout chemin absent du périmètre est interdit, notamment `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md` et `CAP.md`.
