# Rapport de la refonte — 7 novembre 2026

> Mesuré sur `origin/master` = `17557033` (Lot #952, 7 novembre 2026), dans le
> worktree `.atelier/direct/refonte-mesures`, sur le PC (i7-13700K, Windows,
> Python 3.13). Chaque chiffre donne sa commande ; les sorties brutes sont dans
> [`brut/`](brut/) et les scripts dans [`scripts/`](scripts/). La mesure du
> 6 novembre ([`../2026-11-06-refonte/`](../2026-11-06-refonte/JOURNAL.md)) est
> refaite et comparée.

## En bref

- **Le monde ne tient pas seul.** Graine 0, sans joueur, IA active : au bout
  d'un an, Paris et Milan sont vides (0 %), Le Caire à 3,5 %, Gand et Bruges à
  3,9 %, Florence à 4,8 % ; l'Europe est à 101,8 % parce que les campagnes
  grossissent. Les quatre régions denses de la table du jalon 2 tombent
  sous la médiane dès le 90e jour. Même chose que le 6 novembre, au
  dixième de point près.
- **La soudure suffit pour la première année, pas pour dix.** Avec 212 jours
  de ration au 1er janvier (ce qui reste de la récolte de 1399 jusqu'au
  1er août), aucune cellule de la table ne perd plus de la moitié de ses
  habitants par la faim au 365e jour (pire : Gand, 47 %) et Paris garde 51 % ;
  avec 90 jours, ou en retirant d'avance la perte du grenier, la preuve
  échoue. Les villes meurent ensuite parce que le commerce ne leur apporte
  qu'une petite part de leur manque (Paris : 41 t par jour au mieux pour
  417 t).
- **Le tick avec IA coûte 213 à 230 ms** (41 à 43 ms sans IA), pour un seuil
  de révision à 100 ms. Le profil nomme la cause : `maisons_de_l_ia` refait à
  chaque tick, par point dans polygone et en relisant des fichiers JSON, une
  liste qui ne change pas (170 ms sur 218). Calculée une fois par la boucle :
  **67 ms**, et le monde reste identique octet pour octet.
- **La chaîne livre petit, et de plus en plus autour du jeu plutôt que dans
  le jeu** : depuis le 28 octobre, 60 % des lots livrés sont `pc` et un sur
  trois n'est qu'une preuve, un juge, un montage ou un test réécrit ; une
  PR de lot fait 290 lignes (plafond 300) ; une ligne du CAP du jalon 4 est
  devenue 3,9 issues. Les douze lots « à créer » du CAP — ceux du jeu visé —
  n'ont toujours pas d'issue. Une fois le brief écrit, un lot fusionne en
  1 h 20 ; une panne de session Claude a coûté 145 h d'un seul tenant
  (22-28 octobre). Détail : section 3.

## 1. Le monde sans joueur

### Ce qu'on a mesuré

```bash
cd jeu
py ../docs/mesures/2026-11-07-refonte/scripts/mesure_monde.py --ticks 3650 \
   --jalons 90,365,1825,3650 --sortie ../docs/mesures/2026-11-07-refonte/brut/monde-ia.json
```

La boucle est celle de `python -m sim --ia` : l'IA dépose avant chaque tick,
puis `tick(monde, rng, monde.ticks_ecoules)`. Les morts de faim se comptent en
enveloppant `engine._apply_mortality`, sans rien changer à ce qu'il fait. La
cellule de chaque ville vient de `world.attribution_villes.placees`. Gand et
Bruges tombent dans la même cellule (10391).

| | départ | 90e jour | 365e jour | 1 825e jour | 3 650e jour |
|---|---|---|---|---|---|
| Europe (habitants) | 34 957 409 | 96,7 % | 101,8 % | 102,2 % | 100,1 % |
| Paris (10322) | 275 000 | 0,9 % | **0 %** | 0 % | 0 % |
| Milan (10466) | 177 000 | 1,0 % | **0 %** | 0 % | 0 % |
| Florence (10260) | 101 000 | 9,6 % | 4,8 % | 0 % | 0 % |
| Gand et Bruges (10391) | 181 000 | 9,3 % | 3,9 % | 0 % | 0 % |
| Le Caire (8992) | 360 000 | 5,7 % | **3,5 %** | 0 % | 0 % |
| Constantinople (10374) | 147 167 | 93,1 % | 97,6 % | 84,4 % | 77,2 % |
| Londres (10237) | 63 826 | 97,7 % | 103,4 % | 76,6 % | 43,4 % |
| échecs à la table du jalon 2 | 0 | 4 | 4 | 4 | 4 |
| cellules de la table mortes de faim à plus de moitié (sur 61) | 0 | 5 | 6 | 9 | 45 |

Au 365e jour, Paris a perdu 248 154 habitants par la faim (90 % de son départ),
Milan 175 852 (99 %), Le Caire 344 893 (96 %). Les quatre échecs du jalon 2
sont les quatre régions denses (Flandre, Île-de-France, Italie du Nord, delta
du Nil), sous la médiane dès le 90e jour. L'IA a déposé 94 gestes acceptés
dans l'année (70 parts, 17 greniers ouverts, 7 routes), 35 maisons sur 36 en
ont fait au moins un. **L'IA se tait ensuite** : dans la cinquième année,
21 maisons sur 36 seulement déposent un geste, 22 dans la dixième (la preuve
du jalon 5 en demande un par maison et par an). Au bout de dix ans, l'Europe
a gardé son total (100,1 %) en vidant ses villes : 45 des 61 cellules de la
table ont perdu plus de la moitié de leurs habitants par la faim.

Le 6 novembre (base `b6e15ae6`), les mêmes chiffres : Paris et Milan 0 % au
365e jour, Le Caire 3,4 %, l'Europe 101,8 %. Les dix-huit lots fusionnés depuis
n'ont rien changé à la tenue du monde.

### Pourquoi

```bash
cd jeu && py ../docs/mesures/2026-11-06-refonte/scripts/diagnostic_villes.py
```
([`brut/diagnostic-villes.txt` du 6 novembre](../2026-11-06-refonte/brut/diagnostic-villes.txt))

| ville | habitants | sa cellule en nourrit | manque par jour | stock du 1er janvier |
|---|---|---|---|---|
| Paris | 275 000 | 66 225 | 417 t | 15 277 t |
| Le Caire | 360 000 | 219 163 | 282 t | 12 050 t |
| Gand et Bruges | 181 000 | 70 656 | 221 t | 8 431 t |
| Milan | 177 000 | 85 899 | 182 t | 7 236 t |
| Florence | 101 000 | 77 602 | 47 t | 2 414 t |

Le stock de départ (`INITIAL_FOOD_RESERVE_TICKS = 5` jours, plus
`RESERVE_VILLES_TICKS = 30` jours du manque des villes) tombe en février. Le
commerce, lui, apporte à Paris 41 t par jour au mieux (deuxième mois), et
dans le premier mois les villes **exportent** : Paris 0 t, Le Caire −73 t,
Gand −49 t par jour en moyenne. Le monde de 1400 n'a pas d'arrière-pays qui
nourrisse ses villes.

### Les expériences de soudure

```bash
cd jeu
py ../docs/mesures/2026-11-07-refonte/scripts/experience_soudure.py --nom ration-212-habitants \
   --jours 212 --par-habitants --ia      # et les variantes du tableau
```

Rien n'est changé dans le dépôt : l'amorçage est remplacé en mémoire. Graine
0, IA active, 365 jours ; « J jours » = chaque cellule part avec J jours de
la ration de ses habitants, à la place des cinq jours et du mois des villes.

| variante | stock de l'Europe au 1er janvier | Paris | Milan | Le Caire | Gand | échecs jalon 2 | mortes de faim > ½ | pire |
|---|---|---|---|---|---|---|---|---|
| le dépôt (témoin) | 388 880 t (5,6 jours) | 0 % | 0 % | 3,4 % | 3,8 % | 4 | 6 | Milan 99 % |
| le dépôt, stock partagé par habitants | 388 880 t | 0 % | 0 % | 3,4 % | 3,8 % | 4 | 6 | Milan 99 % |
| 90 jours | 6 292 334 t | 0 % | 32 % | 50 % | 4,8 % | 3 | 5 | Paris 77 % |
| 212 jours, moins la perte du grenier | 12 669 714 t | 19 % | 19 % | 55 % | 3,1 % | 2 | 3 | Milan 74 % |
| **212 jours** (partage par surface, celui du dépôt) | **14 821 941 t** | **51 %** | **105 %** | **70 %** | 12 % | **0** | **0** | Gand 47 % |
| 212 jours, partagé par habitants | 14 821 941 t | 51 % | 105 % | 70 % | 13 % | 0 | 0 | Gand 47 % |

Ce qu'on en tire :

- **212 jours est un ordre de grandeur juste** (niveau 1) : 14,8 Mt, 58 % de
  ce que l'Europe mange en un an, soit les sept douzièmes d'une récolte
  rentrée au 1er août.
- **La preuve du jalon 5 passe, de justesse** : Gand perd 47 % de ses gens
  par la faim au 365e jour pour un seuil de 50 %. Retirer d'avance la perte du
  grenier (25 % par an) la fait échouer ; le moteur ne fait pas pourrir le
  grain des foyers (niveau 3), la soudure n'a donc rien à en retirer.
- **Le partage entre lieux ne compte pas** : par surface ou par habitants,
  même monde au point près. On garde celui du dépôt.
- **Ce n'est qu'un an de gagné.** Paris à 51 % au bout d'un an, Gand à 12 % :
  la soudure finie, les villes retombent dans le manque que le commerce ne
  comble pas. La tenue sur dix ans demande que l'arrière-pays nourrisse ses
  villes (le commerce et sa capacité), et c'est un lot du jalon 5, pas la
  soudure.

## 2. Le tick

```bash
cd jeu && py ../docs/mesures/2026-11-07-refonte/scripts/mesure_tick.py \
   --sortie ../docs/mesures/2026-11-07-refonte/brut/tick.json
```

Graine 0 ; trente ticks de chauffe, puis soixante ticks chronométrés un à un
(ticks 30 à 89) ; `jouer_ia` et `engine.tick` séparés.

| | médiane | min | max |
|---|---|---|---|
| tick sans IA | **43,5 ms** | 39,7 | 65,5 |
| `jouer_ia` | 178,9 ms | 155,1 | 346,8 |
| tick du monde avec IA | 47,1 ms | 42,5 | 68,5 |
| **total avec IA** | **229,7 ms** | 200,7 | 390,2 |

Le 6 novembre : 39,7 ms sans IA, 195,9 ms avec. Le seuil de révision du CAP
(jalon 1) est à 100 ms.

### Le profil (`cProfile`, trente ticks avec IA, ticks 90 à 119)

[`brut/profil-cumulative.txt`](brut/profil-cumulative.txt),
[`brut/profil-tottime.txt`](brut/profil-tottime.txt). Les cinq fonctions les
plus chères, par temps cumulé, sous `jouer_ia` (218 ms par tick) :

| fonction | par tick | ce qu'elle fait |
|---|---|---|
| `capitales.maisons_de_l_ia` | **170 ms** | refait à chaque tick la liste des maisons de l'IA |
| `villes._dans_anneau` (sous `point_dans_geometrie`) | 120 ms | point dans polygone, 16 800 anneaux par tick, pour placer trente capitales et six sièges |
| `capitales.cellule_de_capitale` | 108 ms | la boucle sur les 596 cellules, capitale par capitale |
| `programme_ia.proposer_route_vers_le_champ` | 37 ms | la route de l'IA, dont `verifier_base` 33 ms (la ville de 1400 recalculée à chaque écart essayé) |
| `aggregation.charger_positions` | 32 ms | relit un fichier JSON à chaque tick (six `json.loads` par tick en tout) |

Le tick du monde lui-même (47 ms) se partage entre la consommation (30 ms),
la production (34 ms, `_verser_recolte`), le commerce (26 ms), les départs
(10 ms) et le prélèvement (9 ms).

### Le gain, mesuré sans toucher au dépôt

```bash
cd jeu && py ../docs/mesures/2026-11-07-refonte/scripts/mesure_tick_optimise.py \
   --sortie ../docs/mesures/2026-11-07-refonte/brut/tick-optimise.json
```

La liste des maisons de l'IA ne dépend que des tables de 1400 et de la carte :
le script la calcule une fois, au chargement, et la donne à `jouer_ia`
(`decider_intentions` écarte déjà la maison du joueur). **Même monde** :
empreinte sha256 du monde au 120e tick identique avec et sans
(`b5b324af…`), mêmes 74 gestes. Mesuré au calme, juste après le témoin
(`brut/tick-calme.json`, `brut/tick-optimise.json`) :

| ticks 30 à 89, médiane (max) | le dépôt | la liste calculée une fois |
|---|---|---|
| `jouer_ia` | 169,0 ms (319,7) | **23,9 ms** (191,0) |
| tick du monde | 43,0 ms (55,5) | 42,9 ms (83,3) |
| **total avec IA** | **213,3 ms** (363,1) | **67,4 ms** (234,7) |

Le reste du pic (234 ms) vient des jours où une maison cherche sa route vers
le champ : `verifier_base` recalcule alors la ville de 1400 de sa cellule à
chaque écart essayé (jusqu'à 90 ms pour une grande ville). Ce calcul reste
sans cache : ses contre-épreuves le remplacent par une fonction de même
signature ([`brut/profil-optimise-cumulative.txt`](brut/profil-optimise-cumulative.txt)).

## 3. La chaîne

### GitHub (lecture seule)

[`brut/chaine-github.md`](brut/chaine-github.md), chaque section avec sa
commande ; collecte `scripts/chaine_github_collecte.py` (GraphQL, dix issues
par requête : au-delà de trente, GitHub rend des timelines tronquées sans
erreur), mesure `scripts/chaine_github_mesure.py --compact
brut/chaine-github.json --section <n>`. Un lot livré = une issue fermée avec
`livre` (la date de fusion de sa PR ne change aucune case).

**Les lots livrés, par jalon et par semaine** (semaines ISO, heure de Paris) :

| jalon | S40 | S41 | S42 | S43 | S44 | S45 (partielle) | depuis le 1er oct. | depuis le 28 oct. |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| J2 | 9 | · | · | · | · | · | 9 | · |
| J3 | 2 | 31 | 25 | 8 | · | · | 66 | · |
| J4 | 13 | 28 | 20 | 24 | 49 | 7 | **141** | **54** |
| J5 | · | 6 | 1 | · | 2 | 11 | 20 | 13 |
| J6 | · | · | · | 8 | 4 | · | 12 | 3 |
| total | 24 | 65 | 46 | 40 | 55 | 18 | **248** | **70** |

| | depuis le 1er octobre | depuis le 28 octobre |
|---|--:|--:|
| part des lots `pc` | 50 % (124 / 248) | **60 %** (42 / 70) |
| part des lots qui ne sont que preuve, épreuve, juge, test, montage ou mesure (titre) | 17 % (42) | **31 %** (22) |
| la même, avec capture, photo, banc, contrôle, verdict | 20 % (49) | 33 % (23) |
| PR de lot sans aucun fichier produit (ni code du jeu, ni Unity, ni 3D) | 17 % (40 / 241) | **29 %** (20 / 70) |
| taille médiane d'une PR de lot (Q1 – Q3), brief compris | **299** (289 – 440) | 290 (264 – 299) |
| la même, sans le brief | 242 (203 – 332) | 202 (179 – 239) |

Le plafond du brief est `lignes_max = 300` : la médiane y colle. Depuis le
28 octobre, un lot livré sur trois est une preuve, un juge, un montage ou un
test réécrit (« Les tests du monde ne jouent plus l'ancienne règle des
routes », « Le juge de la raison lit les deux règles »…), et les lots `pc`
sont surtout des sessions, des verdicts et des photos d'épreuves.

**Ce que chaque ligne du CAP est devenue** (l'issue et ses sous-lots
« Découpé du lot #N », récursivement ; feuille = issue sans sous-lot) :

| jalon | lignes | dont découpées | feuilles | feuilles par ligne | livrées | ouvertes |
|---|--:|--:|--:|--:|--:|--:|
| J3 | 19 | 9 | 58 | 3,05 | 58 | 0 |
| J4 | 30 | 15 | **116** | **3,87** | 108 | 8 |
| J5 | 9 | 1 | 24 | 2,67 | 16 | 8 |
| J6 | 19 | 2 | 36 | 1,89 | 12 | 24 |
| J7 – J9 | 47 | 0 | 47 | 1,00 | 0 | 47 |

Les lignes qui ont le plus enflé : #431 les familles de 1400 (17 feuilles),
#426 l'IA bâtit sa capitale (16, cinq niveaux de découpe), #856 la fiche parle
en noms (15), #409 le jeu ouvre la capitale (13). En plus des lignes, J4
porte 45 issues qui ne descendent d'aucune ligne du CAP.

**Les lots « à créer » sans issue** : 12 — J5 : la soudure, l'Europe qui
tient dix ans, le fil des nouvelles, le jeu en observateur avec cinq
vitesses, le siècle mesuré chaque semaine ; J6 : le pays d'un seul tenant,
prendre n'importe quel pays, bâtir dans une province, le panneau du pays ;
J7 : l'alliance, la bataille dans `sim/`, la bataille sur la carte. **Ce sont
les lots du jeu décrit plus haut** ; ils attendent depuis le 28 octobre, faute
d'issue, pendant que la chaîne livrait les preuves des autres.

**État courant** : une seule PR de lot ouverte (#511, la preuve du jalon 5,
ouverte le 7 octobre) ; J4 garde huit lots ouverts, tous `pc` : la langue du
cabinet (#849, #850, #851), le prix d'un chantier (#419), la preuve du jalon
(#508), les 60 images par seconde (#962), et deux bloqués, les maisons
regroupées (#960) et le jeu qui s'ouvre en pause (#860). J5 en garde huit
(dont #324, la preuve, et sa PR #511), J6 vingt-quatre.

### Le journal du pilote, sur le VPS (lecture seule)

[`brut/vps-pilote.md`](brut/vps-pilote.md) ;
`scripts/vps_pilote_collecte.py` puis `scripts/vps_pilote.py`. Le journal
remonte au 15 septembre ; il ne date ni le passage à `pret` (pris dans les
timelines GitHub) ni la durée d'un appel (estimée par les en-têtes de tour).

| de `pret` à la fusion (heures) | Q1 | médiane | Q3 | p90 | max |
|---|---|---|---|---|---|
| depuis le 1er octobre (241 lots) | 3,1 | **9,9** | 54 | 125 | 505 |
| depuis le 28 octobre (70 lots) | 6,0 | **16,1** | 28 | 159 | 505 |
| `pret` et dépendances fermées → fusion, depuis le 1er octobre | 1,4 | 3,4 | 16,7 | 38,8 | 260 |
| brief écrit → fusion, depuis le 1er octobre | 1,0 | **1,4** | 3,2 | 16,7 | 256 |
| brief écrit → fusion, depuis le 28 octobre | 0,9 | 1,2 | 3,4 | 14,8 | 166 |

- **Le temps se perd avant le chef** (la moitié de la somme des durées) et
  dans les **blocages** (24 % pour 39 lots, médiane 9,9 h avant la reprise).
- **Appels d'agents** : 1 071 depuis le 1er octobre, 266 depuis le 28. Chef
  Opus 194 appels (médiane 5,7 min, 36 échecs) ; codeur Codex 167 (14 min,
  47 échecs ou vides) ; codeur Sonnet 22 (9,7 min, aucun échec) ; relecteur
  Opus 126 (4,2 min), Codex 129, grok 104 (11 min). Environ 187 heures d'agent
  en cinq semaines, hors PC.
- **Attentes** : 217 h de tours sans agent possible depuis le 1er octobre,
  80 h depuis le 28. Une seule panne en fait 145 : la session Claude expirée
  du 22 octobre 21 h 53 au 28 octobre 10 h 45 (trois lots fusionnés en cinq
  jours). Le quota Claude : 47 h depuis le 1er octobre, dont 14 épisodes et
  70 h depuis le 28 (les plus longs : 15,6 h et 15,4 h le 29 octobre).
- **Ce qui coûte en plus** : 33 % de relectures `CORRIGER` depuis le
  1er octobre (23 % depuis le 28) ; 131 blocages sur 81 lots ; 63 appels
  coupés par leur délai, dont 30 chefs ; 33 % de tours « RIEN » (44 % depuis
  le 28 octobre) ; 69 lots découpés par le chef, plus d'un sur quatre.

## 4. Le plan classé

Le jeu visé : un pays de 1400 qu'on gouverne depuis la carte, avec la pause et
cinq vitesses, dont les gestes jouent sur des métriques paramétrables
(modificateurs, jauges, bâtiments), contre une IA qui a les mêmes, dans un
monde qui tourne seul. Chaque ligne dit sur quoi elle s'appuie dans les
mesures ci-dessus.

### Ce qui le sert, dans l'ordre

1. **La soudure de 1400** (lot « à créer » du jalon 5) : 212 jours de ration au
   1er janvier. Sans elle, Paris est vide en avril et la table du jalon 2
   échoue au 90e jour ; avec elle, la première année tient (section 1).
2. **Le tick avec IA sous 100 ms** : 213 à 230 ms aujourd'hui, dont 170 ms pour
   refaire une liste qui ne change pas (section 2). Les cinq vitesses du
   jalon 5 en dépendent.
3. **Le registre des modificateurs** (D34, D35, D37) : le cœur de la
   refonte ; récolte, prélèvement, natalité, mortalité, départs, chantiers et
   commerce y passent, et leurs chiffres vivent dans `jeu/data/`.
4. **Le pays d'un seul tenant et ses quatre jauges** (lot « à créer » du
   jalon 6, et D36) : le joueur gouverne aujourd'hui quatre lieux ; la vue
   `pays(maison)` et `/pays` lui donnent un pays.
5. **Les bâtiments de province, posés depuis la carte** (lot « à créer » du
   jalon 6) : le premier geste de bâtisseur qui n'exige pas la 3D, et le
   premier que l'IA puisse faire hors de sa capitale.
6. **Ce que le joueur en voit**, des lots `pc` qui lisent le service :
   l'infobulle et le détail des modificateurs, la barre et ses jauges, le
   panneau du pays.
7. **L'IA qui joue ses jauges et ses bâtiments**, par le même chemin.
8. **L'arrière-pays qui nourrit ses villes** : sans lui, la soudure finie, les
   villes de 1400 retombent (Paris 41 t par jour d'apport pour 417 t de
   manque). C'est la tenue sur dix ans du jalon 5.
9. **Le jeu en observateur avec cinq vitesses, et le fil des nouvelles**
   (lots « à créer » du jalon 5) ; puis **prendre n'importe quel pays**
   (jalon 6).

### Ce qui l'attend

- **La dynastie** (jalon 6, #432 à #447) : elle donnera les compétences d'où
  naissent les points de la Plume, du Sceau et de l'Épée (#434), et la
  succession contestée qui entame le Droit. Les familles de 1400 (#804 à #806,
  #977 à #980) en sont la donnée.
- **La guerre** (jalon 7), **l'argent** (jalon 8), **le siècle** (jalon 9) :
  leurs gestes poseront des modificateurs et dépenseront des jauges ; ils
  s'écriront sur le registre plutôt qu'à côté.
- **#954, la route vers la voisine du commerce** (jalon 5) : elle touche le
  commerce qui ne nourrit pas les villes ; à relire contre le lot 8 ci-dessus.

### Ce qui le contourne

- **Les lots de preuve séparés** : un lot livré sur trois depuis le 28 octobre
  est une preuve, un juge, un montage ou un test réécrit (section 3), et une
  ligne du CAP devient en moyenne 3,9 issues au jalon 4. Une capacité et sa
  preuve iront dans la même PR.
- **La capitale en 3D au-delà de ce qui est fait** : le prix d'un chantier
  dans le panneau de la capitale (#419), la preuve complète du jalon 4
  (#508), les 60 images par seconde (#962), les maisons regroupées (#960),
  la langue de la capitale (#851). La capitale est une vue (décision 27) ;
  60 % des lots livrés depuis le 28 octobre sont `pc`.
- **L'IA qui bâtit sa capitale au plan** (#953 les parcelles le long des rues,
  #955 l'enceinte de l'IA) : ses gestes de bâtisseur seront ceux du pays, les
  bâtiments de province, pas les parcelles de la ville.
- **La relecture par une autre famille de modèle** et les secours Cursor : il
  n'y a plus qu'un abonnement (Claude) ; la chaîne doit le dire et cesser d'en
  dépendre (relecteur Opus, Sonnet qui code).

## 5. Les réponses du propriétaire (7 novembre 2026)

Posées en une fois, chacune avec sa recommandation ; les quatre recommandations
sont retenues.

| question | réponse |
|---|---|
| les quatre jauges | la **Concorde** (−3 à +3, la stabilité), le **Renom** (le prestige), le **Droit** (la légitimité) et trois réserves de points, la **Plume** (administrer), le **Sceau** (traiter) et l'**Épée** (combattre) ; la refonte donne tout de suite aux chefs de 1400 leurs compétences de gestion, de diplomatie et de guerre (0 à 10, niveau 2), pour que les points coulent dès 1400 ; #434 garde les traits, l'hérédité et l'éducation |
| la chaîne pendant la refonte | arrêtée (`atelier-boucle arret` le 7 novembre, `PC_ACTIF` = `non`, la variable était absente), réarmée à la fin |
| le jalon 4 | clos : #849 et #850 (le socle et la carte dans la langue du cabinet) passent au jalon 6 avec la barre et le panneau du pays ; #860 au jalon 5 avec l'observateur ; #851, #419, #508, #962 et #960 à la Réserve, chacun avec sa raison ; aucun n'est fermé |
| les événements à choix | oui, nés d'une cause du monde (une famine, une révolte, une succession contestée), deux ou trois choix qui posent des modificateurs ou dépensent une jauge, jamais une issue imposée ; l'IA choisit par le même chemin ; un lot, après les jauges |

Elles entrent dans [docs/VISION.md](../../VISION.md) comme décisions 39 à 41.

## 6. Après la soudure et la liste des maisons de l'IA (PR 2)

```bash
cd jeu
py ../docs/mesures/2026-11-07-refonte/scripts/mesure_monde.py --ticks 3650 \
   --jalons 90,365,1825,3650 --sortie ../docs/mesures/2026-11-07-refonte/brut/apres-monde-ia.json
```

Même boucle que la section 1 (graine 0, IA active, la liste des maisons de
l'IA calculée une fois), sur la branche `direct/soudure-et-tick`.

| | 90e jour | 365e jour | 1 825e jour | 3 650e jour |
|---|---|---|---|---|
| Europe | 101,8 % | 106,9 % | 106,5 % | **88,3 %** |
| Paris | 96,8 % | **50,6 %** (avant : 0 %) | 22,6 % | 22,8 % |
| Milan | 101,7 % | 105,0 % | 4,1 % | 4,2 % |
| Florence | 101,8 % | 107,6 % | 0,8 % | 0,2 % |
| Gand et Bruges | 95,8 % | 12,8 % | 0,3 % | 0 % |
| Le Caire | 101,8 % | 70,3 % | 54,3 % | 53,1 % |
| Constantinople | 101,8 % | 105,8 % | 86,9 % | 83,4 % |
| Londres | 101,8 % | 106,2 % | 92,9 % | 60,5 % |
| échecs à la table du jalon 2 | 0 | **0** | 2 | 2 |
| cellules de la table mortes de faim à plus de moitié (sur 61) | 0 | **0** | 17 | 49 |
| maisons de l'IA qui ont déposé un geste dans l'année (sur 36) | — | 34 | 11 | 16 |

La première année tient : c'est la preuve de la PR 2. **Les suivantes non** :
les villes retombent dans le manque, et à dix ans l'Europe a perdu 12 % de
ses habitants (dans la mesure d'avant, elle gardait son total en vidant ses
villes au profit des campagnes). L'IA se tait de plus en plus : 11 maisons sur
36 déposent un geste dans la cinquième année. Deux lots du jalon 5 en
découlent : l'arrière-pays qui nourrit ses villes (le commerce et sa
capacité), et une IA qui garde des raisons d'agir quand ses greniers sont
vides.

Le tick, ticks 30 à 89 avec IA, sur le PC : **67 ms** de médiane (section 2),
pour 213 ms avant.

## 7. À la fin de la refonte (PR 3 à 5)

```bash
cd jeu
py ../docs/mesures/2026-11-07-refonte/scripts/mesure_tick.py \
   --sortie ../docs/mesures/2026-11-07-refonte/brut/tick-fin.json
py ../docs/mesures/2026-11-07-refonte/scripts/mesure_monde.py --ticks 3650 \
   --jalons 90,365,1825,3650 --sortie ../docs/mesures/2026-11-07-refonte/brut/monde-fin.json
```

Sur la branche des bâtiments de province (#1040, qui porte #1039 et #1025),
au calme, sur le PC. Les deux scripts jouent désormais le mois des jauges
avant l'IA, comme les boucles du jeu. Entre parenthèses, la section 6 (la
soudure seule).

| | 90e jour | 365e jour | 1 825e jour | 3 650e jour |
|---|---|---|---|---|
| Europe | 101,8 % (101,8 %) | 107,2 % (106,8 %) | 108,9 % (106,5 %) | 93,8 % (88,3 %) |
| Paris | 96,8 % (96,8 %) | 52,6 % (50,6 %) | 25,6 % (22,6 %) | 25,9 % (22,8 %) |
| Milan | 101,7 % (101,7 %) | 105,0 % (105,0 %) | 4,7 % (4,1 %) | 5,0 % (4,2 %) |
| Florence | 101,8 % (101,8 %) | 107,6 % (107,6 %) | 0,7 % (0,8 %) | 0,1 % (0,1 %) |
| Gand et Bruges | 95,6 % (95,8 %) | 12,7 % (12,8 %) | 0,3 % (0,3 %) | 0,0 % (0,0 %) |
| Le Caire | 101,8 % (101,8 %) | 108,2 % (70,2 %) | 53,7 % (54,3 %) | 60,4 % (53,1 %) |
| Constantinople | 101,8 % (101,8 %) | 106,2 % (105,8 %) | 130,7 % (86,9 %) | 106,7 % (83,4 %) |
| Londres | 101,8 % (101,8 %) | 107,6 % (106,2 %) | 103,0 % (92,9 %) | 91,3 % (60,5 %) |
| échecs à la table du jalon 2 | 0 (0) | 0 (0) | 2 (2) | 2 (2) |
| cellules de la table mortes de faim à plus de moitié (sur 61) | 0 (0) | 0 (0) | 18 (17) | 46 (49) |
| maisons de l'IA qui ont déposé un geste dans l'année (sur 36) | 35 (33) | 35 (34) | 18 (11) | 17 (16) |

Gestes acceptés de l'IA en dix ans, par type : batir_dans_une_province 35, depenser_jauge 186, fixer_part 112, ouvrir_grenier 94, tracer_route 173.

Ce qui a changé depuis la section 6 vient des gestes du pays, joués par
l'IA par le même chemin que le joueur : 35 moulins (28 dès le 90e jour,
chacun +10 % de grain récolté sur sa cellule), 186 gestes de jauge (la
Concorde affermie après une famine). L'Europe perd 6 % en dix ans au lieu de
12 % ; Londres, Constantinople et Le Caire tiennent ; à cinq ans, 18 maisons
de l'IA agissent encore au lieu de 11. **Les villes qui vivent du commerce
retombent toujours** (Paris 26 %, Milan 5 %, Florence et la Flandre vides) :
c'est le lot #1026, premier du jalon 5.

**Le tick**, ticks 30 à 89, médiane (max) : sans IA 38,7 ms
(50,1 ms) ; avec IA, mois des jauges compris, **50,8 ms**
(66,2 ms), pour 213 ms au début de la refonte et 67 ms après la PR 2.
