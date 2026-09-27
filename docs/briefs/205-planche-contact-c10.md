# Brief 205 — Planche de contact C-10

## But

Produire la planche 96 px fidèle aux 24 FBX publiés et un protocole court pour
que le propriétaire rende le jugement artistique C-10.

## Règle du monde

Une mesure technique ne remplace pas la lecture visuelle. L'exécutant prépare
la preuve ; le propriétaire accepte, demande une reprise ou refuse.

## Périmètre

- `Tools/AssetFactory/clay_review.py`
- `AssetFactory/Reports/QA/factory_review_board.png`
- `AssetFactory/Manifests/building_pilot.json`
- `Docs/ASSET_FACTORY_ROADMAP.md`

## Conditions de succès

### SC1 — La planche représente le lot courant

`py -3 Tools/AssetFactory/clay_review.py --help` expose la commande de
régénération ; le rapport relie les 24 cases aux hashes FBX courants.

### SC2 — Le jugement reste humain

`rg -n "C-10|M1-ASSET-07" Docs/ROADMAP.md Docs/ASSET_FACTORY_ROADMAP.md`
montre une porte à juger et aucune promotion automatique à `DONE`.

## Hors périmètre

Juger à la place du propriétaire, changer un seuil, ajouter des triangles,
modifier ForgeHistory ou fusionner.

---

*Ce lot venait du dépôt Victoria CityLab, où il portait le numéro 005. La fusion a ajouté 200 aux lots de la ville pour que les numéros du moteur et ceux de la ville ne se chevauchent plus.*
