# Lot #702 — La session Unity de l'épreuve de la capitale
Jalon : J4 · Machine : pc · Taille prévue : 210 lignes

## But
Une session Unity joue, comme le joueur, le choix d'une terre dans le cabinet de la carte, un tick, puis le passage à la capitale, et écrit dans un rapport ce qui s'est ouvert ou affiché, sans rien juger.

## Le joueur
Le joueur choisit l'émirat du Zab dans le cabinet de la carte. Au tick suivant, Biskra s'ouvre, avec le panneau « Cellule 10103 ». S'il choisit le duché de Bar, la carte lui dit « Pas encore de kit pour cette terre ». C'est le geste de J4 « passer de la carte à sa ville d'un geste » (`CAP.md`).

C'est un lot de fond pour la preuve de J4. Il donne à l'épreuve de la capitale (#684) sa moitié Unity : la session joue le geste pour de vrai, dans l'éditeur, sur un service lancé à part. Elle ne remplace ni le chargement de la scène ni la caméra. Le verdict, `pc/epreuve_capitale.py`, est le sous-lot 3 de #684. Il lance un service neuf par terre, appelle cette session et compare son rapport au siège servi par `/maison`. C'est lui qui rendra la preuve rouge ou verte.

Dépend de : rien qui manque. #701 est sur la base (c83f42e) : `PassageALaCapitale.PrendreCelluleRemise`, et `DesertRoadTool.Awake` passe la remise. Le cabinet (`CabinetDeCarte`, `LecturePartie`) s'installe tout seul sur `Forge_Carte` en Play. Les aides `internal` de `Lot690` sont sur la base, tout comme `EpreuveChoix` (#651).

## Règle du monde
Sans objet : outil d'épreuve. La session éprouve trois choses déjà sur la base, sans les changer :
- un choix de départ déposé s'applique au tick suivant (« Les intentions du joueur », `jeu/sim/MODELE.md`) ;
- la cellule de la ville est le siège de la maison servie (« Les maisons servies, vue dérivée ») ;
- `cell_id` reste la seule clé.

Rien ne change dans `jeu/`, `Pont/`, `Carte/`, `Desert/` ni `Interface/`.

**Ce que le lot fait.** Un seul fichier de code neuf, `Editor/EpreuveCapitale.cs`, sur le modèle exact d'`Editor/EpreuveChoix.cs` : `[InitializeOnLoad]`, `SessionState`, `EditorApplication.update`, `CitadelEditorBridge.Finish`, un rapport toujours écrit. Le geste est celui des captures `Lot690` (Bar) et `Lot701` (Zab), déjà vertes. La session les reprend sans le chargement additif ni la photo : ici, le passage charge sa scène lui-même, par `SceneManager.LoadScene`, comme dans le jeu.

```
Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveCapitale.Jouer
      -forgeEpreuve <rapport.json> -forgeTerre N [-logFile <journal>]
```

Reprises sans recopie. Dans `EpreuveChoix.cs`, seuls `Argument`, `DossierDeLancement`, `Terre` et `Relever` passent de `static` à `internal static`, sans autre changement. `EpreuveChoix.Recu` (déjà public) sert de type au reçu. Les attentes et lectures sont celles de `Lot690`, déjà `internal` et inchangées : `Jusqua`, `Attendre`, `LecturePrete`, `Dire`, `PousserTick`, `LireMonde`. Chaque attente a une borne de 30 s. Une exception levée par la session devient `defaut`, comme dans `EpreuveChoix.Tick`.

1. **`Jouer()`.** Un `-forgeEpreuve` absent, ou un `-forgeTerre` absent ou qui n'est pas un entier ≥ 1 (`EpreuveChoix.Terre`) : `Debug.LogError("EPREUVE_CAPITALE : …")`, `EditorApplication.Exit(2)`, aucun rapport. Sinon la fonction range le chemin et N dans `SessionState`, ouvre `CarteBuilder.Chemin` et entre en Play, comme le menu « Forge/Interface/Jouer sur la carte ».
2. **Le cabinet.** La session prend l'unique `CarteDessinee` de la scène, son unique `PassageALaCapitale` et son `CabinetDeCarte`. Si l'un manque, elle lève une exception qui le nomme. Elle attend `Lot690.LecturePrete(cabinet.Partie)` : un dépassement lève « cabinet : <`Lot690.Dire`> en 30 s ». `tick_avant` = le tick de `Partie.Monde`. Une fiche d'id N absente de `Partie.Departs` donne « terre N absente de /departs ».
3. **Le choix.** La session appelle `Partie.Choisir(N)`, attend la tâche, puis relève `choix = EpreuveChoix.Relever(Partie.Recu)`. Un reçu non accepté donne le défaut « choix de <nom> refusé : <raison> », sans tick. Elle laisse ensuite passer `2 × PassageALaCapitale.PERIODE_LECTURE_S + 0,25 s`, comme `Lot701` : le passage doit voir le départ avant le tick. Si, pendant ce temps, `passage.Absence`, `TexteAffiche` ou `SceneDemandee` n'est plus nul, elle lève « passage avant le tick : … ».
4. **Le tick.** Un seul `Lot690.PousserTick(port)`, `port` = `carte.port`. Un statut autre que 200 est un défaut qui le cite. La session ne touche jamais `/vitesse`, et ne pousse jamais un second tick.
5. **Ville ou message.** La session attend `passage.TexteAffiche != null || passage.SceneDemandee != null`. Un dépassement lève « après le tick, ni ville ni message en 30 s : passage « <Absence> », cabinet « <Dire> » ».
   - **Un message** : `message_passage` = `passage.TexteAffiche`, tel quel.
   - **Une scène demandée** : la session retient son nom tout de suite, car la carte disparaît au chargement. Elle attend que la scène active porte ce nom et contienne un `DesertRoadTool`. Elle prend l'unique outil et l'unique `PanneauLieu` de cette scène. Elle attend ensuite `outil.TickOuverture >= 0 && panneau.Reconstructions > 0`. Puis : `cellule` = `outil.Cellule`, `tick_ouverture` = `outil.TickOuverture`, `panneau_lieu` = la première ligne de `panneau.TexteAffiche`. Un dépassement lève « ville « <scène> » : plan ou lieu non lu en 30 s : « <outil.Message> » ». `cellule` et le panneau restent alors relevés tels qu'ils sont.
   - La session ne compare rien : ni à 1175, ni au siège, ni au message attendu. Une ville ouverte sur 1175 est un résultat (code 0), relevé tel quel.
6. **`tick_apres`.** `/monde` est relu par `Lot690.LireMonde(port)` après le point 5. Son tick, ou −1 s'il est absent.
7. **Le rapport.** Il est toujours écrit dès que les arguments sont valides. Juste avant l'écriture, `scene_active` = `SceneManager.GetActiveScene().name`, même après un défaut. Puis `JsonUtility.ToJson(rapport, true)`, et `Debug.Log("EPREUVE_CAPITALE <chemin> : scène <scene_active>, cellule <cellule>, tick <tick_ouverture>, panneau « <panneau_lieu> », message « <message_passage> »")`, suivi de « ; défaut : … » s'il y en a un. Code de sortie : **0** quand une ville ouverte ou un message est relevé, **1** quand `defaut` n'est pas vide, **2** pour des arguments fautifs. Le verdict lira tout code non nul comme une épreuve impossible.

```csharp
[Serializable] public class Rapport {
    public long terre = -1, tick_avant = -1, tick_apres = -1, cellule = -1, tick_ouverture = -1;
    public EpreuveChoix.Recu choix = new EpreuveChoix.Recu();
    public string scene_active = "", panneau_lieu = "", message_passage = "", defaut = "";
}
```

Valeurs attendues à la graine 0, service neuf en pause, d'après #651, #688, #690 et #701. Le Zab est le départ 6 : siège Biskra 10103, scène `Forge_Desert_Ville_ksar_des_sept_puits` (`TerresAvecKit.Scenes["seigneurie-6"]`). Bar est le départ 1, sans kit : message `PassageALaCapitale.MESSAGE_SANS_KIT`. La Morée est le départ 3, sans kit.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/EpreuveCapitale.cs
3d/unity/Assets/ForgeLocal3D/Editor/EpreuveCapitale.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/EpreuveChoix.cs
jeu/ville/README.md
docs/mesures/702-session-capitale/rapport-zab.json
docs/mesures/702-session-capitale/rapport-bar.json

Tout autre chemin est interdit. Dans `EpreuveChoix.cs`, seuls quatre mots `internal` s'ajoutent. Budget indicatif : 145 lignes de code, 11 de `.meta` (générée par Unity), 4 dans `EpreuveChoix.cs`, 25 de README, 26 pour les deux rapports.

## Conditions de succès
Toutes se jouent sur le PC, éditeur fermé, depuis la racine du dépôt : `$u = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. `SESSION` = `& $u -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveCapitale.Jouer`, sans `-quit` ni `-nographics`. Le service se lance dans un second terminal, depuis `jeu\` : `py -m sim.service --seed 0 --jours-par-seconde 0` (port 8000, tick 0, en pause). Il s'arrête après chaque essai, pour que le suivant parte d'un monde neuf.

SC1 — **Le Zab.** Service neuf, puis `SESSION -forgeEpreuve docs\mesures\702-session-capitale\rapport-zab.json -forgeTerre 6 -logFile "$env:TEMP\lot702-zab.log"`. La commande rend **0**, et le rapport porte :
- `terre` 6, `tick_avant` 0, `tick_apres` 1 ;
- `choix` = {200, 0, ""} ;
- `scene_active` "Forge_Desert_Ville_ksar_des_sept_puits", `cellule` 10103, `tick_ouverture` 1 ;
- `panneau_lieu` "Cellule 10103 · tick 1", `message_passage` "", `defaut` "".

Le journal contient « EPREUVE_CAPITALE ». Contre-épreuves : SC2 à SC4.

SC2 — **Bar.** Service neuf, puis la commande de SC1 vers `rapport-bar.json` avec `-forgeTerre 1`. La commande rend **0**, et le rapport porte :
- `terre` 1, `tick_avant` 0, `tick_apres` 1 ;
- `choix` = {200, 0, ""} ;
- `scene_active` "Forge_Carte", `cellule` −1, `tick_ouverture` −1, `panneau_lieu` "" ;
- `message_passage` "Pas encore de kit pour cette terre", `defaut` "".

Une session qui confondrait les deux issues, ou qui fixerait l'issue d'avance, rougit entre SC1 et SC2.

SC3 — **La session ne juge rien.** Service neuf, puis la commande de SC1 avec `-forgeTerre 3`, vers un chemin neuf dans `$env:TEMP` (rapport non versé). La commande rend **0**, avec `terre` 3, `scene_active` "Forge_Carte" et le message sans kit : la terre demandée est bien celle qui est jouée. Le codeur montre aussi, dans la PR, une ville ouverte sur 1175 relevée avec le code 0. Pour cela, il remplace un instant, en local et sans la verser, la remise de `DesertRoadTool.Awake` par `null` : le rapport dit `cellule` 1175, `defaut` "". Il restaure le fichier ensuite : `git diff origin/master --stat` ne le nomme pas.

SC4 — **La session impossible le dit.** Aucun service, puis la commande de SC1 vers un chemin neuf. La commande rend **1**, le rapport est écrit, et :
- `defaut` commence par « cabinet : » et finit par « en 30 s » ;
- `choix.statut` vaut −1, `tick_avant` −1 ;
- `scene_active` "Forge_Carte".

SC5 — **Les arguments.** La commande de SC1 sans `-forgeTerre`, puis avec `-forgeTerre Zab`, rend **2** et n'écrit aucun rapport (à vérifier sur un chemin neuf dans `$env:TEMP`). Le journal nomme « EPREUVE_CAPITALE ».

SC6 — **Les rapports versés se relisent**, sur le VPS comme sur le PC :
```bash
python3 - <<'EOF'
import json
d = "docs/mesures/702-session-capitale/"
lire = lambda n: json.load(open(d + n, encoding="utf-8"))
z = lire("rapport-zab.json")
assert (z["terre"], z["tick_avant"], z["tick_apres"], z["cellule"], z["tick_ouverture"]) == (6, 0, 1, 10103, 1), z
assert z["choix"] == {"statut": 200, "tick": 0, "raison": ""}, z["choix"]
assert (z["scene_active"], z["panneau_lieu"], z["message_passage"], z["defaut"]) == ("Forge_Desert_Ville_ksar_des_sept_puits", "Cellule 10103 · tick 1", "", ""), z
b = lire("rapport-bar.json")
assert (b["terre"], b["tick_avant"], b["tick_apres"], b["cellule"], b["tick_ouverture"]) == (1, 0, 1, -1, -1), b
assert b["choix"] == {"statut": 200, "tick": 0, "raison": ""}, b["choix"]
assert (b["scene_active"], b["panneau_lieu"], b["message_passage"], b["defaut"]) == ("Forge_Carte", "", "Pas encore de kit pour cette terre", ""), b
print("ok")
EOF
```
Le script sort `ok`. Contre-épreuve : sur une copie de `rapport-zab.json` où `cellule` vaut 1175, le même script lève `AssertionError`. Le codeur le montre dans la PR, sans verser la copie.

SC7 — **Rien d'autre ne bouge.**
- Les tests EditMode restent verts : `& $u -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -testResults "$env:TEMP\lot702-tests.xml"` rend 0.
- `git diff -U0 origin/master -- 3d/unity/Assets/ForgeLocal3D/Editor/EpreuveChoix.cs` ne montre que quatre lignes, où seul `internal` s'ajoute.
- `git diff --check`, `--name-only` et `git ls-files --others --exclude-standard` ne nomment que le Périmètre, sous 300 lignes.

Contre-épreuve : un changement dans `Lot690.cs`, `Lot701.cs`, `Pont/`, `Desert/`, `Interface/` ou `jeu/` refuse la livraison.

SC8 — **Le README.** Dans `jeu/ville/README.md`, après « La session du choix de la terre », une courte section « La session de l'épreuve de la capitale ». Elle donne :
- la commande ;
- ce que fait la session : cabinet, choix, un tick, ville ou message, sans chargement remplacé ;
- les champs du rapport et les codes 0 / 1 / 2 ;
- le lancement du service à la main ;
- les liens vers les deux rapports versés.

Elle dit que le jugement est celui de `pc/epreuve_capitale.py`, à venir.

SC9 — `python3 -m pytest jeu -q` passe en entier sur le VPS.

## Hors périmètre
- Le verdict : `pc/epreuve_capitale.py` (#684, sous-lot 3), qui lance le service, appelle la session et lit le siège attendu dans `/maison`.
- Toute photo, tout chargement additif, toute caméra recopiée : c'est le travail des captures 690 et 701, qui restent telles quelles.
- `PassageALaCapitale`, `DesertRoadTool`, `PanneauLieu`, `CabinetDeCarte`, `LecturePartie`, les scènes et `jeu/sim/` restent inchangés. Si l'un d'eux semble devoir changer, le codeur le dit dans la PR plutôt que de l'écrire.
- Le retour de la ville à la carte et l'horloge qui suit la vue (#410).

## Photo
sans objet : outil d'épreuve. La session joue le geste en Play sans rien capturer, et rien de ce que voit le joueur ne change. Biskra ouverte depuis la carte est la photo du lot 701 (`zab-biskra-depuis-la-carte`), et le message de Bar celle du lot 690 (`bar-sans-kit`).
