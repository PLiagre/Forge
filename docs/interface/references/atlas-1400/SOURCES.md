# L'atlas posé à côté de la carte politique du jeu

La planche de l'étape 1 (`modes-de-carte`, images `7-atlas-europe` à
`11-atlas-balkans`) pose la carte politique du jeu à côté d'un atlas
historique, cadre par cadre. Les zones de l'atlas qui répondent aux cadres
du jeu sont dans [`cadres.json`](cadres.json), en pixels de l'image, depuis
son coin en haut à gauche. Chaque zone couvre ce que montre le cadre du jeu,
calculé sur les terres servies des pays du cadre : pour l'Italie, les îles de
Venise et les comptoirs de Gênes l'élargissent à la Méditerranée centrale, et
la zone de l'atlas la suit, pour que les deux images montrent la même étendue.

Chaque zone nomme aussi ses grands pays (`pays`), tirés des repères de 1400
et écrits comme le service les sert : la planche échoue si l'un d'eux n'est
pas servi sous ce nom, ou si son nom ne se lit pas en entier sur la carte du
cadre. Une zone sans grand pays échoue aussi.

## La planche rangée

La planche du monde livré est rangée dans [`planche-du-jeu/`](planche-du-jeu/) :
une image par cadre (`europe.png`, `france-et-iles.png`…) et `planche.json`,
qui dit le monde dont elle est la photo (graine, jours poussés, IA ou non,
date servie), les grands pays lus par cadre et l'empreinte des terres
(SHA-256 des lignes « cellule=pays » et « cellule/rang=pays » triées). Le
build (`ForgeLocal3D.Build.Nuit`) la copie à côté du lanceur, et dit si son
monde est encore celui du build.

Elle ne s'écrit qu'avec le drapeau `-forgeRangerLaPlanche`, sur le monde
frais (aucun pays choisi, aucun jour joué depuis le lancement du service) ;
sans lui, aucune capture ne récrit un fichier du dépôt. Pour la refaire :

```powershell
& $unity -batchmode -projectPath 3d\unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeCaptures <dossier> -forgeScenario etape-1-d-un-trait -forgeServiceIa -forgeRangerLaPlanche -logFile <journal>
```

## L'atlas

| | |
|---|---|
| fichier | `shepherd-europe-1360.jpg` (1817 × 1120) |
| carte | *Europe about 1360*, planche 77 |
| ouvrage | William R. Shepherd, *Historical Atlas*, New York, Henry Holt, édition de 1926 |
| source | Perry-Castañeda Library Map Collection, université du Texas à Austin : <https://maps.lib.utexas.edu/maps/historical/shepherd/europe_1360.jpg> |
| licence | domaine public : publié aux États-Unis en 1926, il y est libre depuis 2022 (95 ans) ; l'auteur, mort en 1934, est libre en Europe depuis 2005 (70 ans après sa mort) |
| relevé le | 24 novembre 2026 |

## L'écart de date, dit sur chaque planche

L'atlas montre l'Europe **vers 1360**, quarante ans avant le départ du jeu
(1400). Ce qui a changé entre les deux, et qu'il ne faut pas lire comme une
faute du jeu :

- les Ottomans n'y tiennent encore que le nord-ouest de l'Anatolie et un pied
  en Thrace ; en 1400 ils tiennent la Bulgarie, la Thrace, la Macédoine et la
  Serbie vassale, et Byzance n'est plus que Constantinople et la Morée ;
- la Bulgarie et la Serbie y sont des royaumes indépendants ;
- la Lituanie n'est pas encore unie à la Pologne (union de Krewo, 1385) ;
- la Hongrie et la Bohême n'y sont pas encore aux mains des Luxembourg ;
- l'Union de Kalmar (1397) n'existe pas : Danemark, Norvège et Suède y sont
  séparés ;
- la Bourgogne n'a pas encore pris la Flandre (1384).

## Europa Universalis IV

La carte d'Europa Universalis IV appartient à Paradox Interactive : elle
n'entre jamais dans le dépôt, qui est public, ni dans une image jointe à une
PR. La planche lit une capture d'Europa seulement dans `D:\Forge\references\eu4\`
(ignoré par git), un fichier par cadre (`europe.png`, `france-et-iles.png`,
`empire.png`, `italie.png`, `balkans-et-orient.png`). Quand elle s'y trouve,
la planche complète, avec Europa, s'écrit dans `D:\Forge\references\eu4\planches\`,
hors du dépôt et hors des images jointes ; la planche publiée le dit. Sans
elle, la planche publiée dit qu'elle manque.

La référence publique est la carte politique de **1444** du wiki officiel
d'Europa Universalis IV (<https://eu4.paradoxwikis.com/Map>) : 1444 n'est pas
1400, et l'écart y joue dans l'autre sens (l'Union de Kalmar, la Bourgogne de
Flandre, les Ottomans dans les Balkans y sont, Byzance réduite à la ville).
