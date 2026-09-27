# 3d/ — ce qu'on voit du monde en trois dimensions

Tout ce qui demande Unity ou Blender vit ici. Rien ici ne décide un nombre du
monde : `jeu/sim/` le fait, et la 3D le montre (voir [CAP.md](../CAP.md)).

| dossier | quoi | machine |
|---|---|---|
| `unity/` | **le** projet Unity du jeu (6000.0.43f1, URP 17.0.4). Le kit retenu pour le jalon 1 est le désert : `Assets/ForgeLocal3D/Desert/`. Les paquets `com.victoria.citymode.contracts` (le contrat ville) et `.presentation` restent ; le labo `LocalCitySimulation` est archivé. | PC |
| `local3d/` | le paquet Python qui pilote Blender 5.2 et prépare les kits. Il reste entier : le kit du désert importe le code des autres familles (alpin, citadelle, atelier_v2). | PC |
| `archives/` | les prototypes qui ne portent pas le jalon courant, intacts. Voir [archives/README.md](archives/README.md). | — |

Pourquoi `local3d/` à côté d'`unity/` : les deux s'appellent par chemins
relatifs (`../local3d/...` depuis le projet Unity, `unity/...` depuis le
Python). Voisins, aucun de ces chemins ne change.

## Les packs de l'Asset Store

Le désert utilise deux packs sous licence : *Polylised – Medieval Desert City*
et *TerrainDemoScene_HDRP*. Ils vivent dans `unity/Assets/Vendor/`, **ignoré par
git** : le dépôt est public et leur licence interdit de les republier. Ils
existent sur le PC (dans `D:\Forge` et dans l'espace de travail du runner
`pc-forge`), jamais ailleurs. Sans eux, les scènes du désert s'ouvrent avec des
trous : c'est pourquoi les captures et le build se font sur le PC.

## Ouvrir

```bat
pc\Ouvrir_Unity.cmd            rem le projet, sur la scène du désert
pc\Ouvrir_Blender_Desert.cmd   rem la source Blender du ksar
pc\Ouvrir_Galerie_Desert.cmd   rem les captures
```

La compilation du projet est vérifiée par `.github/workflows/unity.yml` sur le
runner du PC, à chaque poussée qui touche `3d/unity/`.
