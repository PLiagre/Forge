# Notice d'utilisation

> Tout ce qu'on peut lancer, dans l'ordre où on en a besoin. Chaque commande a
> été jouée sur ce dépôt ; les sorties citées sont réelles.

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

Le moteur ne dépend de rien. C'est voulu, et c'est vérifié : `sim/` n'importe
que la bibliothèque standard, pour qu'il tourne sur une machine nue.

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
sortie/carte.png       la statistique en plan, coloriée par une grandeur
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
  effondrement, pas une partie. Avant la fusion il valait 0,691.
- **`part_survivante`** dit ce que l'année a fait de la population. Au-dessus
  de 1, le monde croît.

Options utiles :

```bash
--lecture faim          la grandeur que la carte montre
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
| `densite` | habitants au km² | par rang |
| `nourriture` | stock de nourriture, en kg | par rang |
| `faim` | ticks de faim consécutifs | linéaire |
| `dette` | dette alimentaire par habitant | logarithme |
| `bourg` | part des habitants du bourg | linéaire — **refuse** aujourd'hui |

`bourg` refuse parce que le snapshot ne porte pas encore la donnée (lot 051).
Elle est déclarée quand même : c'est l'inventaire honnête de ce qui manque, et
elle deviendra verte toute seule le jour où le champ arrivera.

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
> indépendante demanderait un second canal de valeurs que `forge3d` 1.36
> n'expose pas : `OverlayLayer` ne se construit que depuis un dégradé appliqué
> au champ élevé. C'est le lot 104.

---

## 4. Les tests

```bash
# tout, sauf ce qui demande un GPU
python3 -m pytest sim/tests/ vues/ forge/tests/ outils/tests/ -q

# par domaine
python3 -m pytest sim/tests/ -q          # le moteur
python3 -m pytest vues/relief/tests/ -q  # la carte de statistique
python3 -m pytest forge/tests/ -q        # la commande de bout en bout
```

Le test qui garde la V1 :

```bash
python3 -m pytest sim/tests/test_survie.py -k amorce -q -s
# -> plafond derive a l'amorcage = 1.249107
```

Il rougit si le monde recommence à amorcer plus de bouches qu'il n'en nourrit.

---

## 5. Le registre des lots

Le registre est la **seule** représentation qui fait autorité sur l'état d'un
lot. Une machine le lit et refuse toute fiche mal formée, tout numéro dupliqué,
tout brief attendu qui manque, toute dépendance qui n'existe pas.

```bash
python3 -m atelier feuille valider --projet .
# -> PASS  ROADMAP.md — 61 lot(s), feuille cohérente

python3 -m atelier feuille etat --projet .
python3 -m atelier feuille marquer --projet . --lot 049 --etat livre --pr 12
```

L'atelier vit dans l'arbre, à `atelier/` : rien à installer, rien à aller
chercher sur une autre branche.

---

## 6. La chaîne d'intégration, jouée à la main

Ces commandes **décident** et n'écrivent jamais sur GitHub. Chacune imprime une
ligne sur la sortie standard — celle que le workflow lit — et son compte rendu
sur l'erreur standard.

```bash
export GITHUB_TOKEN=...

python3 -m outils relecture   --depot PLiagre/Forge --pr 12
python3 -m outils integration --depot PLiagre/Forge --projet .
python3 -m outils palier      --projet .
python3 -m outils tableau     --depot PLiagre/Forge --projet . --sortie site/index.html
python3 -m outils controles   --depot PLiagre/Forge --pr 12
python3 -m outils brouillon   --depot PLiagre/Forge --pr 12
```

`palier --ecrire`, `saisie --ecrire` et `etat --ecrire` sont les seules qui
touchent un fichier — et seulement celui du registre.

---

## 7. La ville, sous Unity

Unity n'est pas sur une VM Linux. Tout ce qui touche au jeu passe par une
machine Windows.

```
Unity     : 6000.0.43f1
Pipeline  : URP 17.0.4
Paquets   : unity/Packages/com.victoria.citymode*
Contrat   : ville/FORGEHISTORY_CITY_MODE_CONTRACT.md
```

> **Ce qui manque encore ici.** Le code Unity et les quatre paquets sont dans
> l'arbre ; les 199 Mo de binaires (FBX, textures, sons) vivaient en Git LFS et
> le clone de fusion n'en portait que les pointeurs. Ils restent à migrer depuis
> une machine qui les a réellement — c'est le lot 101. En attendant, le projet
> Unity ne s'ouvre pas complet.

---

## 8. La fabrique d'assets (Blender, hors Unity)

Aucune de ces commandes ne lance Unity.

```bash
python3 fabrique/citylab_factory.py doctor       # Blender est-il là ?
python3 fabrique/citylab_factory.py scan         # inventaire par SHA-256
python3 fabrique/citylab_factory.py recipe-check
python3 fabrique/qa_factory_release.py           # la QA transversale
```

La publication est en **dry-run par défaut** : rien n'est copié tant que
`publication-check` n'est pas appelé avec `--publish`.

---

## 9. Les pièges qu'on rencontre vraiment

| symptôme | cause | remède |
|---|---|---|
| `feuille valider` refuse | brief orphelin, fiche sans brief, dépendance fantôme | le message nomme le fichier fautif |
| `vues.relief` sort en code 2 | pas de GPU, ou `forge3d` absent | c'est un refus propre, pas un bug |
| la lecture `bourg` refuse | le snapshot ne porte pas encore le champ | attendu : c'est le lot 051 |
| la carte est d'une seule couleur | échelle mal choisie pour la distribution | `quantile` pour les grandeurs étalées |
| `--bobine` échoue | Chromium ou ffmpeg manquant | `--chrome` et `--ffmpeg` pointent un binaire |
| `--ticks` négatif | refusé | code 2, volontairement |
| une PR verte n'entre pas | contrôle absent, ou approbation périmée par un nouveau commit | un contrôle absent n'est pas un contrôle vert |
