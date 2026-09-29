# Lot #184 — Le panneau du lieu dans la scène du désert
Jalon : J1 · Machine : pc · Taille prévue : 290 lignes

## But
Dans la scène `Forge_Desert_Ville_ksar_des_sept_puits.unity`, le joueur voit un
panneau qui dit, pour sa cellule, la date du monde, les habitants, la
nourriture et les autres marchandises, la faim et la dette, **lus dans `sim/`
par le service local**. Le panneau suit le tick. Quand le service manque, il le
dit sans bloquer la scène. C'est « l'écran » du jalon J1 (CAP.md), que la
capture de la chaîne montre enfin.

## Règle du monde
Sans objet : c'est un lot de vue. Le panneau lit, il ne décide aucun nombre
(AGENTS.md, principe 1). Il n'ajoute rien à `jeu/`. Niveau de fidélité : sans
objet.

Ce qu'il respecte de [`jeu/sim/MODELE.md`](../../jeu/sim/MODELE.md) :
- **« Le panier de marchandises »** : `stocks` est un dictionnaire ouvert, et
  la nourriture y est une entrée comme une autre (`nourriture`). Le panneau
  affiche **chaque** clé reçue, sans liste fermée. Une marchandise absente du
  panier n'est pas un zéro (« Absence contre zéro ») : si `nourriture` n'est
  pas une clé, la ligne dit « absente du panier » et jamais « 0 kg ».
- **« La base de temps »** : la date vient du service (`date.annee`,
  `date.jour_de_l_annee`), elle n'est jamais recalculée à partir du tick.
- **« Le déficit alimentaire »** et l'étape 7 d'« En une page » :
  `food_deficit_kg` est la dette de nourriture, en kg ; `hunger_ticks` compte
  les ticks de manque. Le panneau les affiche tels quels, sans conversion.

**Dépendance.** La demande dit « #183 », mais #183 a été découpé en #185 (le
lecteur JSON et l'assemblage `3d/unity/Assets/ForgeLocal3D/Pont/`, isolé
d'Assembly-CSharp, avec son assemblage de tests EditMode) et #186 (le client
`GET /lieu?cell=<cell_id>` sur 127.0.0.1, qui rend le lieu ou une absence
déclarée qui nomme sa cause). Ce lot ne commence que si les deux sont sur
`origin/master`. Sinon le codeur n'écrit rien et répond « bloqué : #185/#186
non livrés ». Le panneau **utilise ce client tel quel**, sans le modifier ni
le doubler : aucun second lecteur JSON, aucun second appel HTTP.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/PanneauLieu.cs
3d/unity/Assets/ForgeLocal3D/Pont/PanneauLieu.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/<asmdef d'exécution de Pont, créé par #185>.asmdef
3d/unity/Assets/ForgeLocal3D/Pont/<dossier des tests EditMode de Pont, créé par #185>/PanneauLieuTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/<dossier des tests EditMode de Pont, créé par #185>/PanneauLieuTests.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/<dossier des tests EditMode de Pont, créé par #185>/<asmdef des tests, créé par #185>.asmdef
3d/unity/Assets/ForgeLocal3D/Desert/Scenes/Forge_Desert_Ville_ksar_des_sept_puits.unity
3d/unity/Packages/manifest.json
3d/unity/Packages/packages-lock.json
docs/mesures/184-panneau-du-lieu/avec-service.png
docs/mesures/184-panneau-du-lieu/lieu-1175.json

Précisions :
- les chemins entre chevrons sont ceux que #185 a créés, lus sur
  `origin/master`. Ce lot n'y crée ni dossier ni asmdef ;
- **l'asmdef d'exécution** gagne une seule référence, `UnityEngine.UI`.
  **L'asmdef des tests** ne change que s'il faut une référence pour compiler
  (au plus une ligne). Aucune autre ligne des deux ne bouge ;
- `manifest.json` et `packages-lock.json` changent **seulement** si
  `UnityEngine.UI` ne se résout pas : uGUI (`com.unity.ugui` 2.0.0) n'arrive
  aujourd'hui qu'en dépendance de URP. On ajoute alors une ligne
  `"com.unity.ugui": "2.0.0"` au manifeste, et le verrou suit tel qu'Unity le
  réécrit. Sinon, aucun des deux ne change ;
- **la scène** gagne un seul objet racine, « Panneau du lieu », avec son
  `Transform` et le composant `PanneauLieu` (cellule 1175, port 8000, caméra
  liée au composant `Camera` de « Caméra de la ville », `{fileID: 1376599988}`),
  plus son entrée dans la liste des racines. Si Unity réécrit d'autres parties
  en sauvant la scène, le codeur les rétablit : le diff de la scène ne contient
  que ces ajouts (voir SC5) ;
- le budget visé : `PanneauLieu.cs` ≈ 110 lignes, `PanneauLieuTests.cs`
  ≈ 110, la scène ≈ 45, les méta et les asmdef ≈ 25.

## Conditions de succès

Forme attendue de `PanneauLieu` (MonoBehaviour de l'assemblage `Pont`, tout
littéral autre que 0, 1, -1 en constante nommée) :

- **La cellule.** `-forgeCell <id>` sur la ligne de commande
  (`Environment.GetCommandLineArgs()`) l'emporte. Sinon, c'est le champ
  sérialisé `cellule` (1175 par défaut). La lecture de l'argument est une
  fonction pure (arguments, défaut) → cellule ou erreur. Une valeur non
  entière ou négative, ou `-forgeCell` sans valeur, est refusée avec une erreur
  qui nomme `-forgeCell` et la valeur reçue. Le panneau affiche alors cette
  erreur et n'interroge pas le service : **jamais de repli silencieux sur
  1175**. Le port est le champ sérialisé `port` (8000, `DEFAULT_SERVICE_PORT`
  de `jeu/sim/service.py`).
- **L'affichage.** Au démarrage, le panneau construit lui-même son uGUI : un
  `Canvas` en **Screen Space – Camera**, dont `worldCamera` est le champ
  sérialisé `camera` et dont `planeDistance` tombe entre les plans de coupe de
  la caméra (0,3 et 2500 dans la scène). Il y ajoute un `CanvasScaler`
  (ScaleWithScreenSize, 1600 × 900), un fond sombre ancré en haut à gauche et
  un `Text` (police `LegacyRuntime.ttf`). Sans caméra, `Debug.LogError` nomme
  le champ `camera` et le panneau ne s'affiche pas. La propriété
  `TexteAffiche` rend le `text` de **ce** composant `Text` : les tests lisent
  ce que l'écran montre, pas une chaîne à côté.
- **Le texte**, les nombres en `CultureInfo.InvariantCulture` (les réels en
  `"R"`, donc relisibles à l'identique) :
  ```
  Cellule 1175 · tick 12
  Date : jour 13 de 1400
  Habitants : 327
  Nourriture : 3270.5 kg
  sel : 12.25 kg
  Faim : 2 ticks de manque
  Dette de nourriture : 40.75 kg
  ```
  La nourriture vient en premier (ou « Nourriture : absente du panier »). Les
  autres marchandises suivent par ordre ordinal de leur nom, une ligne
  chacune.
- **Le rafraîchissement.** Toutes les `PERIODE_LECTURE_S = 0.25` s au plus, une
  lecture du client part **hors du fil principal**, jamais plus d'une à la
  fois. Son résultat est appliqué dans `Update`. Le texte n'est reconstruit que
  si le tick lu diffère du tick affiché, ou si l'état change (présent, absent,
  autre cause). Le compteur `Reconstructions` le compte.
- **L'absence.** Avant toute réponse, le texte est
  « service absent : en attente de 127.0.0.1:<port> ». Quand le client déclare
  le service absent, il devient « service absent : 127.0.0.1:<port> — <cause du
  client> ». Une autre absence (404, JSON invalide, clé manquante) donne
  « lieu illisible : <cause du client> ». Une absence **remplace** les
  nombres : un panneau qui a perdu le service ne garde pas les chiffres d'hier.

**SC1 — Le panneau dit les nombres du faux service, et suit le tick (PC).**
Les tests de `PanneauLieuTests.cs` tournent contre un faux service
`HttpListener` sur un port libre, qui rend une réponse `/lieu` fixe. Ce
document est construit dans le test à partir d'un seul jeu de valeurs :
`cell_id` 1175, `tick` 12, `date` {1400, 13}, `population` 327,
`stocks` {`nourriture` 3270.5, `sel` 12.25}, `hunger_ticks` 2,
`food_deficit_kg` 40.75. Les valeurs attendues sont **ces mêmes valeurs**,
jamais une chaîne recopiée à la main.
- `Le_panneau_affiche_les_nombres_du_faux_service` : après une lecture, chaque
  nombre relu dans `TexteAffiche` (InvariantCulture) est **égal** à sa valeur.
  Les sept lignes sont là, dans l'ordre, et `sel` a sa ligne : le panier est
  lu sans liste fermée.
- `Le_panneau_se_refait_quand_le_tick_change` : le faux service rend le
  tick 12, puis le tick 13 (`population` 326, `nourriture` 3268.5), puis
  encore le tick 13. Après la deuxième lecture, le texte diffère du premier et
  porte les nombres du tick 13. C'est la **contre-épreuve** : une réponse
  décalée d'un tick doit changer ce qu'on lit. Après la troisième lecture,
  `Reconstructions` n'a pas bougé.

**SC2 — Sans service, le panneau le dit, sans zéro et sans bloquer (PC).**
- `Sans_service_le_panneau_dit_service_absent` : sur un port fermé (réservé
  puis libéré par le test), `TexteAffiche` commence par « service absent »,
  nomme `127.0.0.1:<port>`, et ne contient ni « Habitants » ni « Nourriture ».
  Un panneau qui affiche des zéros échoue.
- `Une_lecture_lente_ne_bloque_pas_la_scene` : le faux service attend 2 s
  avant de répondre. L'appel du pas de rafraîchissement (celui qu'`Update`
  fait) rend la main en moins de `DELAI_MAX_PAS_MS = 100`, mesuré par
  `Stopwatch`, et le texte reste celui d'avant. Un panneau qui lit sur le fil
  principal échoue. Sous Windows, un port fermé en local fait aussi attendre
  la connexion : c'est ce cas qui l'attrape.
- `L_argument_forgeCell` (`[TestCase]`) : sans argument → 1175 ;
  `-forgeCell 42` → 42 ; `abc`, `-3` et `-forgeCell` en dernier argument →
  erreur qui contient `-forgeCell` et la valeur reçue.

Commande (sans `-quit`, qui interrompt `-runTests`) :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "<assemblage de tests de Pont>" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
Le code de sortie vaut 0, le XML dit `failed="0"`, et il compte les cas de
#185 et #186 **plus** au moins les 5 méthodes ci-dessus (7 cas avec les
`TestCase`). Aucun cas existant ne change. Zéro cas est un échec.
Contre-épreuves jouées à la main et dites dans la PR : afficher
`population + 1` fait rougir `Le_panneau_affiche_les_nombres_du_faux_service` ;
lire le client directement dans `Update` fait rougir
`Une_lecture_lente_ne_bloque_pas_la_scene`.

**SC3 — Unity compile.** Le workflow `unity` (poussée sur la branche) est
vert, sans aucune `error CS`.

**SC4 — La capture de la chaîne montre le panneau, puis les vrais chiffres (PC).**
- Sans service :
  `Unity.exe -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeCaptures <temp>`
  écrit `Forge_Desert_Ville_ksar_des_sept_puits.png`. **Le codeur ouvre
  l'image** : le panneau y est, entier, lisible, en haut à gauche, et dit
  « service absent ». Une capture sans panneau échoue, même si tout est vert.
- Avec service, depuis `jeu/` :
  `py -m sim.service --jours-par-seconde 0`, puis `POST /tick?n=30`, puis
  `GET /lieu?cell=1175`, enregistré tel quel dans
  `docs/mesures/184-panneau-du-lieu/lieu-1175.json`. Puis la même capture
  avec `-forgeCell 1175`, copiée en
  `docs/mesures/184-panneau-du-lieu/avec-service.png`. Chaque nombre visible
  sur l'image est **égal** à celui du JSON, au tick 30. Un écart est un échec.
  Le compte rendu joint cette capture à la PR. Le PNG passe par LFS
  (`.gitattributes`).

**SC5 — Rien d'autre ne bouge.**
```
git diff --name-only origin/master...HEAD
git diff origin/master...HEAD -- 3d/unity/Assets/ForgeLocal3D/Desert/Scenes/Forge_Desert_Ville_ksar_des_sept_puits.unity
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC
```
Le premier ne nomme que des chemins du périmètre (et ce brief). Le deuxième
ne montre **que des lignes ajoutées**, pour l'objet « Panneau du lieu » et son
entrée dans la liste des racines. La suite du jeu reste verte.

## Hors périmètre
- toute modification du client (#186), du lecteur JSON (#185) et de leurs
  tests ;
- `ForgeCapture.cs` et les autres scripts d'`Editor/` : si la capture ne
  montre pas le panneau, le lot le dit dans son compte rendu et s'arrête,
  sans toucher la capture ;
- `-forgePort`, changer la vitesse ou mettre en pause depuis Unity, un bouton,
  le texte en TextMeshPro ;
- lancer le service depuis Unity, et `pc\Jouer.cmd` ;
- l'épreuve PC du jalon (panneau au tick N contre
  `py -m sim --ticks N --seed S --snapshot-json`, avec sa contre-épreuve d'un
  service décalé) : c'est un lot suivant ;
- les autres scènes du désert et `3d/archives/` ;
- `jeu/`, dont `jeu/sim/service.py` et `MODELE.md` ;
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
