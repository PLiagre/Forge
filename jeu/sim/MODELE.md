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
   **Reprise des écritures extérieures** (`repartir_sur_les_lieux`) — avant le
   premier maillon qui lit les lieux, aligne leurs totaux à proportion de leur
   contenu ; aucun partage général après migration.
5. **Fabrication** (`_apply_fabrication`) — chaque matière première présente
   dans le panier d'ouverture perd 5 % de son stock, dont 60 % du poids devient
   de l'`objet`, sans bras ; les artisans façonnent ensuite le reliquat avec un budget commun.
   L'accord ciblé des marchandises façonnées clôt ce maillon, sans toucher la nourriture.
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
8. **Prélèvement** (`prelevement.prelever`) — perte des charges en route,
   arrivée au grenier, puis départ de la part de la récolte fraîche.
9. **Commerce** — prépare d'abord les **chemins intérieurs**
   (`_remplir_chemins_interieurs`) : seulement si une route achevée sans porte
   atteint un lieu, initialise les capacités par rang avec les facteurs des
   routes, pour le commerce du même tick. Le commerce (`_apply_commerce`) fait
   ensuite circuler les surplus vers les voisines en manque, sur les arêtes
   d'adjacence. Un kilogramme ne traverse
   qu'une arête par tick et ne nourrit qu'une fois. Toute marchandise du panier
   circule, pas seulement la nourriture. Une route achevée avec porte augmente
   le plafond de sa frontière dès ce tick. Arrivées et départs passent par le
   bourg (rang 0) ; les chemins des champs gardent leur ration et un plafond
   partagé entre destinataires et marchandises, de niveau 2.
10. **Consommation** (`_apply_consumption`) — le bourg ne mange que ce qu'il
   atteint, par sa part locale du panier et les chemins venus des champs.
   Ce qui manque devient une **dette** (`food_deficit_kg`), pas un oubli. Si le
   bourg manque pendant que les champs débordent, aucune dette n'est remboursée.
   Sinon, un surplus rembourse la dette, jamais plus vite que le surplus lui-même.
11. **Faim** (`_update_hunger`) — une cellule qui a *manqué* ce tick voit
   `hunger_ticks` monter ; une cellule ravitaillée exactement à son besoin,
   non.
12. **Mortalité** (`_apply_mortality`) — chaque lieu meurt de sa propre dette,
    avec son report de fraction pour ne pas devenir immortel par arrondi ;
    sans lieux, le calcul reste cellulaire.
13. **Natalité** (`_apply_natalite`) — chaque lieu rassasié et sans dette gagne
    des habitants, avec son report local ; sans lieux, le calcul reste cellulaire.
14. **Migration** (`_apply_migration`) — seuls les habitants des lieux affamés
    partent vers les voisines dont il reste de la nourriture après consommation.
    Accueil au rang 0, report migratoire cellulaire, métiers au prorata : niveau 2.
    Personne n'emporte de kilogrammes ni d'états locaux (niveau 3).
15. **Départs** (`departs.appliquer_departs`) — mieux-vivre sur une photo après
    la migration de famine ; foyers entiers, soldes simultanés, aucun bagage.
16. **Avance du compteur** (`_avancer_compteur_ticks`) — une fois tous les
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
limiter la distribution intérieure ; chaque maillon tient ensuite ses
écritures locales et cellulaires, sans partage général en fin de tick.

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
  et retour ; la part minière retire déjà des bras aux champs. La moisson demande les bras de chaque lieu,
  avec un besoin qui suit la saison agricole ; âge, sexe, outils et bêtes de trait restent non simulés.
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
(sans carte : `area_km2`). Chaque surface du lieu demande
`km² cultivés du lieu × BRAS_AUX_CHAMPS_PAR_KM2 × facteur de saison` bras.
La saison est celle du jour explicite (jour 0 compris), la moyenne annuelle pour le chemin moyen,
et 1 sans carte ou sans saison dans la production. Le facteur de bras vaut
`min(1, paysans / bras_requis)` ; les mineurs ne comptent pas et la part
minière reste appliquée. Les paysans du lieu sont ses habitants ; au bourg seul, on retire les non-paysans cellulaires (mineurs, artisans, ouvriers), avec un plancher à zéro.
Sans lieux, besoin saisonnier et paysans se calculent sur la cellule. Sous le seuil, chaque paysan retiré enlève sa part
de récolte ; au-dessus, le facteur vaut exactement 1 et rien ne change.
Métiers non calculés (`-1`) ou bras requis nuls : facteur 1, récolte inchangée.
La règle est de **niveau 2**, plausible, jamais sourcée.
`BRAS_AUX_CHAMPS_PAR_KM2 = 6,2` est relue à chaque appel, relevée de 0,1 à 6,2 par le lot #720.
Calibrage reproductible sur `World.charger(0)` : pour chaque lieu aux métiers calculés,
on divise ses paysans par ses km² cultivés multipliés par le maximum annuel du facteur
de saison de sa cellule (jours 0 à 364). Les km² suivent l'ordre surface du lieu × relief × eau × part agricole.
Au bourg, on retire les non-paysans de la cellule à sa population, plancher zéro ;
ailleurs, tous les habitants sont paysans. On garde les dénominateurs strictement positifs.
La médiane mesurée est 6,204260778 sur 6 619 lieux cultivables ; elle ne se fige pas dans un test.
À 6,2, la moitié des lieux manquent de bras à la moisson, aucun en janvier,
et 35 sur le chemin à saison moyenne. Sans chantier, sur un an numéroté,
la population finale baisse de 0,56 % et la récolte annuelle de 2,47 % face à 0,1,
sous les bornes de 1 % et 3 %. Sans emprunter les bras voisins, le manque local
change donc le monde annuel ; à bras suffisants, les octets restent exacts.
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
`GET /occupation?cell=X` publie exactement `cell_id`, `rang` (0), `tick`, `date`, `base`, `batiments` et `logement` (copie de `/lieu`, ou `null` si absent).
`batiments` contient les seules maisons achevées, par `identifiant` croissant : `capacite` comme ci-dessus, `loges` au minimum de cette capacité et du total publié restant (0 pour une maison vide, -1 sans métiers calculés).
Ces comptes sont copiés dans `EtatPublie` à la publication, sans lecture du monde mutable à la requête ; le tri est une convention de présentation, sans attribution de familles dans le monde.
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
                × facteur_agricole(1 − part minière)  # potentiel à bras suffisants
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

Le facteur de bras local multiplie chaque part de surface dans les deux maillons de production du
tick. Il suit la saison : la moisson manque de bras dans les lieux les plus sollicités.
Le plafond de survie et la production moyenne restent la récolte à bras
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

Après consommation et faim, chaque lieu vivant meurt de sa propre
`dette_alimentaire_kg`. La faim locale (`duree_faim_ticks`) dit le manque du
jour ; c'est la dette locale qui décide des décès. Son report local
`mortality_remainder`, flottant initialisé à `0.0`, conserve les fractions :

```
si dette_alimentaire_kg > 0 et population > 0 :
    deficit_par_tete = dette_alimentaire_kg / population
    taux = min(deficit_par_tete × HUNGER_DEATH_SCALE, MAX_DEATH_RATE_PER_TICK)
    brut   = population × taux + mortality_remainder
    morts  = int(brut)
    mortality_remainder = brut − morts
    population -= min(population, morts)
```

Sans dette ou sans habitants, le report reste intact. Un décès ne rembourse
aucune dette. Les morts des lieux sont totalisés : une seule application
cellulaire retire les personnes des métiers au prorata, plus forts restes
compris. La population cellulaire égale alors exactement la somme des lieux.
Un métier tombé à zéro disparaît ; les métiers ne décident pas des morts.

**Sans lieux**, le repli garde cette formule sur `food_deficit_kg` et la
population cellulaire, avec le report `Cell.mortality_remainder` et sa
sentinelle `-1.0` lue comme zéro. Avec lieux, ce report cellulaire ne commande
plus les décès et n'est pas réinitialisé. Aucun nouvel aléa n'intervient.

| Constante | Valeur | Unité | Ordre de grandeur |
|---|---|---|---|
| `HUNGER_DEATH_SCALE` | 0.005 | 1/(kg/personne) | 1 kg de dette par tête → 0,5 % de mortalité par tick. Une famine médiévale sévère est documentée à 10–30 % de mortalité annuelle sur les populations les plus touchées, soit 0,03–0,08 %/jour ; ce facteur permet à une dette de 5–10 kg/tête d'atteindre 2–5 % par jour. |
| `MAX_DEATH_RATE_PER_TICK` | 0.10 | — | Plafond de 10 % par tick : pas d'effondrement instantané, même à dette extrême. |

**Il n'y a pas de plancher `max(1, …)`.** Une famine légère ne tue plus au
moins une personne par lieu et par tick : le report de la fraction
(`mortality_remainder`, plus bas) fait ce travail correctement, sans inventer
de mort.

> Les formules antérieures — plancher de mortalité binaire, récupération de
> dette multiplicative `D × (1 − r)`, seuil de coupure `DEFICIT_ZERO_EPSILON` —
> ne sont plus décrites ici. Une formule morte décrite au présent piège le
> lot suivant. Elles sont dans l'historique git, avec les raisons de leur
> retrait dans les messages de commit.

---

## La natalité

Après la mortalité, chaque lieu vivant fait des enfants selon sa propre
abondance : sa faim locale `duree_faim_ticks` et sa dette locale
`dette_alimentaire_kg` doivent être nulles. Le report local
`natalite_remainder` est un flottant initialisé à `0.0`.

```
si duree_faim_ticks == 0 et dette_alimentaire_kg == 0 et population > 0 :
    brut       = population × naissances_par_habitant_par_tick() + natalite_remainder
    naissances = int(brut)
    natalite_remainder = brut − naissances
    population += naissances
```

La population utilisée est celle du lieu après mortalité. Un lieu vide ne
fait pas d'enfant. La faim ou la dette bloquent les naissances et conservent
son report : manger aujourd'hui ne suffit pas si la dette demeure. Ni faim
ni dette d'un autre lieu ne bloquent ses enfants. Un champ rassasié peut donc
grandir pendant que son bourg meurt ; couper les chemins peut augmenter la
population totale de la cellule. C'est une règle de niveau 2, plausible,
jamais sourcée.

Les naissances sont totalisées, puis ajoutées une fois aux métiers de la
cellule au prorata, plus forts restes compris. Les métiers ne décident pas
des naissances. Après ce maillon, la somme des lieux retrouve exactement la
population cellulaire.

| Constante | Valeur | Unité | Ordre de grandeur |
|---|---|---|---|
| `NAISSANCES_PAR_HABITANT_PAR_TICK` | 0.0002 | naissance/hab/tick | niveau 2, jamais sourcé |

**Sans lieux**, le repli conserve les conditions cellulaires
`penurie_du_tick == 0` et `food_deficit_kg == 0`, la population après mortalité
et `Cell.natalite_remainder`, sentinelle `-1.0` lue comme zéro. Avec lieux,
ce report cellulaire ne commande plus les naissances et reste intact.
Le report empêche la stérilité des petits lieux par arrondi.
La migration qui suit prélève les seuls lieux affamés et accueille au bourg,
sans déplacer leurs reports locaux ; seuls son report et le prorata des métiers
restent cellulaires.

---

## Les départs

Deux étapes successives, chacune sur sa photo. **Aucun kilogramme ne bouge avec les partants.**

### La famine

Après mortalité et natalité, la migration de famine garde les règles ci-dessous.

#### Qui part

Après mortalité et natalité, seuls les lieux vivants dont `duree_faim_ticks > 0`
fournissent des partants. La population source est la somme de leurs habitants :
un champ rassasié reste chez lui, même si son bourg manque. Sans lieu affamé,
aucun départ ni consommation du report ; une dette seule ne suffit pas.
Sans lieux, la pénurie du tick strictement positive et la population cellulaire
conservent le calcul historique.

```
brut     = habitants_affamés × FRACTION_MIGRANTE_PAR_TICK + migration_remainder
partants = int(brut)
```

| Constante | Valeur | Unité | Ordre de grandeur |
|---|---|---|---|
| `FRACTION_MIGRANTE_PAR_TICK` | 0.01 | — | part des habitants des lieux affamés qui s'en va en un tick ; niveau 2 |

Les départs se prélèvent à proportion des habitants de ces seuls lieux,
en entiers par plus forts restes, égalités par rang croissant. Aucun lieu
ne perd plus que sa population. Le report migratoire reste cellulaire.

#### Où l'on va

Tous les arrivants rejoignent le bourg, au rang 0. Vers les cellules voisines d'adjacence **dont il reste de la nourriture après
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

#### L'atomicité de la famine

Deux règles, qui font que la migration est un déplacement et non une diffusion :

- **une personne ne traverse qu'une arête par tick** ;
- **une cellule qui reçoit des arrivants n'en envoie pas le même tick.** Les
  départs d'une cellule receveuse sont annulés, pas différés. Ses habitants
  anciens restent aussi sur place ; les lieux ne sont modifiés qu'après cette annulation.

Le report de fraction (`migration_remainder`, sentinelle `-1.0`) empêche une
petite cellule affamée d'être immobile par arrondi.

Le solde de la cellule, entrées moins sorties, quitte ou rejoint ses métiers
au prorata. Les arrivants prennent les métiers de la cellule d'arrivée ;
dans une cellule sans métier, ils sont paysans. `_ajouter_par_les_foyers` ou
`_retirer_par_les_foyers` applique ce solde une seule fois.
Aucun kilo, dette, faim ni report de mortalité ou natalité ne voyage.
Départs et accueil sont de niveau 2, plausibles, jamais sourcés ; délais,
bagages et métiers propres aux lieux ne sont pas simulés (niveau 3).

### Le mieux-vivre

Après la famine, `departs.appliquer_departs` photographie les lieux habités.
La réserve nette en jours vaut (nourriture moins dette) / ration des habitants ;
la ration journalière dérive de la consommation et de `TICK_DURATION_DAYS`.
L'écart doit être strictement supérieur à `ECART_DE_DEPART_JOURS = 30`.
Par tranche entière de 30 jours, `TAUX_DE_DEPART = 0.002` donne la part quotidienne,
plafonnée par `PLAFOND_DE_DEPART = 0.01` ; les foyers entiers s'arrondissent vers le bas.
Destination : meilleur autre lieu habité de la cellule, sinon meilleur bourg habité
voisin ; égalités par `(cell_id, rang)`. Les soldes s'appliquent simultanément,
avec métiers au prorata entre cellules. Un lieu peut envoyer et recevoir sur sa photo :
les interdictions de renvoi et de double traversée ci-dessus concernent seulement la famine.
Ni kilo, dette, faim ni report ne voyage ; aucun maître ni taux de prélèvement n'est lu.
Lieux vides et cellules sans lieux ne participent pas. Aucun aléa ni partage général
après les mouvements. Niveau 2 : plausible, jamais sourcé ; délais, bagages et
métiers propres aux lieux : niveau 3, non simulés.

**Preuve annuelle à Bar.** Deux copies du même `World.charger(0)`, graine 0,
avec `random.Random(0)`, jouent 365 ticks de 0 à 364 ; seule la part de
`seigneurie-1` diffère, les autres maisons gardent la coutume. Ses routes
fixent les mêmes quatre lieux initiaux, soit 4 752 foyers complets :
- part 0,1 : 0 foyers internes, 74 foyers hors domaine ;
- part 0,6 : 0 foyers internes, 253 foyers hors domaine.
Ce sont les sorties brutes effectivement appliquées par le mieux-vivre,
en habitants divisés par `TAILLE_FOYER`, observées dans la boucle livrée,
avec sources et destinations. Les mouvements internes restent séparés ;
les arrivées ne retranchent rien aux sorties d'un lieu qui envoie aussi.
À chaque étape, leur somme concorde avec le retour mondial et leurs deltas
avec les populations, sans faire voyager stocks, dette, faim ou reports.
Cette mesure est de niveau 2, plausible, jamais sourcée.

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

### Passage par le bourg

Les besoins et surplus restent ceux de la cellule. L'offre exportable est en
outre bornée par le surplus local du bourg, puis celui des champs par rang
croissant. Chaque champ garde `population × consommation_unitaire` et son
apport est borné par `capacite_chemins_interieurs_kg(1, facteur_transport)`.
Le plafond de chaque chemin est partagé entre destinataires et marchandises
pendant ce commerce : seuls les kilogrammes effectivement expédiés le consomment.
Une quantité inaccessible reste chez sa source et ne compte pas comme transportée.
Capacité nulle : seul le surplus du bourg peut sortir ; un lieu unique ne
calcule aucun chemin. Sans lieux, le calcul cellulaire reste inchangé.
Un chemin que le commerce n'a pas ouvert ce tick compte comme une capacité
nulle, et le résidu d'arrondi d'un envoi est pris au bourg.

Arrivées terrestres et débarquements vont au panier du bourg, au rang 0 ;
départs terrestres et expéditions le quittent. Le bassin maritime est lu sur
son instantané d'ouverture : une expédition ne finance aucun débarquement du
même tick. Arêtes, quais, écrêtage du besoin et atomicité gardent leurs plafonds.
Ni dette ni faim ne sont modifiées. Passage au bourg et chemins bornés sont de
niveau 2, plausibles, jamais sourcés ; délais et pertes sont de niveau 3.

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

Chaque lieu conserve la fraction non appliquée dans son
`EtatDeLieu.mortality_remainder` (float, défaut `0.0`). Cinq habitants au
plafond produisent un mort après deux ticks ; leur voisin sans dette garde
ses habitants et son report. La formule est celle de « Le déficit alimentaire
et la mortalité ». Sans lieux seulement, `Cell.mortality_remainder` conserve
le repli et sa sentinelle `-1.0` lue comme zéro.

**Borne `N_BOUND_MORT`** : au plafond de mortalité, un lieu (ou une cellule
sans lieux) accumule au moins `MAX_DEATH_RATE_PER_TICK` mort par habitant et
par tick ; il faut donc au plus `ceil(1 / MAX_DEATH_RATE_PER_TICK) = 10` ticks
pour qu'une mort entière soit appliquée, quelle que soit sa taille.

Le même motif sert trois fois — mortalité, natalité, migration — avec un champ
de report par maillon : les deux premiers sont locaux quand il y a des lieux,
le troisième reste cellulaire. Ce ne sont pas trois règles : c'est une seule, appliquée
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

Cette valeur de retour — la pénurie du tick — commande le départ des migrants
et la natalité du repli sans lieux. Avec lieux, chaque `duree_faim_ticks` suit
son manque local ; la natalité lit cette faim et la dette du même lieu.
Un lieu exactement nourri revient à zéro, même si son voisin manque.

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

`data/personnages-1400.json` prépare les personnages réels au 1er janvier 1400 (**niveau 1**) : une fiche par entrée historique des trois tables, sièges hors carte compris, sans les maisons plausibles. Les pages publiques citées ont été consultées ; chaque identité précise la fonction exercée au départ et chaque naissance sa précision attestée.
Chaque valeur présente possède sa source (`url`, `fait`) ; chaque valeur `null` possède exactement son motif dans `lacunes`. Une identité non établie interdit d’attribuer une naissance. Les approximations et intervalles gardent la formulation de la source ; aucune année ne devient un 1er janvier certain. Saraï et Tlemcen gardent leur succession indécidable au jour de départ ; le chef du Zab reste non sourcé.
Les institutions conservent leur identifiant et leur nature : titulaire attesté ou direction collective explicitée, sans dynastie héréditaire inventée. Constantinople et Mistra ont des chefs distincts ; Prague et Heidelberg suivent les branches représentées par leurs sièges.
`sim/personnages.py` lit et valide cette table au chargement du monde ; les personnes sont décrites ci-dessous.

`World.parts` conserve séparément la fraction commune aux lieux de chaque maison, institutions et plausibles comprises, sans changer les huit champs gelés. Après attribution, chaque identifiant reçoit la coutume ; sans registre, `{}`. `to_dict()` omet la coutume et publie les autres parts triées sans arrondi (zéro compris), dans un dictionnaire indépendant ; sans différence, il omet `parts`.

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
Niveau 3 : changement de maître. Les noms plausibles sont une vue de niveau 2.
La photographie et `/lieu` portent le maître de chaque lieu ; `/monde` ne le
porte pas. Le tick ne lit ni les maîtres ni le registre et ne réattribue rien.

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

## Les personnes

Après les maîtres et leurs références aux suzerains, `World.charger` construit `personnages` (tuple trié par identifiant) et `chefs` (un lien par maison). L'identifiant initial `personne-<maison>` appartient à la personne, jamais automatiquement à son successeur. Aucun emplacement n'est ajouté : le siège reste celui de la maison.
Les identités, naissances, précisions, sources et lacunes historiques restent de **niveau 1**, sans interprétation. Une identité absente garde un lien nul motivé ; un titulaire institutionnel ne crée aucune dynastie. Chaque maison plausible reçoit le prénom et le nom de la vue existante (**niveau 2**), sans naissance ni source inventées et sans tirage aléatoire.
Un monde manuel garde `personnages=()` et `chefs={}`. `to_dict()` copie toujours ces deux ajouts en profondeur, sans lecteur ni constructeur. Le tick ne les consulte pas : habitants, économie et générateur restent indépendants. Autres familles, âge calculé, vieillissement, mort et succession restent de **niveau 3**, non simulés.

Le catalogue fermé conserve intégralement `chefs` et ajoute `familles` (cinquante-huit fiches), `liens` (compléments aux seize chefs réutilisés) et `etats` (seize états, triés par maison). **Niveau 1**, France (`grande-3`), Bretagne (`grande-28`) et Bohême (`grande-9`) : Isabeau de Bavière, Isabelle, Jeanne, Charles, Marie, Michelle, Louis et Jean de France. Les sept enfants ont pour parents Charles VI (`personne-grande-3`) et Isabeau ; Jeanne (`personne-jeanne`) reste une seule personne, épouse de Jean V (`personne-grande-28`). Sophie de Bavière (`personne-sophie-baviere`), née en 1376 (précision `annee`), épouse Venceslas depuis le 2 mai 1389. Les trois mariages sont réciproques ; aucun enfant de Jean V n'est né au départ (le premier naît en 1409).
Angleterre (`grande-1`) : Henri IV est veuf de Marie de Bohun (vers 1369/1370, morte le 4 juin 1394), mère référencée décédée sans conjoint actif. Leurs six enfants vivants sont Henri de Monmouth, Thomas, Jean et Humphrey de Lancastre, Blanche et Philippa d’Angleterre. Monmouth conserve exactement `1386 ou 1387`, précision `intervalle` ; les saisons et approximations des autres naissances restent déclarées. Jeanne de Navarre n’est pas épouse active avant le 7 février 1403 ; Edmund Leborde, né en 1401, est exclu du départ.
Écosse (`grande-2`) : Robert III et Annabella Drummond (vers 1350) sont conjoints réciproques. Marguerite, Élisabeth (vers 1372/1373, divergence sourcée), David, Marie et Jacques Stuart sont leurs enfants vivants ; Jean Stuart d’Ardgowan est fils hors mariage de Robert III, mère inconnue motivée. Robert Stuart (mort après ou vers 1393), Egidia (1417 ou « morte jeune », naissance inconnue) et Jacques de Kilbride (sans dates) restent exclus des vivants : présences indéterminées, contradictions et limites des notices conservées, sans nier leurs filiations ni affirmer une mort avant 1400. Les deux états déclarent les enfants documentés ; les conjoints des enfants non intégrés restent des lacunes, sans preuve de célibat.
Portugal (`grande-4`) : Jean Ier et Philippa de Lancastre (31 mars 1360) sont conjoints réciproques depuis le 2 février 1387. Leurs cinq enfants vivants sont Afonso (30 juillet 1390), Édouard (31 octobre 1391), Pierre (9 décembre 1392), Henri (4 mars 1394) et Isabelle (21 février 1397). Afonso vit encore : sa mort du 22 décembre 1400 ne sélectionne pas le départ. La notice portugaise diverge au 31 juillet dans son récit ; le 30 du tableau paternel et de l’infobox est retenu, divergence conservée dans la source.
Afonso de Bragance (10 août 1377) et Béatrice (vers 1380) sont les enfants hors mariage de Jean Ier et d’Inês Pires (vers 1350), jamais de Philippa. Inês reste mère référencée de présence `indeterminee`, sans conjoint actif : le tableau paternel donne « 1400 ? », son lien anglais manque de notice, la notice française dit seulement après 1390. Blanche, morte le 6 mars 1389, Jean, né le 13 janvier 1400, et Ferdinand, né en 1402, sont explicitement exclus.
Castille (`grande-5`) : Henri III et Catherine de Lancastre sont conjoints réciproques depuis 1388, sans enfant au départ (`absence_attestee`). Marie (1401), Catherine (1403) et Jean (1405) restent exclus, sans naissance programmée. Catherine conserve `1372-06-06 ou 1373-03-31`, précision `intervalle` : la note et l’infobox divergent, aucun jour choisi.
Aragon (`grande-6`) : Martin d’Aragon et Maria de Luna (vers 1358, approximation conservée malgré l’infobox) sont conjoints réciproques depuis le 13 juin 1372. Martin de Sicile, leur fils vivant, conserve `vers 1374/1376`, précision `vers` ; la notice individuelle donne l’approximation omise au tableau paternel. Jacques, Jean et Marguerite sont exclus : morts jeunes dans les notices des parents, Martin seul fils vivant dès 1391, sans jour de décès inventé. Marguerite de Prades n’est épouse active qu’en 1409. Les notices divergent sur 1390/1391 pour l’union sicilienne, non intégrée ; les conjoints des enfants et parents des conjoints restent des lacunes motivées, sans preuve de célibat.
Navarre (`grande-7`) : Charles III et Éléonore de Castille (vers 1363) restent mariés depuis 1375 malgré la séparation et le retour de 1395. Jeanne (Foix, 1382), Marie (1383 ou 1384), Blanche (1385 ou 1386), Béatrice (1386 ou 1392), Isabelle (1395 ou 1396) et Charles (1397) sont leurs six enfants établis vivants. Les jumelles de 1386 pourraient être Blanche et Béatrice : hypothèse, aucune troisième fille inventée. Lancelot (avril 1386, jour approximatif au BOE) est fils de María Miguel de Esparza ; Godofre (1384 ou 1394) est fils de Teresa. Ces deux mères restent de naissance inconnue et présence `indeterminee`, sans conjoint actif. Jeanne (Zúñiga, vers 1380) a une mère inconnue ; elle reste distincte de Jeanne (Foix), de Jeanne de France et de la future épouse d’Henri IV.
Louis (1399 ou 1402) et Marguerite (dates contradictoires autour du départ) sont exclus des vivants sans décès certain avant 1400. La jumelle non identifiée, Jeanne (Beaumont, future en 1419), Francés (cité en 1418, naissance inconnue) et Pascual (paiement à sa mère en 1395, survie inconnue) ont chacun une exclusion motivée avec les pages examinées, dont le BOE 438. Une mention postérieure ne prouve pas la vie au départ.
Grenade (`grande-8`) : Muhammad VII conserve `conjoints=lacune` et `enfants=lacune`, sources nulles. Sa notice et celle de Yusuf III (enfants évoqués après 1408) n’établissent ni identités ni naissances en 1400. Ces inconnues font partie de la couverture ; elles n’attestent ni célibat, ni veuvage, ni absence d’enfant.
Milan (`grande-10`) : Jean Galéas et Caterina Visconti (1361) sont conjoints réciproques depuis le 2 octobre 1380. Valentine (1371) est fille d’Isabelle de Valois (Vertus, 1er octobre 1348), mère référencée décédée en 1372 ou 1373 sans conjoint actif. Gian Maria (7 septembre 1388) et Filippo Maria (septembre 1392, jours 3/23 non départagés) ont pour mère Caterina ; Gabriele Maria (1385 ou 1386, contradiction entre année et âge narratif) est fils d’Agnese Mantegazza. Agnese reste de naissance inconnue, présence indéterminée et sans conjoint actif. Les trois fils morts d’Isabelle, la fille de Caterina morte le 9 juillet 1385 et Antonio (fils naturel mort enfant en 1391, distingué de ses homonymes) sont exclus. Navarre et Milan portent `union` et enfants `documentes` ; aucun mariage futur ou héritier imposé.
Naples (`grande-11`) : Ladislas reste sans conjoint actif. Costanza Chiaramonte est exclue après l’annulation établie (1392 dans la notice anglaise, 1393 chez Treccani) ; Marie de Lusignan est future (1403 contre arrivée et noces en 1402), comme Marie d’Enghien. Le projet avec la fille de Bayezid ne devient jamais une union. `conjoints=lacune` déclare la limite du schéma sans catégorie d’annulation, sans veuvage fictif. Rinaldo/Reynold et Marie de Durazzo, enfants hors mariage sans dates ni mères établies, sont exclus des vivants pour présence indéterminée ; `enfants=lacune`, sans confondre mariages sans enfant et descendance totale.
Savoie (`grande-12`) : une seule Marie de Bourgogne (`personne-marie-bourgogne`), née en 1386, précision `annee` ; septembre reste probable. Amédée VIII et Marie sont conjoints réciproques, état `union` : contrat de 1386, procuration du 30 octobre 1393, rencontre en 1401 et arrivée en 1403 restent distincts. Les décès divergents de Marie (1422/1428) prouvent sa présence au départ sans programmer sa mort. Les neuf enfants sont exclus individuellement comme futurs : Marguerite I (1405), Antoine I (1407), Antoine II (1408), Marie (1411), Amédée (1412), Louis (1413), Bonne (1415), Philippe (1417/1422), Marguerite II (1420). La notice française signale deux enfants supplémentaires chez FMG, inaccessible (403) : recherche non aboutie, aucune identité ni date inventée ; `enfants=lacune`, sans absence exhaustive attestée.
Kalmar (`grande-13`) : Éric garde `conjoints=lacune` par limite du schéma sans catégorie de célibat. Négociations de 1402, mariage avec Philippa le 26 octobre 1406 et union avec Cecilia après 1430 sont sourcés et exclus du départ. Philippa garde son identité anglaise et ses parents, sans nouveau conjoint. Le fils mort-né de la fin de sa vie est futur, jamais vivant en 1400 ; les notices n’excluent pas exhaustivement d’autres enfants antérieurs : `enfants=lacune`.
Pologne (`grande-14`) : Jagellon porte `veuvage` depuis la mort de Jadwiga le 17 juillet 1399 et `absence_attestee` d’enfant vivant : Élisabeth Bonifacia, née le 22 juin, est morte le 13 juillet 1399. Les deux exclusions conservent leur existence ; Anne de Cilli (1402), Élisabeth de Pilica (1417), Sophie de Holszany (1422) et les enfants Jadwiga (1408), Ladislas (1424), Casimir (1426), Casimir André (1427) sont futurs. Aucun événement imposé. Ces recherches n’ajoutent aucune filiation : bilan chronologique inchangé, trente-cinq vérifiés et quatre-vingt-un indéterminés. Parents des conjoints et relations non intégrées restent des lacunes de périmètre.
Constantinople (`grande-15`) : Manuel II et Hélène Dragaš (`personne-helena-dragas`, vers 1372) sont conjoints réciproques depuis le 10 février 1392, couronnement le lendemain ; l’état est `union`. Jean VIII (18 décembre 1392) et Théodore II (vers 1396) sont leurs enfants vivants, état `documentes`, dans l’ordre de Sphrantzès. Théodore II reste distinct de Théodore Ier (`seigneurie-3`), qui ne reçoit aucun lien et n’en perd aucun. Les parents de Manuel (Jean V, Hélène Cantacuzène), Constantin Dragaš, la mère non nommée d’Hélène et la fratrie restent des lacunes de périmètre, jamais des absences attestées. Neuf exclusions gardent l’existence et les divergences : Constantin l’aîné, Andronic et deux filles non nommées sont de présence indéterminée (morts seulement bornées entre 1400 et 1402, à Monemvasia pour l’aîné) ; la prétendue Zampia, fille de Manuel, est une filiation réfutée (Ganchou : fille naturelle non nommée de Jean V, demi-sœur de Manuel) ; Constantin XI (1404-02-08 contre 1405), Michel, Démétrios et Thomas sont futurs. Aucune présence `decedee` n’est déduite, aucun événement n’est programmé. Le bilan passe à trente-six vérifiés et quatre-vingt-six indéterminés : seule l’antériorité Manuel (1350-06-27) → Jean VIII (1392-12-18) est vérifiée ; Manuel → Théodore II et les quatre contrôles d’Hélène restent indéterminés.
Les présences explicites sont `vivante`, `decedee` ou `indeterminee` ; seules les personnes vivantes ont des conjoints actifs. Une naissance familiale inconnue reste nulle, avec source nulle et lacune motivée.
Les états distinguent `union`, `veuvage`, `lacune`, et, pour les enfants, `documentes`, `absence_attestee`, `lacune`. France : enfants documentés ; Bretagne et Bohême : absence sourcée au départ. Jeanne de Bavière, morte le 31 décembre 1386, est explicitement exclue du mariage actif. Une table vide ne prouve rien ; une présence indéterminée précise les pages examinées et leur limite. Chaque état est copié en profondeur dans `etat_familial` du chef.
Chaque identité, naissance connue, état attesté, exclusion, parenté livrée et présence initiale porte une source `url`/`fait`. Les décès cités justifient la sélection de 1400, sans programmer de mort. Les relations non étudiées sont des lacunes motivées, jamais des absences attestées ; les autres chefs gardent leurs faits et lacunes.
Le même `valider_liens_familiaux` contrôle le catalogue résolu, la construction et `valider_personnages`, sans mutation ni hasard. **Niveau 2** : enfant strictement postérieur aux parents, mère de 15 à 45 ans révolus inclus. Isabeau reste née **vers 1370** : sept antériorités paternelles vérifiées, sept antériorités maternelles et sept âges maternels indéterminés, avec motif faute de bornes exploitables. Les filiations anglaises et écossaises ajoutent trente-quatre contrôles indéterminés, soit quarante-huit avec les quatorze français. Les filiations ibériques ajoutent six antériorités paternelles et dix contrôles maternels vérifiés, puis huit indéterminés (Béatrice, Inês et Martin de Sicile) : bilan avant Navarre et Milan de vingt-trois vérifiés et cinquante-six indéterminés ; aucune approximation ne donne de borne exploitable. Navarre et Milan ajoutent treize antériorités paternelles et vingt-quatre contrôles maternels : douze vérifiés et vingt-cinq indéterminés, soit trente-cinq vérifiés et quatre-vingt-un indéterminés avant Constantinople. Les six antériorités paternelles vérifiées concernent Jeanne (Foix), Charles, Lancelot, Valentine, Gian Maria et Filippo ; les six vérifications maternelles concernent Valentine, Gian Maria et Filippo. Aucun âge exact ni règle d'âge au mariage n'est ajouté.

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

Chantiers débite aussi ce grenier après ses pertes : le maître actuel du bourg paie les journées en grain, versé dans le panier du bourg (voir « Le chantier et ses bras »).

**L'ouvrir.** `ouvrir_grenier` retire la quantité choisie à l'étape Intentions,
avant la perte des greniers. Les lieux tenus viennent de l'index des routes,
sans relire le registre ni leur maître. `sim.lieux.partager` répartit les kilos
par dette alimentaire, sinon par habitants lorsque toutes les dettes sont nulles.
Chaque part non nulle prend la même route vers son lieu. Niveau 2, plausible,
jamais sourcé : la règle de répartition ; aucune constante nouvelle.

## Le prélèvement

Au chargement, une fois les maîtres attribués et les fiches plausibles
rangées, `World.routes_des_lieux` donne pour chaque lieu tenu la route
jusqu'au grenier de son maître : le couple (`cell_id`, `rang`) mène à
`Route(maitre, siege, jours)`. `maitre` est l'identifiant de la maison,
`siege` le couple (`cell_id`, `rang`) de cette maison, `jours` un entier
au moins égal à 1. Un lieu sans maître n'entre pas dans la table. Un maître
absent de `World.maisons`, ou dont le siège est hors carte (`cell_id` is
None), lève `RouteInvalide` en nommant le couple du lieu. Un `World(...)`
d'épreuve porte `{}`. La table n'entre pas dans `to_dict` : les octets du
monde au chargement ne changent pas. Le moteur ne la recalcule pas ;
`sim/prelevement.py` lit son index par cellule et `OuvrirGrenier` ses entrées pendant le tick.

`jours = max(1, ceil(distance / VITESSE_CONVOI_KM_PAR_JOUR))`.
`VITESSE_CONVOI_KM_PAR_JOUR` est la vitesse d'un char à bœufs chargé sur
chemin de terre, niveau 2, plausible, jamais sourcé. Le lieu qui est le
siège de son maître est à 1 jour. Dans la même cellule, la distance est
celle des places ; le relief n'y freine pas, niveau 3, non simulé. Entre
deux cellules, une recherche par cellule de siège suit le plus court chemin
sur les arêtes terrestres de `World.adjacency` (les deux bouts dans
`World.cells` ; une arête vers le nœud de mer ne se prend jamais). La
longueur d'une arête est la distance des centroïdes divisée par le plus
petit des deux facteurs de `facteurs_transport_par_relief()`. Un relief
inconnu ou un centroïde absent sur une arête empruntée est une erreur qui
nomme la cellule, jamais un repli. Sans chemin terrestre,
`jours = JOURS_DE_MER` : une traversée, chargement et attente du vent
compris, niveau 2.

Temps mesuré du chargement sur srv1914711 (AMD EPYC 9354P) :
`places_du_monde` 0,35 s, la table 0,011 s, `World.charger` 1,93 s.

Après Production et avant Commerce, l'étape Prélèvement relit `World.parts`
(la coutume `PART_COUTUMIERE` vaut 0,03, niveau 2). Elle entame
chaque groupe en route de `PERTE_CONVOI_PAR_JOUR` (0,01, niveau 2), cumule
les kilos mangés par les charretiers et bêtes dans `mange_convois_kg`, puis
verse les arrivées du tick dans le grenier. Elle retire enfin la part de la
récolte fraîche de chaque lieu tenu, et la même somme de sa cellule, jamais
une part du stock ancien. La production recueille les récoltes par surface,
sans second calcul. Maître et jours viennent de la table, sans lire le
registre ni le maître du lieu ; la part se relit une fois par maison et tick.
Une part ou récolte nulle n'écrit rien, un monde sans routes ne prélève rien.

Les secours vivent dans `World.secours` : arrivée → charges par lieu
(`cell_id`, `rang`), vide au chargement et en épreuve. Un secours part au début
du tick `t`, avant Production. À Prélèvement, avant les arrivées, chaque charge
garde `1 − PERTE_CONVOI_PAR_JOUR` ; le mangé rejoint `mange_convois_kg`.
Il arrive au tick `t + jours − 1`, après exactement `jours` pertes, pour
`part × (1 − PERTE_CONVOI_PAR_JOUR)^jours`. Un lieu à un jour le mange dès le
tick de l'ouverture. L'arrivée ajoute la nourriture au lieu et à sa cellule,
par `lire/ecrire_stock_marchandise`, puis commerce et consommation la traitent
comme le reste du panier. Le grain suit le lieu même si son maître change.
Sans secours, aucun parcours supplémentaire. `to_dict()` publie seulement
les secours non vides : liste `[cell_id, rang, arrivee, kg]` triée, kilos courants
sans arrondi ; sans geste, les octets et les empreintes restent identiques.

**Calibration de la part coutumière.** Référence historique avec les bras à 0,1
et `TAUX_DE_DEPART = 0`,
sans mieux-vivre : elle ne mesure pas le monde désormais complet. Sur la graine 0, `World.charger(0)`
joue 365 ticks numérotés de 0 à 364 avec `random.Random(0)` ; toutes les
maisons ont la même part `p`, par `monde.parts = dict.fromkeys(monde.parts, p)`.
`habitants(p)` est la somme des populations des cellules après cette année.
La perte `1 − habitants(p) / habitants(0)` se mesure contre le même monde
sans prélèvement au même jour, car le monde grandit pendant l'année.
Convois compris, la part 0,03 coûte 0,96 % des habitants, la part 0,04
en coûte 1,39 %. `PART_COUTUMIERE` est la plus haute part au centième qui
coûte au plus 1 % : sa perte reste sous ce seuil et celle de
`round(PART_COUTUMIERE + 0.01, 2)` le dépasse. Prendre plus coûte davantage.
C'est une règle plausible de niveau 2, jamais sourcée : la coutume ne vide
pas les lieux ; aucune part historique d'un seigneur de 1400 n'est mesurée.
Tout changement de production, de faim ou de départs exige de remesurer.

**Calibration de la part coutumière à 6,2, sans départs.** Le même protocole
(graine 0, 365 ticks numérotés, `random.Random(0)`, `TAUX_DE_DEPART = 0`)
garde les bras du lot #720 à 6,2. À part nulle, il reste 35898495 habitants ;
la part 0,03 en laisse 35546850 (perte 0,98 %), la part 0,04 en laisse
35404646 (perte 1,38 %). La borne de 1 % reste tenue pour 0,03 et
dépassée pour 0,04. Ces mesures sont de niveau 2, plausibles, jamais sourcées.

**Mesures avec départs actifs.** Le même protocole, graine 0, 365 ticks
numérotés de 0 à 364 et `random.Random(0)`, garde le mieux-vivre actif,
avec `TAUX_DE_DEPART = 0.002`, les bras calibrés à 6,2 (lot #720)
et toutes les constantes livrées. Naissances,
morts, commerce, famine et convois restent actifs ; toutes les maisons ont
la même part. La référence est cette année active à part nulle, avec un cache
séparé de la référence historique. Mesures de niveau 2, plausibles, jamais sourcées :
- part 0,00 : 35905313 habitants ; perte 0,000000 % ; 154259 foyers déplacés.
- part 0,03 : 35554619 habitants ; perte 0,976719 % ; 132541 foyers déplacés.
- part 0,04 : 35416781 habitants ; perte 1,360612 % ; 126269 foyers déplacés.
- part 0,10 : 33692103 habitants ; perte 6,164018 % ; 78191 foyers déplacés.
Calibration tenue : perte(0,03) = 0,976719 % ≤ 1 % < perte(0,04) = 1,360612 %.
Les quatre populations décroissent strictement ; 0,10 est trop coûteux.
Les départs sont les sorties brutes du monde, en foyers entiers, observées
à chaque étape réelle et concordant avec son retour, sans déduire les arrivées.

`World.convois` regroupe les charges par tick d'arrivée, avec une liste dense
par maison et un facteur commun de perte : aucune allocation par lieu.
Un départ au tick t arrive à t + jours après exactement jours pertes :
le grenier reçoit `prélevé × (1 − PERTE_CONVOI_PAR_JOUR)^jours`.
La perte du grenier ne commence qu'au tick suivant son arrivée.
`to_dict()` publie seulement les charges en route, triées par arrivée puis
maison, et le cumul mangé non nul ; à part nulle, les octets restent ceux
d'avant. Minerai, objets, capacité et pillage des convois : niveau 3, non simulés.

**Le dû au suzerain.** `PART_DUE_AU_SUZERAIN = 0,10`, niveau 2,
plausible, jamais sourcé : la coutume fait repartir un dixième de chaque
arrivage de prélèvement vers le grenier du suzerain. Le vassal garde
l'entrée moins ce dû. Le dû part le même tick, dans `World.convois`, et
subit exactement `jours` pertes de `PERTE_CONVOI_PAR_JOUR`, ajoutées à
`mange_convois_kg`. Le suzerain lui-même vassal paie à son tour sa part.
`to_dict()` montre cette charge sous le nom du suzerain destinataire.
Les secours, les achats et les greniers remplis à la main ne paient pas de dû.
L'hommage en hommes, en argent et en service : niveau 3, pas simulé.

`World.dus_des_vassaux` est calculée une fois, juste après les routes des
lieux, avec les mêmes places et le même calcul des jours : distance des
places dans une cellule, sinon plus court chemin terrestre depuis le siège
du suzerain, ou `JOURS_DE_MER` sans chemin, au moins un jour.
`routes` associe chaque vassal routé au suzerain et aux jours ; `retenus`
porte la raison `hors_carte` du suzerain hors carte : ce dû reste chez le
vassal. `par_indice`, alignée sur les noms des routes des lieux, donne
l'indice du suzerain et les jours, ou `None`. Un suzerain inconnu, ou sur
carte mais absent des noms, lève `RouteInvalide` en nommant le vassal.
Un `World(...)` d'épreuve porte une table vide ; cette table reste hors de
`to_dict()`. Le prélèvement ne consulte que `par_indice` et la constante,
jamais le registre. Le dû passe entre greniers : lieux, cellules et
calibration restent identiques.

Temps de l'étape mesuré sur srv1914711 (AMD EPYC 9354P), graine 0,
20 ticks après 5 de chauffe, sans autre test en parallèle : médiane 4,79 ms,
moyenne 4,95 ms (avant correction des accès aux paniers : 3,71 ms et 3,96 ms ;
prototype : 3,3 ms).
Après correction des accès aux paniers, test chronométré joué seul :
médiane du tick 77,44 ms, sous 100 ms ; la base avait donné 90 à 93 ms.
Les départs ajoutent leur total une seule fois
par groupe. La production et le prélèvement lisent et écrivent les paniers
par les fonctions de `model.py` ;
le commerce réutilise les besoins du snapshot et ne parcourt pas
les arêtes pour une marchandise sans consommation, donc sans besoin ni flux.

## Les flux sur trente jours

Le monde garde une mémoire d'observation : aucune règle du tick ne la lit ;
seule la décision de part de l'IA, hors du tick, relit départs, arrivées et
lieux affamés, comme le joueur relit `/maison`. La
fenêtre `FENETRE_FLUX_TICKS` vaut trente jours, à un jour par tick ; elle
est relue à chaque appel. `World.flux` part vide au chargement, reste hors
de `to_dict` et ne se sauvegarde pas. Le registre n'ajoute aucune étape au tick.

Chaque jour porte cinq vecteurs par maison, alignés sur les noms de la table
des routes : le prélevé des lieux, le reçu au grenier après dû, le dû envoyé
au suzerain, le mangé en route (convois et secours), et le rendu quand la
maison ouvre son grenier. `en_route` garde la charge courante vers chaque
grenier : elle perd la consommation des charretiers et les arrivées, reçoit
les récoltes et le dû réexpédié. Le dû reçu par le suzerain est une arrivée
ordinaire, soumise à son propre dû s'il en a un.

`JourDeFlux.salaires` cumule par identifiant de maison le même montant qu'au débit
effectif de Chantiers, une seule fois, pour le maître actuel du bourg, même sans
registre des maisons ni route. Un changement de maître ne réattribue pas le passé ;
le tarif n'est jamais relu pour publier. Cette observation partage la même fenêtre.

Le jour garde les références des parts et récoltes lues par le prélèvement,
fraîches à chaque tick. Le prélevé d'un lieu se relit avec le même produit
part × récolte ; on n'alloue aucun tableau supplémentaire par lieu. Les
départs de famine et de mieux-vivre sont comptés en personnes brutes par
`(cell_id, rang)`, y compris à l'intérieur d'une cellule. Un lieu peut envoyer
et recevoir le même jour : les deux mouvements restent visibles. Les cellules
sans lieux, les naissances, les morts et le commerce ne sont pas comptés.
`JourDeFlux.affames` garde les `(cell_id, rang)` dont la population et
`duree_faim_ticks` sont positives une fois la cellule passée par la
consommation, la faim, la mortalité et la natalité, et seulement si la
pénurie du tick est positive. `noter_affames` fait comme `noter_personnes` :
un appel vide ne crée aucun jour, un monde sans registre ne note rien.
`affames` reste hors de `to_dict`.

`flux_de_maison` et `flux_de_lieu` filtrent les jours de tick supérieur ou
égal à `ticks_ecoules − FENETRE_FLUX_TICKS`. Ainsi, après trente ticks, le
jour 0 compte encore ; après trente et un, il ne compte plus. À la création
d'un jour, les jours antérieurs à `ticks_ecoules + 1 − FENETRE_FLUX_TICKS`
sont retirés. Une maison connue sans route rend cinq zéros mesurés ; une
maison ou un lieu inconnu est refusé. Les lecteurs servent les preuves et
le service ; `flux_des_lieux` sert `/lieu` et la photographie en une passe,
dans le même ordre des jours que `flux_de_lieu`. Aucun module de règles ne les appelle.

Le prélèvement accumule les kilos dans une liste locale, sans garde ni
écriture `array` par lieu ; les vecteurs sont convertis une fois par appel.
Les fonctions d'accès au stock sont gardées en variables locales. Les
références des récoltes et des parts restent celles lues par le prélèvement.

Médianes sur srv1914711, graine 0, cinq ticks de chauffe puis ticks 5 à 24,
le 14/10/2026, monde réel chargé puis copié :

| Comparaison | Tick | Prélèvement |
|---|---:|---:|
| Avant le lot, première comparaison en mémoire | 107,68 ms | 7,04 ms |
| Registre initial, même comparaison | 119,96 ms | 10,13 ms |
| Avant le lot (`5d984aa`), nouvelle comparaison en processus séparés | 110,21 ms | 7,42 ms |
| Registre avec variables locales et sans garde par lieu, même séance | 114,35 ms | 9,51 ms |

Chaque processus de la seconde comparaison importe ses propres fichiers,
puis joue seul les mêmes vingt ticks mesurés ; leurs `to_dict()` finaux
ont la même empreinte. Les médianes varient entre les passages.

## Les intentions du joueur

Les trois constructions exigent `maison`, identifiant texte de `World.maisons`.
Après les validations existantes, avant l'attente, la garde relit le maître actuel du rang 0 de `World.cells[cell].lieux`.
Maison mal formée/inconnue, cellule, bourg ou maître absent, maître inconnu : refus nommé sans mutation.
Une autre maison connue reçoit exactement « ce lieu n'est pas à toi : <maître> ».
Sous `verrou_tick`, HTTP exige un départ appliqué, copie le JSON et impose `maison_du_joueur` avant le dépôt journalisé ; refus 400 sans tick ni publication.
Le dépôt commun et `--gestes` exigent une maison explicite, même sans départ. Le tick ne revérifie pas le droit ; le plan ne stocke aucune propriété.

`ouvrir_grenier` accepte exactement `{"type": "ouvrir_grenier", "maison": <id du registre>, "kg": <quantité>}`.
Tout champ manquant ou inconnu, y compris `foyers`, est refusé. Les refus
suivants lèvent `IntentionRefusee`, dans cet ordre, sans changer l'attente,
les greniers ni `to_dict()` :

- « maison inconnue ou mal formée : <repr> » si l'identifiant n'est pas une chaîne ou une fiche du registre ;
- « maison sans lieu : <id> » si elle est absente de `routes_des_lieux.noms` ;
- « kg invalide : <repr> » pour un booléen, une valeur non numérique, non finie ou ≤ 0 ;
- « grenier insuffisant : <kg> kg demandés, <reste> kg disponibles » : du panier alimentaire sont retirées une par une, dans l'ordre, les ouvertures déjà en attente de cette maison ;
- « lieux sans dette ni habitants : <id> » si tous les poids sont nuls.

Un `OuvrirGrenier(maison, kg)` gelé rejoint la fin de l'attente ; deux ouvertures
s'additionnent, sans remplacement. À l'application, le retrait garde la clé
alimentaire, à `0.0` si tout est parti, puis les parts non nulles sont mises en
route. Sous `verrou_tick`, le service exige le départ appliqué (« départ non
appliqué : choisir une terre avant d'ouvrir le grenier »), puis la maison du joueur
(« maison interdite : seule la maison du joueur peut ouvrir son grenier »).
Le dépôt commun et `--gestes` acceptent toute maison connue, chemin commun de l'IA.

`fixer_part` accepte exactement `{"type": "fixer_part", "maison": <id du registre>, "part": <fraction>}`.
Niveau 2, plausible : `PART_COUTUMIERE = 0.03`, `PART_MAXIMALE = 0.6` dans `constants.py`. Le dépôt refuse champs absents ou inconnus, maison inconnue ou mal formée, booléens, valeurs non numériques, non finies ou hors bornes, sans modifier l'attente.
Le geste copié et gelé remplace à sa position celui de la même maison après validation.
Après la garde du tick, il écrit seulement `World.parts`, sans lecture du registre ni prélèvement ; l'étape existante vide l'attente, dans le même ordre qu'avant.
Sous le verrou, le service exige un départ appliqué et la maison du joueur. Le dépôt commun accepte toute maison connue ; `--gestes` garde ce chemin et sa chronologie.

`recevoir_intention` de `sim/intentions.py` est l'entrée commune de
`POST /intention`, `python3 -m sim --gestes` et des routes déposées par l'IA.
La liste est fermée : `choisir_depart` appelle `deposer_intention`,
`tracer_route` dépose une route, `decouper_parcelle` une parcelle,
`poser_batiment` un bâtiment, `fixer_part` une part, `ouvrir_grenier` une ouverture ; tout autre type lève
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
Cette étape ignore les mondes sans attente et ne tire aucun aléa.
Le choix de départ ne lit ni n'écrit aucune cellule. Le reste du tick ne consulte pas la maison du joueur.

`maison_du_joueur` vaut `None` au chargement. Après application, `to_dict()`
et `/monde` portent cette clé et l'identifiant du registre `seigneurie-<n>` ; sans choix, la clé est absente
et les octets comme l'empreinte restent ceux d'avant. Même graine et même
choix donnent le même monde ; un autre choix change son empreinte, sans
changer les cellules, les plans ou l'état du générateur aléatoire.

Une route se dépose avec les cinq champs obligatoires `{"type": "tracer_route", "maison": M, "cell": X,
"points": [[x, y], …], "largeur_m": L}` et les champs facultatifs `foyers` et `porte_cell_id`.
`foyers` vaut 1 par défaut : entier ≥ 1, sans booléen et sans borne haute.
Sinon `IntentionRefusee("foyers invalide : attendu un entier ≥ 1, reçu <repr>")`
est levée avant toute mise en attente. Tout autre champ ou champ obligatoire
absent est refusé. `cell` est un entier présent dans `World.plans`, sans booléen ;
le bourg doit être tenu par la maison déposante. La construction d'une `Rue` vérifie
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

Une parcelle se dépose avec `{"type": "decouper_parcelle", "maison": M, "cell": X,
"rue": 0, "segment": 0, "debut_m": 5, "facade_m": 10, "profondeur_m": 20,
"cote": "gauche"}`. Ces neuf champs sont obligatoires ; un absent donne
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

Un bâtiment se dépose avec `{"type": "poser_batiment", "maison": M, "cell": X,
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
photographie porte `terre_choisie`, `null` sans choix, et `maisons_du_joueur`,
absente sans choix, avec les fiches du joueur et de son suzerain.

**Niveau 1 :** les six terres et leurs attributions héritées, sans changement.
**Niveau 2 :** aucun ajout. **Niveau 3, pas simulé ici :** les lieux du joueur,
la part qu'il prélève et les personnes. Le grenier existe
déjà, voir « Le grenier d'une maison » ; `ouvrir_grenier` le rend à ses lieux.
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

Après `terre_choisie`, `maisons_du_joueur` porte `maison` et `suzerain` :
les deux fiches de `document_de_maison`, tirées d'une seule matière avec
les noms et places déjà calculés, sans arrondi, exactement comme `/maison`.
Une racine porte `suzerain: null`. Sans choix, la clé est absente et aucune
matière de maisons n'est calculée. Une maison absente du registre lève
`SnapshotExportError` « maison inconnue », avec son identifiant ; le refus
« seigneurie inconnue » reste prioritaire pour un choix mal formé.

`build_snapshot_document` et `export_snapshot` acceptent `releve_ia=None` :
aucun calcul de maisons IA ni nouvelle clé, mêmes octets et même version.
Une liste, même vide, ajoute seulement `ia = {maisons, maisons_actives_30j}`.
Les maisons suivent exactement `maisons_de_l_ia` au tick photographié, sans
la seigneurie choisie ; leurs sept champs sont complétés par `population` et `gestes`.
Les gestes copient l'entrée entière du relevé (donc `raison`, et `refus` s'il est noté), filtrent le couple (`sorte`, `id`),
gardent l'ordre du relevé, sans tri, déduplication ni arrondi, en copies profondes.
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

## Les maisons servies, vue dérivée

`GET /maisons` donne le registre complet trié par identifiant : nom, sorte,
suzerain, siège (`cell_id`, `rang`, ou `null` hors carte) et nombre de lieux
tenus. `GET /maison?id=X` donne sa fiche : identité, siège nommé et point
identique à `/lieu`, couples des lieux tenus triés, part, panier du grenier,
`flux_30j`, `absents`, tick et date. Un identifiant inconnu reçoit `404` ;
un paramètre absent, vide ou répété reçoit `400`, sans modifier le monde.
La photographie réutilise `document_de_maison` pour le joueur et son suzerain.

`MatiereMaisons`, dataclass gelée de `sim/maisons_servies.py`, copie les parts,
chaque panier et les sommes des flux à la publication dans `EtatPublie`.
Les cinq kilos sont accumulés en une passe sur les jours de la fenêtre,
dans le même ordre que `flux_de_maison`, sans arrondi. Sans route, les cinq
zéros sont une mesure. Les départs et arrivées somment les mouvements des
lieux actuellement tenus : `partis_personnes` et `arrives_personnes` comptent
des personnes, jamais des foyers. Aucun tick ne lit cette vue.
La même passe copie les salaires dans `MatiereMaisons.salaires` : la fiche ajoute
`flux_30j.salaires_payes_kg`, sans arrondi, seulement pour un payeur dans la fenêtre.
L'absence signifie aucun salaire enregistré depuis l'ouverture dans cette fenêtre,
sans prétendre mesurer avant le démarrage ; après expiration, le champ disparaît.

Les octets des fiches et de la liste sont produits à leur première lecture,
puis conservés dans `EtatPublie.octets_maisons`, initialement vide. Le verrou
propre `verrou_maisons` protège ce cache ; une lecture ne prend jamais le
verrou du tick. Une modification du monde vivant ne change donc pas une
fiche du tick déjà publié, même avant sa première lecture.

Un siège hors carte porte le nom du registre, des coordonnées nulles et sa
raison `hors_carte` dans `absents["siege"]`. Un nom plausible manquant, une
part ou un grenier absent valent `null`, avec une raison dans `absents` ;
celle du nom précise la cellule. Un panier vide et zéro lieu restent des
mesures. Les noms historiques viennent du registre (**niveau 1**) ; ceux
des maisons plausibles viennent du bloc de noms de leur cellule (**niveau 2**,
plausibles, jamais sourcés).

Mesures sur srv1914711 au tick 35, graine 0, premier départ, part 0,25,
médianes de neuf appels en pause : avant le lot, matière non construite
(aucun coût), `_construire_etat` **103,22 ms** ; après le lot,
`matiere_des_maisons` **33,31 ms**, `_construire_etat` **135,85 ms**.
`test_mesure_matiere_et_publication` (marque `chronometre`) reproduit ces mesures.

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
distribution intérieure ; chaque maillon tient ses écritures locales.

Ce découpage est de **niveau 2** : le nombre de lieux et leur surface sont
plausibles, jamais sourcés. Le bourg est celui de « Ce qu'est une ville, à
l'échelle d'une cellule », vu ici par sa surface et sa part des habitants ; il
loge tous les non-paysans à l'amorçage. Les gens des villes nommées, paysans
à l'amorçage A, restent répartis selon les surfaces.
Les chemins limitent la distribution alimentaire intérieure décrite ci-dessous.
La forme, la position et les frontières des lieux ne sont pas simulées.
Les noms sont une vue pure `sim/noms.py` hors du tick : niveau 1 pour le siège historique du bourg (seigneuries par id), sinon la ville placée de plus forte population historique, puis nom croissant ; niveau 2, plausible, jamais sourcé, pour `data/noms-1400.json`.
La première règle applicable lit puissance, religion dans la table des puissances et position du centroïde ; sans puissance, les règles géographiques déclarent puissance et religion absentes. Une absence de règle ou une liste insuffisante est refusée.
Le bloc frère `noms = {"lieux": [{"rang": R, "nom": N}], "maisons": {IDENTIFIANT: {"nom": N, "prenom_chef": P}}}` est identique dans la photographie et `/lieu`. Les maisons suivent leur fiche et leur rang initial, jamais le lieu consulté ; les historiques gardent leur nom et un prénom `null`, absence déclarée.
Les noms distincts suivent un décalage de `cell_id`, sans aléa ni réemploi, en réservant le nom historique. Seuls version des listes ou règles, données historiques, puissance/religion/position ou découpage changent les noms ; graine, tick, population, faim, maître consulté et ordre des dictionnaires sont sans effet à carte, tables et rangs identiques.

### Ce que porte un lieu

`EtatDeLieu`, dataclass mutable de `sim.model`, porte exactement `rang`,
`population`, `stocks`, `dette_alimentaire_kg` (flottant, défaut `0.0`),
`duree_faim_ticks` (entier, défaut `0`), `mortality_remainder` et
`natalite_remainder` (flottants, défaut `0.0`), puis `maitre` (identifiant de maison,
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

Avant fabrication, `repartir_sur_les_lieux` reprend les seules écritures
extérieures faites sur la cellule hors du tick. Elle ne lit jamais les métiers et compare chaque somme au total actuel de
la cellule : déjà d'accord, elle ne bouge pas ; sinon, le contenu actuel donne
les poids. Quand tous les lieux sont à zéro, les surfaces donnent les poids.
Une marchandise absente de la cellule disparaît de tous ses lieux : l'absence
n'est pas zéro. Une écriture sur la cellule hors du tick est suivie de même.
Fabrication et extraction accordent uniquement leurs marchandises modifiées,
à proportion du contenu actuel (surfaces si tout est nul). Production,
commerce, consommation et démographie tiennent leurs propres écritures locales.
Le résidu numérique est corrigé au bourg sans repondérer les lieux ; aucun
partage général après migration ne redistribue importations ou arrivants.

Une cellule construite à la main avec une liste vide reste sans lieux ; le
tick ne lui en invente pas. La dette et la faim partent à zéro dans chaque lieu,
comme dans sa cellule. Les reports de mortalité et natalité sont locaux ;
celui de migration reste cellulaire. Les deux reports locaux figurent dans
la sérialisation canonique de l'empreinte, sans ajout à la photographie ni à `/lieu`. Ce partage est de **niveau 2**, plausible, jamais sourcé ; délais et bagages des migrants
ne sont pas simulés (niveau 3).

Le service les publie. `GET /lieu?cell=X` porte `lieux`, rangés par rang,
chacun avec exactement `rang`, `surface_km2`, `population`, `stocks`, `maitre`,
`point`, `nom` et `flux_30j`.
`maitre` est l’identifiant de maison stocké, ou `None` déclaré pour un état
manuel, sans maison devinée. `nom` reprend l'entrée de même `rang` du bloc
`noms` déjà publié. `flux_30j` vient de `flux_des_lieux` : `preleve_kg` (toujours
un flottant), `partis_personnes` et `arrives_personnes`, sur trente jours,
sans arrondi. Sans noms ou flux fournis, ces champs déclarent `None` ; sans
registre, les flux fournis valent zéro. Ils sont lus par `lieux_en_photographie`, la
fonction même qui remplit les lieux de la photographie, **sans arrondi** : la somme de leurs paniers égale le
panier du monde au bit près, pas le panier arrondi en tête de la réponse.
Ces octets sont construits dans `EtatPublie`, avec la photographie du tick,
dans le même appel que la population, le panier et les foyers. Un lieu publié
ne porte aucun `cell_id` recopié ni `lieu_id` : son identité est le couple
(`cell_id` de la réponse, `rang`). Des lieux qui ne correspondent pas au
découpage lèvent `SnapshotExportError` : le service ne publie jamais une
liste inventée. `/monde` reste léger et ne les porte pas.

`GET /lieu?cell=X&bourg=1` ajoute le bloc `bourg` : exactement `rang`,
`population`, `stocks`, `duree_faim_ticks` et `tick`. Il lit le rang 0,
quelle que soit sa position dans la liste, et conserve toutes ses marchandises
sans arrondi. Son tick est celui de la réponse. Sa faim locale mesure le manque
après consommation et transport intérieur ; ni le panier restant, ni la dette,
ni la faim cellulaire ne la remplacent. Une ration complète peut laisser un
panier alimentaire vide avec une faim mesurée à zéro.
Les deux variantes sont préparées dans le même appel à `_construire_etat`,
dans `EtatPublie` ; HTTP choisit leurs octets sans relire le monde mutable.
Un rang 0 absent ou dupliqué, ou une `duree_faim_ticks` absente, négative ou
non entière, lève `SnapshotExportError` avec la cellule et la cause.
Seule la valeur unique `bourg=1` active l'extension ; une valeur vide, répétée
ou différente rend HTTP 400 sans mutation. Sans paramètre, les octets restent
identiques. La faim locale devient ainsi accessible par cette extension du
service ; la photographie reste inchangée, sans ce bloc supplémentaire.

Depuis `jeu/`, `python3 -m sim.service --epreuve --port 0 --jours-par-seconde 0 --seed 0`
charge un monde jetable en mémoire, sans lecture ni écriture de partie sauvegardée ; l'option et l'argument `ServeurMonde(..., epreuve=True)` sont désactivés par défaut.
Seul ce mode accepte `POST /epreuve/vider-panier?cell=X` : horloge arrêtée, cellule connue, lieux valides et unique bourg habité ; sinon il refuse avant mutation.
Le montage retire artificiellement la nourriture de tous les lieux, champs compris, et du total cellulaire, en conservant autres marchandises et greniers.
Il applique la consommation puis la faim existantes et republie ensemble les routes servies.
Ni tick complet ni avance du temps ou de l'aléa : le tick désigne cet état préparé.
Ce geste d'épreuve n'est jamais une intention ; le panier se lit par `/lieu?cell=X&bourg=1`.

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

**Avec carte et lieux.** Chaque lieu reçoit `récolte × surface / area_km2 × facteur_bras_du_lieu` ; paniers, total cellulaire et relevé du prélèvement portent la récolte réelle.
Le résidu flottant revient au bourg sans redistribuer les parts ; à bras suffisants, écritures et total cellulaire historiques restent exacts. La reprise
des seules écritures extérieures précède la fabrication ; ses paniers se
répartissent à proportion du contenu actuel, ou par surface si tous sont vides.
Le commerce dépose la nourriture importée au bourg, sans partage préalable. Chaque lieu mange dans son panier
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

**La route vers un lieu.** Une rue de `World.plans`, achevée (`en_chantier`
faux) et sans `porte_cell_id`, ne va pas chez le voisin : elle peut viser un
lieu de la cellule. L'extrémité qui sort du bourg est celui des deux bouts le
plus loin de l'origine du plan ; à distance égale, c'est le dernier point. Sa
direction est `atan2(y, x)`, x vers l'est, y vers le nord. Chaque lieu de
rang ≥ 1 a la direction `atan2(y_k − y_0, x_k − x_0)` de ses places. L'écart
`|atan2(sin(θ − φ), cos(θ − φ))|` est ramené dans un tour. Le lieu retenu est
le plus petit écart, au plus `ANGLE_ROUTE_INTERIEURE_DEGRES`, et le plus
petit rang à égalité. Sinon aucun lieu n'est retenu : « aucun lieu à moins de
30° (le plus proche, rang k, à X°) », « route sans direction », « un seul
lieu », ou « ancres des bourgs absentes ». La longueur de la route ne compte
pas (niveau 3).

Le lieu atteint voit la capacité de son chemin vers le bourg passer de
`c = capacite_chemins_interieurs_kg(1, facteur_transport)` à
`c × FACTEUR_ROUTE_INTERIEURE`. Deux routes vers le même lieu ne se cumulent
pas. Cette capacité sert à l'étoile (demande, envois par rang croissant,
service) et au dictionnaire `chemins` du commerce. Les facteurs se calculent
une fois par tick, après Chantiers, et seulement pour les cellules qui ont
une telle route. Sans elle, aucune place n'est calculée et le tick reste
identique au bit près. Le chemin sans lieux ne change pas.

`World.charger` garde, après l'attribution des maîtres, `ancres_des_bourgs` :
`cell_id → (siège du maître du bourg ou None, ville placée ou None)`. Cet
attribut est posé comme `populations_bourg_amorcage` : hors de `to_dict` et
de l'empreinte. Un `World` construit à la main le porte à `None` : la route
est alors « ancres des bourgs absentes », sans effet. Le tick appelle
`places_de_cellule` avec ces ancres, pour les seules cellules routées. Il ne
lit ni le maître, ni le registre, ni `attribution_villes`. Un changement de
maître reste de niveau 3.

Niveau 2 : plausible, jamais sourcé. Mesure, graine 0, 30 ticks, VPS,
11/10/2026 : la première cellule où le bourg a faim pendant qu'un champ
garde du grain est la 1241, champ de rang 1 à −124°. Sans route, 5 ticks de
faim du bourg et 14 375,3 kg de pénurie ; avec la route vers ce champ, 0 et
0. Sur cette machine (Linux 6.8.0-137-generic, x86_64, AMD EPYC 9354P), un
tick avec dix cellules routées vers un lieu, graine 0, a une médiane de
96,5 ms (sept ticks, après un tick d'échauffement).

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
panier, dette et faim cellulaires restent leurs totaux. Morts et naissances
suivent chaque lieu et ses reports locaux ; leurs totaux rejoignent les métiers
au prorata. La migration prélève les lieux affamés et accueille au rang 0,
sans déplacer dette, faim ou reports locaux. Son report reste cellulaire ;
les métiers suivent une seule fois le solde au prorata, sans partage général final.

---

## Les décisions et les gestes de l'IA

`sim/ia.py` décide sans écrire ni aléa, dans l'ordre de `maisons_de_l_ia` : population et faim du rang 0 positives, quelle que soit la cause. Dette, stock vide ou faim des champs ne suffisent pas.
Le JSON porte la maison qui décide (`grande-<id>` ou `identifiant_de_seigneurie`). Un bourg tenu par une autre maison connue ne produit aucune proposition et ne consomme aucun budget ; maître absent ou inconnu : refus nommé avant tout dépôt.
Hors carte : aucun geste. Cellule, plan, bourg ou faim absent/non calculé : refus nommé avant tout dépôt.
Départ choisi, même en attente : exclu. Une route par couple (`sorte`, `id`) et année de `date_de_tick`, budget dérivé des entrées du relevé, refus compris. Tracé `(0, y)` à `(40, y)`, largeur 4 m, un foyer ; `y = largeur × nombre de rues`.
L'exclusion compare l'identifiant du registre : le numéro d'un `ChoixDepart` en attente est converti par `identifiant_de_seigneurie`, comme celui des lignes de seigneurie.
Paramètres relus dans `constants.py`. `jouer_ia` décide tout avant le premier dépôt et n'utilise que `recevoir_intention`, JSON du joueur intact. Chaque proposition porte une `raison` lue avant tout dépôt : `regle` (`route_si_bourg_affame`), `bourg` (`population`, `duree_faim_ticks`, `dette_alimentaire_kg`, `nourriture_kg`, sans arrondi), `champs_nourriture_kg` (rangs 1 à n, dans l'ordre, sans somme), `grenier_nourriture_kg` (panier du registre, `grande-<id>` ou `identifiant_de_seigneurie` ; −1 s'il manque ; une marchandise absente pèse zéro), `chantiers_en_cours` (`rues`, `parcelles`, `batiments`) et `departs` (−1). Une acceptation ajoute `{tick, maison, intention, raison}` ; `IntentionRefusee` ajoute la même entrée avec `refus` (le message), rien n'est déposé, la maison suivante joue. Une donnée absente reste levée avant tout dépôt. `python3 -m sim --ia` joue après les gestes scriptés,
avant chaque tick. Le relevé reste hors du monde ; seul ce mode ajoute `ia` : `releve` et `maisons_actives_30j`, couples distincts
déposés dans les trente premiers jours, refus ignorés, dérivés des ticks et de `TICK_DURATION_DAYS` ; avant trente jours, −1, même à zéro tick.
Niveau 1 : maisons et capitales inchangées. Niveau 2 : faim, borne, géométrie, coûts et bras retirés aux champs sans compensation.
Niveau 3 : efficacité alimentaire, richesse, autres gestes et personnes. La raison d'une route porte des départs à −1 : ce geste ne les compte pas. La part, elle, compte les départs. Tick économique inchangé ; sans option, aucune décision ni sortie IA, y compris dans le service.

Une fois par mois, une maison qui tient des lieux règle sa part. C'est de
niveau 2, plausible, jamais sourcé. Le jour est `crc32` de sa clé modulo
`FENETRE_FLUX_TICKS` ; la fenêtre des flux doit être pleine, sinon elle se
tait. Elle lit en une passe les départs, les arrivées et les lieux `affames`
de toute sa terre. Une perte nette d'au moins `TAILLE_FOYER` (départs moins
arrivées), ou un lieu affamé, baisse la part de `IA_PAS_DE_PART`. Sinon, si
le grenier est sous la réserve — `RESERVE_VOULUE_JOURS` et
`RESERVE_VOULUE_PART_DES_HABITANTS` pour une part des habitants, plus les
salaires encore dus sur les chantiers des bourgs qu'elle tient — elle la
monte d'autant, sans dépasser `PART_MAXIMALE`. La raison se nomme
`part_sur_projets_et_gens`. Le geste est `fixer_part`, déposé par
`recevoir_intention`, comme une route. Le budget des routes ne compte que
les `tracer_route` : une part déposée dans l'année ne bloque pas le tracé.
Mesure du prototype, graine 0 : environ 2 ms par maison qui décide.

Chaque jour, sans attendre le mois ni une fenêtre de flux pleine, une maison
qui tient des lieux secourt ceux qui ont faim depuis strictement plus de
`FAIM_AVANT_SECOURS_JOURS` jours (`duree_faim_ticks` × `TICK_DURATION_DAYS`)
et qui portent une dette alimentaire. Le calcul partagé de la réserve voulue
est celui de la part : `RESERVE_VOULUE_JOURS` de nourriture pour
`RESERVE_VOULUE_PART_DES_HABITANTS` des habitants, plus les salaires encore
dus sur les chantiers des bourgs tenus. Le plancher en est la moitié
(`PLANCHER_PART_DE_LA_RESERVE`). Elle ouvre au plus l'excédent au-dessus du
plancher, et au plus la dette des seuls lieux à secourir. La raison se nomme
`secours_apres_faim` et porte, sans arrondi, la liste triée `lieux`
(`cell_id`, `rang`, `duree_faim_ticks`, `dette_alimentaire_kg`),
`grenier_nourriture_kg`, `reserve_voulue_kg`, `plancher_kg` et
`dette_affamee_kg`. Le geste est `ouvrir_grenier`, déposé par
`recevoir_intention`, après la route du jour et avant l'éventuelle part
mensuelle. À sept jours juste, à dette nulle, au plancher exact, sans lieu,
hors carte ou pour la maison du joueur, elle se tait. Aucun budget annuel ou
mensuel ne l'empêche de rouvrir le lendemain. Niveau 2, plausible, jamais
sourcé. Le réglage de la part, lui, reste mensuel.

`python3 -m sim.service --ia` (ou `ServeurMonde(…, ia=True)`) active un relevé
neuf hors de `World`. Sous `verrou_tick`, `jouer_ia` précède chaque tick,
manuel ou cadencé ; les intentions du joueur déjà reçues précèdent les dépôts IA.
Une donnée absente remet file et relevé à leur longueur initiale, sans tick ni publication :
`POST /tick` rend 500 `{"erreur": "ia : <raison>"}` ; l'horloge passe sa vitesse
à zéro, écrit la raison sur stderr et reste vivante.
Un refus de dépôt (`IntentionRefusee`) n'arrête plus le tick : il est noté au relevé et la partie continue.
`GET /ia` publie avec le monde `{tick, date, releve, maisons_actives_30j}`,
sans arrondi ; la mesure vient de `maisons_actives_30j`, −1 avant trente jours.
Sans option, cette route rend 404 et demande `--ia` ; les autres routes gardent leur forme.
La durée du tick inclut l'IA. Mesure sur la base, VPS, 06/10/2026, graine 0,
30 ticks : médianes IA ≈ 275 ms, tick ≈ 91 ms, soit environ 2,7 jours/s au plus.
Le placement des capitales par polygone est recalculé ; la cadence par défaut de 1 jour/s passe.

Cette absence sans option vaut aussi pour `python3 -m forge`. Avec `--ia`,
son relevé neuf reste hors de `World` : après validation des départs déposés,
`jouer_ia` précède chaque tick, premier compris ; zéro tick ne dépose rien.
La photographie copie l'entrée entière du relevé, `raison` et `refus` compris. La mesure vient de `maisons_actives_30j` et des ticks écoulés.
La planche rejoue séparément sans intentions ; avec `--ia`, son compte rendu
déclare `planche.ia = false`. `--sans-chronique` évite ce rejeu sans IA.

## Le plan du bourg

`/plan?cell=X` ajoute `chantiers_du_jour` seulement si la cellule a été observée au dernier jour joué.
La liste porte exactement `nature`, `identifiant`, `bras`, `grain_paye_kg`, `motif_arret`, triés rue/parcelle/bâtiment puis identifiant ; les kilos ne sont pas arrondis.
Le tick et la date désignent l'état après ce jour. Ces octets sont figés dans `EtatPublie`, lisibles pendant le tick ; ni `Plan.to_dict`, ni `base`, ni `/monde` ne portent ce relevé.

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
`parcelles`, `batiments` et `base` (place, rues, maisons et foyers de 1400). Les octets des gestes sont construits dans `EtatPublie` avec
la photographie du tick : une lecture n'attend pas son calcul et ne consulte
pas le monde mutable. Un paramètre absent ou mal formé donne 400 ; une cellule
inconnue donne 404 en la nommant. Le plan ne s'ajoute ni à `/monde`, ni à
`/lieu`, ni au snapshot.

La forme du plan est de **niveau 2** : plausible, jamais sourcée. Son état
vide initial n'affirme rien. Une rue achevée sans `porte_cell_id`, dirigée
vers un lieu de la cellule, relève le chemin de ce lieu vers le bourg
(distribution intérieure, niveau 2). Restent de **niveau 3**, non simulés : position
et forme du bourg dans la cellule, les autres effets locaux des rues achevées, et ceux des maisons achevées sur le monde,
gestes de bâtiment autres que la pose (démolir, déplacer, agrandir),
et croisements des tracés. Le tracé d'une route est de niveau 2, plausible ;
son coût en journées, les bras pris aux champs et son achèvement sont de
niveau 2. Le droit de bâtir dépend du maître actuel du bourg, de niveau 2. La restriction à la seule capitale, les bornes et les doublons restent
de niveau 3, non simulés. Le découpage d'une parcelle, son coût et son
achèvement sont de niveau 2. Ses chevauchements avec d'autres parcelles,
une rue ou l'extérieur du bourg, sa propriété, son prix et son cadastre
restent de niveau 3. Aucun bâtiment ni flux ne découle encore de son achèvement.
La pose d'un bâtiment, son emprise égale au contour de sa parcelle, son coût
et son achèvement sont de niveau 2. Une emprise plus petite, plusieurs bâtiments par parcelle,
l'orientation, l'étage et les matériaux restent de niveau 3. La maison achevée loge des artisans, sans effet sur le tick ; scierie et four emploient des artisans, de niveau 2.

### Le plan de base

Règle de **niveau 2**, plausible, jamais sourcée. `World.charger` garde,
pour chaque cellule, la population du lieu de rang 0 juste après
`amorcer_lieux`, dans `populations_bourg_amorcage` : un dictionnaire
`cell_id → entier`. Cette population dépend de la graine, parce que
`_seed_population` tire sa variation au fil des cellules ; sans la garder,
rien ne se recalcule à l'identique. L'attribut est posé comme
`attribution_villes` : hors de `to_dict`, jamais lu par le tick, ni par
Chantiers, Ateliers, le logement ou les empreintes. Intentions la lit pour le
refus des gestes, et le service la sert dans `/plan`.
Un `World` construit à la main le porte à `None`. `base_de_cellule` lève
alors `BaseAbsente`, qui nomme la cause et la cellule : la base est
déclarée absente, jamais devinée. Dans ce monde sans amorçage, le dépôt
accepte les gestes sans contrôle des maisons de base. Toute autre absence
(cellule inconnue ou centroïde absent) devient un refus `IntentionRefusee`.

`sim/ville1400.py` est une vue pure. `base_de_cellule(monde, cell_id)` lit
cette population, les arêtes `land-land` et les centroïdes
(`centroid.x_m`, `centroid.y_m`, x vers l'est, y vers le nord). Une voisine
sans centroïde lève `BaseAbsente` : l'angle ne se devine pas.
`base_d_une_population(population, directions)` calcule sans monde.
`directions` est la liste des voisines `(cell_id ou None, angle en radians)`.

Rien ne se pose sur une maison de 1400 : route, parcelle et bâtiment sont
refusés avant toute mise en attente, en nommant son rang, ses foyers et la
cellule. Les voisines sont trouvées par grille ; un bord partagé ou un
recouvrement au plus égal à `TOLERANCE_CHEVAUCHEMENT_M` ne compte pas.
Un segment nul n'a pas de bande. La place libre reçoit les premiers gestes.
L'IA éprouve sa route par la même garde avant de proposer, sans écrire au
monde ni tirer d'aléa. Le dépôt ne garde aucun cache dans le monde.
Le service calcule et sérialise la base une fois par cellule à sa première
lecture, sous un verrou distinct du tick, puis assemble ses octets figés
avec ceux des gestes. Le tick ne calcule ni ne sérialise de maison de base.
Le même cache prépare `occupation.base` : `{rang, foyers}` dans l'ordre de `base.maisons`. Toutes les places initiales sont habitées (réponse A de #411), dernier foyer incomplet compris, sans réaffectation selon la population courante ni changement du logement ou des sans-logis.
`/occupation` refuse un `cell` absent, vide, répété ou non entier (400), inconnu (404), et une base absente par `BaseAbsente`, avec cellule et cause (500). Une cellule valide sans habitants peut publier des listes vides et des zéros mesurés.
Restent de niveau 3 : découper le long d'une rue de base, démolir ou déplacer
une maison de 1400, y loger quelqu'un, croiser une rue de base.

Le repère est celui du plan : x vers l'est, y vers le nord, mètres, origine
au centre du bourg. Le nombre de foyers est `ranger_en_foyers(population).nombre`,
dernier foyer incomplet compris. La place est un carré aligné sur les axes,
centré sur l'origine, de demi-côté `DEMI_COTE_PLACE_1400_M`. Aucune maison
n'y entre. Une rue principale part vers chaque voisine distincte reliée par
une arête `land-land`, à l'angle `atan2` des centroïdes, triée par angle
ramené dans [0, 2π) puis par `cell_id`. C'est un segment de largeur
`LARGEUR_RUE_1400_M`, qui part du bord de la place — là où le rayon sort du
carré, demi-côté / max(|cos|, |sin|) — et s'allonge vers l'extérieur autant
qu'il faut pour loger les foyers. Elle porte `vers_cell_id`. Règle déclarée :
une cellule sans voisine par terre reçoit une seule rue, vers l'est (angle 0),
sans `vers_cell_id`. Les ruelles sont perpendiculaires, de part et d'autre
de chaque rue principale, tous les `ESPACEMENT_RUELLES_1400_M` à partir du
bord de la place, de longueur `LONGUEUR_RUELLE_1400_M` et de largeur
`LARGEUR_RUELLE_1400_M`. Une ruelle peut croiser une autre rue : ces
croisements restent de **niveau 3**, comme pour le plan.

Jusqu'à `FOYERS_SANS_ILOTS` foyers, chaque foyer a une maison :
façade `FACADE_MAISON_1400_M` le long de la voie,
profondeur `SURFACE_M2_PAR_FOYER_LOGE / FACADE_MAISON_1400_M`, en retrait de
`RECUL_MAISON_1400_M` du bord de la chaussée, des deux côtés. Les candidats
sont triés par la distance de leur centre à l'origine, puis par la rue, puis
par le rang, et posés du centre vers l'extérieur. Un candidat qui chevauche
la place, une rue, une ruelle ou une maison déjà posée est sauté. On s'arrête
au nombre de foyers ; s'il en manque, les rues s'allongent et le calcul
recommence. Zéro foyer : la place et les rues, aucune maison. Toute
coordonnée est arrondie à `SNAPSHOT_FLOAT_DECIMALS` avant d'être éprouvée.

Au-delà du seuil, les foyers se groupent en îlots d'au plus
`MAISONS_PAR_ILOT_MAX` (20). Pour `k` foyers, la façade vaut
`FACADE_MAISON_1400_M × min(k, MAISONS_EN_FACADE_ILOT)` et la profondeur
`k × SURFACE_M2_PAR_FOYER_LOGE / façade` : 40 m² par foyer, soit 25 m × 32 m
pour un îlot plein et 5 m × 8 m pour un seul foyer. La limite
`MAISONS_EN_FACADE_ILOT` (5) évite une façade de 100 m : elle ne tiendrait
ni entre deux ruelles (37 m), ni le long d'une ruelle (60 m), et
l'allongement ne finirait jamais. Les îlots pleins se posent d'abord,
puis l'îlot du reste sur les candidats de sa propre forme, avec le même
recul, le même tri et les mêmes contrôles de chevauchement. L'allongement
compte les objets, pas les foyers. Chaque îlot reste un élément de
`maisons`, avec une `emprise` de quatre points et `foyers: k` ; leur somme
reste exacte. Sous le seuil, la base reste identique à l'octet.

`se_chevauchent` est vrai si les intérieurs de deux polygones convexes se
recouvrent de plus de `TOLERANCE_CHEVAUCHEMENT_M` (axes séparateurs). Un
côté partagé, ou un recouvrement au plus égal à la tolérance, n'est pas un
chevauchement. `emprise_de_rue` rend le rectangle d'un segment. Les voisins
d'une emprise se cherchent par une grille de pas `PAS_GRILLE_VILLE_1400_M`,
jamais par toutes les paires. Le contrat de ces deux fonctions vaut pour
des polygones convexes.

Restent de **niveau 3**, non simulés : position et forme du bourg dans la
cellule, relief, rivière, côte, enceinte, église, marché, étages, densité
qui varie, rues courbes, maisons des hameaux (rangs > 0), rues vides qu'on
rognerait ; la forme intérieure d'un îlot (cour, maisons mitoyennes,
passages) et des îlots dans une ville de 500 foyers ou moins.

Mesures avant et après le lot #565, sur la même machine, graine 0 : les
596 bases passent de 85,198 s à 7,462 s ; Paris (10322), de 0,820 s à
0,051 s. Aucun seuil de temps ne conditionne les tests.

Mesures #566, même machine, graine 0, avant → après (secondes, CPU partagé avec les tests ciblés) :
`jouer_ia`, moyenne sur 365 ticks : 0,278226 → 0,450941 ; tick du service : 0,171034 → 0,175798 (+2,8 %).
Démarrage jusqu'au premier `/monde` : 3,251089 → 4,205791 ; Paris, première lecture de `/plan` : 0,001157 → 0,057330 ; seconde : 0,001443 → 0,009289.
Dépôt de la route repliée de la preuve de récolte : 0,000093 → 0,003941. La première lecture paie le calcul et la sérialisation de la base ; le dépôt paie son contrôle ; aucun seuil dans les tests.
L'année donne 7 → 7 dépôts acceptés. Ces mesures ponctuelles ne séparent pas la charge des autres tests du coût de l'IA ; le tick ralentit de moins de 10 %.

## Le chantier et ses bras

Les maisons en `autoconstruction` sont bâties sans salaire : aucun débit du grenier ni versement aux paniers ; la consommation ordinaire continue.
Après le retour des bras, les foyers d'artisans sans logis, dernier incomplet compris, ouvrent au plus `MAISONS_OUVERTES_PAR_JOUR = 1` maison par bourg doté d'un maître, par identifiant de parcelle libre et déjà achevée. Les places promises par toute maison en chantier se déduisent du besoin avant l'affectation ; seules les maisons achevées logent réellement.
Chaque maison autonome prend au plus une personne, artisan disponible, par jour restant. Le métier `autoconstructeurs` préserve son origine et empêche Ateliers de la réemployer ; seuls ses survivants présents reviennent aux artisans au début de Chantiers le lendemain, même après achèvement. Population et somme des métiers sont conservées. Le plan publie ce marqueur, conservé après travail, seulement pour ces maisons ; les poses manuelles gardent salaire et priorités.

`World.chantiers_du_jour`, vide à l'ouverture et absent des sauvegardes, observe sans décider : chaque appel remplace le relevé, aux mêmes clés que les envois.
Les bras sont comptés à l'affectation, les kilos au salaire effectivement débité. Un chantier achevé reste observé ce jour, puis disparaît ; plusieurs ticks ne gardent que le dernier.
À zéro bras, la cause suit cette priorité au passage : `parcelle_en_chantier`, `metiers_non_calcules`, `sans_bras`, `payeur_absent`, `sans_grain`. Avec du travail, elle vaut `null`.

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
de `foyers × TAILLE_FOYER`, du travail restant et des journées payables. Ces paysans deviennent
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
il reste le même objet. Une ouverture autonome reconstruit aussi le plan ; sans candidat ni chantier, aucune écriture nouvelle.

Chaque journée coûte `SALAIRE_JOURNEE_KG = 3` kg de grain (niveau 2), relu à chaque appel.
Le maître actuel du bourg (rang 0) paie depuis `World.greniers` : `floor(stock / salaire)` borne les bras avant tout travail.
Sans lieux, bourg, maître ou grenier déclaré, aucun salaire ; une nourriture absente vaut zéro. Les cellules se partagent la réserve courante dans leur ordre. Les journées réellement fournies débitent exactement leur salaire et le versent au seul panier du bourg et au total cellulaire, deux représentations du même stock ; la reprise intérieure conserve cette destination.
Les métiers restent ceux de la cellule ; rattacher collectivement ces ouvriers au bourg est une convention de niveau 2, sans déplacement individuel. Pertes du grenier avant paiement, récolte et consommation après ; le prélèvement arrivé ensuite finance les jours suivants. Aucun convoi ni perte de salaire ici ; matériaux et argent restent hors simulation.

Mesure #641 : `python3 pc/epreuve_jalon4.py --sortie /tmp/forge-641-j4-{avant,apres}` (deux appels), graine 0, dix ticks, Zab à 0 puis gestes à 2, 3, 5 ; maison et cellule dérivées de `depart_biskra`.

| mesure | avant | après |
|---|---|---|
| route ; parcelle ; bâtiment (journées fournies/requises) | 40/80 ; 20/20 ; 15/400 | 40/80 ; 20/20 ; 10/400 |
| salaire cumulé ; grenier final (kg) | 0 ; 311,51790706477567 | 210 ; 101,98375196817031 |
| SHA-256 `monde-service.json` et `monde-rejoue.json` | 5d36f7552ede792621ff1199242535aa0bf9deca761b8aac8434e9dc16ac0039 | 3538394f432f810340efa6a1244b260b21f01b77db79559dd7af4a7cc2efb8eb |
| SHA-256 `monde-sans-gestes.json` | bdce0bb1a329e179dce66a2f736868273a7ff41c9fbecddca17f1297e3de8ed2 | bdce0bb1a329e179dce66a2f736868273a7ff41c9fbecddca17f1297e3de8ed2 |
Seule Biskra change face au témoin ; la différence des réserves finales inclut les pertes journalières et ne mesure pas le salaire.
Année sans geste (simulation : 39,08 s avant, 44,18 s après) : depuis `jeu/`, `python3 -m forge --ticks 365 --seed 0 --sortie /tmp/forge-641-annee-avant`, puis même commande vers `/tmp/forge-641-annee-apres` ; durée simulée 365 jours.
`sha256sum /tmp/forge-641-annee-{avant,apres}/monde.json` donne deux fois `954dafd53519fbf19033dac4a98c52dda0e9e328f435f58bf6ccbe323e4edb5b`.

La récolte du même tick lit les paysans restés aux champs. Les naissances,
morts et départs suivent le prorata des métiers, ouvriers compris ; le retour
du tick suivant remet tous les bras en commun. Le jour de l’achèvement, les
ouvriers ont travaillé ; ils reviennent le lendemain. Ils comptent dans le
bourg, dérivé des métiers non paysans. `/lieu` les publie dans `foyers` ;
`/monde` ne change pas. L’étape ne tire aucun aléa et n’a aucun état caché.

La constante `BRAS_AUX_CHAMPS_PAR_KM2 = 6,2` donne son poids à la moisson.
Les chantiers ordinaires prennent leurs paysans du bourg, puis des autres lieux du même maître, par rang croissant. Un lieu d'un autre maître ne fournit aucun bras. Chaque personne envoyée augmente le compte journalier `ouvriers_du_jour` de son lieu d'origine. Ce compte est remis à zéro au début de Chantiers, après le retour des ouvriers de la veille ; il n'est ni un métier ni une population, et il n'entre pas dans la sauvegarde. À la récolte du même tick, chaque lieu retranche ses ouvriers du jour de ses paysans avant le facteur de saison. Les mineurs et les artisans restent retranchés du seul bourg, ainsi que le reliquat d'ouvriers cellulaires sans origine journalière. La perte de récolte est celle du lieu qui a prêté ses bras. Âge et
sexe, nourriture propre, outils, matériaux et salaires différenciés restent de
niveau 3, comme les effets locaux des rues achevées autres que le chemin vers un lieu, les artisans
spécialisés et une priorité choisie par le joueur entre chantiers.

---

## Le moteur sans état caché

Les parts vivent dans `World.parts` : défaut relu par le module des constantes au chargement, plafond relu au dépôt ; l'application n'écrit que la part validée.

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
