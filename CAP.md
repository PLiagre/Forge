# CAP — des paliers jouables d'une semaine

Ce que le jeu doit devenir : [docs/VISION.md](docs/VISION.md). Ce fichier dit
dans quel ordre on y va. Il se change en mode direct, ou par le CTO le samedi,
dans la PR du palier que le propriétaire valide.

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

## Le palier en cours : palier 1 — la première guerre

Le joueur lève une armée, déclare la guerre, marche, assiège, et prend une
terre qui change de couleur sur la carte.

| piste | ce que je joue de plus | ce que je vois samedi |
|---|---|---|
| le monde | lever une armée, déclarer la guerre, marcher, assiéger, prendre une terre | la terre prise change de maître, et l'IA fait les mêmes gestes |
| la ville | entrer dans sa capitale depuis la carte et y bâtir une caserne, qui donne le droit de lever (à confirmer en jouant) | la caserne dans la ville du désert, et la levée qui s'ouvre |
| l'interface | suivre la guerre sur la carte | les frontières et les noms des pays, les armées dessinées, les textes de la ville dans le style du cabinet |

Ses lots sont les issues du jalon GitHub « Palier 1 » ; ils y font foi.

## Les paliers candidats

Une ligne chacun. Le samedi choisit, change ou remplace.

- **La paix et les alliés** : traiter la paix, s'allier, appeler ses alliés ;
  les murs et le siège vus de la ville ; l'écran des relations.
- **L'argent** : un trésor, l'impôt en pièces, la solde de l'armée ; le marché
  dans la ville ; le trésor dans la barre du pays.
- **La dynastie** : marier, hériter, jouer l'héritier ; le palais dans la
  ville ; l'arbre de la famille.
- **Le monde qui tient dix ans** : l'arrière-pays nourrit ses villes ; la
  ville qui grandit seule entre deux visites ; le fil des nouvelles.
- **La bataille sur la carte** : deux armées se rencontrent, la bataille dure
  des jours et rend ses morts au monde.
- **Un but** : les ambitions de l'héritier et le score de la dynastie.
- **Le décor d'Occident** : une seconde ville, hors du désert.
