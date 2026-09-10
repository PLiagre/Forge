# Brief 208 — Preuve Unity Windows

## But

Faire exécuter l'EditMode Unity 6000.0.43f1 sur le SHA exact du kit courant et
consigner le XML NUnit et son résumé rouge/vert.

## Règle du monde

Une affirmation Unity n'existe que si l'éditeur a importé le commit exact. Une
absence de runner, de LFS ou de résultat est un échec déclaré.

## Périmètre

- `.github/workflows/unity-windows.yml`
- `Tools/run_unity_windows_worker.ps1`
- `Tools/unity_nunit.py`
- `Docs/VALIDATION.md`

## Conditions de succès

### SC1 — Le worker reçoit une branche autorisée

`py -3 -m unittest Tools.tests.test_unity_windows_worker -v` refuse un SHA
invalide, un XML absent, vide ou rouge.

### SC2 — La preuve est liée au commit

`py -3 Tools/unity_nunit.py Logs/editmode.xml --summary Logs/unity-windows-summary.json`
rend 100 % des tests réussis et la validation cite le SHA et le run.

## Hors périmètre

PlayMode graphique, modification opportuniste d'un test rouge, écriture dans
ForgeHistory et fusion.

---

*Ce lot venait du dépôt Victoria CityLab, où il portait le numéro 008. La fusion a ajouté 200 aux lots de la ville pour que les numéros du moteur et ceux de la ville ne se chevauchent plus.*
