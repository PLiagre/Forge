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
- **Un palier est une seule grosse feature**, taillée pour remplir la
  semaine. La mesure : le palier 1, trois lots, s'est fait en un jour et demi
  (six heures de travail d'agent, un cinquième au plus de la limite
  hebdomadaire de l'abonnement), et la chaîne est restée sans travail le
  reste de la semaine. Un palier pèse donc trois à quatre fois le palier 1 :
  sept à neuf lots, et ce qui le borne est la limite hebdomadaire, pas le
  temps. La piste du monde en porte le plus : le VPS mène deux lots à la
  fois, le PC un seul Unity, et seulement allumé.
- **Il avance sur les trois pistes**, d'une avancée que le joueur voit sur
  chacune. Un palier sans rien de neuf à l'écran n'en est pas un.
- **Il se joue d'un trait.** Ses lots s'emboîtent : ce qu'un geste exige, un
  autre lot du palier le donne à toute maison de départ. Le dernier lot porte
  le scénario du palier, joué de bout en bout dans le build.
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

Un lot est **un système complet du jeu sur une piste** — la bataille, le
traité, l'écran de la diplomatie —, sans plafond de taille : jamais une
tranche qui ne se joue pas seule. Une piste en porte plusieurs dans un
palier, enchaînés par « Dépend de ». C'est une issue, écrite par le CTO comme
une fiche courte :

- **ce que je joue de plus** : le geste, et ce qu'il décide ;
- **ce que je vois samedi** : l'écran, en mots de joueur ;
- **la règle du monde** : comment ça marche, son niveau de fidélité, la
  section de `jeu/sim/MODELE.md` qui change ; « sans objet » pour un écran ;
- **les preuves** : des commandes qui peuvent échouer, et, pour un écran, la
  capture qu'on regarde ;
- **la piste**, la machine, qui le mène, et ce qu'il attend (« Dépend de »).

Celui qui conçoit le lot le construit : le chef de lot écrit son plan dans la
PR et le réalise ([docs/WORKFLOW.md](docs/WORKFLOW.md)).

## Les paliers

Les lots du palier en cours sont les issues de son jalon GitHub ; ils y font
foi. Les paliers suivants sont écrits ici pour que le CTO en tire les lots le
samedi, d'après ce que le propriétaire aura dit en jouant. Chacun est une
seule grosse feature, en sept à neuf lots ; le palier 2 en compte neuf.

### Palier 1 — la première guerre (livré, à jouer)

Le joueur lève une armée, déclare la guerre, marche, assiège, et prend une
terre qui change de couleur sur la carte. Trois lots, un par piste : la
guerre dans le monde, la caserne dans Biskra, la guerre lue sur la carte. Ce
qu'il a laissé, et que le palier 2 reprend : seul l'émirat du Zab peut lever
de la main du joueur, deux armées au même lieu ne se battent pas, et une
guerre ne finit jamais.

### Palier 2 — la guerre complète

Une guerre se gagne en bataille, se tient par les sièges, se finit par un
traité, et ne se fait plus seul. Toute maison de départ la joue de bout en
bout.

| piste | le lot | ce que je joue de plus | ce que je vois samedi |
|---|---|---|---|
| le monde | **la bataille** | chercher ou refuser le combat, choisir son terrain, mener en personne ou confier l'armée à un chef de guerre | deux armées ennemies au même lieu se battent plusieurs jours ; le nombre, les vivres, le terrain et le chef décident ; les morts manquent aux champs, les fuyards rentrent ; une armée de secours lève un siège ; le chef d'une maison peut y mourir |
| le monde | **le siège et l'occupation** | donner l'assaut ou attendre la faim, tenir une place prise avec une garnison, ravager une terre | les murs et le grenier décident de combien de temps une place tient ; l'assaut coûte des hommes ; une terre prise est occupée, pas encore à moi : c'est le traité qui la donne |
| le monde | **la paix** | dire pourquoi je fais la guerre (la terre que je réclame), proposer un traité et ses conditions (céder une terre, rendre une place, un tribut de grain, la paix blanche) | un score de guerre né des places, des batailles et de la durée ; la maison d'en face pèse l'offre et répond avec ses raisons ; la lassitude entame la Concorde ; une trêve suit le traité ; une guerre que personne ne gagne finit d'épuisement |
| le monde | **les alliés et la pyramide** | s'allier en dépensant du Sceau, appeler ses alliés, répondre à l'appel de son suzerain ou le refuser | suzerain, vassaux et alliés entrent dans la guerre ; refuser coûte du Renom ; l'IA s'allie contre un voisin qui grossit et déclare la guerre avec des raisons qu'on peut lire ; Constantinople ne tombe plus la première année |
| le monde | **le jour tient la vitesse la plus rapide** | jouer la guerre à la cinquième vitesse | dix jours par seconde, armées et batailles comprises ; le budget du jour est gardé avant la fusion, pas après |
| la ville | **la ville fortifiée et assiégée** | fermer sa capitale de murs, de portes et de tours tracés à la main, et y poster sa garnison | l'enceinte du kit du désert dans Biskra et son prix ; pendant le siège, l'armée ennemie campée devant les murs, les portes closes, les étals qui se vident ; les murs comptent dans la tenue de la place |
| l'interface | **la guerre pour toute maison** | bâtir la caserne depuis la carte, lever dans tous ses lieux | toute maison de départ fait la guerre, sans passer par une ville en 3D ; la carte se colore par pays ou par maison |
| l'interface | **la bataille et le siège sur la carte** | suivre une bataille, ordonner l'assaut, poster une garnison | la bataille et le siège se lisent sur la carte, avec leurs pertes jour par jour ; la terre occupée se distingue de la terre acquise ; le journal de la guerre |
| l'interface | **la diplomatie et les nouvelles** | composer un traité et voir ce que l'autre en pense avant de l'envoyer, s'allier, appeler, régler le temps | l'écran des relations (qui est en guerre, allié, vassal, et pourquoi) ; le traité qui se compose ; le fil des nouvelles, dont chaque ligne mène au lieu ; la pause et les cinq vitesses ; **le scénario du palier joué d'un trait dans le build** |

### Palier 3 — l'argent et le commerce

Les pièces entrent au monde : on les frappe, on les lève, on les dépense, on
les prête, et les prix naissent du marché.

| piste | ce que je joue de plus | ce que je vois samedi |
|---|---|---|
| le monde | frapper monnaie avec le métal de ses mines, lever l'impôt en pièces, payer la solde, emprunter, dévaluer, acheter une terre ; commercer : le marché fait le prix, lieu par lieu, et les marchands vont où c'est cher | chaque maison a son trésor, et les pièces de 1400 sont déjà dans les bourses ; une armée qu'on ne paie plus se défait ; un prix monte où le grain manque ; une dette pèse des années ; l'IA décide sur les prix |
| la ville | poser le marché et ses étals, tracer les parcelles le long des rues, bâtir les ateliers | le marché de la capitale et ce qui s'y vend ; la route du commerce qui en part vers la ville voisine ; les artisans à l'ouvrage |
| l'interface | suivre son argent, bâtir dans sa province depuis la carte | le trésor dans la barre du pays, avec ce qui entre et ce qui sort ; la carte des prix et des routes marchandes ; le livre de comptes ; ses dettes et leurs échéances |

### Palier 4 — la dynastie et la cour

Le chef vieillit et meurt ; la partie continue avec son héritier, et les
jauges du pays naissent de personnes.

| piste | ce que je joue de plus | ce que je vois samedi |
|---|---|---|
| le monde | marier ses enfants, éduquer un héritier, nommer son conseil, changer sa loi de succession, jouer l'héritier à la mort du chef | on vieillit, on naît, on meurt ; les traits et l'éducation font les compétences, et le conseil remplit la Plume, le Sceau et l'Épée ; la loi désigne l'héritier et partage les terres ; un cadet ambitieux complote ; une dynastie sans terre a perdu |
| la ville | poser le palais à la main, et y tenir sa cour | le palais dans la capitale ; le chef de la maison et les siens qui y marchent |
| l'interface | lire sa famille et sa cour | l'arbre de la dynastie ; le conseil et ce que chacun apporte ; à la mort du chef, la carte montre l'héritier et le partage ; la chronique de la dynastie |

## Les candidats, au-delà du palier 4

Une ligne chacun. Le samedi choisit, change ou remplace.

- **Le monde qui tient dix ans** : l'arrière-pays nourrit ses villes, les
  petits seigneurs jouent aussi, l'IA garde des raisons d'agir chaque année.
- **La bataille menée** : la regarder et la mener en 3D sur le moteur du
  monde, l'artillerie qui ouvre une brèche, le siège livré dans la ville
  bâtie.
- **La révolte** : elle naît de la faim et d'une occasion.
- **Le siècle** : sauvegarder et reprendre, déléguer ce qui se répète
  (intendants, vassaux, lois), les ambitions de l'héritier et le score de la
  dynastie, les républiques et l'Église.
- **Le décor d'Occident et des Balkans** : des villes hors du désert, et la
  ville conquise qui s'ouvre avec le kit de sa terre.
- **La ville plus belle et plus vivante** : les matériaux, la lumière, les
  animations, le son, les carrefours, soixante images par seconde.
- **Le monde plus dur** : l'usure, la maladie, la foi, le crime, le feu.
- **Le jeu en anglais.**
