# Lot #689 — La carte décide d'ouvrir la capitale ou de dire « pas encore de kit »
Jalon : J4 · Machine : pc · Taille prévue : 290 lignes

## But
Un composant du pont, `PassageALaCapitale`, sait mener le joueur de la carte à sa capitale au moment où il confirme une terre qui a un kit, ou lui dire « Pas encore de kit pour cette terre » quand elle n'en a pas.

## Le joueur
Lot de fond, sous-lot 1 de #681 (lui-même sous-lot 3 de #409 « Le jeu ouvre la capitale du joueur »). Il prépare le geste du J4 de `CAP.md` : le joueur **passe de la carte à sa ville d'un geste**. Au Zab, il confirme sa terre sur la carte et, au tick suivant, il entre dans Biskra, la scène du ksar. À Bar, la carte lui dit « Pas encore de kit pour cette terre » : il sait qu'il gouvernera depuis la carte (les autres terres attendent leur kit, jalon 9). Ce lot écrit la décision et le panneau, sans les poser sur la carte. Le sous-lot 2 de #681 les pose sur `Forge_Carte` et photographie Bar choisi.

## Règle du monde
Sans objet : c'est un lecteur de vue. Le monde, `jeu/sim/MODELE.md` et le niveau de fidélité ne changent pas. La maison confirmée vient de `GET /monde` (`maison_du_joueur`, absente tant qu'aucun choix n'est appliqué). La scène vient de `TerresAvecKit`, par `AiguillageDeCapitale.Lire` (#679, sur master). Rien n'est écrit en dur.

Règle de la vue, retenue au découpage de #681 :
- la ville ne s'ouvre que sur une confirmation **vue** : une lecture `Depart`, puis une lecture `Ville` ;
- un Zab déjà confirmé à la première lecture ne renvoie pas en ville, sinon #410 ne pourrait plus revenir de la ville à la carte ;
- le panneau s'affiche dès qu'une lecture rend `PasDeKit`, à l'ouverture comme après un choix. Il se cache sur une lecture `Depart` ou `Ville` ;
- une absence (service absent, statut fautif) n'arme rien, ne désarme rien, ne montre ni ne cache rien.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/PassageALaCapitale.cs
3d/unity/Assets/ForgeLocal3D/Pont/PassageALaCapitale.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PassageALaCapitaleTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PassageALaCapitaleTests.cs.meta

Tout autre chemin est interdit. Les `.meta` sont générés par Unity, avec des GUID uniques. Les fixtures `maison-zab-graine0-tick0.json` et `maison-bar-graine0-tick0.json` sont lues, jamais modifiées.

Budget : environ 85 lignes de composant, 105 de tests, 4 de `.meta`, 95 de brief ; le style dense des tests du pont tient dans ce compte. Modèle à suivre : `HorlogeDeCarte`, pour `Demarrer(Camera)`, `Pas(double)`, `Arreter()`, la tâche en vol et la toile `ScreenSpaceCamera`. Les tests suivent `HorlogeDeCarteTests` et `CapitaleDuJoueurTests` (faux service `HttpListener`, `Fige`, `Id`).

## Conditions de succès
Commande unique, sur le PC (Unity 6000.0.43f1) : `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults <temp>/pont.xml -logFile <temp>/pont.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec, et des cas `PassageALaCapitaleTests` réellement exécutés : zéro cas est un échec. Écrire les tests et les voir rouges avant le composant.

Le composant, en `[DefaultExecutionOrder(10)]` comme l'horloge, expose :
- `port` (défaut `PanneauLieu.DEFAULT_SERVICE_PORT`), `camera` (vide : celle de la `CarteDessinee` du même objet) ;
- `PERIODE_LECTURE_S` = 1, `MESSAGE_SANS_KIT` = « Pas encore de kit pour cette terre » ;
- `ChargerScene` (`Action<string>`, défaut `nom => SceneManager.LoadScene(nom)`), que les tests remplacent par un compteur ;
- `Demarrer(Camera)`, `Pas(double maintenant)`, `Arreter()` ;
- `RequeteEnVol`, `Absence`, `PanneauVisible`, `TexteAffiche`, `SceneDemandee` (nulle tant que rien n'est chargé).

`Pas` lance `AiguillageDeCapitale.Lire(port, 5 s)` par `Task.Run`, une lecture à la fois, au plus une par période. Il applique la lecture finie au pas suivant. Une fois la scène demandée, plus aucune lecture ne part.

**SC1 — Zab confirmé après une lecture sans maison ouvre le ksar, une seule fois.**
Le faux service sert `/monde` sans `maison_du_joueur` pendant deux pas, puis avec `maison_du_joueur` égal à l'`id` de la fixture du Zab ; `/maison?id=` sert la fixture. Après plusieurs pas, on exige :
- `ChargerScene` appelé exactement une fois, avec `TerresAvecKit.Scenes[id du Zab]` ;
- `SceneDemandee` égale à cette scène ;
- panneau jamais visible ;
- aucun `GET /monde` reçu après la demande.

Contre-épreuve : un composant qui recharge à chaque lecture `Ville` fait rougir « une fois » et « aucun GET ».

**SC2 — Bar affiche le panneau, qui survit au geste du cabinet.**
L'objet du test porte le composant et une toile enfant témoin, comme l'horloge. Après sans maison puis Bar, on exige :
- `PanneauVisible`, et `TexteAffiche` égal à `MESSAGE_SANS_KIT` ;
- `ChargerScene` jamais appelé.

Le test refait ensuite le geste de `CabinetDeCarte.Construire` : `SetActive(false)` sur chaque `GetComponentsInChildren<Canvas>()` de l'objet. Il exige alors :
- la toile témoin cachée (preuve que le geste a porté) ;
- la toile du panneau toujours `activeInHierarchy`, sans parent ;
- une toile en `ScreenSpaceCamera`, sur la caméra donnée ;
- un `CanvasScaler` `ScaleWithScreenSize` 1920×1080, `matchWidthOrHeight` 0, comme le cabinet.

Pour le cadre, ancrage et pivot en (1, 1). Avec la caméra du cabinet à 0,67 de 1920 de large, le test exige :
- bord gauche 0,67 × 1920 + `anchoredPosition.x` − `sizeDelta.x` ≥ 764 (fin des feuillets, `Feuillet.cs`) ;
- haut −`anchoredPosition.y` ≥ 100 (bandeau) ;
- bas −`anchoredPosition.y` + `sizeDelta.y` ≤ 872 (guide).

Ces nombres sont écrits dans le test avec leur fichier d'origine en commentaire : `Forge.Pont` ne voit pas `Forge.Interface`. Valeurs conseillées : position (−24, −124), taille (474, 112), texte replié sur deux lignes au besoin.

Contre-épreuve : une toile enfant du composant disparaît avec la toile témoin.

**SC3 — une terre déjà confirmée à l'ouverture.**
- Zab servi dès la première lecture, sur plusieurs pas : `ChargerScene` jamais appelé, panneau caché, et au moins un `GET /monde` reçu (il a bien lu).
- Bar servi dès la première lecture : panneau visible.
- Puis `/monde` sans maison : panneau caché.

Contre-épreuve : armer la transition sans lecture `Depart` fait rougir le cas du Zab.

**SC4 — une absence n'arme rien, et la lecture ne bloque pas.**
- Sans service pendant plusieurs pas : `Absence` non nulle et commençant par `monde : `, panneau caché. Puis le service démarre et sert le Zab : `ChargerScene` jamais appelé.
- Faux service qui attend 500 ms avant de répondre : dix appels à `Pas`, à des instants espacés d'une période, retournent en moins de 200 ms au total, et un seul `GET /monde` est reçu.
- `Demarrer(null)` journalise une erreur (`LogAssert.Expect`) et aucune lecture ne part.

Contre-épreuve : une lecture faite dans `Pas` même, ou une absence prise pour `Depart`, fait rougir ces cas.

**SC5 — les invariants existants restent verts.**
La commande, sur toute l'assemblée `Forge.Pont.Tests`, et `python3 -m pytest jeu -q`. Aucun test existant n'est retiré, renommé ou assoupli ; `CapitaleDuJoueurTests` est inchangé. Contre-épreuve : `git diff --name-only origin/master` ne liste que le périmètre et ce brief.

## Hors périmètre
- Poser le composant sur `Forge_Carte`, toucher `CabinetDeCarte`, `Assets/Interface/`, une scène ou une capture : c'est le sous-lot 2 de #681.
- Changer `AiguillageDeCapitale`, `TerresAvecKit`, `OuvertureDeLaCapitale`, `DesertRoadTool` ou `HorlogeDeCarte`.
- La cellule sur laquelle la ville s'ouvre : elle relit l'aiguillage elle-même (#688). Dans l'éditeur, elle ouvre 1175 par la règle de #687 ; c'est à l'épreuve de #409 d'en juger.
- Le retour de la ville à la carte (#410), le lanceur (#682), le relief (#683).
- Le chevauchement avec le panneau de l'horloge quand aucun cabinet ne cache celui-ci.

## Photo
Sans objet : le composant n'est posé sur aucune scène, donc rien ne change à l'écran. Aucun `Lot689.cs` n'est ajouté. Le sous-lot 2 de #681 pose le composant sur la carte et photographie Bar choisi, avec le panneau visible et le cabinet construit.
