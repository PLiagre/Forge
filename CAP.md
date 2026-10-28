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

## Le constat qui commande (7 et 28 octobre 2026)

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

**Le 28 octobre**, le propriétaire a pris **Europa Universalis IV** pour modèle
de jeu ([docs/VISION.md](docs/VISION.md), décisions 24 à 33) : la simulation
tourne seule, avec un monde vivant, et le joueur fait évoluer son pays depuis
la carte. Le rapport d'avancement du même jour montrait pourquoi il le fallait :

- **le monde ne tient pas seul.** Sa réserve de départ couvre cinq jours
  (trente pour une ville) et la production d'hiver ne suit pas : Paris passe
  de 275 000 habitants à 2 858 avant le 90e jour de 1400 (graine 0, sans
  joueur, mesuré avec et sans migration). La Flandre, Milan et Le Caire
  perdent de 75 à 90 %, l'Est grossit, et l'Europe de 1400 du jalon 2
  n'existe qu'au premier jour ;
- **le joueur gouverne quatre lieux, pas un pays**, et ses gestes de
  bâtisseur n'existent qu'en 3D, à Biskra ;
- **l'IA n'a que deux gestes**, sa part et ses routes ;
- **la bataille tactique en 3D et les kits des autres terres** occupaient le
  PC pour des écrans qu'Europa Universalis ne demande pas.

Les jalons **gardent leurs numéros**, parce que le pilote lie un milestone à
son numéro, et leurs issues restent où elles sont. Le jalon 4 se termine tel
qu'il est écrit. Le jalon 5 devient **le monde vivant**, le jalon 6 **le pays
et sa dynastie**, et le jalon 7 fait **la guerre sur la carte**. La bataille et
le siège en 3D, et les kits des autres terres, passent à l'horizon. Les lots
nouveaux sont écrits sous leur jalon, *à créer* : il faut leur ouvrir une issue
(formulaire « Demander un lot »), puis inscrire son numéro ici.

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

## La langue visuelle

Décidée le 28 octobre 2026 par le propriétaire : l'interface devient
**sombre, gothique et médiévale** — la pierre, le bois brûlé, le métal patiné,
des accents de rouge profond, de cuivre et d'or vieilli, la hiérarchie d'un
registre de pouvoir. L'atmosphère de Warhammer Fantasy en est l'ambiance,
rien de plus : ni ses logos, ni ses signes reconnaissables, ni ses assets. Les
jetons, les états et les interdits sont dans
[docs/interface/DA.md](docs/interface/DA.md), « Révision du 28 octobre 2026 ».

- **Un socle, puis ses écrans.** La langue vit à un seul endroit
  (`SocleInterface`, `MatieresCabinet` : jetons, matières, cadres, états,
  infobulle) ; un écran la reçoit, il ne la redessine pas.
- **Elle sert un geste.** Un lot qui l'applique nomme la décision de son
  jalon qu'elle rend plus lisible. Il ne retire aucune information ni aucun
  geste, et ne change aucun nombre : la vue lit `sim/` et n'ajoute aucune
  règle au monde.
- **Sa preuve peut échouer** : le contraste des jetons calculé (4,5:1 pour
  un texte, 3:1 pour un trait qui porte un état) ; chaque état
  reconnaissable sans sa couleur ; aucun écran qui pose une couleur ou une
  police hors du socle ; les textes affichés au même tick identiques avant
  et après le lot. Et des **captures des vrais écrans**, branchés au vrai
  service, en 1920 × 1080 et 1280 × 720, regardées à l'œil et comparées à la
  galerie du socle : une capture de galerie ne prouve pas un écran. Les
  tests existants du socle (le papier `#E8DDC9`, les polices Noto) restent
  verts sans retouche.
- **Ses lots** : trois lots au jalon 4 (#849, #850, #851) posent le socle et
  l'appliquent à la carte et à la capitale ; les écrans Unity déjà écrits
  des jalons 4 à 9 la reçoivent dans leur brief ; un lot au jalon 9 (#852)
  vérifie le siècle entier. Un lot « à créer » n'a pas encore d'issue : il
  faut la lui ouvrir (formulaire « Demander un lot »), puis l'inscrire ici
  avec son numéro, et ajouter ce numéro à la ligne « Dépend de » des issues
  qui l'attendent.

## L'échelle

| # | jalon | le joueur | l'écran |
|---|---|---|---|
| 1 | **Le pont** — atteint | ouvre un lieu du monde dans Unity et laisse le temps passer | le lieu en 3D, et ses vrais chiffres qui bougent avec `sim/` |
| 2 | **Le monde de 1400** — atteint | choisit sa terre de départ sur la carte de 1400 | les royaumes, les villes et les densités de 1400 |
| 3 | **Le lieu et son maître** | fixe la part qu'il prend sur ses lieux, ouvre son grenier | sa carte dans Unity : ses lieux et ceux des voisins, les flux vers son siège et son suzerain, les lieux qui se vident |
| 4 | **La capitale** | entre dans sa capitale, trace routes, parcelles et murs, pose ses ateliers, paie au grenier | sa ville de 1400 en 3D, qui grandit, se mure et vit d'après le monde |
| 5 | **Le monde vivant** | lance le monde sans pays ou avec le sien, règle la vitesse, et regarde toutes les maisons prélever, nourrir et bâtir seules | la carte qui tourne seule : pause et cinq vitesses, le fil des nouvelles, les voisins et leurs raisons ; une Europe de 1400 encore vraie après dix ans |
| 6 | **Le pays et sa dynastie** | prend n'importe quel pays de 1400 et le gouverne depuis la carte ; marie, éduque, meurt, hérite | le panneau du pays et ses alertes, ses provinces et leurs bâtiments ; l'arbre de la dynastie, l'héritier et le partage |
| 7 | **La guerre** | s'allie, lève, marche, assiège, livre bataille et fait la paix, sur la carte | la colonne et la bataille sur la carte, le siège qui affame, la terre qui change de main |
| 8 | **L'argent** | frappe, emprunte, dévalue, achète une terre | les prix lieu par lieu, son trésor et sa dette, l'inflation |
| 9 | **Le premier siècle** | joue de 1400 à 1500 sans changer de jeu, et délègue ce qui se répète | la chronique d'un siècle, la carte de 1500, le score |

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
Zab, la sixième terre de départ, c'est Biskra ; les autres terres se
gouvernent depuis la carte, et leurs kits sont à l'horizon.

Depuis le 28 octobre, la capitale en 3D est **une vue du pays**, pas le cœur
du jeu (VISION.md, décision 27). Ce jalon se termine avec les lots écrits
ci-dessous, sans lot nouveau ; poser un bâtiment depuis la carte arrive au
jalon 6.

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
17. #849 Le cabinet prend sa langue : la pierre, le bois brûlé et le registre · pc
18. #850 La carte et ses dossiers parlent la langue du cabinet · pc
19. #851 La capitale et ses outils parlent la langue du cabinet · pc
20. #419 Le panneau de la capitale dit ce que coûte un chantier · pc
21. #420 La ville fume, garnit ses étals et s'éclaire, d'après le monde · pc
22. #421 Les gens du bourg circulent dans les rues · pc
23. #422 La capitale dense tient 60 images par seconde · pc
24. #508 La preuve complète du jalon 4 : la capitale du joueur, payée, murée et vivante · pc

Les quatre premiers prouvent la capitale bâtie par intentions telle que le
jalon l'était avant le 7 octobre ; #508 étend cette preuve à tout le jalon.

**La langue visuelle dans ce jalon.** Elle sert la décision du jalon : des
bras au chantier ou aux champs, payés au grenier. Le joueur doit lire le
prix d'un chantier, l'état de son grenier et le refus d'un geste dans le
même registre, sur la carte comme dans sa ville.

- **Le cabinet prend sa langue** — #849. *Le joueur* : partout, il
  reconnaît d'un coup d'œil ce qu'il peut faire, ce qu'il a choisi, ce qui
  attend le monde et ce qui presse ; c'est le registre où il lira le prix
  d'un chantier (#419). Lot de fond du geste « paie au grenier ». *Ce que ça
  fait* : les sept jetons de la révision du 28 octobre à côté des huit
  existants, les matières pierre, bois brûlé et métal générées sans l'aléa du
  monde, la rubrique, la ligne de compte, le séparateur, le sceau,
  l'infobulle et les neuf états ; la galerie du socle les montre tous. Aucun
  écran n'est encore touché. *Preuve* : contraste calculé de chaque paire
  déclarée (contre-épreuve : l'or vieilli déclaré en texte sur papier
  échoue) ; chaque état diffère d'un autre par un mot, un signe ou un trait
  (contre-épreuve : un état réduit à sa teinte échoue) ; l'infobulle d'un
  objet au coin de l'écran reste entière à 1280 × 720 ; les tests du socle
  existants passent sans retouche ; captures de la galerie aux deux
  définitions, regardées. *Dépend de* : #848, le verrou de la passe atlas (#842) ; UI-01, UI-02 et les
  polices sont livrés. *Photo* : la galerie, les neuf états côte à côte.
- **La carte et ses dossiers** — #850. *Le joueur* : avant de descendre
  dans sa capitale, il compare côte à côte son grenier, sa part et les lieux
  qu'il garde ; le lieu survolé, le lieu gardé et sa propre maison ne se
  confondent ni entre eux ni avec une alerte, et une infobulle nomme ce
  qu'il survole avec les valeurs servies. *Ce que ça fait* : le bandeau
  (maison, date, pause, vitesse), le choix de la terre, les dossiers du
  territoire, de la maison, des flux et des voisins, la part et le grenier,
  les calques, les légendes et le menu reçoivent le socle ; les couleurs
  écrites dans les écrans passent en jetons ; les couleurs des maisons
  gardent la teinte du service, en pigment mat du socle (DA.md) ; les
  légendes des lieux (#657) et des flèches (#658) se rangent sans passer
  sous un feuillet ouvert — celle des lieux dépasse aujourd'hui, coupée,
  au-dessus du feuillet de gauche. *Preuve* : aucune couleur ni police posée hors
  du socle dans l'interface de la carte — elle échoue aujourd'hui :
  `LieuxDeCarte` pose son propre rouge ; au même tick,
  graine 0, la liste des textes de chaque dossier est la même avant et après
  (contre-épreuve : un libellé ou un nombre retiré échoue) ; captures du vrai
  cabinet sur le vrai service — choix de la terre avec sa fiche au survol,
  partie en pause avec deux dossiers ouverts, part confirmée puis reçue,
  refus — aux deux définitions, regardées. *Dépend de* : le lot du cabinet (#849).
  *Photo* : la carte de 1400, la maison du joueur, deux dossiers ouverts et
  une infobulle.
- **La capitale et ses outils** — #851. *Le joueur* : dans sa ville, il
  trace une route, découpe une parcelle ou pose un atelier en voyant l'outil
  actif, la parcelle survolée et le refus « pas sur vos terres » (#408) dans
  le même registre que la carte, et revient à la carte sans changer de
  langue. *Ce que ça fait* : le panneau de la capitale, les outils de rue, de
  parcelle et de bâtiment, le passage carte ↔ ville et le dossier des
  chantiers reçoivent le socle ; les marques posées sur le terrain (survol,
  sélection, refus) prennent ses jetons. *Preuve* : la même garde contre les
  couleurs hors du socle et la même égalité des textes ; captures à Biskra
  sur le vrai service — outil de route actif, parcelle survolée, refus hors
  de ses terres, retour à la carte —, regardées. *Dépend de* : le lot du
  cabinet (#849). *Photo* : Biskra, l'outil de parcelle actif et son refus.
- **#419** reçoit la langue : le coût d'un chantier se lit en lignes de
  compte (journées, bras pris aux champs, grain payé, récolte perdue, jours
  restants) avec leur unité et leur tick ; un coût qui dépasse le grenier
  est une alerte avec son mot ; un nombre absent garde l'état d'absence. Sa
  photo, regardée, compare le panneau à la galerie. Son issue doit attendre
  le lot de la capitale (#851).

## Jalon 5 — Le monde vivant

**Le joueur** lance la partie sans prendre de pays — le mode observateur — ou
avec le sien. Il met en pause, choisit l'une des cinq vitesses et laisse filer
les années. Sur la carte, toutes les maisons prélèvent, ouvrent leur grenier,
bâtissent leurs capitales et tracent leurs routes, par les gestes du joueur et
pour des raisons qu'elles disent ; un fil de nouvelles dit ce qui arrive et
mène au lieu. L'Europe qu'il retrouve après dix ans est encore celle de 1400 :
la Flandre et l'Italie du Nord pleines, le désert vide.

**La décision** : quel pays prendre, et quand y entrer, après l'avoir vu vivre ;
puis s'en méfier ou s'en servir — un voisin qui prend trop fait fuir ses gens
vers les terres du joueur, un voisin mieux nourri attire les siens.

**L'écran** : la carte dans Unity qui tourne seule, avec la pause et les cinq
vitesses ; les capitales voisines qui grandissent, leurs parts, leurs
greniers, les foyers qui vont et viennent ; le fil des nouvelles et des gestes
de l'IA, avec leurs raisons ; au journal, la carte d'un monde laissé dix ans
sans joueur, à côté de celle de 1400.

**La preuve** : l'IA n'a qu'un chemin vers le monde, celui des intentions du
joueur, et un contrôle le vérifie ; une intention de l'IA et la même intention
du joueur donnent le même monde ; un voisin qui prend trop envoie des foyers
chez le joueur (direction). **Le monde tient seul** : sans aucun geste du
joueur, l'IA active, graine 0, après un an et après dix ans, les régions denses
de la table de référence du jalon 2 restent au-dessus de la médiane et le
désert au-dessous ; la population totale reste dans la fourchette d'une table
de référence sourcée pour 1400-1410 (niveau 1, ordre de grandeur) ; chaque
maison de l'IA a déposé au moins un geste par an. Contre-épreuves : une IA qui
écrit directement dans le monde fait échouer le contrôle ; un monde sans
soudure — la réserve de cinq jours d'aujourd'hui — fait échouer la tenue (elle
échoue aujourd'hui : Paris perd 99 % de ses habitants avant le 90e jour) ; une
IA muette la fait échouer aussi.

**Dans le monde** : la **soudure** — au 1er janvier 1400, les greniers des
foyers portent ce qui reste de la récolte de 1399, de quoi aller jusqu'à la
moisson moins ce qui se perd (niveau 1 en ordre de grandeur, niveau 2 pour la
répartition) ; c'est un stock réel, qui se mange, se perd et s'échange, pas un
plancher de survie. Le **fil des nouvelles**, lu dans le monde (une famine qui
commence, un grenier ouvert, un chantier fini, des foyers qui partent), qui ne
décide rien. Les maisons de l'IA, grandes et petites, décident avec des
raisons de monde — la faim de leurs gens, les départs, leur grenier, leurs
chantiers — une fois par mois chacune, et chaque geste porte sa raison. Une
exception, le secours : une maison dont un lieu a faim depuis plus de sept
jours ouvre son grenier le jour même, pour la dette de ses lieux affamés, sans
descendre sous la moitié de sa réserve voulue (#424) ; ses gens n'attendent pas
son jour de décision. Le réglage de sa part reste mensuel (décidé le 24
octobre 2026, #425). À partir d'ici, chaque jalon qui ajoute un geste le donne
aussi à l'IA.

**Déjà livré** : les maisons de l'IA et leurs capitales, leur dépôt par le
chemin du joueur, l'IA dans la forge et dans le service (#319, #320, #321,
#323).

**Les lots**, dans l'ordre où ils partent :

1. #322 La carte montre les capitales voisines et ce que l'IA a fait
2. #423 Chaque geste de l'IA dit sa raison
3. #424 L'IA règle sa part sur ses projets et sur ses gens
4. #425 L'IA ouvre son grenier quand ses gens ont faim
5. *(lot à créer)* La soudure de 1400 : les greniers du 1er janvier portent la récolte de 1399
6. *(lot à créer)* L'Europe de 1400 tient dix ans sans joueur
7. #426 L'IA bâtit sa capitale quand son grenier le permet
8. #427 Les petits seigneurs jouent aussi, chacun à son tour
9. *(lot à créer)* Le monde dit ce qui arrive : le fil des nouvelles
10. #428 Le service et la photographie montrent les voisins et leurs raisons
11. *(lot à créer)* Le jeu se lance en observateur, avec la pause et cinq vitesses · pc
12. #429 La carte de Unity montre les voisins et ce qu'ils font · pc
13. *(lot à créer)* Le siècle sans joueur, mesuré chaque semaine au journal
14. #324 La preuve du jalon 5

La preuve #324 et son brief (PR #511, ouverte) s'étendent à « le monde tient
seul » : son issue doit attendre les lots 5, 6, 9 et 11.

- **La soudure de 1400** — *à créer*. *Le joueur* : il lance 1400 et retrouve
  au printemps la Flandre, Paris et le delta du Nil encore pleins ; une
  famine qui arrive a une cause qu'il peut lire, pas l'hiver de tous. Lot de
  fond du geste « regarder le monde vivre ». *Ce que ça fait* : le stock
  alimentaire initial (`MODELE.md`, « Stock alimentaire initial ») devient
  la part de la récolte de 1399 qui reste au 1er janvier, dérivée de la
  production moyenne de la cellule et du rang du jour jusqu'à la moisson ;
  `INITIAL_FOOD_RESERVE_TICKS` et `RESERVE_VILLES_TICKS` sont remplacées, et
  le stock se perd comme un grenier. Niveau 1 en ordre de grandeur, niveau 2
  pour la répartition. *Preuve* : graine 0, sans joueur, au 365e jour, la
  table de référence du jalon 2 tient encore (régions denses au-dessus de la
  médiane, désert au-dessous) et aucune cellule de la table ne perd plus de
  la moitié de ses habitants par la faim (contre-épreuve : la réserve de
  cinq jours la fait échouer, sur Paris dès le 90e jour). Un test existant ne
  s'assouplit pas : s'il supposait la réserve de cinq jours, le lot le dit
  et ajoute ses cas. *Dépend de* : rien d'ouvert.
- **L'Europe de 1400 tient dix ans sans joueur** — *à créer*. *Le joueur* :
  il peut laisser filer dix ans en observateur et choisir son pays dans une
  Europe qui ressemble encore à la sienne. *Ce que ça fait* : une épreuve
  `sim/` qui joue 3 650 ticks avec l'IA et sans geste du joueur, et mesure à
  un an et à dix ans la table du jalon 2, la population totale contre une
  table de référence sourcée pour 1400-1410 (niveau 1), et les gestes de
  chaque maison de l'IA. Elle ne corrige rien : elle dit ce qui ne tient
  pas. *Preuve* : elle échoue sans la soudure ; elle échoue si l'IA est
  muette ; un échantillon vide (aucune maison de l'IA) échoue. *Dépend de* :
  la soudure.
- **Le monde dit ce qui arrive** — *à créer*. *Le joueur* : sans chercher, il
  apprend qu'une famine commence dans tel lieu, qu'un voisin ouvre son
  grenier ou finit un chantier, et une nouvelle le mène au lieu. *Ce que ça
  fait* : le service sert un fil de nouvelles daté, chacune avec son lieu
  (`cell_id`, rang), sa maison et sa cause lue dans le monde (faim qui
  commence, grenier ouvert, chantier achevé, départs) ; la photographie le
  porte. Une nouvelle ne décide rien et n'a aucun choix. *Preuve* : chaque
  nouvelle renvoie à un changement mesurable du monde au même tick
  (contre-épreuve : une nouvelle sans changement, ou un changement de la
  liste sans nouvelle, échoue). *Dépend de* : #428.
- **Le jeu se lance en observateur** — *à créer* · pc. *Le joueur* : il ouvre
  la carte sans choisir de pays, met en pause, passe d'une vitesse à l'autre
  et voit le monde vivre ; il peut prendre un pays quand il veut. *Ce que ça
  fait* : le bandeau de la carte porte la pause et cinq vitesses, la plus
  rapide bornée par le budget du tick ; le choix de la terre devient
  facultatif. *Preuve* : une session Unity en observateur avance de N jours
  et le service dit le même tick que la photographie ; en pause, le tick ne
  bouge pas (contre-épreuve : une pause qui laisse filer un tick échoue).
  *Dépend de* : le lot de la carte (#850). *Photo* : la carte en
  observateur, en vitesse la plus rapide, avec le fil des nouvelles.
- **Le siècle sans joueur, mesuré** — *à créer*. *Le joueur* : il sait, chaque
  semaine, si le monde tient un siècle seul. *Ce que ça fait* : la même
  épreuve sur 36 500 ticks, jouée sur le VPS hors de la CI, qui écrit les
  cartes de 1410, 1450 et 1500 et le temps du tick ; la brancher au journal
  touche `atelier/` et se fait en mode direct. *Preuve* :
  celle de l'épreuve des dix ans, prolongée ; elle peut échouer et le dit au
  journal. *Dépend de* : l'épreuve des dix ans.

**La langue visuelle dans ce jalon.** #429 la reçoit, pour la décision de
s'en méfier ou de s'en servir : une capitale voisine porte une marque
distincte de celle du joueur et de la sélection ; sa part et son grenier
viennent dans l'infobulle du socle, avec leur tick ; les foyers qui
arrivent et ceux qui partent se distinguent par le sens et le signe de leur
flèche, pas par la couleur seule ; le fil des gestes de l'IA s'écrit en
registre — date, maison, geste, et sa raison en note. Sa photo et une
capture du fil long à 1280 × 720, regardées, montrent qu'aucune raison n'est
coupée. Son issue doit attendre le lot de la carte (#850).

## Jalon 6 — Le pays et sa dynastie

**Le joueur** prend la tête de n'importe quel pays de 1400 — un royaume, un
duché, un émirat ou un petit seigneur — et le gouverne depuis la carte, comme
dans Europa Universalis IV. Le panneau du pays lui dit ses terres, ses gens,
sa récolte, ses greniers, ses chantiers et ce qui menace ; il fixe la part
qu'il prend sur tout le pays, ouvre ses greniers et pose ses bâtiments dans
ses provinces sans descendre en 3D. Son pays a une dynastie : le chef vieillit,
se marie, a des enfants qu'il éduque, et meurt ; le joueur continue avec
l'héritier que désigne la loi de succession.

**La décision** : où va le grain de l'année — aux chantiers de quelle
province, au grenier, ou laissé aux gens ; quel mariage (une alliance, une
dot, un héritage possible) ; quelle éducation ; changer la loi de succession,
à un prix, ou risquer le partage.

**L'écran** : le panneau du pays et ses alertes ; la carte de ses provinces et
de leurs bâtiments ; l'arbre de la dynastie, les traits et les ambitions de
chacun ; à la mort du chef, l'héritier et le partage des terres sur la carte.

**La preuve** : un royaume et un petit seigneur, pris dans le registre des
maisons, se choisissent et donnent chacun un panneau égal à la photographie
au même tick ; un bâtiment posé depuis la carte et le même posé en 3D donnent
le même monde ; un partage répartit les lieux sans en perdre ni en créer ; un
héritage par mariage fait passer un lieu d'une maison à l'autre ; un pays sans
terre est une défaite, déclarée au tick où elle survient. Contre-épreuve : un
panneau qui compte un lieu d'un autre maître, un bâtiment de la carte que la
3D ne retrouve pas, un partage qui perd un lieu, ou une défaite jamais
déclarée, doivent échouer.

**Dans le monde** : le **pays** — une maison, ses lieux et ses vassaux, dérivé
du registre et des maîtres des lieux, jamais une seconde clé spatiale ; poser
un bâtiment dans une province, où l'intention dit le bourg et la nature, et le
plan choisit la parcelle libre le long d'une rue (règle déterministe,
niveau 2). Les premières personnes suivies une à une — les chefs des
maisons de 1400 et leurs familles, réels quand on les sait —, qui vieillissent,
naissent et meurent ; leurs traits, leurs compétences, leurs ambitions, qui
raisonnent en monde ; les lois de succession, le partage, l'héritage par les
femmes ; les républiques et l'Église, qui élisent et ne se partagent pas. Les
maisons de l'IA ont leurs personnes, sous les mêmes règles.

**Les lots**, dans l'ordre où ils partent :

1. *(lot à créer)* Le pays se lit d'un seul tenant : ses lieux, ses vassaux et son suzerain
2. *(lot à créer)* Le joueur prend la tête de n'importe quel pays de 1400
3. *(lot à créer)* Le joueur pose un bâtiment dans une province, et le plan lui trouve sa parcelle
4. *(lot à créer)* Le panneau du pays et ses alertes dans Unity · pc
5. #430 Le monde porte des personnes : les chefs des maisons de 1400
6. #431 Les familles de 1400, et leurs découpes (#803 à #806, #824 à #826)
7. #432 On vieillit et on meurt
8. #433 Les couples ont des enfants
9. #434 Chaque personne a ses traits et ses compétences
10. #435 La loi de succession désigne l'héritier
11. #436 À la mort du chef, les terres passent selon la loi
12. #437 Une terre peut passer par une femme
13. #438 Le joueur propose un mariage, et l'autre maison le pèse
14. #439 Le joueur éduque ses enfants
15. #440 Le joueur change sa loi de succession, à un prix
16. #441 Républiques et Église ont leurs règles
17. #442 Le joueur joue l'héritier, et une dynastie sans terre perd
18. #443 Chaque héritier a ses ambitions
19. #444 L'IA marie, éduque et choisit ses lois avec des raisons de monde
20. #445 Le service et la photographie portent les dynasties
21. #446 L'arbre de la dynastie dans Unity · pc
22. #447 À la mort du chef, la carte montre l'héritier et le partage · pc
23. #448 La preuve du jalon 6

La preuve #448 s'étend au pays : son issue doit attendre les lots 1 à 4.

- **Le pays se lit d'un seul tenant** — *à créer*. *Le joueur* : il voit son
  pays comme un tout — combien de lieux, de gens, de grain, de chantiers,
  quels vassaux et quel suzerain — au lieu de quatre lieux autour d'un siège.
  Lot de fond du geste « gouverner depuis la carte ». *Ce que ça fait* : une
  vue dérivée `pays(maison)` dans `sim/` — ses lieux (ceux qu'elle tient,
  puis ceux de ses vassaux), sa population, sa récolte sur trente jours, ses
  greniers, ses chantiers, son suzerain — et `/pays` au service ; rien ne se
  stocke. *Preuve* : les lieux de tous les pays sans suzerain font tous les
  lieux tenus du monde, sans doublon (contre-épreuve : un vassal compté deux
  fois échoue) ; les totaux d'un pays égalent la somme de ses lieux dans la
  photographie. *Dépend de* : rien d'ouvert.
- **Le joueur prend la tête de n'importe quel pays de 1400** — *à créer*.
  *Le joueur* : sur la carte de 1400, il clique un royaume, un duché ou un
  petit seigneur et le joue ; les six terres de départ restent proposées en
  tête. *Ce que ça fait* : l'intention de départ accepte toute maison du
  registre qui tient au moins un lieu, hors républiques et Église ; la
  maison choisie cesse d'être jouée par l'IA, au même tick. *Preuve* : un
  royaume et un petit seigneur se choisissent, et l'IA ne dépose plus rien
  pour eux (contre-épreuve : une maison sans lieu, une république ou
  l'Église sont refusées avec leur raison). *Dépend de* : le lot du pays.
- **Le joueur pose un bâtiment dans une province** — *à créer*. *Le joueur* :
  depuis la carte, il choisit un bourg de son pays et ce qu'il y bâtit ; le
  chantier part comme s'il l'avait posé en 3D, et le prix se lit pareil.
  *Ce que ça fait* : une intention « bâtir dans un bourg » (bourg, nature,
  maison) ; le plan choisit la parcelle libre le long d'une rue, ou en
  découpe une, par une règle déterministe ; ensuite tout passe par le chemin
  de `poser_batiment`. *Preuve* : même graine et mêmes gestes, même monde ;
  le même bâtiment posé en 3D sur la parcelle choisie donne le même monde
  (contre-épreuve : un bourg plein refuse avec sa raison, et un bourg qu'on
  ne tient pas aussi, #408). *Dépend de* : rien d'ouvert.
- **Le panneau du pays et ses alertes dans Unity** — *à créer* · pc. *Le
  joueur* : en haut de la carte, il lit d'un coup d'œil date, vitesse, gens,
  récolte, greniers et chantiers de son pays ; une alerte (famine, grenier
  vide, départs) le mène au lieu. *Ce que ça fait* : le bandeau lit `/pays`
  et le fil des nouvelles, dans la langue du cabinet. *Preuve* : au même
  tick, le panneau est égal à la photographie (contre-épreuve : un service
  décalé d'un tick échoue) ; une alerte cliquée centre la carte sur son
  lieu. *Dépend de* : le lot du pays, le fil des nouvelles (jalon 5), le lot
  de la carte (#850). *Photo* : le bandeau d'un royaume et celui d'un
  petit seigneur, chacun avec une alerte.

**La langue visuelle dans ce jalon.** Elle sert les décisions du mariage, de
l'éducation et de la loi. Dans #446, l'arbre est une généalogie de registre :
des portraits dans des cadres sobres, des filets de métal pour les liens,
l'héritier désigné par son mot et par l'or vieilli ; éduquer, proposer un
mariage ou changer la loi sont des commandes du socle, scellées quand elles
engagent, avec l'attente, le reçu et la raison du refus de l'autre maison.
Dans #447, la mort du chef s'annonce dans le bandeau d'alerte ; les lieux
qui changent de maison ont leur légende avant et après, sur les couleurs
servies ; la défaite, quand le service la déclare, est une page du registre,
pas un écran à part. Photos regardées : l'arbre et la fiche de l'héritier,
une capture de l'arbre d'une grande famille à 1280 × 720 sans nom coupé, la
carte d'un partage. L'issue de #446 doit attendre le lot de la carte
(#850) ; #447 l'attend par #446.

## Jalon 7 — La guerre

**Le joueur** déclare la guerre pour des lieux qu'il revendique, appelle ses
alliés, lève des hommes dans ses foyers, les fait marcher sur la carte et les
nourrit, assiège un lieu ou livre bataille — que son général commande, et que
le moteur de `sim/` calcule jour après jour —, et signe la paix. Comme dans
Europa Universalis IV, la guerre se joue sur la carte.

**La décision** : lever des hommes, c'est vider des champs ; marcher vite en
vivant sur le pays, ou lentement avec ses vivres ; risquer une bataille — et la
vie du chef de sa dynastie — pour trancher la guerre, ou assiéger et attendre ;
s'allier, c'est être appelé à son tour ; céder un lieu pour avoir la paix.

**L'écran** : la colonne sur la carte, ce qu'elle mange dans les lieux
traversés, le creux qu'elle laisse ; la bataille sur la carte, jour après
jour, ses forces et ses pertes ; le siège qui affame la place ; la terre qui
change de main à la paix.

**La preuve** : les soldats sont des habitants (ils quittent leur foyer et y
reviennent, ou meurent) ; une colonne qui ne mange pas meurt de faim ; les
morts manquent ensuite aux champs. Une bataille se calcule dans `sim/` : mêmes
armées, même terrain et même graine donnent la même issue ; une bataille de
l'IA et une bataille du joueur passent par la même fonction ; ses pertes
reviennent au monde. Contre-épreuve : une bataille dont les pertes ne
reviennent pas au monde, ou dont l'issue ne dépend ni des hommes, ni des
vivres, ni du terrain, doit échouer.

**Dans le monde** : la guerre et l'alliance entre maisons, la levée, la
marche, les vivres, la bataille — les hommes, leurs vivres, leur chef et le
terrain du lieu (relief, rivière, murs), constantes de niveau 2 —, le siège,
la paix qui cède des terres, la révolte qui naît de la faim et d'une occasion.
Le chef de la dynastie peut mourir au combat. Citadelle-Guerre reste dans les
archives ; le contrat de bataille (#456) est ce qu'une bataille en 3D lira le
jour où elle reviendra (horizon).

**Les lots**, dans l'ordre où ils partent :

1. #449 La guerre se déclare entre maisons
2. *(lot à créer)* Le joueur s'allie, et l'allié appelé pèse sa réponse
3. #450 Le joueur lève des hommes dans ses foyers
4. #451 L'armée marche de lieu en lieu
5. #452 L'armée mange ce qu'elle porte et ce qu'elle prend
6. #453 Les soldats rentrent chez eux, ou n'en reviennent pas
7. #454 Le siège affame la place
8. #455 La paix cède des terres
9. #456 Le contrat de bataille : le monde envoie ses armées et son terrain, et reçoit ses pertes
10. *(lot à créer)* La bataille se calcule dans `sim/`, jour après jour
11. #462 Le chef de la dynastie peut mourir au combat
12. #465 Une révolte naît de la faim et d'une occasion
13. #466 L'IA fait la guerre avec des raisons de monde
14. #468 Le service et la photographie portent les guerres et les armées
15. #469 La colonne sur la carte · pc
16. *(lot à créer)* La bataille et le siège se suivent sur la carte · pc
17. #470 La preuve du jalon 7 · pc

**Passent à l'horizon** (décision 29), avec l'étiquette `reserve` à poser sur
leurs issues : #457 Citadelle-Guerre sort des archives, #458 le terrain de la
bataille 3D, #459 la bataille 3D sans image, #460 mener ou confier en 3D, #461
le général en 3D, #463 la brèche, #464 le siège dans la ville bâtie. La preuve
#470 ne les attend plus.

- **Le joueur s'allie** — *à créer*. *Le joueur* : il propose une alliance à
  un voisin, qui la pèse ; à la guerre, il appelle ses alliés et voit qui
  vient et pourquoi. *Ce que ça fait* : deux intentions (proposer une
  alliance, appeler ses alliés) ; l'autre maison répond avec des raisons de
  monde — un ennemi commun, la distance, ses propres greniers et ses hommes —,
  par le chemin de l'IA. *Preuve* : une alliance acceptée et une refusée,
  chacune avec sa raison ; l'allié qui vient lève de vrais hommes
  (contre-épreuve : un allié qui vient sans lever personne échoue). *Dépend
  de* : #449.
- **La bataille se calcule dans `sim/`** — *à créer*. *Le joueur* : quand deux
  armées se rencontrent, la bataille dure des jours ; le nombre, les vivres,
  le chef et le terrain décident, et il peut retirer son armée avant la fin.
  *Ce que ça fait* : un moteur de bataille dans `sim/`, appelé au tick pour
  chaque rencontre, qui lit le contrat (#456) et rend ses pertes ; constantes
  de niveau 2, déclarées dans `MODELE.md`. *Preuve* : même contrat, même
  graine, même issue ; plus d'hommes ou de vivres déplacent l'issue en leur
  faveur (direction, pas valeur) ; les pertes reviennent aux foyers
  (contre-épreuve : un moteur qui tire l'issue au sort sans lire les armées
  échoue). *Dépend de* : #456.
- **La bataille et le siège se suivent sur la carte** — *à créer* · pc. *Le
  joueur* : sur la carte, il voit la bataille en cours, ses forces et ses
  pertes jour après jour, et le siège qui affame la place. *Ce que ça fait* :
  la carte lit les batailles et les sièges du service. *Preuve* : au même
  tick, les forces affichées sont égales à la photographie (contre-épreuve :
  un service décalé d'un tick échoue). *Dépend de* : #468, #469. *Photo* :
  une bataille au troisième jour et un siège.

**La langue visuelle dans ce jalon.** Elle sert la décision de lever, de
marcher et de risquer la bataille. Dans #469 et le lot de la bataille sur la
carte, la colonne, son chemin, les lieux vidés par le fourrage, les
batailles et les places assiégées portent les marques du socle sur la
carte ; le panneau de guerre a ses états, avec les refus et les raisons de
l'autre camp ; le bilan des pertes se lit en lignes de compte, tel que la
bataille le rend au monde. Photos regardées : la colonne en marche, une
bataille sur la carte et son bilan. L'issue de #469 doit attendre le lot de
la carte (#850).

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

**La langue visuelle dans ce jalon.** #487 la reçoit, pour la décision de
s'endetter, de dévaluer ou d'attendre. Le calque des prix a sa propre
échelle de données, nommée et graduée dans sa légende avec la marchandise,
l'unité et le tick ; le rouge profond n'y désigne jamais un prix, il reste
à l'alerte. Le trésor est un livre de comptes : lignes de compte en
chiffres alignés, chaque dette avec son créancier, son gage et son
échéance, et l'échéance proche en alerte avec son mot ; frapper, emprunter
et acheter une terre sont des engagements scellés. Photos regardées : la
carte des prix du blé pendant une famine, le trésor avec une dette, et ce
trésor à 1280 × 720 sans chiffre coupé. Son issue doit attendre le lot de
la carte (#850).

## Jalon 9 — Le premier siècle

**Le joueur** joue de 1400 à 1500 d'un seul trait, sans changer de jeu :
plusieurs générations, des guerres, des mariages, des dettes. Il sauve et
reprend sa partie ; il confie ce qui se répète à des intendants, à des vassaux
et à des lois.

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
chronique, la carte de 1500, le score ; le jeu qui se lance seul. La première
partie complète.

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
12. #505 Le jeu se lance sans l'atelier · pc
13. #506 Un siècle se joue dans le jeu, du menu à la chronique · pc
14. #852 Le siècle se lit dans une seule langue · pc
15. #507 La preuve du jalon 9

**Passent à l'horizon** (décision 32), avec l'étiquette `reserve` à poser sur
leurs issues : #500 et #501, le kit et les capitales des Balkans et de Morée ;
#502 et #503, ceux de l'Ouest ; #504, la ville conquise en 3D.

**La langue visuelle dans ce jalon.** Le menu, la sauvegarde (#490) et
l'écran de fin (#506) prennent la langue du socle : la chronique et le score
sont des pages du registre. Un lot la vérifie sur le siècle entier :

- **Le siècle se lit dans une seule langue** — #852. *Le joueur* : du
  menu à l'écran de fin, il lit un état, une alerte, une sélection et un
  engagement de la même façon sur chaque écran — départ, carte, ville,
  bataille, dynastie, trésor, chronique, fin — et aucun ne lui cache ce
  qu'il voyait au jalon précédent. Il sert le geste du jalon : jouer cent ans
  sans changer de jeu. *Ce que ça fait* : la garde contre les couleurs et
  les polices hors du socle s'étend à toute l'interface, et les écarts
  trouvés sont corrigés. *Preuve* : cette garde sur tous les écrans
  (contre-épreuve : un écran qui pose sa couleur échoue) ; le contraste des
  jetons à 100 et 150 % ; une planche des captures du parcours réel de #506,
  chaque écran en 1920 × 1080 et 1280 × 720, regardée écran par écran et
  comparée à la galerie du socle. *Dépend de* : #506. *Photo* : la planche
  du parcours.

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
- **La bataille et le siège en 3D** : les regarder et les mener soi-même,
  le siège grandeur nature dans la ville qu'on a bâtie, sur le moteur de
  `sim/` et son contrat ; Citadelle-Guerre en est la base (#457 à #461,
  #463, #464).
- **Les capitales des autres terres en 3D** : les kits des Balkans et de
  Morée, puis de l'Ouest, et la ville conquise qui s'ouvre avec le kit de sa
  terre (#500 à #504).
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
  Citadelle-Guerre avec la bataille en 3D, à l'horizon (#457).
- **Une vue** ne décide jamais un nombre : elle lit `sim/`.
