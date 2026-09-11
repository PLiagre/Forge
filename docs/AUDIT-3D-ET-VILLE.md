# Audit — la vue 3D et le contrat de ville

Ce document est un **constat daté**, pas un brief et pas une fiche. Il ne dit
pas quoi faire : il dit ce qui a été mesuré le 11 septembre 2026 sur
`vues/relief/` et sur `ville/`, et comment rejouer chaque mesure. Un lot qui
reprend un de ces points écrit son propre brief.

L'état d'un lot ne s'écrit qu'au [registre](../ROADMAP.md#le-registre-des-lots).
Ce fichier n'en change aucun.

## Comment ça a été mesuré

```bash
python3 -m venv /tmp/audit && /tmp/audit/bin/pip install -r requirements.txt
/tmp/audit/bin/python -m pytest vues/relief/tests/ -q
/tmp/audit/bin/python -m vues.relief --ticks 0 --seed 0 --carte /tmp/carte.png
```

Deux choses n'ont **pas** pu être vérifiées, et il faut le dire avant le reste :

- **le rendu forge3d lui-même.** Aucun adaptateur GPU sur cette machine. Tout
  ce qui suit sur `rendu.py` est lu, pas rendu. Les deux sorties `--relief` et
  `--statistique` n'ont jamais été jouées de bout en bout ici.
- **le code C# de `unity/`.** Pas d'éditeur Unity. Les contrats ont été lus et
  comparés au schéma JSON ligne à ligne ; ils n'ont pas été compilés.

---

## Ce qui tient

Six affirmations du dépôt ont été vérifiées mécaniquement, et elles sont vraies.

| ce qui est affirmé | où | vérifié comment |
|---|---|---|
| « quinze contrôles, aucun GPU requis » | `ROADMAP.md` V1-3 | 15 tests, verts en 0,22 s, sans numpy exotique ni carte graphique |
| « six lectures » | `docs/NOTICE.md` | cinq rendent une carte sur la vraie photographie, `bourg` refuse avec le message annoncé |
| « cinq exemples cohérents » | `ville/README.md` | les 5 exemples valident contre leur `$def` en Draft 2020-12, zéro erreur |
| « le SHA-256 porte sur les octets UTF-8 exacts de `payloadJson` » | contrat, § Lecture | l'empreinte de l'exemple **est** le SHA-256 réel de sa charge |
| « `noEngineReferences`, présentation dépendant des seuls contrats » | `CITY_MODE_HOST_API.md` | les `.asmdef` le confirment : `references: []` côté contrats, `["Victoria.CityMode.Contracts"]` côté présentation |
| la matrice de convergence | `UNITY_RENDER_DEPENDENCY_MATRIX.md` | versions, trois empreintes de goldens, 178 175 782 octets et les six chiffres de profil concordent avec `unity-render-convergence-v1.json` |

Le C# et le schéma JSON s'accordent aussi là où ça compte le plus : la table
des politiques de temps (1→0, 2→1000, 3→1..4000) et la table statut/erreur des
reçus sont identiques des deux côtés. La monotonie de la révision est réellement
tenue dans `CityModeSession` (trois gardes), et l'égalité tick/révision sous
`PauseWorld` est réellement exigée à l'ouverture.

---

## La vue 3D — ce qui ne tient pas

### 1. Deux cellules de même valeur reçoivent deux couleurs

`vues/relief/lectures.py:124` — `_echelle_quantile` classe par
`argsort(argsort(v))`. C'est un rang **ordinal** : il n'a pas d'ex æquo. Quatre
cellules qui portent exactement la même population sortent à quatre teintes
différentes.

```python
from vues.relief.lectures import normaliser, Lecture
lec = Lecture("t", "T", "u", "quantile", lambda c: c["v"])
normaliser([5.0, 5.0, 5.0, 5.0, 900.0], lec)[0]
# -> [0.0, 0.25, 0.5, 0.75, 1.0]
```

`docs/NOTICE.md` promet que « la couleur ordonne, elle ne mesure plus ». Elle
n'ordonne pas non plus : elle invente un ordre entre égaux, et cet ordre est
celui de l'index de la cellule dans le tableau, donc un artefact d'écriture du
snapshot.

Sur la photographie réelle à `tick 0`, c'est aujourd'hui mineur et mesurable :
596 cellules, 588 valeurs distinctes, **16 cellules ex æquo (2,7 %)** pour
`population` comme pour `nourriture` ; les deux cellules qui partagent 279
habitants sortent à `t = 0,037` et `t = 0,039`. Le défaut est petit parce que
le monde a peu d'ex æquo, pas parce que le code les traite. Une carte de `faim`
ou de `bourg` — des grandeurs qui se répètent par nature — le verrait en grand.

Aucun test ne couvre le cas des valeurs égales.

### 2. Les cellules non mesurées entrent dans le classement des mesurées

`vues/relief/lectures.py:260` — `normaliser` remplace chaque absence par `0.0`
dans `brutes`, **puis** applique l'échelle au tableau entier. Le rang d'une
cellule mesurée dépend donc du nombre d'absences autour d'elle.

```python
normaliser([0.0, None, None, 0.0, 10.0], lec)[0]
# -> [0.0, 0.25, 0.5, 0.75, 1.0]
#    les deux cellules mesurées à 0.0 sortent à 0,0 et 0,75
```

Le fichier ouvre pourtant sur « une absence n'est pas un zéro (règle 8) ». Elle
n'est pas peinte comme un zéro — ça, `plan()` le tient, et le test le prouve —
mais elle est **comptée** comme un zéro dans le classement, et elle déplace la
couleur des voisines. La règle est tenue à l'affichage et perdue au calcul.

La renormalisation min/max qui suit rattrape le cas simple (toutes les absences
sous toutes les mesures) ; elle ne rattrape pas les égalités.

### 3. Une lecture uniforme envoie un facteur d'échelle absurde à forge3d

`vues/relief/rendu.py:108` — `z_scale = 0.18 * 2.0 / max(altitudes.max(), 1e-6)`.
Quand la grandeur est uniforme, `normaliser` rend `t` tout à zéro (c'est écrit
et assumé, `lectures.py:271`), donc `altitudes.max()` vaut 0, donc le garde-fou
`1e-6` prend la main.

Mesuré sur la photographie réelle à `tick 0` :

| lecture | altitude max | `z_scale` transmis à forge3d |
|---|---:|---:|
| `population` | 2 400,0 m | 0,4 |
| `faim` | 0,0 m | **360 000,0** |

`faim` et `dette` sont uniformes à zéro au `tick 0` — c'est l'état normal d'un
monde qui vient de naître. `python3 -m vues.relief --lecture faim --statistique`
part donc vers forge3d avec un facteur six ordres de grandeur au-dessus du
nominal. Le garde-fou évite la division par zéro ; il ne produit pas un refus,
il produit un nombre. Le champ étant plat, l'image le sera sans doute aussi —
mais personne ne l'a vérifiée, faute de GPU (règle 11).

### 4. `dette` fabrique un zéro là où `densite` refuse

Deux lectures dérivées, un même cas dégénéré, deux traitements opposés :

```python
LECTURES["dette"].valeur({"population": 0, "food_deficit_kg": 5000.0})   # -> 0.0
LECTURES["densite"].valeur({"population": 100, "area_km2": 0.0})         # -> None
```

`_dette_par_habitant` (`lectures.py:186`) rend `0.0` quand la population est
nulle. Une cellule vidée de ses habitants mais chargée de dette est alors
peinte au pas le **plus clair** du dégradé : la moins endettée de la carte.
C'est exactement la règle 8 à l'envers — un zéro qui n'est pas une mesure.
`_bourg` (`lectures.py:209`) a le même réflexe sur un total nul.

### 5. La commande qui prouve la V1-3 ne s'exécute pas

`ROADMAP.md`, tableau des conditions V1 :

```bash
$ python3 -m vues.relief --lecture population --carte carte.png
Il faut --snapshot ou --ticks.
$ echo $?
2
```

La preuve d'une condition de V1 est une commande qui sort en code 2. La forme
correcte existe et marche — elle est dans `docs/NOTICE.md:113`, avec
`--snapshot`. C'est le document de preuve qui est périmé, pas le code.

### 6. `vues/relief/README.md` décrit un paquet qui n'existe plus

Le fichier s'intitule `# visualisateur/` et donne `python3 -m visualisateur`
avec un drapeau `--png`. Le paquet s'appelle `vues.relief` et le drapeau
s'appelle `--relief`.

```bash
$ python3 -m visualisateur --snapshot /tmp/monde.json --png /tmp/monde-3d.png
No module named visualisateur
```

Le même README annonce une exagération verticale « dérivée de l'étendue de la
carte ». Elle est dérivée du **maximum du champ** (`rendu.py:108`), ce qui n'est
pas la même chose : l'étendue kilométrique n'entre nulle part dans le calcul.

### 7. Trois versions de forge3d, et l'épinglage n'est tenu nulle part

| fichier | ce qu'il demande |
|---|---|
| `requirements-3d.txt` | `forge3d==1.36.0`, avec « Épinglé, pas borné : un rendu qui change de version change d'image » |
| `vues/relief/requirements.txt` | `forge3d>=1.35.0` — borné, pas épinglé |
| `docs/NOTICE.md:24`, `vues/relief/README.md` | `python3 -m pip install forge3d` — ni l'un ni l'autre |

`README.md:150` répète la politique : « dépendance **épinglée** ». Aucun des
trois chemins d'installation ne la tient, et `requirements-3d.txt` — le seul qui
la tienne — **n'est cité par aucun fichier du dépôt** : ni un workflow, ni une
notice, ni un README. Un fichier que personne n'installe n'épingle rien.

### 8. Le seul module non testé est celui qui parle à forge3d

L'en-tête de `vues/relief/tests/test_statistique.py` annonce protéger « le
refus : une lecture inconnue, une photographie vide, **un rendu sans GPU** », et
précise : « ce qui est testé, c'est que son absence est un refus propre et pas
une image fausse ».

Aucun test du dépôt n'importe `vues.relief.rendu`. Ni `RenduErreur`, ni
`rendre_png`, ni `rendre_champ_png` n'ont de contrôle. Le refus propre annoncé
par `docs/NOTICE.md:307` — sortie en code 2 quand forge3d manque — n'est vérifié
nulle part, alors qu'il est vérifiable sans GPU : c'est un `ImportError` sur une
machine nue. Règle 4, prouver le rouge d'abord ; règle 7, la présence n'est pas
la fonction.

### 9. Import mort

`vues/relief/__main__.py:98` importe `STOPS_RELIEF`, qui n'est employé nulle
part dans le fichier. `rendre_png` le pose lui-même.

---

## La ville — ce qui ne tient pas

### 1. L'empreinte du snapshot n'est jamais calculée

C'est la garantie centrale du protocole : « le SHA-256 porte sur les octets
UTF-8 exacts de `payloadJson` ». Dans
`unity/Packages/com.victoria.citymode.contracts/Runtime/ForgeHistoryCityModeContracts.cs`,
la seule vérification est `IsSha256` (ligne 456) : **soixante-quatre caractères
hexadécimaux minuscules**. La forme, pas la valeur.

`System.Security.Cryptography` n'est importé nulle part dans le paquet. Un
snapshot dont l'empreinte ne correspond pas à sa charge passe `TryValidate` sans
un mot. La contre-mesure existe dans le document et pas dans le code.

### 2. Le paquet portable des contrats est le seul sans tests

| paquet | tests |
|---|---|
| `com.victoria.citymode` (laboratoire) | 25 fichiers `.cs` |
| `com.victoria.citymode.presentation` | 3 |
| `com.victoria.citymode.assets` | 1 |
| **`com.victoria.citymode.contracts`** | **aucun dossier `Tests/`** |

Les tests qui couvrent la validation du contrat vivent dans
`com.victoria.citymode/Tests/Editor/ForgeHistoryCityModeContractTests.cs` — dans
le bundle que `CITY_MODE_HOST_API.md` désigne comme « laboratoire uniquement » et
qui « ne doit **jamais** être importé dans ForgeHistory ».

L'import minimal documenté livre donc la logique de validation sans aucun de ses
contrôles, et les contrôles ne s'exécutent qu'avec le paquet qu'on a interdit.

### 3. Le schéma JSON est plus strict que le code qui l'implémente

Deux définitions du même contrat, et rien ne vérifie qu'elles s'accordent :

| champ | schéma JSON | validation C# |
|---|---|---|
| `intentKind` | `^[a-z][a-z0-9_.-]{2,127}$` | non vide, rien de plus |
| `sessionId`, `cityId`, `mapCellId`, `intentId`, `returnViewId` | `maxLength: 160` | aucune borne |
| `returnViewStateJson` | `minLength: 2` | non vide |
| `message` | `maxLength: 512` | aucune borne |

Un hôte qui émet `intentKind = "Construction.Place"` ou un `cityId` de 300
caractères passe `TryValidate` et produit une charge que le schéma rejette. La
divergence va toujours dans le même sens : le fil est plus strict que le code
censé le produire.

### 4. Aucune commande de validation publiée n'existe dans ce dépôt

Les trois documents de `ville/` se terminent chacun sur une commande de preuve.
Les cinq fichiers qu'elles appellent sont absents :

```
Tools/validate_forgehistory_city_mode_contract.py     ABSENT
Tools.tests.test_forgehistory_city_mode_contract      ABSENT
Tools/validate_unity_render_convergence.py            ABSENT
Tools.tests.test_unity_render_convergence             ABSENT
Tools/run_unity_locked.py                             ABSENT
Tools/UnityHosts/{Minimal,Transition,Asset}Host       ABSENT
```

Il n'y a pas de dossier `Tools/` dans le dépôt. Les portes de validation
listées par le contrat — dont « schéma et exemples JSON v1 cohérents » — ne sont
tenues par rien ici. Elles passent : c'est vérifié à la main plus haut, et c'est
une bonne nouvelle. Mais rien ne les rejouera au prochain diff.

### 5. Les documents de `ville/` portent encore les chemins de l'ancien dépôt

| cité comme | vit en réalité à | où |
|---|---|---|
| `Docs/Integration/Schemas/forgehistory-city-mode-v1.schema.json` | `ville/Schemas/…` | contrat, l. 70 |
| `Docs/Integration/city-mode-asset-port-v1.json` | `ville/city-mode-asset-port-v1.json` | API hôte, l. 128 |
| `Packages/com.victoria.citymode.contracts/Runtime/…` | `unity/Packages/…` | contrat, l. 68 |
| `Docs/Integration/FORGEHISTORY_CITY_MODE_CONTRACT.md` | `ville/…` | `city-mode-asset-port-v1.json`, `authority.productBoundary` |

Les renvois internes à `ville/` (README vers `Schemas/`, etc.) sont corrects.
Ce sont les chemins **absolus** hérités de VictoriaCityLab qui n'ont pas été
réécrits à la fusion — y compris celui qui, dans le manifeste d'assets, désigne
la frontière produit elle-même.

### 6. `unity/` est le projet laboratoire, pas l'hôte intégré

`UNITY_RENDER_DEPENDENCY_MATRIX.md` distingue trois colonnes. Le projet versionné
ici est la colonne du milieu :

| paquet | `packages-lock.json` du dépôt | « Cible intégrée » du document |
|---|---|---|
| `com.unity.entities` | **absent** | `1.3.15` |
| `com.unity.collections` | `2.5.1` | `2.5.7` |
| `com.unity.burst` | `1.8.19` | `1.8.19` |
| `com.unity.mathematics` | `1.3.2` | `1.3.2` |
| `com.unity.inputsystem` | `1.13.1`, dépendance ferme | adaptateur optionnel |
| `com.unity.ai.navigation` | `2.0.6`, dépendance ferme | adaptateur optionnel |

`2.5.1` et l'absence d'Entities sont exactement ce que le document annonce pour
le « Laboratoire CityLab ». Le dépôt porte donc l'état laboratoire ; l'état
intégré n'existe encore nulle part, et `unity/README.md` ne le dit pas.

S'y ajoute une conséquence mécanique : `com.victoria.citymode` — le bundle
laboratoire — est posé dans `unity/Packages/`, avec un `.asmdef` en
`autoReferenced: true`. Unity charge tout ce qui est dans `Packages/`. Ouvrir
`unity/` charge donc le laboratoire par défaut, alors que le contrat exige que
`LocalCitySimulation`, `CitySaveService` et les fixtures soient « absents ou
inaccessibles dans une session hébergée ».

### 7. L'exemple « accepté » fait avancer l'horloge d'un monde en pause

Dans `forgehistory-city-mode-v1.examples.json`, un seul jeu cohérent est censé
relier les cinq objets :

| objet | tick | révision |
|---|---:|---:|
| `launchContext` (`timePolicy: 1`, `PauseWorld`) | 4800 | 42 |
| `acceptedReceipt` | **4801** | 43 |
| `conflictReceipt` | **4802** | 44 |

La politique 1 est décrite par le contrat comme « monde en pause pendant City
Mode », échelle 0. Le tick avance quand même de deux crans. Le C# ne l'attrape
pas : `TrySubmitIntent` n'interdit qu'une révision ou un tick qui **décroît**.
Le schéma non plus : il n'a aucune contrainte entre objets.

Deux lectures possibles, et il faut trancher : soit `PauseWorld` gèle l'horloge
et les exemples sont faux, soit une intention a le droit de faire avancer le
monde sous pause, et c'est le contrat qui doit le dire. En l'état, « cinq
exemples cohérents » est vrai objet par objet et faux pris ensemble.

### 8. Le manifeste d'assets se dit autoritaire sur onze fichiers absents

`city-mode-asset-port-v1.json` déclare 11 ports source→cible avec empreinte,
taille et licence. Les 11 sources et les 11 cibles sont absentes du dépôt.

C'est attendu — c'est le lot 101, et `unity/README.md` explique très bien
pourquoi les 199 Mo de LFS ne sont pas là. Ce qui manque, c'est que le manifeste
ne le dise pas : il se présente comme « le manifeste autoritaire » reliant « 11
sources approuvées à 11 cibles bit-identiques », sans marquer qu'aucune de ces
empreintes n'est vérifiable ici aujourd'hui.

---

## Récapitulatif

| # | constat | nature | où |
|---|---|---|---|
| 3D-1 | le rang ordinal sépare les valeurs égales | défaut | `lectures.py:124` |
| 3D-2 | les absences entrent dans le classement | défaut | `lectures.py:260` |
| 3D-3 | `z_scale` à 360 000 sur une lecture uniforme | défaut latent | `rendu.py:108` |
| 3D-4 | `dette` rend `0.0` au lieu de refuser | règle 8 | `lectures.py:186` |
| 3D-5 | la commande de preuve V1-3 sort en code 2 | doc périmée | `ROADMAP.md` |
| 3D-6 | README d'un paquet renommé | doc périmée | `vues/relief/README.md` |
| 3D-7 | trois versions de forge3d, épinglage non tenu | dérive | `requirements-3d.txt` et al. |
| 3D-8 | `rendu.py` n'a aucun test | manque | `vues/relief/tests/` |
| 3D-9 | import mort | propreté | `__main__.py:98` |
| V-1 | le SHA-256 n'est jamais calculé | manque | `ForgeHistoryCityModeContracts.cs:456` |
| V-2 | les contrats portables n'ont pas de tests | manque | `com.victoria.citymode.contracts` |
| V-3 | schéma plus strict que le C# | divergence | schéma ↔ `.cs` |
| V-4 | aucune commande de validation n'existe | manque | `ville/*.md` |
| V-5 | chemins de l'ancien dépôt | doc périmée | `ville/*.md`, manifeste |
| V-6 | `unity/` est le laboratoire | état non dit | `unity/Packages/` |
| V-7 | tick qui avance sous `PauseWorld` | incohérence | exemples |
| V-8 | manifeste autoritaire sur des fichiers absents | état non dit | `city-mode-asset-port-v1.json` |

Les quatre qui touchent au comportement observable du produit, et pas à sa
documentation, sont **3D-1, 3D-2, 3D-4 et V-1**. Les autres sont des écarts entre
ce que le dépôt dit de lui-même et ce qu'il fait.
