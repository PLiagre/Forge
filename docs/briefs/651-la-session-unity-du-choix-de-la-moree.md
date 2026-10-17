# Lot #651 — La session Unity du choix de la Morée
Jalon : J3 · Machine : pc · Taille prévue : 250 lignes

## But
Une session Unity joue, comme le joueur, le clic sur une terre de la carte de 1400 puis le clic sur une autre avant tout tick, et écrit dans un rapport les deux reçus du monde et les deux textes du panneau du choix, sans rien juger.

## Le joueur
Le joueur clique sur la Morée sur la carte de 1400, puis sur une autre terre, et voit le refus du monde : sa terre est prise, et le monde ne le laisse pas en changer en douce. C'est un lot de fond pour le geste « le joueur choisit sa terre sur la carte » (#404, jalon J3) : il donne à l'épreuve du choix de la Morée (#615) sa moitié Unity. Le script qui lance le service, appelle cette session et juge son rapport contre le monde est l'autre sous-lot de #615 ; c'est lui qui rendra la preuve rouge ou verte.

## Règle du monde
Sans objet : outil d'épreuve. La session éprouve deux règles déjà sur la base sans les changer : un choix de départ déposé est appliqué au tick suivant, et un second choix est refusé dès que le premier attend (`jeu/sim/intentions.py`, `deposer_intention` : « départ déjà choisi : seigneurie-N », 409 par `jeu/sim/service.py`). Rien ne change dans `jeu/sim/` ni dans `3d/unity/Assets/ForgeLocal3D/Pont/` ou `Carte/`.

**Ce que le lot fait.** Un seul fichier de code, `Editor/EpreuveChoix.cs`, sur le modèle exact d'`Editor/EpreuveCarte.cs` (`[InitializeOnLoad]`, `SessionState`, `EditorApplication.update`, `CitadelEditorBridge.Finish`). Le geste est celui de la capture `Editor/Captures/Lot613.cs`, déjà verte : la reprendre, pas la réinventer.

```
Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveChoix.Jouer
      -forgeEpreuve <rapport.json> -forgeTerre N -forgeSecondeTerre M [-logFile <journal>]
```

1. **`Jouer()`** lit les trois arguments. Un `-forgeEpreuve` absent, ou un `-forgeTerre` / `-forgeSecondeTerre` absent ou qui n'est pas un entier ≥ 1 (culture invariante) : `Debug.LogError("EPREUVE_CHOIX : …")` et `EditorApplication.Exit(2)`, aucun rapport. Sinon il range chemin, N et M dans `SessionState`, ouvre `CarteBuilder.Chemin` et entre en Play. N et M égaux ne sont pas refusés : la session ne juge rien.
2. **La carte.** `FindFirstObjectByType<CarteDessinee>()` ; `ParcoursDeCarte`, `CommandesDuTemps`, `SurvolDeCarte` passent en `automatique` (aucune souris ni touche lue) ; un seul `ReperesDeDepart` sur la carte (`GetComponents`), sinon défaut.
3. **Les six repères.** Attendre, 30 s au plus, `!reperes.LectureEnVol && reperes.ReperesPoses == 6`. Au-delà : défaut « repères : <n> posés sur 6 en 30 s : « <reperes.TexteAffiche> » » (le texte d'absence de `ReperesDeDepart`, tel quel).
4. **Les terres servies.** Lire `/departs` hors du fil principal (`Task.Run`, `ClientDeparts(reperes.port, ClientDeparts.DelaiMinimal)` dans un `using`, comme `Lot613`) ; `tick_avant` = son tick. Une lecture absente, ou une fiche d'id N ou M absente : défaut qui le nomme (« terre N absente de /departs »).
5. **Le clic sur N.** `carte.transform.Find("Repères des terres de départ/Repère " + fiche.Nom)` ; `ecran = carte.camera.WorldToScreenPoint(repere.position)` ; un point hors de `[0, Screen.width) × [0, Screen.height)` ou derrière la caméra : défaut « repère <nom> hors de l'écran ». Puis `survol.Survoler(ecran); survol.Cliquer(ecran);` — par `SurvolDeCarte`, jamais par `reperes.Choisir` directement. Si `!reperes.ChoixEnVol || reperes.TerreDuChoix?.Id != N` : défaut « clic sur <nom> : aucun dépôt, terre survolée « <Survolee?.Nom> » ». Attendre `!reperes.ChoixEnVol`, 30 s au plus. Relever `premier` du reçu (`reperes.RecuDuChoix`) et `premier_texte` = `reperes.ChoixAffiche ?? ""`.
6. **Le clic sur M**, aussitôt, de la même façon, sans tick entre les deux : la session ne touche jamais `/tick` ni `/vitesse`. Si le service avait avancé, #614 aurait posé le domaine et caché les repères : `Choisir` ne dépose rien, et la session le dit par le défaut du point 5. Relever `second` et `second_texte`.
7. **`tick_apres`** : `/departs` relu après le second reçu (−1 s'il ne répond pas).
8. **Le rapport** est toujours écrit (`JsonUtility.ToJson(rapport, true)`, comme `EpreuveCarte`), puis `Debug.Log("EPREUVE_CHOIX <chemin> : premier <statut> « <raison> », second <statut> « <raison> »")`. Code de sortie : **0** quand les deux reçus sont relevés (quels qu'ils soient), **1** quand `defaut` n'est pas vide (session impossible, ou exception : `defaut` = son message, comme `EpreuveCarte`). Le script juge de #615 lira tout code non nul comme une épreuve impossible.

Le relevé d'un reçu, par une fonction `static Recu Relever(RecuIntention r)` :
- accepté : `statut` 200, `tick` = `AppliqueeAuTick`, `raison` "" ;
- refusé : `statut` = `Statut` (400 ou 409), `tick` −1, `raison` = `Erreur` ;
- absent : `statut` −1, `tick` −1, `raison` = `Absence`.

Le rapport, `[Serializable]`, champs initialisés (un champ jamais rempli sort à sa valeur de départ) :

```csharp
[Serializable] public class Recu { public int statut = -1; public long tick = -1; public string raison = ""; }
[Serializable] public class Rapport {
    public long terre = -1, seconde_terre = -1, tick_avant = -1, tick_apres = -1; public int reperes = -1;
    public Recu premier = new Recu(), second = new Recu();
    public string premier_texte = "", second_texte = "", defaut = "";
}
```

`reperes` = `reperes.ReperesPoses` au moment où l'attente du point 3 finit (réussie ou non).

Mesuré sur master 0c6fbc8, graine 0, service neuf en pause : `/departs` sert au tick 0 les ids 1 à 6 dans l'ordre (1 Duché de Bar, 3 Despotat de Morée, 6 Émirat du Zab) ; la capture Lot613 obtient la Morée acceptée au tick publié puis un refus 409 « départ déjà choisi : seigneurie-3 ». Les textes du panneau sont ceux de `ReperesDeDepart.DireLeChoix`, inchangé.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/EpreuveChoix.cs
3d/unity/Assets/ForgeLocal3D/Editor/EpreuveChoix.cs.meta
jeu/ville/README.md
docs/mesures/651-session-choix-moree/rapport-normal.json
docs/mesures/651-session-choix-moree/rapport-deja-choisi.json
docs/mesures/651-session-choix-moree/rapport-sans-service.json

## Conditions de succès
Sur le PC, éditeur fermé, depuis la racine du dépôt. Le service se lance dans un second terminal, depuis `jeu\` : `py -m sim.service --seed 0 --jours-par-seconde 0` (port 8000, tick 0, en pause), et s'arrête après chaque essai pour que le suivant parte d'un monde neuf.

SC1. **La session normale.** Service neuf, puis
`Unity.exe -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveChoix.Jouer -forgeEpreuve docs\mesures\651-session-choix-moree\rapport-normal.json -forgeTerre 3 -forgeSecondeTerre 1 -logFile "$env:TEMP\lot651.log"`
rend **0**, et le rapport porte : `terre` 3, `seconde_terre` 1, `reperes` 6, `tick_avant` 0, `tick_apres` 0, `defaut` "" ; `premier` = {200, 0, ""} ; `second` = {409, −1, "départ déjà choisi : seigneurie-3"} ; `premier_texte` = « Terre choisie : Despotat de Morée\nLe monde l'applique au tick suivant (après le tick 0). » ; `second_texte` = « Choix refusé pour Duché de Bar :\ndépart déjà choisi : seigneurie-3 ». Contre-épreuves : SC2 et SC3.

SC2. **La session ne juge rien.** Service neuf ; avant Unity, déposer à la main le choix de Bar :
`py -c "import json, urllib.request as u; print(u.urlopen(u.Request('http://127.0.0.1:8000/intention', data=json.dumps({'type': 'choisir_depart', 'seigneurie': 1}).encode(), method='POST')).read())"`
(reçu `{"acceptee": true, "appliquee_au_tick": 0}`), puis la commande de SC1 vers `rapport-deja-choisi.json`. Unity rend **0** (pas 1 : deux refus sont un résultat, pas une panne), `defaut` "", les deux reçus {409, −1, "départ déjà choisi : seigneurie-1"}, `premier_texte` = « Choix refusé pour Despotat de Morée :\ndépart déjà choisi : seigneurie-1 ». Une session qui jugerait ou qui écrirait un reçu attendu au lieu du reçu servi rougit ici.

SC3. **La session impossible le dit.** Aucun service ; la commande de SC1 vers `rapport-sans-service.json` rend **1**, le rapport est écrit, `defaut` commence par « repères : 0 posés sur 6 » et cite le texte d'absence affiché, `premier.statut` −1, `premier_texte` "".

SC4. **Les arguments.** La commande de SC1 sans `-forgeTerre`, puis avec `-forgeTerre Morée`, rend **2** et n'écrit aucun rapport (vérifier avec un chemin neuf dans `$env:TEMP`) ; le journal nomme « EPREUVE_CHOIX ».

SC5. **Les rapports versés se relisent**, sur le VPS comme sur le PC :
```bash
python3 - <<'EOF'
import json
d = "docs/mesures/651-session-choix-moree/"
lire = lambda n: json.load(open(d + n, encoding="utf-8"))
n = lire("rapport-normal.json")
assert (n["terre"], n["seconde_terre"], n["reperes"], n["tick_avant"], n["tick_apres"], n["defaut"]) == (3, 1, 6, 0, 0, ""), n
assert n["premier"] == {"statut": 200, "tick": 0, "raison": ""}, n["premier"]
assert n["second"] == {"statut": 409, "tick": -1, "raison": "départ déjà choisi : seigneurie-3"}, n["second"]
assert n["premier_texte"] == "Terre choisie : Despotat de Morée\nLe monde l'applique au tick suivant (après le tick 0).", n["premier_texte"]
assert n["second_texte"] == "Choix refusé pour Duché de Bar :\ndépart déjà choisi : seigneurie-3", n["second_texte"]
p = lire("rapport-deja-choisi.json")
assert p["defaut"] == "" and p["premier"] == p["second"] == {"statut": 409, "tick": -1, "raison": "départ déjà choisi : seigneurie-1"}, p
assert p["premier_texte"] == "Choix refusé pour Despotat de Morée :\ndépart déjà choisi : seigneurie-1", p["premier_texte"]
s = lire("rapport-sans-service.json")
assert s["defaut"].startswith("repères : 0 posés sur 6") and s["premier"]["statut"] == -1 and s["premier_texte"] == "", s
print("ok")
EOF
```
sort `ok`. Contre-épreuve : sur une copie de `rapport-normal.json` où `second.statut` vaut 200, le même script lève `AssertionError` (le codeur le montre dans la PR, sans verser la copie).

SC6. Les tests EditMode restent verts : `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -testResults "$env:TEMP\lot651-tests.xml"` rend 0 (le lot ne touche aucun test ni aucun fichier de `Pont/` ou `Carte/` : `git diff origin/master --stat` ne nomme que le Périmètre).

SC7. `jeu/ville/README.md`, après la section de l'épreuve de la carte, une courte section « La session du choix de la terre » : la commande, ce que fait la session (six repères, clic sur N, reçu, clic sur M avant tout tick), les champs du rapport, les codes 0 / 1 / 2, le lancement du service à la main, et les liens vers les trois rapports versés. Elle dit que le jugement est celui du script de #615, à venir.

SC8. `python3 -m pytest jeu -q` passe en entier sur le VPS.

## Hors périmètre
- Le juge : le script `pc/epreuve_moree.py`, qui lance le service, appelle cette session, avance d'un tick et compare `/monde.maison_du_joueur` (autre sous-lot de #615), ses tests et ses verdicts.
- Tout tick, toute lecture de `/monde` ou de `maison_du_joueur` par la session ; la descente de la caméra (#614).
- `ReperesDeDepart`, `SurvolDeCarte`, `ClientIntention`, la scène `Forge_Carte` : inchangés ; si l'un d'eux semble devoir changer, le dire dans la PR plutôt que l'écrire.
- La capture `Lot613.cs` : elle reste telle quelle.
- `jeu/sim/` : aucune règle du monde ne change.

## Photo
sans objet : outil d'épreuve ; la session ouvre la carte en Play sans capturer, et rien de ce que voit le joueur ne change. L'écran du refus est déjà la photo du lot 613 (`second-choix-refuse`).
