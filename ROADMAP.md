# Feuille de route

Chaque jalon a une preuve qui peut échouer. Un jalon n'est « fait » que si sa
mesure est verte dans le joueur Windows compilé, sur la machine de référence.

| # | jalon | la preuve | état |
|---|---|---|---|
| 1 | **La foule** — 10 000 hommes en formation marchent dans une vallée, à 60 images/s | `outils/atelier.ps1 mesurer` : 10 000 soldats présents, déplacés, visibles à l'écran, 95e centile < 16,67 ms sur quatre vues ; la contre-épreuve (un soldat retiré) doit échouer | **fait** — 95e centile au plus 1,57 ms ; 30 000 hommes : 2,57 ms |
| 2 | **Les ordres** — sélectionner, déplacer, faire pivoter, élargir ou resserrer un régiment | un régiment ordonné atteint sa place ; un régiment gêné par un autre se déforme au lieu de le traverser | ébauche dans le jalon 1 |
| 3 | **Le corps** — soldat modulaire Blender (armure, arme, couleurs) et animation cuite en textures | 10 000 soldats animés tiennent toujours le budget | |
| 4 | **La mêlée** — poussée, coups, blessures, fatigue, deux régiments qui se battent | le régiment le plus profond repousse l'autre sans règle qui le décrète | |
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
