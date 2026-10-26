# Lot #695 — Le pont lit le relief de chaque cellule
Jalon : J4 · Machine : pc · Taille prévue : 150 lignes

## But
Le pont Unity sait relire, pour chaque cellule de la carte de 1400, sa classe de relief servie par `GET /carte`, et refuse une carte dont le relief est fautif en nommant le chemin de la clé.

## Le joueur
Lot de fond, sous-lot 1 de #683 « Le terrain de la capitale suit le relief de sa cellule » (lui-même sous-lot 5 de #409 « Le jeu ouvre la capitale du joueur »). Il prépare le geste du J4 de `CAP.md` : le joueur **entre dans sa capitale en 3D**, la ville que tient le monde, pas un décor. Au Zab, Biskra (cellule 10103) est en montagne. Il doit voir un ksar sur un terrain plus raide qu'une ville de plaine, et ses routes doivent en payer la pente. Ce lot donne au jeu le relief de chaque cellule, celui que le monde lit déjà pour ses récoltes et ses convois. Seul, il ne change aucun écran. Le sous-lot 3 de #683 (`DesertRoads`, l'outil et la photo de Biskra) l'appliquera au terrain de la capitale et le rendra visible.

## Règle du monde
Sans objet : lecture de vue, le monde ne change pas. Le contrat vient de `jeu/sim/MODELE.md`, « La carte et les terres servies, vue dérivée ». Chaque cellule de `/carte` porte exactement `cell_id`, `contour`, `relief`, `puissance`, `maison` et `villes`. `relief` est la classe de la cellule dans `world.carte` (`carte_servie.py`, l. 117). Le moteur refuse une classe nulle ou inconnue (`engine.py`, `_facteur_relief_pour_cellule`) : le service sert donc toujours un texte. Sur la fixture `carte-graine0.json` (596 cellules), on compte plaine 322, colline 162, montagne 77, marais 20, haute_montagne 15 ; 1175 est en plaine et 10103 en montagne. Unity relit la classe telle quelle. Il ne la traduit en aucun facteur et n'en vérifie pas la liste des classes : c'est l'affaire du sous-lot 3 et de `routes.PARAMETRES` (sous-lot 2, Python). Aucune constante, règle ni fidélité du monde ne change.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientCarte.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientCarteTests.cs
docs/briefs/695-le-pont-lit-le-relief-de-chaque-cellule.md

Tout autre chemin est interdit. Les fixtures `carte-graine0.json` et la chaîne `CARTE_TROIS` des tests sont lues, jamais modifiées. Les quatre autres appelants de `new CelluleDeCarte(…)` (tous dans `Pont/Tests/`) ne sont pas touchés : ils doivent compiler tels quels.

Ce que fait le code :
- `CelluleDeCarte` gagne une propriété en lecture seule `string Relief`, et son constructeur un paramètre facultatif **en dernière position** : `string relief = null`. Le constructeur ne le valide pas : `null` dit « relief non servi ».
- `ClientCarte.Cellule` lit `relief` après `villes` et le passe au constructeur. La lecture suit les règles suivantes :
  - clé absente : `Relief == null`, la carte reste présente. C'est ce qu'exige `LesClesQueLeClientNeLitPasNeSontPasExigees`, qui retire le relief de 10196 ;
  - clé présente avec un texte non vide : la classe est gardée telle quelle, sans `Trim` ni changement de casse ;
  - clé présente avec toute autre valeur (`null`, nombre, booléen, tableau, objet, texte vide ou blanc) : `CleRefusee` avec `Refus(chemin + ".relief", "un texte non vide", valeur)`. Toute la carte est alors refusée (`Absence` « carte : clé cells[i].relief : un texte non vide attendu, reçu … »).
- Une petite aide locale, par exemple `TexteFacultatif`, peut lire une clé facultative. Les aides existantes (`Valeur`, `Texte`, `Refus`, `Decrire`) ne changent pas de comportement.

Budget : environ 12 lignes de client, 50 lignes de tests ajoutées, 85 lignes de brief.

## Conditions de succès
Commande de toutes les SC, sur le PC, depuis la racine, avec Unity 6000.0.43f1 du projet, en PowerShell :
```powershell
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot695.xml" -logFile "$env:TEMP\lot695.log"
```
Sans `-quit`. Attendre la fin du processus, puis exiger :
- la sortie 0 ;
- un XML neuf, sans échec ni cas ignoré ;
- chaque nouveau cas de `ClientCarteTests` présent dans le XML et réellement exécuté. Zéro cas nouveau compte comme un échec.

Écrire les cas d'abord et constater leur rouge, y compris à la compilation tant que `Relief` manque.

**SC1 — Le relief servi est relu, cellule par cellule.** Nouveau test `LeReliefDeChaqueCelluleEstRelu` sur `CARTE_TROIS` : on exige `Relief` égal à `"plaine"`, `"montagne"`, `"plaine"` pour 10134, 10196 et 10417, dans cet ordre. Un second test, `LeReliefDeLaCarteServieEstReluSurToutesSesCellules`, sert les octets de `carte-graine0.json` par le faux service `Servir`. Il exige :
- 596 cellules, aucune de `Relief` nul ;
- le compte par classe exact : plaine 322, colline 162, montagne 77, marais 20, haute_montagne 15 ;
- `Relief == "montagne"` pour la cellule 10103 (Biskra) et `"plaine"` pour 1175.

Les attentes sont écrites en dur, mesurées sur la fixture, jamais tirées du lecteur. Contre-épreuves :
- un lecteur qui rend toujours `null`, ou toujours le relief de la première cellule, fait rougir SC1 ;
- un lecteur qui fait `ToUpper` ou `Trim`, ou qui remplace `haute_montagne` par `montagne`, fait rougir le compte par classe.

**SC2 — Une clé absente donne un relief nul, pas un refus.** Nouveau test `UnReliefAbsentDonneUnReliefNul` : il retire `"relief":"montagne",` de `CARTE_TROIS` par `RemplacerUneFois`, puis exige :
- une carte présente, `Absence == null` ;
- `Relief == null` pour 10196 ;
- `"plaine"` pour 10134 et 10417 ;
- `Cellule10196` vert, contour et identités intacts.

`LesClesQueLeClientNeLitPasNeSontPasExigees` reste vert sans une ligne changée. Contre-épreuve : lire `relief` par `Valeur` (clé exigée) fait rougir ce cas et le test existant.

**SC3 — Un relief présent mais fautif refuse la carte en nommant son chemin.** On ajoute des lignes `[TestCase]` à `UneCarteFautiveEstRefuseeEnNommantSonChemin`, sans toucher ses lignes existantes ni son corps. Les cas :
- `"relief":"montagne"` → `"relief":3` : chemin `cells[1].relief`, précision « un texte non vide attendu, reçu Double » ;
- `"relief":"montagne"` → `"relief":null` : `cells[1].relief`, « reçu null » ;
- `"relief":"montagne"` → `"relief":""` : `cells[1].relief`, « un texte non vide » ;
- `"relief":"montagne"` → `"relief":true` : `cells[1].relief`, « un texte non vide » ;
- `"relief":"montagne"` → `"relief":["montagne"]` : `cells[1].relief`, « un texte non vide » ;
- `"nom":"France"},"relief":"plaine"` → `"nom":"France"},"relief":{}` : `cells[2].relief`, « un texte non vide ». Ce cas prouve que le chemin porte l'indice de la cellule fautive, pas celui de la première.

Chaque motif ancien paraît exactement une fois dans `CARTE_TROIS`, et `RemplacerUneFois` le vérifie déjà. Contre-épreuves :
- un lecteur qui prend `null` pour une clé absente fait rougir le cas `null` ;
- un lecteur qui fait `ToString()` sur la valeur fait rougir le cas nombre ;
- un chemin codé en dur sur `cells[1]` fait rougir le cas `cells[2]`.

**SC4 — La cellule se fabrique avec ou sans relief.** Nouveau test `UneCelluleSeFabriqueAvecOuSansRelief`. On exige :
- `new CelluleDeCarte(1, polygones, null, null, new VilleDeCarte[0])` compile et rend `Relief == null` ;
- le même appel avec `"colline"` en dernier argument rend `Relief == "colline"`.

`UneCarteNeSeFabriqueNiSansListeNiSansNomNiSansCause` reste inchangé et vert. Contre-épreuve : un paramètre obligatoire, ou placé ailleurs qu'en fin de liste, casse la compilation des quatre appelants de `Pont/Tests/`, donc toute l'assemblée.

**SC5 — Périmètre et taille tenus, aucun test assoupli.** Commandes :
- `git diff --check` ;
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` : seuls les trois chemins du Périmètre ;
- `git diff --numstat origin/master` : moins de 300 lignes ajoutées et supprimées en tout, ce brief compris ;
- `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientCarteTests.cs` : rien que des lignes ajoutées (aucune ligne `-`).

Le relevé des cas du XML se compare à celui d'avant le lot : mêmes cas, plus les nouveaux. Contre-épreuve : un chemin de plus, une ligne de test existante retirée ou modifiée, ou un total ≥ 300 refuse la livraison.

## Hors périmètre
- Le service Python, `carte_servie.py`, `MODELE.md` et les fixtures.
- La traduction du relief en facteur de hauteur, le pivot de la guelta et le fondu 400→500 m : ce sont les sous-lots 2 (Python) et 3 (`DesertRoads`, l'outil, la photo de Biskra) de #683.
- Toute vérification de la liste des classes côté Unity.
- Tout usage du relief par `CarteDessinee`, `FicheDeCellule`, le cabinet, `PassageALaCapitale` ou la scène du désert : aucun affichage ni teinte de relief sur la carte.
- Toute nouvelle requête HTTP et tout changement des autres clients du pont.

## Photo
sans objet : ce lot ajoute une donnée au client `/carte` et ses tests, sans rien brancher à une scène. Rien de ce qu'on voit à l'écran ne change. La photo de Biskra sur un terrain relevé selon sa montagne viendra au sous-lot 3 de #683, qui portera son scénario de capture.
