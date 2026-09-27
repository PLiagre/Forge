# Brief 206 — Carte MetallicGloss empilée

## But

Publier une carte où R porte le metallic et A la smoothness, puis la câbler
dans les matériaux URP sans transformer toute la ville en surface brillante.

## Règle du monde

Les matériaux de présentation sont reproductibles et leurs conventions sont
prouvées dans les pixels et dans l'import Unity.

## Périmètre

- `Tools/AssetFactory/generate_pbr_trim.py`
- `Tools/AssetFactory/matter_gate.py`
- `Assets/CityLabHost/Editor/CityLabFactoryAssetIntegration.cs`
- `Packages/com.victoria.citymode/Tests/Editor/FactoryMatterTests.cs`

## Conditions de succès

### SC1 — Le bake est déterministe

`py -3 -m unittest Tools.AssetFactory.test_citylab_factory -v` prouve R =
metallic, A = 1 - roughness et un hash canonique stable.

### SC2 — Le cliquet reste fermé

`py -3 Tools/AssetFactory/matter_gate.py` rend 36/36 matériaux texturés, dette
M-1 à zéro et un slot gloss non vide.

### SC3 — Unity prononce l'import

Le check `unity-windows` du SHA exact est vert ; le `.meta` est produit par
Unity, jamais écrit à la main.

## Hors périmètre

Metallic brut dans le slot gloss, édition manuelle de `.meta`, jugement C-10,
ForgeHistory, personnages et fusion.

---

*Ce lot venait du dépôt Victoria CityLab, où il portait le numéro 006. La fusion a ajouté 200 aux lots de la ville pour que les numéros du moteur et ceux de la ville ne se chevauchent plus.*
