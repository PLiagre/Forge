# visualisateur/

Regard 3D. Il **lit** une photographie de `sim/` et n'en décide aucun
nombre — comme `viewer/`, un étage plus loin.

Il est le seul dossier du dépôt à demander des bibliothèques extérieures
(`requirements.txt`). C'est assumé : parler à un moteur de rendu écrit en
Rust ne se fait pas en bibliothèque standard. Rien d'autre ne dépend de
lui, et le jeu tourne sans lui — `py -m sim` n'a besoin de rien.
Le moteur de rendu est le fork [PLiagre/forge3d](https://github.com/PLiagre/forge3d)
(paquet PyPI `forge3d`).

```bash
# photographier le monde (le jeu, inchangé)
python3 -m sim --ticks 0 --seed 0 --snapshot-json /tmp/monde.json

# le montrer en relief, via forge3d
python3 -m visualisateur --snapshot /tmp/monde.json --png /tmp/monde-3d.png
```

Raccourci qui photographie puis rend, sans recalculer le tick :

```bash
python3 -m visualisateur --ticks 0 --seed 0 --png /tmp/monde-3d.png --apercu /tmp/monde-mnt.png
```

## Ce que c'est

La carte porte des **classes de relief**, pas un MNT en mètres. Le
visualisateur rasterise les polygones du snapshot, pose une altitude
plausible par classe (fidélité 2), et demande à forge3d une image
hors écran. L'exagération verticale est un facteur de **lecture**,
dérivé de l'étendue de la carte.

## Dépendances (ce paquet seulement)

```bash
python3 -m pip install numpy pillow forge3d
```

`sim/` et `viewer/` restent en bibliothèque standard. Rien d'ici
n'y entre.

## Hors périmètre

Pas de fenêtre interactive. Pas de mer navigable. Pas de villes.
Pas de second monde.
