# Brief 203 — Schémas de construction

## But

Faire varier les bâtiments par des schémas de masse et des finitions déclarés,
sans relever les budgets ni les seuils de silhouette.

## Règle du monde

Une famille architecturale est une donnée reproductible. Une variante ne gagne
pas son identité par un jitter ou un détail invisible à l'échelle RTS.

## Périmètre

- `AssetFactory/Styles/frontier.json`
- `AssetFactory/Schemas/architecture_style.schema.json`
- `AssetFactory/Catalogs/building_pilot.json`
- `Tools/AssetFactory/silhouette_gate.py`
- `Tools/AssetFactory/Blender/generate_building_family.py`

## Conditions de succès

### SC1 — Les portes C sont mécaniques

`py -3 Tools/AssetFactory/silhouette_gate.py` mesure articulation, IoU,
schémas, finitions et budgets sur les 24 variantes.

### SC2 — Les seuils restent inchangés

`py -3 -m unittest Tools.AssetFactory.test_citylab_factory -v` réussit sans
test supprimé ou affaibli.

## Hors périmètre

Copie des références, source Vendor, modification silencieuse des seuils,
jugement C-10 par l'exécutant, ForgeHistory et fusion.

---

*Ce lot venait du dépôt Victoria CityLab, où il portait le numéro 003. La fusion a ajouté 200 aux lots de la ville pour que les numéros du moteur et ceux de la ville ne se chevauchent plus.*
