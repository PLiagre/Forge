# Feuille de route

Chaque jalon a une preuve qui peut échouer. Un jalon n'est « fait » que si sa
mesure est verte dans le joueur Windows compilé, sur la machine de référence.

| # | jalon | la preuve | état |
|---|---|---|---|
| 1 | **La foule** — 10 000 hommes en formation marchent dans une vallée, à 60 images/s | `outils/atelier.ps1 mesurer` : 10 000 soldats présents, déplacés, visibles à l'écran, 95e centile < 16,67 ms sur quatre vues ; la contre-épreuve (un soldat retiré) doit échouer | **fait** — 95e centile au plus 1,57 ms ; 30 000 hommes : 2,57 ms |
| 2 | **Les ordres** — sélectionner, déplacer, faire pivoter, élargir ou resserrer un régiment | `atelier.ps1 mesurer` : un régiment atteint sa place sur 16 puis 40 files (front à 10 % près, 95 % des hommes à leur place) ; un régiment envoyé à travers un autre ne passe pas (< 5 %) et aucun corps n'en recouvre un autre (> 0,6 m) ; sans les corps, l'essai doit échouer | **fait** — 16,7 m pour 16,5 ; 43,0 m pour 42,9 en 14 s ; 0 % passés ; 0,80 m |
| 3 | **Le corps** — soldat modulaire Blender (armure, arme, couleurs) et animation cuite en textures | `atelier.ps1 mesurer` : 10 000 soldats animés tiennent le budget ; deux phases de marche, positions figées, changent l'image ; sans l'animation, cette preuve doit échouer | **fait** — 95e centile au plus 2,39 ms ; l'animation change 6,6 % de l'image, 0,00 % sans elle ; 30 000 hommes : 5,28 ms |
| 4 | **La mêlée** — poussée, coups, blessures, fatigue, deux régiments qui se battent | `atelier.ps1 mesurer` : trois duels de même front, 10 contre 5 rangs, 5 contre 10 et 10 contre 10. Le plus profond fait reculer la ligne d'au moins 3 m, dans les deux sens ; les régiments ne se traversent pas. Sans la poussée des rangs arrière, l'essai doit échouer. La mesure de performance porte sur une mêlée engagée sur tout le front | **fait** — +9,9 m et −9,4 m (témoin +0,5 m) ; sans poussée : +1,3 m et −0,2 m ; mêlée de 954 hommes au contact en 2,23 ms |
| 5 | **La peur** — le moral naît des blessés autour de soi, des flancs, de la fatigue ; fuite et ralliement | `atelier.ps1 mesurer` : vingt épreuves à armes égales, avec 20 000 hommes. Dans chacune, un régiment est attaqué de front, et un second régiment ennemi l'attaque de flanc (10 fois) ou reste en réserve derrière le premier (10 fois). De flanc, la part d'hommes en fuite au plus fort doit dépasser de 10 points celle de la réserve, les ruptures doivent être plus nombreuses, et des fuyards doivent revenir. Sans la peur, l'essai doit échouer | **fait** — 6 ruptures sur 10 contre 1 ; 51 % de fuyards au plus fort contre 19 % ; 1 564 ralliements |
| 6 | **Les tireurs** — flèches et carreaux simulés en masse, trajectoires, boucliers, pavois | `atelier.ps1 mesurer`, avec 20 000 hommes : une salve de masse à 220 m met plus de 2 000 carreaux en vol, dans le budget ; en tir tendu à 100 m, les régiments à pavois sont touchés au plus 60 % autant que les autres. Sans pavois, l'essai doit échouer | **fait** — 2 909 carreaux en vol, 95e centile 2,68 ms ; pavois : 7 % des touches (42 contre 581), 0 mort contre 101 |
| 7 | **La cavalerie** — masse, élan, charge, chevaux modélisés | `atelier.ps1 mesurer`, avec 20 000 hommes : vingt charges de 80 hommes d'armes à 150 m. Sur des arbalétriers sans pavois (10 fois), les cavaliers entrent d'au moins 3 m au-delà du premier rang debout, et le rang rompt au moins 7 fois. Sur des piquiers arrêtés (10 fois), ils entrent de moins d'un rang (1,1 m) ; la cavalerie rompt au moins 7 fois et perd plus d'hommes qu'elle n'en tue ; les piquiers rompent au plus 2 fois. Sans la masse des chevaux, le rang non préparé ne doit plus être brisé ; sans les piques, la charge ne doit plus se briser | **fait** — rang non préparé : 69,6 m, 10 ruptures sur 10 ; piques : 0,5 m, cavalerie rompue 10 fois sur 10, 226 cavaliers tués contre 36 piquiers, aucune rupture de piquiers |
| 8 | **La carte** — vallée dédiée et citadelle recomposée avec le kit de Forge | les parcours de la vallée, du pont et des rues sont franchissables | |
| 9 | **Le siège** — échelles, béliers, tours, trébuchets, bombardes ; murs pré-fracturés | une brèche ouverte par l'artillerie est franchissable par l'infanterie | |
| 10 | **Le feu et la ville** — incendie des maisons, effondrement, combats de rue | une maison brûlée perd ses appuis et s'effondre | |
| 11 | **L'IA** — attaque et défense de la citadelle, bataille de vallée | l'IA gagne contre elle-même en défense une fois sur deux, à forces égales | |
| 12 | **Le contrat Forge** — entrée (armées) et sortie (morts, blessés, fuyards) en JSON | une bataille relue donne les mêmes pertes que celles qu'elle a écrites | |

## Journal

- **24 septembre 2026** — vision fixée, projet créé.
- **24 septembre 2026** — jalon 1 fait. Le joueur Windows fait marcher 10 000 silhouettes (128 triangles) en 40 régiments dans une vallée de 2,4 km, avec les ombres, le brouillard et un anticrénelage 4×. 95e centile : 1,28 / 1,57 / 1,53 / 1,23 ms sur les quatre vues. La contre-épreuve échoue comme prévu (9 999 / 10 000). À 30 000 hommes, le 95e centile vaut 2,57 ms au pire : la marge est large pour les corps animés, la mêlée et les projectiles. Limite connue : les soldats n'ont pas de membres. Le pas est une simple élévation procédurale, en attendant le jalon 3.
- **24 septembre 2026** — jalon 2 fait. On sélectionne à la boîte ou avec Maj. Un clic droit fait aller le groupe en gardant sa disposition ; un clic droit glissé trace la ligne de bataille, dont la longueur fixe le front et le sens fixe la face ; Retour arrière commande la halte. Les hommes ont un corps de 0,8 m.
  - **Les appuis :** un homme campé cède moins qu'un homme en marche face à un autre régiment, et s'efface devant un camarade qui rejoint sa place.
  - **Le reclassement :** à chaque ordre, les hommes reprennent un numéro dans l'ordre où ils se tiennent, si bien que le front s'élargit sans que personne ne traverse le régiment.
  - **L'attente :** le régiment attend ses hommes. Un bloc large pivote plus lentement, parce que ses ailes doivent courir.
  - **Ce que les essais ont appris :** la première version laissait un régiment en traverser un autre par les couloirs entre les files, sans qu'aucun corps ne se recouvre. Avec les appuis, les hommes restaient ensuite bloqués au reclassement, par un équilibre de forces entre camarades. Le diagnostic est resté dans le rapport d'essai (`trainards`).
  - **Performance :** avec les corps, le 95e centile ne dépasse pas 1,53 ms.
  - **Limite :** le régiment arrêté contre un autre attend en bon ordre ; la poussée des rangs arrière vers l'avant reste à faire (jalon 4).
- **24 septembre 2026** — jalon 3 fait. `fabrique/soldats.py` construit dans Blender trois soldats de 1400 sur un vrai squelette de 11 os : le **piquier** (chapel de fer, pique de 4,6 m portée droite), le **hallebardier** (bassinet, plastron, hallebarde) et l'**arbalétrier** (calotte de cuir, arbalète, carquois). Ils font de 472 à 498 triangles, et leur tunique prend la couleur du camp.
  - **La cuisson :** le script pose le squelette image par image, pour un cycle de marche de 24 images (deux pas, 1,5 m) et un repos de 24 images (respiration, regard, report du poids). Chaque sommet de chaque image est cuit en demi-précision, puis Unity en fait une texture d'animation.
  - **Le shader :** `Guerre/Soldat` rejoue l'animation sur le GPU, compatible Entities Graphics, avec les ombres. L'état d'animation est propre à chaque homme ; le pas suit le chemin réellement parcouru, si bien qu'un homme bousculé ne marche pas sur place ; le passage de la marche au repos suit la vitesse. Au premier rang, piques et hallebardes alternent ; les arbalétriers tiennent la seconde ligne.
  - **Les sens des os** (vers où une rotation positive porte la jambe) sont mesurés par le script, pas supposés. Des planches de contrôle sont rendues par Workbench dans `fabrique/sorties/`.
  - **Limites :** pas de niveaux de détail (le budget n'en a pas encore besoin) ; pas encore de course ni de coups (jalon 4) ; les visages sont lisses ; l'arme se tient d'une seule main et ne s'abaisse pas.
- **24 septembre 2026** — jalon 4 fait. La mêlée est physique, et la victoire de la profondeur n'est écrite nulle part.
  - **Les corps :** chaque homme pèse 80 kg et pousse avec une courbe de muscle, fort à l'arrêt et faible en vitesse. Les corps sont des ressorts amortis avec frottement ; la presse transmet l'effort de rang en rang.
  - **Au contact :** les rangs se serrent (0,80 m, épaule contre épaule ; 0,90 m entre les rangs). On tient sa file coude à coude. Qui charge pousse sur ce qu'il a devant lui ; sans rien devant, il ne dépasse pas sa place. L'ancre suit les hommes le long de l'axe du combat.
  - **Les coups :** portée, rythme et poids par arme (la pique frappe du troisième rang), avec l'armure. Un homme écrasé par la presse ne pare plus. Les blessures affaiblissent. Les morts restent au sol, et les rangs se referment deux fois par seconde.
  - **La fatigue** monte avec l'effort, ronge la force et se répare lentement.
  - **Les ordres :** clic droit sur un régiment rouge pour l'attaquer. En démonstration, chaque régiment charge l'ennemi le plus proche à 150 m.
  - **L'animation :** un cycle de combat est cuit dans Blender (garde, pique abaissée, hallebarde qui s'abat), et les morts tombent à la renverse.
  - **Ce que les essais ont appris**, dans l'ordre :
    1. les coups tuaient sept fois trop vite ;
    2. les deux blocs se traversaient (les places étaient dans l'ennemi, et chacun passait par les vides entre les files) ;
    3. personne ne poussait, parce que la profondeur était calculée à l'ordre ouvert ;
    4. les rangs arrière restaient à leur place, car on poussait « vers une place » et non avec sa force ;
    5. les blocs glissaient l'un contre l'autre de côté ;
    6. les ailes contournaient l'ennemi ;
    7. l'espacement serré de 0,85 m laissait des vides.

    Chaque cause a été mesurée (retard par rang, centres, mélange au fil du temps) avant d'être corrigée. Au passage, les normales des soldats étaient inversées depuis le jalon 3 : les coins sont désormais écrits à rebours pour Unity.
  - **Limites :** au-delà de 45 s de presse, deux régiments témoins usés (15 % de morts, 40 % de fatigue) commencent à s'entremêler. Le critère de mélange ne porte donc que sur les 45 premières secondes, et la série complète reste dans le rapport : c'est au moral (jalon 5) de les faire rompre avant. Le combat est un corps à corps ; les arbalétriers n'y tirent pas encore (jalon 6). Personne ne fuit (jalon 5).
- **24 septembre 2026** — jalon 5 fait. La peur est propre à chaque homme ; aucun modificateur de moral n'est écrit au niveau du régiment.
  - **Ce qui la nourrit, et seulement ce qu'il perçoit :**
    - un camarade qui tombe à quelques mètres (un ennemi qui tombe rassure un peu) ;
    - ses propres blessures ;
    - être seul ou presque avec l'ennemi tout près ;
    - un ennemi à côté de soi ou dans le dos, qu'on ne peut ni parer ni frapper ;
    - la peur de ses voisins : la panique se propage vite, le calme lentement ;
    - la fatigue, qui amplifie le tout.
  - **Retour au calme :** la peur retombe d'elle-même, plus vite loin de l'ennemi et entouré des siens.
  - **La fuite :** au-delà de son courage, propre à chacun (0,55 à 0,9), un homme fuit loin de la menace. Il ne pousse plus, ne frappe plus et ne pare plus. Il revient quand sa peur est tombée sous 30 % de son courage.
  - **Le régiment :** il est en déroute quand la moitié de ses hommes fuient. Il cesse alors d'attaquer et se regroupe autour de ceux qui tiennent, puis se rallie quand ils reviennent.
  - **La direction compte par la physique :** on ne pare et ne frappe que devant soi. Le flanc tue donc davantage de lui-même, et la peur fait le reste.
  - **Ce que les essais ont appris :**
    - une réserve qui attaquait aussi contournait ses amis et frappait de flanc : le témoin était faux, il reste désormais en réserve ;
    - les épreuves n'avaient pas les mêmes armes ; tout le monde a désormais la pique ;
    - trois ou cinq épreuves par condition jugées « rompu ou non », c'était le hasard : on juge maintenant sur vingt épreuves et sur une grandeur continue, la part de fuyards au plus fort ;
    - **la simulation dépendait de la cadence d'affichage :** elle avance désormais à pas fixe (60 pas par seconde simulée), ce qui touche tous les jalons ; tous ont été revérifiés ;
    - la perception « ennemi hors de vue » a été resserrée au-delà de 90°, sinon elle s'allumait aussi dans une mêlée de front qui se déforme.
  - **Calibrage :** les taux de peur sont des nombres réglés, pas des règles de jeu (un mort voisin : +0,10 ; un ennemi hors de vue : +0,07 par seconde).
  - **Isolement des essais :** l'essai du jalon 4 isole la poussée et coupe donc la peur.
  - **Mesure de performance :** elle attend désormais 300 hommes au contact au lieu de 1 000, parce que des fronts rompent avant que toute la ligne soit engagée.
  - **Limites :** pas de drapeau ni de chef, dont la présence rassurerait ; un fuyard rallié retourne à sa place, même au milieu de l'ennemi ; les régiments en déroute ne quittent pas le champ de bataille.
- **24-25 septembre 2026** — jalon 6 fait. Les arbalétriers tirent de vrais carreaux.
  - **Le carreau :** un objet balistique lancé à 55 m/s, courbé par la gravité, sur une trajectoire calculée pour atteindre un homme du régiment visé. La dispersion croît avec la fatigue.
  - **Ce qu'il rencontre :** il s'arrête sur le premier corps, le premier pavois ou le sol. Un carreau peut tuer un ami placé sur sa route.
  - **Le réservoir :** 8 192 carreaux sont réutilisés, sans créer ni détruire d'entités pendant la bataille.
  - **L'arbalétrier :** il s'approche à 230 m, s'arrête et tire. Il recharge en environ 20 s (arbalète de guerre au cranequin). Il se forme en quinconce et ne tire pas dans le dos d'un camarade. Chaque carreau blesse, tue et fait peur par les mécanismes du jalon 5.
  - **Le pavois :** chaque arbalétrier le porte dans le dos, le plante devant lui à l'arrêt, et s'abrite à genou derrière, sauf pour viser. Le pavois est un objet posé dans le monde : il reste planté si son porteur fait un pas ou tombe. Une posture « à l'abri » est cuite dans Blender.
  - **Ce que l'essai montre, sans règle de protection :** le pavois protège presque entièrement du tir tendu (7 % des touches) et moins bien du tir plongeant (21 %), qui frappe par le haut. C'est ce que disent les sources.
  - **Ce que les essais ont appris :**
    - les rangs arrière tuaient les rangs avant, d'où la vérification de la ligne de tir (elle mesurait d'abord la distance depuis le mauvais point) et le quinconce ;
    - un pavois « attaché » au porteur immobile disparaissait à chaque mouvement de rang : il est devenu un objet posé ;
    - debout derrière un pavois, on reste exposé : d'où la posture à l'abri ;
    - un premier essai mesurait la protection dans le seul cas où elle ne joue pas (le tir plongeant) : l'essai a désormais deux temps ;
    - le rechargement de 10 s rendait l'arbalète si meurtrière que les premières lignes de la démonstration mouraient avant de se rejoindre : il est passé à 20 s.
  - **Mesure de performance :** elle met désormais la bataille en scène (premières lignes à 40 m, arbalétriers derrière) pour mesurer mêlée et tir ensemble : 308 hommes au contact et 1 857 carreaux en vol, 95e centile au plus 3,19 ms.
  - **Limites :** pas encore d'arcs (plus rapides, moins perçants) ni d'armes à feu ; on ne vise pas un homme précis, on tire dans la masse ; les boucliers portés à la main n'existent pas encore ; en démonstration, les arbalétriers représentent la moitié de chaque armée, ce qui est beaucoup.
- **25 septembre 2026** — jalon 7 fait. La charge brise un rang non préparé et se brise sur des piques, sans qu'aucune règle ne dise « cavalerie ».
  - **Le cavalier :** `fabrique/soldats.py` construit un homme d'armes monté (866 triangles), sur un squelette de 19 os : un destrier bai, sa housse aux couleurs du camp, le harnois, le bassinet et une lance de 4,2 m. Blender cuit quatre allures : le trot, lance droite ; le repos ; le combat arrêté ; et le galop de charge en quatre temps, lance couchée. Le galop se joue au pas réellement parcouru, et la foulée s'allonge avec la vitesse.
  - **Le corps :** un cheval et son cavalier pèsent 620 kg, poussent jusqu'à 3 000 N et galopent à 8,5 m/s. C'est un disque de 1,3 m, qui n'est pas du même régiment que les fantassins qu'il bouscule.
  - **Le renversement :** un choc plus lourd que soi, trop brusque pour qu'on le suive d'un pas (au-delà de 45 m/s²), renverse. Le choc est alors inélastique : le renversé part avec le cheval, qui y perd d'autant son élan ; les deux corps font le même calcul, et la quantité de mouvement se conserve. À terre, un homme ne pousse ni ne pare ; il est piétiné par les chevaux lancés et se relève en quelques secondes. Un cheval qui passe sur des corps trébuche.
  - **La pique baissée :** un ressort amorti pointé à 3,2 m devant le piquier. Le fer entre dans le poitrail jusqu'à 5 000 N ; la hampe se rompt enfoncée de 1,2 m. Le cheval meurt d'avoir absorbé 2 500 J sur des fers. Le talon planté en terre porte l'essentiel du choc : arrêté, le piquier en reçoit 15 % ; en marche, tout. Un cheval voit les fers devant lui et renâcle (une perception du jalon 5 : +0,05 de peur par seconde et par fer).
  - **L'ordre de baisser les piques :** il est donné quand des hommes ennemis approchent de front, à 70 m. En hérisson, la pique reste droit devant ; une hampe de cinq mètres ne se braque pas sur un cheval.
  - **La charge :** le trot, puis le galop pour les 110 derniers mètres, vers un point au-delà de l'ennemi. Chaque cavalier tient l'allure de sa ligne et corrige son retard. Une charge arrêtée au contact cesse de pousser.
  - **Ce que les essais ont appris :**
    - un homme renversé devenait transparent, et le cheval traversait dix rangs sans perdre d'élan ; d'où le choc inélastique ;
    - la pique ne couvrait que le milieu du poitrail et se rompait à 0,6 m : un cheval sur deux passait entre les hampes ;
    - les piques se braquaient sur le cheval le plus proche, et convergeaient en ouvrant des passages ;
    - les chevaux ne galopaient jamais : chacun réglait sa vitesse sur son retard, sans tenir l'allure de la ligne, et touchait l'ennemi entre 1 et 3,5 m/s ;
    - l'ancre de la cavalerie filait devant ses chevaux et passait au-delà des piquiers, qui relevaient alors leurs piques : l'alerte regarde désormais les hommes, pas l'ancre ;
    - les chevaux arrêtés continuaient de pousser et rompaient les piques rang après rang ;
    - la blessure d'une pique se comptait d'abord à travers l'armure du cavalier, alors que le fer entre dans le poitrail du cheval.
  - **La mesure :** on juge l'entrée des cavaliers par rapport au premier rang debout, pas à la ligne de départ. Contre les piques, le premier rang recule d'un ou deux mètres sous le choc et tient : un front repoussé n'est pas un front traversé. Le seuil de 0,5 m fixé d'abord était arbitraire, et la mesure donnait 0,53 m. Il est devenu la profondeur d'un rang (1,1 m), ce que dit « ne dépasse pas le premier rang ».
  - **Contre-épreuves :**
    - sans la masse des chevaux, les cavaliers n'entrent que de 0,8 m et aucun rang ne rompt ;
    - sans les piques, ils entrent de 67,6 m, tuent 2 447 piquiers sans perte, et tous les piquiers rompent.
  - **Performance :** la mesure met la cavalerie sur les ailes, qui charge le bout de la ligne adverse ; 95e centile au plus 3,09 ms. La démonstration en range deux régiments par armée sur les ailes de la seconde ligne.
  - **Jalon 5, revérifié :** il passe toujours, mais avec une autre marge : 3 ruptures sur 10 de flanc contre 0, et 48 % de fuyards au plus fort contre 19 % (6 contre 1 et 51 % contre 19 % auparavant).
  - **Limites :**
    - le cheval est un disque : il n'a ni flanc long ni croupe, et ne tombe jamais lui-même ;
    - le cavalier et son cheval ne font qu'un seul corps : on ne tue pas l'un sans l'autre, et il n'y a pas d'homme démonté ;
    - la lance ne se rompt pas, et le trot se joue même au pas ;
    - un piquier tué laisse sa pique disparaître avec lui ;
    - contre des arbalétriers à la dague, 80 hommes d'armes ne perdent personne ;
    - les piques n'arrêtent que les chevaux : un homme à pied ne s'y embroche pas.
