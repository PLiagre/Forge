# 3d/archives/ — les prototypes qui dorment

Rangés le 27 septembre 2026, quand le désert a été retenu pour porter le
jalon 1 de [CAP.md](../../CAP.md). **Rien n'a été supprimé** : chaque dossier est
intact, et l'historique git garde tout le reste. Un lot de la chaîne n'y touche
pas ; un jalon qui en a besoin les réveille en mode direct.

| dossier | ce que c'est | pourquoi il dort | quand il se réveille |
|---|---|---|---|
| `citadelle-guerre/` | projet Unity à part (ECS, Burst) : batailles de 5 000 à 10 000 hommes autour d'une citadelle alpine, jalons 1 à 8 prouvés, jalon 9 (le siège) en cours. Importé avec son histoire. | c'est un jeu de bataille, pas un lieu vivant | jalon 6 (la colonne) : son moteur de foule en est la base |
| `unity-prototypes/` | les scènes V1, V2 (4 biomes), alpines (3) et de la citadelle (2), avec les assets qu'elles seules utilisent, à leur chemin d'origine sous `Assets/`. | elles ne portent pas le jalon courant | quand un jalon demande un biome tempéré ou alpin |
| `unity-citymode-labo/` | `com.victoria.citymode` (le labo `LocalCitySimulation` : une seconde économie, 11 785 lignes C#) et `com.victoria.citymode.assets` (coquille). | une seule simulation : `jeu/sim/` | jamais comme autorité ; ses idées de ville peuvent nourrir des lots |
| `fabrique/` | l'usine Blender d'assets venue de VictoriaCityLab. Ses chemins sont ceux de l'ancien dépôt ; 34 de ses images QA sont perdues (liste dans `donnees/Reports/QA/IMAGES-PERDUES.md`). | morte tant qu'elle n'est pas recâblée | si un jalon demande une chaîne d'assets |
| `lanceurs/` | les lanceurs `.cmd` des familles archivées. Ceux qui ouvrent Unity ne trouvent plus leurs scènes (elles sont ici) ; ceux qui ouvrent Blender ou une galerie visent `3d/local3d/`, qui n'a pas bougé de contenu. | lanceurs actifs : `pc/` | avec leur famille |

## Réveiller une scène Unity archivée

Les fichiers de `unity-prototypes/Assets/...` gardent leurs `.meta` (donc leurs
GUID). Les remettre au même chemin sous `3d/unity/Assets/` suffit : les
références se recollent. Le code C# des familles n'a pas été archivé (le désert
s'en sert), il est resté dans le projet.

## Citadelle-Guerre

Il se construit comme avant, depuis son dossier : `Mesurer.cmd`,
`Ouvrir_Unity.cmd`, `outils/atelier.ps1`. Son kit se lit dans
`3d/local3d/citadelle/sorties` ; ses textures ne sont pas versionnées (la
fabrique Blender de la citadelle les refait).
