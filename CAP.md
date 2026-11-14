# CAP — des paliers jouables d'une semaine

Ce que le jeu doit devenir : [docs/VISION.md](docs/VISION.md). Ce fichier dit
dans quel ordre on y va. Le palier en cours vit sur GitHub : son issue
épinglée, « Palier n », où le propriétaire écrit le samedi et où le CTO
propose la suite, et son jalon, qui porte ses lots. Ce fichier se change en
mode direct.

## D'où l'on part

Une carte d'Europe en 596 cases, une horloge, six maisons à choisir, des
panneaux de texte, six gestes, l'infobulle des modificateurs, une ville 3D au
désert (Biskra). Ni guerre, ni diplomatie, ni argent, ni dynastie jouable, ni
but.

## La règle d'un palier

- **Un palier dure une semaine**, et il est **jouable** : le samedi, le
  propriétaire lance la démo, fait les gestes du palier, et voit le monde
  répondre.
- **Il avance sur les trois pistes**, d'une avancée que le joueur voit sur
  chacune. Un palier sans rien de neuf à l'écran n'en est pas un.
- **Il est atteint quand le propriétaire l'a joué et qu'il dit oui.** Une
  suite verte ne suffit pas : elle dit que c'est juste, pas que ça se joue.
- **Le samedi réoriente.** Ce que le propriétaire écrit après avoir joué
  commande le palier suivant ; les paliers écrits plus bas sont des
  propositions, pas un engagement.

## Les trois pistes

| piste | ce qui y avance | où | machine |
|---|---|---|---|
| **le monde** | la carte et la simulation : les règles, les gestes, l'IA | `jeu/sim/`, `jeu/data/` | le VPS |
| **la ville** | la ville 3D bâtie à la main, sur le kit du désert d'abord | `3d/unity/Assets/ForgeLocal3D/`, `3d/local3d/` | le PC |
| **l'interface** | ce qu'on voit et ce qu'on clique sur la carte : frontières, armées, panneaux, dans le style du cabinet | `3d/unity/Assets/Interface/`, le pont | le PC |

Un geste neuf traverse souvent deux pistes : la règle dans le monde, son
écran dans l'interface. Chaque lot reste dans sa piste ; le lot de l'écran
dit qu'il dépend de celui de la règle.

## La règle d'un lot

Un lot est **l'avancée d'une piste pour un palier**, sans plafond de taille.
C'est une issue, écrite par le CTO comme une fiche courte :

- **ce que je joue de plus** : le geste, et ce qu'il décide ;
- **ce que je vois samedi** : l'écran, en mots de joueur ;
- **la règle du monde** : comment ça marche, son niveau de fidélité, la
  section de `jeu/sim/MODELE.md` qui change ; « sans objet » pour un écran ;
- **les preuves** : des commandes qui peuvent échouer, et, pour un écran, la
  capture qu'on regarde ;
- **la piste**, la machine, qui le mène, et ce qu'il attend (« Dépend de »).

Celui qui conçoit le lot le construit : le chef de lot écrit son plan dans la
PR et le réalise ([docs/WORKFLOW.md](docs/WORKFLOW.md)).

## Les quatre premiers paliers

Chaque palier a trois lots, un par piste. Les lots du palier en cours sont
les issues de son jalon GitHub ; ils y font foi. Les paliers 2 à 4 sont
écrits ici pour que le CTO en tire les lots le samedi, d'après ce que le
propriétaire aura dit en jouant.

### Palier 1 — la première guerre (en cours)

Le joueur lève une armée, déclare la guerre, marche, assiège, et prend une
terre qui change de couleur sur la carte.

| piste | ce que je joue de plus | ce que je vois samedi |
|---|---|---|
| le monde | lever des hommes dans ses foyers, déclarer la guerre à une maison, faire marcher l'armée de lieu en lieu, assiéger une place, la prendre | les hommes levés manquent aux champs ; l'armée mange ce qu'elle porte et ce qu'elle prend ; la place affamée tombe et la terre change de maître ; les soldats rentrent ou ne reviennent pas ; l'IA fait les mêmes gestes |
| la ville | entrer dans sa capitale depuis la carte et y bâtir une caserne, qui donne le droit de lever (à confirmer en jouant) | la caserne dans la ville du désert, son prix en matériaux et en journées, et la levée qui s'ouvre sur la carte quand elle est bâtie |
| l'interface | suivre la guerre sur la carte | les frontières et les noms des pays ; les armées dessinées, avec leur nombre et leur route ; la terre prise qui change de couleur ; dans la ville, les textes de mise au point remplacés par le style du cabinet |

### Palier 2 — la paix et les alliés

La guerre se termine par un traité, et elle ne se fait plus seul.

| piste | ce que je joue de plus | ce que je vois samedi |
|---|---|---|
| le monde | proposer la paix et ses conditions (céder une terre, rendre une place), s'allier, appeler ses alliés | la maison d'en face pèse l'offre et répond ; l'IA déclare la guerre, s'allie et traite avec des raisons qu'on peut lire ; le jour du monde tient la vitesse la plus rapide |
| la ville | fermer sa capitale de murs, et la voir assiégée | l'enceinte et ses portes dans la ville du désert ; l'armée ennemie devant les murs pendant le siège |
| l'interface | lire ses voisins et le monde | l'écran des relations (qui est en guerre, allié, et pourquoi) ; le fil des nouvelles ; la pause et les cinq vitesses |

### Palier 3 — l'argent

Les pièces entrent au monde : on les frappe, on les lève, on les dépense.

| piste | ce que je joue de plus | ce que je vois samedi |
|---|---|---|
| le monde | frapper monnaie avec le métal de ses mines, lever l'impôt en pièces, payer la solde de l'armée | chaque maison a son trésor ; les pièces de 1400 sont déjà dans les bourses ; une armée qu'on ne paie plus se défait |
| la ville | poser le marché, tracer les parcelles le long des rues | le marché et ses étals dans la capitale ; la route du commerce qui en part vers la ville voisine |
| l'interface | suivre son argent, bâtir dans sa province depuis la carte | le trésor dans la barre du pays, avec ce qui entre et ce qui sort ; la carte des prix |

### Palier 4 — la dynastie

Le chef vieillit et meurt ; la partie continue avec son héritier.

| piste | ce que je joue de plus | ce que je vois samedi |
|---|---|---|
| le monde | marier ses enfants, attendre un héritier, jouer l'héritier à la mort du chef | on vieillit, on naît, on meurt ; la loi de succession désigne l'héritier et partage les terres ; une dynastie sans terre a perdu |
| la ville | poser le palais à la main | le palais dans la capitale, et le chef de la maison qui y marche |
| l'interface | lire sa famille | l'arbre de la dynastie ; à la mort du chef, la carte montre l'héritier et le partage |

## Les candidats, au-delà du palier 4

Une ligne chacun. Le samedi choisit, change ou remplace.

- **Le monde qui tient dix ans** : l'arrière-pays nourrit ses villes, les
  petits seigneurs jouent aussi, l'IA garde des raisons d'agir chaque année.
- **La bataille** : deux armées se rencontrent sur le terrain du monde, le
  joueur la mène ou la confie à un général, elle rend ses morts au monde ;
  l'artillerie ouvre une brèche, le siège se livre dans la ville bâtie.
- **La révolte** : elle naît de la faim et d'une occasion.
- **L'argent, suite** : le marché fait le prix, les marchands vont où c'est
  cher, les banquiers prêtent, on dévalue, on achète une terre.
- **La dynastie, suite** : les traits et l'éducation, changer sa loi de
  succession, les ambitions de l'héritier, les républiques et l'Église.
- **Le siècle** : sauvegarder et reprendre, déléguer ce qui se répète
  (intendants, vassaux, lois), la chronique et le score de la dynastie.
- **Le décor d'Occident et des Balkans** : des villes hors du désert, et la
  ville conquise qui s'ouvre avec le kit de sa terre.
- **La ville plus belle et plus vivante** : les matériaux, la lumière, les
  animations, le son, les carrefours, soixante images par seconde.
- **Le monde plus dur** : l'usure, la maladie, la foi, le crime, le feu.
- **Le jeu en anglais.**
