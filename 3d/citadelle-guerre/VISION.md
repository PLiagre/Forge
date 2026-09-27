# Citadelle — Guerre : la vision

> Ce fichier dit ce que le projet doit devenir. Il est fait pour être corrigé :
> changer une ligne ici déplace la feuille de route ([ROADMAP.md](ROADMAP.md)).

## En une phrase

Des batailles tactiques de 5 000 à 10 000 hommes autour d'une citadelle
alpine vers 1400 : assaut des remparts, combats de rue dans le bourg et
batailles de vallée. La mêlée naît de la poussée des corps, de la fatigue et
de la peur, pas de règles écrites d'avance.

## Les décisions (24 septembre 2026)

| | décision | ce qu'on a écarté |
|---|---|---|
| **Jeu** | une bataille tactique seule, contre une IA | la campagne stratégique, le recrutement façon Manor Lords, le multijoueur |
| **Échelle** | 5 000 à 10 000 hommes sur la carte | 1 000 à 3 000 ; plus de 20 000 |
| **Situations** | siège de la citadelle, combats de rue, bataille de vallée | la citadelle en simple décor |
| **Troupes** | mêlée (piquiers, hallebardiers, hommes d'armes), tireurs (arcs, arbalètes, premières armes à feu), cavalerie, engins de siège | — |
| **Combat** | simulation physique : les masses se poussent, les formations se déforment, les hommes se fatiguent ; le moral vient de ce qu'ils subissent | le combat arcade ; les règles Total War à pourcentages |
| **Destruction** | physique : les murs se fracturent, les maisons brûlent et s'effondrent | les brèches par points de vie |
| **Modèles** | soldats, chevaux et engins générés dans Blender, libres de droits | les packs de l'Asset Store |
| **Carte** | une carte de bataille dédiée, dans le style et avec le kit de la Citadelle de Forge | l'emprise actuelle des scènes de Forge |
| **Forge** | projet séparé, mais rebranchable plus tard | une dépendance au moteur Forge |
| **Machine de référence** | RTX 3070 Ti, i7-13700K, 1920 × 1080 | — |

## Les principes

1. **La performance est une preuve, pas une impression.** Un jalon est atteint
   quand le joueur Windows compilé tient un 95e centile sous 16,67 ms, soit
   60 images/s, sur la machine de référence et sur toutes les vues de la mesure.
2. **Une capacité n'existe que si sa preuve peut échouer.** C'est le principe
   repris de Forge. Chaque contrôle a une contre-épreuve qui doit le faire
   rougir.
3. **L'émergence plutôt que la règle.** Interdit : « si flanc alors −30 % de
   moral ». Exigé : les hommes pris de flanc sont frappés sans pouvoir
   répondre, ils reculent, poussent leurs voisins, le rang se désorganise, la
   peur gagne. Le test de Forge s'applique à chaque proposition : est-ce un
   comportement émergent ou une règle codée en dur ?
4. **Un soldat est une personne.** Il a une place dans son rang, une vitesse,
   une fatigue, une blessure et un moral. Le régiment est un ordre donné à des
   hommes, pas une entité qui se bat à leur place.
5. **Les données sont rebranchables sur Forge.** Un soldat est un homme d'une
   population, un régiment est levé quelque part et les pertes sont des morts.
   Le format d'entrée et de sortie d'une bataille (armées engagées, morts,
   blessés, fuyards) est pensé pour que Forge puisse un jour le produire et le
   relire. Aucun code de Forge n'est importé.

## Les choix techniques qui en découlent

| besoin | réponse |
|---|---|
| 10 000 hommes simulés à chaque image | Unity Entities (ECS), Burst, Jobs |
| 10 000 hommes dessinés | Entities Graphics (BatchRendererGroup), URP Forward+ |
| animer 10 000 corps | animation cuite en textures (VAT) sur les modèles Blender ; balancement procédural en attendant |
| le voisinage entre soldats | grille spatiale reconstruite à chaque image |
| la poussée des masses | une simulation de foule maison, pas le moteur physique de Unity, qui ne tient pas 10 000 corps |
| les murs qui se fracturent | des blocs pré-fracturés dans Blender, activés à l'impact, pour rester réellement physiques sans calculer la fracture pendant la partie |
| le feu des maisons | la propagation simulée par pièce de charpente ; l'effondrement suit la perte des appuis, comme le chantier de la Citadelle |

## Les tensions assumées

- **Destruction physique, mêlée physique et 10 000 hommes à 60 images/s**
  cumulent les postes les plus coûteux du genre. On les prouve un par un,
  chacun avec sa mesure, avant de les empiler.
- **Émergence contre lisibilité.** Un joueur doit comprendre pourquoi son
  régiment a cédé. La simulation reste émergente, mais elle doit se voir :
  rangs qui ploient, hommes qui reculent, bannière qui tangue.

## Ce qu'on refuse

- Un compteur de moral qui baisse selon une table.
- Un soldat qui meurt « parce que le régiment a perdu des points de vie ».
- Une mesure de performance prise dans l'éditeur plutôt que dans le joueur.
- Un asset sous licence poussé dans un dépôt, même privé, sans vérifier sa licence.
