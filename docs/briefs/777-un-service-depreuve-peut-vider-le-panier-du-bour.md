# Lot #777 — Un service d’épreuve peut vider le panier du bourg
Jalon : J4 · Machine : vps · Taille prévue : 230 lignes

## But
Un service jetable peut préparer un bourg réellement affamé et publier son panier vide, afin d'éprouver que les étals de la capitale suivent le monde.

## Le joueur
Le joueur verra les étals de sa capitale se vider quand ses habitants manquent de nourriture ; il pourra sentir ce que coûte une route négligée au profit d'autres chantiers. Ce lot de fond prépare l'arbitrage de J4 entre route vers les champs et autres constructions, et sa contre-épreuve « un étal plein dans un bourg affamé ». La suite PC de #420 rendra ce manque visible dans la ville. La demande fournie n'a pas de phrase « Le joueur » distincte : cette phrase en explicite le bénéfice selon `CAP.md`, « La règle d'un lot ».

## Règle du monde
Sans objet : outil d'épreuve, sans nouvelle règle du jeu. Il exerce les règles existantes de **niveau 2**, plausibles, de `jeu/sim/MODELE.md`, « Le panier de marchandises », « Ce que veut dire « affamée » », « Les lieux d'une cellule, vue dérivée » et « La distribution à l'intérieur de la cellule ». Un panier vide ne prouve pas une faim : seule une ration manquante la fait progresser. `cell_id` reste la seule clé spatiale ; le bourg est le lieu de rang 0.

**Dépend de : #776**, deuxième sous-lot de la découpe de #420 ; il livre l'occupation et modifie les mêmes fichiers. Conserver aussi l'extension `bourg=1` de #775.

Contrat à livrer :

- Ajouter au service l'option explicite `--epreuve`, désactivée par défaut, et un argument de construction équivalent, également faux par défaut. Elle ne charge ni ne sauvegarde une partie : le monde d'épreuve est chargé en mémoire puis jeté à l'arrêt. Documenter le lancement depuis `jeu/` : `python3 -m sim.service --epreuve --port 0 --jours-par-seconde 0 --seed 0`.
- Réserver `POST /epreuve/vider-panier?cell=X` à ce mode. Sans activation, répondre HTTP 404 avant toute autre action. Ce geste ne devient jamais un type d'intention et n'est proposé ni au joueur ni à l'IA.
- L'opération exige l'horloge à l'arrêt, une cellule connue, des lieux valides et un unique bourg habité. Refuser `cell` absent, vide, répété ou non entier par HTTP 400, une cellule inconnue par 404, une cellule sans bourg habité ou aux données alimentaires absentes/invalides par 400, une horloge active par 409. Valider avant toute mutation, sous le verrou du tick, sans changer la vitesse pour rendre la requête recevable.
- Préparer un manque certain : retirer la nourriture des paniers de tous les lieux de cette seule cellule et de son total cellulaire, par les accesseurs de `sim.model`. Le retrait des réserves des champs évite qu'ils nourrissent aussitôt le bourg ; il fait partie du montage déclaré. Conserver les autres marchandises et les greniers. L'origine du changement est ce retrait artificiel d'épreuve, jamais une perte ajoutée au jeu.
- Appeler la consommation existante `engine._apply_consumption(cellule, monde.carte)`, puis `engine._update_hunger` avec sa pénurie retournée. La consommation calcule elle-même dette et faim locales ; aucune affectation directe de ces valeurs, aucune formule de remplacement. Ce montage ne joue pas un tick complet : pas de production, commerce, démographie, IA ni avance du compteur ou de l'aléa. Le tick publié désigne l'état ainsi préparé, sans prétendre qu'un jour entier a été joué.
- Reconstruire puis remplacer `EtatPublie` sous les verrous existants. Répondre HTTP 200 avec `cell_id` et `tick` seulement après publication. Le lecteur vérifie ensuite `GET /lieu?cell=X&bourg=1`, et non un panier renvoyé spécialement par la commande. Les lecteurs voient une publication complète, jamais des données assemblées depuis le monde en cours de préparation.

Décrire ce montage, son retrait de nourriture et son absence d'avance du temps dans `MODELE.md`, près des lieux servis. Les tests existants sur les octets figés, les empreintes sans IA, l'égalité avec la photographie, l'occupation et les intentions ne doivent pas changer. Les contrôles d'accès aux paniers et des littéraux numériques restent applicables.

## Périmètre
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/tests/test_monde.py
docs/briefs/777-un-service-depreuve-peut-vider-le-panier-du-bour.md

## Conditions de succès
Commandes depuis la racine. Ajouter uniquement de nouveaux cas dans `test_monde.py`, sans modifier les tests, aides partagées, assertions ou références existants. Montrer leur rouge avant le code, puis leur vert. Exiger des échantillons habités non vides. Budget indicatif : 60 lignes de service, 100 de tests, 10 de documentation et 60 de brief ; diff total strictement inférieur à 300 lignes.

SC1 — **Le geste appartient au seul service jetable.** Commande : `python3 -m pytest jeu/sim/tests/test_monde.py -q -k service_epreuve_reserve`.
Lancer le vrai module en sous-processus avec l'option documentée et lire son port annoncé ; vérifier qu'une requête valide aboutit. Sur le service ordinaire, la même requête rend 404 et conserve monde, aléa, file d'intentions et réponses publiées. Vérifier aussi que `/intention` refuse un type `vider_panier`, même en mode d'épreuve. Contre-épreuves : supprimer l'activation du lancement fait échouer le cas positif ; exposer le geste par défaut ou comme intention fait échouer les cas de refus.

SC2 — **La simulation calcule le manque, HTTP publie son vrai panier.** Commande : `python3 -m pytest jeu/sim/tests/test_monde.py -q -k service_epreuve_panier`.
Sur Biskra, dérivée de `depart_biskra` dans les départs servis, puis une autre cellule habitée avec au moins un champ, relever avant le geste les populations, réserves et durées de faim ; placer aussi une marchandise non alimentaire fractionnaire. Sur une copie indépendante du monde initial, préparer le retrait déclaré et appliquer les deux fonctions existantes pour obtenir la référence. Après le POST, lire réellement `/lieu?cell=X&bourg=1` : comparer exactement son bloc au rang 0 de référence, sans arrondi, avec faim strictement positive, nourriture présente à zéro, population et tick inchangés. Comparer aussi tous les paniers locaux et leur somme au total ; les stocks non alimentaires, greniers, autres cellules, plans, intentions et aléa restent identiques. Contre-épreuves rejetées par le même vérificateur : ancien panier publié, faim forcée à zéro ou marchandise non alimentaire effacée. Neutraliser la consommation du service doit faire échouer la preuve de faim ; le monde de référence ne doit pas utiliser cette fonction neutralisée.

SC3 — **Les refus précèdent le retrait.** Commande : `python3 -m pytest jeu/sim/tests/test_monde.py -q -k service_epreuve_refus`.
Ajouter les refus du contrat, dont une nourriture absente, un bourg absent ou dupliqué et un bourg sans habitants. Comparer avant/après monde complet, aléa, intentions et octets publiés. Pour l'horloge active, employer un montage qui empêche tout tick autonome pendant la comparaison, sans changer les aides existantes. Contre-épreuves : le même montage valide à l'arrêt doit réussir ; un faux HTTP 200 sans retrait et un refus systématique échouent donc aussi. Une mutation avant refus est détectée par les comparaisons d'état.

SC4 — **Publication cohérente et preuves antérieures conservées.** Commandes : `python3 -m pytest jeu/sim/tests/test_monde.py -q -k 'service_epreuve or service_bourg or service_occupation or reponse_figee or service_ia_sans'`, puis `python3 -m pytest jeu -q`.
Dans un nouveau cas `test_service_epreuve_publication`, comparer les octets des routes existantes sur deux services identiques, ordinaire et d'épreuve, avant tout geste : ils sont identiques. Après le retrait, `/monde`, les deux variantes de `/lieu`, `/plan` et `/occupation` annoncent le même tick ; relire le bourg conserve exactement ses octets. Deux courses identiques donnent le même état préparé. Contre-épreuves : le comparateur rejette une ancienne réponse de `/lieu` conservant le panier plein ou une réponse au tick altéré. Les tests existants restent intacts et verts.

## Hors périmètre
Unity, animation des étals, fumées, lumières, captures et lanceur PC : suite de #420. Aucun bouton ni intention de triche, aucun changement de consommation, faim, récolte, transport, logement ou amorçage du jeu. Pas de famine naturelle scénarisée, de manipulation des constantes, de sauvegarde du montage, de nouvelle clé spatiale ni de modification des réponses figées. Aucun test existant assoupli ou réécrit.
