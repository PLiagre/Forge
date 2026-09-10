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

1. **Extraction** — chaque gisement de la cellule sort des kilogrammes de sa
   ressource et les dépose dans le panier de la cellule.
2. **Production** — la cellule produit de la nourriture proportionnellement à
   sa surface, multipliée par un aléa de rendement du tick, par le facteur de
   sa classe de relief — une montagne ne produit pas comme une plaine — et par
   le facteur de saison du jour, tiré de la durée du jour de la cellule : on ne
   récolte pas en janvier comme en juin.
3. **Commerce** — les cellules en surplus livrent leurs voisines en manque, sur
   les arêtes d'adjacence. Un kilogramme ne traverse qu'une arête par tick et
   ne nourrit qu'une fois. Toute marchandise du panier circule, pas seulement
   la nourriture.
4. **Consommation** — chaque habitant mange sa ration. Ce qui manque devient
   une **dette** (`food_deficit_kg`), pas un oubli. Un surplus rembourse la
   dette, jamais plus vite que le surplus lui-même.
5. **Faim** — une cellule qui a *manqué* ce tick voit `hunger_ticks` monter ;
   une cellule ravitaillée exactement à son besoin, non.
6. **Mortalité** — la dette tue, avec report de la fraction d'habitant non
   encore morte pour qu'une petite cellule ne devienne pas immortelle par
   arrondi.
7. **Natalité** — une cellule rassasiée et sans dette gagne des habitants, avec
   le même report de fraction.
8. **Migration** — une part des habitants d'une cellule qui a manqué ce tick
   part vers les voisines dont il reste de la nourriture après consommation.
   Personne n'emporte de kilogrammes.

La **province** ne se stocke pas : elle se recalcule à chaque consultation
comme « le centre administratif le plus proche ». Le tick ne la
consomme pas.

L'ordre fait foi dans `sim/engine.py`, fonction `tick()`. Ce résumé le suit ;
en cas d'écart, c'est le code qui a raison et ce fichier qui a une dette.

## Ce que le moteur ne fait pas encore

La carte porte trois couches — relief, climat, gisements. **Le tick les joue
toutes les trois.** Le snapshot le dit lui-même, couche par couche.

Ce n'est pas une déclaration, c'est une **mesure**. Pour chaque couche, le
snapshot charge deux mondes identiques, en altère franchement la couche dans
l'un **avant l'amorçage**, joue trois ticks avec la même graine et compare
l'état obtenu. Différent : le moteur lit la couche. Identique au bit près :
il ne la lit pas.

Conséquence voulue, et déjà vérifiée trois fois : le jour où le tick a consommé
le relief, puis le climat, puis les gisements, `utilisee_par_le_moteur` est
passé à `true` tout seul. Personne n'a eu de constante à retourner, et personne
ne peut la retourner sans que le moteur ait changé.

**Ce que la sonde ne peut pas voir.** Elle altère une couche en
**multipliant** ses valeurs numériques. Elle est donc aveugle à toute lecture
qui serait, elle aussi, invariante par multiplication — un rapport entre deux
grandeurs de la même couche, par exemple, dont numérateur et dénominateur
seraient altérés ensemble. C'est une limite de l'instrument, à connaître quand
on lit son verdict : un `false` signifie « la sonde n'a rien vu », pas « le
moteur ne lit rien ».

Ce que le monde ne sait toujours pas faire, et qu'aucun lot n'a encore ouvert :

- **fabriquer.** Le minerai extrait reste du minerai. Il n'y a ni atelier, ni
  fonte, ni artisanat, ni transformation d'une marchandise en une autre.
- **répartir le travail.** Tout le monde fait tout : la mine tourne *en plus*
  de l'agriculture, sans occuper de bras. Le lot 044, écrit et non exécuté,
  est le premier à défaire cela.
- **naviguer.** Voir « La mer : la façade que le moteur ne lit pas ».
- **investir.** Aucune route, aucun pont, aucun port, aucun ouvrage : rien dans
  le monde ne se construit, et aucune capacité de transport ne s'améliore.
- **tenir un prix.** Il n'y a ni monnaie, ni marché, ni salaire, ni propriété.
  Le commerce déplace des kilogrammes vers qui en manque, gratuitement.
- **descendre sous la cellule.** La population est un entier agrégé : pas de
  familles, pas de personnes, pas de bâtiments, pas de quartiers.
- **dater le monde.** Le rang du jour se dérive du numéro de tick ; le monde ne
  porte aucune date, et aucune année ne s'écoule pour lui.

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

De la **part non agricole** que le moteur calcule déjà, et de rien d'autre.

Aujourd'hui cette part vaut zéro partout : tout le monde cultive, et la mine
tourne en plus. Le premier mécanisme qui la rend non nulle est le lot 044
(`un-metier-le-mineur`), écrit et non exécuté, qui fait qu'une part des
habitants d'une cellule à gisement **cesse de cultiver** pour extraire.

Conséquence directe et voulue : **tant que 044 n'est pas fusionné, le bourg
n'existe nulle part**, l'échantillon est vide, et un échantillon vide
**échoue** — il ne passe pas en silence (règle 6). Un lot de bourg se déclare
donc **bloqué** tant que 044 n'est pas là, jamais « à adapter ».

Le nom « bourg » est délibérément plus large que le mécanisme qui le porte : le
jour où un second métier existera, la vue le comptera sans être réécrite. Cela
n'autorise personne à inventer ce second métier en même temps que la vue.

### Ce qui se refuse plutôt que se devine

- **Aucune liste de villes historiques.** L'outil qui a fabriqué la carte en
  a employé pour semer la maille ; ce n'est pas une entité du moteur, et
  `data/world-1400.json` n'en porte aucune. Une ville nommée entrerait au niveau 1 de fidélité, donc
  exigerait une source : le jeu n'en a pas, et le niveau 3 ne se simule pas.
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

**Ce que B coûte, dit franchement : la distribution à l'intérieur d'une cellule
est gratuite.** La campagne nourrit son bourg sans transport, sans perte et
sans délai. C'est une entorse au troisième principe — l'économie est physique —
mais elle n'est pas ajoutée par cette décision : elle existe déjà, parce
qu'une cellule n'a qu'un seul panier de stocks pour toute sa surface. B **nomme**
cette gratuité au lieu de l'introduire. Le jour où la cellule se subdivisera,
c'est ici qu'il faudra revenir.

### Ce que le moteur ne fait toujours pas

Le bourg ne donne ni quartiers, ni bâtiments, ni familles, ni personnes, ni
salaires, ni marchés, ni prix, ni routes, ni États. Il ne change aucun nombre du
monde : c'est une vue, et **une vue ne décide rien** — le tick ne la consulte
pas, exactement comme il ne consulte pas la province.

## Déclaration explicite

**L'amorçage décrit dans ce fichier est un proxy paramétrique, pas une donnée
historique.** Aucune valeur de population ou de stock alimentaire initial ne
provient d'une source historique documentée. Conformément à la règle 10
(« l'absence de données ne s'invente pas en silence »), cette limitation est
déclarée ici de manière explicite.

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

Le rang du jour dans l'année se **dérive** du numéro de tick (`jour_de_tick`) ;
il n'est stocké nulle part et le monde ne porte pas de date. C'est de lui que
dépend le facteur de saison.

Conséquence à connaître avant d'écrire un lot : **un appelant qui ne compte pas
ses ticks n'a pas de date à donner au moteur.** Ce que le tick fait alors n'est
pas « le premier jour de l'année » — voir « Les trois régimes de production ».

---

## Population initiale par cellule

### Formule

```
population = max(0, int(area_km2 × INITIAL_POPULATION_PER_KM2 × variation))
```

où `variation = rng.uniform(SEED_POPULATION_VARIATION_LOW, SEED_POPULATION_VARIATION_HIGH)`.

### Paramètres

| Constante | Valeur | Unité | Justification |
|---|---|---|---|
| `INITIAL_POPULATION_PER_KM2` | 10.0 | hab/km² | Densité médiévale européenne moyenne (ordre de grandeur : 5–20 hab/km², Bairoch 1988) |
| `SEED_POPULATION_VARIATION_LOW` | 0.9 | — | Variation minimale autour de la densité nominale (±10 %) |
| `SEED_POPULATION_VARIATION_HIGH` | 1.1 | — | Variation maximale autour de la densité nominale (±10 %) |

**Conséquence à connaître : le monde démarre plat.** La densité ne varie que de
plus ou moins dix pour cent d'une cellule à l'autre, et cette variation est un
tirage, pas une géographie. Aucun endroit n'est peuplé parce qu'il est bon. Ce
qui différencie ensuite les cellules vient du relief, du climat et de la mort,
jamais de l'amorçage.

### Déterminisme

Deux appels à `World.charger(rng_seed=K)` avec la même graine `K` produisent
des populations initiales byte-identiques, car `rng = random.Random(rng_seed)`
initialise un générateur pseudo-aléatoire isolé (jamais de source globale).

---

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
food_stock_kg = population × FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK × INITIAL_FOOD_RESERVE_TICKS
```

Le stock de départ couvre `INITIAL_FOOD_RESERVE_TICKS` ticks de consommation
normale. Ce buffer initial est volontairement court (5 ticks = 5 jours) pour
que la dynamique de production/consommation prenne effet rapidement sans
créer une réserve artificielle trop grande.

C'est la **seule** marchandise présente au panier d'une cellule à l'amorçage.
Toutes les autres y entrent par l'extraction.

### Paramètres

| Constante | Valeur | Unité | Justification |
|---|---|---|---|
| `FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK` | 2.0 × TICK_DURATION_DAYS | kg/personne/tick | Ration journalière médiévale approx. 2 kg (céréales + substituts) × 1 jour/tick |
| `INITIAL_FOOD_RESERVE_TICKS` | 5 | ticks | Réserve de subsistance de 5 jours — suffisante pour absorber 2–3 mauvaises journées consécutives sans mort immédiate, sans masquer le comportement de long terme |

---

## Le rendement agricole et sa variabilité

### Formule (par tick)

```
yield_factor = rng.uniform(RNG_YIELD_LOW, RNG_YIELD_HIGH)
duree_jour   = duree_jour_h(jour, solstice_ete_h, solstice_hiver_h)  # de la cellule

food_produced = area_km2 × FOOD_PRODUCTION_KG_PER_KM2_PER_TICK × yield_factor
                × facteur_relief(classe de relief de la cellule)
                × facteur_saison(duree_jour)
```

Les deux derniers facteurs sont lus dans la carte, cellule par cellule. Une
cellule dont la carte ne porte pas ces données ne se voit pas attribuer une
valeur par défaut — le moteur refuse, par `ReliefInvalideError` ou
`ClimatInvalideError` (règle 10 : l'absence ne s'invente pas en silence).

**Il n'y a qu'une seule formule de production alimentaire dans `sim/`.** Le
tick lui passe un rendement tiré au sort ; le plafond de survie lui passe le
rendement moyen. C'est ce qui garantit que le plafond ne peut pas diverger de
ce que le monde produit vraiment, et c'est ce qui l'a fait suivre tout seul le
jour où le relief, puis la saison, ont modulé le rendement.

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
| un monde sans carte | ni relief ni saison — le nominal seul |
| une carte, **pas** de `numero_tick` | le relief, et le facteur de saison **moyen sur l'année** |
| une carte **et** un `numero_tick` | le relief, et la saison du jour dérivé du numéro de tick |

Le deuxième régime est le piège : un appelant sans compteur n'obtient pas
« le premier jour de l'année », il obtient une année moyennée. C'est un choix
et non un défaut — une mesure qui ne compte pas les ticks ne doit pas hériter
d'un mois d'hiver arbitraire — mais un lot qui mesure la production doit dire
lequel des trois régimes il fait jouer.

### L'équilibre que ces valeurs produisent

À 10 hab/km², la production **nominale** est de 18 kg/km²/tick et la
consommation de 20. Le monde démarre donc **au-dessus de ce qu'il nourrit**, et
le relief creuse l'écart : son facteur vaut 1 sur la plaine et descend jusqu'à
0,15, donc aucune cellule ne produit plus que le nominal, et toute cellule qui
n'est pas de plaine produit moins. La population descend jusqu'à un régime où
elle tient, et la variabilité `[0.5, 1.5]` crée des ticks de surplus qui
alimentent le commerce et des ticks de manque qui créent de la dette.

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

## L'extraction minière

Premier maillon du tick, et la seule façon dont une marchandise autre que la
nourriture entre dans le monde.

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

Ce n'est pas un défaut, c'est une absence déclarée : **il n'y a pas de demande
non alimentaire dans ce monde**, parce qu'il n'y a ni fabrication, ni métier,
ni prix. Le jour où quelque chose consommera du fer, le transport suivra sans
qu'on y touche.

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

Tous les paramètres ci-dessus sont définis comme constantes nommées dans
`sim/constants.py`. Aucun littéral numérique de ces valeurs n'apparaît dans
les fonctions de calcul de `sim/engine.py` ou `sim/world.py` (vérifiable
via `sim/tests/test_no_hardcoded.py`).
