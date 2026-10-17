# Lot #679 — Le pont sait quelle capitale ouvrir
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
Le pont Unity sait, en lisant le service, où le jeu doit mener le joueur : à l'écran de départ s'il n'a pas encore choisi de terre, dans la ville de sa capitale à la cellule de son siège si sa terre a un kit, ou vers « pas encore de kit pour cette terre » sinon.

## Le joueur
Lot de fond, premier sous-lot de #409 « Le jeu ouvre la capitale du joueur ». Il prépare le geste du J4 de `CAP.md` : le joueur **entre dans sa capitale en 3D** et passe de la carte à sa ville d'un geste. Au Zab, c'est Biskra, dans la scène du ksar ; les autres terres attendent leur kit (jalon 9) et se gouvernent depuis la carte. Ce lot décide seulement où aller ; il ne change rien à l'écran. Les sous-lots suivants de #409 le rendent visible : la ville ouverte au siège (Biskra, cellule 10103), puis la carte qui ouvre la capitale ou dit « pas encore de kit pour cette terre ».

## Règle du monde
Sans objet : c'est un lecteur de vue. Le monde ne change pas, ni son niveau de fidélité. Le lot s'appuie sur `jeu/sim/MODELE.md`, sections « Les maisons servies, vue dérivée » (`/maison?id=`, siège hors carte avec `absents["siege"]`) et « Les seigneuries de départ, vue dérivée » (le Zab est la seigneurie 6, maison servie `seigneurie-6`). La maison du joueur vient de `GET /monde` (`maison_du_joueur`, absente sans choix) ; la cellule vient de `siege.cell_id` de sa fiche, jamais d'une constante. `cell_id` reste la seule clé spatiale.

La liste des terres qui ont un kit est un fait de la vue, pas du monde : seul le Zab a un kit, celui du désert. Aucune table des kits n'existe encore, ni dans les données ni dans le service. Elle est déclarée ici, avec pour clé l'identifiant de maison servi. Dépend de #407 (le Zab), #602 (`/maison`) et #610/#611 (`ClientMaison`, `ClientMonde.LireAvecMaison`), tous sur master.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/CapitaleDuJoueur.cs
3d/unity/Assets/ForgeLocal3D/Pont/CapitaleDuJoueur.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/CapitaleDuJoueurTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/CapitaleDuJoueurTests.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/maison-zab-graine0-tick0.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/maison-zab-graine0-tick0.json.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/maison-bar-graine0-tick0.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/maison-bar-graine0-tick0.json.meta
jeu/sim/tests/test_maisons_servies.py

Tout autre chemin est interdit. Côté Python, le lot ajoute seulement un test, dans le fichier qui porte déjà l'invariant de `/maison`, sans changer aucune ligne existante. Les `.meta` sont générés par Unity, avec des GUID uniques.

Budget : environ 65 lignes de code, 110 de tests C#, 15 de test Python, 20 de fixtures et de `.meta`, 60 de brief. Le code réutilise `ClientMonde`, `ClientMaison` et `Lecture<T>` sans modifier leurs fichiers. Les tests reprennent le faux service `HttpListener` des tests du pont.

## Conditions de succès
**SC1 — les fixtures viennent du vrai service.**

Commande : `python3 -m pytest jeu/sim/tests/test_maisons_servies.py -q -k fiches_figees_du_pont` (Windows : `py -m pytest` avec les mêmes arguments).

Le codeur prélève une seule fois les octets de `GET /maison?id=seigneurie-6` et de `GET /maison?id=seigneurie-1` sur le vrai service : graine 0, horloge arrêtée, tick 0. Il les enregistre sans reformatage et sans fin de ligne ajoutée.

Le test `test_fiches_figees_du_pont` relit les deux fixtures depuis la racine du dépôt. Avec `lancer_service(0)` et `requete_service`, il exige :
- le statut 200 ;
- des octets égaux aux fixtures ;
- après `POST /tick?n=1`, une fiche du Zab différente ;
- dans les fixtures, `siege.cell_id` 10103 pour le Zab et 10430 pour Bar ;
- l'identifiant du Zab égal à `seigneurie-<id>` de la ligne « Émirat du Zab » de `charger_seigneuries()`, sans écrire 6 en dur.

Le test n'écrit jamais les fixtures. La commande recueille exactement un test.

Contre-épreuve : changer un chiffre de la fixture du Zab fait échouer la comparaison.

Relevé fait dans ce chantier, pour la provenance seulement (ce ne sont pas des références de test) :
- Zab : 555 octets, SHA-256 `9805cc08…011b4f` ;
- Bar : 556 octets, SHA-256 `3aef8623…210cdf`.

**SC2 — la table des kits ne connaît que le Zab, et sa scène est au build.**

Commande PC (Unity 6000.0.43f1) : `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults <temp>/pont.xml -logFile <temp>/pont.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec, et des cas `CapitaleDuJoueurTests` réellement exécutés ; zéro cas est un échec.

Dans `Forge.Pont`, créer `TerresAvecKit`, une table immuable et publique (`IReadOnlyDictionary<string,string>`) qui va de l'identifiant de maison au nom de scène. Elle a une seule entrée : `seigneurie-6` → `Forge_Desert_Ville_ksar_des_sept_puits`.

Le test exige :
- exactement une clé ;
- une clé égale à l'`id` lu dans la fixture du Zab ;
- une scène présente et active dans `EditorBuildSettings.scenes` ;
- aucune clé égale à l'`id` de la fixture de Bar.

Contre-épreuve : ajouter Bar à la table, ou nommer une scène absente du build, fait rougir le test.

**SC3 — l'aiguillage rend la bonne destination.**

Commande : celle de SC2.

Créer `AiguillageDeCapitale.Lire(int port, TimeSpan delai)`, qui rend `Lecture<CapitaleAOuvrir>`. `CapitaleAOuvrir` est immuable et expose :
- `Destination` : une énumération `Depart`, `Ville` ou `PasDeKit` ;
- `Maison` : nul pour `Depart` ;
- `Scene` et `Cellule` (`long?`) : renseignés seulement pour `Ville`.

L'aiguillage lit d'abord `ClientMonde.LireAvecMaison()`. Il ne lit `ClientMaison.Lire(maison)` que si la maison est dans `TerresAvecKit`. Le faux service répond selon le chemin. Le `/monde` des tests est un corps minimal valide (une cellule), avec ou sans `maison_du_joueur`. `/maison?id=` sert les fixtures relues du disque. Le test retient les requêtes reçues.

| cas | attendu |
|---|---|
| sans maison (`/monde` sans la clé ; `/maison` sert quand même le Zab) | `Depart` ; requêtes exactement `["GET /monde"]` |
| Zab | `Ville`, maison `seigneurie-6`, scène du ksar, cellule 10103 ; requêtes `GET /monde` puis `GET /maison?id=seigneurie-6` |
| Zab, avec `siege.cell_id` de la fixture changé en 10104 (seul le siège change, les lieux gardent 10103) | `Ville`, cellule 10104 |
| Bar (`/maison` sert la fixture de Bar) | `PasDeKit`, maison `seigneurie-1`, cellule nulle ; requêtes exactement `["GET /monde"]` |
| maison inconnue `seigneurie-99` | `PasDeKit` |

Contre-épreuves :
- une cellule écrite en dur (10103, ou `PanneauLieu.CELLULE_PAR_DEFAUT`) ou lue dans `lieux[0]` fait rougir le cas 10104 ;
- un aiguillage qui ouvre tout siège servi fait rougir le cas de Bar ;
- un aiguillage qui confond « pas de maison » et « pas de kit » fait rougir le premier cas.

**SC4 — un service absent ou fautif ne mène jamais nulle part.**

Commande : celle de SC2.

Une absence de `Lecture` commence par la cause de son client (`monde : ` ou `maison : `). Elle n'est jamais une destination de remplacement : ni `Depart`, ni `Ville` à une cellule par défaut, ni `PasDeKit`.

| cas | attendu |
|---|---|
| port sans service | absence contenant `monde : service absent` |
| `/monde` statut 500 | absence contenant `monde : statut 500` |
| Zab, `/maison` statut 500 | absence contenant `maison : statut 500` |
| Zab, `/maison` sert la fiche de Bar | absence `maison : clé id` |
| Zab, siège hors carte (`cell_id`, `rang` et `point` à null, `absents.siege` = `hors_carte`) | absence qui contient `hors_carte` |

Le délai et le port sont refusés comme dans `ServiceLocal`.

Contre-épreuve : rendre `Depart` quand le service est absent, ou `Ville` à 1175 quand la fiche manque, fait rougir ces cas. Écrire et constater ces tests rouges avant d'implémenter, puis obtenir le vert.

**SC5 — les invariants existants restent verts.**

Commandes : `python3 -m pytest jeu -q` et la commande de SC2 pour toute l'assemblée `Forge.Pont.Tests`.

Aucun test existant n'est retiré, renommé ou assoupli. Le relevé des cas Unity se compare à celui d'avant le lot. Le diff reste sous 300 lignes et ne touche que le périmètre et ce brief.

Contre-épreuve : `git diff --name-only origin/master` ne liste aucun autre chemin.

## Hors périmètre
- Charger une scène, lire `-forgeCell`, changer `DesertRoadTool`, `OuvertureDeLaCarte`, `PanneauLieu`, la carte, `CabinetDeCarte` ou une scène : ce sont les sous-lots suivants de #409.
- Afficher « pas encore de kit », changer le lanceur (`pc/`, `test_lanceur_jouer.py`), le relief de Biskra, l'épreuve Zab/Bar.
- Toute table des kits côté service ou données, toute nouvelle clé servie, tout changement du monde ou de `MODELE.md`.
- Toute lecture asynchrone ou en cache.

## Photo
Sans objet : ce lot ne change rien de ce qu'on voit à l'écran, et aucune vue n'appelle encore l'aiguillage. Aucun `Lot679.cs` n'est ajouté. Le sous-lot de #409 qui ouvre la ville au siège portera la photo de Biskra.
