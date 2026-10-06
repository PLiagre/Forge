# CAP — douze jalons jusqu'au premier siècle jouable

> Ce fichier dit **où va Forge et dans quel ordre**. Il est court exprès : tout
> le reste en découle. Chaque lot porte le jalon qu'il sert (le jalon de son
> issue) ; un lot qui ne sert pas son jalon est refusé par le chef.
>
> Chaque jalon est un milestone GitHub (`J1 — Le pont`, …). Le **jalon
> courant** est le premier milestone ouvert. La chaîne travaille dans une
> **fenêtre de trois jalons** : le courant d'abord ; une machine qui n'y a plus
> rien à prendre avance le suivant, puis le troisième, et le découpe s'il n'a
> encore rien. Un lot
> pris en avance ne s'appuie sur rien que le courant doit encore livrer. Un
> jalon est atteint quand ses lots sont livrés — sa preuve comprise, avec sa
> capture au journal — et le pilote ferme alors son milestone. Le pourcentage
> d'un jalon se dérive de ses issues (fermées / toutes), jamais d'une
> estimation écrite à la main ; ce fichier ne tient pas d'état.

## Le constat qui commande (29 septembre 2026)

Le 27 septembre, le constat était technique : le jeu était deux mondes qui ne
se parlaient pas, `sim/` (Python, 596 cellules, vivant) et quatorze scènes
Unity qui ne le lisaient pas. Le jalon 1 referme cette fracture ; il est en
cours.

Le 29 septembre, la vision a été réécrite ([docs/VISION.md](docs/VISION.md))
et elle déplace le centre du jeu : on joue **une dynastie réelle de 1400**,
contre une IA qui a les mêmes outils, et on perd quand on n'a plus de terre.
L'ancienne échelle construisait l'économie d'un lieu (jalons 2 à 4), puis le
prélèvement et la colonne, et repoussait le reste — les autres seigneurs, la
dynastie, l'argent, la bataille, l'État — dans un septième jalon qui contenait
presque tout le jeu. La nouvelle échelle les fait monter un par un, et
s'arrête sur un premier jeu complet : **un siècle joué d'un seul trait**. Ce
qui vient après est un horizon, écrit en jalons quand on y sera.

Mesuré le même jour, et à rejouer : le monde ne ressemble pas encore à 1400.
L'amorçage ignore l'aridité — le désert occidental égyptien y est aussi peuplé
que le delta du Nil — et il n'y a ni royaume, ni ville, ni maison.

## La ville et la bataille montent (6 octobre 2026)

La vision prend deux choses à deux jeux : à Manor Lords, la capitale bâtie à
la main, dense et vivante ; à Total War, la bataille tactique en temps réel.
L'échelle du 29 septembre leur faisait trop peu de place. La capitale du
jalon 4 est une base — une route, une parcelle, un atelier — et la ville
vivante n'avait pas de jalon : ses lots dormaient dans la réserve. La guerre
arrivait au septième jalon, en un seul bloc qui portait la levée, la marche,
la bataille, le siège et la paix.

L'échelle passe donc de neuf à douze jalons, sans toucher aux cinq premiers :

- **la ville vivante** (jalon 6) suit les autres, pour que l'IA bâtisse ses
  capitales par les mêmes gestes dès qu'ils existent ;
- **une première bataille** (jalon 7) vient avant la dynastie : le pont entre
  `sim/` et le moteur de bataille est le plus risqué du jeu, on le pose tôt ;
- **la guerre se fait en trois temps** : la bataille (jalon 7), la campagne,
  qui a besoin de la dynastie pour risquer la vie du chef (jalon 9), puis le
  siège et la paix, livrés dans la ville bâtie au jalon 6 (jalon 10).

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
- **sa machine** — le VPS pour `sim/` et les vues, le PC pour Unity et Blender.

## L'échelle

| # | jalon | le joueur | l'écran |
|---|---|---|---|
| 1 | **Le pont** | ouvre un lieu du monde dans Unity et laisse le temps passer | le lieu en 3D, et ses vrais chiffres (habitants, stocks, faim, date) qui bougent avec `sim/` |
| 2 | **Le monde de 1400** | choisit sa terre de départ sur la carte de 1400 | les royaumes, les villes et les densités de 1400 : le désert vide, la Flandre pleine |
| 3 | **Le lieu et son maître** | fixe la part qu'il prend sur ses lieux | la cellule découpée en lieux, chacun avec son seigneur ; les flux vers son siège et vers son suzerain |
| 4 | **La capitale** | trace une route, découpe une parcelle, pose un atelier | sa capitale en 3D, dessinée d'après le plan que tient le monde ; ses foyers par métier |
| 5 | **Les autres** | regarde ses voisins faire comme lui | les capitales voisines qui grandissent, leurs prélèvements, par les mêmes gestes |
| 6 | **La ville vivante** | découpe des lots où ses foyers bâtissent, pose les grands bâtiments, trace l'enceinte | une capitale dense en 3D, qui fume, vend et s'éclaire, dans ses murs ; la rue à hauteur d'homme |
| 7 | **Première bataille** | lève une troupe dans ses foyers et la mène en 3D, ou la confie à un général | la levée, la mêlée en 3D, et au retour les foyers qui ont perdu un homme |
| 8 | **La dynastie** | marie, éduque, meurt, hérite | l'arbre de la dynastie, l'héritier que désigne la loi, le partage des terres |
| 9 | **La campagne** | fait marcher et nourrir son armée, cherche la bataille, y risque sa vie | la colonne sur la carte, ce qu'elle mange, le creux qu'elle laisse ; le chef qui revient, ou son héritier |
| 10 | **Le siège et la paix** | assiège, donne l'assaut, défend sa capitale, signe la paix | le siège en 3D, la brèche, les combats de rue dans sa propre ville ; la terre qui change de main |
| 11 | **L'argent** | emprunte, frappe, dévalue, achète une terre | les prix lieu par lieu, sa dette, l'inflation qui suit la dévaluation |
| 12 | **Le premier siècle** | joue de 1400 à 1500 sans changer de jeu | la chronique d'un siècle de sa dynastie, et la carte de 1500 que la partie a faite |

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

## Jalon 2 — Le monde de 1400

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

**Dans le monde** : l'amorçage cesse d'être un proxy plat. Le moteur apprend
l'aridité, la population de départ suit l'histoire dans les grandes lignes
(niveau 1), et les royaumes et les grandes maisons entrent dans le monde au
niveau de la cellule ; le détail sous la cellule attend les lieux (jalon 3).
`jeu/sim/MODELE.md` change dans le même lot.

## Jalon 3 — Le lieu et son maître

**Le joueur** tient quelques lieux dans une cellule. Il fixe la part qu'il
prend sur ce qu'ils produisent, et son suzerain prend la sienne sur ce qu'il
reçoit.

**La décision** : prendre plus aujourd'hui pour bâtir, ou garder ses gens —
trop prendre les fait partir chez le voisin.

**L'écran** : la cellule découpée en lieux, chacun avec son seigneur (réel
quand on le sait, plausible sinon) ; sur la carte, les flux qui convergent vers
le siège du joueur et vers celui de son suzerain ; les lieux qui se vident
quand il prend trop.

**La preuve** : chaque lieu a un seul maître, et les lieux d'une cellule font
la cellule (rien ne se perd au découpage) ; ce que le siège reçoit est
exactement ce qui a été prélevé, moins le transport ; aucun prélèvement ne crée
de kilo ; un prélèvement plus fort fait partir plus de foyers (direction, pas
valeur). La distribution à l'intérieur de la cellule cesse d'être gratuite :
sans chemin, le bourg a faim pendant que les champs débordent. Contre-épreuve :
un prélèvement qui ne retire rien des lieux doit faire échouer la conservation.

**Dans le monde** : la cellule se peuple de **lieux**, à l'identité dérivée de
`cell_id` et de leur rang, jamais une seconde clé spatiale ; chaque lieu a un
maître, chaque maître un suzerain. C'est le premier pas de la pyramide.
`MODELE.md` change dans le même lot.

## Jalon 4 — La capitale

**Le joueur** entre dans sa capitale en 3D, y marche, trace une route, découpe
des parcelles, pose un atelier (une scierie, un four).

**La décision** : des bras au chantier, c'est moins de bras aux champs cette
année ; une route vers les champs, ou vers le marché.

**L'écran** : la capitale en 3D, dessinée d'après le plan que tient le monde
(rues, parcelles, bâtiments) ; le chantier qui prend des bras aux champs ; les
foyers du bourg par métier et leur logement.

**La preuve** : chaque geste est une intention déposée dans `sim/` et appliquée
au tick suivant ; même graine et mêmes gestes, même monde ; sans le geste, rien
ne bouge. Le plan de la ville vit dans le monde : Unity relancé redessine la
même ville d'après le service. Cent personnes agrégées en foyers puis
désagrégées font cent personnes ; un métier n'existe que si quelqu'un
l'exerce. Contre-épreuve : un moteur qui ignore l'intention, ou une ville que
seul Unity connaît, font échouer l'épreuve.

**Dans le monde** : la route, première infrastructure — elle coûte du travail
réel et concentre un flux là où une frontière le diffuse ; les premiers
bâtiments ; la population cesse d'être un entier par lieu et se compte en
foyers. Le kit du désert sert ici ; les lots de ville de la réserve
attendent la ville vivante (jalon 6).

## Jalon 5 — Les autres

**Le joueur** regarde ses voisins prélever, bâtir leurs capitales et tracer
leurs routes — par les mêmes gestes que lui.

**La décision** : s'en méfier ou s'en servir ; un voisin qui prend trop fait
fuir ses gens vers les terres du joueur, un voisin mieux nourri attire les
siens.

**L'écran** : sur la carte, les capitales voisines qui grandissent et leurs
prélèvements ; au journal, ce que chaque maison de l'IA a fait, geste par
geste.

**La preuve** : l'IA n'a qu'un chemin vers le monde, celui des intentions du
joueur, et un contrôle le vérifie ; une intention de l'IA et la même intention
du joueur donnent le même monde. Contre-épreuve : une IA qui écrit directement
dans le monde fait échouer le contrôle.

**Dans le monde** : les maisons de l'IA, grandes et petites, décident avec des
raisons de monde (la faim de leurs gens, la richesse de leurs lieux). À partir
d'ici, chaque jalon qui ajoute un geste le donne aussi à l'IA.

## Jalon 6 — La ville vivante

**Le joueur** bâtit sa capitale à la main, comme dans Manor Lords : il découpe
ses parcelles en lots où les foyers bâtissent leurs maisons, pose les
bâtiments singuliers (l'église, la halle, le moulin, la demeure du seigneur),
trace l'enceinte et ses portes. Il survole sa ville et descend dans la rue.

**La décision** : des murs ou des maisons — la pierre et les bras d'une
enceinte, c'est autant de moins pour loger et nourrir ; une ville serrée dans
ses murs, ou étalée et ouverte ; quel grand bâtiment d'abord.

**L'écran** : une capitale dense et vivante en 3D — les maisons sur leurs
lots, les étals garnis de ce que contiennent les stocks, la fumée des foyers
qui cuisent, les lumières la nuit ; l'enceinte et ses portes ; la caméra de
city builder qui passe du survol à la rue.

**La preuve** : chaque maison est celle d'un foyer de `sim/`, et un foyer sans
toit se déclare sans abri ; un étal ne montre que ce que le stock du lieu
contient, une cheminée ne fume que si un foyer cuit ; un mur coûte la pierre
transportée et les journées de travail réelles ; Unity relancé redessine la
même ville d'après le service. L'IA bâtit ses capitales par les mêmes
intentions. La ville dense tient 60 images par seconde sur la machine de
référence. Contre-épreuve : une maison sans foyer, un étal plein dans un lieu
affamé, ou un mur sans pierre font échouer l'épreuve.

**Dans le monde** : le bâti devient une donnée du moteur. Les lots, les
maisons, les bâtiments singuliers et l'enceinte entrent dans le plan de la
ville que tient `sim/` — le siège du jalon 10 se livrera dedans. Les lots de
ville de la réserve servent ici, reformulés contre `sim/` : la caméra (#155),
les maisons sur leurs lots (#158), les bâtiments posés à la main (#161), la
ville qui vit (#165), la ville dense à 60 images par seconde (#166).

## Jalon 7 — Première bataille

**Le joueur** lève une troupe dans ses foyers et la mène en 3D contre celle
d'un voisin, sur le terrain de sa cellule : il la place, lui donne ses ordres,
la voit tenir ou plier. Il peut aussi la confier à un général.

**La décision** : combien d'hommes lever — chaque homme levé est un bras de
moins aux champs cette saison ; des piques ou des arbalètes ; engager, ou
reculer quand la ligne plie.

**L'écran** : la levée foyer par foyer ; le champ de bataille en 3D, les deux
troupes, la mêlée ; au retour, les foyers qui ont perdu un homme et les champs
qui manquent de bras.

**La preuve** : les soldats sont des habitants — ils quittent leur foyer et y
reviennent, ou meurent, et le compte tient ; les pertes reviennent au monde au
tick qui suit la bataille. Une bataille déléguée passe par le même moteur
qu'une bataille jouée : mêmes troupes, même terrain, mêmes ordres et même
graine donnent la même issue, avec ou sans image. L'IA lève ses troupes par
les mêmes intentions. Contre-épreuve : une bataille dont les pertes ne
reviennent pas au monde, ou une issue calculée à part, « abstraite », font
échouer l'épreuve.

**Dans le monde** : la levée et la bataille, rien de plus — ni marche sur la
carte, ni siège, ni terre qui change de main. Citadelle-Guerre sort des
archives : son moteur de foule (#169) porte la bataille, sur le terrain du
monde. Le pont entre `sim/` et la bataille — des hommes vers le champ, des
pertes vers les foyers — est le cœur du jalon.

## Jalon 8 — La dynastie

**Le joueur** est un personnage : il vieillit, se marie, a des enfants qu'il
éduque, et meurt. Il joue ensuite l'héritier que désigne la loi de succession.

**La décision** : quel mariage (une alliance, une dot, un héritage possible) ;
quelle éducation ; changer la loi de succession, ou risquer le partage.

**L'écran** : l'arbre de la dynastie, les traits et les ambitions de chacun ;
à la mort du chef, l'héritier et le partage des terres sur la carte.

**La preuve** : un partage répartit les lieux sans en perdre ni en créer ; un
héritage par mariage fait passer un lieu d'une maison à l'autre ; une dynastie
sans terre est une défaite, déclarée au tick où elle survient. Contre-épreuve :
un partage qui perd un lieu, ou une défaite jamais déclarée, doivent échouer.

**Dans le monde** : les premières personnes suivies une à une — les
personnages des dynasties, avec des personnalités qui raisonnent en monde.
Les maisons de l'IA ont les leurs, sous les mêmes règles.

## Jalon 9 — La campagne

**Le joueur** déclare la guerre à une maison voisine, fait marcher son armée
sur la carte, la nourrit en route, cherche la bataille ou l'évite — et la
mène en personne, à ses risques, ou la confie à un général de sa dynastie.

**La décision** : marcher vite en vivant sur le pays, ou lentement avec ses
vivres ; risquer la vie du chef pour trancher la guerre, ou confier l'armée à
un cadet qui pourrait en tirer gloire et ambition.

**L'écran** : la colonne sur la carte, ce qu'elle mange dans les lieux
traversés, le creux qu'elle laisse ; la bataille où elle rencontre l'ennemi ;
le chef qui en revient, ou son héritier.

**La preuve** : une colonne qui ne mange pas meurt de faim, et ce qu'elle
mange manque aux lieux traversés ; les morts manquent ensuite aux champs ; un
chef tombé au combat meurt dans le monde, et sa succession suit la loi du
jalon 8. Les batailles entre maisons de l'IA passent par le même moteur que
celles du joueur. Contre-épreuve : une colonne qui mange sans rien retirer
des lieux doit faire échouer la conservation.

**Dans le monde** : la guerre entre maisons, la colonne qui marche et mange,
le général. L'IA mène ses campagnes par le même chemin que le joueur.

## Jalon 10 — Le siège et la paix

**Le joueur** assiège un lieu fortifié — il l'affame, ou donne l'assaut par
la brèche —, défend sa propre capitale, et signe une paix qui cède ou gagne
des terres.

**La décision** : assiéger et attendre, en payant ce que l'armée mange, ou
donner l'assaut et le payer en morts ; céder un lieu pour avoir la paix, ou
continuer la guerre.

**L'écran** : le siège en 3D — les murs, la brèche, les combats de rue ; sa
propre capitale assiégée ; sur la carte, la terre qui change de main à la
paix.

**La preuve** : le siège de sa capitale se livre dans la ville qu'il a bâtie
(jalon 6) : mêmes rues, mêmes murs, d'après le plan que tient `sim/` ; une
ville assiégée mange ses stocks et a faim quand ils sont vides ; une brèche
ne s'ouvre que dans un mur qui existe dans le plan ; un lieu cédé à la paix
change de maître sans qu'aucun lieu se perde ni se crée. Contre-épreuve : un
siège livré dans une ville que seul Unity connaît, ou une paix qui perd un
lieu, font échouer l'épreuve.

**Dans le monde** : le siège, l'assaut, la paix et ses clauses ; la terre
change de main par la guerre. Les engins et les essais de siège de
Citadelle-Guerre (brèche, assaut, combats de rue) servent ici.

## Jalon 11 — L'argent

**Le joueur** emprunte pour acheter une terre, met un lieu en gage, dote sa
fille, frappe monnaie — et peut la dévaluer.

**La décision** : s'endetter pour grandir vite, ou attendre ; dévaluer pour
payer sa guerre, et le payer en inflation ; parier sur le commerce ou sur
l'atelier.

**L'écran** : les prix lieu par lieu sur la carte ; le trésor, la dette et ses
échéances ; l'inflation qui suit une dévaluation.

**La preuve** : la monnaie se conserve — ce qui est frappé vient du métal
extrait, ce qui est prêté sort d'un trésor ; une dévaluation fait monter les
prix (direction, pas valeur) ; une dette se rembourse en pièces réelles, elle
ne s'efface jamais. Contre-épreuve : une monnaie créée sans métal doit faire
échouer la conservation.

**Dans le monde** : la monnaie physique, les prix, le crédit. Les prix
deviennent le signal sur lequel l'IA décide, et les républiques marchandes
trouvent ici leurs outils.

## Jalon 12 — Le premier siècle

**Le joueur** joue de 1400 à 1500 d'un seul trait, sans changer de jeu :
plusieurs générations, des guerres, des mariages, des dettes.

**La décision** : toutes celles des jalons précédents, à l'échelle d'un
siècle.

**L'écran** : la chronique de la dynastie sur cent ans, et la carte de 1500
que la partie a faite.

**La preuve** : un siècle joué d'un trait tient le budget du tick (jalon 1) ;
les agrégations restent conservatives à toutes les échelles ; **chaque
décision pèse** — le nombre de gestes demandés au joueur par année de jeu ne
grandit pas avec son royaume, mesuré sur une partie scriptée qui va du
seigneur au roi. Contre-épreuve : une partie où chaque lieu demande son geste
doit la faire échouer.

**Dans le monde** : la première partie complète.

---

## L'horizon, après le premier siècle

Ce ne sont pas encore des jalons : ils s'écriront quand le jalon 12 sera
atteint, avec ce qu'on aura appris.

- **Les rails de l'histoire** : l'imprimerie, la Réforme, les Grandes
  Découvertes, la vapeur — des étincelles à leur date, que le monde diffuse.
- **L'État qui émerge** : la pyramide qui se centralise, les lois comme
  contraintes sur des flux, jamais comme modificateurs ; le geste passe de
  « où je pose la scierie » à « quelle loi je passe ».
- **Les religions, les cultures, les techniques** et leur diffusion.
- **L'industrie** : la vapeur, les usines, le rail, l'économie de 1900 ; la
  carte, la ville et la bataille, sur la même horloge, jusqu'en 1900.
- **Les batailles de 1900** : lignes, artillerie, fusils, autant d'hommes que
  la machine en tient ; les batailles navales, si on les retient.
- **Le monde entier**, sur une nouvelle carte.

## La réserve

Les lots qui ne servent aucun jalon — venus pour la plupart de l'ancien
`ROADMAP.md` : ville du désert, sauvegarde, audio, localisation… — vivent dans
le milestone **Réserve**, que le pilote ne prend jamais (son titre ne commence
pas par `J`). Un jalon qui en a besoin en tire un lot, le reformule contre
`sim/`, et le range chez lui.

## Ce qui n'est pas un jalon

- **La machine** (l'atelier, la CI, les workflows) ne se change qu'en mode
  direct. Un lot de la chaîne ne touche jamais `atelier/` ni `.github/`.
- **Les prototypes 3D** qui ne portent pas le jalon courant dorment dans
  `3d/archives/`, intacts. Ils en ressortent quand un jalon les demande.
- **Une vue** ne décide jamais un nombre : elle lit `sim/`.
