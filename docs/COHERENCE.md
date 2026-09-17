# Inventaire de cohérence — produit face à `VISION.md`

Document de **constat** pour la révision mesurée ci-dessous. Une suite verte
ne transforme pas une promesse absente en promesse tenue ; l'état des lots
reste dans `ROADMAP.md` seul.

## Révision mesurée et rejeu

| Élément | Valeur |
|---|---|
| Révision git | `9ae6b32ffddec52300a2b9671e7e4924979ae0ec` |
| Python | 3.12.3 (`python3 --version`) |
| Dépendances du produit `sim/` et `vues/tableau/` | bibliothèque standard uniquement |
| Dépendances optionnelles `vues/relief/` | `requirements.txt` (forge3d, numpy) — non exigées pour `py -m sim` |

Commandes rejouées depuis la racine du dépôt (`PYTHONPATH=.` si besoin pour
les sondes qui importent `sim` ou `vues`) :

```bash
git rev-parse HEAD
python3 --version
python3 -m pytest sim/tests/ vues/tableau/tests/ -q
python3 -m sim --ticks 0 --seed 0 --json
python3 -m sim --ticks 365 --seed 0 --json
python3 -m pytest sim/tests/test_province.py vues/tableau/tests/test_viewer_v0b.py -q
python3 -m sim --ticks 20 --seed 0 --snapshot-json /tmp/fh-coherence.json
python3 -m pytest sim/tests/test_determinisme.py -q
```

### Résultats des exécutions (révision `9ae6b32…`)

| Commande | Code | Résultat utile |
|---|---|---|
| `pytest sim/tests/ vues/tableau/tests/ -q` | 0 | `207 passed in 535.07s` |
| `sim --ticks 0 --seed 0 --json` | 0 | 596 cellules, pop. 36 969 739, `kg_transportes`: 0.0 |
| `sim --ticks 365 --seed 0 --json` | 0 | pop. 36 969 739 → 38 010 422, `kg_transportes`: 6 187 172 660.81, 20 cellules affamées |
| `pytest test_province.py test_viewer_v0b.py -q` | 0 | `48 passed in 134.56s` |
| `sim --ticks 20 --seed 0 --snapshot-json /tmp/fh-coherence.json` | 0 | snapshot ~1.98 Mo, 596 cellules |
| `pytest test_determinisme.py -q` | 0 | `9 passed in 84.30s` |

Propositions non fusionnées : non mesurées comme produit ; seul le contenu de
`origin/master` à la révision ci-dessus fait foi ici.

---

## Assertions liminaires (hors titres `##`)

| ID | Promesse (citation courte) | État | Code / recherche | Preuve | Limite |
|---|---|---|---|---|---|
| L-01 | « Le moteur tourne dans `sim/` (`py -m sim`) » | mesure | `sim/__main__.py` | `python3 -m sim --ticks 0 --seed 0 --json` → exit 0, JSON émis | Ne couvre pas Unity ni clients externes |
| L-02 | « `viewer/` est un regard mince » (note d’en-tête) | partiel | `vues/tableau/` ; la note dit `viewer/` | Tableau lit snapshot via `vues/tableau/snapshot_loader.py` | Chemin réel `vues/tableau/`, pas `viewer/` ; wording vision périmé |
| L-03 | « Il n’y a pas de moteur de rendu » (note statut) | partiel | `vues/relief/rendu.py` appelle forge3d | `rg -n 'forge3d\|WebGPU' vues/relief/` → rendu 3D séparé du tick | Le tick tourne sans relief ; la note vision est en retard sur `vues/relief/` |
| L-04 | « Le monde est amorcé historiquement » (⚠️ vision) | partiel | `sim/world.py::_seed_population` ; `sim/MODELE.md` § Déclaration explicite | Carte figée niveau 1 (`data/world-1400.json`) + formules paramétriques | **Contradiction documentaire** : vision = historique à t0 ; modèle = proxy paramétrique, pas de source historique pour pop/stocks |
| L-05 | « L’émergence concerne ce qui arrive PENDANT la partie » | mesure | `sim/engine.py::tick` | 365 ticks modifient pop/stocks/commerce (résumé CLI) | L’amorçage reste paramétrique (L-04) |
| L-06 | « Ce document est la source de vérité de la vision produit » | mesure | `VISION.md` présent | Lecture seule pour cet inventaire | Écart vision ↔ `sim/MODELE.md` sur l’amorçage consigné, non réparé ici |

---

source : Ce que nous construisons

## Ce que nous construisons

| ID | Promesse | État | Code / recherche négative | Preuve | Limite |
|---|---|---|---|---|---|
| C-01 | Moteur de simulation historique, pas clone Victoria 3 | mesure | `sim/` agrégé cellulaire, pas de couche « Victoria » | `sim/README.md` + exécution `py -m sim` | Aucun critère « clone / non-clone » automatisé |
| C-02 | Gameplay émerge de la simulation | partiel | Faim → mortalité/migration/commerce dans `sim/engine.py` | Tests survie/commerce passent (suite SC2) | Pas de boucle joueur ni objectifs ; émergence partielle au sens vision |
| C-03 | Mécaniques type Victoria, EU4, Manor Lords, Total War émergent | absent | `rg -n 'diplom|fiscal|bataille tactique' sim/` → pas de modules état/armée tactique | Suite sim verte n’exerce pas ces domaines | Couches roadmap 3–5 non commencées (voir R-*) |

---

source : Principe fondateur : une seule simulation

## Principe fondateur : une seule simulation

| ID | Promesse | État | Code / recherche | Preuve | Limite |
|---|---|---|---|---|---|
| P-01 | Monde entier simulé en permanence | partiel | 596 cellules tickées ensemble (`World.cells`) | `sim --ticks 365` met à jour toutes les cellules actives | Pas de simulation off-map ni de « pause » stratégique |
| P-02 | Une seule source de vérité | partiel | État dans `World` ; vues lisent snapshot | `test_agregats_monde_derivent_du_snapshot` (48 tests province/tableau) | `stocks_mer` vit sur `World` mais absent de `World.to_dict()` (D-03) |
| P-03 | Interfaces n’observent que cette simulation | mesure | `vues/tableau/snapshot_loader.py` agrège le JSON exporté | Sonde SC3 ci-dessous | Relief 3D lit snapshot/MNT, ne décide rien |
| P-04 | Aucune donnée dupliquée pour une interface | partiel | Tableau ne recalcule pas le tick | Tests viewer_v0b | Snapshot duplique géométrie carte + état cellule (photographie, pas second moteur) |
| P-05 | Jamais deux bases stratégique vs tactique | mesure | Pas de couche tactique dans l’arbre | `rg 'tactique' sim/` → rien de jouable | Promesse tenue par absence de couche 5 |

---

source : Philosophie

## Philosophie

| ID | Promesse | État | Code / recherche | Preuve | Limite |
|---|---|---|---|---|---|
| PH-01 | Raisonner en termes de monde, pas de gameplay | partiel | Mortalité liée à `food_deficit_kg`, pas à un score « criminalité +20 % » | `sim/MODELE.md` + `sim/engine.py` | Pas d’audit exhaustif de toutes les constantes |
| PH-02 | Règles générales, comportements émergents | partiel | Commerce par arêtes, migration famine | `sim/tests/test_commerce.py`, `test_survie.py` (via suite SC2) | Nombreuses constantes de calibration niveau 2 |
| PH-03 | Test « émergent vs codé en dur » | absent | Aucun outil produit ne formalise ce test | — | Discipline de brief, pas de métrique inventaire |

---

source : Échelles de simulation

## Échelles de simulation

| ID | Promesse | État | Code / recherche négative | Preuve | Limite |
|---|---|---|---|---|---|
| E-01 | Hiérarchie Monde → … → Personne | absent | `rg 'class Personne|class Famille|Quartier' sim/*.py` → aucune entité | `sim/README.md` : population agrégée | Seule maille simulée : **cellule** (+ province dérivée) |
| E-02 | Chaque niveau simulable indépendamment | absent | Idem | — | Pas de zoom désagrégé |
| E-03 | Agrégations/désagrégations conservatives | partiel | `sim/aggregation.py` province ; bourg **dérivé** (`repartition_bourg_de_cellule`) | `sim/tests/test_province.py` | Bourg = répartition pop cellule, pas ville habitée ; snapshot n’exporte pas `bourg` (S-03) |
| E-04 | Rien ne se perd en changeant d’échelle | partiel | Masses nourriture/minerai suivies par cellule + bassin mer | Tests conservation commerce (suite SC2) | Pas de changement d’échelle réel, seulement invariant cellule |

---

source : Les piliers

## Les piliers

Chaque pilier de la vision est listé ; l’état reflète le moteur à la révision
mesurée, pas la feuille de route complète.

| ID | Pilier (vision) | État | Symbole / recherche | Preuve | Limite |
|---|---|---|---|---|---|
| PI-01 | Géographie | mesure | `data/world-1400.json`, `World.carte` | 596 cellules, géométrie dans snapshot | Carte figée, non régénérée |
| PI-02 | Climat | partiel | Carte + `sim/engine.py` saisons | Climat exporté snapshot ; `_couche_consommee("climat")` mesure usage tick | Relief/climat/gisements : export « utilisée_par_le_moteur » mesuré dans snapshot |
| PI-03 | Saisons | mesure | `sim/constants.py::jour_de_tick`, `tick(..., numero_tick)` | `test_jour_de_tick_present_ou_absent` | Année = 365 jours dérivés ; pas calendrier historique daté |
| PI-04 | Ressources naturelles | partiel | Gisements sur carte, extraction minière | Tests gisements/commerce (SC2) | Minerai : commerce limité (MODELE) |
| PI-05 | Population | mesure | `Cell.population`, natalité/mortalité/migration | 365 ticks changent la pop | Agrégée, pas individus |
| PI-06 | Familles | absent | `rg 'Famille' sim/` → aucun type | — | — |
| PI-07 | Économie | partiel | Production, stocks, déficit | Suite sim | Pas de prix/marchés |
| PI-08 | Commerce | mesure | `sim/engine.py` commerce + `stocks_mer` | `kg_transportes` > 0 après 365 ticks | Maritime partiel selon topologie |
| PI-09 | Infrastructures | absent | `rg 'route|pont|infrastructure' sim/engine.py` → pas de réseau routier simulé | — | — |
| PI-10 | Politique | absent | `rg -i 'politique|loi|fiscal' sim/` → rien | — | Couche 3 non commencée |
| PI-11 | Diplomatie | absent | `rg -i 'diplom' sim/` → rien | — | — |
| PI-12 | Religion | absent | `rg -i 'religion' sim/` → constantes commentaires seulement | — | — |
| PI-13 | Culture | absent | `rg -i 'culture' sim/` → rien de simulé | — | — |
| PI-14 | Technologie | absent | `rg -i 'technolog' sim/` → rien | — | — |
| PI-15 | Armées | absent | `rg -i 'armee|armée|soldat' sim/` → consommation métaphorique seulement | — | Couche 4 |
| PI-16 | Logistique | partiel | Transport kg inter-cellules + mer | Tests commerce SC2 | Pas de convois/armées |
| PI-17 | Urbanisation | absent | Pas de construction de quartiers | Bourg dérivé numériquement seulement | — |
| PI-18 | Industrie | absent | Pas d’usines/chaînes | Extraction + nourriture | — |
| PI-19 | « Chaque système évolue indépendamment » | absent | Systèmes absents ci-dessus | — | Formulation vision = cible, pas état |

---

source : Règles par domaine

## Règles par domaine

| ID | Promesse | État | Code / recherche | Preuve | Limite |
|---|---|---|---|---|---|
| Règ-01 | Population : personne → famille → … → États émergent | absent | Pas de personne (`E-01`) | — | Pop cellulaire + province |
| Règ-02 | Économie entièrement physique | partiel | Flux kg, pas de téléportation agrégée non testée | `test_kg_transportes_egal_deltas_positifs` (commerce) | Bassin mer séparé de `to_dict()` |
| Règ-03 | Armées depuis population, consommation, retour civil | absent | Pas d’entité armée | — | Lot recensé : aucun (couche armées) |
| Règ-04 | Urbanisation : conditions, pas placement bâtiment | absent | Pas de bâtiments | — | — |
| Règ-05 | Batailles : même données, retour pertes au monde | absent | Pas de couche bataille | — | — |

---

source : Architecture en couches

## Architecture en couches

| ID | Promesse | État | Code | Preuve | Limite |
|---|---|---|---|---|---|
| A-01 | Core → … → Présentation | partiel | `sim/` + `vues/tableau/` + `vues/relief/` | Imports : tableau lit sim.constants, pas l’inverse | Relief optionnel |
| A-02 | Présentation sans logique métier | mesure | `snapshot_loader` classify/agrège | Tests viewer | `classify` est présentation, pas tick |
| A-03 | Moteur tourne sans présentation | mesure | `py -m sim` sans vues | SC2 CLI | — |

---

source : Roadmap par couches

## Roadmap par couches

| ID | Couche vision | État produit | Indices | Preuve | Lot registre si écart nommé |
|---|---|---|---|---|---|
| R-01 | 1 — Monde vivant | partiel | Carte, pop, économie locale, commerce | Suite sim + snapshot | Palier couche 1 : voir ROADMAP (non inventaire ici) |
| R-02 | 2 — Villes | absent | Pas de ville simulée | Bourg dérivé, pas snapshot bourg | Briefs 051–052 en PR possibles, non fusionnés à `9ae6b32` |
| R-03 | 3 — États | absent | — | — | aucun lot recensé pour couche entière |
| R-04 | 4 — Armées | absent | — | — | aucun lot recensé |
| R-05 | 5 — Batailles tactiques | absent | — | — | aucun lot recensé |

---

source : Mesure du succès

## Mesure du succès

| ID | Promesse | État | Code | Preuve | Limite |
|---|---|---|---|---|---|
| M-01 | Succès = émergence de situations complexes, pas nombre de features | absent | Aucune métrique produit | — | Jugement qualitatif hors scope mesure auto |
| M-02 | Crédibilité / intérêt joueur | non_verifie | Nécessite playtest humain | Non joué dans cet inventaire | — |

---

## Jointures demandées (écarts types)

### Amorçage historique vs paramétrique

Constat : **L-04**. Population/stocks initiaux via `_seed_population` /
`_seed_food_stock` et rendement (`sim/world.py`, `sim/engine.py`).
`sim/MODELE.md` l’affirme explicitement paramétrique ; `VISION.md` affirme
l’inverse en en-tête. Reproduction : lire les deux fichiers ; amorçer
`World.charger(rng_seed=0)` et comparer à aucune table historique (absente).

### Hiérarchie conservatrice vs cellule / province / bourg

- Simulé : cellule (`sim/model.py::Cell`).
- Dérivé : province (`sim/aggregation.py`), bourg/champs (`repartition_bourg_de_cellule`) — **vue**, tick ne consulte pas le bourg (`test_province.py` SC6).
- Absent : Pays, Ville, Quartier, Bâtiment, Famille, Personne (`E-01`).

### Économie physique et bassin maritime

- Transport terrestre cumulé dans `kg_transportes` (CLI et tick).
- `World.stocks_mer` modifié par commerce maritime (`sim/engine.py`).
- Masse : tests commerce SC2 ; mer incluse dans runs avec façade maritime.

### Déterminisme et `World.to_dict()`

| ID | Fait | État | Preuve |
|---|---|---|---|
| D-01 | Empreinte SHA256 via `World.to_dict()` identique à graine fixe | mesure | `test_ticks_deterministes_meme_graine` (nom d’empreinte dans test, pas valeur citée ici) |
| D-02 | `World.to_dict()` ne contient que `cells` | mesure | `sim/world.py:169-179` |
| D-03 | `stocks_mer` déterministe mais hors `to_dict()` | mesure | `test_bassin_maritime_deterministe_a_graine_fixe` + sonde ci-dessous |

Sonde reproductible (20 ticks, graine 0) — preuve SC4 :

```bash
PYTHONPATH=. python3 <<'PY'
import random
from sim.world import World
from sim import engine

def serie(seed, n=20):
    world = World.charger(rng_seed=seed)
    rng = random.Random(seed)
    vus = []
    for i in range(n):
        engine.tick(world, rng, i)
        vus.append(dict(world.stocks_mer))
    return vus

p, s = serie(0), serie(0)
assert any(panier for panier in p), "échantillon vide : bassin jamais chargé"
assert p == s
print("OK cellules via to_dict non montré ici ; bassin identique tick à tick")
PY
```

Exécution à `9ae6b32…` : exit 0, message `bassin_deterministe_20_ticks: OK, paniers_non_vides 20`.

### Date, jour saisonnier, régimes de `tick`

- `TICK_DURATION_DAYS = 1` : un tick = un jour (`sim/constants.py`).
- `jour_de_tick(numero_tick)` : rang dans l’année 365 jours, pas date 1400.
- `tick(world, rng, numero_tick=None)` : sans numéro → saison moyenne annuelle ; avec numéro → saison du jour (`sim/MODELE.md` § régimes).
- Reproduction : `python3 -m sim --ticks 365 --seed 0 --json` ≠ calendrier historique.

### Snapshot, tableau, champs exportés

Export : `sim/snapshot_export.py::build_snapshot_document`. Champs racine lus
par `agregats_monde` : `cells`, `tick`, `seed`, `jour_de_tick`, `kg_transportes`.

**Non exportés** à cette révision : `stocks_mer`, bloc `bourg` par cellule
(recherche `rg '"bourg"' sim/snapshot_export.py` → aucune occurrence).

Sonde SC3 — comparer agrégats tableau aux sommes cellules (`/tmp/fh-coherence.json`) :

```bash
python3 -m sim --ticks 20 --seed 0 --snapshot-json /tmp/fh-coherence.json
PYTHONPATH=. python3 <<'PY'
import json
from pathlib import Path
from vues.tableau.snapshot_loader import EchantillonVide, agregats_monde
from sim.constants import MARCHANDISE_NOURRITURE

doc = json.loads(Path("/tmp/fh-coherence.json").read_text())
kpis = agregats_monde(doc)
cells = doc["cells"]
pop_sum = sum(c["population"] for c in cells if "population" in c)
assert kpis["population"]["valeur"] == pop_sum
stock_sum = sum(float(c["stocks"][MARCHANDISE_NOURRITURE])
                for c in cells if isinstance(c.get("stocks"), dict)
                and MARCHANDISE_NOURRITURE in c["stocks"])
assert kpis["stock_nourriture_kg"]["valeur"] == stock_sum
assert not any("bourg" in c for c in cells)
try:
    agregats_monde({"cells": []})
except EchantillonVide:
    pass
else:
    raise SystemExit("EchantillonVide attendu")
print("OK", len(cells), "cellules")
PY
```

Résultat `9ae6b32…` : 596 cellules ; `population` et `stock_nourriture_kg`
alignés ; `bourg_dans_cellules` False ; `EchantillonVide` sur liste vide OK.
Champs `kg_transportes` / `jour_de_tick` : présents dans snapshot de cette
course → `mesure` dans kpis ; s’ils manquaient, le loader répondrait `absent`
(sans inventer zéro).

### Causalité simulée vs raccourcis

Faim, production, commerce, mortalité enchaînés dans `engine.tick` (tests
survie/commerce). Pas de levier « gameplay » direct. Couches non simulées =
absence de causalité, pas raccourci silencieux.

### Photographie vs sauvegarde ; vue vs habitants

- Snapshot JSON : export one-shot ; **aucun** `World.charger_depuis_snapshot` dans `sim/` (`rg 'export_snapshot|load_snapshot' sim/` → export seulement côté moteur).
- Tableau : agrégats population, pas individus (`agregats_monde`).
- Relief : `vues/relief/tests/test_raster.py` prouve la rasterisation CPU ;
  rendu GPU forge3d (`rendu.py`) **non exécuté** dans les preuves SC2 — essai
  GPU = `non_verifie` (dépendance externe, pas lancé ici).

---

## Défauts observés (reproduction, invariant, lot)

| Défaut | Reproduction | Invariant / règle | Lot registre |
|---|---|---|---|
| Vision « amorçage historique » vs modèle paramétrique | Lire `VISION.md` ⚠️ et `sim/MODELE.md` § Déclaration explicite | Règle 10 AGENTS — absence déclarée côté modèle seulement | aucun lot recensé |
| Empreinte `to_dict()` ignore la mer | Deux runs : hash `to_dict()` égal mais comparer `stocks_mer` | Déterminisme (test_bassin_maritime_*) | aucun lot recensé (couvert par test existant) |
| Snapshot sans bourg / sans mer | `build_snapshot_document` vs `repartition_bourg_de_cellule` existant | Vue lit ce qui est photographié | lots 051–052 (état registre), non fusionnés à cette révision |
| Note vision « pas de moteur de rendu » vs `vues/relief/` | Lire en-tête `VISION.md` et `vues/relief/rendu.py` | Présentation séparée | aucun lot recensé |

Aucune priorité ni numéro de lot inventé au-delà du registre.

---

## Contrôle SC1 (sections vision)

Neuf lignes `source : …` dans ce fichier reprennent exactement les titres
`##` de `VISION.md`. Les assertions liminaires et jointures couvrent les
puces d’en-tête (produit, rendu, amorçage historique, primauté vision).
