# CAP — la feuille de route, en jours

Ce que le jeu doit devenir : [docs/VISION.md](docs/VISION.md). Ce fichier dit
dans quel ordre on y va, en combien de jours, et à quoi on reconnaît qu'on y
est. Il se change en mode direct. L'étape en cours vit sur GitHub : son issue
épinglée, où le propriétaire écrit quand il a joué, et son jalon, qui porte
ses lots. Pour la chaîne, une étape se mène comme un palier : son issue
s'appelle « Palier n ».

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

Et une cause de méthode : on ajoutait un geste sur trois pistes à la fois, et
un palier se disait fait quand un script réussissait le parcours. On a élargi
un jeu dont aucun écran n'était au niveau.

## Où partait le temps

Mesuré sur le palier 1 (lots #1108, #1109, #1110), dans les marques des PR et
les passages du PC. Trois lots, 25 heures de la prise du premier à la fusion
du dernier : **6 heures de travail d'agent, 19 heures d'attente**.

| l'attente | combien | ce qui la retire |
|---|---|---|
| le PC éteint la nuit, un passage resté en file | 11 h 50 | le PC allumé tant qu'une étape tourne (au propriétaire) |
| la limite de cinq heures de l'abonnement, atteinte une fois | 2 h | rien : c'est la borne qui reste (voir plus bas) |
| un passage du PC tombé, renvoyé une heure plus tard, deux fois | 2 h | le renvoi au bout d'un quart d'heure |
| des appels coupés par leur délai sans rien rendre (une étape, deux relectures) | 2 h | le relecteur sait son délai et rend son verdict avant |
| le tour du pilote entre deux pas, la CI | 1 h 15 | laissé tel quel |

Et tout s'est fait à la file : le second lot Unity (#1109, 1 h 50 de travail)
n'a commencé qu'à la fusion du premier, dix-neuf heures après son envoi, parce
que le PC n'avait qu'un chantier. Puis quatre jours sans aucun travail : le
palier était vidé, et rien ne se rouvrait avant le samedi. Les trois lots
auraient tenu en six heures et demie l'un après l'autre, et en quatre heures
et demie avec les deux lots Unity menés ensemble.

Le mode direct, lui, ne connaît pas ces attentes : la carte en relief (six
PR, 4 300 lignes) s'est faite en 29 heures, nuit comprise, chaque PR fusionnée
trois minutes après son ouverture.

## Le rythme

1. **Les étapes se comptent en jours.** L'étape 0 tient en un jour, deux au
   plus. Un lot demande deux à quatre heures de travail d'agent, plan, CI et
   relecture compris ; une étape dure donc son plus long enchaînement de lots
   qui s'attendent, pas la somme de ses lots.
2. **Une étape s'enchaîne dès que la précédente est jouée**, quel que soit le
   jour. Dès qu'une étape n'a plus de lot ouvert, le PC en fige un build et
   **le testeur le joue** : par l'écran seul, sans guide, comme un joueur
   averti qui le découvre. Son rapport, puis la note de démo du CTO, arrivent
   sur l'issue de l'étape ; le CTO propose la suite, et elle s'ouvre sur le
   verdict du testeur : l'étape suivante s'il la dit tenue, ce qui la corrige
   sinon. Le propriétaire joue quand il veut.
3. **Tout part en parallèle**, sauf ce qui dépend vraiment d'un autre lot. Le
   VPS mène deux lots à la fois, le PC deux lots Unity, chacun dans son
   chantier. Deux lots menés ensemble ne touchent ni le même écran, ni la même
   scène, ni les mêmes données ; ce qui touche les mêmes fichiers va dans le
   même lot, ou se suit.
4. **Les retouches vues en jouant se font en mode direct, dans la journée** :
   un bouton qui ne répond pas, un texte faux, un réglage. Un système complet
   reste un lot de la chaîne.
5. **Le critère de fin ne s'adoucit pas : c'est celui qui le juge en premier
   qui change.** Une étape est tenue quand elle a été jouée **seul, sans
   guide et sans touche à connaître** : par le testeur d'abord, qui ne
   connaît que sa promesse et l'écran, jamais le code. Avoir fini par trouver
   ne compte pas : un objectif qu'il ne trouve pas en cinq essais est bloqué,
   un défaut qui arrête ou trompe un joueur est bloquant, et l'étape n'est
   alors pas tenue. Le CTO repropose d'abord ce qui la corrige, et ce tour de
   correction, qui compte un à deux jours, part sans attendre. Après cinq
   « non tenue » de suite, la chaîne n'ouvre plus rien seule : elle appelle le
   propriétaire.
6. **Le propriétaire garde le dernier mot.** Il joue quand il veut. Ce qu'il
   écrit sur l'issue de l'étape passe devant le verdict du testeur, à tout
   moment : son « non » fait reproposer d'abord ce qui corrige, et dès qu'il
   a parlé, rien ne s'y ouvre plus sans son « oui ». Le testeur juge ce qu'un
   joueur trouve seul et ce qui est faux ou incohérent ; le goût (« la carte
   est belle », « on est au niveau d'Europa ») reste celui du propriétaire.
   Une ligne d'`atelier.toml` (`[testeur] ouvre = false`) rend son « oui » de
   nouveau nécessaire à chaque étape.

Ce qui ne change pas : la qualité avant l'étendue, la carte et son interface
avant la ville, une étape jugée à l'œil contre Europa Universalis IV ou Manor
Lords, rien de neuf hors de l'interface (décisions 51 à 54).

## Ce qui borne encore la vitesse

| la borne | sa mesure | ce qui la lève |
|---|---|---|
| **l'abonnement** | un lot prend 35 à 50 % d'une fenêtre de cinq heures et 3 à 6 % de la limite de la semaine : deux lots menés sans arrêt remplissent une fenêtre, et la semaine porte une vingtaine de lots, une quinzaine avec des sessions directes à côté | un abonnement plus large : au propriétaire |
| **le PC** | il ne travaille qu'allumé ; ses deux runners mènent deux lots Unity ensemble, pas plus | le laisser allumé pendant une étape : au propriétaire |
| **l'écran du PC** | le jeu n'a d'écran que dans la session Windows ouverte du propriétaire : le testeur n'y joue que lorsqu'il a quitté clavier et souris depuis dix minutes, et lui rend la main dès qu'il y touche. Il attend six heures au plus ; après, la note de démo part sans verdict, et le « oui » du propriétaire redevient nécessaire | laisser la session ouverte et non verrouillée quand on s'éloigne : au propriétaire |
| **le jugement du testeur** | prouvé sur une seule étape (l'étape 0, où il a retrouvé les critiques du propriétaire) ; un « tenue » complaisant ouvrirait une étape sur une base qui ne l'est pas, un « non tenue » à tort coûterait un tour de correction d'un à deux jours | le « non » du propriétaire, à tout moment ; comparer son verdict au sien sur l'étape 1 ; `[testeur] ouvre = false` |
| **l'art de la ville** | la chaîne écrit du code, pas des maisons : la ville ne vaudra pas Manor Lords avec le seul kit du désert | un kit de village d'Occident, acheté : au propriétaire, à la fin de l'étape 2 |
| le VPS | deux processeurs : deux lots au plus | une machine plus grosse ; inutile tant que l'abonnement borne avant lui |

## Les étapes

Les jours sont des jours de chaîne, PC allumé. Le calendrier entier tient en
**trois à quatre semaines** si chaque étape passe au premier ou au second
essai : trente-six lots, une quarantaine avec les corrections, soit deux à
trois semaines de l'abonnement.
Les lots de l'étape en cours font foi sur GitHub ; ceux des étapes suivantes
sont préparés dans [docs/etapes/](docs/etapes/), et le CTO les reprend quand
il propose l'étape. Chaque « fini quand » ci-dessous est d'abord joué par le
testeur ; ce qui y tient du goût (« trouve la carte belle », « a envie d'y
passer une heure ») reste jugé par le propriétaire, quand il joue.

| étape | jours | lots | ce qui part en parallèle |
|---|---|---|---|
| 0 — on s'y retrouve | 1, 2 au plus | 3 | le monde (VPS) et la ville (PC) ensemble ; l'accueil dès que les pays ont leur nom |
| 1 — la carte de 1400 qu'on reconnaît | 4 | 9 | deux files sur le VPS (les frontières ; la forme des lieux), deux sur le PC (le plein écran ; le dessin) |
| 2 — l'interface d'un Europa | 5 | 8 | deux écrans à la fois sur le PC, jamais deux lots sur le même panneau |
| 3 — une guerre crédible | 3, pendant les étapes 1 et 2 | 5 | sur le VPS, quand il n'a pas de lot de l'étape en cours ; ses écrans à la fin de l'étape 2 |
| 4 — la ville qu'on a envie de bâtir | 8 | 11 | trois temps qui se suivent ; dans chacun, deux lots Unity à la fois |
| 5 — le jeu s'étend | un système tous les 2 à 3 jours | — | la règle sur le VPS pendant que son écran se fait sur le PC |

### Étape 0 — on s'y retrouve (1 jour, 2 au plus)

Arrêter l'élargissement et rendre le jeu d'aujourd'hui trouvable.

| lot | machine | attend | ce qu'il livre |
|---|---|---|---|
| A. Chaque pays porte son nom | VPS | — | le service donne à chaque terre son pays (France, Bohême, Navarre), la maison en second, et dit pour chaque départ si sa capitale est bâtie |
| B. L'accueil et le bouton de la ville | PC | A | « Choisissez votre pays », la fiche du pays, « Commencer », les trois premiers gestes ; « Entrer dans la ville », grisé avec sa raison quand le pays n'en a pas |
| C. Les outils de la ville en boutons | PC | — | Rue, Parcelle, Caserne, Valider, Annuler, « Retour à la carte » ; plus aucune touche obligatoire |

A et C partent ensemble ; B part quand A est fusionné. Le plus long
enchaînement est A puis B : cinq à six heures.

**Fini quand** le propriétaire lance le jeu, choisit un pays, lève une armée
et entre dans Biskra sans rien lire d'autre que l'écran.

### Étape 1 — la carte de 1400 qu'on reconnaît (4 jours)

| lot | machine | attend | ce qu'il livre |
|---|---|---|---|
| 1. Les frontières de 1400 : France, Îles, Ibérie, Italie | VPS | — | chaque cellule au pays qui la tenait, d'après des sources citées |
| 2. Les frontières de 1400 : l'Empire, le Nord et l'Est | VPS | 1 | le Saint-Empire rendu à ses princes |
| 3. Les frontières de 1400 : Balkans, Orient, Maghreb | VPS | 2 | la fin de la table ; les vassaux rattachés à leur suzerain |
| 4. La forme des lieux | VPS | — | chaque cellule découpée en ses lieux, calée sur les côtes et les fleuves ; `cell_id` reste la seule clé |
| 5. Les noms de l'atlas | VPS | — | villes, fleuves, mers et régions, nommés et placés |
| 6. La carte en plein écran | PC | — | vue de dessus, qu'on glisse et qu'on zoome sous la souris, du continent à la province |
| 7. Les frontières au grain du lieu | PC | 4 | dessinées dix fois plus fin qu'aujourd'hui |
| 8. Les pays et leurs noms sur la carte | PC | 3, 7 | les pays réels, chacun sa couleur, son nom couché, sa capitale ; les noms de l'atlas |
| 9. Les modes de carte, et la carte à côté de l'atlas | PC | 6, 8 | politique, relief, population, vivres, guerres ; la preuve de l'étape |

Jour 1 : 1 et 4 sur le VPS, puis 2 et 5 ; 6 sur le PC, et 7 dès que les
lieux ont leur forme. Jour 2 : 3 sur le VPS ; la fin de 6 et de 7. Jour 3 :
8. Jour 4 : 9, puis le build figé. Le lot 4 commence par sa preuve sur vingt
cellules : si le découpage ne donne pas des provinces qu'on reconnaît, le CTO
propose une autre maille avant d'aller plus loin.

**Fini quand**, la carte du jeu posée à côté d'un atlas de 1400 et de la carte
politique d'Europa, le propriétaire reconnaît chaque grand pays, ne relève
aucune absurdité, et trouve la carte belle.

### Étape 2 — l'interface d'un Europa (5 jours)

Huit lots sur le PC, deux à la fois, un par écran :

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
- **Les premiers pas** : trois objectifs affichés au départ, qui apprennent le
  jeu en le jouant.
- **Le passage de finition**, en dernier : un bouton impossible est grisé et
  dit pourquoi au survol ; plus aucune page de texte ; les nombres arrondis
  comme on les lit ; une heure de jeu d'un trait dans le build.

**Fini quand** le propriétaire joue une heure, mène une guerre du début à la
fin, et n'a posé aucune question.

### Étape 3 — une guerre crédible (3 jours, menés sur le VPS pendant les étapes 1 et 2)

Cinq lots du monde, sans écran neuf avant la fin de l'étape 2 :

- L'IA règle ses levées et ses guerres sur l'histoire : des armées à
  l'échelle de 1400, des raisons de guerre lisibles, des années de paix.
- Le siège affame et prend la place sans vider le pays.
- La paix : on propose, on cède une terre, la guerre se termine.
- Le monde tient dix ans sans joueur en gardant une Europe vraisemblable
  (la preuve longue tourne la nuit).
- Les écrans de la paix et du siège, sur le PC, quand l'étape 2 est jouée.

**Fini quand** le propriétaire regarde dix ans en observateur et dit « c'est
plausible », puis gagne et perd une guerre.

### Étape 4 — la ville qu'on a envie de bâtir (8 jours)

En trois temps, chacun joué et jugé contre Manor Lords avant le suivant.

1. **Elle existe** (3 jours, 4 lots) : la ville du monde dessinée en entier —
   ses maisons au nombre de ses foyers, ses rues, ses champs, son marché, son
   enceinte —, une caméra libre, une lumière et une végétation soignées.
2. **On la bâtit à la souris** (3 jours, 4 lots) : la rue qu'on tire et qui se
   courbe, la parcelle qui se découpe seule le long de la rue, le bâtiment
   qu'on pose en fantôme, tourne et valide, le chantier qui monte étape par
   étape, le prix et le refus dits sur place.
3. **Elle vit** (2 jours, 3 lots) : les habitants marchent, portent,
   travaillent ; les bêtes, les fumées, les saisons, le son ; un clic sur une
   maison dit qui y vit et ce qu'il mange.

**Fini quand** le propriétaire a envie d'y passer une heure, et qu'une image de
la ville ne fait pas honte à côté de Manor Lords.

### Étape 5 — le jeu s'étend

Une fois la carte, l'interface et la ville au niveau, les systèmes reviennent
un par un, chacun avec son écran, un tous les deux à trois jours : l'argent,
la dynastie, les alliances, les bâtiments de province, les événements à
choix, la bataille.

## Ce qu'il faut savoir

- Europa Universalis IV et Manor Lords sont des années de travail. Au bout des
  étapes 0 à 4 on vise un **petit Europa crédible et une ville qu'on a envie
  de bâtir**, pas leur égal en contenu.
- Les jours comptent le travail de la chaîne, pas le jugement. Une étape
  refusée ne se rattrape pas en allant plus vite : elle se corrige, puis se
  rejoue.
- Aucune date n'est promise au-delà de l'étape suivante : le calendrier se
  corrige à chaque étape jouée, d'après ce qu'elle a vraiment pris.

## Ce qui revient au propriétaire

| décision | ce qu'elle coûte | ce qu'elle fait gagner | ce que je recommande |
|---|---|---|---|
| laisser le PC allumé tant qu'une étape tourne | l'électricité d'une nuit | douze heures sur vingt-quatre : la nuit du palier 1 a coûté 11 h 50 à elle seule | oui, dès l'étape 0 |
| laisser sa session Windows ouverte et non verrouillée quand il s'éloigne, quand une étape se termine | le jeu s'ouvre sur son bureau pendant son absence, et se ferme dès qu'il touche la souris | le testeur joue le build sans lui ; sinon la note de démo part sans verdict au bout de six heures | oui |
| un abonnement plus large | le prix du palier au-dessus de l'abonnement Max en place, ou d'un second abonnement | la seule borne qui reste une fois le PC réglé : plus de deux lots menés sans arrêt, plus de vingt par semaine | attendre la mesure de l'étape 1 : si le journal du matin montre la limite de la semaine au-dessus de 70 % avant le cinquième jour, oui |
| le décor de la ville : rester au désert, ou passer à un village d'Occident | un kit de l'Asset Store | la ville jugée contre Manor Lords, que le désert ne donnera pas | décider à la fin de l'étape 2, comme prévu (décision 54) |
| donner une forme aux lieux, ou refaire la maille | — | — | les lieux d'abord : le moteur ne bouge pas ; la preuve du lot 4 de l'étape 1 tranche |

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
- la machine, qui le mène, **les dossiers qu'il touche**, et ce qu'il attend
  (« Dépend de »). Un lot n'attend que ce dont il a vraiment besoin : le
  pilote prend tout ce qui est prêt, deux lots par machine.

Celui qui conçoit le lot le construit : le chef de lot écrit son plan dans la
PR et le réalise ([docs/WORKFLOW.md](docs/WORKFLOW.md)).
