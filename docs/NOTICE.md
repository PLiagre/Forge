# Notice d'utilisation

> Tout ce qu'on peut lancer, dans l'ordre où on en a besoin. Les sorties citées
> sont des exemples. La chaîne d'agents (pilote, rôles, lots) est décrite dans
> [WORKFLOW.md](WORKFLOW.md) et [CLAUDE.md](../CLAUDE.md).

---

## 0. Ce dont on a besoin

| pour | il faut |
|---|---|
| le moteur | **Python 3.11+**, et rien d'autre |
| le tableau de bord, la chronique | Python seul ; Chromium et ffmpeg **seulement** pour la vidéo |
| la carte de statistique | `numpy`, `pillow` |
| le rendu 3D | en plus : `forge3d`, et un GPU |
| les tests | `pytest` |
| la ville | **Unity 6000.0.43f1** + URP 17.0.4, sur Windows |

Le moteur ne dépend de rien. C'est voulu, et c'est vérifié : `jeu/sim/` n'importe
que la bibliothèque standard, pour qu'il tourne sur une machine nue.

**Toutes les commandes du jeu se lancent depuis le dossier `jeu/`** (`cd jeu`),
où vivent `sim/`, `vues/`, `forge/`, `ville/` et `data/`. Les tests se lancent
aussi depuis la racine du dépôt, en préfixant leurs chemins par `jeu/`.

```bash
python3 -m pip install pytest numpy pillow       # tests, carte
python3 -m pip install forge3d                   # rendu 3D seulement
```

---

## 1. La commande qui fait tout

C'est la porte de la V1 : une simulation, trois vues.

```bash
python3 -m forge --ticks 365 --seed 0 --sortie sortie
```

Elle écrit cinq fichiers :

```
sortie/monde.json      la photographie — la seule source des trois vues
sortie/carte.png       la carte de 1400 — densités, frontières, villes, terre choisie et sa fiche ; capitales de l'IA, voisines et gestes (avec --ia)
sortie/tableau.svg     le tableau de bord, en preuve dessinée
sortie/planche.html    la chronique : la suite des instants
sortie/resume.json     ce que la commande a mesuré
```

Ce qu'elle imprime, mesuré sur une année complète :

```json
{"ticks": 365, "seed": 0, "cellules": 596,
 "population_depart": 36969739, "population_arrivee": 38330077,
 "part_survivante": 1.0368, "plafond_de_survie_a_l_amorcage": 1.2505,
 "secondes": 21.28}
```

Deux nombres à lire en premier :

- **`plafond_de_survie_a_l_amorcage`** doit être **≥ 1**. En dessous, le monde
  amorce plus de bouches que sa terre n'en nourrit, et ce qu'on affiche est un
  effondrement, pas une partie.
- **`part_survivante`** dit ce que l'année a fait de la population. Au-dessus
  de 1, le monde croît.

Options utiles :

```bash
--lecture faim          la grandeur des vues (par défaut : densité pour la carte, population pour le tableau)
--pas 15                un instant de chronique tous les N ticks
--sans-chronique        sauter la planche : elle rejoue le monde, donc le paie deux fois
--largeur 1400          finesse du raster de la carte
```

---

## 2. Le moteur seul

```bash
# le monde à t0, sans jouer un tick — le test de fumée
python3 -m sim --ticks 0 --json
```

```json
{"cellules": 596, "population_depart": 36969739, "population_arrivee": 36969739,
 "stock_kg_depart": 369697390.0, "ticks": 0, "seed": 0, "sans_unity": true}
```

```bash
python3 -m sim --ticks 365 --seed 0 --json      # une année, ~21 s
python3 -m sim --ticks 60 --seed 7 --json       # une autre graine, un autre monde
```

Même graine, même monde : le moteur est déterministe, et un test le protège.

Photographier sans afficher :

```bash
python3 -m sim --ticks 0 --seed 0 --snapshot-json monde.json
```

Une **photographie** est un document JSON déterministe : la carte figée, plus
l'état que le moteur a fait évoluer. C'est le seul objet que les vues lisent —
aucune vue ne parle au moteur.

---

## 3. Les trois vues

### 3a. La carte de statistique

Le monde colorié par une de ses grandeurs. Aucun GPU.

```bash
python3 -m vues.relief --snapshot monde.json --lecture population --carte carte.png
```

Six lectures :

| lecture | ce qu'elle montre | échelle |
|---|---|---|
| `population` | habitants par cellule | par rang |
| `densite` | densité en habitants au km², lue dans la photographie | par rang |
| `nourriture` | stock de nourriture, en kg | par rang |
| `faim` | ticks de faim consécutifs | linéaire |
| `dette` | dette alimentaire par habitant | logarithme |
| `bourg` | part des habitants du bourg | linéaire — **refuse** sans le champ `bourg` |

`bourg` refuse sur un snapshot qui ne porte pas la donnée : la lecture est
déclarée, et son refus est l'inventaire honnête de ce qui manque.

**Pourquoi l'échelle « par rang ».** Les populations vont de 5 à 269 000
habitants et se serrent près du haut. En linéaire, presque tout le continent
prend le pas le plus clair ; en logarithme, presque tout prend le plus foncé.
Les deux rendent une image d'une seule couleur. Le rang garantit que le dégradé
sert sur toute sa longueur. Ce qu'il coûte : la couleur ordonne, elle ne mesure
plus — les bornes chiffrées de la légende restent la seule source des
magnitudes.

### 3b. Le tableau de bord

```bash
python3 -m vues.tableau --snapshot monde.json --port 8000
# puis http://localhost:8000
```

```bash
python3 -m vues.tableau --snapshot monde.json --compare monde-an1.json
python3 -m vues.tableau --snapshot monde.json --proof-svg preuve.svg --layer population
```

### 3c. La chronique — la suite des instants

Le tableau montre **un** instant ; la chronique montre leur suite.

```bash
python3 -m vues.chronique --ticks 180 --pas 4 --html planche.html

# garder la chronique pour la redessiner sans resimuler
python3 -m vues.chronique --ticks 180 --pas 4 --json chronique.json
python3 -m vues.chronique --chronique chronique.json --html planche.html

# en faire une vidéo — demande Chromium et ffmpeg
python3 -m vues.chronique --chronique chronique.json --html p.html \
        --bobine monde.webm --bobine-lecture faim
```

Un instant précis se demande par l'adresse : `planche.html?image=12&lecture=faim`.

La chronique sépare le **décor** — géométrie, relief, climat, gisements, écrit
une fois — de l'**image**, ce qui bouge. Cinquante instants ne coûtent donc pas
cinquante fois deux mégaoctets.

### 3d. Le relief, en 3D

Demande `forge3d` et un GPU.

```bash
# la géographie
python3 -m vues.relief --snapshot monde.json --relief relief.png

# la statistique, élevée en relief
python3 -m vues.relief --snapshot monde.json --lecture population --statistique pop3d.png
```

Sans carte graphique, les deux **refusent proprement** avec le code 2 :

```
forge3d ne voit aucun adaptateur GPU (ni logiciel).
```

C'est voulu : la CI ne prétend pas rendre ce qu'elle ne peut pas rendre.

> **Une limite, nommée plutôt que contournée.** Dans la carte de statistique en
> 3D, c'est **la grandeur qui devient le terrain** — la population s'élève, les
> montagnes disparaissent. Colorier la vraie géographie par une grandeur
> indépendante demanderait un second canal de valeurs que `forge3d` n'expose
> pas : `OverlayLayer` ne se construit que depuis un dégradé appliqué au champ
> élevé.

---

## 4. Les tests

```bash
# tout, sauf ce qui demande un GPU
python3 -m pytest sim/tests/ vues/ forge/tests/ -q   # depuis jeu/

# par domaine
python3 -m pytest sim/tests/ -q          # le moteur
python3 -m pytest vues/relief/tests/ -q  # la carte de statistique
python3 -m pytest forge/tests/ -q        # la commande de bout en bout
```

Les tests du moteur sont longs sur un seul cœur :
`-n auto` les joue sur tous les cœurs (`pip install pytest-xdist`). La CI les
répartit en trois tranches, test par test, chacune sur les cœurs de son
runner ; une tranche se rejoue telle quelle en local :

```bash
python3 -m pytest sim/tests/ -q -n auto -m "not chronometre"       # tous les cœurs
FORGE_TRANCHE=2/3 python3 -m pytest sim/tests/ -q -n auto --dist worksteal -m "not chronometre"  # la tranche 2 de la CI
python3 -m pytest -m chronometre sim/tests/ -q                      # les tests qui chronomètrent, seuls
```

Quelques tests comparent un temps réel à un budget (un tick sous 100 ms, la
cadence de l'horloge) : sur tous les cœurs ils mesurent la charge de la
machine, pas le moteur. Ils portent `@pytest.mark.chronometre` ; la CI les joue
seuls, dans un travail à part, sans `-n`.

Le test qui garde la V1 :

```bash
python3 -m pytest sim/tests/test_survie.py -k amorce -q -s
# -> plafond derive a l'amorcage = 1.249107
```

Il rougit si le monde recommence à amorcer plus de bouches qu'il n'en nourrit.

---

## 5. La ville, sous Unity

Unity n'est pas sur une VM Linux. Tout ce qui touche au jeu en 3D passe par le
PC Windows (runner `pc-forge`).

```
Unity     : 6000.0.43f1
Pipeline  : URP 17.0.4
Projet    : 3d/unity (kit retenu : le désert)
Paquets   : 3d/unity/Packages/com.victoria.citymode.contracts, .presentation
Contrat   : jeu/ville/FORGEHISTORY_CITY_MODE_CONTRACT.md
Lanceurs  : pc\Ouvrir_Unity.cmd, pc\Ouvrir_Blender_Desert.cmd, pc\Ouvrir_Galerie_Desert.cmd
```

Les packs de l'Asset Store que le désert utilise vivent dans
`3d/unity/Assets/Vendor/`, ignoré par git : voir [3d/README.md](../3d/README.md).

---

## 6. Les pièges qu'on rencontre vraiment

| symptôme | cause | remède |
|---|---|---|
| `vues.relief` sort en code 2 | pas de GPU, ou `forge3d` absent | c'est un refus propre, pas un bug |
| la lecture `bourg` refuse | le snapshot lu ne porte pas le champ `bourg` | rephotographier le monde : `jeu/sim/snapshot_export.py` écrit le champ |
| la carte est d'une seule couleur | échelle mal choisie pour la distribution | `quantile` pour les grandeurs étalées |
| `--bobine` échoue | Chromium ou ffmpeg manquant | `--chrome` et `--ffmpeg` pointent un binaire |
| `--ticks` négatif | refusé | code 2, volontairement |
