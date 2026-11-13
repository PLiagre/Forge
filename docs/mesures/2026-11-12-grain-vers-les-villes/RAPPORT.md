# Lot #1071 — Le grain monte vers les grandes villes : rapport de mesure

Mesures du 13 novembre 2026, graine 0, sous Linux (VPS), sur le code du lot.
Règle de niveau 2 (plausible, jamais sourcée) : `appel_ville_affamee_part = 1,0`
(P) et `rayon_ville_affamee_jours = 6` (R) dans `jeu/data/commerce.toml`.

## SC3 — la preuve d'un an, quatre réglages

Commande, jouée une fois par réglage (depuis la racine du dépôt) :

```
python3 docs/mesures/2026-11-12-grain-vers-les-villes/scripts/mesure_un_an.py avant
python3 docs/mesures/2026-11-12-grain-vers-les-villes/scripts/mesure_un_an.py rayon
python3 docs/mesures/2026-11-12-grain-vers-les-villes/scripts/mesure_un_an.py appel
python3 docs/mesures/2026-11-12-grain-vers-les-villes/scripts/mesure_un_an.py depot
```

Sortie recopiée telle quelle (habitants et grain au 365e jour ; morts de
faim de `engine._apply_mortality` ; pertes nettes au pas des départs ; grain
reçu par le commerce, en tonnes).

```
== avant : P = 0, R = 1, 365 jours ==
ville           départ  habitants  grain (t)     morts    pertes   reçu (t)
Paris           275000     153052        956         0    138625          0
Milan           177000     185767       4557         0      4560          0
Gand            181000      33669          0     73317     69225        116
Alexandrie       35000      22305          0     11455         0       7757
Le Caire        360000     389614       3125         0         0          0
pire cellule de test_soudure.py : Gand (cellule 10391), 0.4051 de ses habitants morts de faim (73317 sur 181000) ; seuil 0,5

== rayon : P = 0, R = 6, 365 jours ==
ville           départ  habitants  grain (t)     morts    pertes   reçu (t)
Paris           275000     153052        956         0    138625          0
Milan           177000     185767       4557         0      4560          0
Gand            181000      33674          0     73317     69220        116
Alexandrie       35000      22454          0     11140         0       7757
Le Caire        360000     389779       3116         0         0          0
pire cellule de test_soudure.py : Gand (cellule 10391), 0.4051 de ses habitants morts de faim (73317 sur 181000) ; seuil 0,5

== appel : P = 1, R = 1, 365 jours ==
ville           départ  habitants  grain (t)     morts    pertes   reçu (t)
Paris           275000     188377       5199     44022     47410      24810
Milan           177000     191211      37745         0         0      37820
Gand            181000      97249       3355     28503     52630       7741
Alexandrie       35000      41976       1252        22         0       7441
Le Caire        360000     388336      23186         0         0        408
pire cellule de test_soudure.py : Paris (cellule 10322), 0.1601 de ses habitants morts de faim (44022 sur 275000) ; seuil 0,5

== depot : P = 1.0, R = 6, 365 jours ==
ville           départ  habitants  grain (t)     morts    pertes   reçu (t)
Paris           275000     284985       8081         0     16680      50130
Milan           177000     196333      50292         0         0      52937
Gand            181000      89260       1665     63926     16815      11507
Alexandrie       35000      42231       1252        22         0       7470
Le Caire        360000     388042      23196         0         0        408
pire cellule de test_soudure.py : Gand (cellule 10391), 0.3532 de ses habitants morts de faim (63926 sur 181000) ; seuil 0,5
```

Ce que la table dit :

- **Le commerce d'avant** (`avant`) redonne les chiffres de master et ceux des
  mesures jetables du chef : Paris 153 052 habitants et 956 t, Gand à 0 t,
  Alexandrie à 22 305. Paris ne reçoit rien de l'année (0 t reçues) : c'est
  l'appel qui le nourrit.
- **Le rayon seul** (`rayon`) ne nourrit personne : Paris et Milan finissent
  comme avant, à l'habitant et au kilo. Gand, Alexandrie et Le Caire bougent à
  peine (Gand +5 habitants, Alexandrie +149, Le Caire +165 et −9 t) : leurs
  arêtes sont plus larges, mais ils n'appellent rien de plus que leur ration.
- **L'appel seul** (`appel`) nourrit, mais moins que les deux ensemble pour
  Paris (188 377 contre 284 985 habitants) et Milan.
- **Les données du dépôt** (`depot`) sont celles de `test_grain_monte_vers_les_villes_un_an` :
  Paris, Milan, Gand et Alexandrie ont plus d'habitants et plus de grain que
  sous `avant`, et Le Caire plus de grain. Le Caire n'a ni mort ni perte au
  départ sous aucun des quatre réglages : il est jugé sur son grain.
- **Une observation, non cherchée** : Gand compte moins de morts de faim sous
  `appel` (28 503) que sous `depot` (63 926), et finit à 97 249 habitants contre
  89 260. Il reste très au-dessus de `avant` (33 669) et sous le seuil de
  `test_soudure.py`. Le brief ne demande pas de monotonie entre les réglages ;
  je le note sans en tirer de règle.
- **La pire cellule de `test_soudure.py`** (part des habitants morts de faim,
  seuil 0,5) : Gand à 0,4051 avant le lot, 0,3532 avec les données du dépôt.
  Le chiffre « 40,5 % » de `MODELE.md` (réserve de #1057) est bien celui du
  commerce d'avant l'appel.

`R = 6` tient donc la preuve et `test_soudure.py` : `R` n'a pas été réglé.

## SC5 — les valeurs neutres redonnent master, les vraies valeurs font rouge

Les tests de master sont les fichiers `jeu/sim/tests/test_determinisme.py` et
`test_commerce.py` de `origin/master`, copiés pour la mesure sous un autre nom
puis supprimés (rien n'en reste dans le dépôt). Commandes depuis `jeu/`.

**Pas 1 — `appel_ville_affamee_part = 0` et `rayon_ville_affamee_jours = 1`
dans `commerce.toml` (retirés ensuite, les vraies valeurs sont remises) :**

| commande | résultat |
|---|---|
| `pytest sim/tests/<test_determinisme de master> -k "test_part_bit_pres or test_prelevement_bit_pres or test_du_au_suzerain_bit_pres"` | 3 réussis |
| `pytest sim/tests/<test_commerce de master> -k "ville_affamee and not appel"` (fixture `_epreuve_1057` de master, sans coupure) | 18 réussis |

Même chose, rejouée par la première passe du codeur sur ce lot, avec les
tests de master pour tous les autres candidats de SC6 (valeurs neutres) :
`test_determinisme.py -k bit_pres` 10 réussis ; `test_monde.py -k "service_ia_sans or service_reponse_figee or service_ia_raison or flux_des_lieux_publication"`
11 réussis ; `test_ville1400.py -k "ilots_sc3 or sc9 or pont_plan_biskra"` 3 ;
`test_ville_dense.py -k sc5` 1 ; `forge/tests/test_forge.py -k "forge_ia_sans or forge_ia_sorties"` 3 ;
`vues/relief/tests/test_carte1400.py -k capitales_ia_sans` 1 ;
`test_modificateurs.py -k photographie_a_365_jours_est_celle_d_avant` 1 ;
`test_commerce.py -k "ville_affamee and not appel"` 18. Tous verts : avec
P = 0 et R = 1, le monde est celui de master, octet pour octet. (Le
`R = 1` n'atteint même pas l'index des arêtes : le moteur rend la main avant.)

**Pas 2 — les vraies valeurs (P = 1,0 ; R = 6), tests de master :**

| commande | résultat |
|---|---|
| `test_determinisme` de master `-k "test_part_bit_pres or test_prelevement_bit_pres or test_du_au_suzerain_bit_pres"` | **3 rouges** : `test_part_bit_pres`, `test_prelevement_bit_pres`, `test_du_au_suzerain_bit_pres` |
| `test_commerce` de master `-k "ville_affamee and not appel"` | **1 rouge**, 17 verts : `test_premier_mois_ville_affamee_janvier_inchange_puis_exportent_moins` |

Dans la première passe du codeur sur ce lot (valeurs du dépôt, tests de master,
logs gardés hors du dépôt), `test_monde` (9), `test_ville1400` (4), `test_ville_dense` (7),
`test_forge` (2), `test_carte1400` (1) et `test_modificateurs` (1) restent verts :
leurs empreintes ne bougent pas, elles ne sont donc pas recapturées.

La liste des rouges est celle des empreintes recapturées de SC6, plus l'épreuve
de janvier de #1057. Une règle qui ne ferait rien ne rougirait rien : la
contre-épreuve du pas 1 tient.

**`_epreuve_1057` isolée.** Le test rouge ci-dessus est joué avec la fixture de
master, c'est-à-dire sans `couper_l_appel_des_villes` pour la copie « réserve » :
l'appel change janvier (les villes affamées reçoivent dès le premier jour), et
l'épreuve de la réserve seule rougit. Dans la branche, la fixture porte la
coupure et ce test est vert ; retirer la coupure redonne exactement la
configuration du test de master ci-dessus, qui rougit.

## SC6 — après un tick, qui diffère ?

Plus courte des empreintes rouges : `_PART_BASE[(0, 1)]` (graine 0, un tick).
Comparaison cellule par cellule du stock de nourriture après un tick sous
P = 0 / R = 1 et sous les données du dépôt (script jetable, qui charge
`World.charger(0)`, joue `engine.tick(monde, random.Random(0), 0)` deux fois
sur deux copies et compare ; voisines et côtières lues sur `world.adjacency` et
`engine._aretes_maritimes_du_monde`) :

```
P = 1.0, R = 6
cellules : 596 ; affamées au départ : 8 ; voisines terrestres d'une affamée : 27 ; côtières : 447
cellules dont le stock de nourriture diffère après un tick : 32
  dont affamées : 8 ; voisines terrestres (non affamées) : 24 ; côtières seules : 0
  autres (ni affamée, ni voisine terrestre, ni côtière) : 0 []
affamées au départ qui ne diffèrent pas : 0
```

Les 8 cellules affamées (population au-dessus de `populations_soutenables`) :
Paris, Gand, Alexandrie, Le Caire, la cellule de Milan (qui porte aussi Crémone,
Brescia et Plaisance), Malaga, Pise et Gênes. Toutes diffèrent. Les 24 autres cellules qui diffèrent sont des
voisines terrestres d'une ville affamée (elles envoient leur surplus). Aucune
cellule ne diffère sans être affamée, voisine terrestre d'une affamée ou côtière,
et aucune cellule côtière seule (ni affamée, ni voisine terrestre) ne diffère au
premier jour.

Les empreintes recapturées dans `jeu/sim/tests/test_determinisme.py` sont celles
que cette comparaison annonce : `_PART_BASE` aux points 1 et 3 (le point 0, avant
tout tick, ne change pas), `_PRELEVEMENT_BASE` et `_DU_BASE` à tous leurs points
(le premier point mesuré y est déjà après un tick). Rien d'autre ne change dans
ce fichier : les valeurs `(0, 0)` et `(42, 0)` de `_PART_BASE` sont intactes. Les
empreintes d'un seul système (Linux) : le tableau n'en porte pas par système.

## Les tests joués sous `couper_l_appel_des_villes` (décision A)

Quatre tests rougissent parce que la faim qu'ils attendent disparaît sous
l'appel. Dans chacun, le seul changement est l'appel à
`couper_l_appel_des_villes(monkeypatch)` avec un commentaire daté : aucune
assertion, aucun chiffre ni aucun seuil ne bouge.

| test | cause |
|---|---|
| `test_famine.py` (fixture `monde_de_soixante_ticks` et deux tests) | la capitale affamée n'a plus faim en 60 ticks : aucune famine posée |
| `vues/chronique/tests/test_chronique.py::test_les_champs_mobiles_sont_mesures_et_pas_declares` | la faim ne mord plus en 30 ticks, les champs mobiles ne bougent plus |
| `test_survie.py::test_la_survie_repond_a_la_mortalite` | la faim ne tue presque plus en 200 ticks (écart de 4e-6) |
| `test_pays_et_jauges.py::test_jauges_sur_deux_ans_l_ia_et_le_joueur_jouent_le_meme_monde` | moins de lieux ont faim, la Concorde baisse moins : une seule maison joue la Plume en deux ans au lieu de deux |

Les deux premiers sont nommés par la décision A ; les deux autres ont la même
cause (« faim attendue sous l'appel »), qu'elle autorise.

## Le tick

`_elargir_aretes_des_villes_affamees` ne parcourt plus l'adjacence : les arêtes
de chaque cellule affamée viennent de `_aretes_par_cellule`, un index bâti une
fois par liste d'adjacence et gardé sur le monde (hors sauvegarde). La population
de chaque cellule est encore lue chaque tick (le relevé des champs est comparé à
elle) : c'est le seul parcours.
