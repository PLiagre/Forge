# Lot #208 — Les grandes maisons tiennent leurs cellules
Jalon : J2 · Machine : vps · Taille prévue : 290 lignes

## But
Le monde sait dire quelle maison tient chaque cellule couverte au 1er janvier 1400 : Valois à Paris, Valois-Bourgogne à Dijon et à Bruges, Montfort à Nantes, Wittelsbach à Munich et à Heidelberg, Habsbourg à Vienne, Luxembourg à Prague et à Buda, Paléologue à Constantinople. Les républiques, l'Église et les ordres, eux, se déclarent sans maison. C'est la part « les grandes maisons entrent dans le monde au niveau de la cellule » du jalon 2 (CAP.md), et c'est ce que la carte de 1400 et la fiche de la terre choisie afficheront.

## Règle du monde
Elle découle de `jeu/sim/MODELE.md`, sections « Les puissances de 1400, vue
dérivée » et « La province dérivée et ses centres » (la règle du plus proche
et son départage). **Base : master après la fusion de #207** (`e2d6021`,
39 puissances, 73 ancres, 8 lacunes). Si la branche du lot part d'avant, le
codeur la rebase d'abord sur `origin/master`.

**La règle des puissances ne change pas, et le tick ne lit rien de neuf.** Ni
la portée, ni la projection, ni les 39 puissances, ni les 73 ancres, ni leurs
`id`, ni `jeu/sim/puissances.py` ne bougent. Aucune ancre n'est ajoutée, et
aucune cellule ne change de puissance.

**Ce qui s'ajoute.**

- **Une maison** a un `id`, un `nom` et une `source`, c'est-à-dire l'article
  public qui atteste ce qu'elle tient au 1er janvier 1400.
- **Chaque puissance nomme la maison qui la tient, ou se déclare.** Une
  puissance de nature `république`, `Église` ou `ordre` n'a **pas** de champ
  `maison` : sa nature suffit à la déclarer. Toutes les autres (`royaume`,
  `principauté`, `empire`, `sultanat`, `khanat`) en portent un, qui désigne
  une maison connue.
- **Un grand vassal tient des ancres de sa puissance.** Une ancre peut
  déclarer `maison` : la maison qui tient cette ville, quand ce n'est pas
  celle de la puissance (Dijon, ancre de la France, est tenue par
  Valois-Bourgogne). Sans déclaration, l'ancre est tenue par la maison de sa
  puissance (ou par personne si la puissance se déclare république, Église ou
  ordre). Par construction, l'ancre d'un vassal est une ancre de sa
  puissance. La preuve vérifie que **la cellule de ce point** relève bien de
  cette puissance et de ce vassal.
- **La maison tenante d'une cellule** est celle qui tient l'ancre dont la
  cellule relève déjà. C'est la même ancre la plus proche, avec le même
  départage par le plus petit `id`, que celle qui donne la puissance. Une
  cellule non couverte n'a pas de maison (`None`), pas plus qu'une cellule
  d'une république, d'une Église ou d'un ordre. La maison d'une cellule est
  donc toujours la maison de sa puissance ou celle d'un vassal ancré dans
  cette puissance, jamais une maison étrangère.
- La vue est pure, recalculée, hors de `sim.model` ; elle ne pose rien sur
  `Cell` et n'est pas une seconde clé spatiale.

**Niveaux de fidélité.**

- **Niveau 1** (sources publiques) : la maison qui tient chaque puissance au
  1er janvier 1400, et le vassal qui tient chacune des six villes déclarées.
- **Niveau 2** (plausible ; une anomalie n'est pas un défaut) : l'étendue de
  chaque maison, qui suit les ancres. Mesures du chef sur la carte figée :
  Montfort tient 18 cellules et Valois 13 ; Habsbourg en tient 2 ; Innsbruck
  (Tyrol, habsbourgeois) tombe chez Wittelsbach, et Linz en Bohême ;
  Besançon et Lille tombent chez Valois-Bourgogne. Luxembourg tient le
  Saint-Empire, mais aucune de ses cellules : ses trois ancres sont tenues
  par des vassaux. Ses cellules sont celles de la Bohême et de la Hongrie.
  Tout cela est accepté, pas corrigé.
- **Niveau 3, pas simulé** : le lien de suzeraineté lui-même (hommage,
  pyramide : jalon 3) ; les personnes (Charles VI, Philippe le Hardi :
  jalon 6) ; Vytautas en Lituanie (la cellule reste Jagellon) ; la Naples
  disputée entre Ladislas et Louis II d'Anjou ; Édigu derrière le khan ;
  Marguerite derrière Éric ; les vassaux sans ancre (Orléans, Anjou, Berry,
  Foix, Armagnac, Wettin, Hohenzollern, la Hollande des Wittelsbach) ; les
  terres d'Empire de Bourgogne.

### Ce que le codeur écrit

**1. `jeu/data/puissances-1400.json`.**

- `fidelite` devient « Niveau 1, d'après des sources publiques ; les maisons
  tenantes sont de niveau 1 ; le Grand Schisme et les suzerainetés ne sont
  pas simulés. »
- Une liste racine **`maisons`** est ajoutée, une entrée par ligne
  (`{ "id": …, "nom": …, "source": … }`), avec exactement ces 30 maisons.
- Les 29 lignes de puissance du tableau gagnent `"maison": <id>`.
- Les six ancres de vassal gagnent `"maison": <id>`.
- Rien d'autre ne change : ni champ, ni `id`, ni coordonnée.

| id | nom (exact, le test le lit) | tient la puissance (champ `maison` de la puissance) | tient l'ancre (champ `maison` de l'ancre) |
|---|---|---|---|
| 1 | `Lancastre` | Angleterre | — |
| 2 | `Stuart` | Écosse | — |
| 3 | `Valois` | France | — |
| 4 | `Aviz` | Portugal | — |
| 5 | `Trastamare` | Castille | — |
| 6 | `Barcelone` | Aragon, Sicile | — |
| 7 | `Évreux` | Navarre | — |
| 8 | `Nasrides` | Grenade | — |
| 9 | `Luxembourg` | Saint-Empire, Bohême, Hongrie | — |
| 10 | `Visconti` | Milan | — |
| 11 | `Anjou-Durazzo` | Naples | — |
| 12 | `Savoie` | Savoie | — |
| 13 | `Poméranie` | Union de Kalmar | — |
| 14 | `Jagellon` | Pologne-Lituanie | — |
| 15 | `Paléologue` | Byzance | — |
| 16 | `Osman` | Ottomans | — |
| 17 | `Lazarević` | Serbie | — |
| 18 | `Kotromanić` | Bosnie | — |
| 19 | `Basarab` | Valachie | — |
| 20 | `Mușat` | Moldavie | — |
| 21 | `Djötchides` | Horde d'Or | — |
| 22 | `Barquq` | Mamelouks | — |
| 23 | `Hafsides` | Hafsides | — |
| 24 | `Zayyanides` | Zayyanides | — |
| 25 | `Mérinides` | Mérinides | — |
| 26 | `Lusignan` | Chypre | — |
| 27 | `Valois-Bourgogne` | — | Dijon, Bruges |
| 28 | `Montfort` | — | Nantes |
| 29 | `Wittelsbach` | — | Munich, Heidelberg |
| 30 | `Habsbourg` | — | Vienne |

Sans champ `maison`, et c'est voulu : Archevêché de Trèves, Confédération
des cantons suisses, Venise, Florence, Gênes, Papauté, Ordre teutonique,
Novgorod, Pskov, Hospitaliers (10 puissances).

Chaque `source` nomme l'article public qui atteste qui tient quoi au
1er janvier 1400. Par exemple :

- Henri IV, roi depuis le 30 septembre 1399 ;
- Venceslas de Luxembourg, roi des Romains jusqu'au 20 août 1400 ;
- Martin Ier d'Aragon et Martin le Jeune en Sicile, maison de Barcelone ;
- Ladislas d'Anjou-Durazzo ;
- Éric de Poméranie, roi de l'Union depuis 1397 ;
- Iuga de Moldavie, maison de Mușat ;
- Faraj, fils de Barquq, sultan depuis 1399 ;
- Janus de Lusignan ;
- Philippe le Hardi, duc de Bourgogne et comte de Flandre depuis 1384 ;
- Jean V de Montfort, duc de Bretagne depuis 1399 ;
- Robert III, électeur palatin, et les ducs de Bavière-Munich ;
- Albert IV, duc d'Autriche.

Le codeur vérifie chaque ligne contre sa source. Un nom qu'une source
publique donne autrement peut prendre cette graphie ; il le dit dans la PR
et le test suit le fichier. Une **attribution** qu'il ne peut pas sourcer, il
ne la remplace pas par une autre : il s'arrête et le dit dans la PR.

**2. `jeu/sim/maisons.py`** (nouveau ; aucun littéral numérique hors
{0, 1, −1} dans un corps de fonction, et `test_no_hardcoded` l'inspecte
seul). Il lit le même fichier que `puissances.py` et peut en importer
`_CHEMIN_TABLE`, `_refuser_id`, `_texte`, `PuissanceInvalide`,
`charger_table`, `charger_portee`, `charger_latitude_moyenne_puissances` et
`puissance_par_cellule`. Il ne modifie pas `puissances.py`.

- `Maison(_NoBadSpatialField)`, dataclass gelée : `id`, `nom`, `source`.
- `TableDesMaisons(_NoBadSpatialField)`, dataclass gelée, avec trois champs :
  - `maisons`, un tuple trié par `id` ;
  - `par_puissance`, un dict qui donne pour chaque id de puissance un id de
    maison, ou `None` ;
  - `par_ancre`, un dict qui donne pour chaque id d'ancre la maison qui tient
    l'ancre : celle qu'elle déclare, sinon celle de sa puissance, ou `None`.
- `charger_maisons(path=None) -> TableDesMaisons`. Elle lève
  `PuissanceInvalide` en nommant la ligne et le champ dans ces cas :
  - `maisons` absente ou vide (« champ maisons ») ;
  - un `id` de maison dupliqué ou booléen ;
  - un `nom` ou une `source` absents ou vides (« maison <id>, champ <champ> ») ;
  - une puissance `république`, `Église` ou `ordre` qui porte `maison` ;
  - une autre puissance sans `maison`, ou dont la `maison` est inconnue
    (« puissance <id>, champ maison ») ;
  - une ancre dont la `maison` est inconnue, ou est déjà celle de sa
    puissance (« ancre <id>, champ maison ») ;
  - une maison qui ne tient ni puissance ni ancre (« maison <id>, champ
    maison : ne tient rien »).

  `charger_table` ne lit pas les maisons et n'en dépend pas.
- `maison_par_cellule(positions, table, maisons, portee, latitude_moyenne)
  -> dict`. Elle est pure et ses clés sont celles de `positions`. Pour chaque
  cellule :
  - si `puissance_par_cellule` la donne non couverte, la valeur est `None` ;
  - sinon, c'est `maisons.par_ancre[a]`, où `a` est l'ancre que
    `derive_appartenance(positions, table.ancres, latitude_moyenne)` lui donne.

  Une ancre de `table` absente de `maisons.par_ancre` lève
  `PuissanceInvalide` (« ancre <id>, champ maison »).
- `maisons_depuis_monde(world, positions=None, table=None, maisons=None,
  portee=None, latitude_moyenne=None) -> dict`. Elle est faite sur le modèle
  de `puissances_depuis_monde`, par `positions_du_monde`.
- `maison_de_cellule(cell_id, vue, maisons)` rend la `Maison` de la cellule,
  ou `None`.

**3. `jeu/sim/tests/test_maisons.py`** (nouveau). Il peut importer
`_cellule_la_plus_proche` de `sim.tests.test_puissances` plutôt que la
recopier. **Aucun test existant n'est touché.**

**4. `jeu/sim/MODELE.md`** :

- Une section **« ## Les maisons de 1400, vue dérivée »** s'ajoute,
  juste après celle des puissances. Elle dit la règle ci-dessus, les
  30 maisons, les dix puissances qui se déclarent, les six ancres de vassal,
  les mesures (476 cellules tenues par une maison, 89 de république, d'Église
  ou d'ordre, 31 non couvertes) et les trois niveaux. Elle dit aussi que le
  tick ne la lit pas.
- Dans « En une page », la phrase sur la puissance gagne la maison : elle
  aussi est une vue dérivée, que le tick ne consomme pas.

## Périmètre
jeu/data/puissances-1400.json
jeu/sim/maisons.py
jeu/sim/tests/test_maisons.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent depuis la racine par
`python3 -m pytest jeu/sim/tests/test_maisons.py -q -s -k <nom>`. Chaque test
imprime ses compteurs, et un échantillon vide échoue. Aucun `cell_id` ni
`id` n'est écrit dans un test : maisons, puissances et ancres se trouvent par
leur `nom`, les cellules par des points nommés dans le test (niveau 1),
via `_cellule_la_plus_proche`. Prouver chaque contre-épreuve rouge avant de
la garder.

**SC1 — tout se lit** (`-k lecture`). Sur la vraie table, le test exige :

- `maisons_lues == 30` ;
- `len(par_puissance) == 39`, dont 29 maisons et 10 `None`, et les natures de
  ces 10 sont toutes dans {`république`, `Église`, `ordre`} ;
- `vassaux_declares == 6` (ancres dont la maison diffère de celle de leur
  puissance) ;
- les clés de `par_ancre` égales aux `id` des ancres de `charger_table()`.

Contre-épreuve (`tmp_path`) : la table sans Visconti ni le `maison` de Milan
est refusée, puisque Milan, une principauté, n'a plus de maison.

**SC2 — les refus tiennent, sans toucher la table des puissances**
(`-k refus`). Un test paramétré fait une altération à la fois dans
`tmp_path` :

- `maisons` retirée ;
- `maison` de la France retirée ;
- `maison` ajoutée à Venise ;
- `maison` de la France inconnue (max + 1) ;
- `maison` de Nantes inconnue ;
- `maison` de Vienne mise à Luxembourg, celle du Saint-Empire ;
- `nom` de Valois vide ;
- `source` de Habsbourg absente ;
- `id` de maison dupliqué ;
- `id` de maison booléen ;
- `maison` de Vienne retirée, si bien que Habsbourg ne tient plus rien.

Chacune lève `PuissanceInvalide` en nommant la ligne et le champ
(`refus_observés == len(cas) > 0`). `charger_table` lit encore chacune de
ces tables altérées. Contre-épreuve : la vraie table se charge.

**SC3 — les maisons sont justes** (`-k connues`). Une fonction vérifie sur la
vraie table les 29 couples puissance → maison du tableau et les six ancres
(Dijon et Bruges → `Valois-Bourgogne`, Nantes → `Montfort`, Munich et
Heidelberg → `Wittelsbach`, Vienne → `Habsbourg`). Contre-épreuves
(`tmp_path`) : elle devient fausse quand la France est donnée à Lancastre,
puis quand la maison de Vienne est mise à Wittelsbach (Habsbourg retiré
avec elle).

**SC4 — les grands vassaux sont dans leur puissance** (`-k vassaux`). Sur
`World.charger(0)`, pour chaque ancre qui déclare sa maison
(`vassaux_vus == 6`), la cellule de son point doit relever de la puissance
de l'ancre (vue des puissances) **et** de la maison déclarée (vue des
maisons). Le test imprime `vassaux_vus` et `vassaux_hors`, et exige
`vassaux_hors == 0`. Contre-épreuve, en mémoire
(`dataclasses.replace`) : une ancre du Saint-Empire de plus, `id` = max + 1,
posée exactement sur Prague et tenue par Wittelsbach, donne
`vassaux_hors == 1`. Sa cellule reste en Bohême, parce que Prague a le plus
petit `id` et gagne l'égalité (mesuré).

**SC5 — la carte des maisons** (`-k geographie`). Sur
`maisons_depuis_monde(World.charger(0))`, les cellules doivent être
**distinctes** (sinon échec) et porter ces maisons :

| point | lat ; lon | maison attendue |
|---|---|---|
| Paris | 48,86 N ; 2,35 E | `Valois` |
| Dijon | 47,32 N ; 5,04 E | `Valois-Bourgogne` |
| Bruges | 51,21 N ; 3,22 E | `Valois-Bourgogne` |
| Nantes | 47,22 N ; 1,55 W | `Montfort` |
| Munich | 48,14 N ; 11,58 E | `Wittelsbach` |
| Heidelberg | 49,41 N ; 8,69 E | `Wittelsbach` |
| Vienne | 48,21 N ; 16,37 E | `Habsbourg` |
| Prague | 50,08 N ; 14,44 E | `Luxembourg` |
| Buda | 47,50 N ; 19,04 E | `Luxembourg` |
| Londres | 51,51 N ; 0,13 W | `Lancastre` |
| Constantinople | 41,01 N ; 28,98 E | `Paléologue` |
| Edirne | 41,68 N ; 26,56 E | `Osman` |
| Nicosie | 35,17 N ; 33,36 E | `Lusignan` |
| Venise | 45,44 N ; 12,33 E | `None`, avec la puissance `Venise` (république, pas une absence) |

Contre-épreuves, en mémoire :

- `par_ancre` où Dijon et Bruges reviennent à Valois : leurs deux cellules
  passent à `Valois`, et Valois-Bourgogne ne tient plus aucune cellule ;
- les maisons de Vienne et de Munich échangées : Vienne passe à
  `Wittelsbach`, Munich à `Habsbourg`.

**SC6 — chaque cellule, chaque maison** (`-k compte`). Le test exige :

- les clés de la vue sont exactement `set(world.cells)` ;
- une cellule non couverte n'a pas de maison ;
- une cellule de république, d'Église ou d'ordre n'a pas de maison ;
- toute autre cellule couverte en a une ;
- `incoherentes == 0`. Une cellule est incohérente quand sa maison n'est ni
  celle de sa puissance ni celle d'une ancre de sa puissance ;
- chacune des 30 maisons tient au moins une cellule (l'assertion nomme
  celle qui n'en tient pas).

Il imprime `avec_maison`, `sans_maison_declaree` et `non_couvertes`, dont la
somme est `len(world.cells)` (mesuré : 476, 89, 31). Contre-épreuves :

- une copie de la vue où la cellule de Paris porte Habsbourg donne
  `incoherentes == 1` ;
- `par_puissance` où Chypre passe à Lancastre, en mémoire : Lusignan ne tient
  plus de cellule, et l'assertion la nomme.

**SC7 — une vue pure, que le tick ne lit pas** (`-k pure`). Deux appels de
`maisons_depuis_monde` rendent la même vue. `monde.to_dict()` et les
attributs des cellules sont inchangés. Une position retirée lève
`PositionCelluleInconnue` en nommant la cellule. Enfin,
`grep -c "maisons" jeu/sim/engine.py jeu/sim/world.py jeu/sim/model.py`
rend 0 pour chacun. Contre-épreuve : la même commande sur
`jeu/sim/maisons.py` rend plus de 0.

**SC8 — rien d'autre ne bouge.**
`git diff --name-only origin/master -- jeu/sim/tests jeu/sim/puissances.py`
rend exactement `jeu/sim/tests/test_maisons.py`, et
`git diff origin/master -- jeu/data/puissances-1400.json | grep '^-[^-]' | grep -c -e '"lat"' -e '"nature"'`
rend 35 : ce sont les 29 puissances et les 6 ancres réécrites, et rien d'autre.
Contre-épreuve : toute coordonnée ou nature déplacée fait monter ce compte,
et toute ligne d'un test existant touchée allonge la première liste.
Enfin, `python3 -m pytest jeu -q` est vert, y compris les 39/73 de
`test_puissances.py`, inchangés, et `test_no_hardcoded.py`, qui inspecte
`maisons.py` : un littéral `30` glissé dans une fonction le fait rougir.

**SC9 — le modèle le dit.** La commande
`awk '/^## Les maisons de 1400, vue dérivée/{s=1;next} /^## /{s=0} s' jeu/sim/MODELE.md | grep -c -e Wittelsbach -e Habsbourg`
rend au moins 2, et
`grep -c "les maisons et les suzerainetés ne sont pas simulés" jeu/data/puissances-1400.json`
rend 0. Contre-épreuve : sur la base, avant le lot, la première commande
rend 0 et la seconde 1.

## Hors périmètre
- Toute ancre, puissance ou lacune ajoutée, retirée ou déplacée. Pas de
  changement de portée, de projection, de `puissances.py`, ni de
  `test_puissances.py`.
- Les vassaux sans ancre dans la table (Orléans, Anjou, Berry, Foix,
  Armagnac, Wettin, Hohenzollern, la Hollande des Wittelsbach, Vytautas) :
  les ancrer déplacerait des cellules de puissance.
- Le lien de suzeraineté comme donnée (qui doit l'hommage à qui), les lieux
  et leurs maîtres (jalon 3), les personnes et les dynasties suivies une à
  une (jalon 6).
- Le tick, l'amorçage, `World.charger`, les villes, le service, Unity et
  toute vue d'affichage : la maison n'entre pas encore à l'écran.
- `jeu/data/world-1400.json`, `province-centres-1400.json`,
  `villes-1400.json`, `sim/aggregation.py`, `sim/model.py` : aucun ne change.
