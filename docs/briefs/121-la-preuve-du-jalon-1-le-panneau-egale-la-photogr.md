# Lot #121 — La preuve du jalon 1 : le panneau égale la photographie
Jalon : J1 · Machine : pc · Taille prévue : 290 lignes

## But
Sur le PC, `py pc\epreuve_jalon1.py --sortie <dossier>` fait lancer le service de `sim/` (graine S, tick N) par la capture Unity, ouvre la scène du désert en Play (batch), relit le texte que le panneau affiche et le compare, nombre par nombre, à la photographie `py -m sim --ticks N --seed S --snapshot-json` de la même cellule. Elle rend 0 sur égalité exacte et échoue quand le service est décalé d'un tick. La capture que la chaîne publie au journal montre désormais le panneau avec les vrais chiffres de `sim/`. C'est la preuve du jalon J1 (CAP.md) : avec ce lot, le jalon est atteint.

## Règle du monde
Sans objet : c'est un lot d'outil, un regard (CAP.md, jalon 1 : « Ce que le jalon change dans le monde : rien »). Il ne décide aucun nombre et ne touche ni le moteur, ni `service.py`, ni `MODELE.md`. Niveau de fidélité : sans objet.

Ce qu'il respecte de [`jeu/sim/MODELE.md`](../../jeu/sim/MODELE.md) et d'AGENTS.md :
- **« La base de temps »** : le monde au tick N se joue par le seul moteur. La photographie vient de `py -m sim --ticks N --seed S`, et le service de `--seed S` poussé par `POST /tick?n=N`. Les deux sont égaux par construction (#116, #117). La date attendue est `constants.date_de_tick(N)`, jamais recalculée à la main.
- **« Le panier de marchandises »** et **« Absence contre zéro »** : le panier se compare clé à clé, dans les deux sens. Une marchandise de la photographie qui manque au panneau, ou l'inverse, est un écart. « absente du panier » n'est pas `0`.
- **`cell_id` est la seule clé spatiale** : la cellule par défaut est celle de `pc\Jouer.cmd` (`jeu/ville/cellule_du_desert.py::charger_et_choisir`), passée à Unity en `-forgeCell`.
- **Une absence se déclare** (§ 4) : un panneau qui dit « service absent » ou « lieu illisible » n'est jamais lu comme des zéros ; l'épreuve échoue en le citant.

**Dépendance.** Ce lot s'appuie sur `pc/jouer.py` (#120, commit `89d6754`), ainsi que sur `PanneauLieu.cs` et `ClientLieu.cs` (#184, #186). Si la branche du lot ne contient pas `89d6754`, le codeur n'écrit rien et répond « bloqué : #120 absent de la branche ».

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/ForgeCapture.cs
pc/epreuve_jalon1.py
jeu/ville/tests/test_epreuve_jalon1.py
jeu/ville/README.md
docs/mesures/121-preuve-du-jalon-1/panneau.png
docs/mesures/121-preuve-du-jalon-1/panneau.txt
docs/mesures/121-preuve-du-jalon-1/verdict.txt
docs/mesures/121-preuve-du-jalon-1/verdict-decalage-1.txt

Précisions. Tout littéral numérique autre que 0, 1 et -1 est une constante nommée. En Python, la bibliothèque standard seule.

- **`ForgeCapture.cs`** (≈ +75 lignes). Il reste la seule entrée que la chaîne appelle (`atelier/pc.py` n'est pas modifié) et gagne le service :
  1. **Les arguments.** `-forgeSeed` vaut `GRAINE_PAR_DEFAUT = 0` par défaut et `-forgeTicks` vaut `TICKS_PAR_DEFAUT = 30` (les 30 jours de la carte du journal). Une valeur absente derrière l'argument, non entière ou négative donne `Debug.LogError`, qui nomme l'argument et la valeur, puis `EditorApplication.Exit(2)`, sans service et sans Play. Jamais de repli silencieux.
  2. **Le port.** La constante `PORT_SERVICE = 8000` porte le commentaire « celui de `PanneauLieu.DEFAULT_SERVICE_PORT` et de `jeu/sim/service.py` ». Si une connexion TCP à `127.0.0.1:8000` aboutit avant le lancement, `LogError` dit « le panneau lirait un autre monde », puis `Exit(3)`, sans Play.
  3. **L'interpréteur.** Il se résout une fois par `py -3 -c "import sys;print(sys.executable)"`, et c'est ce chemin qu'on lance (tuer le lanceur `py` ne tuerait pas forcément son enfant). Il lance ensuite `<python> -m sim.service --seed S --port 8000 --jours-par-seconde 0`, avec `WorkingDirectory` = `<dépôt>/jeu`, dérivé de `Application.dataPath`, et `PYTHONIOENCODING=utf-8`. Il attend la ligne `service prêt sur 127.0.0.1:8000` au plus `DELAI_SERVICE_PRET_S = 60` s, puis fait `POST /tick?n=N` quand N ≥ 1 (`HttpClient`, délai `DELAI_TICKS_S = 300`). Le pid se garde dans `SessionState` (le Play recharge le domaine) et s'écrit dans `<forgeCaptures>/service.pid`. Enfin `Debug.Log("CAPTURE_SERVICE graine S tick N pid P")`.
  4. **L'échec du service.** Si `py` est introuvable, si le service meurt, si le délai est dépassé ou si `/tick` rend autre chose que 200, `LogError("CAPTURE : service absent : <cause>")` est émis, le processus est tué s'il vit, et la capture continue : le panneau dira lui-même « service absent ». Une capture de chaîne qui compile reste utile.
  5. **L'attente du panneau.** Après les `Attente` images existantes, si la scène a un objet racine « Panneau du lieu », la capture attend que son `UnityEngine.UI.Text` (`GetComponentInChildren`) ne commence plus par « service absent : en attente ». L'attente dure au plus `DELAI_PANNEAU_S = 15` s de temps réel. Puis la capture photographie comme avant et écrit `<scène>.panneau.txt` (UTF-8, sans BOM), qui contient **exactement** `Text.text` : ce que l'écran montre. Sans panneau, rien ne change.
  6. **L'arrêt du service.** Le service est tué (par son pid) avant **chaque** `CitadelEditorBridge.Finish` ou `Exit`, y compris dans le `catch`.
  L'assemblage `Forge.Pont` n'est pas référencé : on lit le `Text` par son objet, pas `PanneauLieu`.
- **`pc/epreuve_jalon1.py`** (≈ 120 lignes). Il charge `pc/jouer.py` par `importlib.util.spec_from_file_location`, pour `_repond` et `_regle`, sans le modifier. Sa ligne de commande : `py pc\epreuve_jalon1.py --sortie D [--seed S] [--ticks N] [--cellule C] [--decalage K] [--unity CHEMIN]`.
  1. **Les défauts.** `--seed 0`, `--ticks 30`, `--decalage 0` (un entier ≥ 0) ; `--cellule` absent donne `charger_et_choisir()`. `--unity` absent vaut `C:\Program Files\Unity\Hub\Editor\<m_EditorVersion>\Editor\Unity.exe`, lu dans `3d/unity/ProjectSettings/ProjectVersion.txt`. S'il est introuvable, le script sort à 2 en le nommant.
  2. **Le port.** Si le port 8000 répond déjà, il sort à 2 en nommant le port, sans rien lancer.
  3. **La photographie.** `sys.executable -m sim --ticks N --seed S --snapshot-json D/photo-tick-N.json` (`cwd` = `jeu/`). Une cellule C absente de la photographie donne une sortie à 2 qui nomme C.
  4. **Unity.** `<unity> -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -logFile D/unity.log -forgeCaptures D -forgeCell C -forgeSeed S -forgeTicks N+K`, sans `-quit`, délai `DELAI_UNITY_S = 1800`. Si le code est non nul ou le délai dépassé, il sort à 2 avec les 30 dernières lignes du journal d'Unity.
  5. **L'arrêt.** Unity fermé, le port 8000 doit refuser la connexion. S'il répond encore, il sort à 2 en citant le pid de `D/service.pid` (« service laissé ouvert »).
  6. **Les fichiers.** `D/Forge_Desert_Ville_ksar_des_sept_puits.png` doit être non vide et `…panneau.txt` doit être présent ; sinon il sort à 2 en les nommant.
  7. **La comparaison.** `lire_panneau(texte) -> dict` donne `tick`, `annee`, `jour`, `population`, `stocks` (un dictionnaire ; la nourriture n'y entre que si sa ligne porte un nombre), `hunger_ticks` et `food_deficit_kg`. Elle lève `ValueError` sur un texte vide, « service absent », « lieu illisible » ou une ligne inconnue, en citant le début du texte. `comparer(panneau, photographie, cellule) -> list[str]` compare par `==` après `int()` ou `float()` : le format `"R"` du C#, `0`, `1E+15` sont relus. Elle couvre le tick contre `photo["tick"]`, la date contre `date_de_tick(tick de la photo)`, les quatre champs d'état et le panier dans les deux sens. Chaque écart nomme le champ, la valeur du panneau et celle de la photographie.
  8. **Le verdict.** Il s'écrit dans `D/verdict.txt` : une première ligne `ÉGALITÉ` ou `ÉCART`, la graine, les ticks, la cellule et le décalage, puis une ligne par champ. La sortie vaut 0 sur égalité, 1 sur écart.
- **`jeu/ville/README.md`** : une section « L'épreuve du jalon 1 », qui donne la commande, les codes 0/1/2, la contre-épreuve `--decalage 1` et le fait que la capture de la chaîne lance désormais le service. Elle ne recopie aucun nombre du monde.
- **`docs/mesures/121-preuve-du-jalon-1/`** : les fichiers de la vraie épreuve jouée sur le PC. `panneau.png` et `panneau.txt` sont copiés de la sortie sans décalage, avec `verdict.txt`, et `verdict-decalage-1.txt` vient de la sortie `--decalage 1`. Le PNG passe par LFS (`.gitattributes`) ; ni la photographie de 2 Mo ni `unity.log` ne sont versionnés.

## Conditions de succès

**SC1 — la comparaison accepte l'égal et refuse le décalé (VPS ou PC).**
```
python3 -m pytest jeu/ville/tests/test_epreuve_jalon1.py -q
```
Le test charge `pc/epreuve_jalon1.py` par son chemin. Il produit, par la vraie commande (`sys.executable -m sim --ticks N --seed 0 --snapshot-json`), les photographies aux ticks 3 et 4. La cellule est `charger_et_choisir()`. Le texte du panneau se construit dans le test au format de `PanneauLieu.Decrire` (sept lignes et plus, la nourriture d'abord, puis le panier par ordre ordinal), **à partir des valeurs de la photographie**, jamais recopié à la main. Cas :
- le panneau de la photographie 3 contre la photographie 3 donne `[]`. La cellule doit avoir au moins une marchandise ; sinon le test échoue (un échantillon vide échoue) ;
- **contre-épreuve du décalage** : le panneau de la photographie 4 contre la photographie 3 donne des écarts, dont `tick` et au moins un champ du monde (population, panier, faim ou dette). Si la cellule ne bouge pas entre 3 et 4, le cas échoue en le disant : la preuve serait aveugle ;
- **les nombres comptent, pas seulement le tick** : les nombres de la photographie 4 sous le tick et la date de la 3 donnent des écarts, et aucun ne porte sur `tick` ni sur la date ;
- une marchandise retirée du texte, une marchandise en trop, ou « Nourriture : absente du panier » alors que la photographie en a, donnent chacune un écart qui nomme la marchandise. La dette `0.0` écrite `0` (la forme du C#) n'est pas un écart ;
- `lire_panneau` sur `""`, sur « service absent : 127.0.0.1:8000 — … » et sur « lieu illisible : … » lève `ValueError`. Jamais un dictionnaire de zéros ;
- une cellule absente de la photographie donne une `ValueError` qui nomme son `cell_id` ;
- **les libellés sont ceux du panneau** : chaque libellé que lit `lire_panneau` (« Habitants : », « Faim : », « ticks de manque », « Dette de nourriture : », « absente du panier », « Date : jour ») figure dans le texte de `PanneauLieu.cs` ; `PORT_SERVICE`, lu par expression régulière dans `ForgeCapture.cs`, égale `sim.service.DEFAULT_SERVICE_PORT`. Un fichier ou une constante introuvable donne un échec qui le nomme.

**SC2 — Unity compile.** Le workflow `unity` (poussée sur la branche) est vert, sans aucune `error CS`.

**SC3 — l'épreuve sur le PC : égalité, puis décalage qui échoue.**
Depuis `D:\Forge` (le chantier du lot) :
```
py pc\epreuve_jalon1.py --sortie <temp>\j1
py pc\epreuve_jalon1.py --sortie <temp>\j1-decale --decalage 1
```
- Le premier sort à **0**, et `verdict.txt` commence par `ÉGALITÉ` et nomme la cellule du désert, la graine 0 et le tick 30.
- Le second sort à **1**, et son verdict nomme l'écart sur `tick` et au moins un champ du monde. S'il sortait à 0, l'épreuve serait fausse.
- Pour les deux, le port 8000 refuse la connexion ensuite (`curl http://127.0.0.1:8000/horloge` échoue).
- Contre-épreuve de l'absence, jouée à la main et dite dans la PR : avec `jeu\` renommé le temps d'un essai, l'épreuve sort non nulle et le panneau capturé dit « service absent ».
- La PR recopie les deux verdicts et le fichier `docs/mesures/121-preuve-du-jalon-1/panneau.txt`.

**SC4 — la capture montre les vrais chiffres, et la chaîne la publie (PC).**
**Le codeur ouvre `panneau.png`** : le panneau y est entier, lisible, en haut à gauche. Chacun de ses nombres est égal à ceux de `panneau.txt` et de `verdict.txt`, et aucun ne dit « service absent ». Une capture sans panneau, ou illisible, échoue même si tout est vert. La capture que la chaîne prend ensuite (sans `-forgeCell`, donc la cellule 1175 au tick 30) doit elle aussi montrer des nombres. C'est elle qui entre au journal. Le compte rendu dit ce que les deux images montrent.

**SC5 — rien d'autre ne bouge.**
```
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC (pc\Tests.cmd)
py pc\verifier_lanceurs.py
git diff --name-only origin/master...HEAD
```
La suite du jeu reste verte, `test_lanceur_jouer.py`, `test_cellule_du_desert.py`, `test_contrat_cell_id.py` et `test_no_hardcoded.py` compris. Le vérificateur des lanceurs sort à 0. Le diff ne nomme que des chemins du périmètre (plus ce brief).

## Hors périmètre
- modifier `PanneauLieu.cs`, `ClientLieu.cs`, `LecteurJson.cs`, leurs tests, les asmdef ou la scène ; ajouter `-forgePort` au panneau ;
- modifier `pc/jouer.py`, `pc/Jouer.cmd`, `pc/verifier_lanceurs.py`, `pc/Tests.cmd`, ou ajouter un lanceur `.cmd` ;
- modifier `jeu/sim/` (le service, le moteur, `snapshot_export.py`, `MODELE.md`) ou `jeu/data/` ;
- changer la manière dont la chaîne appelle la capture ou publie ses images (`atelier/pc.py`, `atelier/captures.py`) : la capture gagne le service de son côté ;
- brancher l'épreuve ou les tests EditMode dans un workflow ; le build `Forge.exe` ;
- la vitesse, la pause et le choix de la cellule depuis Unity ;
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
