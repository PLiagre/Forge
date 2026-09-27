# Brief 209 — Approbation artistique Factory

## But

Assembler un dossier de revue fidèle aux assets publiés afin que le
propriétaire rende l'approbation artistique de M1-ASSET-05.

## Règle du monde

L'auteur des assets ne signe pas leur réception. Les licences, les hashes et
les limites de placeholder restent visibles dans la décision.

## Périmètre

- `AssetFactory/Reports/QA/factory_review_board.png`
- `AssetFactory/Manifests/building_pilot.json`
- `Docs/VENDOR_AUDIT.md`
- `Docs/ASSET_FACTORY_ROADMAP.md`

## Conditions de succès

### SC1 — Le dossier correspond aux publications

`py -3 Tools/AssetFactory/qa_factory_release.py` relie la planche, les hashes
et les licences à un échantillon non vide.

### SC2 — Le statut ne précède pas le jugement

`rg -n "M1-ASSET-05" Docs/ROADMAP.md` reste `BLOCKED` tant qu'une décision du
propriétaire n'est pas écrite.

## Hors périmètre

Signer l'approbation, régénérer librement les bâtiments, qualifier le jeu de
1.0, modifier ForgeHistory ou fusionner.

---

*Ce lot venait du dépôt Victoria CityLab, où il portait le numéro 009. La fusion a ajouté 200 aux lots de la ville pour que les numéros du moteur et ceux de la ville ne se chevauchent plus.*
