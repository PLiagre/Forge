# Lot #263 — Le panneau de la capitale montre les foyers, leur logement et le chantier
Jalon : J4 · Machine : pc · Taille prévue : 280 lignes

## But
Dans la scène de la capitale, le panneau du lieu montre, lus tels quels dans `GET /lieu` du service, les foyers de la cellule par métier, le logement des artisans (logés, sans logis, places) et les bras partis au chantier. Chaque chiffre absent y est dit absent, et Unity ne calcule aucun nombre.

## Règle du monde
Sans objet : c'est un lot de vue. Il **lit** ce que le monde publie déjà, sans rien changer à `jeu/`.

Ce que le panneau lit, et d'où ça vient dans `jeu/sim/MODELE.md` :
- « ## Les foyers par métier » : `GET /lieu?cell=X` porte `foyers`. C'est un objet trié par nom de métier, où chaque métier vaut `{"foyers": n, "personnes": p}`, le dernier foyer incomplet compté. La valeur est `-1` si les métiers ne sont pas calculés, `{}` pour une cellule vide. Un métier n'existe que si quelqu'un l'exerce : son absence veut dire personne, jamais « inconnu ».
- Même section, paragraphe du logement (#348) : `/lieu` porte `logement` = `{"capacite", "loges", "sans_logis"}` **seulement si le plan a un bâtiment**. Si les métiers ne sont pas calculés, `loges` et `sans_logis` valent `-1`.
- « ## Le chantier et ses bras » : les paysans envoyés au chantier pendant le tick sont comptés dans le métier `ouvriers`, et reviennent aux champs au tick suivant. Les « bras partis au chantier » sont donc `foyers.ouvriers.personnes`.

Mesuré le 06/10/2026 (service graine 0, poussé au tick 30, sans IA, cellule 1175, celle du panneau par défaut). Au tick 30 : `foyers = {"paysans": {"foyers": 66, "personnes": 328}}`, sans `logement`. On dépose ensuite la recette de `test_service_logement` (`jeu/sim/tests/test_monde.py`) :
1. `tracer_route` `[[0,0],[20,0]]`, largeur 1, foyers 100, puis un tick ;
2. deux `decouper_parcelle` (rue 0, segment 0, côté `gauche`, `(debut, facade, profondeur)` = `(0,4,10)` et `(6,8,20)`, foyers 100), puis un tick ;
3. `poser_batiment` `maison` sur la parcelle 0 et `four` sur la parcelle 1 (foyers 100), puis deux ticks.

Au tick 34, `/lieu?cell=1175` vaut alors :
- `artisans` 4 foyers / 20 personnes ;
- `ouvriers` 15 / 71 ;
- `paysans` 48 / 238 ;
- `logement = {"capacite": 1, "loges": 1, "sans_logis": 3}`.

C'est une prévision : seuls les octets du service font foi.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientLieu.cs
3d/unity/Assets/ForgeLocal3D/Pont/PanneauLieu.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientLieuTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PanneauLieuTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot263.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot263.cs.meta
docs/briefs/263-le-panneau-de-la-capitale-montre-les-foyers-leur.md

Précisions :

- **`ClientLieu.cs`, `Lieu`.** `Lieu` gagne deux lectures, gardées telles que le service les a écrites.
  - **Les foyers**, dans un de trois états : *servis* (un dictionnaire en lecture seule, métier → `(Foyers, Personnes)`, entiers, dans l'ordre reçu), *non calculés* (le service a écrit `-1`) ou *absents* (la clé `foyers` manque).
  - **Le logement** : *absent* (la clé manque) ou *servi* (`Capacite`, `Loges`, `SansLogis`, entiers ; `-1` est relu tel quel).

  Les entiers passent par `Entier(...)` du client. Une valeur mal formée rend une absence du lieu entier qui nomme son chemin, comme pour les autres clés :
  - `foyers` qui n'est ni un objet ni exactement `-1` : « clé foyers : … » ;
  - un métier sans `personnes`, ou avec `1.5` : `foyers.<métier>.personnes` ;
  - `logement` qui n'est pas un objet, ou une de ses trois clés absente ou non entière : `logement.<clé>`.

  Aucune autre clé n'est lue, et aucune somme ni aucune division n'est faite.
- **`PanneauLieu.cs`.** Le texte actuel (`TexteAffiche`, `Decrire`) **ne change pas d'un caractère**. L'épreuve du jalon 1 (`pc/epreuve_jalon1.py`) relit ce texte ligne par ligne et refuse toute ligne inconnue. `ForgeCapture` l'écrit dans `<scène>.panneau.txt` par `GetComponentInChildren<Text>()` sur « Panneau du lieu ».

  Le lot ajoute donc un **second `Text`**, enfant du même fond, créé **après** le premier : `GetComponentInChildren` doit toujours rendre celui du jalon 1. Une propriété `TexteFoyers` l'expose. Il se refait dans `Appliquer`, en même temps que le premier et au même tick.

  Son texte, ligne par ligne, avec ces libellés exacts :
  - `Foyers par métier :`, puis une ligne par métier servi, dans l'ordre reçu : `<métier> : <foyers> foyers, <personnes> personnes` ;
  - si les foyers sont servis mais vides (`{}`) : `Foyers par métier : aucun` ;
  - s'ils ne sont pas calculés : `Foyers par métier : non calculés par le monde` ;
  - si la clé est absente : `Foyers par métier : absents de la réponse du service` ;
  - pour le chantier :
    - `Au chantier : <personnes d'ouvriers> bras pris aux champs` si `ouvriers` est servi ;
    - `Au chantier : personne` si les foyers sont servis sans `ouvriers` ;
    - `Au chantier : non calculé` si les foyers ne sont pas calculés ;
    - `Au chantier : absent de la réponse du service` si la clé `foyers` est absente ;
  - pour le logement :
    - `Logement des artisans : <loges> foyers logés, <sans_logis> sans logis, <capacite> places` ;
    - si `loges` ou `sans_logis` vaut `-1` : `Logement des artisans : <capacite> places, logés et sans-logis non calculés` ;
    - si la clé est absente : `Logement : absent du service (aucun bâtiment au plan)`.

  Les nombres s'écrivent en `InvariantCulture`, comme `Entier`.

  Quand la lecture est une absence (service absent, lieu illisible, cellule refusée) ou que le panneau attend encore le service, `TexteFoyers` vaut `""` et son objet est inactif. Aucun chiffre d'une lecture précédente ne reste à l'écran.
- **Tests C#.** On **ajoute** des cas à `ClientLieuTests.cs` et `PanneauLieuTests.cs`, sans en modifier ni en retirer aucun. Le `Document(...)` de `PanneauLieuTests` peut gagner un paramètre facultatif (les foyers et le logement à servir) à condition que ses appels existants rendent les mêmes octets qu'avant. Les assistants nouveaux s'ajoutent à côté des anciens.
- **`Lot263.cs`** : le scénario de la photo (voir « Photo »). Son `.meta` est celui qu'Unity génère.
- La taille reste sous 300 lignes. Pour cela, les cas d'absence se regroupent en `[TestCase]` plutôt qu'en méthodes copiées.

## Conditions de succès

**SC1 — le projet compile.**
Le workflow `unity` (poussée sur la branche) est vert, sans aucune `error CS`.
Contre-épreuve : c'est le même workflow qui a refusé les lots dont le C# ne compilait pas ; il n'y a rien de plus à prouver ici.

**SC2 — le client relit foyers et logement tels quels, et déclare ce qui manque (PC).**
Sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
(sans `-quit`, qui interrompt `-runTests`). Le code de sortie vaut 0, le XML dit `failed="0"` et aucun cas n'est ignoré. Le nombre de cas est celui de `origin/master` plus les cas ajoutés, ce que la PR dit chiffres à l'appui.

Cas ajoutés à `ClientLieuTests` :
- `lieu-graine0-tick3.json` (figé, inchangé) : les foyers sont *servis*, avec exactement `mineurs`, puis `paysans`. Mineurs 2195 foyers / 10974 personnes ; paysans 19756 / 98778, comparés par `==`. Le logement est *absent*.
  Contre-épreuve dans le même cas : `lieu-graine0-tick4.json` donne mineurs 2196 / 10976. Un client qui rendrait des foyers figés échoue.
- Le même fichier où `"foyers":{…}` est remplacé par `"foyers":-1` : *non calculés*. Le même sans la clé `foyers` : *absents*, et non pas un dictionnaire vide.
- Le même avec `,"logement":{"capacite":9,"loges":1,"sans_logis":3}` inséré : `9`, `1`, `3`. Ces valeurs sont choisies **incohérentes** (`min(foyers, capacité)` ne donne pas 1) : un client qui recalculerait échoue. Avec `"loges":-1,"sans_logis":-1` : `-1` relus.
- Refus, chacun une absence dont le texte contient le chemin nommé :
  - `"foyers":"x"` → `foyers` ;
  - `"personnes":10974` → `"personnes":1.5` → `foyers.mineurs.personnes` ;
  - `"personnes":10974` retiré → `foyers.mineurs.personnes` ;
  - `logement` sans `sans_logis` → `logement.sans_logis` ;
  - `"logement":3` → `logement`.

Cas ajoutés à `PanneauLieuTests`, par le faux service du fichier :
- **Le jalon 1 reste intact.** Un document servi avec foyers et logement passe le `Verifier(texte, Tick12)` existant tel quel (7 lignes). `objet.GetComponentInChildren<Text>().text == panneau.TexteAffiche`.
- **Rien n'est calculé.** On sert les foyers `{"artisans":{"foyers":7,"personnes":20},"ouvriers":{"foyers":15,"personnes":71},"paysans":{"foyers":48,"personnes":238}}` et le logement `{"capacite":9,"loges":1,"sans_logis":3}`. `TexteFoyers`, relu par `Relire` (libellés exacts, nombres en `InvariantCulture`), a exactement 6 lignes :
  - l'en-tête `Foyers par métier :` ;
  - `artisans` 7 / 20, puis `ouvriers` 15 / 71, puis `paysans` 48 / 238 ;
  - `Au chantier : ` 71 ` bras pris aux champs` ;
  - le logement 1, 3, 9.

  7 foyers pour 20 personnes est voulu : un panneau qui calculerait `personnes / 5` écrirait 4 et échoue.
- **Les absences se disent, sans chiffre**, en `[TestCase]`. Pour chacune, les lignes attendues sont exactes et aucune ne contient de chiffre :
  - foyers `-1` : `non calculés par le monde`, `Au chantier : non calculé` ;
  - clé `foyers` absente : `absents de la réponse du service`, `Au chantier : absent de la réponse du service` ;
  - `{}` : `Foyers par métier : aucun`, `Au chantier : personne` ;
  - foyers sans `ouvriers` : `Au chantier : personne` ;
  - sans `logement` : `Logement : absent du service (aucun bâtiment au plan)` ;
  - `loges` `-1` : `9 places, logés et sans-logis non calculés`.
- **Le panneau suit le tick, et une absence efface les chiffres.** Avec les mêmes foyers, `artisans` à 7 puis à 8 foyers au tick suivant : `TexteFoyers` change avec le tick. Puis une 404 : `TexteFoyers == ""`, son objet est inactif, et `TexteAffiche` commence par `lieu illisible : `.

**SC3 — l'épreuve du jalon 1 passe toujours (PC).**
Commande : `py pc\epreuve_jalon1.py --sortie <temp>\j1` sort à `0` (égalité entre le panneau et la photographie, graine 0, tick 30).
Contre-épreuve : `py pc\epreuve_jalon1.py --sortie <temp>\j1d --decalage 1` sort à `1` (un écart).
Les deux sorties sont dites dans la PR. Un second texte qui se glisserait dans `<scène>.panneau.txt` ferait échouer la première commande sur « ligne inconnue ».

**SC4 — la photo est prise, et elle montre les trois chiffres (PC).**
Commande :
```
Unity.exe -batchmode -quit -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier `
  -forgeCaptures <temp>\cap263 -forgeLot 263 -logFile <temp>\cap263.log
```
- Le journal contient `CAPTURE_SCENARIOS lot 263 : 1` et deux `CAPTURE_OK` : le plan fixe et `Forge_Desert_Ville_ksar_des_sept_puits--chantier.png`.
- Il ne contient aucun `CAPTURE : le scénario`.
- Le code de sortie vaut 0.
- Le scénario lui-même lève si le panneau n'atteint pas l'état attendu (voir « Photo »). Un panneau qui n'afficherait pas les foyers ne donne donc pas de photo.

**SC5 — rien d'autre ne bouge.**
- `git diff --name-only origin/master...HEAD` ne nomme que des chemins du périmètre : aucun fichier sous `jeu/`, `pc/` ni `ForgeCapture.cs`.
- `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/ | grep -c '^-[^-]'` affiche `0` : on a seulement ajouté des lignes aux tests.
- `cd jeu && timeout 900 python3 -m pytest ville/tests/test_epreuve_jalon1.py ville/tests/test_lanceur_jouer.py -q` est vert, inchangé.

## Hors périmètre
- Tout changement de `jeu/` : service, `/lieu`, `logement_de`, métiers, chantier, MODELE.md. Le service sert déjà tout ce que le panneau lit.
- Lire `/plan` dans le panneau, ou montrer les journées de travail requises et fournies d'un chantier.
- Dessiner les parcelles et les bâtiments en 3D (sous-lots de #261), ou faire passer la route du scénario par l'outil des routes.
- Les foyers par lieu (rang) : `/lieu` ne les publie qu'à la cellule.
- Un geste du joueur dans le panneau (choisir le nombre de foyers envoyés au chantier) ; l'IA.
- Changer le texte du jalon 1, `pc/epreuve_jalon1.py`, `ForgeCapture.cs`, les réponses figées `lieu-graine0-tick*.json` ou `LecteurJsonTests.cs`.
- Brancher les tests EditMode dans un workflow : ce geste appartient au propriétaire, en mode direct.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.

## Photo
La photo montre la capitale du désert avec le panneau du lieu en haut à gauche. Au-dessous des chiffres du jalon 1, on voit les foyers de la cellule 1175 par métier (artisans, ouvriers, paysans), les bras partis au chantier et les artisans logés et sans logis. Le plan fixe pris juste avant (tick 30, sans geste) montre le même panneau sans artisans, avec `Au chantier : personne` et `Logement : absent du service (aucun bâtiment au plan)`. Les deux images se comparent.

Le scénario de capture est écrit dans `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot263.cs`, sur le modèle de `Lot293.cs` : `[ScenarioDeCapture(263, "chantier")]`, un seul scénario. Il fait ceci :
1. Il trouve le `PanneauLieu` de la scène et lève s'il n'y en a pas. Il prend sa cellule par `PanneauLieu.LireCellule(Environment.GetCommandLineArgs(), PanneauLieu.CELLULE_PAR_DEFAUT, out _)`, comme `DesertRoadTool`.
2. Il dépose la recette de « Règle du monde » sur cette cellule, avec ses ticks. Les dépôts passent par `ClientIntention.Deposer` et les ticks par `POST /tick?n=1`, tous hors du fil de l'éditeur (`Task.Run`, comme `Lot293`). Il lève si un dépôt n'est pas accepté ou si un tick ne rend pas 200.
3. Il attend, image par image (`yield return null`), au plus 20 s mesurées par `Time.realtimeSinceStartupAsDouble`, que `TexteAffiche` commence par `Cellule <cellule> · tick 34`. Si le service a été poussé à un autre tick, il attend le tick de départ + 4, qu'il lit au premier `TexteAffiche`.
4. Il lève si `TexteFoyers` ne contient pas, à ce moment, une ligne `artisans : `, une ligne `Au chantier : ` suivie d'un nombre et une ligne `Logement des artisans : ` suivie d'un nombre.
5. Il ne déplace pas la caméra : le panneau est attaché à la caméra de la scène, et le plan fixe sert de comparaison. Il laisse passer 10 images avant la photo.

Le codeur regarde lui-même les deux PNG et le dit dans la PR. Le second bloc doit être lisible en entier, sans rien de coupé ni de chevauché, et ses chiffres doivent être ceux du `/lieu` du tick 34.
