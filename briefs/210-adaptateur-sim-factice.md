# Brief 210 — Adaptateur snapshot/intention factice

## But

Prouver le protocole de snapshots et d'intentions contre un backend in-memory
déterministe avant que la couche villes réelle de ForgeHistory soit disponible.

## Règle du monde

ForgeHistory reste l'unique autorité de production. Le factice éprouve le
transport, l'ordre et les refus ; il ne crée aucune économie Unity de secours.

## Périmètre

- `Packages/com.victoria.citymode.contracts/Runtime/ForgeHistoryCityModeContracts.cs`
- `Packages/com.victoria.citymode.presentation/Runtime/CityModeSession.cs`
- `Packages/com.victoria.citymode.presentation/Tests/Editor/InMemoryCityModeGateway.cs`
- `Packages/com.victoria.citymode.presentation/Tests/Editor/InMemoryCityModeGatewayTests.cs`
- `Tools/validate_forgehistory_city_mode_contract.py`

## Conditions de succès

### SC1 — Les intentions sont idempotentes et révisionnées

`py -3 -m unittest Tools.tests.test_forgehistory_city_mode_contract -v` prouve
qu'un `intentId` doublé ne produit qu'un effet et qu'une révision périmée est
refusée ; le check `unity-windows` du SHA exact couvre le factice C#.

### SC2 — La frontière reste pure

`py -3 Tools/validate_forgehistory_city_mode_contract.py` rend
`upstream_writes=0` et aucune dépendance Unity dans les contrats.

### SC3 — La phase réelle reste bloquée

`rg -n "M3-FH-05" Docs/ROADMAP.md` ne présente pas l'adaptateur ForgeHistory
réel comme livré.

## Hors périmètre

Modifier ForgeHistory, implémenter la couche villes réelle, faire de
`LocalCitySimulation` une autorité, M3-FH-07 et fusionner.

---

*Ce lot venait du dépôt Victoria CityLab, où il portait le numéro 010. La fusion a ajouté 200 aux lots de la ville pour que les numéros du moteur et ceux de la ville ne se chevauchent plus.*
