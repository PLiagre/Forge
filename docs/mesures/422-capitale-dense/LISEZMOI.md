# Capitale dense, mesure d'avant (lot 959)

Ce qui est mesuré : le temps d'image de Biskra dense (cellule 10103, 600 maisons, 80 passants, un chantier de maison, soir à 19,6 h) sur quatre vues, avant toute optimisation. Le banc prend 300 images après 60 de chauffe, en 1920 × 1080, rendu vrai, sans vSync.

Commande P, jouée depuis la racine le 01/11/2026, commit `36169e441a8034a0bcf5731420fd7b204afdfb9a` :

`& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 959 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forgeCaptures '3d/unity/Temp/lot959-photo' -logFile '3d/unity/Temp/lot959-photo.log'`

Machine du rapport : Intel(R) UHD Graphics 770, Direct3D11, 13th Gen Intel(R) Core(TM) i7-13700K, 32522 Mo, Unity 6000.0.43f1, qualité Ultra.

| vue | médiane (ms) | P95 (ms) | max (ms) |
| --- | --- | --- | --- |
| survol | 138,2 | 143,9 | 148,2 |
| rue | 127,1 | 134,2 | 139,7 |
| place | 63,2 | 74,6 | 85,3 |
| chantier | 42,0 | 44,5 | 52,7 |

Contre-épreuve C2, sans fumée, sans lampe et sans étal : médianes survol 26,5 ms, rue 44,0 ms, place 39,1 ms, chantier 22,5 ms.

mesure d'avant les optimisations : rien ne lit `OptimisationsDeLaVille.Actives` à ce commit.

Les sous-lots 4 (maisons et enceinte regroupées) et 5 (LOD des fumées et des lampes) de #422 accélèrent cette ville ; le sous-lot 6 la rejoue pour prouver un 95e centile sous 16,7 ms.
