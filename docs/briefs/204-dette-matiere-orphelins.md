# Brief 204 — Vider la dette matière

## But

Prouver que les 28 anciens matériaux plats sont orphelins, les retirer avec
leurs `.meta`, fermer la dette M-1 et câbler l'occlusion du bon atlas.

Le commit distant non fusionné
`origin/cursor/m1-asset-07-c1-silhouette-79c2@61a30e2` contient une tentative de
ce retrait. Il peut servir de matière de reprise, mais ses faits doivent être
rejoués sur `main`; sa seule présence ne vaut pas livraison.

## Règle du monde

Une preuve décrit les assets effectivement instanciés. Un fichier orphelin ne
devient pas recevable en recevant artificiellement une texture.

## Périmètre

- `Assets/CityLabHost/Adapted/Factory/Materials/aged_bronze.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/aged_bronze.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/black_iron.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/black_iron.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/blue_black_slate.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/blue_black_slate.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/cold_stone.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/cold_stone.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/dark_bark.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/dark_bark.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/dressed_limestone.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/dressed_limestone.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/dry_hay.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/dry_hay.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/ember_glass.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/ember_glass.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/forge_coal.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/forge_coal.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/fresh_cut_wood.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/fresh_cut_wood.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/hemp_rope.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/hemp_rope.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/kiln_fired_brick.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/kiln_fired_brick.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/market_green_produce.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/market_green_produce.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/market_red_produce.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/market_red_produce.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/roof_a.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/roof_a.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/roof_accent_a.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/roof_accent_a.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/roof_accent_b.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/roof_accent_b.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/roof_accent_c.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/roof_accent_c.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/roof_b.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/roof_b.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/roof_c.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/roof_c.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/saw_steel.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/saw_steel.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/sawn_timber_boards.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/sawn_timber_boards.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/soot_plaster.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/soot_plaster.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/timber_a.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/timber_a.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/timber_b.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/timber_b.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/timber_c.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/timber_c.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/weathered_slate.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/weathered_slate.mat.meta`
- `Assets/CityLabHost/Adapted/Factory/Materials/woven_cloth.mat`
- `Assets/CityLabHost/Adapted/Factory/Materials/woven_cloth.mat.meta`
- `AssetFactory/Manifests/unity_matter_debt.json`
- `Tools/AssetFactory/matter_gate.py`
- `Assets/CityLabHost/Editor/CityLabFactoryAssetIntegration.cs`
- `Packages/com.victoria.citymode/Tests/Editor/FactoryMatterTests.cs`
- `Docs/ASSET_FACTORY_ROADMAP.md`

Cette liste correspond exactement à `m1_materials_without_any_texture`; aucun
autre asset du dossier ne relève de ce lot.

## Conditions de succès

### SC1 — Chaque retrait est précédé d'une preuve d'orphelin

Pour chaque GUID, `rg -n '<guid>' Assets Packages` ne trouve aucune référence
hors du couple `.mat`/`.meta` retiré. Un résultat non vide bloque le retrait.

### SC2 — La dette est un cliquet

`py -3 Tools/AssetFactory/matter_gate.py --declare-debt` produit
`still_owed=0`, conserve les 28 noms sous `were_owed` et refuse leur retour.

### SC3 — L'occlusion vient du même atlas

`py -3 -m unittest Tools.AssetFactory.test_citylab_factory.UnityMatterGateTests -v`
prouve un remap idempotent, aucun AO sur un aplat et zéro matériau d'atlas sans
occlusion.

### SC4 — La branche reste propre

`git diff --check` réussit. Unity est différé au brief 008.

## Hors périmètre

Éditer un `.meta`, élargir la dette, affecter `Metallic.png` directement au
slot gloss, juger C-10, modifier ForgeHistory ou fusionner.

---

*Ce lot venait du dépôt Victoria CityLab, où il portait le numéro 004. La fusion a ajouté 200 aux lots de la ville pour que les numéros du moteur et ceux de la ville ne se chevauchent plus.*
