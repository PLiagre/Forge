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
   du joueur, une route, une parcelle ou un bâtiment entre au plan en chantier ;
   sans cellule ni aléa.
3. **Greniers** (`_appliquer_pertes_greniers`) — chaque réserve de maison
   perd une part de sa nourriture ; les habitants n'y mangent pas.
4. **Chantiers** (`_avancer_chantiers`) — les ouvriers reviennent aux champs,
   puis les rues, les parcelles et enfin les bâtiments dont la parcelle est
   prête prennent leurs bras et comptent les journées fournies.
   **Ateliers** (`_affecter_artisans`) — les scieries et fours achevés prennent les paysans restants.
5. **Fabrication** (`_apply_fabrication`) — chaque matière première présente
   dans le panier d'ouverture perd 5 % de son stock, dont 60 % du poids devient
   de l'`objet`, sans bras ; les artisans façonnent ensuite le reliquat avec un budget commun.
6. **Extraction** (`_apply_extraction`) — chaque gisement de la cellule sort
   des kilogrammes de sa ressource et les dépose dans le panier de la cellule.
7. **Production** (`_apply_production`, `_apply_production_saison_moyenne`) —
   la cellule produit de la nourriture proportionnellement à sa surface,
   multipliée par un aléa de rendement du tick, par le facteur de sa classe de
   relief — une montagne ne produit pas comme une plaine —, par le
   `facteur_eau` de l'eau de la cellule — sa pluie plus la crue du fleuve — et
   par le facteur de saison du jour, tiré de la durée du jour de la cellule :
   on ne récolte pas en janvier comme en juin, ni sans eau comme sous une
   pluie suffisante.
8. **Commerce** (`_apply_commerce`) — les cellules en surplus livrent leurs
   voisines en manque, sur les arêtes d'adjacence. Un kilogramme ne traverse
   qu'une arête par tick et ne nourrit qu'une fois. Toute marchandise du panier
   circule, pas seulement la nourriture. Une route achevée avec porte augmente
   le plafond de sa frontière dès ce tick.
9. **Consommation** (`_apply_consumption`) — le bourg ne mange que ce qu'il
   atteint, par sa part locale du panier et les chemins venus des champs.
   Ce qui manque devient une **dette** (`food_deficit_kg`), pas un oubli. Si le
   bourg manque pendant que les champs débordent, aucune dette n'est remboursée.
   Sinon, un surplus rembourse la dette, jamais plus vite que le surplus lui-même.
10. **Faim** (`_update_hunger`) — une cellule qui a *manqué* ce tick voit
   `hunger_ticks` monter ; une cellule ravitaillée exactement à son besoin,
   non.
11. **Mortalité** (`_apply_mortality`) — la dette tue, avec report de la
   fraction d'habitant non encore morte pour qu'une petite cellule ne devienne
   pas immortelle par arrondi.
12. **Natalité** (`_apply_natalite`) — une cellule rassasiée et sans dette gagne
   des habitants, avec le même report de fraction.
13. **Migration** (`_apply_migration`) — une part des habitants d'une cellule
    qui a manqué ce tick part vers les voisines dont il reste de la nourriture
    après consommation. Personne n'emporte de kilogrammes.
14. **Répartition sur les lieux** (`repartir_sur_les_lieux`) — leurs habitants
    et paniers sont remis d'accord avec les totaux de la cellule.
15. **Avance du compteur** (`_avancer_compteur_ticks`) — une fois tous les
    maillons réussis, `ticks_ecoules` augmente de un et fait ainsi passer la
    date dérivée au jour suivant.

La **province** ne se stocke pas : elle se recalcule à chaque consultation
comme « le centre administratif le plus proche ». La **pluie** et la **crue**
ne sont pas stockées sur `Cell` : leurs vues se dérivent respectivement du
relevé le plus proche et du cours du fleuve, puis entrent dans la carte au
moment où le monde la lit. La **puissance** et la **maison** dont relève une
cellule sont pareillement des vues dérivées, jamais un second identifiant
spatial stocké. Le registre des maisons, distinct de cette tenure dérivée,
est désormais détenu par `World.maisons` : chargé une fois, il figure dans
`to_dict()` et n'est jamais lu au tick. Chaque maison a en outre son grenier
dans `World.greniers`, lu tel quel par le tick. Le nombre et les surfaces des **lieux**
se dérivent de la surface de la cellule ; ses lieux portent désormais leur population et leur
panier sur `Cell`. Le tick lit la pluie et la crue dans la carte, jamais dans
leurs vues ; il ne consomme ni la vue des provinces, ni celle des puissances,
ni celle des maisons. Il lit les habitants et paniers des lieux pour
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
  place : 5 % sans bras, puis un supplément par les artisans des ateliers ; les objets produits
  ne sont pas consommés.
- **répartir le travail.** Les habitants ont un métier : mineur, paysan, ouvrier ou artisan.
  Naissances, morts et départs suivent les métiers ; récolte, chantiers, ateliers et fabrication les lisent. Les chantiers font passer les paysans à ouvriers, les ateliers à artisans
  et retour ; la part minière retire déjà des bras aux champs.
- **naviguer.** Voir « La mer : la façade que le moteur ne lit pas ».
- **investir.** Une route se bâtit à la journée ; achevée avec porte, elle
  augmente la capacité de transport terrestre ; ponts et ports restent non simulés.
- **tenir un prix.** Il n'y a ni monnaie, ni marché, ni salaire, ni propriété.
  Le commerce déplace des kilogrammes vers qui en manque, gratuitement.
- **descendre sous les lieux pour les calculs.** Les lieux portent habitants
  et paniers ; à la consommation, les paniers, habitants et chemins déterminent
  ce que chaque lieu mange. Pas de mouvement propre aux lieux, de familles,
  de personnes ni de quartiers. Le plan peut porter des bâtiments, mais ils
  ne font rien une fois achevés ; un bâtiment posé se bâtit à la journée.
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
2. **Les routes.** La carte n'en porte aucune à l'amorçage. Le joueur peut
   désormais en bâtir : une route achevée vers une voisine concentre le commerce
   à cette frontière. Ponts, ports, entretien et monnaie restent non simulés.

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

1. **A dépend des surplus et des infrastructures.** Voir « Le mur » : les
   routes commerciales choisies et bâties relèvent le plafond de transport,
   sans garantir les surplus nécessaires. A ne définit pas le bourg.
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
Aucune cellule sans part minière ne s'écarte. La distribution intérieure lit
désormais les habitants persistés au rang 0, sans relire les métiers.

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

**La distribution coûte des chemins.** Chaque lieu mange dans son panier ;
les échanges passent par le bourg, selon « La distribution à
l'intérieur de la cellule ». Les pertes et le délai ne sont pas simulés.

### Ce que le moteur ne fait toujours pas

La vue du bourg compte les foyers par métier ; la consommation lit les lieux.
Le bourg ne donne ni quartiers, ni personnes, ni salaires, ni marchés,
ni prix, ni États. Son plan peut porter des rues et des bâtiments,
mais ils ne font rien. La vue du bourg ne décide
rien et le tick ne la consulte pas : il lit les habitants et paniers des
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

**Le tick ne lit les métiers que pour la récolte et pour le chantier**.
Ateliers lit aussi les métiers pour affecter les artisans ; Fabrication les lit pour leur budget de matière.
Le métier `ouvriers` reçoit les paysans envoyés aux chantiers pour ce tick.
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
Le logement des artisans est de niveau 2 : réponse A, seuls les artisans cherchent un logis ; paysans, mineurs et ouvriers gardent le leur.
`sim/logement.py` relit `SURFACE_M2_PAR_FOYER_LOGE = 40` et `TAILLE_FOYER` à chaque appel.
Une maison finie loge `max(1, int(aire_du_contour(emprise) // SURFACE_M2_PAR_FOYER_LOGE))` foyers ; les autres bâtiments et chantiers ne logent personne.
`capacite` somme ces places ; `loges = min(foyers d’artisans, capacite)` ; `sans_logis = foyers d’artisans − loges`, dernier foyer incomplet compris.
Métiers non calculés : capacité calculée, les deux autres champs à `-1`.
`/lieu` publie `logement` seulement si le plan porte un bâtiment, avec `foyers` et `lieux` au même tick.
Le logement ne lit les métiers que dans la photographie, sans stockage ni effet sur le tick.
Âge, sexe, parenté, logement des autres métiers et sort des sans-logis (froid, départ, santé) restent de niveau 3, non simulés.

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
garde les 5 % sans bras. Ensuite, par nom de matière, `budget = artisans × FABRICATION_KG_PAR_ARTISAN_PAR_TICK` (5 kg/personne/tick), commun à toutes les matières.
`consomme = min(stock restant, budget restant)` ; l'objet vaut cette masse × `RENDEMENT_FABRICATION`, les chutes la différence. Métiers non calculés : aucun supplément ; sans matière positive, aucun objet écrit. L'extraction vient après. L'`objet` produit n'est pas
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
apport  = DEBIT_ROUTE_KG_PAR_M_PAR_TICK × somme des largeurs achevées vers cette porte
capacité = (base + apport) × goulot
```

| Constante | Valeur | Unité | Ce que c'est |
|---|---|---|---|
| `DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK` | 200.0 × TICK_DURATION_DAYS | kg/km/tick | Niveau 2. Calibré pour qu'une frontière d'un kilomètre rende exactement l'ancienne capacité plate. |
| `METRES_PAR_KM` | 1000.0 | — | Conversion d'unité, pas un réglage. Lue par `metres_par_km()`. |
| `TRADE_CAPACITY_KG_PER_EDGE_PER_TICK` | 200.0 × TICK_DURATION_DAYS | kg/arête/tick | **Repli seul** : employé uniquement par une arête qui ne porte pas `shared_length_m`. Une arête qui la porte n'y touche jamais. |

**Ce que cette forme dit du monde.** Une longue frontière commune laisse passer
plus de convois qu'un contact ponctuel : il y a plus de chemins, plus de gués,
plus de cols. Cette base décrit la perméabilité brute d'une frontière.
L'apport routier est de niveau 2 : `DEBIT_ROUTE_KG_PAR_M_PAR_TICK =
5000.0 * TICK_DURATION_DAYS`, relu à chaque appel. La somme des largeurs
achevées vers l'autre cellule, aux deux bouts et en ordre stable, sert le
même plafond dans les deux sens et pour toutes les marchandises : 4 m
ajoutent 20 000 kg en plaine, 6 000 kg en montagne. Sans carte, goulot = 1.
Sans apport, les opérations et retours restent exactement ceux de la base.

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
repli. Une longueur **nulle** est valide : base zéro mesurée, mais une route
achevée avec porte peut y ajouter son débit. Les données invalides restent refusées.

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
Le point du Caire est dans le polygone **8992**, même si aucune ancre
n'y est placée. Cette cellule relève des Mamelouks grâce aux ancres
d'Alexandrie et de Damiette.

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
**niveau 3**, pas simulés, sauf les seuls liens de départ du registre ci-dessous.

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

Le registre ajoute seulement les liens de départ décrits ci-dessous ; cette vue reste inchangée. Restent de **niveau 3**, pas simulés : les autres liens de suzeraineté et l'hommage,
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
six petites seigneuries : le **Duché de Bar** (maison Bar, Robert Ier,
Barrois mouvant relevant de la France), le **Comté de Wurtemberg** (maison
Wurtemberg, Eberhard III, Saint-Empire), le **Despotat de Morée** (maison
Paléologue, Théodore Ier, Byzance), la **Terre des Branković** (maison
Branković, Đurađ, Ottomans), l'**Uç d'Evrenos** (maison Evrenosoğulları,
Gazi Evrenos Bey, Ottomans) et l'**Émirat du Zab** (maison Banou Mozni,
Biskra, Hafsides). Bar et Wurtemberg sont catholiques ; Morée
et Branković sont orthodoxes ; Evrenos et le Zab sont musulmans. La source
du Zab déclare « Chef de la maison au 1er janvier 1400 : non sourcé » ;
cette mention reste visible dans la fiche, la photographie et `/departs`.
La reprise hafside en 1402 donne un contexte, sans imposer une conquête.
Bar désigne ici la
branche de Scarpone. Le projet hospitalier concernant Mistra est postérieur
au départ : la cession de Corinthe est datée de 1400 par la source publique.

Chaque ligne donne un `id`, un `nom`, une `religion` de `RELIGIONS`, le nom
de sa `maison`, l'identifiant de sa puissance `suzerain`, une `source`
publique et son `siege` : nom, latitude et longitude en EPSG:4326, coordonnées
`x_m`, `y_m` en EPSG:3035. Les sièges sont Bar-le-Duc, Stuttgart, Mistra,
Vučitrn, Giannitsa (Yenice-i Vardar) et Biskra. La cellule du siège est dérivée par
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

**Niveau 1** : maison, religion, suzerain et point du siège, vérifiés contre
des sources publiques ; seigneur quand il est sourcé, chef du Zab déclaré
non sourcé. **Niveau 2**, plausible et jamais sourcé : seigneurie
réduite à la cellule entière de son siège, habitants amorcés et production
de cette cellule, étendue du suzerain suivant ses ancres. Les habitants de
la fiche mesurent la cellule actuelle, pas la ville historique. Les anomalies
de cette réduction ne sont pas des défauts. **Niveau 3**, pas simulé :
prélèvement et hommage (jalon 3), personnes, autres seigneuries.

La fiche est une **vue pure**, recalculée, hors de `sim.model` : elle ne pose
rien sur `Cell` et ne stocke aucune seconde clé spatiale. La table des
puissances, ses maisons, l'amorçage, la carte et le tick restent identiques.
**Le tick ne la lit pas.**

---

## Les maisons de l'IA et leurs capitales, vue dérivée

La table `data/capitales-1400.json`, datée du **1er janvier 1400**, déclare
une capitale par grande maison de la table des puissances, sans modifier
celle-ci : `maison` (id), `nom`, `lat`, `lon` en EPSG:4326 et `source`
publique du siège et de la tenure dynastique. Seul un point hors de tous
les polygones porte `hors_carte`, sa raison textuelle. Sur la carte figée,
**30** capitales sont déclarées : **29** placées, chacune dans une cellule
que `maisons_depuis_monde` donne à sa propre maison, et **1** hors carte,
Saraï des Djötchides sur la basse Volga, avec `cell_id = None` et sa raison.

`cellule_de_capitale` projette le point par `projeter_epsg3035`, puis lit
`point_dans_geometrie` en parcourant les polygones par `cell_id` croissant ;
le plus petit gagne sur une frontière. Le centroïde le plus proche ne sert
jamais. Un point hors carte sans raison est refusé ; une raison hors carte
pour un point contenu est refusée en nommant sa cellule. Londres tombe en
10237, Constantinople en 10374, Le Caire en 8992 et Roskilde en 9892.
Perth est retenue pour les Stuart avant le transfert à Édimbourg au milieu
du XVe siècle ; Roskilde représente la maison Poméranie avant 1443.

Le chargement lève `PuissanceInvalide` en nommant la maison et le champ :
liste absente ou vide, date autre que `1400-01-01`, maison inconnue,
booléenne ou non entière, doublon, maison sans capitale, nom ou source
absents ou vides, coordonnée non finie ou booléenne, `hors_carte` présent
mais vide. Le placement refuse aussi une géométrie absente ; la vue passe
par `positions_du_monde` et refuse une position absente en nommant la cellule.

`maisons_de_l_ia(monde, …)` de `sim/capitales.py` recalcule un tuple gelé :
d'abord les grandes maisons triées par id, puis les seigneuries de départ
triées par id, sauf celle dont `identifiant_de_seigneurie(s.id)` vaut
`monde.maison_du_joueur`. Les ids des lignes restent entiers. Chaque ligne porte
`sorte` (`grande maison` ou `seigneurie`), `id`, `nom` de la maison,
`capitale` (ou siège), `cell_id`, `hors_carte` (raison ou `None`) et `source`.
Les sièges viennent de `cellule_du_siege`, leur source de la seigneurie.
Sans choix, **36** maisons ; après un choix appliqué au tick, **35**.
La branche Paléologue de Morée est distincte de celle de Constantinople :
sans choix, toutes deux sont à l'IA ; choisir la Morée laisse la grande
maison Paléologue à l'IA. La vue ne conserve rien entre deux appels,
hérite de `_NoBadSpatialField`, vit hors de `sim.model` et ne pose rien sur
`Cell`. `engine.py`, `world.py` et `model.py` ne lisent pas `capitales`.
**Le tick ne lit pas cette vue.**

Avec l'IA, la photographie ajoute les habitants actuels du **bourg de capitale**,
lieu de rang 0 : ni population historique de la ville, ni total des terres de la maison.
Une capitale hors carte conserve sa raison, `cell_id = null`, `population = null`
et `gestes = []`. Sur carte, zéro habitant est une mesure ; cellule ou bourg
attendu mais absent fait refuser l'export en nommant la maison et la donnée.
Ces habitants actuels sont de niveau 2, plausible et jamais sourcé.

**Niveau 1** : villes capitales et sources publiques, sièges des seigneuries
déjà sourcés. **Niveau 2**, plausible et jamais sourcé : une maison réduite
à une seule capitale, notamment Tolède pour la cour itinérante de Castille
et Heidelberg pour la branche palatine Wittelsbach (Munich reste une ancre),
et la cellule donnée par le polygone. **Niveau 3**, pas simulé : autres décisions
et gestes de l'IA, liens entre branches dynastiques, personnes, succession,
capitales qui changent, autres seigneuries et vassaux sans ancre.
Républiques, Église et ordres, sans maison, sont absents de cette vue.

---

## Les maisons du monde

`sim/registre_maisons.py` charge les trois tables `data/puissances-1400.json`, `data/capitales-1400.json` et `data/seigneuries-1400.json` avec la carte en argument ; des chemins alternatifs permettent les contre-épreuves. Le tuple stable de fiches gelées héritant de `_NoBadSpatialField` comprend toutes les maisons, y compris celle du joueur, sans fusionner les branches homonymes. Chaque fiche porte `id`, `nom`, `sorte`, `suzerain`, `siege` (nom), `cell_id`, `rang` et `hors_carte`.
Une grande maison a l'id `grande-<id maison>`, son nom et sa capitale ; une puissance sans maison devient `institution-<id puissance>`, nommée comme la puissance, siégeant à son ancre de plus petit id ; chaque départ devient `seigneurie-<id>`, nommé par son champ `maison`, à son siège déclaré.
La maison du joueur est cette fiche `seigneurie-<n>`, comme toute autre seigneurie du registre. `sim/seigneuries.py` définit seul le format par `identifiant_de_seigneurie(numero)` ; `numero_de_seigneurie` refuse toute valeur non canonique (préfixe exact, chiffres décimaux ASCII sans signe ni zéro de tête).
Les grandes maisons et institutions sont des racines sans suzerain ; les départs relèvent de la grande maison de leur puissance suzeraine, ou de son institution. Aucun lien supplémentaire ne rattache les grands vassaux des ancres.
La validation publique refuse une référence inconnue ou tout cycle, même sur soi, avec `PuissanceInvalide` nommant la maison ; elle accepte un registre altéré pour l'éprouver.
Les ancres sont projetées par `projeter_epsg3035` ; les sièges suivent les polygones, frontière au plus petit `cell_id`, jamais le centroïde le plus proche. Sur carte, le siège est le couple (`cell_id`, `rang = 0`), sans seconde clé spatiale.
Hors carte, `cell_id` et `rang` sont `None` : Saraï reprend la raison de sa capitale, Venise celle déclarée dans son ancre, sans déplacement ni bourg inventé. Toute raison absente ou vide hors carte, raison sur un point contenu ou géométrie absente est refusée.
**Niveau 1** : identités, capitales et sièges déjà sourcés. **Niveau 2**, plausible, jamais sourcé : racines sans suzerain, siège institutionnel choisi par id, rattachement au bourg de rang 0. **Niveau 3**, pas simulé ici : hommage matériel, personnes et succession. Le grenier de chaque maison est conservé à part : voir « Le grenier d'une maison ».

**Le maître de chaque lieu.** `sim/maitres.py` dérive les couples de
`lieux_depuis_monde` et lit le registre `monde.maisons`, sans le recharger.
D'abord, les seigneuries placées tiennent les `LIEUX_DE_LA_SEIGNEURIE = 4`
premiers rangs de leur siège, bourg compris, ou tous s'il y en a moins.
Ensuite, les grandes maisons et institutions placées prennent les lieux
encore libres de leur capitale ou siège ; hors carte, elles ne tiennent rien.
Chaque étape passe les maisons par id : un lieu déjà tenu ne change jamais.
Enfin, dans l'ordre des cellules et des rangs, les rangs libres se découpent
par `LIEUX_PAR_SEIGNEUR_PLAUSIBLE = 3`, dernier groupe éventuellement incomplet.
Chaque groupe crée une fiche `plausible-<cell_id>-<premier rang>` : nom et
siège reprennent l'id, sorte `plausible`, rang initial, `hors_carte=None`.
Dans une cellule couverte, son suzerain est la racine de la puissance de la
cellule (`grande-<par_puissance[p]>` ou `institution-<p>`), même si une autre
maison y tient des terres ; sans couverture, son suzerain est `None`.
Les constantes sont relues à chaque appel et exigent des entiers positifs.
`valider_attribution` refuse l'échantillon vide, les couples absents ou en trop,
les maîtres inconnus, les ids dupliqués et tout écart à la règle, couple nommé ;
`valider_registre_maisons` refuse les suzerains inconnus et cycles.
Niveau 2, plausible, jamais sourcé : les quatre lieux, groupes de trois,
maisons plausibles et suzerains. Le maître est stocké au chargement.
Niveau 3 : changement de maître et noms plausibles (#392).
La photographie et le service gardent leurs contrats ; le tick ne lit ni
les maîtres ni le registre et ne réattribue rien.

Le lecteur reste pur : il ne modifie ni tables, ni carte, ni monde.
`World.charger` l'appelle une fois avec sa carte, puis appelle `attribuer_maitres`
après l'amorçage des lieux et le registre historique. Les maîtres sont écrits
sur leurs lieux ; les fiches plausibles complètent une seule fois `World.maisons`,
en tuple trié par `id`, gelé et sans doublon, avant les greniers vides.
Un `World(...)` d'épreuve initialise
explicitement ce registre à `()`, sans lire les tables. `to_dict()` sérialise
toujours les fiches détenues dans une liste de dictionnaires indépendants triée
par `id`, sans rappeler le lecteur ou une vue. Aucun champ n'est ajouté à `Cell` ;
le siège reste (`cell_id`, `rang`). Le tick ne consulte jamais le registre :
sans geste, ses octets restent identiques pour toute graine et tout tick, tandis
que le monde évolue. Les anciennes vues et la sélection de l'IA gardent leur contrat.

## Le grenier d'une maison

Chaque fiche du registre, institutions et maison du joueur comprises, a un
panier dans `World.greniers` : identifiant de maison → marchandise → kilogrammes.
Il est vide au chargement, distinct de tous les autres paniers, et `{}` pour
un `World(...)` sans registre. L'emplacement reste le siège déjà déclaré
(`cell_id`, `rang`) ; un siège hors carte n'invente pas de lieu. Les fiches
gardent leurs huit champs.

Après la validation du numéro de tick et avant la fabrication,
`_appliquer_pertes_greniers` lit ces paniers sans consulter `World.maisons`,
les tables ni les vues. Les habitants n'y mangent pas. Production, fabrication,
commerce et répartition ne les remplissent ni ne les déplacent. Un panier vide
reste vide, une nourriture à zéro reste à zéro, une marchandise absente n'est
pas ajoutée, et les autres marchandises gardent leur poids.

`PERTE_GRENIER_PAR_AN` vaut 0,25. La part d'un tick est
`p = PERTE_GRENIER_PAR_AN × TICK_DURATION_DAYS / CALENDAR_DAYS_PER_YEAR`.
Sur le stock alimentaire courant `S`, le maillon retire `S × p` une fois.
Après `n` ticks sans apport, le reste est `S × (1 − p)ⁿ`. Aucun retrait annuel
ne s'ajoute. Chaque kilogramme retiré s'ajoute à `World.pertes_kg`, sans
arrondi, et ne devient ni dette ni nourriture ailleurs.

`to_dict()` ajoute `greniers` seulement pour les paniers non vides, triés par
identifiant, en copies indépendantes, et `pertes_kg` seulement si le cumul
n'est pas nul. Greniers vides et cumul nul laissent les octets antérieurs.

**Niveau 2**, plausible, jamais sourcé : le taux de perte par rongeurs et
moisissure. **Niveau 3**, pas simulé : la capacité du grenier et la
dégradation des marchandises autres que la nourriture.

## Les intentions du joueur

`recevoir_intention` de `sim/intentions.py` est l'entrée commune de
`POST /intention`, `python3 -m sim --gestes` et des routes déposées par l'IA.
La liste est fermée : `choisir_depart` appelle `deposer_intention`,
`tracer_route` dépose une route, `decouper_parcelle` une parcelle,
`poser_batiment` un bâtiment ; tout autre type lève
`IntentionRefusee("type d'intention inconnu : <repr>")` sans effet.

Le joueur dépose `{"type": "choisir_depart", "seigneurie": <id>}` par
`POST /intention`. `python3 -m forge --depart ID` continue d'appeler
directement `deposer_intention`, toujours avec le numéro entier de la terre.
La table se lit par `charger_seigneuries()` ; `cellule_du_siege` vérifie
que le siège est dans la carte. Le dépôt vérifie aussi que `identifiant_de_seigneurie(n)`
est une fiche de sorte `seigneurie` de `monde.maisons`, sinon refuse la seigneurie inconnue.
Aucune cellule ni aucun plan ne change.

Le dépôt refuse avant toute mise en attente, par `IntentionRefusee` :

- une valeur absente, booléenne, non entière ou inconnue :
  « seigneurie inconnue : <valeur reçue> » ; un siège hors carte est aussi refusé ;
- un choix déjà retenu ou en attente : « départ déjà choisi : seigneurie-<n> ».

Le choix accepté est un `ChoixDepart(identifiant)` gelé, placé dans
`World.intentions_en_attente` ; il garde le numéro entier. Il reste invisible dans `to_dict()` et les
vues. Au tick suivant, `_appliquer_intentions` vient après la validation du
numéro et avant la fabrication : elle appelle chaque intention par
`.appliquer(monde)` dans l'ordre du dépôt, puis vide la liste.
`ChoixDepart.appliquer` pose `maison_du_joueur = identifiant_de_seigneurie(self.identifiant)`
sans consulter le registre : la validation appartient au dépôt, jamais au tick.
Un numéro invalide laisse donc les intentions en attente.
Cette étape ignore les mondes d'épreuve, ne tire aucun aléa et ne lit ni
n'écrit aucune cellule. Le reste du tick ne consulte pas la maison du joueur.

`maison_du_joueur` vaut `None` au chargement. Après application, `to_dict()`
et `/monde` portent cette clé et l'identifiant du registre `seigneurie-<n>` ; sans choix, la clé est absente
et les octets comme l'empreinte restent ceux d'avant. Même graine et même
choix donnent le même monde ; un autre choix change son empreinte, sans
changer les cellules, les plans ou l'état du générateur aléatoire.

Une route se dépose avec les quatre champs obligatoires `{"type": "tracer_route", "cell": X,
"points": [[x, y], …], "largeur_m": L}` et les champs facultatifs `foyers` et `porte_cell_id`.
`foyers` vaut 1 par défaut : entier ≥ 1, sans booléen et sans borne haute.
Sinon `IntentionRefusee("foyers invalide : attendu un entier ≥ 1, reçu <repr>")`
est levée avant toute mise en attente. Tout autre champ ou champ obligatoire
absent est refusé. `cell` est un entier présent dans `World.plans`, sans booléen ;
toute cellule de la carte convient. La construction d'une `Rue` vérifie
points et largeur selon le contrat du plan ; un `PlanInvalide` devient
`IntentionRefusee("route invalide : <raison>")`. Le dépôt accepté est un
`TraceRoute(cell_id, points, largeur_m, foyers, porte_cell_id)` gelé, aux points copiés en tuples.
L'attente ne change ni les cellules, ni les plans, ni `to_dict()`.
`porte_cell_id`, absent ou `null`, laisse la route locale, sans apport commercial.
Sinon, entier ≥ 0 sans booléen, il nomme une voisine terrestre distincte : les
deux cellules doivent exister dans `world.cells` et être reliées par `world.adjacency`.
Le dépôt refuse toute porte invalide avant la file ; il ne déduit rien des points.
La porte copiée dans le geste gelé passe à la rue au tick suivant.

`TraceRoute.appliquer` reconstruit le plan avec une rue en chantier. Son
identifiant est le maximum des identifiants de rue, ou −1 si le plan est
vide, plus un. Les dépôts sur la même cellule se suivent donc sans collision.
L'écriture vit dans `sim/intentions.py` ; le moteur ne lit pas le plan.
Le dépôt et l'application de la route, de la parcelle ou du bâtiment n'écrivent
aucune cellule ; l'étape Chantiers écrit ensuite les métiers de sa seule
cellule, sans aléa. Mêmes
gestes et même graine donnent le même monde ; sans geste, les plans restent
vides et l'empreinte reste celle d'avant.

Une parcelle se dépose avec `{"type": "decouper_parcelle", "cell": X,
"rue": 0, "segment": 0, "debut_m": 5, "facade_m": 10, "profondeur_m": 20,
"cote": "gauche"}`. Ces huit champs sont obligatoires ; un absent donne
« champ manquant : X », un champ supplémentaire « champ inconnu : X ».
Seul `foyers` est facultatif, avec la même validation que pour la route.
Les refus lèvent `IntentionRefusee`, avant toute attente et sans effet,
dans cet ordre :

- `cell`, entier sans booléen présent dans les plans : « cell inconnu : <repr> » ;
- `rue`, entier sans booléen, identifiant d'une rue déjà au plan de cette
  cellule, même en chantier : « rue absente du plan : <repr> ». Une route
  en attente ne convient pas ; il faut attendre son application au tick suivant ;
- `segment`, entier sans booléen entre 0 inclus et `len(rue.points) − 1`
  exclu : « segment hors de la rue : <repr> » ;
- `debut_m`, nombre fini sans booléen ≥ 0, puis `facade_m` et `profondeur_m`,
  nombres finis sans booléen > 0 : « <champ> invalide : <repr> » ;
- `debut_m + facade_m` supérieur à la longueur euclidienne du segment,
  sans tolérance : « façade dépasse le segment : <debut> + <facade> > <longueur> ».
  Ce contrôle refuse une façade sur un segment nul avant toute division ;
- `cote`, exactement `"gauche"` ou `"droite"` : « cote invalide : <repr> » ;
- le contour passe par `Parcelle(0, contour)` ; un `PlanInvalide`, notamment
  un point devenu infini, donne « parcelle invalide : <raison> ».

Pour le segment de `a` à `b`, `L = dist(a, b)` et `u = (b − a) / L`.
La normale gauche est `n = (−u_y, u_x)`, en regardant dans le sens du tracé,
x vers l'est et y vers le nord ; à droite, on prend son opposée.
`d = largeur_m × DEMI_LARGEUR_PAR_LARGEUR`, avec la constante géométrique
à 0,5. Le contour est ordonné : `c0 = a + u·debut_m + n·d`,
`c1 = a + u·(debut_m + facade_m) + n·d`, `c2 = c1 + n·profondeur_m`,
`c3 = c0 + n·profondeur_m`. La façade borde la chaussée ; le lot va vers
l'extérieur. Sur `[[0, 0], [40, 0], [40, 25]]`, largeur 4 m, début 5 m,
façade 10 m, profondeur 20 m, au segment 0 :
`[(5, 2), (15, 2), (15, 22), (5, 22)]` à gauche,
`[(5, −2), (15, −2), (15, −22), (5, −22)]` à droite.
Au segment 1, à gauche, début 0, façade 25, profondeur 10 :
`[(38, 0), (38, 25), (28, 25), (28, 0)]`.

Le dépôt accepté est un `DecoupeParcelle(cell_id, contour, facade_m,
profondeur_m, foyers)` gelé, au contour en tuples calculé au dépôt.
L'attente ne change ni les cellules, ni les plans, ni `to_dict()`.
`DecoupeParcelle.appliquer` reconstruit le plan avec une parcelle en chantier,
identifiant maximum des parcelles (ou −1) plus 1, `en_chantier=True`,
`foyers`, `travail_fourni=0`. Le requis se calcule à l'application par
`travail_requis_de_parcelle(facade_m, profondeur_m)`, en relisant la constante.
Rues et bâtiments sont repris tels quels. Sans geste, aucune parcelle
n'entre en chantier et le monde reste identique à l'octet près.

Un bâtiment se dépose avec `{"type": "poser_batiment", "cell": X,
"parcelle": 0, "nature": "maison"}` ; `foyers` vaut 1 par défaut.
Les champs obligatoires vivent dans un seul dictionnaire par type ; un absent
ou un champ inconnu donne « champ manquant : X » ou « champ inconnu : X ».
Sans `type`, le refus reste « type d'intention inconnu : None ».
Après ces contrôles, `IntentionRefusee` refuse, dans cet ordre :

- `cell` non entière, booléenne ou absente des plans : « cell inconnu : <repr> » ;
- `parcelle` non entière, booléenne ou absente du plan de cette cellule :
  « parcelle absente du plan : <repr> ». Une parcelle en chantier convient,
  mais une découpe encore en attente doit d'abord être appliquée ;
- une parcelle portant déjà un bâtiment : « parcelle déjà bâtie : <id> » ;
- une pose en attente sur la même cellule et parcelle : « parcelle déjà promise : <id> » ;
- `nature` autre que `maison`, `scierie` ou `four`, sans tolérer casse ou espace :
  « nature inconnue : <repr> » ;
- `foyers` invalide, par le contrôle partagé des routes et parcelles.

Le dépôt accepté, `PoseBatiment(cell_id, parcelle, nature, foyers)` gelé,
attend sans changer cellules, plans ni `to_dict()`. Au tick suivant,
`PoseBatiment.appliquer` relit la parcelle ; son contour copié en tuples de
tuples devient l'emprise. Le bâtiment prend le maximum des identifiants de
bâtiment (ou −1) plus un, la parcelle, la nature et les foyers du dépôt,
`en_chantier=True`, zéro journée fournie et le requis calculé à l'application
par `travail_requis_de_batiment(emprise)`. Le nouveau `Plan` reprend rues et
parcelles telles quelles, sans écrire de cellule.

Le service dépose tout objet JSON sous `verrou_tick`. Il répond 200 avec
`{"acceptee": true, "appliquee_au_tick": <tick publié>}`, 400 pour une intention
inconnue ou mal formée, 409 pour un second choix. Tout refus, y compris un
corps illisible ou qui n'est pas un objet, rend
`{"acceptee": false, "erreur": "<raison>"}` sans avancer ni republier le monde.
Avec `--ia`, l'IA dépose par le même `recevoir_intention`, sous ce même verrou,
après les intentions du joueur déjà reçues et avant le tick.

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
s'applique au tick suivant ». Le compte rendu écrit dans
`resume.json["simulation"]["maison_du_joueur"]` l'identifiant du registre seulement après un choix appliqué ; la
photographie porte `terre_choisie`, `null` sans choix ; c'est sa seule différence.

**Niveau 1 :** les six terres et leurs attributions héritées, sans changement.
**Niveau 2 :** aucun ajout. **Niveau 3, pas simulé ici :** les lieux du joueur,
la part qu'il prélève, son dû au suzerain, et les personnes. Le grenier existe
déjà, voir « Le grenier d'une maison » ; l'ouvrir à ses lieux n'est pas simulé.
Changer de départ, sauvegarder et recharger ne sont pas simulés.


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
`fiche_de_seigneurie(numero_de_seigneurie(world.maison_du_joueur), …)`, dont l'id
reste entier, avec siège, source, cellule, habitants, production,
suzerain, sa maison (`null` si absente), ses cellules et habitants, et voisins
dans l'ordre de la fiche. Un identifiant mal formé lève `SnapshotExportError`
« seigneurie inconnue », sans modifier le monde. **Le tick ne la lit pas.**

`build_snapshot_document` et `export_snapshot` acceptent `releve_ia=None` :
aucun calcul de maisons IA ni nouvelle clé, mêmes octets et même version.
Une liste, même vide, ajoute seulement `ia = {maisons, maisons_actives_30j}`.
Les maisons suivent exactement `maisons_de_l_ia` au tick photographié, sans
la seigneurie choisie ; leurs sept champs sont complétés par `population` et `gestes`.
Les gestes `{tick, maison: {sorte, id}, intention}` filtrent le couple (`sorte`, `id`),
gardent l'ordre des dépôts acceptés, sans tri, déduplication ni arrondi, en copies indépendantes.
`simulation.ia` de `forge`, dans le résumé et le JSON affiché, reprend exactement
ce bloc construit une seule fois dans `snapshot_export.py` ; les cellules restent inchangées.

**Niveau 1 :** puissances, maisons, villes et terres avec leurs sources.
**Niveau 2, plausible :** étendue des puissances et maisons, terre réduite à
la cellule de son siège, population amorcée. **Niveau 3, pas simulé :**
frontières réelles, suzeraineté hors des seuls liens de départ du registre, et villes hors carte, déclarées sans placement.

## La carte et les terres servies, vue dérivée

`GET /carte` sert `crs` (`EPSG:3035`), `tolerance_m`, la `version` de la
carte, `cell_count`, `cells` triées par `cell_id` et `villes_hors_carte`.
Chaque cellule porte exactement `cell_id`, `contour` (toujours un
`MultiPolygon`), `relief`, `puissance`, `maison` (`id`, `nom` ou `null`)
et `villes` (`nom`, `population`, `x_m`, `y_m`), triées par nom. Les identités
et les villes viennent des mêmes vues que la photographie ; les villes
hors carte sont déclarées par leurs noms triés. Aucun tick, stock ou
population de cellule n'entre dans ce document.

Douglas-Peucker simplifie chaque anneau à `TOLERANCE_CONTOUR_M = 1000` mètres,
en gardant son premier sommet, puis arrondit ses coordonnées au mètre.
Une garde sur ce résultat exige `SOMMETS_MIN_ANNEAU = 4` points par anneau
(fermeture comprise) et conserve le point témoin. Celui-ci est le centroïde
de la carte s'il est intérieur ; certains contours concaves l'excluent déjà.
Dans ce cas, le témoin est le milieu du plus large intervalle intérieur sur
l'horizontale du centroïde, calculé par intersections selon la règle pair-impair.
Sans intervalle, la cellule est refusée explicitement. Si la simplification
perd un anneau ou le témoin, la cellule sert son contour d'origine arrondi ;
si ce repli perd encore le témoin, elle est refusée avec son `cell_id`.

Les octets de `/carte`, la vue des puissances et les tables des seigneuries,
puissances et maisons sont calculés à la première lecture de `/carte` ou
`/departs`, sous un verrou propre, puis figés pour la partie.
`GET /departs` recalcule à chaque requête `tick`, `date` et `departs` : les
fiches triées par `id`, exactement dans la forme de `terre_choisie` de la
photographie. `fiche_de_seigneurie` accepte `vue=None` : sans vue fournie,
elle recalcule les puissances ; avec la vue figée, seuls les contours et
les ancres de 1400 sont réutilisés. Les fiches dérivent des tables et du
monde sous le verrou du tick, sans cache des nombres du monde et sans
calcul supplémentaire à chaque tick. Une erreur de construction rend
`500` avec `erreur`, sans arrêter le service.

**Niveau 1 :** trait des contours de la carte figée, puissances, maisons et
villes avec leurs sources. **Niveau 2, plausible :** simplification à 1 km,
approximation de dessin, et étendue des puissances. **Niveau 3, pas simulé :**
frontières réelles, comme dans la photographie.

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
`sim.model`. Le tick lit surfaces, habitants et paniers pour limiter la
distribution intérieure ; il remet ces états d'accord avec la cellule à la fin.

Ce découpage est de **niveau 2** : le nombre de lieux et leur surface sont
plausibles, jamais sourcés. Le bourg est celui de « Ce qu'est une ville, à
l'échelle d'une cellule », vu ici par sa surface et sa part des habitants ; il
loge tous les non-paysans à l'amorçage. Les gens des villes nommées, paysans
à l'amorçage A, restent répartis selon les surfaces.
Les chemins limitent la distribution alimentaire intérieure décrite ci-dessous.
La forme, la position, les frontières et les noms des lieux ne sont pas simulés.

### Ce que porte un lieu

`EtatDeLieu`, dataclass mutable de `sim.model`, porte exactement `rang`,
`population`, `stocks`, `dette_alimentaire_kg` (flottant, défaut `0.0`) et
`duree_faim_ticks` (entier, défaut `0`), puis `maitre` (identifiant de maison,
défaut `None`). Pour les états manuels, `None` déclare une donnée absente :
aucune maison n'est devinée. Dans `World.charger`, tout lieu chargé reçoit
un maître présent dans le registre complet, historique et plausible.
La liste `Cell.lieux` rattache ces états
à leur cellule : aucun `cell_id` recopié ni `lieu_id`. La surface reste celle de la
vue `lieux_de_cellule`, jamais une deuxième donnée stockée.

La règle unique `partager(total, poids)` utilise le **plus fort reste** : les
parts exactes sont mises au plancher, puis les unités entières restantes vont
aux plus grands restes, à égalité au plus petit rang. Les rangs supérieurs à
zéro gardent des entiers ; le bourg reçoit `total − somme(des autres parts)`.
Cette soustraction conserve la fraction de kilogramme, et la somme retrouve
le total de la cellule **au bit près**. Les totaux et poids négatifs, booléens
ou non finis et une somme de poids nulle sont refusés par `LieuxInvalides`.

À l'amorçage seulement, `amorcer_lieux`, appelée par `World.charger`, lit une
fois les métiers par `lire_habitants_par_metier` de `sim.model`. Le compte
`P` de `METIER_PAYSANS` vaut zéro si ce métier est absent ; tous les autres
habitants, `M = population − P`, sont non-paysans. Les paysans se partagent
entre tous les lieux, bourg compris : `parts = partager(P, surfaces)`.
Le bourg (rang 0) reçoit `parts[0] + M`, chaque autre rang reçoit `parts[r]` :
la somme retrouve exactement la population. Des métiers non calculés (`-1`,
cellule construite sans métiers) déclarent tout le monde paysan,
`P = population`. Chaque marchandise garde `partager(total, surfaces)`.

Après la migration et avant l'avance du compteur, `repartir_sur_les_lieux`
ne lit jamais les métiers et compare chaque somme au total actuel de
la cellule : déjà d'accord, elle ne bouge pas ; sinon, le contenu actuel donne
les poids. Quand tous les lieux sont à zéro, les surfaces donnent les poids.
Une marchandise absente de la cellule disparaît de tous ses lieux : l'absence
n'est pas zéro. Une écriture sur la cellule hors du tick est suivie de même.

Une cellule construite à la main avec une liste vide reste sans lieux ; le
tick ne lui en invente pas. La dette et la faim partent à zéro dans chaque lieu,
comme dans sa cellule. Les restes de mortalité, natalité et migration restent
à la cellule. Ce partage est de **niveau 2**, plausible, jamais sourcé ; aucun mouvement propre aux lieux
n'est simulé (niveau 3).

Le service les publie. `GET /lieu?cell=X` porte `lieux`, rangés par rang,
chacun avec exactement `rang`, `surface_km2`, `population` et `stocks`. Ils
sont lus par `lieux_en_photographie`, la fonction même qui remplit les lieux
de la photographie, **sans arrondi** : la somme de leurs paniers égale le
panier du monde au bit près, pas le panier arrondi en tête de la réponse.
Ces octets sont construits dans `EtatPublie`, avec la photographie du tick,
dans le même appel que la population, le panier et les foyers. Un lieu publié
ne porte aucun `cell_id` recopié ni `lieu_id` : son identité est le couple
(`cell_id` de la réponse, `rang`). Des lieux qui ne correspondent pas au
découpage lèvent `SnapshotExportError` : le service ne publie jamais une
liste inventée. `/monde` reste léger et ne les porte pas.

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

**Sans lieux, avec carte.** Le nombre d'habitants que le moteur compte au **rang 0** est
`population × part_miniere_de(gisements, facteurs_richesse_extraction())`.
Ce calcul ne lit ni la population ni les stocks persistés des lieux : il
utilise les totaux cellulaires et les surfaces. Les villes historiques
nommées ne sont pas comptées au bourg.

Ce nombre reste la part minière du moteur. Après des ticks, un écart avec le
bourg de la vue est possible : celle-ci compte les métiers non paysans,
dont les variations suivent le prorata des foyers. La distribution nourrit
le rang 0 selon la part minière, sans consulter la vue ni les métiers.

À chaque consommation sans lieux, le panier alimentaire se partage selon
les surfaces : pour un stock `S` (sentinelle −1 lue comme 0), une surface
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
tracé des chemins et intégration des villes nommées dans le bourg.

**Avec carte et lieux.** Chaque lieu reçoit `récolte × surface / area_km2`, dans
les deux chemins de production, sans changer la récolte cellulaire. Avant de
manger, `repartir_sur_les_lieux` aligne nourriture et habitants sur la cellule :
le commerce et les écritures se répartissent à proportion du contenu actuel,
ou par surface si tous les lieux sont vides. Chaque lieu mange dans son panier
`min(nourriture, population × ration)`, sentinelle −1 lue comme zéro.
L'écart avec la part minière n'intervient plus : le bourg mange selon `lieux[0].population`.

Chaque champ a un chemin vers le bourg, de capacité `c = capacite_chemins_interieurs_kg(1, facteur_transport)`.
La demande est le manque du bourg plus la somme des `min(manque_champ, c)`.
Le pot prend le reste du bourg, puis les surplus des champs par rang croissant,
au plus `c` chacun, jusqu'à couvrir la demande. Le bourg est servi d'abord,
puis les champs par rang croissant, au plus `c` chacun ; le restant reste au bourg.

Si un lieu manque et qu'un autre garde de la nourriture, la pénurie est la somme
des manques : la dette augmente d'autant, sans remboursement ancien, et le panier
cellulaire devient la somme des restes. Sinon, le calcul cellulaire reste identique
au bit près, remboursement physique compris. Les paniers finaux sortent de
`partager(total, restes)`, ou des surfaces si les restes sont nuls : leur somme
retrouve exactement la cellule, en `Fraction` aussi. Un lieu unique ne calcule
aucune capacité ; des chemins infinis rendent le calcul gratuit au bit près.
Récolte par surface, étoile et ordre de
service sont de niveau 2, plausibles, jamais sourcés.

Chaque lieu porte aussi sa dette et sa durée de faim, de niveau 2. Avant
consommation, si la somme des dettes locales diffère de la dette cellulaire
(`−1` lu comme zéro), `partager` les remet d'accord avec leurs dettes actuelles
comme poids, ou les surfaces si toutes sont nulles. Une dette finale nulle
met tous les lieux à zéro sans partage. En pénurie, `partager` répartit la
dette finale selon les dettes anciennes augmentées des manques finaux de
l'étoile ; sans pénurie, le remboursement se fait **à proportion des dettes**,
seulement si leur somme diffère du nouveau total. Un lieu unique porte toute
la dette. La somme retrouve la dette cellulaire au bit près, en `Fraction` aussi.

Sans pénurie cellulaire, aucun lieu ne manque. Si la cellule manque mais que
les manques locaux sont tous nuls par arrondi, le bourg porte toute la pénurie.
Chaque lieu qui manque incrémente `duree_faim_ticks`, les autres reviennent à
zéro. La cellule a faim si et seulement si un de ses lieux a faim ; aucune
durée locale ne dépasse la sienne. Ces données figurent dans l'empreinte,
mais pas dans la photographie ni `/lieu`. L'IA lit désormais la faim du bourg ;
panier, dette et faim cellulaires, morts, naissances et migration restent
identiques au bit près.

---

## Les décisions et les gestes de l'IA

`sim/ia.py` décide sans écrire ni aléa, dans l'ordre de `maisons_de_l_ia` : population et faim du rang 0 positives, quelle que soit la cause. Dette, stock vide ou faim des champs ne suffisent pas.
Hors carte : aucun geste. Cellule, plan, bourg ou faim absent/non calculé : refus nommé avant tout dépôt.
Départ choisi, même en attente : exclu. Une route par couple (`sorte`, `id`) et année de `date_de_tick`, budget dérivé des dépôts acceptés. Tracé `(0, y)` à `(40, y)`, largeur 4 m, un foyer ; `y = largeur × nombre de rues`.
L'exclusion compare l'identifiant du registre : le numéro d'un `ChoixDepart` en attente est converti par `identifiant_de_seigneurie`, comme celui des lignes de seigneurie.
Paramètres relus dans `constants.py`. `jouer_ia` utilise uniquement `recevoir_intention`, JSON du joueur intact, puis copie `{tick, maison: {sorte, id}, intention}` après acceptation. `python3 -m sim --ia` joue après les gestes scriptés,
avant chaque tick. Le relevé reste hors du monde ; seul ce mode ajoute `ia` : `releve` et `maisons_actives_30j`, couples distincts
déposés dans les trente premiers jours, dérivés des ticks et de `TICK_DURATION_DAYS` ; avant trente jours, −1, même à zéro tick.
Niveau 1 : maisons et capitales inchangées. Niveau 2 : faim, borne, géométrie, coûts et bras retirés aux champs sans compensation.
Niveau 3 : efficacité alimentaire, richesse, autres gestes et personnes. Tick économique inchangé ; sans option, aucune décision ni sortie IA, y compris dans le service.

`python3 -m sim.service --ia` (ou `ServeurMonde(…, ia=True)`) active un relevé
neuf hors de `World`. Sous `verrou_tick`, `jouer_ia` précède chaque tick,
manuel ou cadencé ; les intentions du joueur déjà reçues précèdent les dépôts IA.
Un refus remet file et relevé à leur longueur initiale, sans tick ni publication :
`POST /tick` rend 500 `{"erreur": "ia : <raison>"}` ; l'horloge passe sa vitesse
à zéro, écrit la raison sur stderr et reste vivante.
`GET /ia` publie avec le monde `{tick, date, releve, maisons_actives_30j}`,
sans arrondi ; la mesure vient de `maisons_actives_30j`, −1 avant trente jours.
Sans option, cette route rend 404 et demande `--ia` ; les autres routes gardent leur forme.
La durée du tick inclut l'IA. Mesure sur la base, VPS, 06/10/2026, graine 0,
30 ticks : médianes IA ≈ 275 ms, tick ≈ 91 ms, soit environ 2,7 jours/s au plus.
Le placement des capitales par polygone est recalculé ; la cadence par défaut de 1 jour/s passe.

Cette absence sans option vaut aussi pour `python3 -m forge`. Avec `--ia`,
son relevé neuf reste hors de `World` : après validation des départs déposés,
`jouer_ia` précède chaque tick, premier compris ; zéro tick ne dépose rien.
La mesure de la photographie vient de `maisons_actives_30j` et des ticks écoulés.
La planche rejoue séparément sans intentions ; avec `--ia`, son compte rendu
déclare `planche.ia = false`. `--sans-chronique` évite ce rejeu sans IA.

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
  défaut, vrai pour une route déposée ; tout autre type est refusé),
  `foyers`, `travail_requis`, `travail_fourni` : entiers ≥ 0, sans booléens,
  tous à 0 par défaut. Le fourni ne dépasse pas le requis ; `en_chantier`
  vaut exactement `travail_fourni < travail_requis`, avec au moins un foyer
  en chantier. Une rue ancienne (0, 0, 0, pas en chantier) reste valide.
  `porte_cell_id`, entier ≥ 0 sans booléen ou `None`, est le dernier champ ;
  `Plan.to_dict()` l'omet si `None`, préservant les octets locaux et anciens,
  sinon le publie dans `/plan` et l'empreinte, sans autre identifiant spatial ;
- `parcelles` : `identifiant`, `contour` (au moins `POINTS_MIN_CONTOUR = 3`),
  `en_chantier` booléen faux par défaut, `foyers`, `travail_requis`,
  `travail_fourni` entiers ≥ 0 sans booléens, à 0 par défaut. Comme pour une
  rue, fourni ≤ requis, `en_chantier == (travail_fourni < travail_requis)`
  et au moins un foyer en chantier. Une parcelle ancienne reste valide ;
- `batiments` : `identifiant`, `parcelle` (identifiant d'une parcelle du même
  plan), `nature` (texte libre non vide), `emprise` (au moins `POINTS_MIN_CONTOUR`),
  `en_chantier` booléen faux par défaut, `foyers`, `travail_requis`,
  `travail_fourni` entiers ≥ 0 sans booléens, à 0 par défaut. Le contrat
  partagé avec rue et parcelle impose fourni ≤ requis,
  `en_chantier == (travail_fourni < travail_requis)` et au moins un foyer
  en chantier. Un bâtiment ancien reste valide ; le geste `poser_batiment`
  n'accepte que maison, scierie ou four.

Chaque point est un couple `(x, y)` de nombres finis, sans booléen ni texte.
Le repère est local au bourg : x vers l'est, y vers le nord, en mètres,
origine au centre du bourg. `PlanInvalide` nomme la donnée manquante ou
invalide : point non fini, nombre de points insuffisant, largeur nulle ou
négative, identifiant invalide ou en double, parcelle absente, nature vide.
Aucune coordonnée n'est bornée : la position et la forme du bourg dans la
cellule ne sont pas simulées.

Le plan se sérialise dans `World.to_dict()["plans"]`, sous des clés de cellule
en chaîne, triées comme celles de `"cells"`. L'empreinte du monde voit donc
son plan ; Intentions, Chantiers, Ateliers et Commerce le lisent via leurs modules. Intentions
y ajoute une rue, une parcelle ou un bâtiment ; Chantiers compte le travail
des rues, parcelles et bâtiments et écrit les métiers de leur cellule. Sans geste, l'évolution reste identique au bit près.

`GET /plan?cell=X` sert `cell_id`, `rang: 0`, `tick`, `date`, `rues`,
`parcelles` et `batiments`. Les octets sont construits dans `EtatPublie` avec
la photographie du tick : une lecture n'attend pas son calcul et ne consulte
pas le monde mutable. Un paramètre absent ou mal formé donne 400 ; une cellule
inconnue donne 404 en la nommant. Le plan ne s'ajoute ni à `/monde`, ni à
`/lieu`, ni au snapshot.

La forme du plan est de **niveau 2** : plausible, jamais sourcée. Son état
vide initial n'affirme rien. Restent de **niveau 3**, non simulés : position
et forme du bourg dans la cellule, effets locaux des rues et des maisons achevées sur le monde,
gestes de bâtiment autres que la pose (démolir, déplacer, agrandir),
et croisements des tracés. Le tracé d'une route est de niveau 2, plausible ;
son coût en journées, les bras pris aux champs et son achèvement sont de
niveau 2. La restriction à la capitale, les bornes et les doublons restent
de niveau 3, non simulés. Le découpage d'une parcelle, son coût et son
achèvement sont de niveau 2. Ses chevauchements avec d'autres parcelles,
une rue ou l'extérieur du bourg, sa propriété, son prix et son cadastre
restent de niveau 3. Aucun bâtiment ni flux ne découle encore de son achèvement.
La pose d'un bâtiment, son emprise égale au contour de sa parcelle, son coût
et son achèvement sont de niveau 2. Une emprise plus petite, plusieurs bâtiments par parcelle,
l'orientation, l'étage et les matériaux restent de niveau 3. La maison achevée loge des artisans, sans effet sur le tick ; scierie et four emploient des artisans, de niveau 2.

## Le chantier et ses bras

Règle de **niveau 2**, plausible, jamais sourcée : le déblai, le nivellement
et les fossés d’une route en terre battue demandent
`TRAVAIL_ROUTE_JOURNEES_PAR_M2 = 0,5` journées par m². La longueur est la
somme euclidienne des segments en mètres ; le requis vaut
`max(1, ceil(longueur × largeur_m × TRAVAIL_ROUTE_JOURNEES_PAR_M2))`.
La préparation d'un lot à bâtir (arpentage, bornage, défrichage et clôture)
demande `TRAVAIL_PARCELLE_JOURNEES_PAR_M2 = 0,1` journées par m², de niveau 2.
Le requis vaut `max(1, ceil(facade_m × profondeur_m × TRAVAIL_PARCELLE_JOURNEES_PAR_M2))` :
la surface est le produit exact du rectangle, sans recalcul sur les points.
Ainsi, 10 m × 20 m demandent 20 journées. La fonction relit la constante à
chaque appel. Une journée est une personne pendant un tick, soit un jour.

Les fondations, murs de pisé, charpente et couverture d'un bâtiment simple
coûtent `TRAVAIL_BATIMENT_JOURNEES_PAR_M2 = 2` journées par m² d'emprise,
de niveau 2. Le requis vaut
`max(1, ceil(aire_du_contour(emprise) × TRAVAIL_BATIMENT_JOURNEES_PAR_M2))`.
L'aire suit la formule du lacet : valeur absolue de la somme bouclée des
produits croisés `x_i × y_{i+1} − x_{i+1} × y_i`, multipliée par
`AIRE_PAR_PRODUIT_CROISE = 0,5`, moitié géométrique. Les deux fonctions
relisent leur constante à chaque appel, quel que soit le sens du contour.
Ainsi, 10 m × 20 m demandent 400 journées ; un contour plat demande 1 journée.
Ateliers (`sim/ateliers.py`) rend les artisans aux champs, puis emploie par identifiant les paysans restants des scieries et fours achevés :
`min(paysans restants, max(1, int(surface // SURFACE_M2_PAR_FOYER_ARTISAN)) × TAILLE_FOYER)`, avec 40 m² par foyer et la surface issue de `aire_du_contour(emprise)`.
Les foyers du chantier ne fixent pas cet emploi ; mineurs et ouvriers restent en poste, les ouvriers du jour reviennent le lendemain. Sans atelier, retour aux champs ; métiers non calculés : zéro emploi. Ni aléa, ni emploi stocké sur le bâtiment, ni réécriture du plan. Scierie et four utilisent les matières disponibles pour le même objet générique, sans bois ni argile dans cette base.

`sim/chantiers.py` parcourt les cellules par `cell_id`. Tous leurs `ouvriers`
redeviennent d’abord `paysans`, puis les rues en chantier, par identifiant,
après elles les parcelles en chantier, puis les bâtiments en chantier, chacun
par identifiant, prennent le minimum des bras disponibles,
de `foyers × TAILLE_FOYER` et du travail restant. Ces paysans deviennent
ouvriers ; chaque personne envoyée ajoute exactement une journée fournie.
La rue, la parcelle ou le bâtiment s’achève au requis : `en_chantier` devient faux.
La porte survit aux reconstructions par `dataclasses.replace` ; le commerce,
placé après Chantiers, bénéficie de la route dès ce tick d'achèvement.
Le dernier jour n’envoie que les journées
manquantes : aucune journée ne se crée ni ne se perd. Les métiers gardent
leur somme et la population ; non calculés (`-1`), ils n’envoient personne.
Sans travail fourni le plan n’est pas reconstruit, et sans changement les
métiers ne sont pas écrits. Sans chantier ni ouvrier, rien n’est écrit.
Le retour compte chaque envoi : clé `(cell_id, identifiant)` pour une rue,
`(cell_id, "parcelle", identifiant)` pour une parcelle et
`(cell_id, "batiment", identifiant)` pour un bâtiment, même pour zéro bras
ou pour un bâtiment qui attend sa parcelle. Un chantier achevé n'a pas d'entrée.
Un bâtiment dont la parcelle est en chantier au début de l'étape attend :
l'état est lu dans le plan d'avant l'étape. Même achevée ce jour, la parcelle
ne laisse son bâtiment prendre des bras que le tick suivant. Cette attente
concerne sa parcelle, pas les autres bâtiments de la cellule.
Le plan est reconstruit par `Plan(rues=…, parcelles=…, batiments=…)`, en mots-clés,
seulement si une rue, une parcelle ou un bâtiment reçoit du travail ; sinon
il reste le même objet. Sans geste, aucun bâtiment n'entre en chantier et
le monde reste identique à l'octet près.

La récolte du même tick lit les paysans restés aux champs. Les naissances,
morts et départs suivent le prorata des métiers, ouvriers compris ; le retour
du tick suivant remet tous les bras en commun. Le jour de l’achèvement, les
ouvriers ont travaillé ; ils reviennent le lendemain. Ils comptent dans le
bourg, dérivé des métiers non paysans. `/lieu` les publie dans `foyers` ;
`/monde` ne change pas. L’étape ne tire aucun aléa et n’a aucun état caché.

L’effet sur la récolte est faible : `BRAS_AUX_CHAMPS_PAR_KM2 = 0,1` reste.
Une cellule est immense et le chantier ne coûte de récolte que s’il retire
presque tous ses paysans ; les lieux de J3 changeront cette échelle. Âge et
sexe, nourriture propre, outils, matériaux, saison et salaire restent de
niveau 3, comme les effets locaux des rues achevées, les artisans
spécialisés et une priorité choisie par le joueur entre chantiers.

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

Les capitales déclarées dans `data/capitales-1400.json` et les maisons de
l’IA sont lues et recalculées dans `sim/capitales.py`.

La projection ellipsoïdale des ancres est définie dans `sim/projection.py` ;
leur sélection commune vit dans `sim/puissances.py` et sert `sim/maisons.py`.

Les paramètres du tick sont définis comme constantes nommées dans
`sim/constants.py`. Aucun littéral numérique de ces valeurs n'apparaît dans
les fonctions de calcul de `sim/engine.py` ou `sim/world.py` (vérifiable
via `sim/tests/test_no_hardcoded.py`).
