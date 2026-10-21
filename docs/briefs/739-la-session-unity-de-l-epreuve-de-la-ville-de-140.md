# Lot #739 — La session Unity de l'épreuve de la ville de 1400
Jalon : J4 · Machine : pc · Taille prévue : 200 lignes

## But
Une session Unity ouvre quatre villes de 1400 sur le service, comme le joueur les verrait, et écrit pour chacune ce qu'elle a posé, maison par maison, sans rien juger.

## Le joueur
Le joueur entre dans Biskra et y voit les maisons de terre que le monde tient pour sa ville de 1400 (#737), le long des rues de #738. Ce lot de fond prépare la preuve de J4 « le plan de la ville vit dans le monde : Unity relancé redessine la même ville d'après le service », et sa contre-épreuve « une ville que seul Unity connaît » (`CAP.md`). Il donne à cette preuve sa moitié Unity : ouvrir les villes, relever chaque maison posée, rouvrir sur un service neuf, et savoir tricher sur commande (une maison sautée, une maison ajoutée) pour que le verdict puisse rougir. Le verdict, `pc/epreuve_ville1400.py`, est le sous-lot 6 de #412 : c'est lui qui rendra visible au joueur que sa ville ne vient pas d'Unity.

Dépend de : #737, sur la base (037d243) : `DesertRoadTool.Maisons` (`DesertMaisons1400` : `Racine`, `Posees`, `Foyers`, `Absence`, `Refus`, `Boite`). #738 aussi (`DesertRoadTool.Rues1400`, `Empreinte`, `Dessinees`). Rien n'est attendu de J3.

## Règle du monde
Sans objet : outil d'épreuve. La session éprouve, sans la changer, la règle de `jeu/sim/MODELE.md`, « Le plan du bourg » → « Le plan de base » : la ville de 1400 d'un bourg est dérivée de ses habitants d'amorçage et servie par `/plan` ; Unity la lit et ne l'invente pas. Rien ne change dans `jeu/`, `Pont/`, `Desert/` ni `Interface/`.

**Ce que le lot fait.** Un seul fichier de code neuf, `Editor/EpreuveVille1400.cs`, sur le modèle d'`Editor/EpreuveCapitale.cs` (#702) : `[InitializeOnLoad]`, `SessionState`, `EditorApplication.update`, rapport toujours écrit dès que les arguments sont valides, sortie du Play puis `CitadelEditorBridge.Finish(code)`. Il réutilise `EpreuveChoix.Argument` et `EpreuveChoix.DossierDeLancement` (déjà `internal`) et `DesertMaisons1400.Boite` (déjà `public`), sans les modifier.

```
Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveVille1400.Jouer
      -forgeEpreuve <dossier> [-forgeSauter | -forgeAjouter] [-logFile <journal>]
```
`ForgeLocal3D.EpreuveVille1400.Relancer` prend les mêmes arguments. Les deux font la même chose ; seul le champ `session` (« jouer » ou « relance ») et le nom des fichiers changent. La relance se lance sur un service neuf de même graine : c'est elle que le verdict comparera à `jouer`.

1. **Arguments.** `-forgeEpreuve` absent, ou `-forgeSauter` et `-forgeAjouter` ensemble : `Debug.LogError("EPREUVE_VILLE1400 : …")`, `EditorApplication.Exit(2)`, aucun rapport. Les deux drapeaux sont des présences (`Array.IndexOf` sur `Environment.GetCommandLineArgs()`). Le dossier, résolu depuis `DossierDeLancement()`, est créé s'il manque.
2. **La ville.** La session ouvre `Assets/ForgeLocal3D/Desert/Scenes/Forge_Desert_Ville_ksar_des_sept_puits.unity` et entre en Play. Après deux images, elle prend l'unique `DesertRoadTool` et l'unique `DesertCityCamera` de la scène (sinon exception qui les nomme), et met `automatique` à vrai sur l'outil, la caméra et son marcheur, comme `Lot737`.
3. **Les cellules**, dans cet ordre fixe : `10103, 1175, 1232, 10337` (Biskra, le ksar de l'éditeur, 493 maisons seules, 28 îlots). Pour chacune : un `Stopwatch` autour de `outil.Ouvrir(cellule)` donne `duree_dessin_ms` (lecture du plan et dessin compris). Un `Ouvrir` faux donne `defaut` = « ouverture de la cellule <c> : <outil.Message> », la cellule suivante est quand même essayée.
4. **La contre-épreuve**, après l'ouverture et avant le relevé, sur la seule racine `outil.Maisons.Racine` :
   - `-forgeSauter` : le premier enfant est détruit (`Object.DestroyImmediate`) ;
   - `-forgeAjouter` : le premier enfant est copié (`Object.Instantiate`, même nom, même parent), la copie décalée de +10 m en x Unity, sans nouveau calage au sol.

   `contre_epreuve` vaut alors « sauter » ou « ajouter », sinon "". Une racine vide ne reçoit rien et le dit dans `defaut`.
5. **Le relevé**, sur ce qui est réellement sous la racine, dans l'ordre de ses enfants. Une ligne par maison : `"<rang> <indice> <variante> <x> <y> <sol> <lacet>"`, culture invariante, les quatre derniers en `F2`.
   - `rang` et `indice` sont lus dans le nom « Maison <rang> indice <indice> » ; un nom illisible donne −1 et −1.
   - `variante` est le v de 0 à 5 dont `KitDesBatiments.Charger().Maison(v).Prefab` a la même suite de `sharedMesh` que l'instance (comparaison de `Lot737`), −1 si aucune.
   - `b = DesertMaisons1400.Boite(instance)`. Le centre monde est `instance.transform.TransformPoint(b.center)`, et `x`, `y` sont ses coordonnées du plan : −x et −z Unity. `sol` est le y monde de `TransformPoint(b.center.x, b.min.y, b.center.z)`, `lacet` vaut `transform.eulerAngles.y`.
   - `empreinte` est le SHA-256 hexadécimal minuscule de l'UTF-8 des lignes, chacune suivie de `\n` (aucune ligne : le hachage de "").
   - Les autres champs viennent de l'outil : `tick` = `TickOuverture`, `foyers`, `posees`, `absence` (`Absence ?? ""`), `refus` de `Maisons`, et `rues_dessinees`, `empreinte_rues` de `Rues1400`.
6. **Les images.** La caméra se pose par `ville.Poser(Vector3.zero, 40f, 68f, d)`, où d = max(60 m, 2 × la plus grande distance à l'origine d'un centre de maison relevé), puis `outil.Placer()`. La session laisse passer 10 images, puis en compte 300 : `images` = 300 et `image_ms` = 1000 × la somme de `Time.unscaledDeltaTime` / 300. Une mesure de session, pas la preuve des 60 images par seconde (#422).
7. **Le rapport** de chaque cellule s'écrit dans `<dossier>/<session>-<cellule>.json`, par `JsonUtility.ToJson(rapport)` **sans indentation** : une ligne par fichier, car 1 133 maisons indentées feraient des milliers de lignes versées. Après les quatre, un `Debug.Log("EPREUVE_VILLE1400 <session> : <cellule> <posees>/<foyers> …")` par cellule, avec « ; défaut : … » s'il y en a un. Code **0** si aucun `defaut`, **1** sinon, **2** pour des arguments fautifs.

```csharp
[Serializable] public class Rapport {
    public string session = "", contre_epreuve = "", absence = "", empreinte = "", empreinte_rues = "", defaut = "";
    public long cellule = -1, tick = -1;
    public int foyers = -1, posees = -1, rues_dessinees = -1, images = 0;
    public double duree_dessin_ms = -1, image_ms = -1;
    public string[] refus = new string[0], maisons = new string[0];
}
```
La session ne compare rien, ni au plan ni à une autre session : une maison refusée ou un écart sont relevés tels quels, avec le code 0.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/EpreuveVille1400.cs
3d/unity/Assets/ForgeLocal3D/Editor/EpreuveVille1400.cs.meta
jeu/ville/README.md
docs/mesures/739-session-ville1400/jouer-10103.json
docs/mesures/739-session-ville1400/jouer-1175.json
docs/mesures/739-session-ville1400/jouer-1232.json
docs/mesures/739-session-ville1400/jouer-10337.json
docs/mesures/739-session-ville1400/relance-10103.json
docs/mesures/739-session-ville1400/relance-1175.json
docs/mesures/739-session-ville1400/relance-1232.json
docs/mesures/739-session-ville1400/relance-10337.json

Tout autre chemin est interdit. Budget indicatif : 155 lignes de code, 11 de `.meta` (générée par Unity), 25 de README, 8 pour les huit rapports d'une ligne.

## Conditions de succès
Toutes se jouent sur le PC, éditeur fermé, depuis la racine : `$u = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. `JOUER` = `& $u -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveVille1400.Jouer`, `RELANCER` de même avec `.Relancer`, sans `-quit` ni `-nographics`. Le service se lance dans un second terminal, depuis `jeu\` : `py -m sim.service --seed 0 --jours-par-seconde 0` (port 8000, tick 0, en pause). Il s'arrête après chaque essai : le suivant part d'un service neuf.

SC1 — **Jouer.** Service neuf, puis `JOUER -forgeEpreuve docs\mesures\739-session-ville1400 -logFile "$env:TEMP\lot739-jouer.log"`. La commande rend **0** et écrit les quatre `jouer-<cellule>.json`. Chacun porte `session` « jouer », `contre_epreuve` "", `defaut` "", `absence` "", `tick` 0, `images` 300, `duree_dessin_ms` > 0 et `image_ms` > 0. `foyers` vaut 33, 66, 493 et 541. Le journal porte quatre lignes « EPREUVE_VILLE1400 jouer ». Le contrôle du plan est SC4.

SC2 — **Relancer.** Service arrêté puis relancé neuf, puis `RELANCER -forgeEpreuve docs\mesures\739-session-ville1400 -logFile "$env:TEMP\lot739-relance.log"`. La commande rend **0**. Chaque `relance-<c>.json` a le même `tick`, les mêmes `foyers`, `posees`, `refus`, `maisons`, `empreinte`, `rues_dessinees` et `empreinte_rues` que `jouer-<c>.json` (SC4 le vérifie). Contre-épreuve : SC3.

SC3 — **Les contre-épreuves changent le relevé.** Service neuf, puis `JOUER -forgeEpreuve "$env:TEMP\lot739-sauter" -forgeSauter`. La commande rend **0** et, dans chaque cellule, `contre_epreuve` vaut « sauter », `posees` = celui de `jouer` − 1, `empreinte` diffère. Service neuf, puis la même commande vers `"$env:TEMP\lot739-ajouter"` avec `-forgeAjouter` : **0**, `posees` = celui de `jouer` + 1, et une paire (rang, indice) apparaît deux fois dans `maisons`. Le codeur passe aussi les deux dossiers au script de SC4, en remplaçant le préfixe `jouer-` par celui du dossier : le script lève `AssertionError`. Il colle les deux sorties dans la PR. Rien n'est versé.

SC4 — **Les rapports versés se relisent contre le monde**, sur le VPS comme sur le PC, depuis `jeu/` :
```bash
python3 - <<'EOF'
import hashlib, json
from sim.world import World
from sim.ville1400 import base_de_cellule
w = World.charger(rng_seed=0)
d = "../docs/mesures/739-session-ville1400/"
def dedans(px, py, poly, tol=0.05):
    n = len(poly); signes = set()
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        l = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        c = ((bx - ax) * (py - ay) - (by - ay) * (px - ax)) / l
        if abs(c) > tol: signes.add(c > 0)
    return len(signes) <= 1
for c in (10103, 1175, 1232, 10337):
    base = base_de_cellule(w, c)
    j = json.load(open(f"{d}jouer-{c}.json", encoding="utf-8"))
    r = json.load(open(f"{d}relance-{c}.json", encoding="utf-8"))
    assert (j["session"], r["session"], j["contre_epreuve"], r["contre_epreuve"]) == ("jouer", "relance", "", ""), c
    assert j["defaut"] == r["defaut"] == "" and j["tick"] == 0, (c, j["defaut"], r["defaut"])
    assert j["foyers"] == sum(m["foyers"] for m in base["maisons"]) == j["posees"] + len(j["refus"]), c
    assert len(j["maisons"]) == j["posees"] > 0, c
    assert j["empreinte"] == hashlib.sha256("".join(l + "\n" for l in j["maisons"]).encode()).hexdigest(), c
    vus = set()
    for l in j["maisons"]:
        rang, indice, variante, x, y = l.split()[:5]; rang, indice = int(rang), int(indice)
        assert (rang, indice) not in vus and int(variante) == (rang + indice) % 6, l
        assert 0 <= indice < base["maisons"][rang]["foyers"] and dedans(float(x), float(y), base["maisons"][rang]["emprise"]), l
        vus.add((rang, indice))
    for k in ("tick", "foyers", "posees", "refus", "maisons", "empreinte", "rues_dessinees", "empreinte_rues"):
        assert j[k] == r[k], (c, k)
    print(c, j["posees"], "posées", len(j["refus"]), "refus", round(j["duree_dessin_ms"]), "ms", round(j["image_ms"], 1), "ms/image")
print("ok")
EOF
```
Le script sort quatre lignes de mesure puis `ok`. Contre-épreuves (le codeur les montre dans la PR, sans rien verser) : une copie de `jouer-1232.json` privée d'une ligne de `maisons`, ou dont un `x` est augmenté de 50, fait lever `AssertionError` ; SC3 aussi.

SC5 — **La session impossible le dit.** Aucun service, puis `JOUER -forgeEpreuve "$env:TEMP\lot739-sans-service"`. La commande rend **1** et écrit quatre rapports, chacun avec un `defaut` qui commence par « ouverture de la cellule ».

SC6 — **Les arguments.** `JOUER` sans `-forgeEpreuve`, puis `JOUER -forgeEpreuve "$env:TEMP\lot739-deux" -forgeSauter -forgeAjouter`, rendent **2**. Le second dossier n'est pas créé. Le journal nomme « EPREUVE_VILLE1400 ».

SC7 — **Rien d'autre ne bouge.**
- Les tests EditMode restent verts : `& $u -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -testResults "$env:TEMP\lot739-tests.xml"` rend 0, résultats neufs et non vides.
- `py pc/epreuve_capitale.py --sortie "$env:TEMP\lot739-capitale"` rend 0 : la session #702 est intacte.
- `python3 -m pytest jeu -q` passe en entier sur le VPS.
- `git diff --check`, `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne nomment que le Périmètre ; `git diff --numstat origin/master` totalise moins de 300 lignes.

Contre-épreuve : un changement dans `EpreuveChoix.cs`, `EpreuveCapitale.cs`, `Pont/`, `Desert/`, `Interface/`, une capture ou `jeu/sim/` refuse la livraison.

SC8 — **Le README.** Dans `jeu/ville/README.md`, après « L'épreuve de la capitale », une courte section « La session de l'épreuve de la ville de 1400 ». Elle donne :
- les deux commandes et les deux drapeaux ;
- le service lancé à la main, neuf avant chaque session ;
- les quatre cellules, les champs du rapport, le format d'une ligne de maison, l'empreinte ;
- les codes 0, 1 et 2 ;
- les liens vers les huit rapports versés.

Elle dit que le jugement est celui de `pc/epreuve_ville1400.py`, à venir.

## Hors périmètre
- Le verdict `pc/epreuve_ville1400.py` (sous-lot 6 de #412) : lancer les services, appeler les sessions, comparer au plan servi, rougir sur les contre-épreuves.
- Toute photo, caméra de capture ou scénario `Captures/` : le dessin de Biskra est la photo de #737, les rues celle de #738.
- `DesertRoadTool`, `DesertMaisons1400`, `DesertRues1400`, `MaisonsDeLaBase`, le kit, les scènes et `jeu/` restent tels quels. Si l'un semble devoir changer (par exemple une maison refusée à 1232 ou 10337), le codeur le dit dans la PR et le relève dans le rapport, sans l'écrire.
- La tenue des 60 images par seconde (#422) : `image_ms` est relevé, pas jugé.
- Paris (10322), dont la ville dépasse le terrain : pas dans les quatre cellules.

## Photo
sans objet : outil d'épreuve. La session ouvre les villes en Play sans rien capturer, et rien de ce que voit le joueur ne change. Biskra et ses maisons sont la photo du lot 737, ses rues celle du lot 738.
