# CAP — sept jalons jusqu'au jeu entier

> Ce fichier dit **où va Forge et dans quel ordre**. Il est court exprès : tout
> le reste en découle. Chaque lot porte le jalon qu'il sert (le jalon de son
> issue) ; un lot qui ne sert pas le jalon courant est refusé par le chef.
>
> Le **jalon courant** est le premier de la table qui n'est pas « atteint ».
> Un jalon est atteint quand sa preuve est verte **et** que sa capture est au
> journal. Le pourcentage d'un jalon se dérive de ses issues (fermées / toutes),
> jamais d'une estimation écrite à la main.

## Le constat qui commande (27 septembre 2026)

Le jeu était deux mondes qui ne se parlaient pas : `sim/` (Python, 596
cellules, vivant) et quatorze scènes Unity qui sont des visites — aucune ne lit
`sim/`. Le labo Unity portait une seconde économie (`LocalCitySimulation`), et
le contrat ville exigeait un `cityId` que [`jeu/sim/MODELE.md`](jeu/sim/MODELE.md)
interdit. Les sept jalons ci-dessous referment cette fracture d'abord, puis
montent vers la vision d'[docs/OBJECTIF.md](docs/OBJECTIF.md) : seigneur en 1400, État
industriel en 1900, **une seule simulation**.

## La règle d'un jalon

Un jalon est **jouable** : on lance quelque chose, on fait un geste, on voit le
monde répondre. Il a :

- **ce que le joueur fait** — un geste, pas une fonctionnalité ;
- **ce qu'on voit à l'écran** — ce que la capture du journal doit montrer ;
- **sa preuve** — une commande qui peut échouer (principe 5), avec sa
  contre-épreuve ;
- **sa machine** — le VPS pour `sim/` et les vues, le PC pour Unity et Blender.

## L'échelle

| # | jalon | le joueur | l'écran | état |
|---|---|---|---|---|
| 1 | **Le pont** | ouvre un lieu du monde dans Unity et laisse le temps passer | le lieu en 3D, et ses vrais chiffres (habitants, stocks, faim, date) qui bougent avec `sim/` | en cours |
| 2 | **Le geste revient** | trace une route dans le lieu | le chantier accepté au tick suivant, puis plus de kilos qui passent la frontière | à venir |
| 3 | **La nourriture traverse le lieu** | relie ses champs à son bourg | deux stocks (champs, bourg), le flux sur la route ; sans route, le bourg s'endette | à venir |
| 4 | **Des foyers** | pose un atelier, subit une disette | les foyers par métier, les départs ; une vallée qui se vide, une voisine qui grossit | à venir |
| 5 | **Le siège prélève** | fixe la part qu'il prend sur plusieurs lieux | les flux vers le siège sur la carte, son grenier ; trop prendre fait partir les gens | à venir |
| 6 | **La colonne** | lève des hommes et les fait marcher | la colonne sur la carte et sur le terrain, ce qu'elle mange, le creux qu'elle laisse | à venir |
| 7 | **1400 → 1900** | joue le siècle suivant sans changer de jeu | la ville au zoom (Unity), la carte en relief au dézoom (forge3d), la même horloge | à venir |

---

## Jalon 1 — Le pont

**Le joueur** lance `pc\Jouer.cmd`, choisit une cellule du monde (par défaut un
lieu du désert, là où vit le kit retenu), et regarde. Le temps avance d'un jour
par seconde ; il peut accélérer ou mettre en pause.

**L'écran** : la scène 3D du lieu, et un panneau qui dit, pour cette cellule,
la date du monde, les habitants, la nourriture et les autres marchandises du
panier, la faim et la dette. Les chiffres sont **ceux de `sim/`**, au même
tick : pas une copie, pas une estimation.

**La preuve** : sur le PC, une épreuve lance le service de simulation, ouvre la
scène, lit le panneau au tick N et le compare à la photographie
`py -m sim --ticks N --seed S --snapshot-json` de la même cellule. Égalité
exigée. Contre-épreuve : un service qui décale d'un tick doit la faire échouer.
La capture du panneau entre au journal.

**Ce que le jalon change dans le monde** : rien. C'est un regard. Le contrat
ville cesse de demander un `cityId` : la clé qu'Unity reçoit est `cell_id`, la
seule clé spatiale du modèle. Le lieu comme subdivision de la cellule arrive au
jalon 3, avec son identité dérivée de `cell_id`.

### La mesure qui a tranché l'architecture du pont

Jouée le 27 septembre 2026 sur le PC (i7-13700K, Unity 6000.0.43f1 en batch,
runtime Mono de l'éditeur ; Python 3.13), avec un service jetable et un client
dans un vrai projet Unity. Scripts et résultats bruts :
[`docs/mesures/2026-09-27-pont/`](docs/mesures/2026-09-27-pont/).

| ce qu'on a mesuré | valeur |
|---|---|
| un tick du monde entier, en Python | **42 ms** (dont commerce 38 ms) |
| une année ; une partie 1400 → 1900 d'un seul trait | 15 s ; 2,1 h |
| lire un lieu depuis Unity (HttpClient, connexion gardée) | **0,28 ms** médiane, 0,54 ms au 95e centile (côté serveur : 4 µs) |
| lire un lieu avec `UnityWebRequest` | 0,97 ms médiane |
| déposer une intention | **0,27 ms** médiane |
| demander un tick et attendre la réponse | 42 ms : le tick lui-même, le transport ne compte pas |
| lire l'état léger du monde entier (596 cellules, 168 Ko) | 2,3 ms |
| le même morceau du tick (production → naissances, 596 cellules) | Python 1,19 ms ; **C# 0,018 ms, 66 fois plus vite** |
| pont par fichiers (écrire puis relire l'état léger) | 6,9 ms, sans accusé de réception |
| photographie complète (géométrie, sondes des couches) | 1,19 s, 2,0 Mo : faite pour les vues, pas pour un pont |

| critère | service local (`sim/` dans son processus) | portage C# du moteur |
|---|---|---|
| une seule simulation | oui, par construction : `sim/` reste l'unique moteur | non, tant que le Python vit : deux moteurs à tenir égaux |
| ce qu'il faut écrire | ~150 lignes Python (service) + ~200 lignes C# (client, panneau) | 2 884 lignes de moteur, et 7 815 lignes de tests à porter ou à doubler |
| qui écrit le moteur | les agents du VPS, sans Unity (278 tests du jeu en 5 min 30) | du C#, éprouvé sous Unity ou dotnet |
| ce que coûte un tick au joueur | 42 ms dans un autre processus : aucune image perdue | ~0,6 ms (estimé par le rapport ×66) |
| vitesse maximale de l'horloge | ~24 jours par seconde, soit une année en 15 s | bien au-delà |
| livrer le jeu | embarquer Python « embeddable » (bibliothèque standard seule) | rien de plus |

**Décision : le service local.** `sim/` tourne dans son propre processus, tient
le monde et l'horloge ; Unity lit (`/lieu`, `/monde`) et dépose des intentions
(`/intention`) que le tick suivant applique. Trois raisons, dans l'ordre :
le principe 1 tient par construction ; une lecture coûte 0,3 ms, soit 2 % d'une
image à 60 images/s ; et le tick de 42 ms ne bloque jamais l'image puisqu'il
tourne ailleurs. L'horloge d'un jour par tick suffit pour **jouer** 500 ans : à
24 jours par seconde au plus, une année passe en 15 s, l'ordre de grandeur d'un
jeu de grande stratégie en vitesse maximale.

**Quand revenir sur cette décision** : si le tick dépasse 100 ms (moins de dix
jours par seconde) une fois les gains évidents pris — le profilage montre que
35 % du tick actuel est un balayage linéaire des arêtes, indexable. Alors on
porte le moteur **en entier**, tests compris, jamais à moitié. Le journal suit
ce budget chaque semaine.

## Jalon 2 — Le geste revient

**Le joueur** trace une route dans le lieu (l'outil du désert : clic, Entrée).

**L'écran** : le panneau dit « chantier accepté au tick N+1 » ; le chantier
avance en prenant des bras aux champs (la production baisse pendant qu'on
construit) ; route finie, la frontière qu'elle franchit laisse passer plus de
kilos, et le tableau de bord le montre.

**La preuve** : même graine, même geste au même tick ⇒ même monde (déterminisme) ;
sans le geste, la capacité de l'arête ne bouge pas ; une route de longueur nulle
ne coûte rien et ne change rien. Contre-épreuve : un moteur qui ignore
l'intention doit faire échouer l'épreuve.

**Dans le monde** : la route devient la première infrastructure de `sim/`. Elle
coûte du travail réel, et elle concentre un flux là où une frontière le diffuse
(`MODELE.md`, « Les routes »).

## Jalon 3 — La nourriture traverse le lieu

**Le joueur** relie ses champs à son bourg, ou ne le fait pas.

**L'écran** : deux stocks, champs et bourg ; le flux de la route entre les deux ;
sans route, le bourg a faim pendant que les champs débordent, et ses habitants
partent.

**La preuve** : la masse se conserve entre champs, bourg, route et pertes ; sans
route, le bourg s'endette ; avec la route, sa dette baisse. La gratuité de
distribution que `MODELE.md` nomme (« la campagne nourrit son bourg sans
transport ») disparaît : un test le vérifie.

**Dans le monde** : la cellule se peuple de **lieux**. Un lieu a une identité
stable dérivée de `cell_id` et de son rang, jamais une seconde clé spatiale ;
`MODELE.md` change dans le même lot.

## Jalon 4 — Des foyers

**Le joueur** pose un atelier (une scierie, un four) ; plus tard, il subit une
mauvaise année.

**L'écran** : les foyers du bourg par métier (champ, mine, atelier), leur
logement ; la chronique d'une vallée qui se vide et d'une voisine qui grossit.

**La preuve** : cent personnes agrégées en foyers puis désagrégées font cent
personnes ; un métier n'existe que si quelqu'un l'exerce ; la faim fait partir
des foyers entiers, jamais une fraction de personne.

**Dans le monde** : la population cesse d'être un entier par cellule. Les
foyers restent agrégés (pas de personne individuelle).

## Jalon 5 — Le siège prélève

**Le joueur** est seigneur : il fixe la part qu'il prend sur ce qui passe dans
ses lieux, sur plusieurs cellules, et s'en sert pour payer ses chantiers.

**L'écran** : sur la carte, les flux qui convergent vers le siège ; son grenier ;
les lieux qui se vident quand il prend trop.

**La preuve** : ce que le siège reçoit est exactement ce qui a été prélevé, moins
le transport ; un prélèvement plus fort fait partir plus de foyers (direction,
pas valeur) ; aucun prélèvement ne crée de kilo.

**Dans le monde** : le premier pas vers l'État. Pas encore de diplomatie.

## Jalon 6 — La colonne

**Le joueur** lève des hommes dans ses foyers et les fait marcher.

**L'écran** : la colonne sur la carte ; sur le terrain, les hommes en marche
(le moteur de foule de `Citadelle-Guerre` en est la base) ; ce qu'elle mange
dans les cellules traversées ; le creux démographique qu'elle laisse.

**La preuve** : les soldats sont des habitants (ils quittent leur foyer et y
reviennent, ou meurent) ; une colonne qui ne mange pas meurt de faim ; les
morts manquent ensuite aux champs.

## Jalon 7 — 1400 → 1900

**Le joueur** joue un siècle, puis le suivant, sans changer de jeu : ses gestes
passent de « où je pose la scierie » à « quelle loi je passe ».

**L'écran** : la ville au zoom (Unity), la carte en relief au dézoom (forge3d),
sur la même horloge ; des chaînes de fabrication qui s'allongent.

**La preuve** : une partie 1400 → 1900 d'un seul trait tient son budget de tick ;
les agrégations restent conservatives à toutes les échelles ; une loi est une
contrainte sur des flux, jamais un modificateur.

---

## Ce qui n'est pas un jalon

- **La machine** (l'atelier, la CI, les workflows) ne se change qu'en mode
  direct. Un lot de la chaîne ne touche jamais `atelier/` ni `.github/`.
- **Les prototypes 3D** qui ne portent pas le jalon courant dorment dans
  `3d/archives/`, intacts. Ils en ressortent quand un jalon les demande.
- **Une vue** ne décide jamais un nombre : elle lit `sim/`.
