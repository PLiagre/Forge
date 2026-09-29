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

## En un paragraphe

On incarne une petite dynastie réelle de 1400 — catholique, orthodoxe ou
musulmane, n'importe où entre l'Irlande et l'Égypte. On bâtit à la main, en
3D, la ville de sa cour ; on gouverne ses autres terres sur la carte, par des
lois, des impôts et des consignes. La terre se gagne et se perd par la guerre,
l'héritage, le mariage, l'argent et la révolte ; ses batailles, on les mène
soi-même ou on les confie à un général. Chaque héritier a sa personnalité et
ses ambitions, et la loi de succession peut coûter des terres. En face, des
dynasties, des républiques et une Église jouées par l'IA, avec exactement les
mêmes outils. L'histoire allume ses étincelles à leur date — l'imprimerie, la
Réforme, les Grandes Découvertes, la vapeur —, mais qui en profite, qui a faim
et qui règne se décide dans une économie physique où chaque kilo et chaque
pièce d'argent ont une origine. On perd quand on n'a plus de terre. La partie
va de 1400 à 1900.

## Ce qui n'existe nulle part ailleurs

Chacun des jeux qui nous servent de repère existe déjà. Ce qui n'existe pas,
c'est **le passage de l'un à l'autre dans un seul monde** :

- la ville qu'on bâtit en 3D est un lieu du monde que la carte gouverne, et
  **le terrain du siège** le jour où on vient la prendre : on défend les murs
  qu'on a tracés, dans les rues qu'on a ouvertes ;
- la bataille se livre avec les hommes de ses foyers, et ses morts manquent
  ensuite aux champs ;
- sa dette, sa monnaie et ses routes pèsent sur les prix du voisin, et
  inversement ;
- l'IA n'a aucun privilège : elle joue avec les mêmes gestes que le joueur.

| repère | ce qu'on lui prend | ce qu'on refuse |
|---|---|---|
| Manor Lords | la capitale bâtie à la main, dense et vivante | bâtir toutes ses villes à la main |
| Crusader Kings | la dynastie, les personnalités, la succession | les mille petites actions sans portée, surtout en fin de partie |
| Europa Universalis | la carte, les royaumes, la diplomatie | les modificateurs (« +10 % ») à la place des causes |
| Victoria | l'économie, les prix, l'industrie | des mécaniques codées comme des règles de jeu |
| Total War | la bataille tactique en temps réel | la même bataille rejouée tour après tour |

## Le joueur : une dynastie

- **Le départ.** Un petit seigneur réel de 1400, choisi n'importe où sur la
  carte. Les grandes maisons, les républiques et l'Église sont jouées par
  l'IA : on vit toujours l'ascension depuis le bas.
- **Des personnalités.** Chaque membre de la dynastie a des traits, des
  compétences, une éducation, une santé, des ambitions. Un cadet peut
  comploter, un frère se révolter, un fils mal éduqué gouverner mal. Eux
  aussi raisonnent en monde : un complot naît d'une ambition et d'une
  occasion, pas d'un pourcentage.
- **En personne.** Le chef de la dynastie marche dans sa ville, mène ses
  troupes, et peut mourir au combat.
- **La succession.** À sa mort, on joue l'héritier que désigne la loi de
  succession (l'aîné, le partage entre les fils…). Un partage peut coûter
  des terres ; changer la loi est un geste de jeu.
- **La défaite** : il ne reste plus de terre.
- **Le but.** Rien n'est imposé. Chaque héritier porte ses ambitions
  (devenir duc, roi, unifier un royaume), et les accomplir s'écrit dans la
  chronique de la dynastie ; un score de dynastie (prestige, terres,
  richesse, sur cinq siècles) permet de comparer deux parties. Qui veut
  jouer sans but le peut.

## Deux échelles, trois vues, une horloge

- **Sa capitale, on la bâtit.** C'est la seule ville qu'on construit à la
  main : tracer les rues, découper les parcelles, poser les ateliers et les
  murs. **Le reste, on le gouverne** : les autres domaines grandissent par
  leurs habitants, sous les lois, les impôts et les consignes du joueur.
  Les deux phrases que le dépôt portait sans les accorder — « le joueur crée
  des conditions » et « le joueur pose les bâtiments » — sont vraies toutes
  les deux, l'une pour le reste, l'autre pour la capitale.
- **Trois vues du même monde** : la carte (l'Europe, les royaumes, ses
  terres), la ville (ses terres en 3D : sa capitale, et ses autres domaines à
  inspecter) et le champ de bataille. On passe de l'une à l'autre par une
  transition. Les villes étrangères restent sur la carte ; une ville conquise
  s'ouvre en 3D, donc toute ville doit pouvoir se dessiner à partir de ce que
  le monde contient — son plan est une donnée du moteur, pas d'Unity.
- **Une seule horloge, dont la vitesse suit la vue.** Un tick est un jour.
  En ville le temps ralentit tout seul (une année ≈ une heure) ; sur la
  carte il accélère (une année ≈ une minute) ; pendant une bataille jouée, le
  monde s'arrête.

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
- **Les batailles tactiques sont obligatoires** : toute bataille est une vraie
  bataille, sur un vrai terrain, et le joueur choisit — il la mène, ou il la
  confie à un général. Le **même moteur de bataille** la calcule alors sans
  image, plus vite que le temps réel ; les batailles entre IA passent par lui
  aussi. Il n'y a pas de second calcul, « abstrait », à côté.
- **Une bataille a un enjeu** : une grande bataille peut trancher une guerre
  et ouvrir une conquête.
- **Les sièges se jouent grandeur nature** : remparts, brèches, combats de
  rue. Quand on assiège sa capitale, c'est la ville qu'on a bâtie qui est le
  terrain.
- **Autant d'hommes que possible** sur un PC de jeu courant. Les batailles
  changent en cinq siècles — des piques et des arbalètes aux lignes, à
  l'artillerie et aux fusils — et leur taille avec elles.
  [Citadelle-Guerre](../3d/archives/citadelle-guerre/README.md) (5 000 à
  10 000 hommes, sièges, combats de rue) en est la base.

## Le monde réel

| | |
|---|---|
| étendue | Europe et pourtour méditerranéen : d'Irlande à l'Anatolie, de Norvège à Alexandrie |
| maille | 596 cellules et 1 364 arêtes ; une cellule du continent couvre environ 15 000 km², et un tiers des cellules, des îles pour la plupart, n'ont aucun voisin terrestre |
| période | 1400 → 1900 ; un tick = un jour |
| carte | un fichier, `jeu/data/world-1400.json`, figé par version |

- **L'Europe réelle.** Au premier jour, le monde contient ce que l'histoire
  dit qu'il contient : les grandes maisons, les frontières, les villes, les
  populations de 1400. Ce n'est pas encore le cas — l'amorçage est un proxy,
  et le moteur ne connaît pas l'aridité : le désert occidental égyptien y est
  aussi peuplé que le delta du Nil. C'est un jalon de [CAP.md](../CAP.md).
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
   l'affichage ». La bataille tactique n'est pas une vue : c'est une couche
   de cette simulation, qui reçoit du monde ses hommes et son terrain, lui
   rend ses morts, ses blessés et ses fuyards, et ne garde rien pour elle.
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

- une grande bataille qui tranche une guerre et ouvre une conquête ;
- la défense de sa citadelle, grandeur nature, dans la ville qu'on a bâtie ;
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
| où se dessine la carte du joueur | les vues d'aujourd'hui (tableau, chronique, relief forge3d) sont des outils de développement ; la carte du joueur pourrait vivre dans Unity, avec la ville et la bataille |
| les batailles navales | la Méditerranée, la Manche et la Baltique en appellent ; rien n'est décidé |
| la religion et la technique | les rails en allument les étincelles ; leur diffusion reste à écrire |
| combien de lieux dans une cellule | assez pour qu'un petit seigneur en tienne quelques-uns ; à mesurer contre le budget du tick |
| la capitale peut-elle changer de ville | rien n'est décidé |

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
