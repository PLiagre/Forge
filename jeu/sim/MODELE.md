# sim/MODELE.md — comment le monde fonctionne

> Ce fichier dit **comment le monde fonctionne** — pas quoi faire pour un
> lot donné : ça, c'est le brief. C'est d'ici que les briefs sont découpés,
> et c'est pourquoi une affirmation fausse ici se propage à tous les lots
> suivants.
>
> Il est rangé par **mécanisme**, jamais par numéro de lot. Les numéros qui
> apparaissent encore ci-dessous datent une règle, ils ne la nomment pas ;
> les lots eux-mêmes vivent dans l'historique git.
>
> **Une formule morte décrite au présent piège le lot suivant.** Quand un
> mécanisme change, ce document change dans le même mouvement — sinon la
> dette se paie au lot d'après.

## En une page

Le monde est une grille de cellules lues dans la carte figée
`data/world-1400.json` — leur nombre est celui du fichier, il n'est écrit nulle
part. À chaque tick, dans cet ordre :

1. **Validation du numéro de tick** (`_valider_numero_tick`) — lorsqu'un
   `numero_tick` est fourni, il doit être égal à `world.ticks_ecoules` ; le
   tick refuse tout écart avant la première mutation.
2. **Intentions** (`_appliquer_intentions`) — les intentions en attente
   s'appliquent dans l'ordre du dépôt : un choix de départ devient la maison
   du joueur, une route entre au plan en chantier ; sans cellule ni aléa.
3. **Fabrication** (`_apply_fabrication`) — chaque matière première présente
   dans le panier d'ouverture perd 5 % de son stock, dont 60 % du poids devient
   de l'`objet`, sur place et sans occuper de bras.
4. **Extraction** (`_apply_extraction`) — chaque gisement de la cellule sort
   des kilogrammes de sa ressource et les dépose dans le panier de la cellule.
5. **Production** (`_apply_production`, `_apply_production_saison_moyenne`) —
   la cellule produit de la nourriture proportionnellement à sa surface,
   multipliée par un aléa de rendement du tick, par le facteur de sa classe de
   relief — une montagne ne produit pas comme une plaine —, par le
   `facteur_eau` de l'eau de la cellule — sa pluie plus la crue du fleuve — et
   par le facteur de saison du jour, tiré de la durée du jour de la cellule :
   on ne récolte pas en janvier comme en juin, ni sans eau comme sous une
   pluie suffisante.
6. **Commerce** (`_apply_commerce`) — les cellules en surplus livrent leurs
   voisines en manque, sur les arêtes d'adjacence. Un kilogramme ne traverse
   qu'une arête par tick et ne nourrit qu'une fois. Toute marchandise du panier
   circule, pas seulement la nourriture.
7. **Consommation** (`_apply_consumption`) — le bourg ne mange que ce qu'il
   atteint, par sa part locale du panier et les chemins venus des champs.
   Ce qui manque devient une **dette** (`food_deficit_kg`), pas un oubli. Si le
   bourg manque pendant que les champs débordent, aucune dette n'est remboursée.
   Sinon, un surplus rembourse la dette, jamais plus vite que le surplus lui-même.
8. **Faim** (`_update_hunger`) — une cellule qui a *manqué* ce tick voit
   `hunger_ticks` monter ; une cellule ravitaillée exactement à son besoin,
   non.
9. **Mortalité** (`_apply_mortality`) — la dette tue, avec report de la
   fraction d'habitant non encore morte pour qu'une petite cellule ne devienne
   pas immortelle par arrondi.
10. **Natalité** (`_apply_natalite`) — une cellule rassasiée et sans dette gagne
   des habitants, avec le même report de fraction.
11. **Migration** (`_apply_migration`) — une part des habitants d'une cellule
    qui a manqué ce tick part vers les voisines dont il reste de la nourriture
    après consommation. Personne n'emporte de kilogrammes.
12. **Répartition sur les lieux** (`repartir_sur_les_lieux`) — leurs habitants
    et paniers sont remis d'accord avec les totaux de la cellule.
13. **Avance du compteur** (`_avancer_compteur_ticks`) — une fois tous les
    maillons réussis, `ticks_ecoules` augmente de un et fait ainsi passer la
    date dérivée au jour suivant.

La **province** ne se stocke pas : elle se recalcule à chaque consultation
comme « le centre administratif le plus proche ». La **pluie** et la **crue**
ne sont pas stockées sur `Cell` : leurs vues se dérivent respectivement du
relevé le plus proche et du cours du fleuve, puis entrent dans la carte au
moment où le monde la lit. La **puissance** et la **maison** dont relève une
cellule sont pareillement des vues dérivées, jamais un second identifiant
spatial stocké. Le nombre et les surfaces des **lieux** se dérivent de la
surface de la cellule ; ses lieux portent désormais leur population et leur
panier sur `Cell`. Le tick lit la pluie et la crue dans la carte, jamais dans
leurs vues ; il ne consomme ni la vue des provinces, ni celle des puissances,
ni celle des maisons. Il lit les surfaces des lieux à la consommation pour
limiter la distribution intérieure, puis remet leurs états d'accord avec
les totaux de la cellule à la fin.

L'ordre fait foi dans `sim/engine.py`, fonction `tick()`. Ce résumé le suit ;
en cas d'écart, c'est le code qui a raison et ce fichier qui a une dette.

## Ce que le moteur ne fait pas encore

La carte, telle que le monde la lit, porte quatre couches — relief, climat,
gisements, pluie. **Le tick les joue toutes les quatre.** Le snapshot le dit
lui-même, couche par couche.

Ce n'est pas une déclaration, c'est une **mesure**. Pour chaque couche, le
snapshot charge deux mondes identiques, en altère franchement la couche dans
l'un **avant l'amorçage**, joue trois ticks avec la même graine et compare
l'état obtenu. Différent : le moteur lit la couche. Identique au bit près :
il ne la lit pas.

Conséquence voulue, et déjà vérifiée trois fois : le jour où le tick a consommé
le relief, puis le climat, puis les gisements, `utilisee_par_le_moteur` est
passé à `true` tout seul. Personne n'a eu de constante à retourner, et personne
ne peut la retourner sans que le moteur ait changé.

**Ce que la sonde ne peut pas voir.** Elle altère les couches numériques en
**multipliant** leurs valeurs, sauf la pluie qu'elle **remplace par zéro**.
Elle est donc aveugle à toute lecture invariante sous l'altération choisie —
un rapport entre deux grandeurs multipliées ensemble, par exemple. C'est une
limite de l'instrument : un `false` signifie « la sonde n'a rien vu », pas
« le moteur ne lit rien ».

Ce que le monde ne sait toujours pas faire, et qu'aucun lot n'a encore ouvert :

- **organiser la fabrication.** Les matières premières sont transformées sur
  place, sans atelier, sans métier et sans bras affectés ; les objets produits
  ne sont pas consommés.
- **répartir le travail.** Les habitants ont un métier, mineur ou paysan.
  Naissances, morts et départs suivent les métiers ; le tick ne les lit que pour
  la récolte. La part minière retire déjà des bras aux champs ; les
  changements de métier ne sont pas encore simulés.
- **naviguer.** Voir « La mer : la façade que le moteur ne lit pas ».
- **investir.** Aucune route, aucun pont, aucun port, aucun ouvrage : rien dans
  le monde ne se construit, et aucune capacité de transport ne s'améliore.
- **tenir un prix.** Il n'y a ni monnaie, ni marché, ni salaire, ni propriété.
  Le commerce déplace des kilogrammes vers qui en manque, gratuitement.
- **descendre sous la cellule pour les calculs.** Les lieux portent habitants
  et paniers, mais le tick calcule toujours à l'échelle de la cellule : les
  surfaces et chemins limitent ce que le bourg atteint à la consommation,
  sans lire ses stocks persistés. Pas de mouvement propre aux lieux, de
  familles, de personnes ni de quartiers. Le plan peut porter des bâtiments,
  mais ils ne font rien.
- **décrire un calendrier complet.** La date dérivée ne dit que l'année et le
  rang du jour dans cette année : elle ne porte ni mois, ni semaine, ni fête.

## Le mur qui sépare la couche 1 de la couche 2

Une ville est un endroit qui **ne produit pas ce qu'il mange**. Tant qu'aucun
endroit du monde ne peut être nourri par ce qu'on lui apporte, la couche 2
n'est pas atteignable et un lot qui définirait un bourg porterait sur un
phénomène que le moteur ne peut pas produire.

**Ce mur a été baissé par le lot 043, il n'est pas levé.** Avant lui, la
capacité d'une arête valait un convoi de mulets par jour, quelle que soit
l'arête, contre une cellule médiane de plusieurs milliers de kilomètres carrés
— trois ordres de grandeur d'écart. Depuis, la capacité dérive de la longueur
de frontière partagée, et l'écart se compte en unités, plus en milliers.

Mesuré le **2026-08-30** sur `master`, et à rejouer plutôt qu'à croire :
**aucune cellule du monde ne peut couvrir sa consommation par ce que ses arêtes
laissent entrer**, et la mieux dotée n'en couvrirait qu'environ la moitié —
en supposant, ce qui est faux, que toutes ses voisines aient ce surplus à
donner. Sur une année jouée, le commerce déplace moins d'un centième de ce que
le monde mange.

La commande qui donne cet état. Elle ne porte aucune cible : c'est le rapport
lui-même qui se lit, et il vieillit à chaque lot de transport.

```bash
py -c "
import statistics
from collections import defaultdict
from sim.world import World
from sim.engine import _capacite_transport_arete_kg
from sim import constants as C
w = World.charger(0)
ration = C.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
capa = defaultdict(float)
for e in w.adjacency:
    a, b = e.get('a'), e.get('b')
    if a in w.cells and b in w.cells:
        cap = _capacite_transport_arete_kg(w, a, b)
        capa[a] += cap; capa[b] += cap
ratios = [capa[cid] / (c.population * ration)
          for cid, c in w.cells.items() if c.population > 0]
print('cellules', len(w.cells))
print('nourrissables_par_import', sum(1 for r in ratios if r >= 1.0))
print('couverture_par_import_mediane', statistics.median(ratios))
print('couverture_par_import_maximale', max(ratios))
"
py -m sim --ticks 365 --seed 0 --json
```

**Ce que le mur produit, et qui se vérifie en jouant le moteur : rien ne
concentre la population.** Ni une natalité conditionnée à la satiété, ni une
migration qui fuit la famine ne font monter la densité d'une cellule au-dessus
de la densité médiane de départ. Le rapport entre la cellule la plus dense et
la médiane monte bien au fil d'une année — mais par le bas, parce que les
mauvaises cellules se vident, pas parce qu'une bonne se remplit. Chaque fois,
les arrivants dépassent ce que leur nouvelle cellule cultive, et rien ne peut
leur apporter la différence.

**Ce qui reste à faire pour lever le mur, dans l'ordre des données
disponibles :**

1. **La mer.** La carte porte une façade maritime pour trois cellules sur
   quatre, et le moteur ne la lit pas du tout. Voir la section suivante. C'est
   la plus grosse donnée de transport non lue du dépôt.
2. **Les routes.** Une route concentre un flux là où une frontière perméable le
   diffuse : c'est la forme de transport qu'une ville exige. **La carte n'en
   porte aucune**, et le moteur n'a ni investissement, ni travail, ni monnaie
   pour en faire naître. Ce n'est donc pas un lot `sim/` aujourd'hui — c'est
   une décision de modèle qui n'a pas été prise, et elle est déclarée ici comme
   absente plutôt que devinée (règle 10).

## La mer : la façade que le moteur ne lit pas

L'adjacence de la carte figée porte deux sortes d'arêtes, distinguées par leur
champ `kind` :

- `land-land` — deux cellules du monde qui se touchent. Ce sont les seules que
  `sim/` lit aujourd'hui.
- `land-sea` — une cellule du monde et **la mer**. Elles portent, comme les
  autres, la longueur de frontière partagée `shared_length_m`, c'est-à-dire la
  longueur de façade maritime de la cellule.

Trois faits, mesurés le 2026-08-30 et à rejouer plutôt qu'à croire :

- la carte compte **plus de kilomètres de côte que de frontières terrestres** ;
- **trois cellules sur quatre** touchent la mer ;
- **plus d'une cellule sur trois n'a aucun voisin terrestre.** Elle ne touche
  que la mer. Dans le moteur d'aujourd'hui, elle ne peut donc ni recevoir un
  kilogramme, ni en donner, ni être quittée par un migrant : c'est une boîte
  fermée, et rien ne le signale.

```bash
py -c "
import collections, json
doc = json.load(open('data/world-1400.json', encoding='utf-8'))
ids = {c['cell_id'] for c in doc['cellules']}
adj = doc['adjacence']
print('kinds', collections.Counter(e['kind'] for e in adj))
deg = collections.Counter()
for e in adj:
    if e['a'] in ids and e['b'] in ids:
        deg[e['a']] += 1; deg[e['b']] += 1
print('cellules', len(ids))
print('sans_voisin_terrestre', sum(1 for c in ids if deg[c] == 0))
print('noeuds_hors_monde', {x for e in adj for x in (e['a'], e['b'])} - ids)
"
```

**Ce que la carte ne porte pas, et qu'il ne faut pas inventer.** Toutes les
arêtes maritimes touchent **un seul et même nœud** — un identifiant qui n'est
pas une cellule du monde. Il n'existe donc, dans la carte, **aucune liaison
d'un port à un autre port**, et aucune distance en mer. La carte dit « cette
cellule touche la mer, sur cette longueur », et rien de plus.

Conséquence de modélisation, à connaître avant d'écrire un lot maritime : la
seule topologie que la carte autorise est un **bassin commun** — on expédie
vers la mer, on puise depuis la mer — et non un réseau de routes maritimes.
Dans un bassin, Venise et Bruges sont à égale distance l'une de l'autre. C'est
une limite de la donnée, déclarée ici pour que personne ne la prenne pour une
décision de modèle ; le jour où la carte portera une adjacence
port-à-port, elle tombera sans que le reste bouge.

## Ce qu'est une ville, à l'échelle d'une cellule

Cette section tranche une question que le dépôt avait laissée ouverte. Elle est
écrite **avant** tout brief de couche 2, et c'est d'elle qu'ils découlent.

### Le problème d'échelle

`VISION.md` pose la hiérarchie Monde → Pays → Province → **Ville** → Quartier →
Bâtiment → Famille → Personne. Mais une cellule de ce monde couvre plusieurs
milliers de kilomètres carrés et compte des dizaines de milliers d'habitants :
c'est une **région**, pas une ville. Aucune ville médiévale ne fait cette
taille. « Une cellule est une ville » est donc faux à l'échelle, et « une ville
est un groupe de cellules » ferait de la ville quelque chose de plus grand
qu'une province.

Deux lectures étaient possibles, et le dépôt n'en avait retenu aucune :

- **A — la ville est une cellule qui importe sa nourriture.** C'est le cadrage
  du lot 043. Il a l'avantage d'être physique : une ville est un endroit qui ne
  produit pas ce qu'il mange.
- **B — la ville est une concentration *dans* la cellule.** La campagne de la
  même cellule nourrit son bourg.

### La décision : B

**Le bourg d'une cellule est la part de ses habitants qui ne tire pas sa
nourriture de ses champs.** La campagne de la même cellule les nourrit.

Trois raisons, dans l'ordre où elles pèsent :

1. **A n'est pas mesurable aujourd'hui, et ne le sera pas bientôt.** Voir « Le
   mur » : aucune cellule ne peut couvrir sa consommation par ses importations,
   et ce qui lèverait le mur — les routes — n'existe ni dans la carte ni dans
   le moteur. Un critère d'acceptation fondé sur A serait invérifiable.
2. **B tient à l'échelle.** Une région de plusieurs milliers de kilomètres
   carrés contient évidemment un bourg et sa campagne. C'est la seule des deux
   lectures qui décrive quelque chose de vrai à la taille de la cellule.
3. **B ne crée aucune seconde clé spatiale.** Le bourg est une **vue dérivée**
   de la cellule, comme la province. Il n'est jamais un champ
   stocké, jamais un `ville_id`, jamais une entité que le tick fait évoluer.

### D'où vient la donnée

Des **foyers par métier** : le bourg compte tous les habitants dont le métier
n'est pas « paysans », et les champs comptent le reste. Des paysans seuls
donnent un bourg de zéro, même sur de riches gisements. La vue lit une copie
par `lire_habitants_par_metier` et ne modifie jamais la cellule.

Sans métiers calculés (lecture `-1`), la vue appelle `metiers_d_amorcage`,
dans `sim/foyers.py`, comme `World.charger`. Cet amorçage A donne aux mineurs
`int(population × part_miniere_de(gisements, facteurs_richesse_extraction()))`
et aux paysans le reste ; seuls les comptes strictement positifs sont rendus.

À l'amorçage, la vue et le moteur comptent les mêmes personnes. Ensuite, les
naissances, morts et migrations se répartissent au prorata des métiers,
tandis que le moteur relit la part minière : un **écart** apparaît. Mesuré le
03/10/2026 sur la graine 0, il touche 10 des 25 cellules minières après un tick
(une personne au plus), puis les 25 après 30 ticks (15 personnes au plus).
Aucune cellule sans part minière ne s'écarte. Le rang 0 que nourrit la
distribution intérieure reste la part minière du moteur, pas le bourg de la
vue. Réconcilier les deux demanderait de faire lire les métiers par le tick.

Le nom « bourg » est délibérément plus large que le mécanisme qui le porte : le
jour où un second métier existera, la vue le comptera sans être réécrite. Cela
n'autorise personne à inventer ce second métier en même temps que la vue.

### Ce qui se refuse plutôt que se devine

- **Villes historiques nommées.** `data/villes-1400.json` porte une table
  non exhaustive de niveau 1, avec point et population sourcés. À l'amorçage,
  `sim/villes.py` attribue chaque point à un polygone de cellule ; un point
  hors carte reste explicitement hors carte. Cette ville est distincte du
  bourg dérivé des métiers : elle ne crée aucun métier ni champ sur `Cell`.
- **Aucun `city_id`, `ville_id` ni `bourg_id`.** `cell_id` reste la seule clé
  spatiale (mode de défaillance n° 1).
- **Aucun seuil qui « fait » une ville.** Poser un drapeau au-dessus d'un
  nombre d'habitants serait une règle de gameplay, pas une règle de monde.
  Le bourg n'est pas déclaré : il est **compté**.
- **Un échantillon vide échoue**, il ne rend pas zéro bourg en silence.

### Le niveau de fidélité, et ce que la décision coûte

La part du bourg est de **niveau 2** : plausible, générée, jamais sourcée. Une
répartition locale surprenante n'est pas un défaut historique et n'ouvre ni
correctif, ni brief.

**Ce que B coûte, dit franchement : un seul panier reste partagé dans la
cellule.** La gratuité prend fin pour le bourg : sa part locale et la capacité
des chemins limitent ce qu'il peut manger, selon « La distribution à
l'intérieur de la cellule ». Les pertes et le délai ne sont pas simulés ; la
distribution entre les lieux des champs reste gratuite.

### Ce que le moteur ne fait toujours pas

La vue du bourg compte les foyers par métier ; le moteur garde la part minière.
Le bourg ne donne ni quartiers, ni personnes, ni salaires, ni marchés,
ni prix, ni États. Son plan peut porter des rues et des bâtiments,
mais ils ne font rien. La vue du bourg ne décide
rien et le tick ne la consulte pas : il calcule la part minière et lit les
lieux pour appliquer « La distribution à l'intérieur de la cellule ».

## Déclaration explicite

Le peuplement rural amorcé par cellule reste un **proxy paramétrique** de
niveau 2. Les populations des villes nommées sont des estimations historiques
de niveau 1, datées, sourcées et incertaines. Aucun stock alimentaire initial
n'est attesté : la réserve ordinaire et le grenier urbain sont des proxies de
niveau 2, déclarés comme présents avant le début de la partie. Le défaut
d'eau du Nil demeure : placer Le Caire et Alexandrie ne crée pas de crue.

Les paramètres ci-dessous sont des valeurs d'ordre de grandeur plausibles pour
une simulation médiévale/proto-moderne (1400-1900). Ils peuvent être calibrés
à tout moment par un brief ultérieur disposant de données historiques réelles.

---

## La base de temps

### Constante centrale

```
TICK_DURATION_DAYS = 1
```

Un tick représente **1 jour calendaire**. Toutes les constantes temporelles
ci-dessous sont dérivées de cette valeur — aucune d'elles ne contient de
littéral de durée indépendant.

**Justification** : le jour est la plus petite unité de temps agronomique
pertinente (rotation des convois, consommation alimentaire quotidienne, cycle
de production journalier). Un tick-jour permet une calibration directe avec
les sources historiques (rations, rendements annuels ÷ 365).

### L'année calendaire et le rang du jour

```
CALENDAR_DAYS_PER_YEAR = 365
jour = (numero_tick × TICK_DURATION_DAYS) modulo CALENDAR_DAYS_PER_YEAR
```

Le monde porte `ticks_ecoules`, nul à l'amorçage, sérialisé et augmenté de un
à la fin de chaque tick réussi. Le rang du jour dans l'année et l'année se
**dérivent** de ce compteur par `date_de_tick`, depuis `ANNEE_INITIALE = 1400` ;
la date elle-même n'est pas stockée. Lorsqu'un `numero_tick` est fourni, le
tick refuse de jouer s'il diffère de `ticks_ecoules`. Le rang du jour détermine
le facteur de saison.

Conséquence à connaître avant d'écrire un lot : **un appelant qui ne compte pas
ses ticks n'a pas de date à donner au moteur.** Ce que le tick fait alors n'est
pas « le premier jour de l'année » — voir « Les trois régimes de production ».

---

## Population initiale par cellule

### Formule

```
population_rurale = max(0, int(population_soutenable_de(cellule)
                               × PART_SOUTENABLE_AMORCEE × variation))
population = max(population_rurale, somme_des_villes_contenues)
```

où `variation = rng.uniform(SEED_POPULATION_VARIATION_LOW, SEED_POPULATION_VARIATION_HIGH)`.
`population_soutenable_de` se dérive de l'unique formule de production, au
rendement et à la saison moyens.

### Paramètres

| Constante | Valeur | Unité | Justification |
|---|---|---|---|
| `PART_SOUTENABLE_AMORCEE` | 0.8 | part | Marge sous le plafond physique pour absorber les ticks sous la moyenne |
| `SEED_POPULATION_VARIATION_LOW` | 0.9 | — | Variation minimale autour de la densité nominale (±10 %) |
| `SEED_POPULATION_VARIATION_HIGH` | 1.1 | — | Variation maximale autour de la densité nominale (±10 %) |

**Conséquence à connaître : le monde démarre selon ce qu'il nourrit.** La
population rurale initiale suit le relief, la saison moyenne, la part laissée à
l'agriculture par les mines et le `facteur_eau`. Le désert s'amorce presque
vide ; la variation de plus ou moins dix pour cent ne remplace pas cette
géographie, elle s'y applique. Les villes historiques peuvent dépasser la
capacité nourricière locale ; leurs habitants ne s'ajoutent pas au proxy
rural, ce qui évite un double compte. Plusieurs villes dans une cellule se
cumulent. Leur plancher ne s'applique qu'une fois, à l'amorçage.

### Déterminisme

Deux appels à `World.charger(rng_seed=K)` avec la même graine `K` produisent
des populations initiales byte-identiques, car `rng = random.Random(rng_seed)`
initialise un générateur pseudo-aléatoire isolé (jamais de source globale).

---

## Les foyers par métier

À l'amorçage A, une fois la population fixée, villes comprises, les mineurs
valent `int(population × part_miniere_de(gisements, facteurs_richesse_extraction()))`.
Les gisements viennent de la carte de la cellule ; les paysans sont le reste.
`Cell.habitants_par_metier` conserve seulement les métiers dont le compte
est strictement positif ; une cellule vide porte `{}`. Leur somme est
exactement la population. `cell_id` reste la seule clé spatiale.

`TAILLE_FOYER = 5` est une règle de **niveau 2**, plausible, jamais sourcée.
`sim/foyers.py` relit cette taille à chaque rangement et rend un `Foyers`
figé : taille, foyers complets, personnes du dernier foyer incomplet.
Cent personnes donnent vingt foyers complets ; cent trois ajoutent un
dernier foyer de trois personnes. La désagrégation rend le nombre exact.

Une écriture directe de la population, hors du tick, passe par `repartir` :
chaque métier reçoit `N × compte // somme`, puis le reste va au métier le
plus nombreux (nom le plus petit en cas d'égalité). Une population inchangée
garde ses comptes ; sans métier, les nouveaux habitants sont paysans. Les
comptes nuls disparaissent.

Une cellule construite sans métiers les déclare non calculés : la lecture
et la clé sérialisée `foyers` rendent `-1`, même après écriture de la population.
Sinon, la sérialisation porte par métier les personnes, les foyers complets
et le dernier foyer. Une somme initiale incohérente, un nom vide, un compte
nul, négatif, booléen ou non entier sont refusés par `FoyersInvalides`.
Sont aussi refusés une population écrite négative ou non entière sur une
cellule amorcée, un rangement négatif ou non entier, une taille non entière
ou inférieure à un et un foyer négatif ou dont le dernier atteint la taille.

Naissances, morts, départs et arrivées du tick se répartissent au prorata
des métiers, plus forts restes d'abord. Chaque métier reçoit d'abord
`n × compte // somme`, en calcul entier. Les personnes qui restent vont
une à une aux métiers dont le reste `n × compte % somme` est le plus fort.
À reste égal, le nom de métier le plus petit passe d'abord. Un mort parmi
50 mineurs et 950 paysans est un paysan ; deux morts parmi 5 et 5 font un
mineur et un paysan ; un seul mort parmi les mêmes est un mineur. Le
migrant ne garde pas son métier. Une cellule sans métier accueille des
paysans.

**Le tick ne lit les métiers que pour la récolte**.
Les km² cultivés valent `area_km2 × facteur_relief × facteur_eau × facteur_agricole`
(sans carte : `area_km2`), sans facteur saisonnier. Ils demandent
`km² cultivés × BRAS_AUX_CHAMPS_PAR_KM2` bras. Le facteur de bras vaut
`min(1, paysans / bras_requis)` ; les mineurs ne comptent pas et la part
minière reste appliquée. Sous le seuil, chaque paysan retiré enlève sa part
de récolte ; au-dessus, le facteur vaut exactement 1 et rien ne change.
Métiers non calculés (`-1`) ou bras requis nuls : facteur 1, récolte inchangée.
La règle est de **niveau 2**, plausible, jamais sourcée.
`BRAS_AUX_CHAMPS_PAR_KM2 = 0,1` est choisie basse pour que le monde mesuré
ne bouge pas : sur 365 ticks, graine 0, le minimum de paysans par km² cultivé
vaut 0,291 sans numéro de tick et 0,248 avec. Ce n'est pas une densité agricole
réaliste ; elle sera revue quand un geste retirera des bras aux champs.
En famine, les paysans morts ou partis peuvent réduire la récolte : la famine
peut s'aggraver d'elle-même.
L'extraction garde son calcul de part minière ; la vue du bourg compte les métiers.
L'amorçage A est partagé par le chargement et la vue dans `metiers_d_amorcage`.
Âge, sexe, parenté et logement restent de niveau 3, non simulés.

`GET /lieu?cell=X` porte `foyers` : par métier, trié par nom, ses
`personnes` et son nombre de `foyers`, dernier foyer incomplet compris
(10 974 mineurs font 2 195 foyers). Des métiers non calculés publient
`"foyers": -1`, jamais un dictionnaire deviné ; une cellule amorcée vide
publie `{}`. Ces octets sont construits dans `EtatPublie` avec la
photographie du tick, dans le même appel que la population et les stocks :
une lecture de `/lieu` donne toute la cellule au même tick et ne consulte
pas le monde mutable. `/monde` ne les porte pas et reste léger ; le snapshot
de la CLI n'est pas touché.

## Le panier de marchandises

Le stock d'une cellule n'est pas un nombre : c'est un **panier**,
`Cell.stocks`, qui associe un nom de marchandise à des kilogrammes.

La nourriture y est une entrée comme une autre, sous la constante nommée
`MARCHANDISE_NOURRITURE` ; elle est seulement la seule que quelqu'un mange
(voir « Le commerce entre cellules »).

### Absence contre zéro

Deux états qu'il ne faut jamais confondre, et que le panier distingue :

| état du panier | ce que rend `lire_stock_marchandise` | ce que ça veut dire |
|---|---|---|
| la marchandise n'est pas une clé | `-1.0` | non calculé : cette cellule n'a jamais vu cette marchandise |
| la marchandise vaut `0.0` | `0.0` | **mesure réelle** : il y en a eu, il n'y en a plus |

C'est la règle 8 appliquée au stock : la sentinelle « non calculé » du projet
est `-1`, jamais `0`. Les deux seuls accès autorisés sont
`lire_stock_marchandise` et `ecrire_stock_marchandise`, définis dans
`sim/model.py` ; aucun autre module n'indexe `stocks` directement, et un
contrôle le vérifie.

`Cell.food_stock_kg` subsiste comme **propriété** déléguant à ces deux accès.
Ce n'est pas un champ : c'est le nom historique de l'entrée nourriture du
panier.

---

## Stock alimentaire initial

### Formule

```
réserve_ordinaire = population_finale × ration × INITIAL_FOOD_RESERVE_TICKS
manque_kg = max(0, population_finale - population_soutenable_de(cellule, carte)) × ration
grenier_urbain = manque_kg × RESERVE_VILLES_TICKS  # seulement si la cellule porte une ville
food_stock_kg = réserve_ordinaire + grenier_urbain
```

Le stock ordinaire couvre cinq ticks de consommation normale, y compris dans
les cellules urbaines. `RESERVE_VILLES_TICKS = 30` est fixé avant mesure :
environ un mois de manque donne du temps aux échanges, sans promettre un an
de survie. Le supplément n'existe que pour une cellule portant une ville et
dépassant sa capacité locale. Son origine est une réserve antérieure à 1400,
non une production du premier tick. Le commerce peut l'exporter ; rien ne la
réapprovisionne automatiquement.
Le total urbain est arrondi à la précision en kilogrammes de la photographie
du monde (`SNAPSHOT_FLOAT_DECIMALS`), pour que le stock lu et le stock exporté
portent exactement la même valeur ; les cellules sans ville gardent leur
amorçage antérieur.

Invariant d'amorçage : toutes les cellules mangent sans faim ni dette au
premier tick ; celles sans ville restent en outre sous leur plafond local et
conservent exactement leur réserve de cinq ticks. Après ce premier tick,
aucune absence de famine n'est garantie.

C'est la **seule** marchandise présente au panier d'une cellule à l'amorçage.
Toutes les autres y entrent par l'extraction.

### Paramètres

| Constante | Valeur | Unité | Justification |
|---|---|---|---|
| `FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK` | 2.0 × TICK_DURATION_DAYS | kg/personne/tick | Ration journalière médiévale approx. 2 kg (céréales + substituts) × 1 jour/tick |
| `INITIAL_FOOD_RESERVE_TICKS` | 5 | ticks | Réserve de subsistance de 5 jours — suffisante pour absorber 2–3 mauvaises journées consécutives sans mort immédiate, sans masquer le comportement de long terme |
| `RESERVE_VILLES_TICKS` | 30 | ticks | Proxy de niveau 2 : un mois environ de manque local pour laisser agir les échanges |

---

## Le rendement agricole et sa variabilité

### Formule (par tick)

```
yield_factor = rng.uniform(RNG_YIELD_LOW, RNG_YIELD_HIGH)
duree_jour   = duree_jour_h(jour, solstice_ete_h, solstice_hiver_h)  # de la cellule

food_produced = area_km2 × FOOD_PRODUCTION_KG_PER_KM2_PER_TICK × yield_factor
                × facteur_relief(classe de relief de la cellule)
                × facteur_eau(pluie_mm_par_an + crue_mm_par_an de la cellule)
                × facteur_saison(duree_jour)
                × facteur_agricole(1 − part minière) × facteur_bras
```

Le relief, l'eau, la saison et la part minière sont lus dans la carte. Une
cellule dont la carte ne porte pas ces données ne se voit pas attribuer une
valeur par défaut — le moteur refuse, par `ReliefInvalideError`,
`PluieInvalideError`, `CrueInvalideError` ou `ClimatInvalideError` (règle 10 :
l'absence ne s'invente pas en silence). Pour la pluie et la crue, il refuse
aussi `None`, les booléens, les valeurs non numériques, non finies ou
négatives ; zéro reste une mesure.

**Il n'y a qu'une seule formule de production alimentaire dans `sim/`.** Le
tick lui passe un rendement tiré au sort ; le plafond de survie lui passe le
rendement moyen. À bras suffisants, le plafond suit donc ce que le monde
produit vraiment, et c'est ce qui l'a fait suivre tout seul le
jour où le relief, puis la saison, ont modulé le rendement.

Le facteur de bras s'applique uniquement aux deux maillons de production du
tick. Le plafond de survie et la production moyenne restent la récolte à bras
suffisants : le facteur ne peut que l'abaisser, donc le plafond reste une borne
supérieure. L'amorçage ne dépend pas des métiers et ne forme pas de cercle.

### Paramètres

| Constante | Valeur | Unité | Dérivation |
|---|---|---|---|
| `FOOD_PRODUCTION_KG_PER_KM2_PER_TICK` | 18.0 × TICK_DURATION_DAYS | kg/km²/tick | Proxy annuel : ~6 570 kg/km²/an (rendement brut médiéval ~1 800 kg/ha à 36 % de surface cultivée, référence Slicher van Bath 1963) ÷ 365 jours/an × 1 jour/tick ≈ 18.0 |
| `RNG_YIELD_LOW` | 0.5 | — | Facteur multiplicatif minimum : mauvaise année (sécheresse, gel) à 50 % du rendement nominal |
| `RNG_YIELD_HIGH` | 1.5 | — | Facteur multiplicatif maximum : bonne année à 150 % du rendement nominal |

**Le facteur de relief** — fidélité niveau 2, ordres de grandeur plausibles,
jamais sourcés. La plaine vaut 1 : aucune classe ne produit plus que le
nominal.

| Constante | Valeur |
|---|---|
| `FACTEUR_RELIEF_PLAINE` | 1.0 |
| `FACTEUR_RELIEF_COLLINE` | 0.80 |
| `FACTEUR_RELIEF_MARAIS` | 0.50 |
| `FACTEUR_RELIEF_MONTAGNE` | 0.45 |
| `FACTEUR_RELIEF_HAUTE_MONTAGNE` | 0.15 |

**Le facteur d'eau** — fidélité niveau 2, plausible et jamais sourcée. Un
champ sans eau ne donne rien ; sous le seuil bas, la terre ne nourrit que le
parcours des troupeaux. Entre les seuils, le facteur monte en ligne droite ;
au seuil haut et au-delà, il vaut exactement 1 et ne punit pas l'excès d'eau.
Son plancher est strictement positif parce qu'un désert de 1400 n'est pas
inhabité. La crue annuelle du Nil vaut 600 mm équivalents : elle dépasse le
seuil haut afin qu'une cellule traversée ait un facteur d'eau exactement égal
à 1, quelle que soit sa pluie. Cette valeur est de niveau 2, plausible et
jamais sourcée. La crue est tout ou rien à l'échelle de la cellule : toute une
cellule traversée est arrosée, même au-delà de la vallée réelle ; cette
anomalie de niveau 2 est déclarée.

| Constante | Valeur | Sens |
|---|---|---|
| `PLUIE_SANS_CULTURE_MM` | 250.0 | À égalité ou dessous, pas de culture pluviale |
| `PLUIE_PLEINE_CULTURE_MM` | 400.0 | À égalité ou dessus, l'eau ne limite plus |
| `CRUE_EQUIVALENT_PLUIE_MM` | 600.0 | Eau laissée aux champs par la submersion annuelle du Nil |
| `FACTEUR_EAU_PLANCHER` | 0.05 | Nourriture tirée du parcours des troupeaux |

**Le facteur de saison** — fidélité niveau 2 également. Il compare la durée du
jour de la cellule à l'équinoxe :
`max(0, 1 + SENSIBILITE_SAISON × (duree_jour − DUREE_JOUR_EQUINOXE_H) / DUREE_JOUR_EQUINOXE_H)`.

| Constante | Valeur | Unité | Dérivation |
|---|---|---|---|
| `DUREE_JOUR_EQUINOXE_H` | 12.0 | h | Niveau 1 : douze heures partout, à l'équinoxe |
| `SENSIBILITE_SAISON` | 0.5 | — | Sensibilité du rendement à l'écart de durée du jour ; niveau 2 |
| `JOUR_SOLSTICE_ETE` | 172 | rang | Solstice d'été ; celui d'hiver s'en dérive par une demi-année |

Le plancher à zéro n'est pas un paramètre de calibration mais un **invariant
physique** : une cellule ne produit jamais une quantité négative.

### Les trois régimes de production

`tick(world, rng, numero_tick)` produit de trois façons, selon ce que
l'appelant lui donne. C'est à connaître avant d'écrire un lot qui appelle le
tick : deux de ces régimes ne jouent pas la saison du jour.

| ce que reçoit le tick | ce que joue la production |
|---|---|
| un monde sans carte | ni relief, ni eau, ni saison — le nominal seul |
| une carte, **pas** de `numero_tick` | le relief, l'eau et le facteur de saison **moyen sur l'année** |
| une carte **et** un `numero_tick` | le relief, l'eau et la saison du jour dérivé du numéro de tick |

Le deuxième régime est le piège : un appelant sans compteur n'obtient pas
« le premier jour de l'année », il obtient une année moyennée. C'est un choix
et non un défaut — une mesure qui ne compte pas les ticks ne doit pas hériter
d'un mois d'hiver arbitraire — mais un lot qui mesure la production doit dire
lequel des trois régimes il fait jouer.

### L'équilibre que ces valeurs produisent

Le monde amorce une part de la population que sa production moyenne peut
nourrir. Relief, eau et part minière abaissent ensemble ce plafond, sans
qu'aucune densité soit posée à part. La variabilité `[0.5, 1.5]` crée ensuite
des ticks de surplus qui alimentent le commerce et des ticks de manque qui
créent de la dette.

La saison, elle, ne creuse rien **sur l'année** : `facteur_saison_moyen_annuel`
vaut 1 pour une cellule dont les deux solstices sont symétriques autour des
douze heures d'équinoxe, ce que la carte figée donne aujourd'hui. Elle déplace
la récolte à l'intérieur de l'année — creux d'hiver, pic d'été — sans changer
le total annuel. Cette moyenne est **calculée jour par jour**, jamais supposée
égale à 1 : le jour où la carte porterait des durées dissymétriques, le moteur
suivrait sans qu'on y touche.

C'est voulu — un monde qui démarre à l'équilibre exact ne montre ni famine ni
commerce. Aucun chiffre mesuré n'est cité ici : voir « Ce qui dit que le monde
vit », plus bas, et `py -m sim --ticks 20 --json` pour l'état du jour.

---

## La fabrication

Au début du tick, sur le panier d'ouverture, chaque marchandise présente autre
que la `nourriture` et l'`objet` est une matière première à façonner.

```
matiere_consommee = stock_ouverture × TAUX_FABRICATION_PAR_TICK
objet_produit = matiere_consommee × RENDEMENT_FABRICATION
```

| Constante | Valeur | Unité | Ordre de grandeur |
|---|---|---|---|
| `TAUX_FABRICATION_PAR_TICK` | 0.05 | part du stock/tick | niveau 2, jamais sourcé |
| `RENDEMENT_FABRICATION` | 0.6 | kg d'objet/kg consommé | niveau 2, jamais sourcé |

La fabrication est de **niveau 2**. Elle transforme la matière sur place et
tourne en plus de la mine, de l'agriculture et du reste : aucun atelier,
aucun métier et aucun bras affecté ne la limitent. L'`objet` produit n'est pas
consommé et n'est jamais repris comme matière première.

---

## L'extraction minière

L'extraction suit la fabrication. Elle est la seule source de **matière
première** dans le monde ; la fabrication, jouée avant elle, fait aussi naître
une marchandise en produisant de l'`objet`.

La carte porte, cellule par cellule, une liste de **gisements nommés** de 1400.
Leur emplacement et leur ressource sont de **niveau 1** — ils ont une source.
Ce que le moteur en tire est de **niveau 2**.

### Formule (par gisement, par tick)

```
extraction = population × EXTRACTION_KG_PAR_HABITANT_PAR_TICK × facteur_richesse(richesse)
```

Les extractions d'une même cellule se cumulent **par ressource** : deux
gisements de fer alimentent la même entrée du panier.

| Constante | Valeur | Unité | Ordre de grandeur |
|---|---|---|---|
| `EXTRACTION_KG_PAR_HABITANT_PAR_TICK` | 0.02 | kg/hab/tick | niveau 2, jamais sourcé |
| `FACTEUR_RICHESSE_MAJEURE` | 2.0 | — | niveau 2 |
| `FACTEUR_RICHESSE_NOTABLE` | 1.0 | — | niveau 2 |
| `FACTEUR_RICHESSE_MINEURE` | 0.4 | — | niveau 2 |

### Ce qui se refuse, et ce qui s'ignore

- une **richesse inconnue** — présente mais hors des trois classes dérivées —
  lève `RichesseGisementInvalideError` en nommant la cellule et le gisement ;
- un enregistrement **incomplet** — sans ressource ou sans richesse — est
  ignoré sans erreur. C'est la sonde du snapshot qui l'exige : elle injecte des
  enregistrements partiels, et le moteur ne doit pas les prendre pour des
  gisements ;
- une **ressource inconnue** est acceptée : le panier n'a pas de liste fermée
  de marchandises.

### La limite d'aujourd'hui

L'extraction est calculée sur la **population entière** : personne n'est
affecté à la mine, elle tourne en plus des champs. C'est exactement ce que le
lot 044 doit défaire, et c'est pourquoi il est le premier lot de la division du
travail. Et ce que la mine sort ne va nulle part : voir la fin de « Le commerce
entre cellules ».

---

## Le déficit alimentaire et la mortalité

### Champ `food_deficit_kg`

La nourriture qui a manqué est une **dette**, pas un oubli. Sentinelle `-1.0`
= non encore calculé (règle 8 : zéro est une mesure réelle, jamais un aveu).

- Si `consommation > stock` après production et commerce :
  `food_deficit_kg += (consommation − stock)` et le stock de nourriture est
  mis à zéro.
- Si la cellule a un surplus, la dette est remboursée par des kilogrammes
  réels — voir « La récupération physique du déficit ».

### La mortalité

```
si food_deficit_kg > 0 et population > 0 :
    deficit_par_tete = food_deficit_kg / population
    taux = min(deficit_par_tete × HUNGER_DEATH_SCALE, MAX_DEATH_RATE_PER_TICK)
    brut   = population × taux + mortality_remainder
    morts  = int(brut)
    mortality_remainder = brut − morts
    population = max(0, population − morts)
```

Les personnes réellement retirées quittent les métiers au prorata. Un métier
tombé à zéro disparaît.

| Constante | Valeur | Unité | Ordre de grandeur |
|---|---|---|---|
| `HUNGER_DEATH_SCALE` | 0.005 | 1/(kg/personne) | 1 kg de dette par tête → 0,5 % de mortalité par tick. Une famine médiévale sévère est documentée à 10–30 % de mortalité annuelle sur les populations les plus touchées, soit 0,03–0,08 %/jour ; ce facteur permet à une dette de 5–10 kg/tête d'atteindre 2–5 % par jour. |
| `MAX_DEATH_RATE_PER_TICK` | 0.10 | — | Plafond de 10 % par tick : pas d'effondrement instantané, même à dette extrême. |

**Il n'y a pas de plancher `max(1, …)`.** Une famine légère ne tue plus au
moins une personne par cellule et par tick : le report de la fraction
(`mortality_remainder`, plus bas) fait ce travail correctement, sans inventer
de mort.

> Les formules antérieures — plancher de mortalité binaire, récupération de
> dette multiplicative `D × (1 − r)`, seuil de coupure `DEFICIT_ZERO_EPSILON` —
> ne sont plus décrites ici. Une formule morte décrite au présent piège le
> lot suivant. Elles sont dans l'historique git, avec les raisons de leur
> retrait dans les messages de commit.

---

## La natalité

Le pendant exact de la mortalité, et la seule façon dont la population
augmente.

```
si penurie_du_tick == 0 et food_deficit_kg == 0 et population > 0 :
    brut       = population × NAISSANCES_PAR_HABITANT_PAR_TICK + natalite_remainder
    naissances = int(brut)
    natalite_remainder = brut − naissances
    population += naissances
```

Les naissances rejoignent les métiers de la cellule au prorata.

| Constante | Valeur | Unité | Ordre de grandeur |
|---|---|---|---|
| `NAISSANCES_PAR_HABITANT_PAR_TICK` | 0.0002 | naissance/hab/tick | niveau 2, jamais sourcé |

**Les deux conditions sont distinctes et toutes deux nécessaires.** La pénurie
du tick dit « on a mangé sa ration aujourd'hui » ; la dette dit « on ne doit
plus rien d'hier ». Une cellule qui vient de manger sa ration mais traîne une
dette ne fait pas d'enfant : elle rembourse d'abord. C'est ce qui empêche une
population de rebondir avant que la famine soit payée.

Le report de fraction (`natalite_remainder`, sentinelle `-1.0`) joue le même
rôle que pour la mortalité : sans lui, une petite cellule rassasiée serait
stérile par arrondi pendant que sa grande voisine croît normalement.

---

## La migration de famine

Dernier maillon du tick, joué sur le monde entier après que tout le reste est
résolu. **Aucun kilogramme ne bouge avec les partants.**

### Qui part

Une cellule n'envoie personne si la **pénurie du tick** — la valeur que la
consommation vient de retourner — n'est pas strictement positive. On ne part
pas d'une cellule qui a mangé sa ration, même endettée : on part de celle qui a
manqué aujourd'hui.

```
brut     = population_instantanée × FRACTION_MIGRANTE_PAR_TICK + migration_remainder
partants = int(brut)
```

| Constante | Valeur | Unité | Ordre de grandeur |
|---|---|---|---|
| `FRACTION_MIGRANTE_PAR_TICK` | 0.01 | — | part de la population d'une cellule affamée qui s'en va en un tick ; niveau 2 |

### Où l'on va

Vers les cellules voisines d'adjacence **dont il reste de la nourriture après
consommation**, pondérées par ce reste.

Le poids d'une destination est son **stock de nourriture post-consommation**,
lu sur un instantané pris avant tout mouvement. Ce n'est pas un surplus
recalculé : le maillon consommation a déjà prélevé la ration et déjà remboursé
la dette, et ce qui subsiste dans le panier est exactement ce qui reste à
manger. Un surplus recalculé à partir de la population aurait compté deux fois
la ration du tick.

**Le poids ne dépend pas de la population de la destination.** Deux voisines
avec le même reste attirent autant, qu'elles soient grandes ou petites : ce qui
attire est ce qu'il y a à manger, pas le nombre de bouches déjà présentes.

La répartition entre destinations est proportionnelle aux poids, en parts
entières, le reliquat allant aux plus fortes fractions, les égalités départagées
par `cell_id` croissant. Personne ne se perd dans l'arrondi.

### L'atomicité

Deux règles, qui font que la migration est un déplacement et non une diffusion :

- **une personne ne traverse qu'une arête par tick** ;
- **une cellule qui reçoit des arrivants n'en envoie pas le même tick.** Les
  départs d'une cellule receveuse sont annulés, pas différés.

Le report de fraction (`migration_remainder`, sentinelle `-1.0`) empêche une
petite cellule affamée d'être immobile par arrondi.

Le solde de la cellule, entrées moins sorties, quitte ou rejoint ses métiers
au prorata. Les arrivants prennent les métiers de la cellule d'arrivée ;
dans une cellule sans métier, ils sont paysans.

---

## Ce qui dit que le monde vit

Il n'y a **pas de prédiction analytique** de la fraction de survivants. Il y a
trois propriétés, mesurées sur le moteur, dans `sim/tests/test_survie.py`.

**1. Le monde ne s'éteint pas et ne nourrit pas plus de monde qu'il ne produit.**

```
plafond = production_moyenne_du_monde / (ration × population_de_départ)
0 < fraction_de_survivants ≤ plafond
```

Le plafond est **dérivé du moteur** : `production_moyenne_kg_par_tick()` appelle
la même et unique formule que le tick emploie, avec le rendement moyen au lieu
d'un tirage. Il ne peut donc pas diverger de ce que le monde produit — et il a
suivi tout seul le jour où le relief a modulé le rendement, sans qu'aucun test
de survie ait à changer.

Ce que son dépassement voudrait dire : la population survivante mange plus que
le monde ne produit, donc des kilogrammes apparaissent ailleurs que dans la
production. Un commerce qui duplique, une consommation qui ne prélève pas, une
dette effacée sans surplus pour la payer : tout cela se voit ici.

**2. La survie répond à la mortalité.** `s(HDS×0.5) > s(HDS) > s(HDS×2)`.

**3. La survie répond à la nourriture.** `s(production) > s(production÷2)`.

La démographie répond aussi à la natalité, par la même méthode : le taux
remplacé en mémoire change la population d'arrivée.

### Pourquoi la direction, et pas la valeur

Le modèle précédent prédisait la valeur **absolue** de la fraction de
survivants : capacité de charge, oscillateur déficit/population, espérance du
manque, trois tolérances dérivées, horizon de 1 000 ticks. Il occupait 262 des
358 lignes de `sim/constants.py`.

Sa dérivation suppose **une** capacité de charge globale, `cap = F × ȳ / C`.
Cette grandeur cesse d'exister dès que la production varie d'une cellule à
l'autre — c'est-à-dire dès le lot du relief, désormais fusionné. Mesuré, en
faisant jouer le relief : la survie tombe à **0,447** contre une prédiction de
**0,797 ± 0,101** — 3,5 fois la tolérance. Le test devient rouge sans qu'aucun
défaut n'existe, et la seule issue commode est d'élargir la tolérance après
avoir vu la mesure. C'est la calibration après mesure, que ce document
interdisait ailleurs.

La garde payée par un vrai défaut est conservée intacte : le critère de survie
ne doit pas être **aveugle aux constantes qui gouvernent la mort** — c'est ce
qu'on reprochait à un critère antérieur, où une famine deux fois plus
meurtrière passait le même contrôle. La propriété n° 2 la tient directement,
sur le moteur, et survit à tout changement du modèle de production. Rouge
prouvé : avec une mortalité qui ignore `HUNGER_DEATH_SCALE`, les trois régimes
rendent la même fraction et le test échoue.

### Sur les valeurs mesurées citées dans ce document

Elles sont datées et elles vieillissent. La règle 12 le dit pour les empreintes
de parité, et vaut ici : **un compteur se cite par son nom, pas par sa valeur.**
Une révision antérieure de ce document affirmait quatre compteurs qui étaient
tous faux, de deux à trente fois, parce qu'ils dataient d'un moteur deux
révisions plus vieux — et ce document est celui d'où les lots sont découpés.

Aucune valeur mesurée n'est donc citée comme une propriété du modèle. Pour
connaître l'état du monde : `py -m sim --ticks 20 --json`.

---

## Le commerce entre cellules

Le maillon commerce transporte **toute marchandise présente dans le monde**,
pas seulement la nourriture. La liste des marchandises jouées est **dérivée**
des paniers du monde à chaque tick, plus la ration alimentaire, dans un ordre
stable — jamais une liste écrite à la main.

### La capacité d'une arête

Elle se calcule à **un seul endroit** du moteur, en deux facteurs qui se
composent :

```
base    = DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK × (shared_length_m / METRES_PAR_KM)
goulot  = min(facteur_transport(relief de a), facteur_transport(relief de b))
capacité = base × goulot
```

| Constante | Valeur | Unité | Ce que c'est |
|---|---|---|---|
| `DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK` | 200.0 × TICK_DURATION_DAYS | kg/km/tick | Niveau 2. Calibré pour qu'une frontière d'un kilomètre rende exactement l'ancienne capacité plate. |
| `METRES_PAR_KM` | 1000.0 | — | Conversion d'unité, pas un réglage. Lue par `metres_par_km()`. |
| `TRADE_CAPACITY_KG_PER_EDGE_PER_TICK` | 200.0 × TICK_DURATION_DAYS | kg/arête/tick | **Repli seul** : employé uniquement par une arête qui ne porte pas `shared_length_m`. Une arête qui la porte n'y touche jamais. |

**Ce que cette forme dit du monde.** Une longue frontière commune laisse passer
plus de convois qu'un contact ponctuel : il y a plus de chemins, plus de gués,
plus de cols. Ce n'est pas une route — le jeu n'a pas de routes — c'est la
perméabilité brute d'une frontière.

**Le facteur de transport du relief** — niveau 2, échelle distincte de celle de
la production : un marais se traverse mal et produit mal, sans coïncidence
garantie entre les deux tables.

| Constante | Valeur |
|---|---|
| `FACTEUR_TRANSPORT_PLAINE` | 1.00 |
| `FACTEUR_TRANSPORT_COLLINE` | 0.70 |
| `FACTEUR_TRANSPORT_MARAIS` | 0.40 |
| `FACTEUR_TRANSPORT_MONTAGNE` | 0.30 |
| `FACTEUR_TRANSPORT_HAUTE_MONTAGNE` | 0.10 |

C'est bien un **goulot**, un `min` et non un produit : franchir une chaîne
coûte le pire des deux bords, pas leur moyenne. Une longue frontière de haute
montagne reste une mauvaise frontière.

**Le refus de deviner.** Une longueur de frontière non numérique — chaîne,
booléen, `NaN` — lève `LongueurFrontiereInvalideError` en nommant les deux
`cell_id`. Une longueur **absente** n'est pas une invalide : elle active le
repli. Une longueur **nulle** est valide et rend zéro : deux cellules qui ne se
touchent qu'en un point ne laissent rien passer, et ce zéro est une mesure.

**Le plafond est partagé entre les marchandises** pour la durée du tick : ce
qu'une arête a laissé passer en blé n'est plus disponible pour le fer. Il n'y a
qu'un seul convoi.

### Besoin, surplus et allocation

Le commerce précède la consommation. Le « besoin » d'une cellule n'est donc pas
sa dette cumulée, mais le **manque prévisible du tick courant** :

```
besoin(c)  = max(0, population_c × consommation_unitaire(marchandise) − stock_c)
surplus(c) = max(0, stock_c − population_c × consommation_unitaire(marchandise))
```

Ces valeurs sont calculées sur un **snapshot immuable** pris avant tout
transfert. Une cellule qui vient de recevoir ne peut pas redistribuer le même
tick : le transport est atomique.

L'allocation est déterministe : demandes triées par `cell_id` receveur
croissant, sources parcourues par `cell_id` croissant, part proportionnelle au
besoin si la somme des demandes dépasse le surplus de la source, puis
**écrêtage côté receveur** — une cellule adjacente à deux sources ne reçoit
jamais plus que son besoin, et l'excédent reste aux sources. Rien n'est créé.

`food_deficit_kg` n'est **jamais** modifié par ce maillon.

### Pourquoi le minerai ne bouge pas

`consommation_kg_par_habitant_par_tick(marchandise)` est le seul endroit du
moteur qui distingue une marchandise d'une autre. Il rend la ration pour la
nourriture, et **zéro pour tout le reste**.

Conséquence : une marchandise que personne ne mange n'a **jamais de besoin**,
donc jamais de demandeur, donc elle ne traverse aucune arête. Le fer extrait
s'accumule dans la cellule qui l'a sorti. Le commerce sait le porter — c'est ce
que le lot 039 a acheté — mais rien ne le réclame.

Ce n'est pas un défaut, c'est une absence déclarée : la fabrication transforme
la matière **sur place** et ne crée donc aucune demande entre cellules ; la
consommation par habitant reste nulle hors nourriture. Il n'y a toujours ni
métier ni prix. Le jour où quelque chose réclamera du fer dans une autre
cellule, le transport suivra sans qu'on y touche.

---

## Le report de la fraction de mortalité

`int(population × death_rate)` arrondit à zéro dès que
`population × death_rate < 1`. Une cellule de 5 habitants en famine totale
produit `5 × 0.10 = 0.5` mort par tick : `int(0.5) = 0`, à chaque tick, pour
toujours. Cinq habitants deviennent immortels par arrondi, tandis que leurs
voisins de 5 000 habitants meurent normalement.

Le champ `Cell.mortality_remainder` (float, sentinelle `-1.0` = non calculé)
conserve la fraction non appliquée :

```py
remainder = cell.mortality_remainder if cell.mortality_remainder >= 0.0 else 0.0
raw = cell.population * death_rate + remainder
deaths = int(raw)
cell.mortality_remainder = raw - deaths
cell.population = max(0, cell.population - deaths)
```

**Borne `N_BOUND_MORT`** : au plafond de mortalité, une cellule accumule au
moins `MAX_DEATH_RATE_PER_TICK` mort par habitant et par tick ; il faut donc au
plus `ceil(1 / MAX_DEATH_RATE_PER_TICK) = 10` ticks pour qu'une mort entière
soit appliquée, quelle que soit la taille de la cellule.

Le même motif sert trois fois — mortalité, natalité, migration — avec un champ
de report par maillon. Ce ne sont pas trois règles : c'est une seule, appliquée
partout où un entier d'habitants sort d'un taux.

---

## Ce que veut dire « affamée »

L'ancien critère incrémentait `hunger_ticks` quand `food_stock_kg <= 0` après
consommation. Une cellule ravitaillée **exactement** à son besoin par le
commerce termine le tick avec un stock nul et un déficit nul : elle a mangé sa
ration. La compter comme affamée confond le garde-manger vide et la
sous-alimentation.

Critère causal : `_apply_consumption` retourne la pénurie du tick en kg
(`shortage = besoin − stock_avant_consommation`, nulle s'il n'y a pas de
manque) et `_update_hunger` n'incrémente que si cette pénurie est positive.
Propriété : `food_stock_kg == 0` et `food_deficit_kg == 0` après consommation
→ `hunger_ticks` non incrémenté.

Cette même valeur de retour — la pénurie du tick — commande aussi la natalité
et le départ des migrants. C'est le signal causal du manque, et il n'y en a
qu'un.

---

## La récupération physique du déficit

`DEFICIT_RECOVERY_RATE_PER_TICK` est **supprimée**. Sa formule,
`food_deficit_kg × (1 − r)`, effaçait 10 % de la dette indépendamment du
surplus réel : un surplus d'un nanogramme effaçait 1 000 kg d'une dette de
10 000 kg. Des kilogrammes disparaissaient sans contrepartie physique
(principe 3 : rien ne se téléporte).

Successeur nommé : `DEFICIT_RECOVERY_RATE_PER_SURPLUS_KG = 1.0` — kilogrammes
de dette remboursés par kilogramme de surplus **réellement consommé** au-delà
du besoin d'entretien. Ratio 1:1.

```py
remboursement = min(food_deficit_kg, surplus_du_tick × ratio)
food_deficit_kg -= remboursement
food_stock_kg = surplus_du_tick − remboursement    # les kg quittent le stock
```

Le ratio est borné à 1.0 dans le moteur : la réduction de la dette ne peut
jamais dépasser le surplus physique du tick, quelle que soit la valeur donnée à
la constante.

**La coupure `DEFICIT_ZERO_EPSILON` est supprimée.** Elle n'avait plus de
travail. Le remboursement est une **soustraction** : `dette − min(dette,
surplus × ratio)`. Quand le surplus couvre, `min` rend la dette elle-même et
la soustraction donne **exactement `0.0`** en IEEE 754 — il n'y a pas d'asymptote
à nettoyer. Tout résidu est donc une dette réelle que le surplus n'a pas payée,
et l'effacer faisait disparaître des kilogrammes sans contrepartie : la même
faute de principe 3 que le seuil avait été écrit pour accompagner.

**Conséquence assumée** : la dette se rembourse vite dès qu'il y a un vrai
surplus, et pas du tout quand le surplus est infime.

---

## La province dérivée et ses centres

Cette section décrit d'où viennent les données de l'agrégation, comment elle
calcule, et ce qu'elle refuse de faire.

### Provenance : des données héritées du jeu, pas des frontières de 1400

Les centres administratifs sont lus dans `data/province-centres-1400.json`. Ce
sont des **données héritées du jeu**, reprises telles quelles et en lecture
seule.

Ce ne sont **pas** des frontières historiques de 1400. Rien ici ne prétend au
statut de source savante, de reconstitution d'époque, ni de découpage
administratif attesté. Le fichier lui-même se décrit comme des
« coordonnées approximatives, corrigeables à vue ». Ces centres sont un
**proxy** : un point de départ commode pour éprouver le mécanisme
d'agrégation, destiné à être remplacé par une source documentée quand le
projet en aura une. Leur nombre n'est pas recopié ici : il est celui du
tableau `coordinates` du fichier, lu à chaque exécution.

De même, le nombre de cellules du monde n'est écrit nulle part dans le code :
il est lu de `data/world-1400.json` et dérivé du chargement par
`World.charger()`.

### Projection : celle que le fichier documente lui-même

Le fichier de centres déclare sa propre projection sous la clé `projection` :
équirectangulaire, `x = lon × cos(mid_latitude)`, `y = −lat`. C'est cette
projection qu'emploie `sim/aggregation.py`, et son paramètre
`projection.mid_latitude` est **lu du fichier** par
`charger_latitude_moyenne()`. Aucune valeur de latitude moyenne n'apparaît
comme littéral dans un corps de fonction — `sim/tests/test_no_hardcoded.py`
parcourt récursivement les modules de `sim/` hors tests et refuse tout
littéral numérique autre que 0, 1 et −1.

Les distances sont comparées **au carré** : même ordre que la distance, sans
racine carrée. La conversion des degrés en radians passe par la bibliothèque
standard (`math.radians`), jamais par un facteur recopié à la main.

### Règle de départage des égalités

Une cellule relève du centre le plus proche d'elle. Si deux centres ou plus
sont à distance **exactement** égale, la cellule relève de celui dont l'`id`
est le **plus petit**.

Cette règle est stable : elle ne dépend pas de l'ordre dans lequel les centres
sont parcourus. La comparaison retenue est
`carré < meilleur` **ou** (`carré == meilleur` **et** `id < meilleur_id`). Un
simple « le premier rencontré gagne » donnerait le même résultat dans un ordre
de parcours et un autre résultat dans l'ordre inverse : le déterminisme serait
espéré, pas prouvé. `sim/tests/test_determinisme.py` monte le cas d'égalité
exacte et l'essaie dans les deux ordres.

### Refus de deviner

Si une cellule chargée par `World.charger()` n'a pas de position dans les
artefacts géographiques, le code lève `PositionCelluleInconnue` en **nommant
la cellule**. Il n'attribue pas de province par défaut et n'écarte pas la
cellule en silence : une couverture obtenue en jetant les cellules gênantes
n'est pas une couverture.

### Zéro mesuré contre sentinelle « non calculé »

Le compteur `cellules_sans_province` doit valoir **0**. Ce zéro est une
**mesure réelle** : le code a bien regardé chaque cellule chargée et n'en a
trouvé aucune sans province. La sentinelle « non calculé » du projet est
`-1`, jamais `0` ; un `0` rapporté ici affirme donc quelque chose, il n'avoue
pas une absence de mesure. La même distinction vaut pour
`cellules_position_absente`, `attributs_dynamiques_sur_cellules` et
`egalites_de_distance_monde_reel`.

### Provinces peuplées : un fait mesuré, pas un plancher

Toute cellule relève d'une province ; l'inverse n'est pas exigé. Un centre
peut n'attirer aucune cellule. Le nombre de provinces peuplées est donc
rapporté tel qu'il sort de la mesure, avec le nombre de centres lus pour
dénominateur. Aucun test n'impose de plancher, et l'algorithme n'est en aucun
cas ajusté pour peupler tous les centres.

### Ce que l'agrégation ne fait pas — et le motif que toute vue recopie

Elle ne modifie aucun objet reçu, n'écrit aucun fichier, et n'ajoute aucun
champ à `Cell`. La vue dérivée (`Regroupement`) vit dans `sim/aggregation.py`,
hors de `sim.model`, parce que `sim.model` contient les entités **persistées**
que le moteur fait évoluer : y déclarer la Province inviterait à la traiter
comme un état stockable, exactement ce que la clé spatiale unique interdit. Le pas de
temps (`tick`) ne consomme pas l'agrégation : la Province est une vue du
monde, pas un acteur économique.

**C'est le motif de toute vue dérivée du projet**, et le bourg le recopiera
sans en changer une ligne : elle vit hors de `sim.model`, elle est pure, elle
refuse de deviner, elle départage ses égalités par `cell_id` croissant, et le
tick ne la lit pas.

---

## La pluie de 1400, vue dérivée

La provenance de cette vue est `data/pluie-releves-1400.json`. Chaque ligne y
associe un point géographique, un cumul annuel moyen et une source publique
nommée. Ces relevés sont de **niveau 1** : ils doivent être justes dans les
grandes lignes et rendre notamment le contraste entre façade atlantique et
désert. Le fichier déclare leur limite essentielle : la pluie de 1400 n'a pas
été mesurée. Les normales climatiques modernes sont une **approximation** du
climat de 1400, pas une mesure historique que le projet prétendrait posséder.

À chaque consultation, `sim/pluie.py` attribue à une cellule le relevé le plus
proche selon la projection déclarée par le fichier. Il appelle la règle unique
de `sim/aggregation.py` : pas d'interpolation, pas de moyenne, pas de correction
par le relief. À égalité exacte, le plus petit identifiant de relevé gagne.
Cette attribution est de **niveau 2** : une cellule étendue ou montagneuse ne
reçoit qu'une valeur et une anomalie locale n'est pas un défaut.

La vue vit hors de `sim.model`, ne pose aucun champ sur `Cell` et se recalcule
sans modifier le monde. À la lecture de la carte figée, `World.lire_carte`
calcule cette vue et ajoute seulement en mémoire `pluie_mm_par_an` à chaque
enregistrement de cellule ; le fichier sur disque reste inchangé. Le moteur
lit ensuite cette valeur dans la carte. La vue refuse une table vide, une
provenance ou une déclaration d'approximation absente, une unité inattendue et
toute valeur inexploitable. Une cellule sans position connue est nommée dans
le refus au lieu d'être écartée ou complétée par défaut. Zéro millimètre reste
une mesure ; une cellule absente de la vue rend `None`, jamais un faux zéro.

Enfin, **la pluie n'est pas l'eau** : l'eau disponible est la pluie plus la
crue. Le delta du **Nil** reçoit presque la même pluie que le désert occidental,
mais le cours du fleuve lui apporte sa crue (voir « Le cours du Nil, vue
dérivée »). Le moteur lit la pluie de la carte, mais pour la vue elle-même, le
tick ne la lit pas.

---

## Le cours du Nil, vue dérivée

La provenance de cette vue est `data/nil-cours-1400.json`. Chaque ligne y
place un point du cours et nomme sa source publique. Ces points actuels sont de
**niveau 1**, justes dans les grandes lignes : le fichier déclare qu'ils ne
prétendent pas restituer les bras du delta en 1400. Leur attribution aux
cellules est de **niveau 2**.

À chaque consultation, `sim/fleuve.py` fait chercher à chaque point son
centroïde de cellule le plus proche avec la règle unique de
`sim/aggregation.py`. Ce sens est l'inverse de celui de la pluie : le point
cherche sa cellule. Il n'y a ni segment interpolé, ni largeur, ni bassin
versant. À égalité exacte, le plus petit identifiant de cellule gagne. La vue,
pure et hors de `sim.model`, refuse une table vide, une déclaration ou une
source absente, une coordonnée inexploitable et toute cellule du monde sans
position connue.

La vallée au sud du Caire est explicitement **hors de la carte**. Lui donner
un point ferait choisir le centroïde de Suez et affirmerait à tort que le Nil
traverse l'isthme. Le fichier déclare donc cette lacune au lieu de la masquer.

Enfin, **le tick ne la lit pas**. À la lecture de la carte,
`World.lire_carte` dérive de cette vue `crue_mm_par_an` pour chaque cellule :
la valeur équivalente de la crue si le Nil la traverse, zéro sinon. Le moteur
lit ensuite cette valeur dans la carte, sans consulter la vue du fleuve.

---

## Les puissances de 1400, vue dérivée

La provenance est `data/puissances-1400.json`. La table couvre l'Ouest,
l'Italie, le Nord, le Centre et l'Orient : Byzance, les Ottomans, les Mamelouks,
le Maghreb et la Russie de Novgorod. Ses 39 puissances et 73 ancres, vérifiées
contre des sources publiques, sont de **niveau 1** : elles doivent être justes
dans les grandes lignes au 1er janvier 1400. La nature `principauté` désigne
une puissance tenue par un duc, un comte ou un prince, comme Milan et la
Savoie ; `empire` désigne Byzance, `sultanat` les Ottomans, les Mamelouks et
les trois puissances du Maghreb, `khanat` la Horde d'Or. Le tracé qui en découle
est de **niveau 2**, plausible et jamais sourcé : il ne restitue ni frontière
réelle, ni enclave, ni suzeraineté.

À chaque consultation, une cellule retient d'abord une ancre contenue dans
son polygone (bord compris, trous exclus). Les points EPSG:4326 des ancres
sont projetés en **EPSG:3035** par `sim/projection.py` : Lambert azimutale
équivalente ellipsoïdale GRS80, latitude authalique de Snyder, origine 52° N
et 10° E, fausse abscisse 4 321 000 m et fausse ordonnée 3 210 000 m.
Cette projection est vérifiée au centimètre sur les 58 villes et les 5 sièges.
Si plusieurs ancres sont contenues, la plus proche du centroïde gagne ; sans
ancre contenue, la plus proche parmi toutes gagne. Les distances gardent la
projection et la latitude moyenne déclarées par la table ; la règle unique
de `sim/aggregation.py` départage une égalité exacte par le plus petit `id`
d'ancre, indépendamment de l'ordre de la table. La puissance est celle de
l'ancre retenue. Les fonctions pures sans géométries gardent la règle du
centroïde seul ; les adaptateurs lisent `world.carte[cell_id]["geometry"]`
et refusent une géométrie absente en nommant la cellule.

La portée mesurée de **4,0 degrés projetés**, environ 440 km, s'applique à
l'ancre retenue, même si elle est contenue dans le polygone. Sur les
596 cellules de la carte figée, 565 sont couvertes et
31 sont non couvertes. Au-delà de la portée, la cellule est explicitement
**non couverte** : elle n'est rattachée à aucune puissance par défaut. Cette
vue donne la cellule de Constantinople à Byzance : celle du point de la ville,
**10374**, et non plus seulement celle au centroïde le plus proche, 10032.
Seule 10374 change : Edirne cède la place à Constantinople ; Byzance passe
de 23 à 24 cellules et les Ottomans de 49 à 48. Venise (25) et Copenhague
(37), les deux ancres hors des polygones de la carte, ne comptent que par
la règle du centroïde. Grenade (16) et Malaga (17) sont dans la même cellule,
10209, qui reste aux Nasrides. Les comptes 565/31 restent inchangés.
Le Caire se situe au sud de la carte, qui s'arrête à 30,45 N : sa cellule
la plus proche relève des
Mamelouks grâce aux ancres d'Alexandrie et de Damiette, sans ancre au Caire.

Les huit `lacunes` déclarent des points nommés et une `raison` : Shetland,
Féroé, Finlande, Hiiumaa, Dalécarlie, Tripolitaine, Cyrénaïque et Oued Righ.
Une cellule non couverte est expliquée par la lacune la plus proche de son
centroïde, dans la même projection et la même portée ; une égalité exacte
se départage par le plus petit identifiant de lacune. Au-delà, sa raison est
`None` et la preuve échoue. Chaque cellule non couverte a une raison, chaque
lacune sert. Une lacune n'attribue aucune cellule à une puissance ; son point
est de **niveau 2**, plausible, jamais sourcé.

Les anomalies mesurées de **niveau 2** sont acceptées : Rhodes donne aux
Hospitaliers les Cyclades orientales, l'est de la Crète et un bout de côte
carienne ; Mistra donne à Byzance l'Attique, les îles Ioniennes et l'ouest
de la Crète. Moscou, Tver, la Horde à Sarai, Kaffa, Sinop, Trébizonde et Damas
sont hors de la carte, sans ancre. Les beyliks libres, les suzerainetés,
les tributs, le siège de Constantinople et l'Église de Bosnie restent de
**niveau 3**, pas simulés.

La vue est pure, recalculée et vit hors de `sim.model`. Elle ne pose rien sur
`Cell`, refuse une position absente en nommant la cellule, et **le tick ne la
lit pas**.

---

## Les maisons de 1400, vue dérivée

La même table `data/puissances-1400.json` déclare 30 maisons, chacune avec
un `id`, un `nom` et une `source` publique qui atteste sa tenure au
1er janvier 1400 : Lancastre, Stuart, Valois, Aviz, Trastamare, Barcelone,
Évreux, Nasrides, Luxembourg, Visconti, Anjou-Durazzo, Savoie, Poméranie,
Jagellon, Paléologue, Osman, Lazarević, Kotromanić, Basarab, Mușat,
Djötchides, Barquq, Hafsides, Zayyanides, Mérinides, Lusignan,
Valois-Bourgogne, Montfort, Wittelsbach et Habsbourg.

Chacune des 29 puissances de nature `royaume`, `principauté`, `empire`,
`sultanat` ou `khanat` désigne une maison connue. Les dix autres se
**déclarent sans maison**, par leur nature `république`, `Église` ou `ordre` :
Archevêché de Trèves, Confédération des cantons suisses, Venise, Florence,
Gênes, Papauté, Ordre teutonique, Novgorod, Pskov et Hospitaliers. Leur ligne
ne porte pas de champ `maison` ; une absence de ce champ sur une autre
nature est refusée. Une maison qui ne tient ni puissance ni ancre est refusée.

Six ancres déclarent une maison de grand vassal différente de celle de leur
puissance : Dijon et Bruges sont tenues par **Valois-Bourgogne**, Nantes par
**Montfort**, Munich et Heidelberg par **Wittelsbach**, Vienne par
**Habsbourg**. Une ancre sans déclaration hérite de la maison de sa puissance,
ou de son absence déclarée de maison. Déclarer une maison inconnue ou déjà
celle de la puissance est refusé. L'ancre du vassal reste une ancre de sa
puissance : la preuve vérifie que la cellule la plus proche de son point
relève de cette puissance et de cette maison.

La maison tenante d'une cellule lit **la même ancre retenue** que sa puissance,
par la fonction commune `ancre_par_cellule` de `sim/puissances.py`. Une ancre
contenue dans le polygone l'emporte ; entre ancres contenues, la plus proche
du centroïde gagne, à égalité exacte le plus petit `id`. Sans ancre contenue,
la règle du centroïde parmi toutes reste celle de `sim/aggregation.py`.
La portée existante s'applique ensuite à l'ancre retenue. Venise et Copenhague,
hors carte, gardent la règle du centroïde ; Grenade et Malaga partagent 10209,
toujours aux Nasrides. La cellule du point de Constantinople, 10374, passe
d'Osman à Paléologue ; 10032 reste à Paléologue, les comptes restent inchangés.
Une cellule non couverte rend `None`, comme une cellule de république,
d'Église ou d'ordre. Toute autre cellule couverte porte la maison de sa
puissance ou d'un vassal ancré dans celle-ci, jamais une maison étrangère.
Sur les 596 cellules figées, **476** sont tenues par une maison, **89** sont
sans maison par déclaration de nature, et **31** sont non couvertes.
Chacune des 30 maisons tient au moins une cellule.

Les attributions aux puissances et aux six villes de vassal sont de
**niveau 1**, vérifiées contre des sources publiques. Leur étendue suit les
ancres : elle est de **niveau 2**, plausible et jamais sourcée. Montfort tient
18 cellules et Valois 13 ; Habsbourg en tient 2. Innsbruck tombe chez
Wittelsbach, Linz en Bohême, Besançon et Lille chez Valois-Bourgogne : ces
anomalies sont acceptées. Luxembourg tient le Saint-Empire, mais aucune de
ses cellules, dont les trois ancres sont tenues par des vassaux ; ses cellules
sont celles de la Bohême et de la Hongrie.

Restent de **niveau 3**, pas simulés : le lien de suzeraineté et l'hommage,
les personnes et la succession des dynasties, Vytautas en Lituanie, Naples
disputée, Édigu derrière le khan, Marguerite derrière Éric, les vassaux sans
ancre (Orléans, Anjou, Berry, Foix, Armagnac, Wettin, Hohenzollern, la Hollande
des Wittelsbach) et les terres d'Empire de Bourgogne.

La vue `sim/maisons.py` est pure, recalculée et vit hors de `sim.model`.
Elle passe par `positions_du_monde`, refuse une position absente en nommant
la cellule et ne pose rien sur `Cell`. **Le tick ne la lit pas** ; la règle
des puissances, leurs ancres et leurs cellules restent identiques.

---

## Les seigneuries de départ, vue dérivée

La table `data/seigneuries-1400.json`, datée du **1er janvier 1400**, déclare
cinq petites seigneuries : le **Duché de Bar** (maison Bar, Robert Ier,
Barrois mouvant relevant de la France), le **Comté de Wurtemberg** (maison
Wurtemberg, Eberhard III, Saint-Empire), le **Despotat de Morée** (maison
Paléologue, Théodore Ier, Byzance), la **Terre des Branković** (maison
Branković, Đurađ, Ottomans) et l'**Uç d'Evrenos** (maison Evrenosoğulları,
Gazi Evrenos Bey, Ottomans). Bar et Wurtemberg sont catholiques ; Morée
et Branković sont orthodoxes ; Evrenos est musulman. Bar désigne ici la
branche de Scarpone. Le projet hospitalier concernant Mistra est postérieur
au départ : la cession de Corinthe est datée de 1400 par la source publique.

Chaque ligne donne un `id`, un `nom`, une `religion` de `RELIGIONS`, le nom
de sa `maison`, l'identifiant de sa puissance `suzerain`, une `source`
publique et son `siege` : nom, latitude et longitude en EPSG:4326, coordonnées
`x_m`, `y_m` en EPSG:3035. Les sièges sont Bar-le-Duc, Stuttgart, Mistra,
Vučitrn et Giannitsa (Yenice-i Vardar). La cellule du siège est dérivée par
`point_dans_geometrie` de `sim/villes.py`, en parcourant les polygones de la
carte dans l'ordre des `cell_id` ; sur une frontière, le plus petit gagne.
Le centroïde le plus proche ne sert jamais à cette attribution. Un siège
hors carte est refusé en nommant la seigneurie et le champ `siege`.
La table refuse les listes absentes ou vides, les identifiants booléens ou
dupliqués, les noms dupliqués, les textes absents ou vides, les religions
et suzerains inconnus, les coordonnées non finies et une date ou projection
incompatible. Un identifiant de seigneurie absent, booléen ou non entier
lève `SeigneurieInconnue`, sous-classe de `LookupError`, avant tout calcul.

`fiche_de_seigneurie` de `sim/seigneuries.py` recalcule une fiche gelée :

- `cell_id` du siège et `habitants = monde.cells[cell_id].population` ;
- `production_kg_par_tick = population_soutenable_de(cellule, monde.carte)
  × constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK`, nourriture par tick
  au rendement moyen et sur la saison moyenne, issue de l'unique formule
  du moteur ;
- `suzerain`, la `Puissance`, et `maison`, sa `Maison` selon `par_puissance`,
  ou `None` pour une république, une Église ou un ordre ;
- `cellules_du_suzerain`, le nombre de cellules que `puissances_depuis_monde`
  attribue au suzerain, et `habitants_du_suzerain`, la somme de leurs populations ;
- `voisins`, cellules reliées au siège par une arête `land-land` de
  `monde.adjacency`, sans doublon et triées par `cell_id`, chacune avec sa
  puissance (ou `None`) et ses habitants actuels.

**Niveau 1** : seigneur, maison, suzerain et point du siège, vérifiés contre
des sources publiques. **Niveau 2**, plausible et jamais sourcé : seigneurie
réduite à la cellule entière de son siège, habitants amorcés et production
de cette cellule, étendue du suzerain suivant ses ancres. Les anomalies
de cette réduction ne sont pas des défauts. **Niveau 3**, pas simulé :
prélèvement et hommage (jalon 3), personnes, autres seigneuries.

La fiche est une **vue pure**, recalculée, hors de `sim.model` : elle ne pose
rien sur `Cell` et ne stocke aucune seconde clé spatiale. La table des
puissances, ses maisons, l'amorçage, la carte et le tick restent identiques.
**Le tick ne la lit pas.**

---

## Les intentions du joueur

`recevoir_intention` de `sim/intentions.py` est l'entrée commune de
`POST /intention` et `python3 -m sim --gestes`, que prendra aussi l'IA.
La liste est fermée : `choisir_depart` appelle `deposer_intention`,
`tracer_route` dépose une route ; tout autre type, même absent, lève
`IntentionRefusee("type d'intention inconnu : <repr>")` sans effet.

Le joueur dépose `{"type": "choisir_depart", "seigneurie": <id>}` par
`POST /intention`. `python3 -m forge --depart ID` continue d'appeler
directement `deposer_intention`, dont le comportement ne change pas.
La table se lit par `charger_seigneuries()` ; `cellule_du_siege` vérifie
que le siège est dans la carte. Aucune cellule ni aucun plan ne change.

Le dépôt refuse avant toute mise en attente, par `IntentionRefusee` :

- une valeur absente, booléenne, non entière ou inconnue :
  « seigneurie inconnue : <valeur reçue> » ; un siège hors carte est aussi refusé ;
- un choix déjà retenu ou en attente : « départ déjà choisi : <id> ».

Le choix accepté est un `ChoixDepart(identifiant)` gelé, placé dans
`World.intentions_en_attente`. Il reste invisible dans `to_dict()` et les
vues. Au tick suivant, `_appliquer_intentions` vient après la validation du
numéro et avant la fabrication : elle appelle chaque intention par
`.appliquer(monde)` dans l'ordre du dépôt, puis vide la liste.
`ChoixDepart.appliquer` pose `maison_du_joueur`.
Un numéro invalide laisse donc les intentions en attente.
Cette étape ignore les mondes d'épreuve, ne tire aucun aléa et ne lit ni
n'écrit aucune cellule. Le reste du tick ne consulte pas la maison du joueur.

`maison_du_joueur` vaut `None` au chargement. Après application, `to_dict()`
et `/monde` portent cette clé et l'id choisi ; sans choix, la clé est absente
et les octets comme l'empreinte restent ceux d'avant. Même graine et même
choix donnent le même monde ; un autre choix change son empreinte, sans
changer les cellules, les plans ou l'état du générateur aléatoire.

Une route se dépose avec exactement `{"type": "tracer_route", "cell": X,
"points": [[x, y], …], "largeur_m": L}`. Un champ absent ou supplémentaire
est refusé. `cell` est un entier présent dans `World.plans`, sans booléen ;
toute cellule de la carte convient. La construction d'une `Rue` vérifie
points et largeur selon le contrat du plan ; un `PlanInvalide` devient
`IntentionRefusee("route invalide : <raison>")`. Le dépôt accepté est un
`TraceRoute(cell_id, points, largeur_m)` gelé, aux points copiés en tuples.
L'attente ne change ni les cellules, ni les plans, ni `to_dict()`.

`TraceRoute.appliquer` reconstruit le plan avec une rue en chantier. Son
identifiant est le maximum des identifiants de rue, ou −1 si le plan est
vide, plus un. Les dépôts sur la même cellule se suivent donc sans collision.
L'écriture vit dans `sim/intentions.py` ; le moteur ne lit pas le plan.
La route ne consomme aucun aléa et ne lit ni n'écrit aucune cellule : mêmes
gestes et même graine donnent le même monde ; sans geste, les plans restent
vides et l'empreinte reste celle d'avant.

Le service dépose tout objet JSON sous `verrou_tick`. Il répond 200 avec
`{"acceptee": true, "appliquee_au_tick": <tick publié>}`, 400 pour une intention
inconnue ou mal formée, 409 pour un second choix. Tout refus, y compris un
corps illisible ou qui n'est pas un objet, rend
`{"acceptee": false, "erreur": "<raison>"}` sans avancer ni republier le monde.

`python3 -m sim --gestes FICHIER` lit une liste JSON d'entrées
`{"tick": t, "intention": {…}}` : les intentions du tick `t` se déposent dans
l'ordre du fichier juste avant ce tick, qui les applique. Les ticks doivent
être entiers, sans booléen, non négatifs, croissants ou égaux, et inférieurs
à `--ticks`. Sinon, ou si le fichier est illisible, n'est pas une liste,
manque un champ, ou contient une intention refusée, la commande rend 2 avec
la raison sur stderr (et le rang de l'entrée pour une intention refusée).
Elle n'écrit alors ni `--monde-json`, ni `--snapshot-json`.
`--monde-json FICHIER` écrit `World.to_dict()` final en JSON canonique : clés
triées, UTF-8, `ensure_ascii=False`, séparateurs compacts.

`--depart` est entier et répétable : chaque valeur se dépose dans l'ordre
avant le premier tick. Un refus rend le code 2 sur stderr, sans simulation
ni `resume.json`. Avec `--ticks 0`, la commande refuse : « l'intention
s'applique au tick suivant ». Le compte rendu porte
`simulation.maison_du_joueur` seulement après un choix appliqué ; la
photographie porte `terre_choisie`, `null` sans choix ; c'est sa seule différence.

**Niveau 1 :** les cinq terres et leurs attributions héritées, sans changement.
**Niveau 2, plausible :** la maison du joueur réduite à l'id de sa terre,
donc à la cellule de son siège. **Niveau 3, pas simulé :** ses effets
(prélèvement, jalon 3), les maisons de l'IA (jalon 5) et les personnes
(jalon 6). Changer de départ, sauvegarder et recharger ne sont pas simulés.

## La photographie de 1400, vue dérivée

La photographie lit les vues existantes sans modifier le monde. Chaque
cellule porte `puissance` et `maison` (`id`, `nom`), issues de
`puissances_depuis_monde` et `maisons_depuis_monde` : une cellule non couverte
porte deux `null` ; une république, une Église ou un ordre porte une puissance
et une maison `null`. `densite_hab_par_km2` lit population / surface par
`densite_de_cellule`, avec l'arrondi commun de la photographie. `villes`
porte les noms et populations de `charger_villes`, placés par
`attribuer_villes` et triés par nom ; sans ville documentée, la liste est vide.

À la racine, `villes_hors_carte` déclare les noms triés des villes non placées.
`terre_choisie` vaut `null` sans choix, sinon porte la fiche actuelle de
`fiche_de_seigneurie`, avec siège, source, cellule, habitants, production,
suzerain, sa maison (`null` si absente), ses cellules et habitants, et voisins
dans l'ordre de la fiche. **Le tick ne la lit pas.**

**Niveau 1 :** puissances, maisons, villes et terres avec leurs sources.
**Niveau 2, plausible :** étendue des puissances et maisons, terre réduite à
la cellule de son siège, population amorcée. **Niveau 3, pas simulé :**
frontières réelles, suzeraineté et villes hors carte, déclarées sans placement.

## Les lieux d'une cellule, vue dérivée

La surface `area_km2` d'une cellule de la carte se partage en lieux. Leur
nombre est `max(1, floor(area_km2 / SURFACE_KM2_PAR_LIEU))`, avec
`SURFACE_KM2_PAR_LIEU = 1000.0`. Chaque lieu a pour identité le couple
(`cell_id`, `rang`), des rangs 0 à `n − 1` ; **le rang 0 est le bourg**. Aucun
identifiant spatial supplémentaire n'est stocké.

Chaque rang supérieur à 0 reçoit `q = floor(area_km2 / n)` kilomètres carrés.
Le bourg reçoit le reste, `area_km2 − (n − 1) × q` : il est au moins aussi
grand que les autres. Ce reste est une soustraction exacte tant que la surface
de la carte est sous 2⁵³ km² ; les surfaces des lieux rendent ainsi celle de
la cellule au bit près, sans l'arrondi d'un partage égal par division.

La vue refuse une surface absente, booléenne, textuelle, non finie, nulle ou
négative en nommant sa cellule. Elle refuse aussi une constante non finie ou
inférieure à 1 km². Elle est pure, recalculée à chaque consultation hors de
`sim.model`. Le tick lit les surfaces à la consommation pour limiter la
distribution intérieure, sans lire les habitants et paniers persistés ; il
remet ces états d'accord avec la cellule à la fin.

Ce découpage est de **niveau 2** : le nombre de lieux et leur surface sont
plausibles, jamais sourcés. Le bourg est celui de « Ce qu'est une ville, à
l'échelle d'une cellule », vu ici par sa surface et sa part des habitants ; il
ne concentre encore ni les gens de la ville ni ceux de `RepartitionBourg`.
Les chemins limitent la distribution alimentaire intérieure décrite ci-dessous.
La forme, la position, les frontières et les noms des lieux ne sont pas simulés.

### Ce que porte un lieu

`EtatDeLieu`, dataclass mutable de `sim.model`, porte exactement `rang`,
`population` et `stocks`. La liste `Cell.lieux` rattache ces états à leur
cellule : aucun `cell_id` recopié ni `lieu_id`. La surface reste celle de la
vue `lieux_de_cellule`, jamais une deuxième donnée stockée.

La règle unique `partager(total, poids)` utilise le **plus fort reste** : les
parts exactes sont mises au plancher, puis les unités entières restantes vont
aux plus grands restes, à égalité au plus petit rang. Les rangs supérieurs à
zéro gardent des entiers ; le bourg reçoit `total − somme(des autres parts)`.
Cette soustraction conserve la fraction de kilogramme, et la somme retrouve
le total de la cellule **au bit près**. Les totaux et poids négatifs, booléens
ou non finis et une somme de poids nulle sont refusés par `LieuxInvalides`.

`amorcer_lieux` partage la population et chaque marchandise selon les surfaces
après leur amorçage dans `World.charger`. Après la migration et avant l'avance
du compteur, `repartir_sur_les_lieux` compare chaque somme au total actuel de
la cellule : déjà d'accord, elle ne bouge pas ; sinon, le contenu actuel donne
les poids. Quand tous les lieux sont à zéro, les surfaces donnent les poids.
Une marchandise absente de la cellule disparaît de tous ses lieux : l'absence
n'est pas zéro. Une écriture sur la cellule hors du tick est suivie de même.

Une cellule construite à la main avec une liste vide reste sans lieux ; le
tick ne lui en invente pas. Les compteurs de faim, la dette et les restes de
mortalité, natalité et migration restent à la cellule. Ce partage est de
**niveau 2**, plausible, jamais sourcé ; aucun mouvement propre aux lieux
n'est simulé (niveau 3).

### L'identité d'un lieu, et ce qui la change

Un lieu se retrouve par son couple (`cell_id`, `rang`) avec `lieu_du_monde`,
qui ne découpe que la cellule demandée. Un couple mal formé — `cell_id` ou
`rang` booléen, textuel, flottant, ou absent — lève `LieuxInvalides`. Un
couple bien formé qui ne désigne aucun lieu lève `LieuInconnu` : cellule
absente du monde, rang négatif, ou rang au-delà du dernier lieu de la
cellule. Le rang négatif est refusé avant l'indexation. Rien n'est deviné,
rien n'est ramené dans l'intervalle.

Ce couple désigne le même lieu, de même surface, à tout tick, pour toute
graine, et dans tout ordre des cellules. Le découpage ne lit que `area_km2`
et `SURFACE_KM2_PAR_LIEU` ; le tick ne modifie pas la surface ; l'amorçage
la lit sur la carte figée, sans tirage ; la vue trie par `cell_id`.

Changer la surface d'une cellule sur la carte, ou `SURFACE_KM2_PAR_LIEU`,
renumérote les lieux de cette cellule. C'est un changement du monde : tout
ce qui s'accroche à un lieu devra le suivre. Il n'y a pas de numéro global
de lieu : un tel numéro suivrait l'ordre d'énumération des cellules, et
rien ne fixe cet ordre.

---

## La distribution à l'intérieur de la cellule

Le nombre d'habitants que le moteur compte au **rang 0** est
`population × part_miniere_de(gisements, facteurs_richesse_extraction())`.
Ce calcul ne lit ni la population ni les stocks persistés des lieux : il
utilise les totaux cellulaires et les surfaces. Les villes historiques
nommées ne sont pas comptées au bourg.

Ce nombre reste la part minière du moteur. Après des ticks, un écart avec le
bourg de la vue est possible : celle-ci compte les métiers non paysans,
dont les variations suivent le prorata des foyers. La distribution nourrit
le rang 0 selon la part minière, sans consulter la vue ni les métiers.

À chaque consommation, le panier alimentaire est réputé réparti au prorata
des surfaces : pour un stock `S` (sentinelle −1 lue comme 0), une surface
cellulaire `A` et une surface de rang 0 `s0`, le bourg dispose localement de
`S × s0 / A`. Chacun des `n − 1` autres lieux a un chemin vers lui :
`capacite = CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK × (n − 1) × facteur_transport`.
Le facteur de relief est celui de `facteurs_transport_par_relief()`, comme pour
le commerce. Le bourg atteint `min(S, local + capacite)` ; s'il n'y a qu'un
lieu, il atteint tout le panier et aucune capacité n'est calculée.

`CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK = 2500.0 × TICK_DURATION_DAYS` : cinq
charrettes d'une demi-tonne par jour, ordre de grandeur de **niveau 2**,
plausible, jamais sourcé. La fonction `capacite_chemins_interieurs_kg` relit
cette constante et refuse une valeur NaN ou négative ; l'infini est accepté.

Le besoin du bourg est `population × part × ration`, celui des champs est le
besoin total moins celui du bourg. Le bourg mange le minimum de son besoin et
de ce qu'il atteint ; les champs mangent ensuite sur le reste.

- **Le bourg a faim pendant que les champs débordent** si son manque est
  strictement positif et si `reste_champs = S − mange_bourg − besoin_champs`
  est strictement positif. Le panier garde ce reste ; la dette augmente du
  manque du bourg, sans remboursement de dette ancienne. Ce manque est la
  pénurie du tick, lue par la faim, la mortalité, la natalité et la migration.
- **Sinon, la consommation reste inchangée au bit près**, y compris son
  remboursement physique de la dette. Sans carte ou sans part minière,
  c'est aussi ce calcul qui s'applique.

Aucun kilo n'est créé : les kilos qui quittent le panier ont été mangés, le
besoin du tick n'est pas dépassé dans le cas de distribution limitée, et le
panier reste non négatif. Le remboursement de dette conserve ses kilos réels.
Restent de niveau 3, non simulés : délai, pertes en route, bras des porteurs,
tracé des chemins, consommation du stock persisté de chaque lieu, distribution
entre les lieux des champs et intégration des villes nommées dans le bourg.

---

## Le plan du bourg

Chaque cellule possède un plan du lieu (`cell_id`, 0), le bourg, dans
`World.plans` : un dictionnaire `cell_id → Plan`. Aucun `bourg_id`, `ville_id`
ou numéro de plan n'est ajouté. Le bourg reste une vue dérivée de la
population ; seuls ses tracés sont stockés. Un monde chargé ou construit
directement reçoit un plan vide par cellule, sans tirage ni choix de capitale.

`sim/plan.py` contient trois listes triées par `identifiant`, entier non
négatif et unique dans sa liste :

- `rues` : `identifiant`, `points` (au moins `POINTS_MIN_RUE = 2`),
  `largeur_m` finie et strictement positive, `en_chantier` booléen (faux par
  défaut, vrai pour une route déposée ; tout autre type est refusé) ;
- `parcelles` : `identifiant`, `contour` (au moins `POINTS_MIN_CONTOUR = 3`) ;
- `batiments` : `identifiant`, `parcelle` (identifiant d'une parcelle du même
  plan), `nature` (texte non vide), `emprise` (au moins `POINTS_MIN_CONTOUR`).

Chaque point est un couple `(x, y)` de nombres finis, sans booléen ni texte.
Le repère est local au bourg : x vers l'est, y vers le nord, en mètres,
origine au centre du bourg. `PlanInvalide` nomme la donnée manquante ou
invalide : point non fini, nombre de points insuffisant, largeur nulle ou
négative, identifiant invalide ou en double, parcelle absente, nature vide.
Aucune coordonnée n'est bornée : la position et la forme du bourg dans la
cellule ne sont pas simulées.

Le plan se sérialise dans `World.to_dict()["plans"]`, sous des clés de cellule
en chaîne, triées comme celles de `"cells"`. L'empreinte du monde voit donc
son plan. Aucune règle du tick ne le lit ; seule l'étape Intentions y ajoute
une rue en chantier. Toutes les règles
existantes et l'évolution des cellules restent identiques au bit près.

`GET /plan?cell=X` sert `cell_id`, `rang: 0`, `tick`, `date`, `rues`,
`parcelles` et `batiments`. Les octets sont construits dans `EtatPublie` avec
la photographie du tick : une lecture n'attend pas son calcul et ne consulte
pas le monde mutable. Un paramètre absent ou mal formé donne 400 ; une cellule
inconnue donne 404 en la nommant. Le plan ne s'ajoute ni à `/monde`, ni à
`/lieu`, ni au snapshot.

La forme du plan est de **niveau 2** : plausible, jamais sourcée. Son état
vide initial n'affirme rien. Restent de **niveau 3**, non simulés : position
et forme du bourg dans la cellule, effet des rues et bâtiments sur le monde,
gestes de parcelle et de bâtiment, inclusion d'une emprise dans une parcelle
et croisements des tracés. Le tracé d'une route est de niveau 2, plausible ;
son coût, les bras pris aux champs, son achèvement, la restriction à la
capitale, les bornes et les doublons restent de niveau 3, non simulés.
Aucune règle ne fait passer une rue en chantier à achevée et aucun flux
ne découle encore de son tracé.

---

## Le moteur sans état caché

Deux règles d'architecture qui décident comment un lot s'écrit, et qui ont
chacune coûté un défaut.

**La carte est passée, jamais posée.** `tick(world, rng, numero_tick)` reçoit le
monde et lit `world.carte` ; il ne dépose la carte dans aucune variable de
module. Un module qui garderait la carte d'un tick sur l'autre ferait dépendre
un tick du précédent sans que rien ne le dise, et deux mesures jouées dans un
ordre différent ne rendraient pas la même chose. Un contrôle vérifie que le
tick ne pose rien dans le module, et il n'y a aucune instruction `global` dans
le moteur.

**Une constante se lit par son module, jamais par valeur.** Le moteur écrit
`_constantes.X`, jamais `from sim.constants import X`. Un nom importé par
valeur est figé au chargement : le remplacer en mémoire ne change alors rien au
moteur, et un test de régime croit mesurer un régime alors qu'il mesure un
moteur inchangé, sans qu'aucune erreur ne soit levée. Cinq constantes sur huit
étaient dans ce cas.

Corollaire pour les tables : une table de facteurs se relit par une **fonction**
(`facteurs_production_par_relief()`, `facteurs_transport_par_relief()`,
`facteurs_richesse_extraction()`) qui relit ses constantes nommées à chaque
appel, jamais par un dictionnaire construit au chargement du module.

---

## Le monde d'épreuve, et pourquoi certaines constantes se cachent

`sim/tests/test_write_coverage.py` porte deux contrôles jumeaux qu'il faut
connaître **avant** de nommer une constante dans un brief :

- l'un dérive de l'arbre syntaxique de `sim/engine.py` la liste des constantes
  que le moteur consulte, remplace chacune en mémoire, et exige que le monde
  d'épreuve en sorte différent. La présence n'est pas la fonction (règle 7) ;
- l'autre prend pour dénominateur les constantes **déclarées** et exige que
  chacune soit lue quelque part — un test compte comme lecteur. C'est celui qui
  attrape la constante survivante à sa cause.

Le monde d'épreuve est minuscule : trois cellules, deux arêtes, ni carte, ni
relief, ni gisement, ni `shared_length_m`. Il répond à « le moteur voit-il cette
constante ? », pas à « le monde survit-il ? ».

**Conséquence, et c'est un motif de rédaction de brief, pas une astuce.** Une
constante qui ne peut rien changer sur ce monde-là — parce qu'elle gouverne une
donnée de carte que le monde d'épreuve n'a pas — sera déclarée inerte si le
moteur la lit **par son nom**. Le remède n'est jamais d'élargir le monde
d'épreuve après coup ni de relâcher l'assertion : c'est de faire lire la
constante par une **fonction** de `sim/constants.py`, comme les tables de
facteurs ci-dessus. Elle sort alors du dénominateur du premier contrôle, reste
dans celui du second, et le moteur la relit toujours à chaque appel.

**Le cas payé, et la seule réparation qui était licite.** Le lot 043 a fait lire
`DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK` **par son nom** dans `sim/engine.py`,
alors que le monde d'épreuve n'avait pas de `shared_length_m` sur ses arêtes :
la constante y était inerte, et le contrôle est resté **rouge sur `master`**
pendant quatre jours — le brief 043 l'avait prévu et le lot a fusionné ainsi.

Le micro-lot 043-bis l'a réparé le 2026-08-30, et **la façon dont il l'a fait
est la leçon** : il n'a ni relâché l'assertion, ni retiré la constante du
dénominateur. Il a donné au monde d'épreuve de quoi **exercer les deux
chemins** — une longueur de frontière sur une arête, pour le débit au
kilomètre ; aucune longueur sur l'autre, plus un vrai besoin de commerce au
bout, pour le repli plat. Une première tentative n'ajoutant que la longueur
avait laissé le contrôle rouge, cette fois sur le repli devenu inerte : la
preuve que le chemin doit être *emprunté*, pas seulement *présent* (règle 7).

Ce que cela dicte à tout lot suivant : une constante qui gouverne une donnée de
carte **absente** du monde d'épreuve ne se lit jamais par son nom dans
`sim/engine.py`. Elle se lit par une fonction de `sim/constants.py`. Élargir le
monde d'épreuve n'est licite que si la donnée y a un sens et si les deux
branches y travaillent vraiment ; relâcher l'assertion ne l'est jamais.

---

## Référence de code

La projection ellipsoïdale des ancres est définie dans `sim/projection.py` ;
leur sélection commune vit dans `sim/puissances.py` et sert `sim/maisons.py`.

Les paramètres du tick sont définis comme constantes nommées dans
`sim/constants.py`. Aucun littéral numérique de ces valeurs n'apparaît dans
les fonctions de calcul de `sim/engine.py` ou `sim/world.py` (vérifiable
via `sim/tests/test_no_hardcoded.py`).
