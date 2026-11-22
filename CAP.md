# CAP — la feuille de route

Ce que le jeu doit devenir : [docs/VISION.md](docs/VISION.md). Ce fichier dit
dans quel ordre on y va, et à quoi on reconnaît qu'on y est. Il se change en
mode direct. L'étape en cours vit sur GitHub : son issue épinglée, où le
propriétaire écrit le samedi, et son jalon, qui porte ses lots. Pour la
chaîne, une étape se mène comme un palier : son issue s'appelle « Palier n ».

## Le constat du 22 novembre 2026

Le propriétaire a joué le palier 1 et n'a su ni démarrer, ni jouer, ni ouvrir
la ville : « c'est incompréhensible, tout est brouillon ; on est très loin d'un
Europa sur la carte, très loin d'un Manor Lords dans la ville ». Ce que l'écran
montre lui donne raison, et dit pourquoi.

| ce qu'on voit | la cause |
|---|---|
| « Luxembourg » grand comme l'Allemagne, « Évreux » en Espagne, ni France ni Angleterre | la carte écrit les 30 maisons (dynasties) ; les 39 pays de `puissances-1400.json` (France, Bohême, Hongrie, Navarre…) existent mais ne sont ni dessinés ni nommés |
| des frontières en nids d'abeille | 596 cellules de 15 000 km² : une cellule vaut cinq à dix provinces d'Europa. Les 6 619 lieux, qu'on possède et qu'on assiège, n'ont pas de forme |
| une carte petite, posée de biais dans un cadre | elle tient la moitié de l'écran ; le reste est pris par des panneaux |
| des panneaux qui sont des pages de texte | aucun écran de départ, aucune icône, aucun chiffre mis en avant, des raisons de refus à la place de boutons, des touches à connaître |
| une douzaine de cubes sur des dunes pour 3 564 habitants | la ville dessine quelques maisons du kit, sans rue visible, sans habitant, sans chantier qui monte |
| une seule ville, au Sahara | qui choisit une autre maison que les Banou Mozni n'a pas de ville, et rien ne le dit |
| des armées de 27 000 hommes et des sièges partout dès 1400, un bourg pris qui passe de 332 à 32 habitants | l'IA et le siège ne sont réglés sur aucun ordre de grandeur de l'histoire |

Et une cause de méthode : chaque semaine ajoutait un geste sur trois pistes à
la fois, et un palier se disait fait quand un script réussissait le parcours.
On a élargi un jeu dont aucun écran n'était au niveau.

## Ce qui change dans la méthode

1. **La qualité avant l'étendue.** Aucune règle neuve (paix, argent,
   dynastie) tant que la carte et son interface ne sont pas au niveau. Le
   moteur existe ; c'est ce qu'on en voit qui manque.
2. **Un front à la fois sur le PC.** La carte et son interface d'abord : « la
   carte est le jeu » (décision 24). La ville vient ensuite, entière, au lieu
   d'un morceau par semaine. Pendant ce temps le VPS prépare les données et
   règle l'IA.
3. **Une étape se juge contre son modèle.** Chaque étape a des critères qu'on
   juge à l'œil, et sa preuve est une image du jeu posée à côté de la même vue
   d'Europa Universalis IV ou de Manor Lords.
4. **Une étape dure le temps qu'il faut.** Le samedi reste : le propriétaire
   joue ce qui est prêt et corrige la route. Mais une étape n'est finie que
   s'il a joué **seul, sans guide et sans touche à connaître**, et qu'il dit
   oui. Un parcours réussi par script prouve que le chemin existe, pas qu'on
   le trouve.
5. **Rien ne s'ajoute hors de l'interface.** Un geste neuf n'arrive qu'avec
   son bouton, son infobulle et son retour à l'écran.

## Les étapes

Les durées sont des ordres de grandeur, à corriger chaque samedi.

### Étape 0 — on s'y retrouve (1 semaine)

Arrêter l'élargissement et rendre le jeu d'aujourd'hui trouvable.

- Un écran de départ : « Choisissez un pays », puis « Commencer ».
- Un bouton « Entrer dans la ville », grisé avec sa raison quand le pays n'en
  a pas.
- Les gestes de la ville en boutons ; plus aucune touche obligatoire.
- La carte nomme les **pays** (France, Bohême, Navarre), la maison en second.

**Fini quand** le propriétaire lance le jeu, choisit un pays, lève une armée
et entre dans Biskra sans rien lire d'autre que l'écran.

### Étape 1 — la carte de 1400 qu'on reconnaît (3 à 4 semaines)

- **Les pays réels** : les 39 puissances dessinées chacune avec sa couleur, son
  nom couché sur son territoire, sa capitale ; le Saint-Empire comme un
  ensemble de princes, pas comme la terre d'une seule maison ; les vassaux
  rattachés à leur suzerain.
- **Des frontières à l'échelle d'une province** : donner une forme aux lieux
  (un découpage de chaque cellule en ses lieux, calé sur les côtes et les
  fleuves) et dessiner les frontières à ce grain, dix fois plus fin
  qu'aujourd'hui. `cell_id` reste la seule clé, le moteur ne change pas. Une
  étude de deux jours le confirme ou propose une nouvelle maille.
- **La carte en plein écran**, vue de dessus, qu'on fait glisser et qu'on
  zoome sous la souris, du continent jusqu'à la province.
- **Les modes de carte** : politique, relief, population, vivres, guerres.
- **Villes, fleuves, mers et régions** nommés et placés d'après l'atlas.

**Fini quand**, la carte du jeu posée à côté d'un atlas de 1400 et de la carte
politique d'Europa, le propriétaire reconnaît chaque grand pays, ne relève
aucune absurdité, et trouve la carte belle.

### Étape 2 — l'interface d'un Europa (4 à 5 semaines)

- **La barre du haut** : l'écu et le nom du pays, grain, hommes, les quatre
  jauges en icônes avec leur infobulle, la date, la pause et les cinq vitesses.
- **Le panneau de province**, ouvert d'un clic : qui la tient, ses gens, ce
  qu'elle produit, ses bâtiments, ses modificateurs, ce qu'on peut y faire.
- **Le panneau du pays** par onglets : la cour, l'économie, l'armée, la
  diplomatie.
- **La liste de droite** : ses armées, ses sièges, ses chantiers, en un clic.
- **Les alertes et le fil des nouvelles**, qui mènent au lieu.
- **Les armées sur la carte** : on les sélectionne, clic droit pour marcher,
  la route et les jours s'affichent ; le siège montre son avancement.
- **Partout** : un bouton impossible est grisé et dit pourquoi au survol ;
  plus aucune page de texte ; les nombres arrondis comme on les lit.
- **Les premiers pas** : trois objectifs affichés au départ, qui apprennent le
  jeu en le jouant.

**Fini quand** le propriétaire joue une heure, mène une guerre du début à la
fin, et n'a posé aucune question.

### Étape 3 — une guerre crédible (3 semaines, en partie menée sur le VPS pendant les étapes 1 et 2)

- L'IA règle ses levées et ses guerres sur l'histoire : des armées à
  l'échelle de 1400, des raisons de guerre lisibles, des années de paix.
- La paix : on propose, on cède une terre, la guerre se termine.
- Le siège affame et prend la place sans vider le pays.
- Le monde tient dix ans sans joueur en gardant une Europe vraisemblable.

**Fini quand** le propriétaire regarde dix ans en observateur et dit « c'est
plausible », puis gagne et perd une guerre.

### Étape 4 — la ville qu'on a envie de bâtir (8 à 10 semaines)

En trois temps, chacun jugé contre Manor Lords.

1. **Elle existe** (3 semaines) : la ville du monde dessinée en entier — ses
   maisons au nombre de ses foyers, ses rues, ses champs, son marché, son
   enceinte —, une caméra libre, une lumière et une végétation soignées.
2. **On la bâtit à la souris** (3 semaines) : la rue qu'on tire et qui se
   courbe, la parcelle qui se découpe seule le long de la rue, le bâtiment
   qu'on pose en fantôme, tourne et valide, le chantier qui monte étape par
   étape, le prix et le refus dits sur place.
3. **Elle vit** (3 semaines) : les habitants marchent, portent, travaillent ;
   les bêtes, les fumées, les saisons, le son ; un clic sur une maison dit qui
   y vit et ce qu'il mange.

**Fini quand** le propriétaire a envie d'y passer une heure, et qu'une image de
la ville ne fait pas honte à côté de Manor Lords.

### Étape 5 — le jeu s'étend

Une fois la carte, l'interface et la ville au niveau, les systèmes reviennent
un par un, chacun avec son écran : l'argent, la dynastie, les alliances, les
bâtiments de province, les événements à choix, la bataille.

## Ce qu'il faut savoir

- Europa Universalis IV et Manor Lords sont des années de travail. Au bout des
  étapes 0 à 4, soit cinq à six mois, on vise un **petit Europa crédible et
  une ville qu'on a envie de bâtir**, pas leur égal en contenu.
- La carte et la ville passent toutes deux par l'unique Unity du PC : elles
  se font l'une après l'autre, pas en même temps.

## Ce qui revient au propriétaire

| décision | ce que je recommande |
|---|---|
| l'ordre : la carte et son interface d'abord, la ville ensuite (change la décision 43, « trois pistes chaque semaine ») | oui |
| donner une forme aux lieux pour des frontières fines, ou refaire la maille | les lieux d'abord : le moteur ne bouge pas ; l'étude de l'étape 1 tranche |
| le décor de la ville : rester au désert, ou passer à un village d'Occident, où sont presque tous les pays et le modèle de Manor Lords | décider à la fin de l'étape 2 ; un kit d'Occident de qualité s'achète, c'est une dépense |
| que devient la proposition « la paix et les alliés » posée sur l'issue du palier 1 | elle est retirée ; la paix entre à l'étape 3 |

## La règle d'un lot

Un lot est **un système complet du jeu** — la carte politique, le panneau de
province, la rue qu'on tire —, sans plafond de taille : jamais une tranche qui
ne se joue pas seule. C'est une issue, écrite par le CTO comme une fiche
courte :

- **ce que je joue ou vois de plus**, en mots de joueur ;
- **le modèle** : l'écran d'Europa ou de Manor Lords auquel on le compare ;
- **la règle du monde** : comment ça marche, son niveau de fidélité, la
  section de `jeu/sim/MODELE.md` qui change ; « sans objet » pour un écran ;
- **les preuves** : des commandes qui peuvent échouer, et l'image qu'on
  regarde à côté du modèle ;
- la machine, qui le mène, et ce qu'il attend (« Dépend de »).

Celui qui conçoit le lot le construit : le chef de lot écrit son plan dans la
PR et le réalise ([docs/WORKFLOW.md](docs/WORKFLOW.md)).
