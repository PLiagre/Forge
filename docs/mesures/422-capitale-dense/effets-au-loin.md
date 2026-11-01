# Capitale dense, les fumées et les lampes au loin (lot 961)

La ville dense de #959 (Biskra, cellule 10103, 600 maisons, soir à 19,6 h), avec `EffetsAuLoin` : les 32 lampes les plus proches de la caméra restent allumées, les fumées à plus de 60 m sont en pause, et celles hors de l'image ne sont plus simulées. Même banc : 300 images après 60 de chauffe, 1920 × 1080, rendu vrai.

Jouées depuis la racine le 01/11/2026, sur la branche du lot partie de `f0db9ab06a2199dee2559d9a46be7ba70fd2e368` ; machine : Intel(R) UHD Graphics 770, Direct3D11, 13th Gen Intel(R) Core(TM) i7-13700K, 32522 Mo, Unity 6000.0.43f1, qualité Ultra.

Commande P (`effets-au-loin.json`) : `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 961 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forgeCaptures '3d/unity/Temp/lot961-photo' -logFile '3d/unity/Temp/lot961-photo.log'`

Commande C (`effets-au-loin-sans-optimisations.json`) : `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 961 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forgeSansOptimisations -forgeCaptures '3d/unity/Temp/lot961-sans-optimisations' -logFile '3d/unity/Temp/lot961-sans-optimisations.log'`

| vue | sans optimisations (ms) | avec (ms) | rapport |
| --- | --- | --- | --- |
| survol | 125,9 | 82,7 | 0,66 |
| rue | 128,4 | 87,3 | 0,68 |
| place | 83,5 | 51,8 | 0,62 |
| chantier | 45,5 | 32,3 | 0,71 |

Rappel, médianes d'`avant.json` (#959) : survol 138,2 ms, rue 127,1 ms, place 63,2 ms, chantier 42,0 ms.

Ce lot promet un gain, pas un seuil : le sous-lot 6 de #422 rejoue les quatre vues pour prouver un 95e centile sous 16,7 ms.
