# Lot #385 — L'épreuve du jalon 4 rejoue le journal des gestes et compare le monde
Jalon : J4 · Machine : vps · Taille prévue : 290 lignes

## But
Une commande prouve que les gestes de construction déposés par le joueur en HTTP produisent exactement le monde rejoué depuis leur journal, en conservant les personnes rangées en foyers.

## Règle du monde
Sans objet : outil de preuve, aucune règle du monde ne change. Il éprouve les sections « Les intentions du joueur », « Le plan du bourg », « Le chantier et ses bras » et « Les foyers par métier » de `jeu/sim/MODELE.md` : dépôt accepté en attente, application au tick suivant, plan dans le monde et conservation exacte des personnes. Les tracés, le travail et le rangement en foyers restent de niveau 2, plausibles ; aucune donnée historique n'est ajoutée.

La base fournit déjà `ServeurMonde`, `recevoir_intention`, les trois gestes, `World.to_dict()` et les options `--gestes` et `--monde-json`. Le lot sert la preuve de J4 et ne dépend d'aucune livraison restante de J3.

## Périmètre
`pc/epreuve_jalon4.py`
`jeu/ville/tests/test_epreuve_jalon4.py`
`docs/briefs/385-l-epreuve-du-jalon-4-rejoue-le-journal-des-geste.md`

Tout autre chemin est interdit. Les fichiers de mesure sont temporaires, dans le dossier demandé par `--sortie`, jamais ajoutés au dépôt. Budget total, brief compris : environ 165 lignes de script, 75 de tests et 50 de brief ; moins de 300 lignes de diff.

## Conditions de succès
SC1 — Le service sourd fait rougir la comparaison, puis le service réel la fait passer. Depuis la racine, exécuter d'abord `python3 pc/epreuve_jalon4.py --sortie /tmp/forge-385-sourd --seed 0 --ticks 10 --cellule 1175 --service-sourd`, puis `python3 pc/epreuve_jalon4.py --sortie /tmp/forge-385-normal --seed 0 --ticks 10 --cellule 1175`. La première rend 1 avec un écart entre monde servi et monde rejoué ; la seconde rend 0. Les deux essais passent par le vrai service de `sim.service`, sur `127.0.0.1:8000`, vitesse 0, sans IA ; seuls les appels HTTP à `/tick?n=…` font avancer son monde.

L'enveloppe, écrite exclusivement dans le script, conserve les handlers existants et enveloppe leur appel à la vraie `recevoir_intention`. Sous le même `verrou_tick`, après acceptation, elle copie chaque intention JSON dans `journal.json`, liste ordonnée de `{tick, intention}` directement lisible par `--gestes`. `tick` est `world.ticks_ecoules` au dépôt, égal au reçu `appliquee_au_tick` ; il désigne le tick à jouer, sans ajouter 1. Un refus n'entre jamais au journal. Le mode sourd valide et journalise normalement, puis retire uniquement la pose du bâtiment de la file : route et parcelle restent appliquées pour que les trois dépôts soient acceptés et que la contre-épreuve atteigne la comparaison finale. Toute substitution en mémoire reste limitée à cet essai et est restaurée à la fin.

La recette HTTP fixe la route au tick 2 : `tracer_route`, `cell: 1175`, `points: [[0,0],[40,0]]`, `largeur_m: 4` ; la parcelle au tick 3 : `decouper_parcelle`, même cellule, `rue: 0`, `segment: 0`, `debut_m: 5`, `facade_m: 10`, `profondeur_m: 20`, `cote: gauche` ; la maison au tick 5 : `poser_batiment`, même cellule, `parcelle: 0`, `nature: maison`. Les foyers des trois chantiers gardent leur défaut existant. Le script dépose ces objets par `/intention`, contrôle les reçus, puis avance jusqu'à 10 ticks écoulés. Avant le tick suivant chaque dépôt, le plan doit rester inchangé ; après lui, le nouvel objet doit être présent, sauf dans la contre-épreuve sourde.

SC2 — Le monde entier, le journal et l'effet des gestes sont réellement comparés. `python3 -m pytest jeu/ville/tests/test_epreuve_jalon4.py -q` exerce le jugement du script et un essai HTTP complet de SC1. L'enveloppe ajoute seulement `GET /monde-complet` : sous `verrou_tick`, elle sérialise `World.to_dict()` du service, sans arrondi, en UTF-8, clés triées, `ensure_ascii=False`, séparateurs `(',', ':')`. Elle conserve ces octets dans `monde-service.json` ; `/monde` reste le contrat léger existant.

Depuis `jeu/`, le script lance avec le même interpréteur `python3 -m sim --ticks N --seed S --gestes <sortie>/journal.json --monde-json <sortie>/monde-rejoue.json`, puis la même commande sans `--gestes`, vers `monde-sans-gestes.json`. Les chemins transmis sont absolus. Il exige `monde-service.json == monde-rejoue.json` à l'octet et `monde-rejoue.json != monde-sans-gestes.json`. Il exige un journal non vide, avec les trois types acceptés, et des mondes non vides portant les mêmes cellules et plans, à N ticks écoulés. Le bilan dérive les compteurs et les différences des données ; pour cette recette à graine 0 et tick 10, seuls la cellule 1175 et son plan diffèrent du témoin. Les 596 cellules de la base sont toutes contrôlées, sans coder ce nombre comme référence.

Contre-épreuves de SC2 dans la même commande : journal vide ou privé d'un type ; monde vide ; un octet différent hors du plan (par exemple un stock d'une autre cellule) ; témoin sans geste remplacé par le monde rejoué. Chaque cas doit produire un échec nommé du jugement. Aucun test ne remplace le rejeu CLI par une référence fabriquée depuis le service.

SC3 — Les foyers font exactement les habitants, métier par métier et cellule par cellule. `python3 -m pytest jeu/ville/tests/test_epreuve_jalon4.py -q` contrôle les trois mondes de l'essai : `foyers` doit être un dictionnaire calculé, jamais `-1` ; chaque métier a un nom non blanc et un compte entier strictement positif ; `complets` et `dernier` sont entiers non négatifs, avec `dernier < TAILLE_FOYER`, relue depuis `sim.constants`. Pour chaque métier, `complets × TAILLE_FOYER + dernier == personnes` ; la somme des personnes et celle des foyers désagrégés égalent chacune la population de la cellule. Une cellule de population zéro porte `{}` ; une cellule habitée ne peut porter `{}`. Aucun foyer incomplet n'est arrondi ni perdu.

Contre-épreuves de SC3 dans cette commande : perdre une personne du dernier foyer, ajouter un métier à zéro ou au nom blanc, déclarer `foyers: -1`, vider les métiers d'une cellule habitée. Les copies altérées sont données aux contrôles de conservation sans dépendre d'un échec préalable de l'égalité des octets. Un cas positif de 103 personnes, en plus du cas de 100, exerce le dernier foyer incomplet.

SC4 — L'essai est autonome et les preuves existantes restent exigeantes. `python3 -m pytest jeu/ville/tests/test_epreuve_jalon4.py jeu/ville/tests/test_epreuve_jalon1.py jeu/sim/tests/test_intentions.py jeu/sim/tests/test_foyers.py -q`, puis `python3 -m pytest jeu -q`, passent sans modifier les tests existants. Les nouveaux cas vivent dans le fichier qui porte la nouvelle épreuve. Ils vérifient aussi qu'une intention HTTP refusée ne change ni le journal ni le monde et que le service est fermé après succès comme après échec.

Contre-épreuve de SC4 : garder le port 8000 occupé pendant le lancement de `python3 pc/epreuve_jalon4.py --sortie /tmp/forge-385-occupe` doit rendre 2, nommer le port et laisser son occupant intact. Un arrêt ou un rejeu CLI en échec ne peut jamais réutiliser des sorties anciennes comme preuve. Codes : 0 preuve valide, 1 invariant violé, 2 essai impossible ; messages en français, délais HTTP et sous-processus bornés, arrêt du seul service créé dans un `finally`. Les dépendances du script sont exclusivement la bibliothèque standard et `sim/` ; pytest est réservé aux tests.

## Hors périmètre
Unity, Blender, captures, panneau, redessin après relance et validation visuelle de la capitale : ce lot ne certifie que la partie simulation de l'épreuve J4. Ni choix de départ, ni maîtres ou prélèvements de J3, ni gestes IA. Aucun changement de `jeu/sim/`, de ses tests, de ses formats HTTP, de ses règles ou de ses constantes ; aucun second moteur. Aucun bâtiment nouveau ni exigence que les chantiers soient achevés au tick 10. Aucun test existant retiré, réécrit ou assoupli.
