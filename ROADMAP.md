# Feuille de route

Chaque jalon a une preuve qui peut échouer. Un jalon n'est « fait » que si sa
mesure est verte dans le joueur Windows compilé, sur la machine de référence.

| # | jalon | la preuve | état |
|---|---|---|---|
| 1 | **La foule** — 10 000 hommes en formation marchent dans une vallée, à 60 images/s | `outils/atelier.ps1 mesurer` : 10 000 soldats présents, déplacés, visibles à l'écran, 95e centile < 16,67 ms sur quatre vues ; la contre-épreuve (un soldat retiré) doit échouer | **fait** — 95e centile au plus 1,57 ms ; 30 000 hommes : 2,57 ms |
| 2 | **Les ordres** — sélectionner, déplacer, faire pivoter, élargir ou resserrer un régiment | `atelier.ps1 mesurer` : un régiment atteint sa place sur 16 puis 40 files (front à 10 % près, 95 % des hommes à leur place) ; un régiment envoyé à travers un autre ne passe pas (< 5 %) et aucun corps n'en recouvre un autre (> 0,6 m) ; sans les corps, l'essai doit échouer | **fait** — 16,7 m pour 16,5 ; 43,0 m pour 42,9 en 14 s ; 0 % passés ; 0,80 m |
| 3 | **Le corps** — soldat modulaire Blender (armure, arme, couleurs) et animation cuite en textures | `atelier.ps1 mesurer` : 10 000 soldats animés tiennent le budget ; deux phases de marche, positions figées, changent l'image ; sans l'animation, cette preuve doit échouer | **fait** — 95e centile au plus 2,39 ms ; l'animation change 6,6 % de l'image, 0,00 % sans elle ; 30 000 hommes : 5,28 ms |
| 4 | **La mêlée** — poussée, coups, blessures, fatigue, deux régiments qui se battent | `atelier.ps1 mesurer` : trois duels de même front, 10 contre 5 rangs, 5 contre 10 et 10 contre 10. Le plus profond fait reculer la ligne d'au moins 3 m, dans les deux sens ; les régiments ne se traversent pas. Sans la poussée des rangs arrière, l'essai doit échouer. La mesure de performance porte sur une mêlée engagée sur tout le front | **fait** — +9,9 m et −9,4 m (témoin +0,5 m) ; sans poussée : +1,3 m et −0,2 m ; mêlée de 954 hommes au contact en 2,23 ms |
| 5 | **La peur** — le moral naît des blessés autour de soi, des flancs, de la fatigue ; fuite et ralliement | un régiment pris de flanc cède plus souvent, sans modificateur écrit | |
| 6 | **Les tireurs** — flèches et carreaux simulés en masse, trajectoires, boucliers, pavois | 2 000 projectiles en vol tiennent le budget | |
| 7 | **La cavalerie** — masse, élan, charge, chevaux modélisés | une charge brise un rang non préparé et se brise sur des piques | |
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
