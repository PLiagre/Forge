# Brief 201 — Kit matière et silhouette

## But

Remplacer le kit architectural trop dense par une grammaire de silhouette,
des ouvertures réelles, un trim exportable et des LOD construits par retrait.

## Règle du monde

CityLab présente une ville ForgeHistory sans devenir sa simulation. Les assets
restent déterministes, licenciés et publiés hors des sources Vendor.

## Périmètre

- `AssetFactory/Styles/frontier.json`
- `AssetFactory/Schemas/architecture_style.schema.json`
- `Tools/AssetFactory/style.py`
- `Tools/AssetFactory/Blender/building_kit.py`

## Conditions de succès

### SC1 — La grammaire est mesurable

`py -3 Tools/AssetFactory/citylab_factory.py style-check` réussit et les tests
Factory prouvent ouvertures, UV, budgets et déterminisme.

### SC2 — La preuve ne dépend pas d'une déclaration

`py -3 -m unittest Tools.AssetFactory.test_citylab_factory -v` réussit sur un
échantillon non vide.

## Hors périmètre

ForgeHistory, les sources Vendor, toute fusion et toute promotion artistique
sans revue humaine.

---

*Ce lot venait du dépôt Victoria CityLab, où il portait le numéro 001. La fusion a ajouté 200 aux lots de la ville pour que les numéros du moteur et ceux de la ville ne se chevauchent plus.*
