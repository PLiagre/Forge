# L'objectif final — ce que ce jeu est censé devenir

> Ce fichier est **fait pour être corrigé**. Il énonce la destination en termes
> qu'on peut contester ligne à ligne. Tout le reste du dossier `fusion/` en
> découle : si vous changez une phrase ici, la roadmap bouge.
>
> Il ne remplace pas [`VISION.md`](VISION.md), qui reste la source de vérité
> du moteur. Il dit ce que `VISION.md` ne disait pas : **qui joue, et à quoi**.

---

## En une phrase

Un jeu de grande stratégie où l'on commence seigneur d'un domaine en 1400 et
où l'on finit — si l'on y arrive — à la tête d'un État industriel en 1900,
sans jamais quitter la même simulation.

## Le siège du joueur : un seigneur qui devient un État

C'est la décision structurante, et elle n'était écrite nulle part avant ce
fichier.

| | on est seigneur | on devient un État |
|---|---|---|
| **échelle** | un lieu et ses environs | des provinces, puis un pays |
| **ce qu'on fait** | on trace, on bâtit, on nourrit | on taxe, on légifère, on négocie, on fait la guerre |
| **le geste** | poser une route, un champ, une scierie | fixer un impôt, ouvrir une route commerciale, déclarer |
| **la référence** | Manor Lords | Europa Universalis, puis Victoria 3 |
| **la vue** | la ville, en 3D, par Unity | la carte, en relief, par forge3d |

**L'ascension est le jeu.** Ce n'est pas un changement de mode qu'on
sélectionne dans un menu : c'est ce qui arrive quand un domaine devient assez
riche, assez peuplé et assez bien marié pour que le geste utile cesse d'être
« où je pose la scierie » et devienne « quelle loi je passe ». Les deux boucles
coexistent — un roi garde des domaines, un seigneur subit déjà la fiscalité
d'un autre — mais leur poids s'inverse.

Conséquence directe, et elle tranche une contradiction que les deux dépôts
portaient sans le dire :

- `VISION.md` écrit « le joueur crée des conditions, il ne place pas chaque
  bâtiment » ;
- CityLab donne au joueur une truelle : `R` trace une route, `Z` découpe des
  parcelles, `B` fonde un camp de bûcherons.

Les deux ont raison, **à des moments différents de la partie**. On pose les
bâtiments tant qu'on est seigneur. On crée des conditions une fois qu'on est
un État — parce qu'à ce moment-là il y a mille lieux et qu'aucun humain ne les
place à la main.

## Le monde

| | |
|---|---|
| **étendue** | Europe et pourtour méditerranéen — d'Irlande à l'Anatolie, de Norvège à Alexandrie |
| **surface** | 6 667 147 km² |
| **maille** | 596 cellules, 1 364 arêtes d'adjacence, 11 186 km² par cellule en moyenne |
| **provinces** | 50 nommées |
| **relief** | 5 classes — 322 plaines, 162 collines, 77 montagnes, 20 marais, 15 hautes montagnes |
| **gisements** | 27 nommés |
| **période** | 1400 → 1900 |
| **base de temps** | 1 tick = 1 jour, soit 182 625 ticks pour la partie complète |

La carte est **figée** : un seul fichier, `data/world-1400.json`, lu par le
moteur. Sa fidélité est déclarée : niveau 1 (juste dans les grandes lignes)
pour le trait de côte, le relief et les gisements ; niveau 2 (plausible,
jamais sourcé) pour tout ce que le jeu en déduit.

## Les principes qui ne se négocient pas

1. **Une seule simulation.** Le monde entier tourne en permanence. Les vues
   n'ont aucune donnée à elles ; elles regardent. Jamais deux bases, jamais une
   copie « pour l'affichage ».
2. **L'économie est physique.** Chaque kilo a une origine, un transport, un
   stockage, une destination. Aucune ressource ne se téléporte. Une rupture
   logistique produit ses conséquences toute seule.
3. **L'émergence plutôt que la règle.** Interdit : « si famine alors +20 % de
   criminalité ». Exigé : les gens ont faim, ils cherchent, certains volent.
   À chaque proposition on se demande : est-ce un comportement émergent ou une
   règle codée en dur ?
4. **Le monde est amorcé historiquement.** À t0 il contient ce que l'histoire
   dit qu'il contient. L'émergence concerne ce qui arrive **pendant** la
   partie, pas l'amorçage.
5. **Une capacité n'existe que si sa preuve peut échouer.** Un test qui ne peut
   pas rougir ne prouve rien.

## Les échelles

```
Monde → Pays → Province → Cellule → Lieu → Quartier → Bâtiment → Famille → Personne
                             ▲        ▲
                             │        └── ce qui manque, et qu'on va créer
                             └── ce que le moteur sait faire aujourd'hui
```

Chaque niveau doit pouvoir être simulé seul. Le moteur monte ou descend le
niveau de détail selon ce qu'on regarde, et **les agrégations sont
conservatives** : rien ne se perd, rien ne s'invente en changeant d'échelle.
Cent personnes agrégées puis désagrégées font toujours cent personnes.

## Le lot pivot : subdiviser la cellule

C'est la décision la plus lourde du projet et elle mérite d'être comprise
avant d'être acceptée.

**Le problème.** Une cellule couvre 11 186 km² et porte ~110 000 habitants.
C'est une région. Aucune ville médiévale ne fait cette taille. Pourtant le
jeu doit pouvoir ouvrir *un* lieu et y poser une scierie.

**Ce que le moteur dit aujourd'hui.** `sim/MODELE.md` a tranché autrement : le
« bourg » est la part des habitants d'une cellule qui ne tire pas sa nourriture
de ses champs — une **vue dérivée**, sans identité, et le document interdit
explicitement tout `city_id`, `ville_id` ou `bourg_id`. C'était le bon choix
tant qu'on ne jouait pas dans la ville.

**Ce que le contrat Unity exige.** `CityLaunchContext` demande un `city_id`
stable, un `cell_id` parent, un tick monde et une révision. Le contrat est
écrit, schématisé et testé — mais il réclame une chose que le moteur a déclaré
ne jamais produire.

**La décision : on subdivise.** La cellule se peuple de **lieux**. Un lieu
porte une identité stable, dérivée de façon déterministe de `cell_id` et d'une
graine, matérialisée seulement quand on la regarde ou qu'on y joue. La cellule
reste la maille du tick ; le lieu est ce qu'on ouvre.

**Ce que ça coûte, dit franchement.** Ce lot touche la carte, le tick, les
trois vues et le contrat. Il rouvre la gratuité de distribution que
`MODELE.md` nomme aujourd'hui : « la campagne nourrit son bourg sans
transport, sans perte et sans délai ». Le jour où la cellule se subdivise,
c'est là qu'il faut revenir — et ce jour est venu. Ce n'est pas un lot de
V1 : c'est le premier lot d'après.

## La V1 — atteinte

**On ne construit pas encore le jeu.** La V1 était de fusionner trois dépôts
pour obtenir une base saine. Les quatre conditions sont vertes :

1. **Un dépôt, une chaîne.** La fusion est faite, l'atelier vit dans l'arbre,
   il n'y a plus qu'un registre et qu'un jeu de règles. Ce qui reste : poser la
   protection de branche, et faire traverser le cycle entier à un lot.
2. **Une simulation qui ne s'effondre pas.** Le plafond de survie vaut
   **1,250**, contre 0,691 avant la fusion. Une année simulée fait croître le
   monde de 3,7 % au lieu d'en tuer 86 %.
3. **La carte de statistique.** `python3 -m vues.relief --lecture population
   --carte carte.png` colorie le monde par une de ses grandeurs. Six lectures,
   dont une qui refuse proprement tant que le snapshot ne la porte pas.
4. **Le tableau de bord et la chronique.** `python3 -m forge` écrit les trois
   vues depuis **une** simulation, et le prouve : leurs tick et graine doivent
   être ceux du snapshot.

Ce qui n'est **pas** dans la V1 : la vue ville jouable, les États, les armées,
les batailles, la subdivision en lieux.

## Après la V1 — l'ordre des couches

| # | couche | ce qu'elle apporte | état |
|---|---|---|---|
| 1 | **Monde vivant** | carte, relief, climat, ressources, population, économie locale, commerce | faite, et elle tourne |
| 2 | **Villes** | subdivision en lieux, urbanisation, métiers, entreprises, routes | ouverte — un métier existe, le bourg se compte |
| 3 | **États** | fiscalité, lois, diplomatie, technologies, culture, religion | non commencée |
| 4 | **Armées** | recrutement, logistique, ravitaillement, stratégie | non commencée |
| 5 | **Batailles** | une couche de plus sur les **mêmes** données, mêmes terrains, mêmes armées | non commencée |

La couche 3 est celle qui rend l'ascension jouable : sans État, un seigneur qui
réussit n'a nulle part où monter.

## La mesure du succès

Pas le nombre de fonctionnalités. La capacité du moteur à faire émerger seul
des situations complexes, crédibles et intéressantes — une famine qui vide une
vallée, une route qui enrichit un col, une guerre qui dépeuple un comté et fait
monter les salaires ailleurs. Si ces choses arrivent sans qu'on les ait
écrites, le moteur est bon.

## Ce qu'on refuse

- **Un clone de Victoria 3.** Les mécaniques comparables doivent émerger, pas
  être codées comme des règles de jeu.
- **Une seconde source de vérité.** Aucune vue ne possède de données.
- **Une donnée historique inventée.** L'absence de source se déclare ; elle ne
  se comble pas en silence. L'amorçage actuel est un proxy paramétrique, et le
  modèle le dit lui-même.
- **Un seuil qui « fait » une ville.** Poser un drapeau au-dessus d'un nombre
  d'habitants serait une règle de gameplay, pas une règle de monde.

---

## Ce que vous pouvez corriger ici

Ces points sont des décisions, pas des faits. Chacun déplace la roadmap.

| # | décision actuelle | l'alternative, si vous la préférez |
|---|---|---|
| 1 | on est un seigneur qui devient un État | rester seigneur ; ou être un État d'emblée |
| 2 | on subdivise la cellule en lieux | garder le bourg comme vue dérivée, et aligner Unity dessus |
| 3 | forge3d rend la carte, Unity rend la ville | Unity rend tout ; ou forge3d rend tout |
| 4 | 1400 → 1900 | une fenêtre plus courte, donc moins de couches à écrire |
| 5 | Europe et Méditerranée | le monde entier, ou une région seule |
| 6 | la V1 exclut la vue ville | l'inclure, et repousser la fusion d'autant |
| 7 | 1 tick = 1 jour | un tick plus long pour tenir 500 ans en temps humain |

Le point 7 mérite un chiffre : à 36 secondes par année simulée, une partie
complète de 1400 à 1900 coûte **environ cinq heures de calcul**. C'est
supportable pour un serveur, pas pour un joueur qui attend. Ce n'est pas un
problème de V1, mais c'en sera un.
