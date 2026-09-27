# Brief 202 — Porte matière Unity

## But

Prouver que les cartes Factory atteignent les matériaux réellement importés
dans Unity et que la dette matière ne peut pas croître silencieusement.

## Règle du monde

La présentation lit des assets admis ; elle ne masque jamais une absence de
preuve par un matériau plat ou un réglage d'import inventé.

## Périmètre

- `Tools/AssetFactory/matter_gate.py`
- `AssetFactory/Manifests/unity_matter_debt.json`
- `Assets/CityLabHost/Editor/CityLabFactoryAssetIntegration.cs`
- `Packages/com.victoria.citymode/Tests/Editor/FactoryMatterTests.cs`

## Conditions de succès

### SC1 — Le cliquet matière rougit puis passe

`py -3 Tools/AssetFactory/matter_gate.py` refuse une dette accrue et réussit
sur le manifeste publié.

### SC2 — Unity lit les mêmes cartes

Le check `unity-windows` du SHA exact rend un XML NUnit vert ;
`py -3 Tools/unity_nunit.py Logs/editmode.xml` peut le refuser.

## Hors périmètre

Édition manuelle de `.meta`, source Vendor, jugement artistique, ForgeHistory
et fusion.

---

*Ce lot venait du dépôt Victoria CityLab, où il portait le numéro 002. La fusion a ajouté 200 aux lots de la ville pour que les numéros du moteur et ceux de la ville ne se chevauchent plus.*
