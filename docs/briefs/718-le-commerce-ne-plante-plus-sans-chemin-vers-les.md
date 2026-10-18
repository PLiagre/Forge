# Lot #718 — Le commerce ne plante plus sans chemin vers les champs
Jalon : J4 · Machine : vps · Taille prévue : 60 lignes

## But
Un bourg qui envoie un peu plus que son surplus, dans une cellule dont aucun chemin vers les champs n'est ouvert ce tick, expédie depuis son seul panier au lieu d'arrêter le monde.

## Le joueur
Une partie longue ne s'arrête plus d'un coup sur un plantage du commerce :
le joueur qui laisse passer les saisons dans sa capitale voit le monde
continuer, au Caire (cellule 8992) comme ailleurs. Lot de fond : il prépare
la décision de J4 « des bras au chantier, c'est moins de bras aux champs —
et à la moisson, de la récolte perdue ». Le reste de #705 (les champs de
chaque lieu demandent leurs bras, morceau de #415) a fait tomber le monde au
tick 242 sur ce défaut ; avec ce lot, son année de calibrage pourra franchir
ce tick, et #419 puis #508 rendront ce coût visible. Le commerce par lieux,
le passage par le bourg et les chemins intérieurs sont sur la base : ce lot
n'attend rien de J3.

## Règle du monde
Découle de « Le commerce entre cellules », sous-section « Passage par le
bourg », de `jeu/sim/MODELE.md` (niveau 2, plausible, jamais sourcé). Aucune
constante ne change.

Défaut mesuré sur la base : `_apply_commerce` n'ouvre `chemins[cid]` que si le
surplus local du bourg ne couvre pas l'offre de la cellule. Le partage
proportionnel entre receveurs peut ensuite rendre un envoi qui dépasse ce
surplus local d'un résidu d'arrondi ; `_sortir_par_bourg` cherche alors un
apport des champs et lit `chemins[cell.cell_id]`, absent : `KeyError`. Reproduit
sur master avec `_cellule_bourg(8992, [10, 20, 30], [100., 200., 300.])`, ration
1, envoi `math.nextafter(90., math.inf)` et `chemins = {}` : `KeyError: 8992`.

Règle : un chemin non ouvert ce tick vaut un chemin de capacité nulle. Aucun
champ n'apporte ; l'envoi effectif est débité du panier du bourg, puis
`_lieux.corriger_residu_au_bourg` s'applique comme aujourd'hui. Ne créer ni
entrée dans `chemins`, ni capacité, ni grain ; ne pas écrêter l'envoi (le
total cellulaire est déjà débité par l'appelant, la somme des paniers doit
rester égale au stock de la cellule). Quand le chemin est ouvert, rien ne
change : même ordre des rangs, mêmes plafonds, mêmes octets.

Dans `MODELE.md`, après « Capacité nulle : seul le surplus du bourg peut
sortir », ajouter une phrase : un chemin que le commerce n'a pas ouvert ce
tick compte comme une capacité nulle, et le résidu d'arrondi d'un envoi est
pris au bourg.

## Périmètre
jeu/sim/engine.py
jeu/sim/MODELE.md
jeu/sim/tests/test_commerce.py

## Conditions de succès
Commandes depuis `jeu/`. Prouver d'abord le rouge du nouveau test sur la base.
`_alterer_fonction` n'existe pas sur la base (elle était dans la branche de
#705) : écrire dans `test_commerce.py` une aide équivalente, qui relit la
source par `inspect.getsource`, vérifie que le texte remplacé y figure, la
recompile dans l'espace du module et la pose par `monkeypatch`.

SC1 — `python3 -m pytest sim/tests/test_commerce.py -k sortir_par_bourg_sans_chemin -q`.
Ajouter `test_sortir_par_bourg_sans_chemin`, paramétré par `chemins = {}` et
par des chemins ouverts pour une autre cellule seulement (`{8993: {1: 123.}}`).
Montage à plusieurs lieux avec `_cellule_bourg(8992, [10, 20, 30], [100., 200., 300.])`,
ration 1, envoi `math.nextafter(90., math.inf)` (affirmer qu'il dépasse le
surplus du bourg, 90), total cellulaire déjà débité de l'envoi comme chez
l'appelant. Après `engine._sortir_par_bourg` : aucune exception ; champs à
`[200., 300.]` exactement ; bourg à `cell.food_stock_kg − 500.` ; somme des
paniers égale au stock de la cellule ; `chemins` identique à sa copie
profonde d'avant l'appel.
Contre-épreuves, sur le moteur en mémoire, chacune faisant échouer le même
contrôle : remettre la lecture non gardée d'origine lève `KeyError` (attendu
par `pytest.raises(KeyError)`) ; un correctif qui ouvre un chemin à capacité
infinie pour la cellule fait apporter les champs et rougit les paniers ou
`chemins`.

SC2 — `python3 -m pytest sim/tests/test_commerce.py -q` : les 228 tests
existants passent, sans retrait ni assouplissement, en plus des nouveaux.
Contre-épreuve : celles de SC1.

SC3 — Depuis la racine, `python3 -m pytest jeu -q` : tous les invariants
passent, notamment conservation, déterminisme, empreintes et
`test_bras_suffisent_un_an` (365 ticks, avec et sans numéro). Aucune
empreinte ni tolérance actualisée : le correctif ne touche que le cas qui
plantait, les mondes qui tournaient gardent leurs octets.

## Hors périmètre
Le reste de #705 : récolte lieu par lieu selon les bras et la saison,
recalibrage de `BRAS_AUX_CHAMPS_PAR_KM2`, réécriture de tests de
`test_foyers.py` et `test_chantiers.py`. Aucun changement de l'ouverture des
chemins, du partage proportionnel entre receveurs, des plafonds d'arête ou de
quai, du commerce maritime, de la dette ou de la faim. Pas de partie longue
rejouée jusqu'au tick 242 dans les tests : sur la base, l'année tourne sans
ce défaut ; le montage de SC1 en est la preuve. Ni service, ni vue, ni Unity.
