# Vision — ce que Forge doit devenir

> Ce fichier dit **qui joue, à quoi, dans quel monde, et selon quels
> principes**. Il prime sur tout autre document en cas de conflit, et il est
> fait pour être corrigé : changer une phrase ici déplace les jalons de
> [CAP.md](../CAP.md), qui dit dans quel ordre on construit. Comment le monde
> fonctionne aujourd'hui, formule par formule :
> [jeu/sim/MODELE.md](../jeu/sim/MODELE.md).
>
> Réécrit le 29 septembre 2026, après un entretien avec le propriétaire. Il
> réunit l'ancienne vision du moteur et `OBJECTIF.md`, qui disaient la même
> chose en deux endroits et avaient commencé à se contredire.
>
> Révisé le 28 octobre 2026 : le jeu prend **Europa Universalis IV** pour
> modèle de jeu. Le monde tourne seul ; le joueur prend la tête d'un pays et
> le fait évoluer depuis la carte (décisions 24 à 33, en fin de fichier).

## En un paragraphe

Le monde de 1400 **tourne seul** : chaque maison, chaque république et
l'Église y prélèvent, nourrissent, bâtissent, se marient et se font la guerre,
et on peut le regarder vivre un siècle sans y toucher. On y entre en prenant
la tête d'un **pays réel de 1400** — un royaume, un duché, un émirat ou un
petit comté, catholique, orthodoxe ou musulman, n'importe où entre l'Irlande
et l'Égypte —, et on le **fait évoluer depuis la carte**, à la manière
d'Europa Universalis IV : le temps file, on le met en pause, on décide.
Impôts et greniers, chantiers dans ses provinces, armées et guerres, alliances
et mariages, lois, monnaie et dette : chaque geste est une intention que le
monde applique, et ce sont les gestes mêmes de l'IA. La dynastie qui règne sur
le pays a ses héritiers, leurs personnalités et sa loi de succession, qui peut
coûter des terres. Sa capitale peut s'ouvrir en 3D, pour la voir vivre et la
bâtir à la main. L'histoire allume ses étincelles à leur date — l'imprimerie,
la Réforme, les Grandes Découvertes, la vapeur —, mais qui en profite, qui a
faim et qui règne se décide dans une économie physique où chaque kilo et
chaque pièce d'argent ont une origine. On perd quand le pays n'a plus de
terre. La partie va de 1400 à 1900.

## Ce qui n'existe nulle part ailleurs

On joue comme dans Europa Universalis IV : la carte, le temps qui file, un pays
qu'on fait grandir. Ce qui n'existe pas, c'est **un Europa Universalis dont le
monde est simulé**, et qui tourne sans le joueur :

- sous la carte, des gens : une famine vide une vallée parce que ses gens ont
  faim et partent, pas parce qu'un modificateur le dit ;
- l'armée est faite des hommes de ses foyers ; ses morts manquent ensuite aux
  champs ;
- sa dette, sa monnaie et ses routes pèsent sur les prix du voisin, et
  inversement ;
- l'IA n'a aucun privilège : elle joue avec les mêmes gestes que le joueur, et
  le monde vit tout aussi bien quand personne ne joue ;
- la capitale qu'on ouvre en 3D est un lieu du monde que la carte gouverne :
  on peut y descendre et la bâtir à la main.

| repère | ce qu'on lui prend | ce qu'on refuse |
|---|---|---|
| **Europa Universalis IV** — le modèle de jeu | la carte comme écran principal, le temps continu avec pause et vitesses, un pays qu'on fait évoluer, la diplomatie, la guerre sur la carte, le mode observateur | les points de monarque, les modificateurs (« +10 % ») à la place des causes, les événements à choix qui posent une issue |
| Crusader Kings | la dynastie, les personnalités, la succession | les mille petites actions sans portée, surtout en fin de partie |
| Victoria | l'économie, les prix, l'industrie | des mécaniques codées comme des règles de jeu |
| Manor Lords | la capitale qu'on peut ouvrir et bâtir à la main, dense et vivante | en faire le cœur du jeu ; bâtir toutes ses villes à la main |
| Total War | à l'horizon : la bataille regardée et menée en 3D, sur le même moteur | une bataille calculée à part du monde ; la même bataille rejouée tour après tour |

## Le monde tourne seul

- **Il n'attend pas le joueur.** Dès le premier jour, chaque maison, chaque
  république et l'Église décident avec des raisons de monde — la faim de
  leurs gens, leur grenier, leurs chantiers, leurs voisins —, par les gestes
  du joueur. Le monde qu'on regarde est le même qu'on joue.
- **Le mode observateur.** On peut lancer la partie sans prendre de pays et
  laisser filer les années. C'est la preuve que le monde vit, et la meilleure
  façon de choisir où entrer.
- **Ce qui dit qu'il vit.** Un siècle sans joueur garde une Europe
  vraisemblable : les régions denses de 1400 restent denses, le désert reste
  vide, la population suit l'histoire dans les grandes lignes, aucune maison
  ne reste sans décider ; famines, chantiers, mariages et guerres arrivent par
  leurs causes. Mesuré le 28 octobre 2026, ce n'était pas le cas : sans
  réserve de soudure, Paris perdait 99 % de ses habitants avant avril 1400.
- **Le joueur entre dans ce monde-là.** Prendre la tête d'un pays ne change
  aucune règle : seule change la main qui décide.

## Le joueur : un pays et sa dynastie

- **Le départ.** N'importe quel pays réel de 1400 qui tient de la terre, du
  royaume au petit seigneur, choisi sur la carte. Les six terres de départ
  restent les départs conseillés, petits, pour vivre l'ascension depuis le
  bas. Les républiques et l'Église restent jouées par l'IA.
- **Faire évoluer le pays.** Le joueur gouverne depuis la carte : il fixe ce
  qu'il prend, ouvre ses greniers, bâtit dans ses provinces, lève et mène ses
  armées, s'allie, marie, déclare la guerre et fait la paix, frappe monnaie,
  emprunte, passe des lois. Ses gestes sont en petit nombre et de grande
  portée (principe 6) ; « Les gestes d'un pays », plus bas, les range.
- **Des personnalités.** Chaque membre de la dynastie a des traits, des
  compétences, une éducation, une santé, des ambitions. Un cadet peut
  comploter, un frère se révolter, un fils mal éduqué gouverner mal. Eux
  aussi raisonnent en monde : un complot naît d'une ambition et d'une
  occasion, pas d'un pourcentage.
- **En personne.** Le chef de la dynastie mène ses troupes et peut mourir au
  combat ; quand on ouvre sa capitale en 3D, il marche dans ses rues.
- **La succession.** À sa mort, on joue l'héritier que désigne la loi de
  succession (l'aîné, le partage entre les fils…). Un partage peut coûter
  des terres ; changer la loi est un geste de jeu.
- **La défaite** : le pays n'a plus de terre.
- **Le but.** Rien n'est imposé. Chaque héritier porte ses ambitions
  (devenir duc, roi, unifier un royaume), et les accomplir s'écrit dans la
  chronique de la dynastie ; un score de dynastie (prestige, terres,
  richesse, sur cinq siècles) permet de comparer deux parties. Qui veut
  jouer sans but le peut.

## La carte, et la capitale en 3D

- **La carte est le jeu.** Comme dans Europa Universalis IV, on joue sur la
  carte : les pays, leurs provinces, leurs lieux, les armées, les flux. Tout
  geste de pays se fait depuis elle, et le panneau du pays y dit ce qu'il
  possède, ce qu'il récolte, ce qu'il doit et ce qui menace.
- **La capitale en 3D est une vue, pas un passage obligé.** On peut y
  descendre d'un geste, la voir vivre — fumées, étals, passants — et y tracer
  à la main rues, parcelles et murs. Rien ne s'y fait qui ne puisse aussi se
  commander depuis la carte : un bâtiment se pose dans une province, et le
  plan du monde lui trouve sa parcelle. Les autres domaines grandissent par
  leurs habitants, sous les lois, les impôts et les consignes du joueur.
  Toute ville doit pouvoir se dessiner à partir de ce que le monde contient —
  son plan est une donnée du moteur, pas d'Unity.
- **La bataille se suit sur la carte.** Elle se calcule dans le monde (« La
  guerre », plus bas) ; la regarder et la mener en 3D est un horizon.
- **Une seule horloge, que le joueur règle.** Un tick est un jour. Sur la
  carte, le joueur met en pause ou choisit l'une des cinq vitesses ; la plus
  rapide est bornée par le budget du tick (51 ms mesurés le 28 octobre 2026,
  une vingtaine de jours par seconde). En ville le temps ralentit tout seul.
  Le monde ne s'arrête que quand le joueur le met en pause.
- **Le monde dit ce qui arrive.** Un fil de nouvelles et des alertes — une
  famine, un grenier vide, un voisin qui bâtit, une guerre déclarée — mènent
  au lieu où cela se passe. Ce sont des lectures du monde : jamais un
  événement à choix qui poserait une issue ou un modificateur.

## Les gestes d'un pays

Le joueur ne clique pas sur chaque lieu : il décide pour son pays, et le monde
fait le reste. Un geste coûte **ce que le monde porte** — du grain, des
pièces, des hommes, du temps, la fidélité de ses vassaux —, jamais des points
abstraits : pas de points de monarque, pas d'idées en « +10 % ».

| domaine | gestes | jalon de CAP.md |
|---|---|---|
| la terre et ses gens | fixer la part qu'on prend (l'impôt), ouvrir un grenier | J3, livré |
| bâtir | tracer une route, poser un bâtiment dans une province ; en 3D, la parcelle à la main | J4 en 3D, J6 depuis la carte |
| la cour | marier, éduquer, changer la loi de succession | J6 |
| la guerre et les alliés | revendiquer, lever, marcher, assiéger, livrer bataille, faire la paix ; s'allier, appeler ses alliés | J7 |
| l'argent | frapper, emprunter, mettre en gage, dévaluer, acheter une terre | J8 |
| le gouvernement | inféoder, nommer des intendants, passer une loi | J9 |

Chaque geste existe aussi pour l'IA, par le même chemin (principe 4).

## La terre, cœur du jeu

Tout tourne autour d'une question : **qui tient quel lieu**.

- **Le lieu** est l'unité de la terre. Une cellule du continent couvre
  environ 15 000 km² : elle se découpe en lieux (villages, bourgs, villes,
  avec leurs champs), et c'est le lieu qu'on possède, qu'on hérite, qu'on
  assiège. Un petit seigneur en tient quelques-uns ; un roi, des provinces
  entières. Le lieu a une identité dérivée de `cell_id` : ce n'est jamais une
  seconde clé spatiale.
- **La terre change de main** par la guerre et le siège, par l'héritage et le
  mariage, par l'achat, le gage et la dot, par la révolte et la sécession.
- **La pyramide évolue.** En 1400, on doit l'hommage à un suzerain et on peut
  avoir des vassaux. Au fil des siècles, certains rois centralisent, d'autres
  non : l'État moderne **émerge** de la pyramide, il n'est pas posé. La façon
  de tenir une terre change selon les cultures (le fief, le timar ottoman,
  l'iqta) ; c'est une donnée du monde, pas une exception du code.
- **Les républiques et l'Église** (Venise, Florence, Gênes, la Hanse, les
  évêques, les abbayes) tiennent de la terre sans être des dynasties. Ce sont
  des acteurs de l'IA, avec leurs propres règles (élection, oligarchie,
  succession d'Église). On ne les incarne pas.

## L'économie : des plans à long terme

- **Physique**, comme toujours : chaque kilo a une origine, un transport, un
  stockage, une destination.
- **La monnaie aussi.** L'argent et l'or s'extraient, se frappent,
  circulent, se thésaurisent et se prêtent ; un prince peut dévaluer. Les
  prix naissent lieu par lieu de l'offre et de la demande ; ils sont aussi le
  signal sur lequel l'IA décide.
- **Ce qu'on veut y trouver** : de vrais choix de long terme. Parier sur le
  commerce, sur l'industrie ou sur les deux ; s'endetter pour acheter une
  terre et rembourser pendant vingt ans ; payer une dévaluation en
  inflation ; reconstruire après une guerre. Une décision économique se sent
  sur des décennies.

## La guerre

- **Les soldats sont des habitants.** Ils quittent leur foyer, mangent en
  marchant, meurent ou reviennent ; leurs morts manquent ensuite aux champs.
- **La guerre se joue sur la carte**, comme dans Europa Universalis IV : les
  armées marchent de lieu en lieu, mangent, se rencontrent. Le joueur choisit
  où marcher, quand livrer bataille et quand traiter ; ses généraux
  commandent sur le terrain.
- **Un seul moteur de bataille, dans `sim/`.** Une bataille dure des jours ;
  elle se calcule avec les hommes, leurs vivres, leur chef et le terrain du
  lieu, et rend au monde ses morts, ses blessés et ses fuyards. Les batailles
  entre IA passent par le même. Il n'y a pas de second calcul à côté.
- **Une bataille a un enjeu** : une grande bataille peut trancher une guerre
  et ouvrir une conquête.
- **Le siège affame la place** : ses murs et son grenier décident de combien
  de temps elle tient.
- **À l'horizon, la bataille en 3D.** La regarder et la mener soi-même, le
  siège grandeur nature dans la ville qu'on a bâtie, autant d'hommes que
  possible sur un PC de jeu courant :
  [Citadelle-Guerre](../3d/archives/citadelle-guerre/README.md) (5 000 à
  10 000 hommes, sièges, combats de rue) en reste la base. Ce jour-là, la 3D
  rejoue le moteur de `sim/` et ses ordres sont des intentions : elle n'ajoute
  pas un second moteur.

## Le monde réel

| | |
|---|---|
| étendue | Europe et pourtour méditerranéen : d'Irlande à l'Anatolie, de Norvège à Alexandrie |
| maille | 596 cellules et 1 364 arêtes ; une cellule du continent couvre environ 15 000 km², et un tiers des cellules, des îles pour la plupart, n'ont aucun voisin terrestre |
| période | 1400 → 1900 ; un tick = un jour |
| carte | un fichier, `jeu/data/world-1400.json`, figé par version |

- **L'Europe réelle.** Au premier jour, le monde contient ce que l'histoire
  dit qu'il contient : les grandes maisons, les frontières, les villes, les
  populations de 1400. C'est vrai dans les grandes lignes depuis le jalon 2
  de [CAP.md](../CAP.md) : l'aridité, le Nil, les puissances, les grandes
  maisons et les villes de 1400 sont dans le monde, et le désert est vide.
  C'est vrai **au premier jour** ; que cela tienne quand le monde tourne seul
  est la preuve du jalon 5.
- **Les rails de l'histoire.** L'histoire allume ses étincelles à leur date
  et à leur lieu : l'imprimerie à Mayence, les thèses de Luther, les voyages
  vers l'Amérique, les épidémies, la vapeur. Elle n'impose jamais une
  issue : si quelqu'un en a la force, Constantinople tient. Ce qu'une
  étincelle devient — où elle se diffuse, qui en profite — se décide dans le
  monde.
- **Le reste du monde** est hors carte aujourd'hui ; il sera jouable un jour.
  La carte est donc figée **par version** : le jour où elle s'étend, c'est
  une nouvelle carte, et `cell_id` reste la seule clé.

## Les principes

Ils ne se négocient pas. [AGENTS.md](../AGENTS.md) les donne en une ligne
chacun, dans le même ordre ; ici, leur raison.

1. **Une seule simulation.** Le monde entier tourne en permanence dans
   `jeu/sim/`. La carte, la ville, le tableau, la chronique ne sont que des
   façons de le regarder : ils n'ont aucune donnée à eux et ne décident
   jamais un nombre. Jamais deux bases, jamais une copie « pour
   l'affichage ». La bataille n'est pas une vue : c'est une couche de cette
   simulation, dans `sim/`, qui reçoit du monde ses hommes et son terrain,
   lui rend ses morts, ses blessés et ses fuyards, et ne garde rien pour
   elle ; une bataille en 3D, le jour où elle existera, la regarde.
2. **Le monde raisonne en monde.** Interdit : « si famine alors +20 % de
   criminalité ». Exigé : ils ont faim, ils cherchent, certains volent. Cela
   vaut pour les personnages et pour l'IA. Test à chaque proposition :
   comportement émergent, ou règle codée en dur ?
3. **L'économie est physique.** Tout kilo et toute pièce ont une origine, un
   transport, un stockage, une destination. Rien ne se téléporte ; une
   rupture logistique produit seule ses conséquences.
4. **L'IA a les outils du joueur.** Tout geste du joueur est une intention
   déposée dans le monde (dans `jeu/sim/`, ou dans la bataille pour un ordre
   de combat) ; l'IA dépose les mêmes, par le même chemin, sans bonus caché.
   La 3D n'est que la façon humaine de formuler une intention : un geste de
   jeu qui n'existe qu'en 3D n'existe pas.
5. **Les rails posent un fait, jamais une issue.** Une étincelle historique
   arrive à sa date et à son lieu ; le monde décide de ce qu'elle devient.
6. **Chaque décision pèse.** Le nombre de gestes qu'on demande au joueur dans
   une année de jeu ne grandit pas avec son royaume : c'est leur portée qui
   grandit. Ce qui se répète se délègue (intendants, généraux, lois) ; ce qui
   reste au joueur change quelque chose de visible dans le monde. Un empereur
   ne clique pas plus qu'un seigneur : il fait d'autres gestes.
7. **Réel quand on sait, plausible sinon.**
   - Niveau 1, réel : ce que l'histoire dit clairement — côtes, relief,
     gisements, grandes maisons, frontières, villes, ordres de grandeur des
     populations. Obligatoire ; des sources publiques (atlas, encyclopédies)
     suffisent.
   - Niveau 2, plausible : ce que l'histoire ne dit pas — un petit seigneur
     sans source, le détail d'une ville, une constante de calibration. Généré
     vraisemblable ; une anomalie n'est pas un défaut.
   - Niveau 3 : pas simulé.

   Tout brief qui touche le monde dit son niveau.
8. **Une capacité n'existe que si sa preuve peut échouer.** Prouver le rouge
   d'abord ; un échantillon vide échoue ; un test existant ne s'assouplit
   jamais pour passer.

## Les échelles

```
Monde → Royaume → Province → Cellule → Lieu → Quartier → Bâtiment → Foyer → Personne
```

Chaque niveau peut être simulé seul ; le moteur monte ou descend le détail
selon ce qu'on regarde, et **les agrégations sont conservatives** : cent
personnes agrégées puis désagrégées font cent personnes. La population se
compte par foyers ; les **personnages** — les dynasties, leurs cours, leurs
chefs de guerre — sont les seules personnes suivies une à une.

## La mesure du succès

Pas le nombre de fonctionnalités : ce que le monde fait naître seul. Les
moments qu'on veut vivre :

- laisser tourner le monde de 1400 un siècle sans joueur, et y lire une
  histoire plausible qui n'était écrite nulle part ;
- prendre un petit pays et le voir devenir grand — ou disparaître — par ses
  propres décisions ;
- une grande bataille qui tranche une guerre et ouvre une conquête ;
- le siège de sa capitale, que ses murs et son grenier tiennent ou non ;
- un plan économique sur des décennies — inflation, dette à rembourser,
  commerce ou industrie — qui fait la fortune de la dynastie, ou sa ruine ;
- une famine qui vide une vallée, une route qui enrichit un col, une guerre
  qui dépeuple un comté et fait monter les salaires ailleurs.

Et ce qu'on ne veut jamais vivre : **une fin de partie répétitive**, faite de
mille petites actions sans portée, ou de la même bataille rejouée tour après
tour.

## Ce qui reste à trancher

| question | ce qu'on sait déjà |
|---|---|
| la machine de référence (« un PC de jeu courant ») | Citadelle-Guerre mesure sur un i7-13700K et une RTX 3070 Ti, en 1920 × 1080 |
| les batailles navales | la Méditerranée, la Manche et la Baltique en appellent ; rien n'est décidé |
| la religion et la technique | les rails en allument les étincelles ; leur diffusion reste à écrire |
| combien de lieux dans une cellule | un lieu pour 1 000 km² aujourd'hui (6 619 lieux) ; une terre de départ en tient quatre, un seigneur plausible trois (niveau 2, CAP.md, jalon 3) ; à revoir contre le budget du tick |
| la capitale peut-elle changer de ville | rien n'est décidé |
| quels pays sont jouables | tous ceux qui tiennent de la terre, vassaux compris (décision 26) ; reste à dire si un vassal joué peut refuser l'hommage dès le départ |
| quand la bataille et le siège en 3D reviennent | après le premier siècle (décision 29) ; Citadelle-Guerre attend dans les archives |
| des décisions de cour, à la manière des événements | le fil des nouvelles ne pose aucun choix (décision 31) ; une décision proposée au joueur devrait naître d'une cause du monde et rester un geste ordinaire |

## Les décisions du 29 septembre 2026

Prises en entretien avec le propriétaire. Chacune déplace la roadmap si on la
change.

| # | décision | ce qu'elle a écarté |
|---|---|---|
| 1 | on joue une dynastie : plusieurs personnes au fil de la partie | un seul personnage ; un État sans visage |
| 2 | on commence petit seigneur réel, n'importe où sur la carte, catholique, orthodoxe ou musulman | n'importe quel seigneur, du baron au roi ; une maison inventée ; les seuls Latins |
| 3 | l'héritier est celui que désigne la loi de succession | l'héritier choisi librement |
| 4 | les membres de la dynastie ont des personnalités | une simple lignée |
| 5 | le joueur bâtit sa capitale et gouverne le reste | tout bâtir à la main ; ne rien bâtir |
| 6 | trois vues reliées (carte, ville, bataille), dont la vitesse suit la vue | un zoom continu ; une vitesse que le joueur règle seul |
| 7 | la 3D montre les terres du joueur | toute ville d'Europe ; la seule capitale |
| 8 | la terre change de main par la guerre, l'héritage, le mariage, l'argent et la révolte | — |
| 9 | une pyramide féodale qui évolue, d'où l'État émerge | une pyramide fixe ; des souverains à plat |
| 10 | républiques et Église : des acteurs de l'IA, avec leurs règles | les jouer ; les traiter en dynasties |
| 11 | l'IA a les mêmes outils que le joueur | une IA qui triche |
| 12 | l'Europe réelle : réel quand on sait, plausible sinon | une Europe plausible aux puissances inventées |
| 13 | les rails posent des étincelles, jamais une issue | une histoire sans rails ; des issues imposées |
| 14 | la monnaie est physique et les prix émergent | une monnaie de compte ; pas de monnaie |
| 15 | batailles tactiques obligatoires, jouées ou déléguées au même moteur | une résolution abstraite à part |
| 16 | le chef de la dynastie est en personne : en ville, à la guerre, et il peut y mourir | — |
| 17 | défaite : plus de terre ; pas de victoire imposée, des ambitions et un score de dynastie | une condition de victoire unique |
| 18 | le reste du monde sera jouable un jour | un jeu borné à l'Europe |
| 19 | pas de multijoueur pour l'instant | — |
| 20 | un projet personnel, sans date | une sortie à date |

## Les décisions du 7 octobre 2026

Prises par le propriétaire en relisant ce que les lots construisaient
vraiment (CAP.md, « Le constat qui commande »).

| # | décision | ce qu'elle a écarté |
|---|---|---|
| 21 | une sixième terre de départ en pays de terre crue, l'émirat du Zab (Biskra, sous les Hafsides) : le kit du désert est sa capitale dès le jalon 4 ; les kits des autres terres suivent, Balkans et Morée d'abord, puis l'Ouest | un nouveau kit avant toute capitale ; un désert qui ne serait la terre de personne |
| 22 | la carte du joueur vit dans Unity, avec la ville et la bataille : les trois vues dans un seul jeu ; les vues de Python restent des outils et des captures du journal | une carte dans le navigateur ; une carte en image seulement |
| 23 | l'ordre des neuf jalons du 29 septembre est gardé ; la ville vivante entre au jalon 4, la bataille détaillée au jalon 7 | douze jalons (#344) ; une tranche verticale de chaque pilier |

## Les décisions du 28 octobre 2026

Prises par le propriétaire : « il faut commencer à penser gameplay ; la
simulation tourne seule, avec un monde vivant, et le joueur fait évoluer le
pays ; on vise Europa Universalis IV ». Elles priment sur les décisions
antérieures qu'elles nomment.

| # | décision | ce qu'elle a écarté |
|---|---|---|
| 24 | Europa Universalis IV est le modèle de jeu : la carte, le temps continu avec pause et vitesses, un pays qu'on fait évoluer, la diplomatie et la guerre sur la carte | un jeu centré sur la capitale bâtie à la main |
| 25 | le monde tourne seul, et un mode observateur le montre : un siècle sans joueur reste vivant et vraisemblable, et sa preuve peut échouer | un monde qui attend le joueur ; un monde qui ne vit que là où il regarde |
| 26 | on prend la tête de n'importe quel pays réel de 1400 qui tient de la terre, du royaume au petit seigneur ; les six terres de départ restent les départs conseillés (remplace la décision 2 sur ce point) | le seul petit seigneur |
| 27 | la carte est le jeu ; la capitale en 3D est une vue où l'on peut bâtir à la main, jamais un passage obligé : tout geste de la 3D se commande aussi depuis la carte (précise la décision 5) | la capitale comme cœur du jeu ; un geste qu'on ne ferait qu'en 3D |
| 28 | le joueur règle l'horloge sur la carte : pause et cinq vitesses ; la ville ralentit (remplace la décision 6 sur la vitesse) | une vitesse imposée par la vue |
| 29 | les batailles se calculent dans `sim/`, par un seul moteur, et se suivent sur la carte ; les mener en 3D et le siège grandeur nature passent à l'horizon (remplace la décision 15) | une bataille tactique obligatoire avant le premier siècle ; deux moteurs de bataille |
| 30 | un geste coûte ce que le monde porte : grain, pièces, hommes, temps, fidélité | les points de monarque ; les idées nationales en « +10 % » |
| 31 | le monde parle par un fil de nouvelles et des alertes qui mènent au lieu | les événements scriptés à choix, qui posent une issue ou un modificateur |
| 32 | les kits 3D des autres terres et la ville conquise en 3D passent à l'horizon (précise la décision 7) | toutes les terres de départ en 3D au premier siècle |
| 33 | les jalons gardent leurs numéros et changent de contenu : J5 le monde vivant, J6 le pays et sa dynastie, J7 la guerre sur la carte ; J8 et J9 restent (remplace la décision 23 pour la suite) | renuméroter les jalons et déplacer leurs issues |
