# Brief 207 — Ornement sous budget

## But

Déclarer un vocabulaire d'ornement qui n'ajoute des éléments que lorsque le
budget LOD de la famille le permet.

## Règle du monde

Un ornement invisible ou payé par un dépassement n'améliore pas la ville. Les
silhouettes restent déterministes et lisibles aux distances prévues.

## Périmètre

- `Tools/AssetFactory/Blender/building_kit.py`
- `AssetFactory/Styles/frontier.json`
- `Tools/AssetFactory/silhouette_gate.py`
- `AssetFactory/Manifests/building_pilot.json`

## Conditions de succès

### SC1 — Aucun budget ne bouge

`py -3 Tools/AssetFactory/silhouette_gate.py` conserve les plafonds
4000/1800/600, C-1 et IoU <= 0,80.

### SC2 — Le résultat est reproductible

`py -3 -m unittest Tools.AssetFactory.test_citylab_factory -v` réussit et trois
générations rendent le même hash canonique.

## Hors périmètre

Relever un seuil, jitter de dimensions, jugement C-10, personnages,
ForgeHistory et fusion.

---

*Ce lot venait du dépôt Victoria CityLab, où il portait le numéro 007. La fusion a ajouté 200 aux lots de la ville pour que les numéros du moteur et ceux de la ville ne se chevauchent plus.*
