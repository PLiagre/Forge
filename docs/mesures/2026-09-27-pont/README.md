# Mesure du pont — 27 septembre 2026

Mesure **jetable** : elle a servi une fois, à trancher l'architecture du pont
entre `sim/` et Unity (voir [CAP.md](../../../CAP.md), jalon 1). Ces fichiers ne
sont pas maintenus ; ils restent pour qu'on puisse rejouer la mesure et vérifier
les chiffres.

| fichier | rôle |
|---|---|
| `service_pont.py` | `sim/` comme service HTTP local (bibliothèque standard) : `/lieu`, `/monde`, `/tick`, `/intention` |
| `sous_ensemble.py` | coûts côté Python (tick, commerce, sous-ensemble par cellule, tailles), et entrées du portage C# |
| `MesurePont.cs` | client dans un projet Unity : HttpClient, UnityWebRequest, et le sous-ensemble porté en C# |
| `mesures-python.json`, `mesures-unity.json` | résultats bruts du 27 septembre 2026 |

Machine : i7-13700K, Windows 11, Python 3.13, Unity 6000.0.43f1 (éditeur en
batch, runtime Mono).

## Rejouer

```powershell
py docs/mesures/2026-09-27-pont/sous_ensemble.py --racine . --sortie mesures-python.json --entrees-cs entrees-cs.json
Start-Process py -ArgumentList "docs/mesures/2026-09-27-pont/service_pont.py --racine . --port 8765"
# projet Unity vide : Unity.exe -batchmode -quit -createProject C:\tmp\mesure
# copier MesurePont.cs dans Assets/Editor/, puis :
$env:MESURE_URL="http://127.0.0.1:8765"; $env:MESURE_ENTREES="entrees-cs.json"; $env:MESURE_SORTIE="mesures-unity.json"
& "C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe" -batchmode -nographics -projectPath C:\tmp\mesure -executeMethod MesurePont.Mesurer -quit -logFile mesure.log
```

Le sous-ensemble C# refait l'arithmétique de `sim/engine.py` (production,
consommation, faim, mortalité, natalité) à la manière d'un portage : facteurs
lus une fois, tableaux. Il ne prétend pas à la parité bit à bit ; il donne un
ordre de grandeur de vitesse à langage égal.
