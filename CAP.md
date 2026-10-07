# CAP — neuf jalons jusqu'au premier siècle jouable

> Ce fichier dit **où va Forge, dans quel ordre, et par quels lots**. Chaque
> jalon est un milestone GitHub (`J1 — Le pont`, …) ; le **jalon courant** est
> le premier milestone ouvert. Chaque lot est une issue rangée dans le jalon
> qu'il sert, et la liste des lots de chaque jalon est écrite ici, dans l'ordre
> où ils partent : le cap ne se découpe plus tout seul. Un lot qui ne sert pas
> son jalon est refusé par le chef.
>
> La chaîne travaille dans une **fenêtre de trois jalons** : le courant
> d'abord ; une machine qui n'y a plus rien à prendre avance le suivant, puis
> le troisième. Un lot ne part que quand ce qu'il attend est livré : c'est sa
> ligne « Dépend de » qui le dit, pas sa place dans la fenêtre. Un jalon est
> atteint quand ses lots sont livrés — sa preuve comprise, avec sa capture au
> journal — et le pilote ferme alors son milestone. Ce fichier ne tient pas
> d'état : le pourcentage d'un jalon se dérive de ses issues, jamais d'une
> estimation écrite à la main.

## Le constat qui commande (7 octobre 2026)

**Le 27 septembre**, le constat était technique : le jeu était deux mondes qui
ne se parlaient pas, `sim/` (Python, 596 cellules, vivant) et quatorze scènes
Unity qui ne le lisaient pas. Le jalon 1 a refermé cette fracture.

**Le 29 septembre**, la vision a été réécrite ([docs/VISION.md](docs/VISION.md))
et elle a déplacé le centre du jeu : on joue **une dynastie réelle de 1400**,
contre une IA qui a les mêmes outils, et on perd quand on n'a plus de terre.
Neuf jalons font monter un à un les piliers du jeu — la terre, la capitale,
les autres, la dynastie, la guerre, l'argent — jusqu'à **un siècle joué d'un
seul trait**. Ce qui vient après est un horizon.

**Le 6 octobre**, une relecture des lots l'a montré : la chaîne construisait le
jeu **par ses deux bouts** — le monde en bas (les lieux, leur faim, leurs
morts, leurs naissances) et la ville en haut (le kit du désert) —, les deux
choses qui existaient avant la vision, et pas **le milieu, qui est le jeu** :
qui tient quel lieu, qui prend quoi, qui hérite, qui se bat. Le jalon 3
s'appelait « Le lieu et son maître » et aucun lot ne donnait un maître à un
lieu ; le joueur choisissait une terre que le tick ne lisait pas ; sa capitale
en 3D était un ksar du désert alors qu'aucune terre de départ n'est au
désert ; un chantier ne coûtait presque rien ; l'IA traçait des routes parce
que c'était le seul geste qui existait.

**Le 7 octobre**, le propriétaire a gardé l'ordre des neuf jalons et fait
réécrire tous leurs lots :

- **chaque lot dit ce que le joueur y gagne** (« La règle d'un lot »,
  ci-dessous) ;
- **tous les lots jusqu'au premier siècle sont écrits** : 118 issues, listées
  sous leur jalon, chacune avec ce qu'elle attend ;
- **une sixième terre de départ, en terre crue** — l'émirat du Zab, à Biskra,
  sous les Hafsides —, pour que le kit du désert soit dès le jalon 4 la
  capitale d'un joueur ; les kits des autres terres suivent au jalon 9
  (Balkans et Morée, puis l'Ouest) ;
- **la carte du joueur vit dans Unity**, avec la ville et la bataille : les
  trois vues de la vision, dans un seul jeu ;
- la proposition à douze jalons (#344) n'est pas retenue ; ce qu'elle voulait
  — une ville vivante, une bataille détaillée — entre dans les jalons 4 et 7.

## La règle d'un jalon

Un jalon est **jouable** : on lance quelque chose, on fait un geste, on voit le
monde répondre. Il a :

- **ce que le joueur fait** — un geste, pas une fonctionnalité ;
- **la décision** — l'arbitrage que ce geste lui pose. Un geste sans arbitrage
  ne fait pas un jalon ([VISION.md](docs/VISION.md), principe 6 : chaque
  décision pèse) ;
- **ce qu'on voit à l'écran** — ce que la capture du journal doit montrer ;
- **sa preuve** — une commande qui peut échouer (principe 8), avec sa
  contre-épreuve ;
- **l'IA** — à partir du jalon 5, tout geste neuf est aussi à la portée de
  l'IA, par le même chemin, et la preuve le montre (principe 4) ;
- **sa machine** — le VPS pour `sim/` et les vues, le PC pour Unity et Blender ;
- **ses lots**, dans l'ordre où ils partent.

## La règle d'un lot

Un lot est une issue du jalon qu'il sert. Il dit, dans cet ordre :

- **le joueur** : ce que le joueur peut faire, voir ou décider après ce lot,
  et ce qu'il en sent. Un lot de fond le dit aussi : il nomme le geste du
  jalon qu'il prépare. Un lot qui ne rapproche le joueur d'aucun geste de son
  jalon est refusé par le chef. Le brief reprend cette phrase dans sa section
  « Le joueur », et le relecteur vérifie qu'elle est vraie une fois le lot
  fait ;
- **ce que ça fait**, en termes de monde, avec ses constantes et leur niveau
  de fidélité (principe 7), et les sections de `jeu/sim/MODELE.md` qu'il
  change ;
- **sa preuve**, une commande qui peut échouer, et sa contre-épreuve
  (principe 8) ;
- **ce qu'il attend** : « Dépend de : #n » ;
- **sa machine** : l'étiquette `pc` quand il demande Unity ou Blender, et
  alors ce que montre sa photo.

Il fait moins de 300 lignes ; plus gros, le chef le découpe, et chaque morceau
garde sa phrase du joueur. Les lots d'un jalon s'écrivent en mode direct, par
le propriétaire ou à sa demande. La découpe automatique d'un jalon
([docs/WORKFLOW.md](docs/WORKFLOW.md)) ne sert plus qu'à un jalon qu'on aurait
laissé sans lot.

## L'échelle

| # | jalon | le joueur | l'écran |
|---|---|---|---|
| 1 | **Le pont** — atteint | ouvre un lieu du monde dans Unity et laisse le temps passer | le lieu en 3D, et ses vrais chiffres qui bougent avec `sim/` |
| 2 | **Le monde de 1400** — atteint | choisit sa terre de départ sur la carte de 1400 | les royaumes, les villes et les densités de 1400 |
| 3 | **Le lieu et son maître** | fixe la part qu'il prend sur ses lieux, ouvre son grenier | sa carte dans Unity : ses lieux et ceux des voisins, les flux vers son siège et son suzerain, les lieux qui se vident |
| 4 | **La capitale** | entre dans sa capitale, trace routes, parcelles et murs, pose ses ateliers, paie au grenier | sa ville de 1400 en 3D, qui grandit, se mure et vit d'après le monde |
| 5 | **Les autres** | regarde ses voisins prélever, nourrir et bâtir comme lui | ses voisins sur la carte : leurs parts, leurs greniers, leurs gestes et leurs raisons |
| 6 | **La dynastie** | marie, éduque, meurt, hérite | l'arbre de la dynastie ; à la mort du chef, l'héritier et le partage sur la carte |
| 7 | **La guerre** | lève, marche, assiège, livre bataille — menée ou confiée —, fait la paix | la colonne sur la carte, la bataille et le siège en 3D dans sa propre ville, la terre qui change de main |
| 8 | **L'argent** | frappe, emprunte, dévalue, achète une terre | les prix lieu par lieu, son trésor et sa dette, l'inflation |
| 9 | **Le premier siècle** | joue de 1400 à 1500 sans changer de jeu, et délègue ce qui se répète | la chronique d'un siècle, la carte de 1500, le score ; toutes les terres en 3D |

---

## Jalon 1 — Le pont

Atteint : sa preuve, #121, a montré le panneau égal à la photographie.

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
ce budget chaque semaine, et #497 le mesure sur un siècle.

## Jalon 2 — Le monde de 1400

Atteint : sa preuve, #306, tient à 35 points justes sur 51 pour un seuil de 34.

**Le joueur** ouvre la carte du 1er janvier 1400 et choisit sa terre de départ
parmi une poignée de petites seigneuries réelles, catholiques, orthodoxes ou
musulmanes.

**La décision** : où commencer — une terre riche et convoitée, ou pauvre et
tranquille ; près d'un suzerain fort, ou d'un faible.

**L'écran** : la carte de 1400 — les royaumes et leurs frontières, les grandes
villes, les densités de population ; la fiche de la terre choisie.

**La preuve** : une table de référence, tirée de sources publiques et qui les
cite, est comparée au monde amorcé. Les régions denses de 1400 (Flandre,
Île-de-France, Italie du Nord, delta du Nil) sont plus denses que la médiane,
le désert plus vide ; des points connus (Paris, Londres, Venise,
Constantinople, Le Caire) appartiennent à la bonne puissance. Contre-épreuve :
un amorçage sans aridité, ou des frontières mélangées, doivent la faire
échouer. Un point que la table ne couvre pas est déclaré, jamais deviné.

**Dans le monde** : l'amorçage a cessé d'être un proxy plat. Le moteur connaît
l'aridité et le Nil, la population de départ suit l'histoire dans les grandes
lignes (niveau 1), les puissances, les grandes maisons, les villes et cinq
terres de départ entrent dans le monde au niveau de la cellule. Ce choix de
terre devient un geste de jeu dans Unity au jalon 3 (#404), et une sixième
terre s'y ajoute au jalon 4 (#407).

## Jalon 3 — Le lieu et son maître

**Le joueur** tient quatre lieux autour de son siège, dans une cellule où
d'autres seigneurs tiennent les leurs. Il fixe la part qu'il prend sur ce que
ses lieux récoltent — un seul chiffre pour tout son domaine —, la voit
voyager jusqu'à son grenier, en doit une part à son suzerain, et peut rouvrir
son grenier quand ses gens ont faim.

**La décision** : prendre plus aujourd'hui — pour remplir son grenier, qui
paiera ses chantiers (jalon 4) et nourrira son armée (jalon 7) — ou garder ses
gens : trop prendre les appauvrit et les fait partir chez le voisin ; rendre du
grain en mauvaise année les retient.

**L'écran** : la carte du joueur, dans Unity — la cellule découpée en lieux,
chacun avec son seigneur (réel quand on le sait, plausible sinon) et son nom ;
les flèches de ce qui monte vers le siège du joueur et vers celui de son
suzerain ; les lieux qui se vident quand il prend trop ; son panneau, sa part
et son grenier. Au journal, l'encart de la forge montre la même chose.

**La preuve** : chaque lieu a un seul maître, et les lieux d'une cellule font
la cellule (rien ne se perd au découpage) ; ce que le siège reçoit est
exactement ce qui a été prélevé, moins le transport ; aucun prélèvement ne crée
de kilo ; un prélèvement plus fort fait partir plus de foyers (direction, pas
valeur). La distribution à l'intérieur de la cellule n'est pas gratuite : sans
chemin, le bourg a faim pendant que les champs débordent. Contre-épreuve : un
prélèvement qui ne retire rien des lieux doit faire échouer la conservation.

**Dans le monde** : le registre des maisons (grandes maisons, institutions,
terres de départ, seigneurs plausibles) et la pyramide de leurs suzerains ; un
maître pour chaque lieu, à l'identité dérivée de `cell_id` et de son rang,
jamais une seconde clé spatiale ; le grenier de chaque maison, qui se garde
mal ; le prélèvement, qui voyage en convois et se mange en route ; le dû au
suzerain ; des départs qui cherchent le mieux-vivre, pas seulement la survie.
Toute maison prend la part coutumière ; l'IA choisira la sienne au jalon 5.
`MODELE.md` change avec chaque lot.

**L'IA** : chaque maison prélève, par la même étape du tick que le joueur.

**Déjà livré** : la cellule découpée en lieux, leur identité, la distribution
intérieure qui coûte, leurs habitants, leurs paniers, leur récolte, leur dette
et leur faim (#125, #126, #234, #235, #237, #238, #331, #332, #333, #342).

**Les lots**, dans l'ordre où ils partent :

1. #343 Chaque lieu meurt de sa dette et naît de son abondance
2. #335 Commerce et migration passent par le bourg
3. #390 Les maisons du monde forment une pyramide
4. #391 Chaque lieu a son seigneur
5. #392 Les lieux et leurs seigneurs portent un nom plausible
6. #393 Chaque lieu a sa place dans sa cellule
7. #394 Chaque seigneur a son grenier, qui se garde mal
8. #395 Le joueur fixe la part qu'il prend sur ses lieux
9. #396 Le seigneur prélève sa part, et elle voyage jusqu'à son grenier
10. #397 Le vassal envoie sa part à son suzerain
11. #398 Le joueur ouvre son grenier à ses lieux
12. #399 Les foyers quittent un maître qui les affame
13. #400 Le service et la photographie disent qui tient quoi et ce qui circule
14. #401 La carte de la forge montre les seigneurs et leurs flux
15. #402 Le service sert la carte et les terres de départ
16. #403 La carte du joueur s'ouvre dans Unity · pc
17. #404 Le joueur choisit sa terre sur la carte · pc
18. #405 Le joueur règle sa part et ouvre son grenier sur la carte · pc
19. #406 La preuve du jalon 3

## Jalon 4 — La capitale

**Le joueur** entre dans sa capitale en 3D — la ville de 1400 que tient le
monde, pas un décor —, y marche, trace des routes vers ses champs ou vers le
marché, découpe des parcelles où ses gens bâtissent leurs maisons, pose ses
ateliers, trace son enceinte, et passe de la carte à sa ville d'un geste. Au
Zab, la sixième terre de départ, c'est Biskra ; les autres terres attendent
leur kit (jalon 9) et se gouvernent depuis la carte.

**La décision** : des bras au chantier, c'est moins de bras aux champs — et à
la moisson, de la récolte perdue ; chaque journée se paie en grain pris au
grenier, que le jalon 3 a rempli en prenant à ses gens ; une route vers les
champs, ou vers le marché ; des murs, ou des maisons.

**L'écran** : sa capitale en 3D, dessinée d'après le plan que tient le monde
(la ville de 1400 et ses gestes) ; son enceinte ; ses chantiers et ce qu'ils
coûtent ; une ville vivante dont chaque fumée, chaque étal et chaque passant
suit le monde ; ses foyers par métier, leur logement.

**La preuve** : chaque geste est une intention déposée dans `sim/` et
appliquée au tick suivant ; même graine et mêmes gestes, même monde ; sans le
geste, rien ne bouge. Le plan de la ville vit dans le monde : Unity relancé
redessine la même ville d'après le service. Cent personnes agrégées en foyers
puis désagrégées font cent personnes ; un métier n'existe que si quelqu'un
l'exerce. Un chantier n'avance que s'il est payé, et coûte sa récolte en
saison. Contre-épreuve : un moteur qui ignore l'intention, une ville que seul
Unity connaît, un chantier sans grain ou un étal plein dans un bourg affamé
font échouer l'épreuve.

**Dans le monde** : la route, première infrastructure — elle coûte du travail
réel, fait venir le commerce vers le voisin ou rapproche les récoltes ; les
premiers bâtiments ; la ville de 1400 de chaque bourg, dérivée de ses
habitants ; le salaire en grain ; des bras qui comptent à la moisson ;
l'enceinte ; les sans-logis qui bâtissent ; on ne bâtit que sur ses terres.

**Déjà livré** : la caméra ; le kit du désert et ses étapes de chantier ; le
plan dans le monde ; les intentions de route, de parcelle et de bâtiment, et
leurs chantiers ; les foyers par métier ; les ateliers et le logement ; la
route qui fait commerce ; Unity qui dessine rues, parcelles et bâtiments et y
fait poser les gestes (#251, #253, #254, #256, #257, #259, #263, #266, #269,
#270, #291, #292, #293, #297, #298, #299, #300, #345, #347, #348, #351, #352,
#360, #361, #362, #368, #369, #370, #374, #375, #376, #377).

**Les lots**, dans l'ordre où ils partent :

1. #385 L'épreuve du jalon 4 rejoue le journal des gestes et compare le monde
2. #386 Unity joue les gestes de la preuve et redessine la même ville · pc
3. #387 L'épreuve du jalon 4 sur le PC : Unity joue, Python rejoue, verdict · pc
4. #388 La capture de la capitale bâtie et de son panneau · pc
5. #407 La sixième terre de départ : l'émirat du Zab, en terre crue
6. #408 On ne bâtit que sur ses terres
7. #409 Le jeu ouvre la capitale du joueur · pc
8. #410 Le joueur passe de la carte à sa capitale, et l'horloge suit la vue · pc
9. #411 Chaque bourg naît avec sa ville de 1400
10. #412 Unity dessine la ville de 1400 d'après le service · pc
11. #413 Le chantier se paie en vivres, pris au grenier
12. #414 Les sans-logis bâtissent sur les parcelles libres
13. #415 Les moissons demandent tous les bras
14. #416 Le joueur trace l'enceinte de sa capitale
15. #417 L'enceinte se dessine, et ses portes s'ouvrent sur les rues · pc
16. #418 Une route vers les champs nourrit mieux le bourg
17. #419 Le panneau de la capitale dit ce que coûte un chantier · pc
18. #420 La ville fume, garnit ses étals et s'éclaire, d'après le monde · pc
19. #421 Les gens du bourg circulent dans les rues · pc
20. #422 La capitale dense tient 60 images par seconde · pc
21. #508 La preuve complète du jalon 4 : la capitale du joueur, payée, murée et vivante · pc

Les quatre premiers prouvent la capitale bâtie par intentions telle que le
jalon l'était avant le 7 octobre ; #508 étend cette preuve à tout le jalon.

## Jalon 5 — Les autres

**Le joueur** regarde ses voisins faire comme lui : régler leur part, ouvrir
leur grenier, bâtir leurs capitales, tracer leurs routes et leurs murs — par
les mêmes gestes, pour des raisons qu'ils disent.

**La décision** : s'en méfier ou s'en servir ; un voisin qui prend trop fait
fuir ses gens vers les terres du joueur, un voisin mieux nourri attire les
siens.

**L'écran** : sur la carte, les capitales voisines qui grandissent, leurs
parts, leurs greniers, les foyers qui vont et viennent entre eux et le
joueur ; le fil de leurs gestes, avec leurs raisons ; au journal, ce que
chaque maison de l'IA a fait, geste par geste.

**La preuve** : l'IA n'a qu'un chemin vers le monde, celui des intentions du
joueur, et un contrôle le vérifie ; une intention de l'IA et la même intention
du joueur donnent le même monde ; un voisin qui prend trop envoie des foyers
chez le joueur (direction). Contre-épreuve : une IA qui écrit directement dans
le monde fait échouer le contrôle.

**Dans le monde** : les maisons de l'IA, grandes et petites, décident avec des
raisons de monde — la faim de leurs gens, les départs, leur grenier, leurs
chantiers — une fois par mois chacune, et chaque geste porte sa raison. À
partir d'ici, chaque jalon qui ajoute un geste le donne aussi à l'IA.

**Déjà livré** : les maisons de l'IA et leurs capitales, leur dépôt par le
chemin du joueur, l'IA dans la forge et dans le service (#319, #320, #321,
#323).

**Les lots**, dans l'ordre où ils partent :

1. #322 La carte montre les capitales voisines et ce que l'IA a fait
2. #423 Chaque geste de l'IA dit sa raison
3. #424 L'IA règle sa part sur ses projets et sur ses gens
4. #425 L'IA ouvre son grenier quand ses gens ont faim
5. #426 L'IA bâtit sa capitale quand son grenier le permet
6. #427 Les petits seigneurs jouent aussi, chacun à son tour
7. #428 Le service et la photographie montrent les voisins et leurs raisons
8. #429 La carte de Unity montre les voisins et ce qu'ils font · pc
9. #324 La preuve du jalon 5

## Jalon 6 — La dynastie

**Le joueur** est un personnage : il vieillit, se marie, a des enfants qu'il
éduque, et meurt. Il joue ensuite l'héritier que désigne la loi de succession.

**La décision** : quel mariage (une alliance, une dot, un héritage possible) ;
quelle éducation ; changer la loi de succession, à un prix, ou risquer le
partage.

**L'écran** : l'arbre de la dynastie, les traits et les ambitions de chacun ;
à la mort du chef, l'héritier et le partage des terres sur la carte.

**La preuve** : un partage répartit les lieux sans en perdre ni en créer ; un
héritage par mariage fait passer un lieu d'une maison à l'autre ; une dynastie
sans terre est une défaite, déclarée au tick où elle survient. Contre-épreuve :
un partage qui perd un lieu, ou une défaite jamais déclarée, doivent échouer.

**Dans le monde** : les premières personnes suivies une à une — les chefs des
maisons de 1400 et leurs familles, réels quand on les sait —, qui vieillissent,
naissent et meurent ; leurs traits, leurs compétences, leurs ambitions, qui
raisonnent en monde ; les lois de succession, le partage, l'héritage par les
femmes ; les républiques et l'Église, qui élisent et ne se partagent pas. Les
maisons de l'IA ont leurs personnes, sous les mêmes règles.

**Les lots**, dans l'ordre où ils partent :

1. #430 Le monde porte des personnes : les chefs des maisons de 1400
2. #431 Les familles de 1400
3. #432 On vieillit et on meurt
4. #433 Les couples ont des enfants
5. #434 Chaque personne a ses traits et ses compétences
6. #435 La loi de succession désigne l'héritier
7. #436 À la mort du chef, les terres passent selon la loi
8. #437 Une terre peut passer par une femme
9. #438 Le joueur propose un mariage, et l'autre maison le pèse
10. #439 Le joueur éduque ses enfants
11. #440 Le joueur change sa loi de succession, à un prix
12. #441 Républiques et Église ont leurs règles
13. #442 Le joueur joue l'héritier, et une dynastie sans terre perd
14. #443 Chaque héritier a ses ambitions
15. #444 L'IA marie, éduque et choisit ses lois avec des raisons de monde
16. #445 Le service et la photographie portent les dynasties
17. #446 L'arbre de la dynastie dans Unity · pc
18. #447 À la mort du chef, la carte montre l'héritier et le partage · pc
19. #448 La preuve du jalon 6

## Jalon 7 — La guerre

**Le joueur** déclare la guerre pour des lieux qu'il revendique, lève des
hommes dans ses foyers, les fait marcher et les nourrit, assiège un lieu ou
livre bataille — qu'il mène lui-même en 3D, ou qu'il confie à un général —,
défend sa capitale dans les murs qu'il a tracés, et signe la paix.

**La décision** : lever des hommes, c'est vider des champs ; marcher vite en
vivant sur le pays, ou lentement avec ses vivres ; risquer une bataille — et sa
propre vie — pour trancher la guerre, ou assiéger et attendre ; céder un lieu
pour avoir la paix.

**L'écran** : la colonne sur la carte, ce qu'elle mange dans les lieux
traversés, le creux qu'elle laisse ; le champ de bataille en 3D, sur le
terrain du lieu ; le siège d'une ville, et de la sienne, en 3D ; la terre qui
change de main à la paix.

**La preuve** : les soldats sont des habitants (ils quittent leur foyer et y
reviennent, ou meurent) ; une colonne qui ne mange pas meurt de faim ; les
morts manquent ensuite aux champs. Une bataille déléguée passe par le même
moteur qu'une bataille jouée : mêmes armées, même terrain, mêmes ordres et même
graine donnent la même issue, avec ou sans image. Le siège de la capitale se
livre dans la ville que le joueur a bâtie. Contre-épreuve : une bataille dont
les pertes ne reviennent pas au monde doit échouer.

**Dans le monde** : la guerre entre maisons, la levée, la marche, les vivres,
le siège, la paix qui cède des terres, la révolte qui naît de la faim et
d'une occasion. Le monde prépare chaque bataille (ses armées, son terrain) et
en reçoit les pertes ; il ne la calcule jamais lui-même. Citadelle-Guerre sort
des archives : son moteur de foule porte la bataille, sur le terrain du monde
et dans les villes du plan. Le chef de la dynastie peut mourir au combat.

**Les lots**, dans l'ordre où ils partent :

1. #449 La guerre se déclare entre maisons
2. #450 Le joueur lève des hommes dans ses foyers
3. #451 L'armée marche de lieu en lieu
4. #452 L'armée mange ce qu'elle porte et ce qu'elle prend
5. #453 Les soldats rentrent chez eux, ou n'en reviennent pas
6. #454 Le siège affame la place
7. #455 La paix cède des terres
8. #456 Le contrat de bataille : le monde envoie ses armées et son terrain, et reçoit ses pertes
9. #457 Citadelle-Guerre sort des archives et lit le contrat · pc
10. #458 Le terrain de la bataille vient du monde · pc
11. #459 La bataille se joue sans image, à l'identique · pc
12. #460 Le joueur mène sa bataille, ou la confie à un général · pc
13. #461 Un général commande la bataille qu'on lui confie · pc
14. #462 Le chef de la dynastie peut mourir au combat
15. #463 L'artillerie ouvre une brèche dans les murs du plan · pc
16. #464 Le siège se livre dans la ville bâtie · pc
17. #465 Une révolte naît de la faim et d'une occasion
18. #466 L'IA fait la guerre avec des raisons de monde
19. #468 Le service et la photographie portent les guerres et les armées
20. #469 La colonne sur la carte · pc
21. #470 La preuve du jalon 7 · pc

## Jalon 8 — L'argent

**Le joueur** frappe monnaie, emprunte pour acheter une terre, met un lieu en
gage, dote sa fille, rachète un captif, lève sa part en pièces — et peut
dévaluer.

**La décision** : s'endetter pour grandir vite, ou attendre ; dévaluer pour
payer sa guerre, et le payer en inflation ; parier sur le commerce ou sur
l'atelier.

**L'écran** : les prix lieu par lieu sur la carte ; le trésor, la dette et
ses échéances ; l'inflation qui suit une dévaluation.

**La preuve** : la monnaie se conserve — ce qui est frappé vient du métal
extrait, ce qui est prêté sort d'un trésor ; une dévaluation fait monter les
prix (direction, pas valeur) ; une dette se rembourse en pièces réelles, elle
ne s'efface jamais. Contre-épreuve : une monnaie créée sans métal doit faire
échouer la conservation.

**Dans le monde** : les mines d'argent et d'or de 1400, le métal, la frappe
et le seigneuriage, les trésors, la masse monétaire de 1400, un marché par
bourg où naissent les prix, des marchands qui achètent bas et vendent haut à
la place du commerce gratuit, les salaires et le cens en pièces, le crédit et
ses gages, l'achat de terre. Les prix deviennent le signal sur lequel l'IA
décide, et les républiques marchandes trouvent ici leurs outils.

**Les lots**, dans l'ordre où ils partent :

1. #471 Les mines d'argent de 1400 entrent au monde
2. #472 L'argent et l'or sortent des mines en kilos de métal
3. #473 Le seigneur frappe monnaie
4. #474 Chaque maison a son trésor
5. #475 La monnaie de 1400 est déjà dans les bourses
6. #476 Le marché du bourg fait le prix
7. #477 Les marchands achètent où c'est bon marché et vendent où c'est cher
8. #478 Les salaires se paient en pièces
9. #479 Le prélèvement peut se payer en pièces
10. #480 Le joueur dévalue sa monnaie, et les prix montent
11. #481 Les banquiers prêtent ce qu'ils ont
12. #482 Une dette se rembourse en pièces, ou le gage change de main
13. #483 Le joueur achète une terre
14. #484 La dot et la rançon se paient en pièces
15. #485 L'IA décide sur les prix
16. #486 Le service et la photographie portent les prix, les trésors et les dettes
17. #487 La carte des prix, le trésor et la dette dans Unity · pc
18. #488 La preuve du jalon 8

## Jalon 9 — Le premier siècle

**Le joueur** joue de 1400 à 1500 d'un seul trait, sans changer de jeu :
plusieurs générations, des guerres, des mariages, des dettes. Il sauve et
reprend sa partie ; il confie ce qui se répète à des intendants, à des vassaux
et à des lois ; toutes les terres de départ ont leur capitale en 3D.

**La décision** : toutes celles des jalons précédents, à l'échelle d'un
siècle ; et ce qu'on garde pour soi, ce qu'on délègue.

**L'écran** : la chronique de la dynastie sur cent ans, la carte de 1500 que
la partie a faite, le score ; le jeu entier, du menu à l'écran de fin.

**La preuve** : un siècle joué d'un trait tient le budget du tick (jalon 1) ;
les agrégations restent conservatives à toutes les échelles ; **chaque
décision pèse** — le nombre de gestes demandés au joueur par année de jeu ne
grandit pas avec son royaume, mesuré sur une partie scriptée qui va du
seigneur au roi. Contre-épreuve : une partie où chaque lieu demande son geste
doit la faire échouer.

**Dans le monde** : la sauvegarde, les intendants, le fief, les premières lois
(le geste passe de « où je pose la scierie » à « quelle loi je passe »), la
chronique, la carte de 1500, le score ; les kits des autres terres — Balkans et
Morée, puis l'Ouest — et le jeu qui se lance seul. La première partie complète.

**Les lots**, dans l'ordre où ils partent :

1. #489 La partie se sauvegarde et se recharge à l'identique
2. #490 Le joueur sauve et reprend sa partie dans le jeu · pc
3. #491 Les intendants gèrent ce qui se répète
4. #492 Le joueur inféode des lieux à ses vassaux
5. #493 Une loi remplace mille gestes
6. #494 La chronique de la dynastie s'écrit seule
7. #495 La carte de 1500 que la partie a faite
8. #496 Le score de la dynastie
9. #497 Le siècle tient le budget du tick
10. #498 Les agrégations restent conservatives sur cent ans
11. #499 Les gestes du joueur ne grandissent pas avec son royaume
12. #500 Le kit de pierre et de tuile des Balkans et de Morée · pc
13. #501 Les capitales des Balkans et de Morée s'ouvrent en 3D · pc
14. #502 Le kit de colombage et de pierre de l'Ouest · pc
15. #503 Les capitales de l'Ouest s'ouvrent en 3D · pc
16. #504 Une ville conquise s'ouvre en 3D avec le kit de sa terre · pc
17. #505 Le jeu se lance sans l'atelier · pc
18. #506 Un siècle se joue dans le jeu, du menu à la chronique · pc
19. #507 La preuve du jalon 9

---

## L'horizon, après le premier siècle

Ce ne sont pas encore des jalons : ils s'écriront quand le jalon 9 sera
atteint, avec ce qu'on aura appris.

- **Les rails de l'histoire** : l'imprimerie, la Réforme, les Grandes
  Découvertes, les épidémies, la vapeur — des étincelles à leur date, que le
  monde diffuse.
- **L'État qui émerge** : la pyramide qui se centralise, les lois comme
  contraintes sur des flux, jamais comme modificateurs.
- **Les religions, les cultures, les techniques** et leur diffusion.
- **L'industrie** : la vapeur, les usines, le rail, l'économie de 1900 ; la
  carte, la ville et la bataille, sur la même horloge, jusqu'en 1900.
- **Les batailles de 1900** : lignes, artillerie, fusils, autant d'hommes que
  la machine en tient ; les batailles navales, si on les retient.
- **Le monde entier**, sur une nouvelle carte.

## La réserve

Les lots qui ne servent aucun jalon vivent dans le milestone **Réserve**, que
le pilote ne prend jamais (son titre ne commence pas par `J`). Le 7 octobre
2026, ceux de l'ancien `ROADMAP.md` qui étaient faits, ou que remplace un lot
de ce fichier, ont été fermés avec le numéro qui les remplace ; restent ceux
qui serviront au finissage du jeu ou après le premier siècle (épidémies, foi,
ordre et criminalité, incendies, usure des bâtiments, art, audio, lumière,
accessibilité, localisation, tutoriel…). Un jalon qui en a besoin en tire un
lot, le reformule contre `sim/` avec sa phrase du joueur, et le range chez lui.

## Ce qui n'est pas un jalon

- **La machine** (l'atelier, la CI, les workflows) ne se change qu'en mode
  direct. Un lot de la chaîne ne touche jamais `atelier/` ni `.github/`.
- **Les prototypes 3D** qui ne portent pas le jalon courant dorment dans
  `3d/archives/`, intacts. Ils en ressortent quand un jalon les demande :
  Citadelle-Guerre au jalon 7 (#457).
- **Une vue** ne décide jamais un nombre : elle lit `sim/`.
