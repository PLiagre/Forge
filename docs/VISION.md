# Vision — ce que Forge doit devenir

> Ce fichier dit **qui joue, à quoi, dans quel monde, et selon quels
> principes**. Il prime sur tout autre document en cas de conflit, et il est
> fait pour être corrigé : changer une phrase ici déplace les paliers de
> [CAP.md](../CAP.md), qui dit dans quel ordre on construit. Comment le monde
> fonctionne aujourd'hui, formule par formule :
> [jeu/sim/MODELE.md](../jeu/sim/MODELE.md).
>
> Les décisions du propriétaire sont numérotées en fin de fichier, par date.
> Les plus récentes priment sur celles qu'elles contredisent.

## En un paragraphe

Le monde de 1400 **tourne seul** : chaque maison, chaque république et
l'Église y prélèvent, nourrissent, bâtissent, se marient et se font la guerre,
et on peut le regarder vivre un siècle sans y toucher. On y entre en prenant
la tête d'un **pays réel de 1400** — un royaume, un duché, un émirat ou un
petit comté, catholique, orthodoxe ou musulman, n'importe où entre l'Irlande
et l'Égypte —, et on le **fait évoluer depuis la carte**, à la manière
d'Europa Universalis IV : le temps file, on le met en pause, on décide.
Impôts et greniers, bâtiments dans ses provinces, armées et guerres, alliances
et mariages, lois, monnaie et dette : chaque geste est une intention que le
monde applique, et ce sont les gestes mêmes de l'IA. Ses bâtiments, ses lois,
ses conseillers et ce qui arrive au monde posent des **modificateurs** — « Moulin :
+10 % de grain récolté dans la province » —, que l'infobulle détaille ; ses
quatre **jauges** (la Concorde, le Renom, le Droit, et les points de la Plume,
du Sceau et de l'Épée) montent et baissent par les causes du monde et se
dépensent en gestes. Tous ces chiffres se règlent dans des fichiers de
données, comme les scripts d'EU4. La dynastie qui règne sur
le pays a ses héritiers, leurs personnalités et sa loi de succession, qui peut
coûter des terres. Sa capitale peut s'ouvrir en 3D, pour la voir vivre et la
bâtir à la main. L'histoire allume ses étincelles à leur date — l'imprimerie,
la Réforme, les Grandes Découvertes, la vapeur —, mais qui en profite, qui a
faim et qui règne se décide dans une économie physique où chaque kilo et
chaque pièce d'argent ont une origine. On perd quand le pays n'a plus de
terre. La partie va de 1400 à 1900.

## Ce qui n'existe nulle part ailleurs

On joue comme dans Europa Universalis IV : la carte, le temps qui file, un pays
qu'on fait grandir, des modificateurs qu'on empile et des jauges qu'on
dépense. Ce qui n'existe pas, c'est **un Europa Universalis dont le monde est
simulé**, et qui tourne sans le joueur :

- sous les modificateurs, des kilos : un moulin à +10 % récolte vraiment 10 %
  de grain en plus, qui se transporte, se stocke et se mange ; un modificateur
  change un taux du moteur, il ne crée jamais un kilo ni une pièce ;
- sous la carte, des gens : une famine pose ses modificateurs, et elle vide
  aussi une vallée parce que ses gens ont faim et partent ;
- l'armée est faite des hommes de ses foyers ; ses morts manquent ensuite aux
  champs ;
- sa dette, sa monnaie et ses routes pèsent sur les prix du voisin, et
  inversement ;
- l'IA n'a aucun privilège : elle joue avec les mêmes gestes, les mêmes
  modificateurs et les mêmes jauges que le joueur, sans bonus caché, et le
  monde vit tout aussi bien quand personne ne joue ;
- les jauges du pays naissent de personnes : les points d'un souverain
  viennent de ses compétences et de celles de son conseil, pas d'une note
  fixe ;
- la capitale qu'on ouvre en 3D est un lieu du monde que la carte gouverne :
  on peut y descendre et la bâtir à la main.

| repère | ce qu'on lui prend | ce qu'on refuse |
|---|---|---|
| **Europa Universalis IV** — le modèle de jeu | la carte comme écran principal, le temps continu avec pause et vitesses, un pays qu'on fait évoluer, la diplomatie, la guerre sur la carte, le mode observateur ; les modificateurs partout et leur infobulle détaillée ; la stabilité, le prestige, la légitimité et les points de monarque, sous nos noms (Concorde, Renom, Droit, Plume, Sceau, Épée) ; les bâtiments de province ; les événements à choix ; les chiffres dans des fichiers de données | un modificateur qui crée un kilo ou une pièce hors du moteur ; des points tirés d'une note fixe plutôt que des personnes ; un événement qui impose une issue ; un bonus caché de l'IA |
| Crusader Kings | la dynastie, les personnalités, la succession | les mille petites actions sans portée, surtout en fin de partie |
| Victoria | l'économie, les prix, l'industrie | des mécaniques codées comme des règles de jeu |
| Manor Lords | la ville qu'on bâtit à la main, dense et vivante : l'une des trois pistes du jeu, d'abord sur le kit du désert (décisions 42 et 48) | bâtir toutes ses villes à la main ; un geste de jeu qui n'existerait qu'en 3D |
| Total War | plus tard : la bataille regardée et menée en 3D, sur le même moteur (décision 42) | une bataille calculée à part du monde ; la même bataille rejouée tour après tour |

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
  leurs causes. Ce n'est pas encore tenu : la soudure tient la première
  année, mais les grandes villes se vident ensuite, tant que l'arrière-pays
  ne les nourrit pas.
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
  comploter, un frère se révolter, un fils mal éduqué gouverner mal. Ses
  compétences font les points du pays (« Les modificateurs et les jauges »,
  plus bas) ; ses décisions lisent le monde : un complot naît d'une ambition
  et d'une occasion.
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

## La carte, la ville et la bataille

Trois façons de jouer le même monde, et trois pistes sur lesquelles le jeu
avance chaque semaine ([CAP.md](../CAP.md)) : la carte à la manière d'Europa
Universalis, la ville bâtie à la main à la manière de Manor Lords, et, plus
tard, la bataille à la manière de Total War (décision 42).

- **La carte est le jeu.** Comme dans Europa Universalis IV, on joue sur la
  carte : les pays, leurs provinces, leurs lieux, les armées, les flux. Tout
  geste de pays se fait depuis elle, et le panneau du pays y dit ce qu'il
  possède, ce qu'il récolte, ce qu'il doit et ce qui menace.
- **La ville se bâtit à la main.** On entre dans sa capitale depuis la
  carte, on la voit vivre — fumées, étals, passants — et on y trace rues,
  parcelles et murs, on y pose ses bâtiments. Ce qu'on y bâtit est une
  intention du monde, comme tout geste (principe 4) : l'IA bâtit par le même
  chemin, sans 3D, et un bâtiment peut aussi se poser depuis la carte, où le
  plan du monde lui trouve sa parcelle. Les autres domaines grandissent par
  leurs habitants, sous les lois, les impôts et les consignes du joueur.
  Toute ville doit pouvoir se dessiner à partir de ce que le monde contient —
  son plan est une donnée du moteur, pas d'Unity.
- **La bataille se suit sur la carte.** Elle se calcule dans le monde (« La
  guerre », plus bas) ; la regarder et la mener en 3D vient plus tard.
- **Une seule horloge, que le joueur règle.** Un tick est un jour. Sur la
  carte, le joueur met en pause ou choisit l'une des cinq vitesses ; la plus
  rapide est bornée par le budget du tick, 100 ms au plus avec l'IA.
  En ville le temps ralentit tout seul.
  Le monde ne s'arrête que quand le joueur le met en pause.
- **Le monde dit ce qui arrive.** Un fil de nouvelles et des alertes — une
  famine, un grenier vide, un voisin qui bâtit, une guerre déclarée — mènent
  au lieu où cela se passe ; ce sont des lectures du monde. Ce qui arrive
  pose aussi ses modificateurs (une famine, une révolte, une épidémie, une
  guerre), visibles dans l'infobulle de chaque lieu touché. Et certaines
  causes du monde — une famine, une révolte, une succession contestée —
  ouvrent un **événement à choix** : deux ou trois réponses, chacune pose des
  modificateurs ou dépense une jauge, aucune n'impose une issue ; l'IA y
  répond par le même chemin (décision 41).

## Les gestes d'un pays

Le joueur ne clique pas sur chaque lieu : il décide pour son pays, et le monde
fait le reste. Un geste coûte **ce que le monde porte** — du grain, des
pièces, des hommes, du temps, la fidélité de ses vassaux — et, selon le
geste, des points de ses jauges : la Plume pour administrer, le Sceau pour
traiter, l'Épée pour combattre, ou un peu de sa Concorde, de son Renom, de son
Droit. Ce qu'il bâtit, ce qu'il décrète et qui il nomme posent ensuite leurs
modificateurs.

| domaine | gestes |
|---|---|
| la terre et ses gens | fixer la part qu'on prend (l'impôt), ouvrir un grenier |
| bâtir | poser un bâtiment dans une province, qui coûte du grain, des pièces, des bras et du temps et pose ses modificateurs ; tracer une route ; dans la ville, la parcelle à la main |
| les jauges | dépenser la Plume, le Sceau ou l'Épée pour un geste ; répondre à un événement à choix |
| la cour | marier, éduquer, changer la loi de succession, nommer son conseil |
| la guerre et les alliés | revendiquer, lever, marcher, assiéger, livrer bataille, faire la paix ; s'allier, appeler ses alliés |
| l'argent | frapper, emprunter, mettre en gage, dévaluer, acheter une terre |
| le gouvernement | inféoder, nommer des intendants, passer une loi, choisir une idée |

L'ordre dans lequel ils arrivent est celui des paliers de
[CAP.md](../CAP.md).

Chaque geste existe aussi pour l'IA, par le même chemin, avec les mêmes
modificateurs et les mêmes jauges (principe 4).

## Les modificateurs et les jauges

Ce qui fait de Forge un jeu, et pas seulement une simulation qu'on regarde
(décisions 34 à 38).

- **Un modificateur** a un nom, une source, une cible, une grandeur du moteur,
  une valeur et une durée : « Moulin de Saint-Denis : +10 % de grain récolté
  dans la province, tant que le moulin tient ». La **source** dit qui le pose :
  un bâtiment, une loi, une idée, un conseiller, un événement du monde
  (famine, guerre, révolte, épidémie) ou une jauge du pays ; un modificateur
  sans source n'existe pas. La **cible** est un pays, une province ou une
  cellule, ou un lieu. La **grandeur** est un taux que le moteur lit déjà : la
  récolte, le prélèvement, la natalité, la mortalité, les départs, le coût et
  la durée d'un chantier, la levée, le commerce. La **durée** est un nombre de
  jours, ou la vie de sa source.
- **Ils s'additionnent.** Les modificateurs d'une même grandeur qui touchent
  un lieu — le sien, ceux de sa cellule, de sa province et de son pays —
  s'ajoutent, dans un ordre fixé, et l'infobulle en donne le détail ligne par
  ligne, comme dans EU4 : « Récolte : +10 % moulin, −25 % famine ».
- **L'économie reste physique dessous.** Un modificateur change un taux ; il ne
  crée jamais un kilo ni une pièce hors du moteur. Le moulin à +10 % récolte
  10 % de grain en plus, qui entre au grenier, voyage en convoi et se mange ;
  rien ne s'ajoute à un stock sans passer par la récolte, le transport ou
  l'échange (principe 3).
- **Quatre jauges par pays, à notre façon.** La **Concorde** (de −3 à +3) dit
  si le pays tient ensemble ; le **Renom**, ce qu'on dit de lui ; le **Droit**,
  ce qui fonde son souverain ; trois réserves de points, la **Plume**
  (administrer), le **Sceau** (traiter) et l'**Épée** (combattre), se
  remplissent chaque mois des compétences du souverain et de son conseil — des
  personnes du monde, pas une note fixe. Les jauges bougent par des causes du
  monde (une famine fait baisser la Concorde, une victoire monte le Renom, une
  succession contestée entame le Droit) et par les gestes qui les dépensent ;
  chacune pose à son tour ses modificateurs (une Concorde basse fait partir
  plus de foyers).
- **Les chiffres vivent dans des fichiers de données**, sous `jeu/data/`,
  lisibles et modifiables sans toucher au code, comme les scripts d'EU4 :
  bâtiments, modificateurs, jauges, coûts. Le moteur et l'IA lisent les mêmes.
- **L'IA a les mêmes**, et rien de plus : aucun modificateur réservé, aucune
  jauge qui se remplisse plus vite pour elle.

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
- **Plus tard, la bataille en 3D.** La regarder et la mener soi-même, le
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
  populations de 1400. C'est vrai dans les grandes lignes : l'aridité, le Nil, les puissances, les grandes
  maisons et les villes de 1400 sont dans le monde, et le désert est vide.
  C'est vrai **au premier jour** ; que cela tienne quand le monde tourne seul
  reste à prouver.
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
2. **Des modificateurs partout, sur un monde qui reste physique.** Comme
   dans EU4, les bâtiments, les lois, les idées, les conseillers, les
   événements du monde et les jauges du pays posent des modificateurs : un
   nom, une source, une cible, une grandeur du moteur, une valeur, une durée.
   Ils s'additionnent dans un ordre fixé et l'infobulle en donne le détail.
   Un modificateur change un taux que le moteur lit ; il ne remplace jamais
   la cause qu'il nomme (une famine pose ses modificateurs, et ses gens ont
   toujours faim, cherchent et partent), et il ne crée jamais un kilo ni une
   pièce. Ses valeurs vivent dans les fichiers de données. Les personnages et
   l'IA décident sur le monde — la faim, le grenier, les voisins — et sur les
   modificateurs qu'ils y lisent. Test à chaque proposition : quelle source,
   quelle cible, quelle grandeur, et où va le kilo ? (Ce principe remplace,
   depuis le 6 novembre 2026, « le monde raisonne en monde », qui interdisait
   le « +20 % » : décision 34.)
3. **L'économie est physique.** Tout kilo et toute pièce ont une origine, un
   transport, un stockage, une destination. Rien ne se téléporte ; une
   rupture logistique produit seule ses conséquences. Un modificateur change
   un taux du moteur, jamais un stock : le grain qu'il ajoute se récolte
   (décision 35).
4. **L'IA a les outils du joueur.** Tout geste du joueur est une intention
   déposée dans le monde (dans `jeu/sim/`, ou dans la bataille pour un ordre
   de combat) ; l'IA dépose les mêmes, par le même chemin, avec les mêmes
   modificateurs et les mêmes jauges, sans bonus caché (décision 38).
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

   Toute fiche de lot qui touche le monde dit son niveau.
8. **Une capacité n'existe que si sa preuve peut échouer.** Prouver le rouge
   d'abord ; un échantillon vide échoue. Un changement du monde met à jour
   les tests qu'il touche, dans la même PR, en disant pourquoi : un test juge
   le monde livré, jamais un « monde d'avant » gardé pour lui. Un test qui ne
   dit plus rien du monde livré se réécrit aussi strict, ou se retire en le
   disant. Les longues preuves (un an, dix ans) tournent la nuit et ne
   bloquent pas une fusion (décision 47).

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
| combien de lieux dans une cellule | un lieu pour 1 000 km² aujourd'hui (6 619 lieux) ; une terre de départ en tient quatre, un seigneur plausible trois (niveau 2) ; à revoir contre le budget du tick |
| la capitale peut-elle changer de ville | rien n'est décidé |
| quels pays sont jouables | tous ceux qui tiennent de la terre, vassaux compris (décision 26) ; reste à dire si un vassal joué peut refuser l'hommage dès le départ |
| quand la bataille et le siège en 3D reviennent | plus tard (décision 42) : un samedi le dira ; Citadelle-Guerre attend dans les archives |
| le décor d'Occident de la ville | le kit du désert d'abord (décision 48) ; il se décidera un samedi |
| un bâtiment de la ville reste-t-il commandable depuis la carte | oui aujourd'hui (décision 27) ; la caserne du palier 1 le dira |
| quels événements à choix, et lesquels d'abord | ils naissent d'une cause du monde et posent des modificateurs ou dépensent une jauge (décision 41) ; leur liste et leurs choix restent à écrire, dans les fichiers de données |
| les valeurs des modificateurs et des bâtiments | niveau 2, dans `jeu/data/` ; un réel sourcé (un moulin de 1400, ce qu'il rendait) les remplace quand on le sait |
| le conseil du souverain | ses points naissent du souverain et de son conseil (décision 36) ; en 1400, le conseil n'existe pas encore dans le monde : les conseillers sont des personnes à venir, et des sources de modificateurs |
| les idées et les lois | des sources de modificateurs (décision 34) ; leur liste et leur prix restent à écrire |

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
| 23 | l'ordre des neuf jalons du 29 septembre est gardé ; la ville vivante entre au jalon 4, la bataille détaillée au jalon 7 (**remplacée** par la décision 43) | douze jalons (#344) ; une tranche verticale de chaque pilier |

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
| 27 | la carte est le jeu ; la capitale en 3D est une vue où l'on peut bâtir à la main, jamais un passage obligé : tout geste de la 3D se commande aussi depuis la carte (précise la décision 5 ; **révisée** par la décision 42 : la ville bâtie à la main est l'une des trois pistes) | la capitale comme cœur du jeu ; un geste qu'on ne ferait qu'en 3D |
| 28 | le joueur règle l'horloge sur la carte : pause et cinq vitesses ; la ville ralentit (remplace la décision 6 sur la vitesse) | une vitesse imposée par la vue |
| 29 | les batailles se calculent dans `sim/`, par un seul moteur, et se suivent sur la carte ; les mener en 3D et le siège grandeur nature passent à l'horizon (remplace la décision 15 ; « plus tard », décision 42) | une bataille tactique obligatoire avant le premier siècle ; deux moteurs de bataille |
| 30 | un geste coûte ce que le monde porte : grain, pièces, hommes, temps, fidélité (**remplacée** par les décisions 34 et 36) | les points de monarque ; les idées nationales en « +10 % » |
| 31 | le monde parle par un fil de nouvelles et des alertes qui mènent au lieu (**révisée** par les décisions 34 et 41 : le monde pose aussi des modificateurs, et certaines causes ouvrent un événement à choix) | les événements scriptés à choix, qui posent une issue ou un modificateur |
| 32 | les kits 3D des autres terres et la ville conquise en 3D passent à l'horizon (précise la décision 7 ; **révisée** par la décision 48) | toutes les terres de départ en 3D au premier siècle |
| 33 | les jalons gardent leurs numéros et changent de contenu : J5 le monde vivant, J6 le pays et sa dynastie, J7 la guerre sur la carte ; J8 et J9 restent (remplace la décision 23 pour la suite ; **remplacée** par la décision 43) | renuméroter les jalons et déplacer leurs issues |

## Les décisions du 6 novembre 2026

Prises par le propriétaire : « Forge se rapproche d'Europa Universalis IV. Le
monde tourne seul comme une simulation, mais c'est un jeu : le joueur a des
gestes, et ses gestes jouent sur des métriques paramétrables. » Elles priment
sur toutes les précédentes qu'elles contredisent. Les décisions 39 à 41 sont
ses réponses du 7 novembre.

| # | décision | ce qu'elle a écarté |
|---|---|---|
| 34 | des modificateurs partout, comme dans EU4 : bâtiments, lois, idées, conseillers, événements du monde (famine, guerre, révolte, épidémie) et jauges du pays posent des modificateurs ; chacun a un nom, une source, une cible (pays, province ou cellule, lieu), une grandeur du moteur (récolte, prélèvement, natalité, mortalité, départs, coût et durée d'un chantier, levée, commerce…), une valeur et une durée ; ceux d'une même cible s'additionnent dans un ordre déterministe, et l'infobulle en donne le détail (remplace le principe 2 et la décision 30, révise la décision 31) | « le monde raisonne en monde », qui interdisait le « +10 % » ; un monde qui ne se règle par aucun chiffre lisible |
| 35 | l'économie reste physique sous les modificateurs : un modificateur change un taux du moteur, il ne crée jamais un kilo ni une pièce hors du moteur ; un moulin à +10 % produit vraiment 10 % de grain en plus, qui se transporte, se stocke et se mange (le principe 3 tient) | un bonus qui s'ajoute au stock sans origine |
| 36 | quatre jauges de pays, à notre façon : l'équivalent de la stabilité, du prestige, de la légitimité et des points de monarque d'EU4, sous nos noms ; les points naissent des compétences du souverain et de son conseil, des personnes réelles du jalon 6 ; les jauges bougent par des causes du monde et par des gestes qui les dépensent, et chacune pose ses modificateurs | les noms et les règles d'EU4 recopiés ; des points d'une note fixe |
| 37 | les chiffres vivent dans des fichiers de données lisibles sous `jeu/data/` (bâtiments, modificateurs, jauges, coûts), qu'on modifie sans toucher au code, comme les scripts d'EU4 ; le moteur et l'IA lisent les mêmes ; le moteur reste sur la bibliothèque standard (`tomllib`) | des constantes du jeu dispersées dans le code |
| 38 | l'IA a les mêmes modificateurs et les mêmes jauges, sans bonus caché (le principe 4 tient) | une IA qui triche pour tenir |
| 39 | les jauges s'appellent la **Concorde** (de −3 à +3, la stabilité), le **Renom** (le prestige), le **Droit** (la légitimité), et trois réserves de points, la **Plume** (administrer), le **Sceau** (traiter) et l'**Épée** (combattre) ; les chefs de 1400 reçoivent tout de suite des compétences de gestion, de diplomatie et de guerre (de 0 à 10, niveau 2) pour que les points coulent dès 1400 ; #434 garde les traits, l'hérédité et l'éducation | des réserves vides jusqu'à la dynastie ; un pays sans réserves de points |
| 40 | le jalon 4 se clôt : le socle et la carte dans la langue du cabinet (#849, #850) passent au jalon 6 avec la barre et le panneau du pays, le jeu qui s'ouvre en pause (#860) au jalon 5 avec l'observateur ; la langue de la capitale (#851), le prix d'un chantier dans son panneau (#419), la preuve complète du jalon (#508), les 60 images par seconde (#962) et les maisons regroupées (#960) vont à la Réserve (**révisée** par les décisions 43 et 48 : la ville avance chaque semaine) | finir la capitale en 3D avant le pays |
| 41 | des événements à choix, nés d'une cause du monde (une famine, une révolte, une succession contestée) : deux ou trois choix, chacun pose des modificateurs ou dépense une jauge, aucun n'impose une issue ; l'IA choisit par le même chemin ; un lot, après les jauges | un monde qui ne propose jamais de choix ; des événements scriptés qui imposent l'histoire |

## Les décisions du 14 novembre 2026

Prises par le propriétaire en mettant la chaîne en pause : « le système est
devenu trop complexe, il livre de petits lots invisibles à l'écran, et je ne
suis plus ». Elles priment sur toutes les précédentes qu'elles contredisent,
et sur tout autre fichier du dépôt.

| # | décision | ce qu'elle a écarté |
|---|---|---|
| 42 | la vision à long terme reste : la carte à la manière d'Europa Universalis, la ville bâtie à la main à la manière de Manor Lords, la bataille à la manière de Total War plus tard (révise la décision 27 ; précise les décisions 24 et 29) | une ville qui ne serait qu'une vue ; un jeu de carte seul |
| 43 | on avance par paliers jouables d'une semaine ; chaque palier fait une avancée majeure sur trois pistes : le monde (carte et simulation), la ville 3D, l'interface ; chaque samedi le propriétaire joue la démo et réoriente ; un palier est atteint quand il l'a joué et qu'il dit oui (remplace les jalons : décisions 23 et 33) | neuf jalons longs ; un jalon atteint par une preuve seule |
| 44 | la chaîne d'agents reste : c'est elle qui fait le travail pendant la semaine ; le mode direct ne sert qu'à la refonte, puis aux réparations quand le propriétaire est là | tout faire en mode direct ; une chaîne que le mode direct double |
| 45 | la chaîne se répartit par niveau de jugement, pas par étape, et celui qui conçoit un lot le construit : le CTO (Fable) tire les lots, tranche, débloque et répond de la démo ; le chef de lot (Opus) conçoit, code le difficile et tient la PR ; le développeur (Sonnet) fait les tâches bornées ; le relecteur (Opus, autre session) rend un verdict ; le lecteur (Haiku) résume et ne juge jamais ; changer un rôle de modèle reste une ligne de `atelier.toml` | un rôle par étape ; un brief écrit à froid par un agent pour un autre |
| 46 | plus de plafond de taille : un lot est l'avancée d'une piste pour un palier | les petits lots ; un lot qui code et un lot qui prouve |
| 47 | un changement du monde met à jour les tests qu'il touche, dans la même PR, en disant pourquoi ; les longues preuves (un an, dix ans) tournent la nuit et ne bloquent plus une fusion (réécrit le principe 8) | « un test existant ne s'assouplit jamais », qui faisait de chaque test touché une question au propriétaire |
| 48 | la ville avance d'abord sur le kit du désert ; le décor d'Occident se décidera un samedi (révise les décisions 32 et 40) | attendre un kit d'Occident pour faire avancer la ville |
| 49 | plus aucun reliquat des anciens lots dans le dépôt : ni brief, ni rapport, ni commentaire qui raconte un lot ; les tests sont gardés comme filet | un dépôt qui porte son histoire dans ses fichiers |
| 50 | le quota de l'abonnement n'est plus le premier frein, mais il se mesure : chaque appel relève ce qu'il coûte, par rôle et par lot | une organisation dont on ne sait pas ce qu'elle consomme |
